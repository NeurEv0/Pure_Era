import json
from collections import Counter
import pandas as pd
import numpy as np
import math

import torch
from torch.utils.data import Dataset, DataLoader, random_split

valid_aminos = ["A", "F", "C", "U", "D", "N", "E", "Q", "G", "H", "L", "I",
                "K", "O", "M", "P", "R", "S", "T", "V", "W", "Y", "B", "Z",
                "J"]
MAX_SEQ_LENGTH = 100
MIN_LABEL_COUNT = 100

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
                      if count >= MIN_LABEL_COUNT and pd.notna(org)}
    valid_organisms = sorted(valid_organisms)
    org_to_idx = {org: idx for idx, org in enumerate(valid_organisms)}
    print(f"[Info] the number of valid organisms: {len(valid_organisms)}")
    print(org_to_idx)
    return org_to_idx

def convert_and_normalize(labels, organism_projection):
    def calculate_parameters4half_life(labels):
        values = []
        for label in labels:
            if 'half_life_regression' in label and label['half_life_regression'] is not None:
                values.append(label['half_life_regression'])

        assert len(values) > 0, "No half life values found"

        converted = -np.log10(np.array(values))
        mean = np.mean(converted)
        std = np.std(converted)
        print(f"[Info] Half life mean: {mean}, std: {std}")
        return mean, std
    
    def calculate_parameters4mic(labels):
        values = []
        for label in labels:
            if 'mic_regression' in label:
                for v in label['mic_regression'].values():
                    if v > 0:
                        values.append(v)

        assert len(values) > 0, "No mic values found"
        
        converted = -np.log10(np.array(values))
        mean = np.mean(converted)
        std = np.std(converted)
        print(f"[Info] MIC mean: {mean}, std: {std}")
        return mean, std   
    
    mic_mean, mic_std = calculate_parameters4mic(labels)
    hl_mean, hl_std = calculate_parameters4half_life(labels)

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
        
        if 'mic_regression' in label:
            new_mic_regression = {}
            for org, value in list(label['mic_regression'].items()):
                if org in organism_projection and value > 0:
                    o_id = organism_projection[org]
                    log_val = -math.log10(value)
                    normed = (log_val - mic_mean) / mic_std
                    new_mic_regression[o_id] = o_id
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
                            'values': torch.tensor(v, dtype=torch.float)
                        }
                        self.valid_samples.append(modified_sample)

        else:
            for sample in self.samples:
                if task_name in sample:
                    modified_sample = {
                        'Sequence': sample['Sequence'],
                        task_name: sample[task_name]
                    }
                    self.valid_samples.append(modified_sample)
        print(f"[Info] the number of valid samples: {len(self.valid_samples)}")

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
    task_name = "mic_regression"
    train_loader, val_loader, test_loader = build_dataloader(file_path, task_name, 64)
