# test_uc_components.py
import logging
import numpy as np
import json
from pathlib import Path

# 从 problem.sacs 包中导入我们需要的模块
# 假设此脚本与 'problem' 目录在同一级别
from problem.sacs.sacs_runner import SacsRunner
from problem.sacs.sacs_interface_uc import get_detailed_uc_analysis

# --- 1. 配置 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("UC_Component_Tester")

# 使用与 config.yaml 中相同的项目路径
# 请确保此路径对于您运行脚本的环境是正确的
SACS_PROJECT_PATH = "/mnt/d/wsl_sacs_exchange/demo06_project/Demo06"

# --- 2. 主测试逻辑 ---
def analyze_uc_components():
    """
    运行SACS分析，提取所有UC分量，并对其进行统计分析以评估其作为优化目标的潜力。
    """
    logger.info("=" * 30)
    logger.info("🚀 开始UC分量分析测试 🚀")
    logger.info("=" * 30)

    # --- 步骤 1: 运行SACS分析以生成最新的结果 ---
    logger.info("步骤 1/3: 运行SACS分析以确保结果是新鲜的...")
    runner = SacsRunner(project_path=SACS_PROJECT_PATH)
    analysis_result = runner.run_analysis(timeout=300)

    if not analysis_result.get('success'):
        logger.error("SACS 分析失败，无法继续测试。请检查SACS运行环境和模型文件。")
        logger.error(f"失败原因: {analysis_result.get('error', '未知错误')}")
        return

    logger.info("SACS分析成功完成。")

    # --- 步骤 2: 提取详细的UC分析数据 ---
    logger.info("\n步骤 2/3: 提取详细的UC分析数据...")
    uc_data = get_detailed_uc_analysis(work_dir=SACS_PROJECT_PATH)

    if not uc_data or uc_data.get('status') != 'success':
        logger.error("无法提取UC数据，测试中止。")
        logger.error(f"返回的数据: {uc_data}")
        return

    member_uc_results = uc_data.get('member_uc', {})
    if not member_uc_results:
        logger.warning("UC数据中没有找到任何杆件结果。模型可能为空或有问题。")
        return
        
    num_members = len(member_uc_results)
    logger.info(f"成功提取了 {num_members} 个杆件的UC数据。")

    # --- 步骤 3: 对每个UC分量进行统计分析 ---
    logger.info("\n步骤 3/3: 分析每个UC分量的统计特性...")
    
    # 从第一个杆件的结果中获取所有可用的UC分量名称
    # 例如：['max_uc', 'axial_uc', 'yy_bending_uc', 'zz_bending_uc', 'total_shear_uc', 'von_mises_uc', 'local_buckling_uc']
    first_member_data = next(iter(member_uc_results.values()))
    uc_component_keys = list(first_member_data.keys())

    # 初始化一个字典来存储每个分量的所有值
    component_values = {key: [] for key in uc_component_keys}

    # 收集所有杆件的UC分量值
    for member_data in member_uc_results.values():
        for key in uc_component_keys:
            component_values[key].append(member_data.get(key, 0.0))
            
    # 计算并打印每个分量的统计数据
    logger.info("-" * 80)
    logger.info("                          UC分量统计分析结果")
    logger.info("-" * 80)
    logger.info(f"{'UC分量名称':<20} | {'最大值':>10} | {'平均值':>10} | {'标准差':>10} | {'非零数量 (%)':>18}")
    logger.info("-" * 80)

    component_stats = {}
    for key, values in component_values.items():
        arr = np.array(values)
        non_zero_count = np.count_nonzero(arr)
        non_zero_percentage = (non_zero_count / num_members) * 100 if num_members > 0 else 0
        
        stats = {
            'max': np.max(arr),
            'mean': np.mean(arr),
            'std': np.std(arr),
            'non_zero_count': non_zero_count,
            'non_zero_percentage': non_zero_percentage
        }
        component_stats[key] = stats

        logger.info(f"{key:<20} | {stats['max']:>10.4f} | {stats['mean']:>10.4f} | {stats['std']:>10.4f} | {f'{non_zero_count} ({non_zero_percentage:.1f}%)':>18}")
    
    logger.info("-" * 80)

    # --- 结论与建议 ---
    logger.info("\n结论与建议:")
    potential_objectives = []
    for key, stats in component_stats.items():
        if key == 'max_uc': # max_uc 通常是所有分量的最大值，我们关注的是其组成部分
            continue
        # 一个好的指标：最大值不为0，且有相当数量的杆件其值不为0
        if stats['max'] > 0.01 and stats['non_zero_percentage'] > 5.0:
            potential_objectives.append(key)
            logger.info(f"  [✓] {key:<20} 看起来是一个有效的优化目标 (Max={stats['max']:.3f}, Non-zero={stats['non_zero_percentage']:.1f}%)。")
        else:
            logger.info(f"  [✗] {key:<20} 可能不是一个好的优化目标 (Max={stats['max']:.3f}, Non-zero={stats['non_zero_percentage']:.1f}%)。它可能在此模型中不活跃或值太小。")

    logger.info(f"\n推荐的UC分量目标 (除了 'weight' 之外): {potential_objectives}")
    logger.info("请注意，'max_uc' 仍然是结构安全性的关键硬约束，即使不作为独立的优化目标，也必须在评估中进行检查。")
    logger.info("\n✅ 分析完成。")


if __name__ == "__main__":
    analyze_uc_components()
