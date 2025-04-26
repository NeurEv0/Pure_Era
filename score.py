import json
import re
import os
import yaml
import time
import requests
import warnings
from bs4 import BeautifulSoup
from pathlib import Path
from typing import Dict, Any, List, Union, Optional
from concurrent.futures import ThreadPoolExecutor

# 禁用SSL证书验证警告
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

def find_value_in_dict(data: Any, target_key: str) -> Optional[Any]:
    """Recursively search for a key in a nested dictionary or list."""
    if isinstance(data, dict):
        if target_key in data:
            return data[target_key]
        for key, value in data.items():
            found = find_value_in_dict(value, target_key)
            if found is not None:
                return found
    elif isinstance(data, list):
        for item in data:
            found = find_value_in_dict(item, target_key)
            if found is not None:
                return found
    return None

def safe_get(data: Dict, key: str, default: Any = None) -> Any:
    """安全获取字典中的值，如果键不存在则返回默认值"""
    try:
        return data[key]
    except (KeyError, TypeError):
        return default

class APD3DataLoader:
    """加载本地APD3数据文件夹中的数据"""
    
    def __init__(self, apd3_folder: str = "APD3"):
        """
        初始化APD3数据加载器
        
        Args:
            apd3_folder: APD3数据文件夹路径
        """
        self.apd3_folder = Path(apd3_folder)
        self.sequence_to_apd_id = {}  # 序列到APD ID的映射
        self.apd_id_to_data = {}      # APD ID到数据的映射
        self._load_apd3_data()
    
    def _load_apd3_data(self):
        """加载APD3文件夹中的所有JSON文件数据"""
        if not self.apd3_folder.exists():
            print(f"警告: APD3文件夹 '{self.apd3_folder}' 不存在")
            return
            
        # 查找所有APD3 JSON文件
        apd3_files = list(self.apd3_folder.glob("modified_AP*_detail.json"))
        
        if not apd3_files:
            print(f"警告: 在 '{self.apd3_folder}' 中没有找到APD3数据文件")
            return
            
        print(f"正在加载 {len(apd3_files)} 个APD3数据文件...")
        
        # 逐个加载文件
        for file_path in apd3_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # 提取APD ID和序列
                apd_id = data.get("APD ID:", "")
                sequence = data.get("Sequence:", "")
                
                if apd_id and sequence:
                    # 标准化序列（移除空格和其他非字母字符）
                    sequence = re.sub(r'[^A-Za-z]', '', sequence).upper()
                    
                    # 添加到映射
                    self.sequence_to_apd_id[sequence] = apd_id
                    self.apd_id_to_data[apd_id] = data
                    
            except Exception as e:
                print(f"加载文件 {file_path} 时出错: {str(e)}")
        
        print(f"成功加载了 {len(self.apd_id_to_data)} 个APD3数据条目")
    
    def get_data_by_sequence(self, sequence: str) -> Dict[str, Any]:
        """
        通过序列获取APD3数据
        
        Args:
            sequence: 肽序列
            
        Returns:
            对应的APD3数据，如果找不到则返回空字典
        """
        # 标准化序列
        sequence = re.sub(r'[^A-Za-z]', '', sequence).upper()
        
        # 查找APD ID
        apd_id = self.sequence_to_apd_id.get(sequence)
        if not apd_id:
            return {}
            
        # 返回数据
        return self.apd_id_to_data.get(apd_id, {})
    
    def parse_apd3_json_data(self, sequence: str) -> Dict[str, Any]:
        """
        解析APD3 JSON数据格式为统一的数据结构
        
        Args:
            sequence: 肽序列
            
        Returns:
            解析后的数据结构，与在线解析结果兼容
        """
        # 获取原始数据
        raw_data = self.get_data_by_sequence(sequence)
        if not raw_data:
            return {}
            
        # 创建结果字典
        data = {
            "sequence": sequence,
            "length": len(sequence),
            "hydrophobic_ratio": None,
            "net_charge": None,
            "molecular_weight": None,
            "gravy_value": None,
            "disulfide_bonds": None,
            "detailed_info_fetched": True,
            "from_local_apd3": True,
            "apd_id": raw_data.get("APD ID:", ""),
            "detail_info": {}
        }
        
        # 提取基本信息
        detail_info = {
            "name_class": raw_data.get("Name/Class:", ""),
            "source": raw_data.get("Source:", ""),
            "sequence": raw_data.get("Sequence:", ""),
            "activity": raw_data.get("Activity:", ""),
            "crucial_residues": raw_data.get("Crucial residues:", ""),
            "additional_info": raw_data.get("Additional info:", ""),
            "reference": raw_data.get("Reference:", ""),
            "boman_index": raw_data.get("Boman Index:", "")
        }
        
        # 提取数值字段
        try:
            if "Length:" in raw_data:
                data["length"] = int(raw_data["Length:"])
                detail_info["length"] = int(raw_data["Length:"])
        except ValueError:
            pass
            
        try:
            if "Net charge:" in raw_data:
                data["net_charge"] = int(raw_data["Net charge:"])
                detail_info["net_charge"] = int(raw_data["Net charge:"])
        except ValueError:
            pass
            
        try:
            if "Hydrophobic residue%:" in raw_data:
                hydrophobic_text = raw_data["Hydrophobic residue%:"]
                if isinstance(hydrophobic_text, str) and "%" in hydrophobic_text:
                    value = hydrophobic_text.replace("%", "").strip()
                    data["hydrophobic_ratio"] = float(value)
                    detail_info["hydrophobic_ratio"] = float(value)
        except ValueError:
            pass
            
        try:
            if "Boman Index:" in raw_data:
                data["boman_index"] = float(raw_data["Boman Index:"])
                detail_info["boman_index"] = float(raw_data["Boman Index:"])
        except ValueError:
            pass
        
        # 计算二硫键数量
        cys_count = sequence.upper().count("C")
        if cys_count >= 2:
            data["disulfide_bonds"] = cys_count // 2
            detail_info["disulfide_bonds"] = cys_count // 2
        
        # 检查是否是双链肽
        name_class = detail_info["name_class"].lower()
        activity_info = detail_info["activity"].lower() + " " + detail_info["additional_info"].lower()
        
        is_two_chain = ("two-chain" in name_class or 
                        "two chain" in name_class or 
                        "two-chain" in activity_info or
                        "two chain" in activity_info or
                        "alpha chain" in activity_info or
                        "beta chain" in activity_info)
        
        detail_info["is_two_chain"] = is_two_chain
        
        # 检查是否有协同作用
        has_synergy = ("synerg" in activity_info or 
                       "work together" in activity_info or
                       "work with" in activity_info)
        
        detail_info["has_synergy"] = has_synergy
        
        # 提取MIC值
        mic_pattern = re.compile(r"MIC\s*(\d+(\.\d+)?)\s*[-–]\s*(\d+(\.\d+)?)\s*([µn]g/ml|[µn]M)", re.IGNORECASE)
        mic_pattern2 = re.compile(r"MIC\s*[><≥≤~≈]?\s*(\d+(\.\d+)?)\s*([µn]g/ml|[µn]M)", re.IGNORECASE)
        
        mic_values = []
        
        # 匹配范围MIC (如 "MIC 10-25 ug/ml")
        for match in mic_pattern.finditer(activity_info):
            try:
                min_val = float(match.group(1))
                max_val = float(match.group(3))
                unit = match.group(5).strip()
                # 使用平均值
                avg_val = (min_val + max_val) / 2
                mic_values.append({"value": avg_val, "unit": unit})
            except (ValueError, IndexError):
                pass
        
        # 匹配单值MIC (如 "MIC >100 ug/ml")
        for match in mic_pattern2.finditer(activity_info):
            try:
                value = float(match.group(1))
                unit = match.group(3).strip()
                mic_values.append({"value": value, "unit": unit})
            except (ValueError, IndexError):
                pass
        
        if mic_values:
            detail_info["mic_values"] = mic_values
        
        # 提取pH稳定性
        ph_pattern = re.compile(r"pH\s+(\d+(\.\d+)?)\s*(-|to|\s+)\s*(\d+(\.\d+)?)", re.IGNORECASE)
        ph_match = ph_pattern.search(activity_info)
        if ph_match:
            detail_info["ph_stability"] = {
                "min": float(ph_match.group(1)),
                "max": float(ph_match.group(4))
            }
        
        # 提取温度稳定性
        temp_pattern = re.compile(r"(\d+)(-|to|\s+)(\d+)(\s*°C|\s*degrees)", re.IGNORECASE)
        temp_match = temp_pattern.search(activity_info)
        if temp_match:
            detail_info["temp_stability"] = {
                "min": int(temp_match.group(1)),
                "max": int(temp_match.group(3))
            }
        
        # 添加详细信息到结果
        data["detail_info"] = detail_info
        
        return data

class APD3Predictor:
    """APD3数据加载器，只从本地数据文件中获取APD3数据"""
    
    def __init__(self, cache_file: str = "apd3_cache.json", apd3_folder: str = "APD3"):
        self.cache_file = Path(cache_file)
        self.cache = self._load_cache()
        
        # 初始化本地APD3数据加载器
        self.local_data_loader = APD3DataLoader(apd3_folder)
        
    def _load_cache(self) -> Dict[str, Dict]:
        """加载缓存文件，如果不存在则创建空缓存"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载APD3缓存时出错: {str(e)}")
        return {}
    
    def _save_cache(self):
        """保存当前缓存到文件"""
        try:
            # 创建缓存的深拷贝以避免遍历时修改
            cache_copy = json.dumps(self.cache, indent=2, ensure_ascii=False)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                f.write(cache_copy)
        except Exception as e:
            print(f"保存APD3缓存时出错: {str(e)}")
    
    def predict(self, sequence: str, force_refresh: bool = False) -> Dict[str, Any]:
        """从本地数据加载APD3信息"""
        if not sequence:
            return {"error": "序列为空"}
            
        # 验证序列是否有效
        if not self._is_valid_peptide(sequence):
            return {"error": f"无效的肽序列: {sequence}"}
            
        # 检查缓存
        if not force_refresh and sequence in self.cache:
            print(f"使用缓存数据: {sequence}")
            return self.cache[sequence]
            
        # 尝试从本地APD3数据加载
        local_data = self.local_data_loader.parse_apd3_json_data(sequence)
        if local_data and local_data.get("apd_id"):
            print(f"从本地APD3数据加载: {sequence} -> {local_data.get('apd_id')}")
            # 添加到缓存
            self.cache[sequence] = local_data
            self._save_cache()
            return local_data
        
        # 如果本地没有数据，返回基本信息
        print(f"本地APD3数据中没有找到序列 {sequence} 的信息")
        # 计算基本数据
        result = self._calculate_basic_properties(sequence)
        
        # 添加到缓存
        self.cache[sequence] = result
        self._save_cache()
        
        return result
    
    def _is_valid_peptide(self, sequence: str) -> bool:
        """检查是否是有效的肽序列（只包含标准氨基酸字母）"""
        valid_aa = set("ACDEFGHIKLMNPQRSTVWY")
        return all(aa.upper() in valid_aa for aa in sequence)
    
    def _calculate_basic_properties(self, sequence: str) -> Dict[str, Any]:
        """计算肽序列的基本特性"""
        # 标准氨基酸分子量表（Da）
        aa_weights = {
            'A': 71.08, 'C': 103.14, 'D': 115.09, 'E': 129.12, 'F': 147.18,
            'G': 57.05, 'H': 137.14, 'I': 113.16, 'K': 128.17, 'L': 113.16,
            'M': 131.19, 'N': 114.10, 'P': 97.12, 'Q': 128.13, 'R': 156.19,
            'S': 87.08, 'T': 101.11, 'V': 99.13, 'W': 186.21, 'Y': 163.18
        }
        
        # 氨基酸净电荷（pH 7.0）
        aa_charges = {
            'K': 1, 'R': 1, 'H': 0.1,  # 正电荷
            'D': -1, 'E': -1,           # 负电荷
            'A': 0, 'C': 0, 'F': 0, 'G': 0, 'I': 0, 'L': 0, 'M': 0, 
            'N': 0, 'P': 0, 'Q': 0, 'S': 0, 'T': 0, 'V': 0, 'W': 0, 'Y': 0
        }
        
        # 疏水性氨基酸
        hydrophobic_aa = set("AVILMFYW")
        
        # 计算分子量
        mw = sum(aa_weights.get(aa.upper(), 0) for aa in sequence) + 18.02  # 加上水分子重量
        
        # 计算净电荷
        net_charge = sum(aa_charges.get(aa.upper(), 0) for aa in sequence)
        
        # 计算疏水残基比例
        hydrophobic_count = sum(1 for aa in sequence if aa.upper() in hydrophobic_aa)
        hydrophobic_ratio = (hydrophobic_count / len(sequence)) * 100 if len(sequence) > 0 else 0
        
        # 计算GRAVY值（疏水性指数）- 简化版
        gravy_values = {
            'A': 1.8, 'C': 2.5, 'D': -3.5, 'E': -3.5, 'F': 2.8,
            'G': -0.4, 'H': -3.2, 'I': 4.5, 'K': -3.9, 'L': 3.8,
            'M': 1.9, 'N': -3.5, 'P': -1.6, 'Q': -3.5, 'R': -4.5,
            'S': -0.8, 'T': -0.7, 'V': 4.2, 'W': -0.9, 'Y': -1.3
        }
        gravy = sum(gravy_values.get(aa.upper(), 0) for aa in sequence) / len(sequence) if len(sequence) > 0 else 0
        
        # 计算Boman指数（蛋白质结合势）
        boman_values = {
            'A': -0.5, 'C': -1.0, 'D': 3.0, 'E': 3.0, 'F': -2.5,
            'G': 0.0, 'H': -0.5, 'I': -1.8, 'K': 3.0, 'L': -1.8,
            'M': -1.3, 'N': 0.2, 'P': 0.0, 'Q': 0.2, 'R': 3.0,
            'S': 0.3, 'T': -0.4, 'V': -1.5, 'W': -3.4, 'Y': -2.3
        }
        boman_index = sum(boman_values.get(aa.upper(), 0) for aa in sequence) / len(sequence) if len(sequence) > 0 else 0
        
        # 计算二硫键数量
        cys_count = sequence.upper().count("C")
        disulfide_bonds = cys_count // 2
        
        # 构建结果，确保包含所有必要字段以避免None值比较错误
        result = {
            "sequence": sequence,
            "length": len(sequence),
            "hydrophobic_ratio": hydrophobic_ratio,
            "net_charge": net_charge,
            "molecular_weight": mw,
            "gravy_value": gravy,
            "disulfide_bonds": disulfide_bonds,
            "detailed_info_fetched": False,  # 没有从APD3在线服务获取详细信息
            "from_local_apd3": True,
            "apd_id": "",
            "detail_info": {
                # 基本信息
                "name_class": "",
                "source": "",
                "sequence": sequence,
                "length": len(sequence),
                "net_charge": net_charge,
                "hydrophobic_ratio": hydrophobic_ratio,
                "boman_index": boman_index,
                
                # 活性信息
                "activity": "",
                "crucial_residues": "",
                "additional_info": "",
                
                # 结构信息
                "structure_3d": "",
                "molecular_form": "",
                "is_two_chain": False,
                
                # 稳定性
                "ph_stability": {"min": 7.0, "max": 7.0},
                "temp_stability": {"min": 25, "max": 25},
                
                # 空值但在评分中可能用到的字段
                "has_synergy": False,
                "mic_values": [],
                "sar": "",
                "reference": ""
            }
        }
        
        return result

class AntimicrobialPeptideScorer:
    def __init__(self, config_file: str = None, use_apd3: bool = True, 
                 use_local_apd3: bool = True, apd3_folder: str = "APD3"):
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
        
        # APD3数据加载器初始化
        self.use_apd3 = use_apd3
        self.use_local_apd3 = True  # 强制只使用本地APD3数据
        
        if use_apd3:
            self.apd3_predictor = APD3Predictor(apd3_folder=apd3_folder)
            print(f"已启用APD3功能 (仅使用本地数据: {apd3_folder})")
        
        # 本地APD3数据加载器
        self.local_data_loader = APD3DataLoader(apd3_folder)
        self.apd3_folder = apd3_folder

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

        # 使用 find_value_in_dict 查找序列
        sequence = find_value_in_dict(raw_data, "Sequence") or ""
        dramp_id = find_value_in_dict(raw_data, "DRAMP ID") or ""
        target_organism_str = find_value_in_dict(raw_data, "Target Organism") or ""
        net_charge_str = str(find_value_in_dict(raw_data, "Net Charge") or "0").strip("+").strip("-")
        hydrophobicity_str = str(find_value_in_dict(raw_data, "Hydrophobicity") or "0")
        half_life_str = find_value_in_dict(raw_data, "Half Life") or ""
        seq_len_str = str(find_value_in_dict(raw_data, "Sequence Length") or len(sequence) or "0") # Fallback to calculated length
        biophys_props = find_value_in_dict(raw_data, "Biophysicochemical properties") or ""

        # 数据预处理
        processed_data = {
            "DRAMP ID": dramp_id,
            "Sequence": sequence,
            "Target Organism": target_organism_str, # 保存原始Target Organism文本
            "Net Charge": float(net_charge_str or "0"),
            "Hydrophobicity": float(hydrophobicity_str or "0"),
            "pH Stability": "2-10" if isinstance(biophys_props, str) and
                            "resistant to heat and pH conditions from 2 to 10" in biophys_props
                            else "unknown",
            "Half Life": {"Mammalian": self._parse_half_life(half_life_str)},
            "Disulfide Bonds": self._parse_disulfide_bonds(sequence),
            "Sequence Length": int(seq_len_str or "0")
        }

        # 如果启用APD3，获取APD3预测数据并集成到processed_data
        if self.use_apd3 and sequence:
            apd3_data = self.apd3_predictor.predict(sequence)
            if "error" not in apd3_data:
                processed_data["APD3"] = apd3_data
                
                # 使用APD3数据更新我们的处理数据，注意：保留原database中的boman index和疏水残基比例
                if "net_charge" in apd3_data:
                    processed_data["Net Charge"] = apd3_data["net_charge"]
                if "disulfide_bonds" in apd3_data:
                    processed_data["Disulfide Bonds"] = apd3_data["disulfide_bonds"]
                
                # 保留原始数据中的Boman Index和Hydrophobicity
                # 不复制APD3中的hydrophobic_ratio到Hydrophobicity
            else:
                print(f"获取序列 {sequence} 的APD3预测数据失败: {apd3_data.get('error')}")
        
        # 调用评分逻辑
        scores = self._calculate_scores_with_apd3(processed_data, raw_data)
        
        # 保存target_organisms到结果中
        target_organisms = {}
        if "target_organisms" in scores:
            target_organisms = scores["target_organisms"]
            # 从scores中移除，因为它不是一个数值评分
            if "target_organisms" in scores:
                scores.pop("target_organisms")
        
        # 计算加权总分
        weighted_scores = self._apply_weights(scores)
        total = sum(weighted_scores.values())
        
        result = {
            "DRAMP ID": dramp_id,
            "Sequence": sequence,
            "scores": scores,
            "weighted_scores": weighted_scores,
            "total": total
        }
        
        # 添加APD3原始数据（可选）
        if self.use_apd3 and "APD3" in processed_data:
            result["APD3"] = processed_data["APD3"]
        
        # 添加目标生物结构化数据
        if target_organisms:
            result["target_organisms"] = target_organisms
        
        return result

    def _calculate_scores_with_apd3(self, data: Dict, raw_data: Dict) -> Dict[str, float]:
        """使用APD3数据进行评分计算"""
        scores = {}
        
        # 获取评分参数（如果在配置中定义了）
        params = self.weights.get("scoring_parameters", {})
        max_length = params.get("max_length", 30)
        min_hydrophobicity = params.get("min_hydrophobicity", 0.4)
        optimal_disulfide = params.get("optimal_disulfide", 4)
        gravy_optimal_range = params.get("gravy_optimal_range", [-0.2, 0.1])  # 从配置文件获取GRAVY的最佳区间
        
        # 检查是否有APD3数据
        has_apd3 = "APD3" in data
        has_detail = has_apd3 and "detail_info" in data["APD3"]
        
        # 1. 提取target organism信息而不是转换为分数
        # 存储原始数据，用于结果展示
        target_organism_raw = find_value_in_dict(raw_data, "Target Organism") or ""
        
        # 解析并格式化target organism信息
        if target_organism_raw:
            # 提取有序的靶标生物信息
            target_data = self._parse_target_organism_detailed(target_organism_raw)
            scores["target_organisms"] = target_data  # 存储为结构化数据
        else:
            scores["target_organisms"] = {}
        
        # 2. 抗菌效力评分 - MIC值拟合或GRAVY值优化评分
        # 检查是否有详情页中的MIC值
        if has_detail and "mic_values" in data["APD3"]["detail_info"] and data["APD3"]["detail_info"]["mic_values"]:
            # 如果有实际MIC值，优先使用
            mic_values = data["APD3"]["detail_info"]["mic_values"]
            # 取最小MIC值（最有效的）
            min_mic = min([item["value"] for item in mic_values])
            
            # 转换单位为μg/ml（如果单位是μM，需要进行分子量转换）
            if any(item["unit"].lower().strip() in ["μm", "nm", "um"] for item in mic_values):
                # 如果有分子量数据，可以进行更精确的转换
                if "molecular_weight" in data["APD3"] and data["APD3"]["molecular_weight"]:
                    mw = data["APD3"]["molecular_weight"] / 1000  # 转换为kDa
                    min_mic = min_mic * mw  # 转换为μg/ml
            
            # 基于MIC值的评分: 0.1-10μg/ml范围映射到10-0分
            # MIC值越小，抗菌活性越好，得分越高
            if min_mic <= 0.1:
                scores["mic"] = 10.0
            elif min_mic >= 10:
                scores["mic"] = 1.0
            else:
                # 对数比例转换，使得MIC=1μg/ml时评分约为5分
                scores["mic"] = max(1.0, 10.0 - 5.0 * (min_mic / 1.0))
                
        elif has_apd3 and "gravy_value" in data["APD3"] and data["APD3"]["gravy_value"] is not None:
            # 根据GRAVY值优化评分
            gravy = data["APD3"]["gravy_value"]
            
            # 安全检查optimal_gravy变量
            if gravy_optimal_range and len(gravy_optimal_range) >= 2:
                optimal_min = gravy_optimal_range[0]
                optimal_max = gravy_optimal_range[1]
                
                # 根据打分修改1.md中的GRAVY值评分优化
                if gravy < optimal_min:
                    penalty = 2 * (optimal_min - gravy)
                elif gravy > optimal_max:
                    penalty = 3 * (gravy - optimal_max)
                else:
                    penalty = 0
                    
                scores["mic"] = max(0, 10 - penalty)
            else:
                # 如果配置不正确，使用默认评分
                scores["mic"] = 6.0
        else:
            # 如果没有足够信息，默认给6分
            scores["mic"] = 6.0
        
        # 从详情页提取目标病原体的活性信息
        if has_detail and "activity" in data["APD3"]["detail_info"]:
            activity_text = data["APD3"]["detail_info"]["activity"]
            
            # 检查是否有针对革兰氏阳性菌的活性
            has_gram_positive = "gram+" in activity_text.lower() or "gram positive" in activity_text.lower()
            
            # 检查是否有针对革兰氏阴性菌的活性
            has_gram_negative = "gram-" in activity_text.lower() or "gram negative" in activity_text.lower()
            
            # 检查是否有广谱活性
            broad_spectrum = has_gram_positive and has_gram_negative
            
            # 额外活性分数，但不直接转换为target_potency分数
            if "has_synergy" in data["APD3"]["detail_info"] and data["APD3"]["detail_info"]["has_synergy"]:
                scores["synergy_bonus"] = 1.0  # 协同作用加1分
        
        # =================== 溶血活性评分修改 ====================
        # 判断是否为双链肽：通过 APD3 详情、名称或 Biological Activity 字段
        is_two_chain = False

        # 1. 从 APD3 详情判断
        if has_detail and "is_two_chain" in data["APD3"]["detail_info"]:
            is_two_chain = data["APD3"]["detail_info"]["is_two_chain"]
        
        # 2. 从肽名称判断
        # 使用 find_value_in_dict 查找 Peptide Name
        peptide_name = str(find_value_in_dict(raw_data, "Peptide Name") or "").lower()
        if any(term in peptide_name for term in ["two-chain", "two-peptide", "two chain", "two peptide"]):
            is_two_chain = True
        
        # 3. 从 Biological Activity 字段判断
        # 使用 find_value_in_dict 查找 Biological Activity
        biological_activity = find_value_in_dict(raw_data, "Biological Activity")
        if biological_activity is None:
            biological_activity = [] # Default to empty list if not found
        elif not isinstance(biological_activity, list):
            biological_activity = [str(biological_activity)] # Convert to list if not already

        biological_activity_text = " ".join(biological_activity).lower()

        if any(term in biological_activity_text for term in ["two-chain", "two-peptide", "two chain", "two peptide"]):
            is_two_chain = True
        
        # 获取序列和计算关键特征
        sequence = data.get("Sequence", "")
        if not sequence and "sequence" in data:
            sequence = data["sequence"]
        
        # 计算/获取疏水残基数量
        # 使用 find_value_in_dict 查找 Hydrophobic Residues
        hydrophobic_residues_val = find_value_in_dict(raw_data, "Hydrophobic Residues")
        try:
            hydrophobic_residues = int(hydrophobic_residues_val) if hydrophobic_residues_val is not None else 0
        except (ValueError, TypeError):
            hydrophobic_residues = 0

        sequence_length = len(sequence) if sequence else 0
        
        # 计算疏水比例
        hydrophobic_ratio = 0
        if sequence_length > 0:
            # 优先使用 DRAMP 的 Hydrophobic Residues 字段
            if hydrophobic_residues > 0:
                hydrophobic_ratio = (hydrophobic_residues / sequence_length) * 100
            # 其次使用 APD3 的 hydrophobic_ratio 字段
            elif has_apd3 and "hydrophobic_ratio" in data["APD3"] and data["APD3"]["hydrophobic_ratio"] is not None:
                hydrophobic_ratio = data["APD3"]["hydrophobic_ratio"]
        
        # 获取净电荷
        net_charge = 0
        if has_apd3 and "net_charge" in data["APD3"] and data["APD3"]["net_charge"] is not None:
            net_charge = data["APD3"]["net_charge"]
        else:
            # 使用 find_value_in_dict 查找 Net Charge
            net_charge_str = str(find_value_in_dict(raw_data, "Net Charge") or "0")
            try:
                # 处理 "+2" 或 "-1" 格式
                net_charge_str = net_charge_str.replace("+", "").strip()
                net_charge = int(net_charge_str)
            except (ValueError, AttributeError):
                net_charge = 0
        
        # 根据双链肽状态应用不同的评分规则
        if is_two_chain:
            # 双链肽 - 阈值评分
            if hydrophobic_ratio < 40:
                base_score = 10.0
            elif hydrophobic_ratio < 60:
                base_score = 7.0
            elif hydrophobic_ratio < 80:
                base_score = 4.0
            else:
                base_score = 1.0
        else:
            # 非双链肽 - 更严格的阈值评分
            if hydrophobic_ratio < 30:
                base_score = 10.0
            elif hydrophobic_ratio < 50:
                base_score = 7.0
            elif hydrophobic_ratio < 70:
                base_score = 4.0
            else:
                base_score = 1.0

        # 附加扣分项
        final_score = base_score

        # 1. 连续芳香族氨基酸扣分
        if sequence and re.search(r"[WFY]{3,}", sequence):
            final_score -= 2.0

        # 2. 高芳香族氨基酸比例扣分
        if sequence:
            aromatic_count = sequence.count('W') + sequence.count('F') + sequence.count('Y')
            aromatic_ratio = (aromatic_count / sequence_length) * 100 if sequence_length > 0 else 0
            if aromatic_ratio > 20:
                # 避免与连续芳香族重复扣分过多，如果已经因为连续扣分了，这里只扣1分，否则扣1分
                # (因为连续3个已经是高比例了)
                if not re.search(r"[WFY]{3,}", sequence):
                    final_score -= 1.0
            
        # 3. 长序列扣分
        if sequence_length > 30:
            final_score -= 1.0
            
        # 4. 零净电荷扣分
        if net_charge == 0:
            final_score -= 1.0
            
        # 限制最终分数在0-10之间
        scores["hemolysis"] = max(0, min(10, final_score))
        
        # 细胞毒性评分
        if has_apd3 and "net_charge" in data["APD3"] and data["APD3"]["net_charge"] is not None:
            # 根据净电荷评分（+2~+6最佳）
            net_charge = data["APD3"]["net_charge"]
            if 2 <= net_charge <= 6:
                scores["cytotoxicity"] = 10.0 - abs(4 - net_charge)  # 以+4为最佳点
            else:
                scores["cytotoxicity"] = max(0, 6.0 - abs(net_charge - 4))  # 偏离+4越远越低
        else:
            charge_val = data.get("Net Charge", 0)
            if isinstance(charge_val, (int, float)):
                scores["cytotoxicity"] = 8.0 if abs(charge_val) <= 2 else 4.0
            else:
                scores["cytotoxicity"] = 5.0  # 默认中等分数
        
        # 3. Boman指数评分
        if has_detail and "boman_index" in data["APD3"]["detail_info"] and data["APD3"]["detail_info"]["boman_index"] is not None:
            boman_index = data["APD3"]["detail_info"]["boman_index"]
            
            # 根据Boman指数打分指引的区间划分
            if -0.2 <= boman_index <= 0.2:
                # 两亲性平衡，理想药物候选
                scores["boman_score"] = 10.0
            elif 0.2 < boman_index <= 0.5:
                # 疏水为主，抗菌活性高但毒性风险高
                scores["boman_score"] = 7.0
            elif -0.5 <= boman_index < -0.2:
                # 亲水为主，膜插入能力弱
                scores["boman_score"] = 7.0
            elif boman_index > 0.5:
                # 极强疏水，易聚集/毒性高
                scores["boman_score"] = 3.0
            else:  # boman_index < -0.5
                # 极强亲水，几乎无膜相互作用
                scores["boman_score"] = 3.0
        else:
            # 获取Boman Index
            boman_str = str(find_value_in_dict(raw_data, "Boman Index") or "0")
            try:
                boman_val = float(boman_str)
                if -0.2 <= boman_val <= 0.2:
                    scores["boman_score"] = 10.0
                elif 0.2 < boman_val <= 0.5 or -0.5 <= boman_val < -0.2:
                    scores["boman_score"] = 7.0
                else:
                    scores["boman_score"] = 3.0
            except (ValueError, TypeError):
                scores["boman_score"] = 5.0  # 默认中等分数
        
        # 3. 稳定性评分
        # 蛋白酶抗性 - 检查K和R的存在（胰蛋白酶切位点）
        if sequence:
            scores["protease"] = 10.0 if 'K' not in sequence and 'R' not in sequence else 5.0
        else:
            scores["protease"] = 5.0
        
        # pH稳定性 - 检查详情页是否有pH稳定性数据
        if has_detail and "ph_stability" in data["APD3"]["detail_info"] and isinstance(data["APD3"]["detail_info"]["ph_stability"], dict):
            ph_range = data["APD3"]["detail_info"]["ph_stability"]
            if "min" in ph_range and "max" in ph_range and ph_range["min"] is not None and ph_range["max"] is not None:
                ph_width = ph_range["max"] - ph_range["min"]
                
                # pH范围越宽，稳定性越好
                if ph_width >= 7:
                    scores["ph_thermal"] = 10.0
                elif ph_width >= 4:
                    scores["ph_thermal"] = 8.0
                else:
                    scores["ph_thermal"] = 6.0
            else:
                scores["ph_thermal"] = 5.0
        else:
            # 从原始数据中查找pH Stability
            ph_stability = str(find_value_in_dict(raw_data, "pH Stability") or "unknown")
            scores["ph_thermal"] = 10.0 if ph_stability == "2-10" else 5.0
        
        # 半衰期评分
        if has_detail and "is_two_chain" in data["APD3"]["detail_info"] and data["APD3"]["detail_info"]["is_two_chain"]:
            # 双链肽通常半衰期更长
            scores["half_life"] = 7.0
        else:
            # 从原始数据获取半衰期
            half_life_data = data.get("Half Life", {})
            if isinstance(half_life_data, dict) and "Mammalian" in half_life_data and half_life_data["Mammalian"] is not None:
                scores["half_life"] = min(10, half_life_data["Mammalian"] / 3)
            else:
                # 解析半衰期字符串
                half_life_str = str(find_value_in_dict(raw_data, "Half Life") or "")
                match = re.search(r"Mammalian:(\d+(\.\d+)?)", half_life_str)
                if match:
                    try:
                        mammalian_hl = float(match.group(1))
                        scores["half_life"] = min(10, mammalian_hl / 3)
                    except (ValueError, TypeError):
                        scores["half_life"] = 5.0  # 默认值
                else:
                    scores["half_life"] = 5.0  # 默认值
        
        # 4. 合成可行性评分
        # 序列长度评分
        if has_detail and "is_two_chain" in data["APD3"]["detail_info"] and data["APD3"]["detail_info"]["is_two_chain"]:
            # 双链肽合成难度更高
            total_length = sequence_length
            if "second_chain_sequence" in data["APD3"]["detail_info"]:
                second_chain = data["APD3"]["detail_info"]["second_chain_sequence"]
                if second_chain:
                    total_length += len(second_chain)
            
            scores["length"] = 5.0 if total_length > max_length else 7.0
        else:
            # 使用 safe_get 或 find_value_in_dict 获取序列长度
            seq_length_val = data.get("Sequence Length") or sequence_length
            try:
                if isinstance(seq_length_val, str):
                    seq_length_val = int(seq_length_val)
                scores["length"] = 10.0 if seq_length_val <= max_length else 5.0
            except (ValueError, TypeError):
                scores["length"] = 7.0  # 默认中等难度
        
        # 稀有氨基酸评分
        if has_detail and "molecular_form" in data["APD3"]["detail_info"]:
            molecular_form = data["APD3"]["detail_info"].get("molecular_form", "")
            if not isinstance(molecular_form, str):
                molecular_form = ""
            
            # 检查是否有复杂修饰
            has_complex_modifications = "lantibiotic" in molecular_form.lower() or "thioether" in molecular_form.lower() or "modified" in molecular_form.lower()
            
            if has_complex_modifications:
                scores["rare_aa"] = 4.0  # 复杂修饰降低合成可行性
            else:
                nonterminal_mod = str(find_value_in_dict(raw_data, "Nonterminal Modifications and Unusual Amino Acids") or "").lower()
                scores["rare_aa"] = 10.0 if "unusual" not in nonterminal_mod else 2.0
        else:
            nonterminal_mod = str(find_value_in_dict(raw_data, "Nonterminal Modifications and Unusual Amino Acids") or "").lower()
            scores["rare_aa"] = 10.0 if "unusual" not in nonterminal_mod else 2.0
        
        # 二硫键复杂度
        if has_detail and "sar" in data["APD3"]["detail_info"]:
            # 检查SAR信息中关于二硫键的信息
            sar_text = data["APD3"]["detail_info"].get("sar", "")
            if not isinstance(sar_text, str):
                sar_text = ""
            
            # 如果SAR中提到二硫键不影响活性，那么合成难度降低
            if "disulfide" in sar_text.lower() and ("not essential" in sar_text.lower() or "not required" in sar_text.lower()):
                scores["disulfide"] = 8.0  # 二硫键不是必需的
            else:
                if has_apd3 and "disulfide_bonds" in data["APD3"] and data["APD3"]["disulfide_bonds"] is not None:
                    disulfide_bonds = data["APD3"]["disulfide_bonds"]
                else:
                    disulfide_bonds = data.get("Disulfide Bonds", 0)
                    if not isinstance(disulfide_bonds, (int, float)):
                        disulfide_bonds = 0
                        
                scores["disulfide"] = 6.0 if disulfide_bonds == optimal_disulfide else (10.0 if disulfide_bonds == 0 else 8.0)
        else:
            if has_apd3 and "disulfide_bonds" in data["APD3"] and data["APD3"]["disulfide_bonds"] is not None:
                disulfide_bonds = data["APD3"]["disulfide_bonds"]
            else:
                disulfide_bonds = data.get("Disulfide Bonds", 0)
                if not isinstance(disulfide_bonds, (int, float)):
                    disulfide_bonds = 0
                
            scores["disulfide"] = 6.0 if disulfide_bonds == optimal_disulfide else (10.0 if disulfide_bonds == 0 else 8.0)
        
        return scores
    
    def _apply_weights(self, scores: Dict[str, float]) -> Dict[str, float]:
        """应用权重到各项评分"""
        weighted = {}
        
        # 定义各类别包含的指标
        category_items = {
            "efficacy": ["mic", "synergy_bonus"],
            "toxicity": ["hemolysis", "cytotoxicity", "boman_score"],
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

    def _parse_target_organism_detailed(self, target_organism_text: str) -> Dict:
        """
        解析目标生物信息为结构化数据
        
        Args:
            target_organism_text: 包含靶标生物信息的文本
            
        Returns:
            Dict: 分类整理的靶标生物数据
        """
        if not target_organism_text:
            return {}
            
        # 处理无效数据情况
        invalid_patterns = [
            "No MICs found", 
            "Not found",
            "No information",
            "Not included",
            "None"
        ]
        
        if any(pattern.lower() in target_organism_text.lower() for pattern in invalid_patterns):
            return {"Note": [{"name": target_organism_text, "activity": ""}]}
            
        result = {}
        
        # 尝试提取参考文献标记
        ref_prefix = ""
        ref_match = re.match(r'\[Ref\.(\d+)\]\s*(.*)', target_organism_text)
        if ref_match:
            ref_id = ref_match.group(1)
            ref_prefix = f"[Ref.{ref_id}] "
            target_organism_text = ref_match.group(2)
        
        # 处理冒号分隔的类别格式: "Gram-positive bacteria:bacteria1, bacteria2..."
        main_parts = target_organism_text.split(':', 1)
        
        if len(main_parts) == 2:
            # 有明确类别标识符
            category = main_parts[0].strip()
            content = main_parts[1].strip()
            
            # 添加参考文献前缀到类别
            if ref_prefix and not category.startswith(ref_prefix):
                category = ref_prefix + category
                
            # 提取菌种列表
            bacteria_list = []
            
            # 按逗号分割各个菌种条目
            for bacteria_text in re.split(r',\s*', content):
                bacteria_text = bacteria_text.strip()
                if not bacteria_text:
                    continue
                
                if bacteria_text.lower().startswith("note:"):
                    # 处理注释信息
                    if "Note" not in result:
                        result["Note"] = []
                    result["Note"].append({"name": bacteria_text, "activity": ""})
                    continue
                
                # 提取菌名和活性
                self._extract_bacteria_info(bacteria_text, bacteria_list)
            
            # 按活性强度排序
            bacteria_list.sort(key=self._get_activity_score, reverse=True)
            
            if bacteria_list:
                result[category] = bacteria_list
        else:
            # 没有明确的类别分隔，尝试识别常见类别关键词
            # 常见类别及其关键词
            categories = {
                "Gram-positive bacteria": ["gram-positive", "gram+", "gram positive"],
                "Gram-negative bacteria": ["gram-negative", "gram-", "gram negative"],
                "Fungi": ["fungi", "fungus", "yeast"],
                "Virus": ["virus", "viral"],
                "Parasites": ["parasite", "parasitic"],
                "Cancer cells": ["cancer", "tumor", "tumour", "carcinoma"]
            }
            
            # 检查整个文本是否包含类别关键词
            category_found = False
            for category, keywords in categories.items():
                if any(keyword.lower() in target_organism_text.lower() for keyword in keywords):
                    # 将整个文本作为该类别的内容
                    bacteria_list = []
                    self._extract_bacteria_info(target_organism_text, bacteria_list)
                    
                    # 添加参考文献前缀
                    category_with_ref = category
                    if ref_prefix:
                        category_with_ref = ref_prefix + category
                        
                    result[category_with_ref] = bacteria_list
                    category_found = True
                    break
            
            # 如果没有找到类别，放入"Other"或使用参考文献前缀
            if not category_found:
                category = "Other"
                if ref_prefix:
                    category = ref_prefix + "Other"
                
                bacteria_list = []
                self._extract_bacteria_info(target_organism_text, bacteria_list)
                result[category] = bacteria_list
        
        # 处理注释信息
        note_match = re.search(r'Note:(.*?)(?:$|\.(?:\s|$))', target_organism_text, re.IGNORECASE)
        if note_match and "Note" not in result:
            note_text = note_match.group(1).strip()
            result["Note"] = [{"name": f"Note: {note_text}", "activity": ""}]
        
        return result
        
    def _extract_bacteria_info(self, text: str, target_list: List[Dict]):
        """
        从文本中提取菌种名称和活性信息
        
        Args:
            text: 包含菌种信息的文本
            target_list: 目标列表，用于添加提取的信息
        """
        # 清理文本
        text = text.strip()
        if not text:
            return
            
        # 处理注释
        if text.lower().startswith("note:"):
            return
            
        # 1. 匹配括号中的+号活性 (如 "(+++)")
        plus_match = re.search(r'(.*?)\s*(\(\++\))', text)
        if plus_match:
            name = plus_match.group(1).strip()
            activity = plus_match.group(2).strip()
            target_list.append({"name": name, "activity": activity})
            return
            
        # 2. 匹配MIC值 (如 "MIC = 8-16 μg/ml" 或 "(MIC = 8 μg/ml)")
        mic_match = re.search(r'(.*?)\s*\(?(?:MIC\s*=?\s*)([\d\.\-\s]+)(?:\s*[µμn]g\/ml|[µμn]M)\)?', text)
        if mic_match:
            name = mic_match.group(1).strip()
            mic_value = mic_match.group(2).strip()
            
            # 清理名称中的其他括号内容
            name = re.sub(r'\([^)]*\)', '', name).strip()
            
            target_list.append({
                "name": name, 
                "activity": f"MIC: {mic_value} μg/ml"
            })
            return
            
        # 3. 匹配抑制区 (如 "IZ=14 mm")
        iz_match = re.search(r'(.*?)\s*\(?(?:IZ\s*=?\s*)([\d\.]+)(?:\s*mm)\)?', text)
        if iz_match:
            name = iz_match.group(1).strip()
            iz_value = iz_match.group(2).strip()
            
            # 清理名称中的其他括号内容
            name = re.sub(r'\([^)]*\)', '', name).strip()
            
            target_list.append({
                "name": name, 
                "activity": f"IZ: {iz_value} mm"
            })
            return
            
        # 4. 匹配末尾括号内容作为活性 - 但要避免将菌株信息误认为活性
        general_match = re.search(r'(.*?)(\([^()]*\))$', text)
        if general_match:
            name = general_match.group(1).strip()
            activity = general_match.group(2).strip()
            
            # 过滤掉一些常见的菌株标记和非活性注释
            if re.search(r'(atcc|strain|sp\.|spp\.|isolate|\d{4,})', activity.lower()):
                # 这可能是菌株信息而非活性，将整个文本作为名称
                target_list.append({"name": text, "activity": ""})
            else:
                target_list.append({"name": name, "activity": activity})
            return
        
        # 5. 没有明确活性，整体作为名称
        target_list.append({"name": text, "activity": ""})
    
    def _get_activity_score(self, item: Dict) -> float:
        """
        计算活性强度得分，用于排序
        
        Args:
            item: 包含活性信息的字典
            
        Returns:
            活性强度得分
        """
        activity = item.get("activity", "")
        
        # 计算+号数量
        plus_count = activity.count("+")
        if plus_count > 0:
            return plus_count * 10  # 给+号活性一个较高的基础分
        
        # 提取MIC数值 (值越小越好)
        mic_match = re.search(r'MIC:\s*([\d\.]+)(?:-[\d\.]+)?', activity)
        if mic_match:
            try:
                # MIC值越小活性越强，所以用100减
                return 100 - float(mic_match.group(1))
            except ValueError:
                pass
        
        # 提取IZ数值 (值越大越好)
        iz_match = re.search(r'IZ:\s*([\d\.]+)', activity)
        if iz_match:
            try:
                return float(iz_match.group(1))
            except ValueError:
                pass
        
        return 0

# 评分单个肽序列
def score_single_peptide(sequence: str, config_file: str = None, use_apd3: bool = True, apd3_folder: str = "APD3") -> Dict[str, Any]:
    """
    对单个肽序列进行评分
    
    Args:
        sequence: 肽序列
        config_file: 配置文件路径
        use_apd3: 是否使用APD3数据
        apd3_folder: APD3数据文件夹路径
        
    Returns:
        评分结果字典
    """
    # 只使用本地APD3数据
    scorer = AntimicrobialPeptideScorer(config_file=config_file, use_apd3=use_apd3, use_local_apd3=True, apd3_folder=apd3_folder)
    
    # 构造基本数据
    raw_data = {
        "Sequence": sequence,
        "Sequence Length": str(len(sequence))
    }
    
    # 评分
    result = scorer.score_peptide(raw_data)
    return result

# ----------------- 批量处理函数 -----------------
def batch_score(input_dir: str, output_dir: str, config_file: str = None, max_workers: int = 4, 
               use_apd3: bool = True, apd3_folder: str = "APD3") -> List[Dict]:
    """
    批量处理input_dir中的所有dramp*.json文件，将结果保存到output_dir目录
    
    Args:
        input_dir: 输入目录，包含待处理的json文件
        output_dir: 输出目录，用于保存处理结果
        config_file: 可选，权重配置文件路径
        max_workers: 并行处理的最大工作线程数
        use_apd3: 是否使用APD3数据
        apd3_folder: APD3数据文件夹路径
    """
    # 创建输出目录（如果不存在）
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 初始化评分器 - 只使用本地APD3数据
    scorer = AntimicrobialPeptideScorer(config_file, use_apd3=use_apd3, 
                                        use_local_apd3=True, apd3_folder=apd3_folder)
    
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

# 命令行接口
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="抗菌肽评分系统 (使用本地APD3数据)")
    subparsers = parser.add_subparsers(dest="command", help="命令")
    
    # 单序列评分命令
    single_parser = subparsers.add_parser("score", help="评分单个肽序列")
    single_parser.add_argument("sequence", help="肽序列（单字母代码）")
    single_parser.add_argument("--config", help="配置文件路径", default="weights_config.yaml")
    single_parser.add_argument("--apd3-folder", help="APD3数据文件夹路径", default="APD3")
    
    # 批量评分命令
    batch_parser = subparsers.add_parser("batch", help="批量处理JSON文件")
    batch_parser.add_argument("--input", help="输入目录", default="database")
    batch_parser.add_argument("--output", help="输出目录", default="result")
    batch_parser.add_argument("--config", help="配置文件路径", default="weights_config.yaml")
    batch_parser.add_argument("--workers", help="并行工作线程数", type=int, default=4)
    batch_parser.add_argument("--no-apd3", help="禁用APD3数据", action="store_true")
    batch_parser.add_argument("--apd3-folder", help="APD3数据文件夹路径", default="APD3")
    
    # 创建配置文件模板命令
    config_parser = subparsers.add_parser("create-config", help="创建权重配置文件模板")
    config_parser.add_argument("--output", help="输出配置文件路径", default="weights_config.yaml")
    
    # 解析参数
    args = parser.parse_args()
    
    if args.command == "score":
        # 单序列评分
        result = score_single_peptide(args.sequence, args.config, True, args.apd3_folder)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "batch":
        # 批量处理
        results = batch_score(
            args.input, args.output, 
            config_file=args.config,
            max_workers=args.workers,
            use_apd3=not args.no_apd3,
            apd3_folder=args.apd3_folder
        )
        
        # 合并结果
        merge_results(args.output, os.path.join(args.output, "all_scores.json"))
    
    elif args.command == "create-config":
        # 创建配置文件模板
        config_template = {
            "efficacy": 0.4,
            "toxicity": 0.25,
            "stability": 0.2,
            "synthesis": 0.15,
            "sub_weights": {
                "efficacy": {
                    "mic": 0.9,
                    "synergy_bonus": 0.1
                },
                "toxicity": {
                    "hemolysis": 0.4,
                    "cytotoxicity": 0.3,
                    "boman_score": 0.3
                },
                "stability": {
                    "protease": 0.3,
                    "ph_thermal": 0.4,
                    "half_life": 0.3
                },
                "synthesis": {
                    "length": 0.3,
                    "rare_aa": 0.3,
                    "disulfide": 0.4
                }
            },
            "scoring_parameters": {
                "max_length": 30,
                "min_hydrophobicity": 0.4,
                "optimal_disulfide": 4,
                "gravy_optimal_range": [-0.2, 0.1]  # 最佳GRAVY值范围
            }
        }
        
        with open(args.output, 'w', encoding='utf-8') as f:
            yaml.dump(config_template, f, allow_unicode=True, default_flow_style=False)
            
        print(f"已创建配置文件模板: {args.output}")
    
    else:
        # 如果没有提供命令，执行默认批处理
        print("使用默认参数执行批量处理...")
        batch_score("database", "result", config_file="weights_config.yaml", max_workers=4)
        merge_results("result", "result/all_scores.json") 