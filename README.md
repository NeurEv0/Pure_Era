# 抗菌肽评分系统（APD3集成版）

这是一个通过分析肽序列特征来评估抗菌肽潜力的评分系统，整合了APD3预测功能，可以提供更准确的评分结果。

## 功能特点

- 通过调用APD3网站预测功能获取肽序列的物化特性参数
- 支持单序列评分和批量JSON数据处理
- 按照科学文献中的规则计算MIC、溶血活性等关键指标
- 实现请求缓存，避免重复调用APD3服务
- 提供灵活的权重配置，可根据需要调整评分策略
- 多线程并行处理，加快批量数据的评分速度

## 安装依赖

```bash
pip install requests beautifulsoup4 pyyaml
```

## 使用方法

### 1. 评分单个肽序列

```bash
python score_with_apd3.py score KCKWWNISCDLGNNGHVCTLSHECVVSCN
```

### 2. 批量处理JSON文件

```bash
python score_with_apd3.py batch --input database --output result
```

### 3. 更多选项

```bash
# 使用自定义配置文件
python score_with_apd3.py batch --config my_weights.yaml

# 调整并行处理线程数
python score_with_apd3.py batch --workers 8

# 不使用APD3预测（回退到本地计算）
python score_with_apd3.py batch --no-apd3
```

## 评分规则说明

系统根据以下几个方面评估抗菌肽的性能：

1. **MIC值拟合（抗菌效力模块）**
   - 规则：GRAVY值（0.76）和疏水比例（48%）较高，提示强膜结合能力→推断MIC较低
   - 公式：MIC_score = 10 - (GRAVY * 2)

2. **溶血活性修正（毒性模块）**
   - 规则：APD定义的疏水比例>40%可能增加溶血风险，结合GRAVY>0.5→中等风险
   - 公式：HC50_score = 10 - (hydrophobic_ratio * 0.1)

3. **二硫键复杂度调整（合成可行性模块）**
   - 规则：奇数半胱氨酸（3C）可能导致未配对残基→合成难度增加
   - 评分：4分（若成对则进一步扣分）

## 配置文件

系统使用YAML格式的配置文件定义权重和评分参数。示例：

```yaml
# 主分类权重，总和应为1.0
efficacy: 0.4    # 抗菌效力
toxicity: 0.25   # 毒性
stability: 0.2   # 稳定性
synthesis: 0.15  # 合成可行性

# 其他参数
scoring_parameters:
  max_length: 30        # 最佳序列长度上限
  min_hydrophobicity: 0.4  # 最小疏水性阈值
  optimal_disulfide: 4  # 最佳二硫键数量
```

## 输出格式

```json
{
  "DRAMP ID": "DRAMP00001",
  "Sequence": "KCKWWNISCDLGNNGHVCTLSHECVVSCN",
  "scores": {
    "target_potency": 8,
    "mic": 7.48,
    "hemolysis": 5.5,
    "cytotoxicity": 4.0,
    "protease": 5.0,
    "ph_thermal": 10.0,
    "half_life": 10.0,
    "length": 10.0,
    "rare_aa": 10.0,
    "disulfide": 8.0
  },
  "weighted_scores": {
    "efficacy": 3.1,
    "toxicity": 1.2,
    "stability": 1.7,
    "synthesis": 1.4
  },
  "total": 7.4,
  "APD3": {
    "sequence": "KCKWWNISCDLGNNGHVCTLSHECVVSCN",
    "in_database": true,
    "apd_id": "AP01609",
    "hydrophobic_ratio": 45.0,
    "net_charge": 0.5,
    "gravy": -0.12758620689655,
    "molecular_weight": 3250.731,
    "cys_count": 5,
    "disulfide_bonds": 2,
    "ww_hydrophobicity": 1.68
  }
}
``` 