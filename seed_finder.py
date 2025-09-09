# seed_finder.py (V2 - Aggressive Explorer)
"""
独立脚本，用于生成、测试和筛选在性能维度上表现“极致”的精英种子方案。
此版本采用激进探索策略，旨在找到设计空间边界上的“临界种子”，
包括最优可行解、最差可行解以及“有价值的”不可行解。
"""
import os
import json
import logging
import random
import copy
import re
from pathlib import Path
from tqdm import tqdm
import yaml
import numpy as np # 需要numpy

# --- 导入你项目中的SACS工具模块 ---
try:
    from problem.sacs.sacs_file_modifier import SacsFileModifier
    from problem.sacs.sacs_runner import SacsRunner
    from problem.sacs.sacs_interface_uc import get_sacs_uc_summary
    from problem.sacs.sacs_interface_weight_improved import calculate_sacs_weight_from_db
    # 从你的evaluator.py中导入核心资源
    from problem.sacs.evaluator import SEED_BASELINE, W_SECTIONS_LIBRARY
except ImportError as e:
    print(f"错误: 无法导入项目模块。请确保此脚本的运行位置正确。错误信息: {e}")
    exit(1)

# --- 设置日志 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler(), logging.FileHandler("seed_finder.log", mode='w')])
logger = logging.getLogger("SeedFinderV2")

def load_config(config_path=None):
    """
    从主配置文件加载SACS相关配置。
    [V3 修复]：此版本根据您的项目结构，精确定位到 "problem/sacs/config.yaml"，解决路径错误。
    """
    try:
        # 脚本所在的目录就是项目根目录 (MOLLM-MAIN)
        script_dir = Path(__file__).resolve().parent 
        
        # --- [核心修复] 直接构建正确的相对路径 ---
        # 从项目根目录构建到SACS配置文件的正确路径
        config_path = script_dir / "problem" / "sacs" / "config.yaml"
        
        if not config_path.exists():
            logger.critical(f"配置文件未找到，请确认路径是否正确: {config_path}")
            # 根据您的项目结构给出明确的提示
            logger.critical(f"  - 脚本期望的结构是: [项目根目录]/problem/sacs/config.yaml")
            logger.critical(f"  - 脚本当前认为的项目根目录是: {script_dir}")
            exit(1)
        
        logger.info(f"正在从 '{config_path}' 加载配置文件...")
        with open(config_path, "r") as f:
            full_config = yaml.safe_load(f)
        
        # 检查加载的配置是否正确
        if 'sacs' not in full_config:
            logger.critical(f"错误！加载的配置文件 '{config_path}' 中缺少 'sacs' 部分。请检查文件内容。")
            exit(1)
        output_dir_path = script_dir / "problem" / "sacs" / "elite_seeds"
        script_config = {
            "PROJECT_PATH": full_config['sacs']['project_path'],
            "SACS_INSTALL_PATH": full_config['sacs']['install_path'],
            "OPTIMIZABLE_BLOCKS": full_config['sacs']['optimizable_blocks'],
            "NUM_CANDIDATES_TO_GENERATE": 500,
            "NUM_SEEDS_PER_CATEGORY": 2,       
            "MAX_ACCEPTABLE_UC": 3.0,
            "OUTPUT_DIR": str(output_dir_path)
        }
        logger.info(f"主配置文件 '{config_path}' 加载成功。")
        return script_config
    except Exception as e:
        logger.critical(f"加载或解析 '{config_path}' 时出错: {e}", exc_info=True)
        exit(1)

def _parse_and_modify_line_aggressive(line: str, block_name: str) -> str:
    """
    激进版修改函数，用于生成更大范围的设计。
    """
    try:
        keyword = block_name.split()[0]
        original_line_stripped = line.rstrip()

        # I-Beam Logic (更激进的步长)
        if keyword == "GRUP" and re.search(r'(W\d+X\d+)', line):
            match = re.search(r'(W\d+X\d+)', line)
            current_section = match.group(1)
            try:
                current_index = W_SECTIONS_LIBRARY.index(current_section)
            except ValueError: return original_line_stripped

            # 步长可以更大，覆盖更广的范围
            step = random.randint(2, 6) * random.choice([-1, 1]) 
            new_index = np.clip(current_index + step, 0, len(W_SECTIONS_LIBRARY) - 1)
            new_section = W_SECTIONS_LIBRARY[new_index]
            return original_line_stripped.replace(current_section, new_section, 1)

        # Tubular Member Logic (更宽的扰动范围)
        elif keyword == "GRUP":
            if 'CONE' in line: return original_line_stripped
            try:
                od_val, wt_val = float(line[18:24]), float(line[25:30])
            except (ValueError, IndexError): return original_line_stripped

            # --- 核心变更: 扰动范围大幅扩大 ---
            if random.choice([True, False]):
                od_val *= random.uniform(0.6, 1.4) # 从 (0.9, 1.1) 扩大
            else:
                wt_val *= random.uniform(0.6, 1.4) # 从 (0.9, 1.1) 扩大

            od_val = np.clip(od_val, 10.0, 99.999)
            wt_val = np.clip(wt_val, 0.5, 9.999)
            
            new_od_str = f"{od_val:6.3f}"
            new_wt_str = f"{wt_val:5.3f}"
            new_line = line[:18] + new_od_str + " " + new_wt_str + line[30:]
            return new_line.rstrip()

        # Plate Member Logic (类似地扩大范围)
        elif keyword == "PGRUP":
            thick_match = re.search(r"(\d+\.\d+)", line[10:])
            if not thick_match: return original_line_stripped
            thick_str = thick_match.group(1)
            
            # --- 核心变更: 扰动范围扩大 ---
            thick_val = float(thick_str) * random.uniform(0.5, 2.0)
            thick_val = np.clip(thick_val, 0.250, 2.000)
            
            num_decimals = len(thick_str.split('.')[1])
            new_thick_str = f"{thick_val:.{num_decimals}f}"
            return line.replace(thick_str, new_thick_str, 1)

    except Exception: return line.rstrip()
    return line.rstrip()

def generate_random_candidate_aggressive(base_candidate, optimizable_blocks):
    """
    通过激进的随机扰动生成一个新候选方案。
    """
    new_candidate = copy.deepcopy(base_candidate)
    # --- 核心变更: 每次修改更多构件 ---
    num_modifications = random.randint(len(optimizable_blocks)//3, len(optimizable_blocks))
    blocks_to_modify = random.sample(optimizable_blocks, num_modifications)
    
    for block_name in blocks_to_modify:
        block_key = block_name.replace(" ", "_").replace(".", "")
        if block_key in new_candidate["new_code_blocks"]:
            original_line = new_candidate["new_code_blocks"][block_key]
            modified_line = _parse_and_modify_line_aggressive(original_line, block_name)
            new_candidate["new_code_blocks"][block_key] = modified_line
            
    return new_candidate

def evaluate_candidate(runner, project_path):
    # ... (此函数保持不变) ...
    analysis_result = runner.run_analysis(timeout=300)
    if not analysis_result.get('success'):
        logger.warning(f"SACS分析失败: {analysis_result.get('error', '未知')[:150]}")
        return None
    try:
        weight_res = calculate_sacs_weight_from_db(str(project_path))
        uc_res = get_sacs_uc_summary(str(project_path))
        if not (weight_res.get('status') == 'success' and uc_res.get('status') == 'success'):
            return None
        return {'weight': weight_res['total_weight_tonnes'], **uc_res} # 合并字典
    except Exception as e:
        logger.error(f"在指标提取过程中发生异常: {e}", exc_info=True)
        return None

def main():
    logger.info("="*50 + "\n精英种子发现器启动 (V2 - 激进探索模式)\n" + "="*50)
    
    CONFIG = load_config()
    project_path = Path(CONFIG["PROJECT_PATH"])
    modifier = SacsFileModifier(str(project_path))
    runner = SacsRunner(str(project_path), CONFIG["SACS_INSTALL_PATH"])
    
    successful_results = []
    logger.info(f"将生成和测试 {CONFIG['NUM_CANDIDATES_TO_GENERATE']} 个候选方案...")
    for i in tqdm(range(CONFIG['NUM_CANDIDATES_TO_GENERATE']), desc="生成和评估候选方案"):
        # 使用激进的生成函数
        candidate_design = generate_random_candidate_aggressive(SEED_BASELINE, CONFIG["OPTIMIZABLE_BLOCKS"])
        
        if not modifier.replace_code_blocks(candidate_design["new_code_blocks"]): continue
            
        metrics = evaluate_candidate(runner, project_path)
        if metrics is None: continue

        if metrics.get('max_uc', 999) <= CONFIG["MAX_ACCEPTABLE_UC"]:
             logger.info(f"成功方案 {i+1}: Weight={metrics['weight']:.2f}, MaxUC={metrics.get('max_uc', -1):.3f}")
             successful_results.append({'id': i+1, 'design': candidate_design, 'metrics': metrics})

    if not successful_results:
        logger.critical("没有一个候选方案成功完成评估，无法挑选种子。请检查SACS配置或扩大搜索范围。")
        return

    logger.info("开始筛选精英种子...")
    selected_seeds = {}
    
    feasible_designs = [res for res in successful_results if res['metrics'].get('max_uc', 999) <= 1.0]
    infeasible_designs = [res for res in successful_results if res['metrics'].get('max_uc', 999) > 1.0]

    def add_seed(seed, reason):
        seed_key = json.dumps(seed['design'], sort_keys=True)
        if seed_key not in selected_seeds:
            selected_seeds[seed_key] = {'reason': reason, **seed}

    # A: 最优可行种子
    if feasible_designs:
        add_seed(sorted(feasible_designs, key=lambda x: x['metrics']['weight'])[0], 'best_feasible_lightweight')
        add_seed(sorted(feasible_designs, key=lambda x: x['metrics']['max_uc'])[0], 'best_feasible_safest')

    # B: 最差可行种子 (重但安全, 或UC接近1.0)
    if feasible_designs:
        # 最重但仍然安全的
        worst_heavy = sorted(feasible_designs, key=lambda x: x['metrics']['weight'], reverse=True)
        if worst_heavy: add_seed(worst_heavy[0], 'worst_feasible_heavy')
        # 最不安全但仍然可行的 (UC最接近1.0)
        worst_uc = sorted(feasible_designs, key=lambda x: x['metrics']['max_uc'], reverse=True)
        if worst_uc: add_seed(worst_uc[0], 'worst_feasible_risky')

    # C: 有价值的不可行种子 (UC刚好超过1.0)
    if infeasible_designs:
        # UC值最接近1.0但大于1.0的种子
        valuable_infeasible = sorted(infeasible_designs, key=lambda x: x['metrics']['max_uc'])
        if valuable_infeasible: add_seed(valuable_infeasible[0], 'valuable_infeasible_edge')
            
    # D: 基准方案
    modifier.replace_code_blocks(SEED_BASELINE["new_code_blocks"])
    baseline_metrics = evaluate_candidate(runner, project_path)
    if baseline_metrics:
        add_seed({'id': 'baseline', 'design': SEED_BASELINE, 'metrics': baseline_metrics}, 'baseline_original')
        
    output_dir = Path(CONFIG["OUTPUT_DIR"])
    output_dir.mkdir(exist_ok=True, parents=True)
    for f in output_dir.glob('*.json'): f.unlink()
    
    logger.info("="*50 + f"\n最终挑选出 {len(selected_seeds)} 个精英种子并保存:\n" + "="*50)
    # ... (保存文件的逻辑保持不变) ...
    sorted_final_seeds = sorted(selected_seeds.values(), key=lambda x: x['reason'])

    for seed_data in sorted_final_seeds:
        filename = f"seed_{seed_data['reason']}.json"
        filepath = output_dir / filename
        with open(filepath, 'w') as f:
            json.dump(seed_data['design'], f, indent=4)
        metrics = seed_data['metrics']
        log_msg = (
            f"  -> 已保存 '{filename}': "
            f"Weight={metrics.get('weight', -1):.2f}, "
            f"MaxUC={metrics.get('max_uc', -1):.3f}"
        )
        logger.info(log_msg)    

    logger.info("-" * 50)
    logger.info(f"所有精英种子已保存至 '{output_dir.resolve()}' 目录。")

if __name__ == "__main__":
    main()
