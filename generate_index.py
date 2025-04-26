import os
import json
import sys
from typing import Any, Optional

# --- 辅助函数 ---
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

# --- 配置 ---
DATABASE_DIR = 'database'  # 相对于脚本位置的数据库目录名
OUTPUT_FILE = 'peptide_index.json'  # 输出的索引文件名
# ---

def create_peptide_index():
    """遍历数据库目录，提取信息并生成索引文件。"""
    # script_dir = os.path.dirname(os.path.abspath(__file__)) # 不再需要
    # db_path = os.path.join(script_dir, DATABASE_DIR) # 使用相对路径
    # output_path = os.path.join(script_dir, OUTPUT_FILE) # 使用相对路径
    db_path = DATABASE_DIR # 直接使用相对路径
    output_path = OUTPUT_FILE # 直接使用相对路径

    if not os.path.isdir(db_path):
        print(f"错误：数据库目录 '{db_path}' 未找到。", file=sys.stderr)
        return

    peptide_index = []
    print(f"开始扫描目录: {db_path}")
    processed_files = 0
    skipped_files = 0

    for filename in os.listdir(db_path):
        if filename.lower().endswith('.json'):
            file_path = os.path.join(db_path, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 提取关键字段，使用 find_value_in_dict 增加健壮性
                dramp_id = find_value_in_dict(data, 'DRAMP ID')
                name = find_value_in_dict(data, 'Peptide Name') or 'N/A' # Default to N/A if not found
                sequence = find_value_in_dict(data, 'Sequence')

                if dramp_id is None:
                    print(f"警告：文件 '{filename}' 缺少 'DRAMP ID'，已跳过。", file=sys.stderr)
                    skipped_files += 1
                    continue
                
                # 确保 name 是字符串
                if not isinstance(name, str):
                    name = str(name)

                # 确保 sequence 是字符串
                if not isinstance(sequence, str):
                    print(f"警告：文件 '{filename}' 的 'Sequence' 不是字符串，将尝试转换或置空。", file=sys.stderr)
                    try:
                        sequence = str(sequence) if sequence is not None else ''
                    except:
                        sequence = '' # Conversion failed

                length = len(sequence)

                entry = {
                    'id': dramp_id,
                    'name': name,
                    'sequence': sequence,
                    'length': length
                }
                peptide_index.append(entry)
                processed_files += 1
                if processed_files % 100 == 0: # 每处理100个文件打印一次进度
                     print(f"已处理 {processed_files} 个文件..." )


            except FileNotFoundError:
                print(f"错误：文件未找到 '{file_path}'（理论上不应发生）。", file=sys.stderr)
                skipped_files += 1
            except json.JSONDecodeError:
                print(f"错误：解析 JSON 文件失败 '{file_path}'。文件可能已损坏。", file=sys.stderr)
                skipped_files += 1
            except Exception as e:
                print(f"处理文件 '{file_path}' 时发生未知错误: {e}", file=sys.stderr)
                skipped_files += 1
        else:
            # print(f"跳过非 JSON 文件: {filename}")
            pass

    print(f"扫描完成。共处理 {processed_files} 个 JSON 文件，跳过 {skipped_files} 个文件。")

    if not peptide_index:
        print("未找到任何有效的肽数据，索引文件未生成。")
        return

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(peptide_index, f, indent=4, ensure_ascii=False) # 使用 indent=4 美化输出, ensure_ascii=False 支持中文
        print(f"成功！索引文件已生成: {output_path}")
    except IOError as e:
        print(f"错误：写入索引文件 '{output_path}' 失败: {e}", file=sys.stderr)
    except Exception as e:
        print(f"写入索引文件时发生未知错误: {e}", file=sys.stderr)


if __name__ == "__main__":
    create_peptide_index() 