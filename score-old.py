import json
import re
import os
import yaml
from typing import Dict, Any, List, Union
from concurrent.futures import ThreadPoolExecutor

def safe_get(data: Dict, key: str, default: Any = None) -> Any:
    """安全获取字典中的值，如果键不存在则返回默认值"""
    try:
        return data[key]
    except (KeyError, TypeError):
        return default

class AntimicrobialPeptideScorer:
    def __init__(self, config_file: str = None):
        # 默认权重配置
        default_weights = {
            "efficacy": 0.4,
            "toxicity": 0.25,
            "stability": 0.2,
            "synthesis": 0.15,
            "sub_weights": {
                # 子权重可以在这里定义
            }
        }
        
        # 如果提供了配置文件，则从配置文件加载权重
        self.weights = default_weights
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    if config and isinstance(config, dict):
                        self.weights.update(config)
                print(f"已从 {config_file} 加载权重配置")
            except Exception as e:
                print(f"加载配置文件时出错: {str(e)}，将使用默认配置")

    # ----------------- 数据预处理函数 -----------------
    def _parse_target_potency(self, target_organism: str) -> int:
        """提取目标病原体的最高'+'数量"""
        if not target_organism:
            return 0
            
        matches = re.findall(r"\(\++\)", target_organism)
        if not matches:
            return 0
        max_plus = max(len(match.strip("()")) for match in matches)
        return min(10, max_plus * 2)  # 每个+得2分，上限10分

    def _parse_half_life(self, half_life: str) -> float:
        """提取哺乳动物半衰期（小时）"""
        if not half_life:
            return 0.0
            
        match = re.search(r"Mammalian:(\d+(\.\d+)?)", half_life)
        return float(match.group(1)) if match else 0.0

    def _parse_disulfide_bonds(self, sequence: str) -> int:
        """通过序列计算半胱氨酸（C）数量"""
        if not sequence:
            return 0
        return sequence.count("C")

    # ----------------- 核心评分函数（适配字段） -----------------
    def score_peptide(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """根据原始肽数据计算评分"""
        if not raw_data:
            return {"DRAMP ID": "", "scores": {}, "total": 0}
            
        # 数据预处理
        processed_data = {
            "DRAMP ID": safe_get(raw_data, "DRAMP ID", ""),
            "Sequence": safe_get(raw_data, "Sequence", ""),
            "Target Organism": self._parse_target_potency(safe_get(raw_data, "Target Organism", "")),
            "Net Charge": float(safe_get(raw_data, "Net Charge", "0").strip("+").strip("-") or "0"),
            "Hydrophobicity": float(safe_get(raw_data, "Hydrophobicity", "0")),
            "pH Stability": "2-10" if "Biophysicochemical properties" in raw_data and 
                            safe_get(raw_data, "Biophysicochemical properties", "") and 
                            "resistant to heat and pH conditions from 2 to 10" in raw_data["Biophysicochemical properties"] 
                            else "unknown",
            "Half Life": {"Mammalian": self._parse_half_life(safe_get(raw_data, "Half Life", ""))},
            "Disulfide Bonds": self._parse_disulfide_bonds(safe_get(raw_data, "Sequence", "")),
            "Sequence Length": int(safe_get(raw_data, "Sequence Length", "0") or "0")
        }
        
        # 调用评分逻辑
        scores = self._calculate_scores(processed_data, raw_data)
        
        # 计算加权总分
        weighted_scores = self._apply_weights(scores)
        total = sum(weighted_scores.values())
        
        return {
            "DRAMP ID": safe_get(raw_data, "DRAMP ID", ""),
            "scores": scores,
            "weighted_scores": weighted_scores,
            "total": total
        }

    def _calculate_scores(self, data: Dict, raw_data: Dict) -> Dict[str, float]:
        """实际评分逻辑"""
        scores = {}
        
        # 获取评分参数（如果在配置中定义了）
        params = self.weights.get("scoring_parameters", {})
        max_length = params.get("max_length", 30)
        min_hydrophobicity = params.get("min_hydrophobicity", 0.4)
        optimal_disulfide = params.get("optimal_disulfide", 4)
        
        # 1. 抗菌效力
        scores["target_potency"] = data["Target Organism"]
        scores["mic"] = 8.0 if data["Disulfide Bonds"] >= optimal_disulfide and data["Hydrophobicity"] > min_hydrophobicity else 6.0
        
        # 2. 毒性
        scores["hemolysis"] = 10.0 if not re.search(r"[WFY]{3,}", data["Sequence"]) else 2.0
        scores["cytotoxicity"] = 8.0 if abs(data["Net Charge"]) <= 2 else 4.0
        
        # 3. 稳定性
        scores["protease"] = 10.0 if 'K' not in data["Sequence"] and 'R' not in data["Sequence"] else 5.0
        scores["ph_thermal"] = 10.0 if data["pH Stability"] == "2-10" else 5.0
        scores["half_life"] = min(10, data["Half Life"]["Mammalian"] / 3)
        
        # 4. 合成可行性
        scores["length"] = 10.0 if data["Sequence Length"] <= max_length else 5.0
        
        # 检查字段是否存在
        nonterminal_mod = safe_get(raw_data, "Nonterminal Modifications and Unusual Amino Acids", "").lower()
        scores["rare_aa"] = 10.0 if "unusual" not in nonterminal_mod else 2.0
        
        scores["disulfide"] = 6.0 if data["Disulfide Bonds"] == optimal_disulfide else (10.0 if data["Disulfide Bonds"] == 0 else 8.0)
        
        return scores
    
    def _apply_weights(self, scores: Dict[str, float]) -> Dict[str, float]:
        """应用权重到各项评分"""
        weighted = {}
        
        # 定义各类别包含的指标
        category_items = {
            "efficacy": ["target_potency", "mic"],
            "toxicity": ["hemolysis", "cytotoxicity"],
            "stability": ["protease", "ph_thermal", "half_life"],
            "synthesis": ["length", "rare_aa", "disulfide"]
        }
        
        # 获取子权重配置（如果存在）
        sub_weights = self.weights.get("sub_weights", {})
        
        # 计算每个类别的加权得分
        for category, items in category_items.items():
            # 获取该类别的主权重
            main_weight = self.weights.get(category, 0.25)  # 默认均分
            
            # 获取该类别的子权重
            item_weights = sub_weights.get(category, {})
            
            # 计算类别得分
            if item_weights:
                # 使用配置的子权重
                category_score = 0
                for item in items:
                    if item in scores:
                        item_weight = item_weights.get(item, 1.0 / len(items))
                        category_score += scores[item] * item_weight
            else:
                # 子权重未配置，使用平均权重
                category_items_present = [item for item in items if item in scores]
                if category_items_present:
                    category_score = sum(scores.get(item, 0) for item in category_items_present) / len(category_items_present)
                else:
                    category_score = 0
            
            # 应用主权重
            weighted[category] = category_score * main_weight
        
        return weighted

# ----------------- 批量处理函数 -----------------
def batch_score(input_dir: str, output_dir: str, config_file: str = None, max_workers: int = 4):
    """
    批量处理input_dir中的所有dramp*.json文件，将结果保存到output_dir目录
    
    Args:
        input_dir: 输入目录，包含待处理的json文件
        output_dir: 输出目录，用于保存处理结果
        config_file: 可选，权重配置文件路径
        max_workers: 并行处理的最大工作线程数
    """
    # 创建输出目录（如果不存在）
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 初始化评分器
    scorer = AntimicrobialPeptideScorer(config_file)
    
    # 获取输入目录中的所有json文件
    json_files = [f for f in os.listdir(input_dir) if f.lower().startswith('dramp') and f.lower().endswith('.json')]
    
    print(f"找到{len(json_files)}个DRAMP JSON文件，开始处理（使用{max_workers}个线程）...")
    
    # 定义处理单个文件的函数
    def process_file(json_file):
        input_path = os.path.join(input_dir, json_file)
        output_path = os.path.join(output_dir, f"scored_{json_file}")
        
        try:
            # 读取JSON文件
            with open(input_path, 'r', encoding='utf-8') as f:
                peptide_data = json.load(f)
            
            # 评分
            result = scorer.score_peptide(peptide_data)
            
            # 保存结果
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            print(f"已处理: {json_file} -> {output_path}")
            return json_file, result
        
        except Exception as e:
            print(f"处理文件 {json_file} 时出错: {str(e)}")
            return json_file, None
    
    # 使用线程池并行处理文件
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {executor.submit(process_file, file): file for file in json_files}
        for future in future_to_file:
            file, result = future.result()
            if result:
                results.append(result)
    
    print(f"批量处理完成。{len(results)}/{len(json_files)}个文件处理成功。结果已保存到 {output_dir} 目录。")
    
    return results

# 多个JSON文件合并函数
def merge_results(input_dir: str, output_file: str):
    """
    合并input_dir中的所有scored_*.json文件到一个大的JSON文件
    
    Args:
        input_dir: 包含已评分JSON文件的目录
        output_file: 合并后的输出文件路径
    """
    results = []
    
    # 获取所有已评分的JSON文件
    scored_files = [f for f in os.listdir(input_dir) if f.startswith('scored_') and f.endswith('.json')]
    
    for file in scored_files:
        try:
            with open(os.path.join(input_dir, file), 'r', encoding='utf-8') as f:
                data = json.load(f)
                results.append(data)
        except Exception as e:
            print(f"读取文件 {file} 时出错: {str(e)}")
    
    # 按总分排序（可选）
    results.sort(key=lambda x: x.get('total', 0), reverse=True)
    
    # 保存合并后的结果
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"已合并 {len(results)} 个结果到文件: {output_file}")

if __name__ == "__main__":
    # 处理database目录中的所有dramp*.json文件，结果保存到result目录
    batch_score("database", "result", config_file="weights_config.yaml", max_workers=8)
    
    # 合并所有评分结果到一个文件
    merge_results("result", "result/all_scores.json")