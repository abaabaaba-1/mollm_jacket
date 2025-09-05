import re
import copy
import numpy as np

# ==============================================================================
# --- 步骤 1: 将您的基准方案粘贴到这里 ---
# ==============================================================================
BASELINE_CODE_BLOCKS = {
    # 请确保这里是您完整的、正确的、未被修改过的基准方案
    "GRUP_LG1": "GRUP LG1         42.200 1.450 29.0011.6050.00 1    1.001.00     0.500N490.005.00",
    "GRUP_LG2": "GRUP LG2         42.200 1.450 29.0011.6050.00 1    1.001.00     0.500N490.006.15",
    "GRUP_LG3": "GRUP LG3         42.200 1.450 29.0011.6050.00 1    1.001.00     0.500N490.006.75",
    "GRUP_LG4": "GRUP LG4         42.200 1.450 29.0011.6050.00 1    1.001.00     0.500N490.00",
    "GRUP_T01": "GRUP T01         16.100 0.650 29.0111.2035.00 1    1.001.00     0.500N490.00",
    "GRUP_T02": "GRUP T02         20.100 0.780 29.0011.6035.00 1    1.001.00     0.500N490.00",
    "GRUP_T03": "GRUP T03         12.800 0.520 29.0111.6035.00 1    1.001.00     0.500N490.00",
    "PGRUP_P01": "PGRUP P01 0.3750I29.000 0.25036.000                                     490.0000"
}


# ==============================================================================
# --- 步骤 2: 修正后的修改函数，能正确处理 GRUP 和 PGRUP ---
# ==============================================================================
def modify_sacs_line(line: str, od_factor: float, wt_factor: float, thick_factor: float) -> str:
    """
    根据给定的系数修改 SACS GRUP 或 PGRUP 行，已修复格式问题。
    """
    try:
        if line.strip().startswith("GRUP"):
            # GRUP 卡格式 (严格按列)
            od_str = line[18:24]
            wt_str = line[25:30]
            
            original_od = float(od_str)
            original_wt = float(wt_str)
            
            # 应用系数并添加 clip 确保值在合理范围内，防止格式溢出
            new_od = np.clip(original_od * od_factor, 10.0, 60.0)
            new_wt = np.clip(original_wt * wt_factor, 0.25, 3.0)
            
            # 格式化回字符串，保持固定宽度和对齐
            new_od_str = f"{new_od:>6.3f}"
            new_wt_str = f"{new_wt:>5.3f}"
            
            # 使用切片重建行，确保其他部分不变
            new_line = line[:18] + new_od_str + line[24:25] + new_wt_str + line[30:]
            return new_line

        elif line.strip().startswith("PGRUP"):
            # PGRUP 卡格式: "PGRUP P01 0.3750I..."
            # 从第11列开始是数值部分
            value_part = line[11:]
            
            # 找到'I'作为分隔符
            if 'I' in value_part:
                thick_str, rest_of_line = value_part.split('I', 1)
                separator = 'I'
            else: # 备用方案，如果没有'I'
                thick_str = value_part[:6].strip()
                rest_of_line = value_part[6:]
                separator = ''
            
            original_thick = float(thick_str)
            new_thick = np.clip(original_thick * thick_factor, 0.2500, 0.7500)
            
            # 格式化回字符串 (6位，左对齐，4位小数)
            new_thick_str = f"{new_thick:<6.4f}"
            
            # 重建行
            return line[:11] + new_thick_str + separator + rest_of_line

    except Exception as e:
        print(f"解析行失败: '{line}'. 错误: {e}")
        return line

    return line
    
# ... (文件的其余部分可以保持不变) ...
# 如果你运行这个修正后的脚本，它现在应该可以正确地生成代码了。



def generate_seed_code(philosophy_name: str, code_blocks: dict) -> str:
    """生成一个种子方案的完整 Python 代码块"""
    var_name = f"{philosophy_name.upper()}_CODE_BLOCKS"
    output = f'# Design Philosophy: {philosophy_name}\n'
    output += f'{var_name} = {{\n'
    output += '    "new_code_blocks": {\n'
    for key, line in code_blocks.items():
        output += f'        "{key}": "{line}",\n'
    output += '    }\n}\n'
    return output

# ==============================================================================
# --- 步骤 3: 定义设计哲学并生成代码 ---
# ==============================================================================
if __name__ == "__main__":
    
    # 定义不同的设计哲学及其对应的修改系数 (od_factor, wt_factor, thick_factor)
    design_philosophies = {
        "Baseline":      (1.0, 1.0, 1.0),
        "Ultralight":    (0.85, 0.85, 0.9), # 显著减轻重量
        "Fortress":      (1.15, 1.20, 1.2), # 显著增强稳固性
        "Fatigue_First": (1.05, 1.15, 1.1), # 略微增加OD，显著增加WT以提升疲劳
    }

    generated_code_snippets = []
    
    print("="*30)
    print("--- 开始生成多样化种子方案 ---")
    print("="*30 + "\n")

    for name, factors in design_philosophies.items():
        od_f, wt_f, thick_f = factors
        new_blocks = {}
        for key, original_line in BASELINE_CODE_BLOCKS.items():
            modified_line = modify_sacs_line(original_line, od_f, wt_f, thick_f)
            new_blocks[key] = modified_line
        
        # 生成该方案的Python代码
        code_snippet = generate_seed_code(name, new_blocks)
        generated_code_snippets.append(code_snippet)
        print(f"✅ 已生成 '{name}' 方案。")

    print("\n" + "="*30)
    print("--- 代码生成完毕 ---")
    print("--- 请将以下所有内容复制并粘贴到您的 evaluator.py 文件顶部 ---")
    print("="*30 + "\n\n")

    # 打印所有生成的代码块
    for code in generated_code_snippets:
        print(code)
    
    # 打印最终的 INITIAL_SEEDS 列表
    seed_list_names = [f"{name.upper()}_CODE_BLOCKS" for name in design_philosophies.keys()]
    print("\n# 将所有种子方案汇集到一个列表中")
    print(f"INITIAL_SEEDS = [{', '.join(seed_list_names)}]")
