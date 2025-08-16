import json
from collections import Counter
import pandas as pd
import numpy as np
import math
import os

import torch
from torch.utils.data import Dataset, DataLoader, random_split

valid_aminos = ["A", "F", "C", "U", "D", "N", "E", "Q", "G", "H", "L", "I",
                "K", "O", "M", "P", "R", "S", "T", "V", "W", "Y", "B", "Z",
                ]
MAX_SEQ_LENGTH = 100
MIN_LABEL_COUNT = 100
MIN_ORGANISM_COUNT = 500
PARAMS_FILE = "normalization_parameters.csv"

def filt_seq(seq):
    if len(seq) > 0 and len(seq) < MAX_SEQ_LENGTH:
        return all(char in valid_aminos for char in seq)
    return False  

def create_bioactivity_projection(labels):
    label_count = Counter()
    for label in labels:
        if 'bioactivity_classification' in label:
            label_count.update(label['bioactivity_classification'])

    selected_labels = [label for label, count in label_count.items() 
                       if count >= MIN_LABEL_COUNT]
    selected_labels = sorted(selected_labels)
    label_to_idx = {label: idx for idx, label in enumerate(selected_labels)}
    print(f"[Info] selected {len(selected_labels)} kind of projection: {label_to_idx}")
    return label_to_idx

def create_orgainsm_projection(labels):
    all_orgs = [
        org 
        for label in labels 
        if 'mic_regression' in label 
        for org in label['mic_regression'] 
        if pd.notna(org)
    ]
    org_counter = Counter(all_orgs)

    valid_organisms = {org for org, count in org_counter.items() 
                      if count >= MIN_ORGANISM_COUNT and pd.notna(org)}
    valid_organisms = sorted(valid_organisms)
    org_to_idx = {org: idx for idx, org in enumerate(valid_organisms)}
    print(f"[Info] the number of valid organisms: {len(valid_organisms)}")
    print(org_to_idx)
    return org_to_idx

def calculate_mic_stats_by_organism(labels, organism_projection):
    idx_to_org = {idx: org for org, idx in organism_projection.items()}
    mic_values = {org_idx: [] for org_idx in idx_to_org.keys()}
    
    for label in labels:
        if 'mic_regression' in label:
            for org, value in label['mic_regression'].items():
                if org in organism_projection and value > 0:
                    org_idx = organism_projection[org]
                    log_val = -math.log10(value)
                    mic_values[org_idx].append(log_val)
    
    # calculate average value and mean standard deviation for each organism
    mic_stats = {}
    for org_idx, values in mic_values.items():
        if values:  # make sure there are values
            mean = np.mean(values)
            std = np.std(values)
            mic_stats[org_idx] = (mean, std)
    
    return mic_stats

def save_normalization_parameters(params):
    """保存所有标准化参数到CSV文件"""
    df = pd.DataFrame(columns=["parameter_type", "organism", "mean", "std"])
    
    for org_idx, (mean, std) in params["mic_params"].items():
        org_name = params["idx_to_org"].get(org_idx, f"organism_{org_idx}")
        df = pd.concat([df, pd.DataFrame([{
            "parameter_type": "mic_regression",
            "organism": org_name,
            "mean": mean,
            "std": std
        }])], ignore_index=True)
    
    df = pd.concat([df, pd.DataFrame([{
        "parameter_type": "half_life_regression",
        "organism": None,
        "mean": params["hl_mean"],
        "std": params["hl_std"]
    }])], ignore_index=True)
    
    df = pd.concat([df, pd.DataFrame([{
        "parameter_type": "hemolysis_regression",
        "organism": None,
        "mean": params["hem_mean"],
        "std": params["hem_std"]
    }])], ignore_index=True)
    
    df.to_csv(PARAMS_FILE, index=False)
    print(f"[Info] Saved normalization parameters to {PARAMS_FILE}")

def convert_and_normalize(labels, organism_projection):
    idx_to_org = {idx: org for org, idx in organism_projection.items()}
    def calculate_parameters4half_life(labels):
        values = []
        for label in labels:
            if 'half_life_regression' in label and label['half_life_regression'] is not None:
                values.append(label['half_life_regression'])

        assert len(values) > 0, "No half life values found"

        converted = -np.log10(np.array(values))
        mean = np.mean(converted)
        std = np.std(converted)
        return mean, std  
    
    def calculate_parameters4hemolysis(labels):
        values = []
        for label in labels:
            if 'hemolysis_regression' in label and label['hemolysis_regression'] is not None:
                values.append(label['hemolysis_regression'])

        assert len(values) > 0, "No hemolysis values found"
        converted = np.log1p(values)
        mean = np.mean(converted)
        std = np.std(converted)
        return mean, std
    
    mic_stats_by_org = calculate_mic_stats_by_organism(labels, organism_projection)

    hl_mean, hl_std = calculate_parameters4half_life(labels)
    hem_mean, hem_std = calculate_parameters4hemolysis(labels)

    # save normalization parameters
    normalization_params = {
        "mic_params": mic_stats_by_org,
        "hl_mean": hl_mean,
        "hl_std": hl_std,
        "hem_mean": hem_mean,
        "hem_std": hem_std,
        "idx_to_org": idx_to_org
    }
    save_normalization_parameters(normalization_params)

    # apply the conversion and normalization
    for label in labels:
        if 'half_life_regression' in label and label['half_life_regression'] is not None:
            value = label['half_life_regression']
            if value <= 0:
                label['half_life_regression'] = torch.tensor(float('nan'))
            else:
                log_val = -math.log10(value)
                normed = (log_val - hl_mean) / hl_std
                label['half_life_regression'] = torch.tensor(normed, dtype=torch.float)
        
        if 'hemolysis_regression' in label and label['hemolysis_regression'] is not None:
            value = label['hemolysis_regression']
            if value <= 0:
                label['hemolysis_regression'] = torch.tensor(float('nan'))
            else:
                log_val = math.log1p(value)
                normed = (log_val - hem_mean) / hem_std
                label['hemolysis_regression'] = torch.tensor(normed, dtype=torch.float)

        if 'mic_regression' in label:
            new_mic_regression = {}
            for org, value in list(label['mic_regression'].items()):
                if org in organism_projection and value > 0:
                    org_idx = organism_projection[org]
                    log_val = -math.log10(value)
                    
                    # 使用对应微生物的统计量进行标准化
                    if org_idx in mic_stats_by_org:
                        mean, std = mic_stats_by_org[org_idx]
                        normed = (log_val - mean) / std
                    else:
                        # 如果找不到该微生物的统计量，使用全局平均值作为后备
                        # (实际不会发生，因为我们已经过滤了样本量不足的微生物)
                        normed = log_val
                    
                    new_mic_regression[org_idx] = normed
            label['mic_regression'] = new_mic_regression
    return labels

def load_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    seqs = list(data.keys())
    labels = list(data.values())
    bioactivity_projection = create_bioactivity_projection(labels)
    organism_projection = create_orgainsm_projection(labels)
    labels = convert_and_normalize(labels, organism_projection)

    valid_samples = []
    for seq, label in zip(seqs, labels):
        if not filt_seq(seq) or not label:
            continue

        label['Sequence'] = seq.upper()

        if 'amp_classification' in label:
            label['amp_classification'] = torch.tensor(label['amp_classification'], dtype=torch.long)
        
        if 'bioactivity_classification' in label:
            multihot = [0] * len(bioactivity_projection)
            for l in label['bioactivity_classification']:
                if l in bioactivity_projection:
                    multihot[bioactivity_projection[l]] = 1
            label['bioactivity_classification'] = torch.tensor(multihot, dtype=torch.float)
        
        valid_samples.append(label)
    return valid_samples

class AMPDataset(Dataset):
    def __init__(self, file_path, task_name):
        super().__init__()
        assert task_name in ['amp_classification', 'bioactivity_classification', 'mic_regression', 'half_life_regression', 'hemolysis_regression'], "Invalid task name"

        self.samples = load_data(file_path)
        self.valid_samples = []

        if task_name == 'mic_regression':
            for sample in self.samples:
                if task_name in sample and sample[task_name]:
                    organisms = list(sample[task_name].keys())
                    values = list(sample[task_name].values())
                    assert len(organisms) == len(values), f"Mismatch between number of organisms and values. Organisms: {len(organisms)}, Values: {len(values)}"

                    for o, v in zip(organisms, values):
                        modified_sample = {
                            'Sequence': sample['Sequence'],
                            'organism': torch.tensor(o, dtype=torch.long),
                            'label': torch.tensor(v, dtype=torch.float)
                        }
                        self.valid_samples.append(modified_sample)

        else:
            for sample in self.samples:
                if task_name in sample:
                    modified_sample = {
                        'Sequence': sample['Sequence'],
                        'label': sample[task_name]
                    }
                    self.valid_samples.append(modified_sample)
        
        print(f"[Info] Loaded {len(self.valid_samples)} samples for task {task_name}")

    def __len__(self):
        return len(self.valid_samples)
    
    def __getitem__(self, idx):
        return self.valid_samples[idx]

def build_dataloader(file_path, task_name, batch_size):
    dataset = AMPDataset(file_path, task_name)
    num_samples = len(dataset)

    num_train = int(num_samples * 0.8)
    num_val = int(num_samples * 0.1)
    num_test = num_samples - num_train - num_val

    train_dataset, val_dataset, test_dataset = random_split(
        dataset, 
        [num_train, num_val, num_test],
        generator=torch.Generator().manual_seed(1234)
        )
    
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False
    )
    test_loader = DataLoader(
        test_dataset,
        batch_size=batch_size,
        shuffle=False
    )
    return train_loader, val_loader, test_loader

if __name__ == '__main__':
    file_path = "merged_data.json"
    train_loader, val_loader, test_loader = build_dataloader(file_path, "half_life_regression", 64)