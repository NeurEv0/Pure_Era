"""
transformers==4.52.4
You must download normalization_parameters.csv to denormalize the output of the model.
unit: 
- μg/ml for MIC
- min for half life
- score for hemolysis
"""
from transformers import AutoModel, AutoTokenizer
import torch
import pandas as pd
import numpy as np

organism2id = {
            'Acinetobacter baumannii': 0, 'Bacillus subtilis': 1, 'Candida albicans': 2, 
            'Enterococcus faecalis': 3, 'Escherichia coli': 4, 'Klebsiella pneumoniae': 5,
            'Micrococcus luteus': 6, 'Pseudomonas aeruginosa': 7, 'Salmonella enterica': 8,
            'Staphylococcus aureus': 9, 'Staphylococcus epidermidis': 10
            }
id2organism = {v: k for k, v in organism2id.items()}

# demonstration for task mic_regression
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = AutoModel.from_pretrained(
    "amp4multitask",
    task_name="mic_regression",     # choose the task ["amp_classification", "hemolysis_regression", "mic_regression", "half_life_regression"]
    trust_remote_code=True      # required for loading the model
)
model.eval()
model = model.to(device)
tokenizer = AutoTokenizer.from_pretrained("muskwff/amp4multitask_124M")

sample_seq = "KGGK"

encoding = tokenizer(
sample_seq,
padding='max_length',
max_length=128,
truncation=True,
return_tensors='pt'
)
input_ids = encoding['input_ids'].to(device)
attention_mask = encoding['attention_mask'].to(device)

with torch.no_grad():
    output = model(
        input_ids=input_ids,
        attention_mask=attention_mask,
        task_name="mic_regression",
        organism_ids=torch.tensor([4], dtype=torch.long, device=device)    # Escherichia coli
        # organism_ids=None for the rest tasks
    )

norm_params_path = "normalization_parameters.csv"       # change this to your path
norm_params = pd.read_csv(norm_params_path)
def denormalize(task_name, normalized_value, organism_id=None):
    """
    Denormalize the value for regression tasks
    """
    if isinstance(organism_id, torch.Tensor):
        organism_id = organism_id.cpu().item()

    if task_name == "mic_regression":
        org_name = norm_params.iloc[organism_id]['organism']
        params = norm_params[
            (norm_params['parameter_type'] == 'mic_regression') &
            (norm_params['organism'] == org_name)
        ]
        mean = params['mean'].values[0]
        std = params['std'].values[0]
        log_val = normalized_value * std + mean
        return 10 ** (-log_val)  # 10^(-log10(value)) = value
    elif task_name == "half_life_regression":
        params = norm_params[norm_params['parameter_type'] == 'half_life_regression']
        mean = params['mean'].values[0]
        std = params['std'].values[0]
        log_val = normalized_value * std + mean
        return 10 ** (-log_val)    
    elif task_name == "hemolysis_regression":
        params = norm_params[norm_params['parameter_type'] == 'hemolysis_regression']
        mean = params['mean'].values[0]
        std = params['std'].values[0]
        log_val = normalized_value * std + mean
        return np.expm1(log_val)  # e^(log_val) - 1

    return normalized_value  # the rest of tasks are not normalized

logits = output[0]
mic_value = denormalize("mic_regression", logits.item(), 4)     # μg/ml
print(round(mic_value, 4))

"""
model = model = AutoModel.from_pretrained(
    "muskwff/amp4multitask_124M",
    task_name="mic_regression",
    trust_remote_code=True
)

...

probs = torch.softmax(logits, dim=-1)
true_prob = probs[0][1].item()      # the probability of the positive class
print(round(true_prob, 4))
"""