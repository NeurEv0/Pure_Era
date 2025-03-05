# Reproduce details

- **Reproduce project**: 
  - 🆕Paper title: Explainable deep learning and virtual evolution identifies antimicrobial peptides with activity against multidrug-resistant human pathogens
  - 🆕Paper link: https://www.nature.com/articles/s41564-024-01907-3
  - 🖥️github link: https://github.com/MicroResearchLab/AMP-potency-prediction-EvoGradient.git

## Reproducing
⭐️🤝**When we checked the github repository, we found that there was no training code for the deep learning model. So we looked for the training strategy in the paper and completed the writing of the training code. Due to the particularity of swanlab, there are many repeated parts in the reproduction code.**

### Classification Result
|  Models\index  | Train Loss | Train Accuracy | Test Loss | Test Accuracy |
| :-------: | :--------: | :------------: | :------: | :------: |
|    CNN    |   0.2330   |     99.2193      |     0.2572     |     95.0216     |
|   LSTM    |   **0.0032** |   **99.9015**      |     0.413     |     **95.5655**     |
| Attention |   0.1550    |     94.3736      |     0.2065     |     93.5655     |
|    Transformer     |      0.1616      |         93.6979       |     **0.1754**     |     93.4474     |
