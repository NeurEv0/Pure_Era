import json
from tqdm import tqdm
import os
import gc
import pandas as pd

import torch
from torch.utils.data import Dataset, DataLoader, random_split
import torch.nn as nn
from transformers import EsmTokenizer

from modeling_amp import AMPConfig, AMPForMultiTask

valid_aminos = ["A", "F", "C", "U", "D", "N", "E", "Q", "G", "H", "L", "I",
                "K", "O", "M", "P", "R", "S", "T", "V", "W", "Y", "B", "Z",
                "J"]
MAX_SEQ_LENGTH = 100

def filt_seq(seq):
    if len(seq) > 0 and len(seq) < MAX_SEQ_LENGTH:
        return all(char in valid_aminos for char in seq)
    return False  

def load_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    seqs = list(data.keys())
    seqs = [seq for seq in seqs if filt_seq(seq)]
    return seqs

class MaskedPeptidesDataset(Dataset):
    def __init__(self, file_path, tokenizer, max_length=128, mask_prob=0.15):
        self.samples = load_data(file_path)
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.mask_prob = mask_prob
        self.mask_token_id = tokenizer.mask_token_id
        self.vocab_size = tokenizer.vocab_size
        self.special_token_ids = tokenizer.special_tokens_map
        self.prob_replace_mask = 0.8  # 80%替换为[MASK]
        self.prob_replace_rand = 0.1  # 10%替换为随机token

    def __getitem__(self, idx):
        seq = self.samples[idx]
        encoding = self.tokenizer(
            seq,
            padding='max_length',
            max_length=self.max_length,
            truncation=True,
            return_tensors='pt'
        )
        input_ids = encoding['input_ids'].squeeze(0)
        attention_mask = encoding['attention_mask'].squeeze(0)

        masked_inputs, labels = self.mask_tokens(input_ids.clone())
        
        return {
            'input_ids': masked_inputs,
            'attention_mask': attention_mask,
            'labels': labels
        }
    
    def __len__(self):
        return len(self.samples)

    def mask_tokens(self, inputs):
        """
        Prepare masked tokens inputs/labels for masked language modeling: 80% MASK, 10% random, 10% original.
        """
        labels = inputs.clone()
        # We sample a few tokens in each sequence for MLM training (with probability `self.mask_prob`)
        special_tokens_mask = torch.zeros_like(inputs, dtype=torch.bool)
        for token_id in self.special_token_ids:
            special_tokens_mask |= (inputs == token_id)

        probability_matrix = torch.full(labels.shape, self.mask_prob)
        probability_matrix.masked_fill_(special_tokens_mask, value=0.0)
        masked_indices = torch.bernoulli(probability_matrix).bool()
        labels[~masked_indices] = -100  # We only compute loss on masked tokens

        # 80% of the time, we replace masked input tokens with tokenizer.mask_token ([MASK])
        indices_replaced = torch.bernoulli(torch.full(labels.shape, self.prob_replace_mask)).bool() & masked_indices
        inputs[indices_replaced] = self.mask_token_id

        # 10% of the time, we replace masked input tokens with random word
        current_prob = self.prob_replace_rand / (1 - self.prob_replace_mask)
        indices_random = torch.bernoulli(torch.full(labels.shape, current_prob)).bool() & masked_indices & ~indices_replaced
        random_words = torch.randint(len(self.tokenizer), labels.shape, dtype=torch.long)
        for token_id in self.special_token_ids:
            indices_random = indices_random & (inputs != token_id)
        inputs[indices_random] = random_words[indices_random]

        # The rest of the time (10% of the time) we keep the masked input tokens unchanged
        return inputs, labels

def build_dataloader(file_path, tokenizer, batch_size):
    dataset = MaskedPeptidesDataset(file_path, tokenizer)
    num_samples = len(dataset)

    num_train = int(num_samples * 0.8)
    num_val = int(num_samples * 0.1)
    num_test = num_samples - num_train - num_val

    train_dataset, val_dataset, test_dataset = random_split(
        dataset, 
        [num_train, num_val, num_test],
        generator=torch.Generator().manual_seed(1234)
    )
    print(f"[Info] Train: {num_train}, Val: {num_val}, Test: {num_test}")

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

class EarlyStopping:
    def __init__(self, patience=5, delta=0, output_dir=None, checkpoint_path='best_model.pt'):
        self.patience = patience
        self.delta = delta
        self.counter = 0
        self.best_score = None
        self.early_stop = False
        self.min_val_loss = float('inf')
        if output_dir:
            self.checkpoint_path = os.path.join(output_dir, checkpoint_path)
        else:
            self.checkpoint_path = checkpoint_path

    def __call__(self, val_loss, model):
        if self.best_score is None:
            self.best_score = val_loss
            self.save_checkpoint(val_loss, model)
        elif val_loss > self.best_score + self.delta:
            self.counter += 1
            print(f"EarlyStopping counter: {self.counter}/{self.patience}")
            if self.counter >= self.patience:
                self.early_stop = True
        else:
            if val_loss < self.best_score:
                self.best_score = val_loss
                self.save_checkpoint(val_loss, model)
            self.counter = 0  

    def save_checkpoint(self, val_loss, model):
        if val_loss < self.min_val_loss:
            self.min_val_loss = val_loss
            torch.save(model.state_dict(), self.checkpoint_path)
            print(f"Validation loss improved to {val_loss:.5f}. Model saved to {self.checkpoint_path}!")

class TrainingConfig:
    def __init__(self):
        self.batch_size = 64
        self.learning_rate = 5e-5  
        self.epochs = 100
        self.max_grad_norm = 1.0
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_dir = "amp4multitask"
        self.data_path = "merged_data.json"
        self.save_dir = "training_outputs" 
        self.checkpoint_path = os.path.join(self.save_dir, "best_pretrain_model.pth")
        os.makedirs(self.save_dir, exist_ok=True)

def train():
    config = TrainingConfig()
    device = torch.device(config.device)
    print(f"Using device: {device}")

    tokenizer = EsmTokenizer.from_pretrained(
        config.model_dir,
        padding_side="left"
    )

    with open(os.path.join(config.model_dir, "task_config.json"), encoding='utf-8') as f:
        task_config = json.load(f)

    train_loader, val_loader, _ = build_dataloader(config.data_path, tokenizer, config.batch_size)

    amp_config = AMPConfig.from_json_file(os.path.join(config.model_dir, "config.json"))
    model = AMPForMultiTask(amp_config, task_config)
    model = model.to(device)

    checkpoint = torch.load(config.checkpoint_path, map_location=device)
    model.load_state_dict(checkpoint, strict=False)
    print(f"[Info] Model loaded from {config.checkpoint_path}")

    optimizer = torch.optim.AdamW(
        model.parameters(), 
        lr=config.learning_rate
    )

    loss_fn = nn.CrossEntropyLoss(ignore_index=-100)
    early_stopping = EarlyStopping(output_dir=config.save_dir, checkpoint_path="best_pretrain_model.pth")

    train_history = {
        'epoch': [],
        'train_loss': [],
        'val_loss': []
    }

    for epoch in range(config.epochs):
        model.train()
        model.set_train_mode("masked_lm")
        total_train_loss = 0
        train_steps = 0

        process_bar = tqdm(train_loader, desc=f"Epoch {epoch+1}/{config.epochs}")
        for batch in process_bar:
            inputs = batch['input_ids'].to(device)
            if torch.isnan(inputs).any() or torch.isinf(inputs).any():
                print("NaN/Inf detected in inputs, skipping batch")
                optimizer.zero_grad()
                continue

            attention_mask = batch['attention_mask'].to(device)
            if torch.isnan(attention_mask).any() or torch.isinf(attention_mask).any():
                print("NaN/Inf detected in attention_mask, skipping batch")
                optimizer.zero_grad()
                continue
            labels = batch['labels'].to(device)
            if torch.isnan(labels).any() or torch.isinf(labels).any():
                print("NaN/Inf detected in labels, skipping batch")
                optimizer.zero_grad()
                continue

            outputs = model(
                input_ids=inputs, 
                attention_mask=attention_mask, 
                task_name="masked_lm"
            )

            if torch.isnan(outputs).any() or torch.isinf(outputs).any():
                print("NaN/Inf detected in model outputs, skipping batch")
                optimizer.zero_grad()
                continue

            logits = outputs.view(-1, outputs.size(-1))
            labels_flat = labels.view(-1)

            loss = loss_fn(logits, labels_flat)

            if torch.isnan(loss) or torch.isinf(loss):
                print(f"Invalid loss value: {loss.item()}, skipping batch")
                optimizer.zero_grad()
                continue

            total_train_loss += loss.item()
            train_steps += 1
            
            # Backward pass and optimize
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), config.max_grad_norm)
            optimizer.step()
            process_bar.set_postfix({'loss': round(loss.item(), 4)})

            del inputs, labels, outputs, loss
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        avg_train_loss = total_train_loss / train_steps
        avg_val_loss = validate(model, val_loader, loss_fn, device)
        
        print(f"Epoch {epoch+1}/{config.epochs}: Train Loss: {avg_train_loss:.4f}, Val Loss: {avg_val_loss:.4f}")
        train_history["epoch"].append(epoch + 1)
        train_history["train_loss"].append(avg_train_loss)
        train_history["val_loss"].append(avg_val_loss)

        early_stopping(avg_val_loss, model)
        if early_stopping.early_stop:
            print(f"Early stopping triggered at epoch {epoch+1}")
            break
    
    final_model_path = os.path.join(config.save_dir, "final_model.pt")
    torch.save(model.state_dict(), final_model_path)
    print(f"Final model saved at {final_model_path}")

    # Save final loss history
    save_loss_history(train_history, config.save_dir)
    print("Training completed!")

def validate(model, val_loader, loss_fn, device):
    model.eval()
    total_val_loss = 0
    val_steps = 0
    
    with torch.no_grad():
        for batch in tqdm(val_loader, desc="Validation"):
            inputs = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels = batch['labels'].to(device)
            
            outputs = model(
                input_ids=inputs, 
                attention_mask=attention_mask, 
                task_name="masked_lm"
            )

            if torch.isnan(outputs).any():
                print(f"NaN in model outputs")
                break

            logits = outputs.view(-1, outputs.size(-1))
            labels_flat = labels.view(-1)
            loss = loss_fn(logits, labels_flat)

            if torch.isnan(loss) or torch.isinf(loss):
                print(f"NaN/Inf validation loss: {loss.item()}")
                continue
            
            total_val_loss += loss.item()
            val_steps += 1
            
            # Free memory
            del inputs, labels, outputs, loss
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()

    avg_val_loss = total_val_loss / val_steps if val_steps > 0 else float('inf')
    return avg_val_loss

def save_loss_history(history, output_dir, filename="masked_pretrain_losses.csv"):
    df = pd.DataFrame(history)
    df.to_csv(os.path.join(output_dir, filename), index=False)

if __name__ == "__main__":
    train()