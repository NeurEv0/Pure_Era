# Training
## Overview
- During the whole training process, we use AdamW as the optimizer and initialize the epoch as 100. 
- We use the Early Stopping to stop the training when the validation loss doesn't decrease for 5 epochs to avoid overfitting. 
- We use gradient clipping to increase the stability of training.
```python
torch.nn.utils.clip_grad_norm_(model.parameters(), config.max_grad_norm)
```
- We save the model parameters with the best validation loss.
```
Training file structure:
- amp4multitask(download from huggingface)\
    - config.json
    - model.safetensors
    - modeling_amp.py
    - normalization_parameters.py
    - pytorch_model.bin
    - README.md
    - tokenizer_config.json
    - vocab.txt
- merged_data.json
- merged_dataloader.py
- pretrain.py
- Trainer.py
```

## Pretrain
run `pretrain.py` to pretrain the model
We use mask training as the pretrain task for AMP4multitask.
- learning rate: 5e-5
- We sample a few tokens in each sequence for MLM training.
- 80% of the time, we replace masked input tokens with tokenizer.mask_token ([MASK])
- The rest of the time (10% of the time) we keep the masked input tokens unchanged
```python
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
```
- The loss function is CrossEntropy Loss.
```python
loss_fn = nn.CrossEntropyLoss(ignore_index=-100)
```

## MultiTask Training
run `Trainer.py` to perform multi-task training
- We frozen the first 5 layers of the encoder in this training stage.
```python
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
```
- learning rate: 2e-5
- During task switching, we initialize the model to the best model of the previous task.
```python
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
```
- Training order: 
  1. amp_classification
  2. bioactivity_classification
  3. half_life_regression
  4. hemolysis_regression
  5. mic_regression 

| task                       | loss function | best validation loss | epoch(early stop at) |
| -------------------------- | ------------- | -------------------- | -------------------- |
| amp_classification         |  nn.CrossEntropyLoss()         |         0.1079             |           6           |
| bioactivity_classification |      nn.BCEWithLogitsLoss()         |        0.2076            |           11           |
| half_life_regression       |      nn.MSELoss()         |        0.0118            |         16             |
| hemolysis_regression                       |      nn.MSELoss()         |            0.3841        |       30               |
| mic_regression             |      nn.HuberLoss(delta=1.0)         |         0.0863           |       30               |
