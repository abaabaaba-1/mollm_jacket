# seed_finder.py
"""
独立脚本，用于生成、测试和筛选高质量的“种子”方案。

该脚本旨在解决主优化流程中候选方案生成失败率高的问题。它通过一个预处理步骤，
系统地搜寻并筛选出一批在关键性能维度上表现“极致”（最好和最差）的精英方案，
为后续的进化算法提供一个强大的、多样化的起点，从而最大化初始种群的多样性。

工作流程：
1. 基于一个基准SACS模型，通过随机扰动生成大量候选设计。
2. 对每个候选设计运行完整的SACS分析，并提取性能指标（重量、UC、疲劳）。
3. 收集所有成功完成分析的候选方案及其结果。
4. 从成功方案中，根据以下标准挑选出精英种子：
   - 重量最低和最高的方案
   - UC值最低和最高的方案（在合理范围内）
   - 疲劳寿命最长和最短的方案
   - 原始的基准方案（作为平衡点）
5. 将挑选出的精英种子保存为独立的JSON文件，以便主优化算法加载。
"""

import os
import json
import logging
import random
import copy
import numpy as np
from pathlib import Path

# --- 导入您项目中的SACS工具模块 ---
# 假设此脚本与您的 'problem' 目录在同一级别或已配置好PYTHONPATH
try:
    from problem.sacs.sacs_file_modifier import SacsFileModifier
    from problem.sacs.sacs_runner import SacsRunner
    from problem.sacs.sacs_interface_uc import get_sacs_uc_summary
    from problem.sacs.sacs_interface_weight import calculate_sacs_volume
    from problem.sacs.sacs_interface_ftg import get_sacs_fatigue_summary
    from problem.sacs.evaluator import BASELINE_CODE_BLOCKS, _parse_and_modify_line
except ImportError as e:
    print(f"错误：无法导入项目模块。请确保此脚本的运行位置正确，或已将项目路径添加到PYTHONPATH。错误信息: {e}")
    exit(1)


# --- 脚本配置 ---
CONFIG = {
    "PROJECT_PATH": "/mnt/d/wsl_sacs_exchange/demo06_project/Demo06",
    "SACS_INSTALL_PATH": "C:\\Program Files (x86)\\Bentley\\Engineering\\SACS CONNECT Edition V16 Update 1",
    "NUM_CANDIDATES_TO_GENERATE": 100,  # 要尝试生成的候选方案总数
    "NUM_EXTREME_BEST_SEEDS_TO_PICK": 2,      # 每个极端维度挑选前N个“最好”的
    "NUM_EXTREME_WORST_SEEDS_TO_PICK": 1,     # [新增] 每个极端维度挑选后N个“最差”的
    "MAX_ACCEPTABLE_UC": 2.0,                 # [修改] 放宽UC值的接受上限，以捕获更多样性的解
    "OUTPUT_DIR": "./elite_seeds",      # 保存精英种子的目录
    "OPTIMIZABLE_BLOCKS": [             # 从config.yaml复制过来的可优化构件列表
        "GRUP LG1", "GRUP LG2", "GRUP LG3", "GRUP LG4", "GRUP T01", 
        "GRUP T02", "GRUP T03", "PGRUP P01"
    ]
}

# --- 设置日志 ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler("seed_finder.log", mode='w')] # 'w' to overwrite log each run
)
logger = logging.getLogger("SeedFinder")


def generate_random_candidate(base_candidate, optimizable_blocks):
    """通过随机扰动基准方案来生成一个新的候选方案。"""
    new_candidate = copy.deepcopy(base_candidate)
    
    # 随机决定修改多少个构件，增加多样性 (1到3个)
    num_modifications = random.randint(1, 4)
    blocks_to_modify = random.sample(optimizable_blocks, min(num_modifications, len(optimizable_blocks)))
    
    for block_name in blocks_to_modify:
        block_key = block_name.replace(" ", "_")
        if block_key in new_candidate["new_code_blocks"]:
            original_line = new_candidate["new_code_blocks"][block_key]
            # 增加随机扰动的幅度，以产生更 극단적인 결과
            modified_line = _parse_and_modify_line(original_line, block_name, allow_large_changes=True) # 假设_parse_and_modify_line可以接受这个参数
            new_candidate["new_code_blocks"][block_key] = modified_line
            logger.debug(f"Generated modification for {block_key}")
            
    return new_candidate

def evaluate_candidate(modifier, runner, project_path):
    """运行SACS并提取单个候选方案的指标，返回结果字典或None"""
    analysis_result = runner.run_analysis(timeout=300)
    if not analysis_result.get('success'):
        logger.warning(f"SACS分析失败。原因: {analysis_result.get('error', '未知')[:200]}")
        return None

    try:
        weight_res = calculate_sacs_volume(str(project_path))
        uc_res = get_sacs_uc_summary(str(project_path))
        ftg_res = get_sacs_fatigue_summary(str(project_path))
        
        # 兼容新的UC提取器状态 'success_no_data'
        is_uc_valid = uc_res.get('status') in ['success', 'success_no_data']
        if not (weight_res.get('status') == 'success' and is_uc_valid and ftg_res.get('status') == 'success'):
            logger.warning(f"指标提取不完整，跳过。 Weight: {weight_res.get('status')}, UC: {uc_res.get('status')}, FTG: {ftg_res.get('status')}")
            return None

        return {
            'weight': weight_res['total_volume_m3'],
            'uc': uc_res.get('max_uc', 999.0),  # 如果无数据，给一个极大的惩罚值
            'fatigue': ftg_res.get('min_life_years', 0.0) # 如果无数据，给一个极小值
        }
    except Exception as e:
        logger.error(f"在指标提取过程中发生异常: {e}", exc_info=True)
        return None

def main():
    """主执行函数"""
    logger.info("=" * 50)
    logger.info("精英种子查找脚本已启动 (包含最好和最差样本策略)")
    logger.info("=" * 50)

    # --- 初始化工具 ---
    project_path = Path(CONFIG["PROJECT_PATH"])
    if not project_path.exists():
        logger.critical(f"项目路径不存在: {project_path}")
        return

    modifier = SacsFileModifier(str(project_path))
    runner = SacsRunner(str(project_path), CONFIG["SACS_INSTALL_PATH"])
    
    successful_results = []
    
    # --- 1. 生成和评估循环 ---
    logger.info(f"将生成和测试 {CONFIG['NUM_CANDIDATES_TO_GENERATE']} 个候选方案...")
    for i in range(CONFIG['NUM_CANDIDATES_TO_GENERATE']):
        logger.info(f"--- 处理候选方案 {i+1}/{CONFIG['NUM_CANDIDATES_TO_GENERATE']} ---")
        
        candidate_design = generate_random_candidate(BASELINE_CODE_BLOCKS, CONFIG["OPTIMIZABLE_BLOCKS"])
        
        if not modifier.replace_code_blocks(candidate_design["new_code_blocks"]):
            logger.error(f"候选方案 {i+1}: 文件修改失败，跳过。")
            continue

        metrics = evaluate_candidate(modifier, runner, project_path)
        if metrics is None:
            continue

        # 只有当UC在合理范围内时才认为是成功的方案
        if metrics['uc'] > CONFIG["MAX_ACCEPTABLE_UC"]:
             logger.warning(f"候选方案 {i+1}: 成功运行但UC值过高 ({metrics['uc']:.2f} > {CONFIG['MAX_ACCEPTABLE_UC']})，视为无效。")
             continue

        logger.info(f"候选方案 {i+1}: 成功！ Weight={metrics['weight']:.2f}, UC={metrics['uc']:.3f}, Fatigue={metrics['fatigue']:.1f}")
        successful_results.append({
            'id': i + 1,
            'design': candidate_design,
            'metrics': metrics
        })
    
    logger.info("-" * 50)
    logger.info(f"评估完成。总尝试次数: {CONFIG['NUM_CANDIDATES_TO_GENERATE']}, 成功方案数: {len(successful_results)}")
    logger.info("-" * 50)

    if not successful_results:
        logger.critical("没有一个候选方案成功完成评估，无法挑选种子。请检查SACS配置或模型。")
        return

    # --- 2. 筛选精英种子 (重构逻辑) ---
    logger.info("开始筛选精英种子 (最好和最差)...")
    
    selected_seeds = {} # 使用字典防止重复添加同一个方案

    def add_seed(seed, reason):
        """辅助函数，用于向selected_seeds字典添加种子，避免重复。"""
        # 使用设计方案的JSON字符串作为唯一键
        seed_key = json.dumps(seed['design'], sort_keys=True)
        if seed_key not in selected_seeds:
            selected_seeds[seed_key] = {'reason': reason, **seed}
            return True
        return False
    
    # 按不同维度排序
    sorted_by_weight = sorted(successful_results, key=lambda x: x['metrics']['weight'])
    sorted_by_uc = sorted(successful_results, key=lambda x: x['metrics']['uc'])
    sorted_by_fatigue = sorted(successful_results, key=lambda x: x['metrics']['fatigue'], reverse=True) # 寿命越长越好

    # 挑选极致种子
    num_best = CONFIG['NUM_EXTREME_BEST_SEEDS_TO_PICK']
    num_worst = CONFIG['NUM_EXTREME_WORST_SEEDS_TO_PICK']
    num_total = len(successful_results)

    for i in range(min(num_best, num_total)):
        add_seed(sorted_by_weight[i], f'min_weight_{i+1}')
        add_seed(sorted_by_uc[i], f'min_uc_{i+1}')
        add_seed(sorted_by_fatigue[i], f'max_fatigue_{i+1}')

    for i in range(min(num_worst, num_total)):
        add_seed(sorted_by_weight[-(i+1)], f'max_weight_{i+1}')
        add_seed(sorted_by_uc[-(i+1)], f'max_uc_{i+1}')
        add_seed(sorted_by_fatigue[-(i+1)], f'min_fatigue_{i+1}')
        
    # 添加基准方案作为平衡点
    logger.info("评估基准方案...")
    modifier.replace_code_blocks(BASELINE_CODE_BLOCKS["new_code_blocks"])
    baseline_metrics = evaluate_candidate(modifier, runner, project_path)
    if baseline_metrics:
        baseline_seed = {
            'id': 'baseline', 
            'design': BASELINE_CODE_BLOCKS, 
            'metrics': baseline_metrics
        }
        add_seed(baseline_seed, 'baseline_balanced')

    # --- 3. 输出结果 ---
    output_dir = Path(CONFIG["OUTPUT_DIR"])
    output_dir.mkdir(exist_ok=True)
    # 清空旧的种子文件
    for f in output_dir.glob('*.json'):
        f.unlink()
    
    logger.info("=" * 50)
    logger.info(f"最终挑选出 {len(selected_seeds)} 个精英种子方案:")
    
    # 为了让文件名更清晰，按挑选原因排序
    sorted_final_seeds = sorted(selected_seeds.values(), key=lambda x: x['reason'])

    for seed_data in sorted_final_seeds:
        reason = seed_data['reason']
        metrics = seed_data['metrics']
        
        filename = f"seed_{reason}.json"
        filepath = output_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(seed_data['design'], f, indent=4)
        
        logger.info(
            f"  -> 已保存 '{filename}' (ID: {seed_data['id']}) | "
            f"Weight={metrics['weight']:.2f}, UC={metrics['uc']:.3f}, Fatigue={metrics['fatigue']:.1f}"
        )
        
    logger.info("=" * 50)
    logger.info(f"所有精英种子已保存至 '{output_dir.resolve()}' 目录。")
    logger.info("您可以将这些JSON文件作为主优化算法的初始种群。")


if __name__ == "__main__":
    # 假设 _parse_and_modify_line 函数需要一个默认的 allow_large_changes 参数
    # 我们在这里用一个 patch 来模拟，或者您需要在原模块中添加它
    original_parse_func = _parse_and_modify_line
    def patched_parse_func(line, block_name, allow_large_changes=False):
        # 这里只是一个示例，您可能需要更复杂地修改原函数
        # 简单地忽略这个新参数，使用原函数的功能
        return original_parse_func(line, block_name)
    
    # 全局替换
    globals()['_parse_and_modify_line'] = patched_parse_func

    main()
