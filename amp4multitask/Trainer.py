import os
import json
import numpy as np
from tqdm import tqdm
import gc
import pandas as pd
from collections import defaultdict

import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.nn.utils import clip_grad_norm_
from transformers import EsmTokenizer

from amp4multitask.modeling_amp import AMPConfig, AMPForMultiTask
from merged_dataloader import build_dataloader

class EarlyStopping:
    def __init__(self, patience=5, delta=0, output_dir=None, checkpoint_path='best_pretrain_model.pth'):
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
            print(f"Validation loss improved to {val_loss:.4f}. Model saved to {self.checkpoint_path}!")

class ampTrainer:
    def __init__(self, model_root, data_file, save_dir="training_outputs"):
        self.model_root = model_root
        self.data_file = data_file
        self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


        self.task_config = {
            "masked_lm":{
                "num_organisms": None
            },
            "amp_classification":{
                "num_organisms": None
            },
            "bioactivity_classification":{
                "num_organisms": None
            },
            "half_life_regression":{
                "num_organisms": None
            },
            "hemolysis_regression":{
                "num_organisms": None
            },
            "mic_regression":{
                "num_organisms": 11
            }
        }
        self.task_order = list(self.task_config.keys())[1:]     # task order starts with task 1: amp_classification
        print(f"Task order: {self.task_order}")

        self.model = self.load_modelFromPretrain()
        self.tokenizer = EsmTokenizer.from_pretrained(
        self.model_root,
        padding_side="left"
        )

        self.batch_size = 64
        self.optimizer = AdamW(
            self.model.parameters(),
            lr=2e-5
        )
    def load_modelFromPretrain(self):
        amp_config = AMPConfig.from_pretrained("amp4multitask")
        model = AMPForMultiTask(amp_config)
        model = model.to(self.device)
        
        checkpoint_path = os.path.join(self.save_dir, "best_pretrain_model.pth")
        if os.path.exists(checkpoint_path):
            checkpoint = torch.load(checkpoint_path, map_location=self.device, weights_only=True)
            
            # load model state dict with the same keys
            model_state_dict = model.state_dict()
            
            filtered_state_dict = {}
            for k, v in checkpoint.items():
                if k in model_state_dict:
                    if v.shape == model_state_dict[k].shape:
                        filtered_state_dict[k] = v
                    else:
                        print(f"[Warning] Skipping {k} due to shape mismatch: "
                            f"Pretrained {v.shape} vs Current {model_state_dict[k].shape}")
                else:
                    print(f"[Warning] Skipping unmatched key: {k}")
            
            model.load_state_dict(filtered_state_dict, strict=False)
            print(f"[Info] Loaded {len(filtered_state_dict)}/{len(checkpoint)} parameters from {checkpoint_path}")
        else:
            raise FileNotFoundError(f"[Error] No pretrained model found at {checkpoint_path}")
        return model

    def freeze_encoder_layers(self, num_frozen_layers: int=5):
        """freeze some certain layers of the encoder"""
        assert num_frozen_layers <= len(self.model.amp.layers) and num_frozen_layers > 0, "Invalid number of frozen layers"
    
        # freeze the word embeddings
        for param in self.model.amp.word_embeddings.parameters():
            param.requires_grad = False
    
        # freeze the layer norm layer
        for param in self.model.amp.emb_layer_norm.parameters():
            param.requires_grad = False
    
        # freeze some layers of the encoder
        for i, layer in enumerate(self.model.amp.layers):
            if i < num_frozen_layers:
                for param in layer.parameters():
                    param.requires_grad = False

    def train_task(self, task_name, epochs = 100):
        """Train a single task"""
        print(f"\n{'='*50}")
        print(f"Starting training for task: {task_name}")
        print(f"{'='*50}\n")
        self.model.set_train_mode(task_name)
        self.freeze_encoder_layers(4)

        train_loader, val_loader, _ = build_dataloader(self.data_file, task_name, self.batch_size)

        early_stopping = EarlyStopping(output_dir=self.save_dir, checkpoint_path=f"best_{task_name}_model.pth")
        train_history = {
        'epoch': [],
        'train_loss': [],
        'val_loss': []
        }

        for epoch in range(epochs):
            self.model.train()
            total_loss = 0.0
            train_steps = 0
        
            progress_bar = tqdm(train_loader, desc=f"Epoch {epoch+1}/{epochs}")
            for batch in progress_bar:
                loss = self._compute_loss(task_name, batch)

                self.optimizer.zero_grad()
                loss.backward()
                clip_grad_norm_(self.model.parameters(), 1.0)
                self.optimizer.step()

                total_loss += loss.item()
                train_steps += 1
                avg_train_loss = total_loss / train_steps
                progress_bar.set_postfix({'loss': round(avg_train_loss, 4)})
 
                del loss, avg_train_loss
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

            val_loss = self.validate(val_loader, task_name)
            avg_train_loss = total_loss / len(train_loader)
            print(f"Epoch {epoch+1}/{epochs} | Train Loss: {avg_train_loss:.4f} | Val Loss: {val_loss:.4f}")
            train_history["epoch"].append(epoch+1)
            train_history["train_loss"].append(avg_train_loss)
            train_history["val_loss"].append(val_loss)

            early_stopping(val_loss, self.model)
            if early_stopping.early_stop:
                print(f"Early stopping triggered at epoch {epoch+1}")
                break
        
        # after training, loaded the best model
        best_checkpoint_path = os.path.join(self.save_dir, f"best_{task_name}_model.pth")
        if os.path.exists(best_checkpoint_path):
            self.model.load_state_dict(torch.load(best_checkpoint_path, map_location=self.device, weights_only=True))
            print(f"[Info] Loaded best model for {task_name} from {best_checkpoint_path}")
        else:
            raise FileNotFoundError(f"[Error] No best model found for {task_name}")

        # Save final loss history
        self.save_loss_history(train_history, task_name)
        print("Training completed!")

        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def save_loss_history(self, history, task_name):
            filename = os.path.join(self.save_dir, f"{task_name}_losses.csv")
            df = pd.DataFrame(history)
            df.to_csv(filename, index=False)
            print(f"Loss history saved to {filename}")

    def _compute_loss(self, task_name, batch):
        sequences = batch['Sequence']
        encoding = self.tokenizer(
        sequences,
        padding='max_length',
        max_length=128,
        truncation=True,
        return_tensors='pt'
        )
        inputs = encoding['input_ids'].to(self.device)
        attention_mask = encoding['attention_mask'].to(self.device)
        organism_ids = None
        labels = batch['label'].to(self.device)

        if task_name == "mic_regression":
            organism_ids = batch['organism'].to(self.device)

        outputs = self.model(
            input_ids=inputs, 
            attention_mask=attention_mask, 
            task_name=task_name,
            organism_ids=organism_ids,
            return_dict=True
            )
        outputs = outputs.logits
        
        if task_name == "amp_classification":
            loss_fn = nn.CrossEntropyLoss()
            loss = loss_fn(outputs, labels.long())
        elif task_name == "bioactivity_classification":
            loss_fn = nn.BCEWithLogitsLoss()
            loss = loss_fn(outputs, labels.float())
        elif task_name == "mic_regression":
            loss_fn = nn.HuberLoss(delta=1.0)
            loss = loss_fn(outputs.squeeze(), labels.float())
        else:
            loss_fn = nn.MSELoss()
            loss = loss_fn(outputs.squeeze(), labels.float())
        return loss

    def validate(self, data_loader, task_name):
        self.model.eval()
        total_loss = 0
        batch_count = 0
        
        with torch.no_grad():
            for batch in data_loader:
                loss = self._compute_loss(task_name, batch)
                total_loss += loss.item()
                batch_count += 1
                del batch, loss
        return total_loss / batch_count if batch_count > 0 else float('inf')
    
    def train_all_tasks(self, epochs_per_task=100, start_from=None):
        if start_from:
            start_idx = self.task_order.index(start_from)
            tasks_to_train = self.task_order[start_idx:]
        else:
            tasks_to_train = self.task_order

        for i, task in enumerate(tasks_to_train):
            print(f"\n=== Starting Task {i+1}/{len(tasks_to_train)}: {task} ===")
            if i > 0:
                prev_task = self.task_order[i-1]
                checkpoint_path = os.path.join(self.save_dir, f"best_{prev_task}_model.pth")
                checkpoint = torch.load(checkpoint_path, map_location=self.device, weights_only=True)
                self.model.load_state_dict(checkpoint)

            self.train_task(task, epochs=epochs_per_task)
            print(f"Completed training for {task}\n")

            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()

if __name__ == '__main__':
    trainer = ampTrainer(
        model_root="amp4multitask",
        data_file="merged_data.json",
        save_dir="training_outputs"
    )
    
    trainer.train_all_tasks()
