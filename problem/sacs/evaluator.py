# problem/sacs/evaluator.py

import numpy as np
import json
import logging
import random
import copy
from pathlib import Path

# --- 从相同目录导入 SACS 特定模块 ---
from .sacs_file_modifier import SacsFileModifier
from .sacs_runner import SacsRunner
from .sacs_interface_uc import get_sacs_uc_summary
from .sacs_interface_weight import calculate_sacs_volume
from .sacs_interface_ftg import get_sacs_fatigue_summary

# --------------------------------------------------------------------------
# --- 修改开始：定义所有精英种子并更新初始种群列表 ---
# --------------------------------------------------------------------------

# 1. 将所有由 seed_finder.py 生成的精英种子定义为Python字典

# 基准方案
SEED_BASELINE = { "new_code_blocks": { "GRUP_LG1": "GRUP LG1         42.200 1.450 29.0011.6050.00 1    1.001.00     0.500N490.005.00", "GRUP_LG2": "GRUP LG2         42.200 1.450 29.0011.6050.00 1    1.001.00     0.500N490.006.15", "GRUP_LG3": "GRUP LG3         42.200 1.450 29.0011.6050.00 1    1.001.00     0.500N490.006.75", "GRUP_LG4": "GRUP LG4         42.200 1.450 29.0011.6050.00 1    1.001.00     0.500N490.00", "GRUP_LG5": "GRUP LG5         36.300 1.050 29.0011.6050.00 1    1.001.00     0.500N490.00", "GRUP_LG6": "GRUP LG6         36.300 0.800 29.0011.0036.00 1    1.001.00     0.500N490.003.25", "GRUP_LG7": "GRUP LG7         26.200 0.800 29.0011.6036.00 1    1.001.00     0.500N490.00", "GRUP_PL1": "GRUP PL1         36.300 1.050 29.0011.6036.00 1    1.001.00     0.500N490.00", "GRUP_PL2": "GRUP PL2         36.300 1.050 29.0011.6036.00 1    1.001.00     0.500N490.00", "GRUP_PL3": "GRUP PL3         36.300 1.050 29.0011.6036.00 1    1.001.00     0.500N490.00", "GRUP_PL4": "GRUP PL4         36.300 1.050 29.0011.6036.00 1    1.001.00     0.500N490.00", "GRUP_T01": "GRUP T01         16.100 0.650 29.0111.2035.00 1    1.001.00     0.500N490.00", "GRUP_T02": "GRUP T02         20.100 0.780 29.0011.6035.00 1    1.001.00     0.500N490.00", "GRUP_T03": "GRUP T03         12.800 0.520 29.0111.6035.00 1    1.001.00     0.500N490.00", "GRUP_T04": "GRUP T04         24.100 0.780 29.0011.6036.00 1    1.001.00     0.500N490.00", "GRUP_T05": "GRUP T05         26.100 1.050 29.0011.6036.00 1    1.001.00     0.500N490.00", "GRUP_W.B": "GRUP W.B         36.500 1.050 29.0111.2035.97 1    1.001.00     0.500 490.00", "PGRUP_P01": "PGRUP P01 0.3750I29.000 0.25036.000                                     490.0000" } }
# 我们将基准方案作为第一个，并重命名为 BASELINE_CODE_BLOCKS 以兼容旧代码
BASELINE_CODE_BLOCKS = SEED_BASELINE

# 重量最小的方案
SEED_MIN_WEIGHT_1 = { "new_code_blocks": { "GRUP_LG1": "GRUP LG1          10.000 0.450 9.0011.6050.00 1    1.001.00     0.500N490.005.00", "GRUP_LG2": "GRUP LG2         42.200 1.450 29.0011.6050.00 1    1.001.00     0.500N490.006.15", "GRUP_LG3": "GRUP LG3         42.200 1.450 29.0011.6050.00 1    1.001.00     0.500N490.006.75", "GRUP_LG4": "GRUP LG4           2.200 0.500 9.0011.6050.00 1    1.001.00     0.500N490.00", "GRUP_T02": "GRUP T02          10.000 0.780 9.0011.6035.00 1    1.001.00     0.500N490.00", **{k:v for k,v in SEED_BASELINE["new_code_blocks"].items() if k not in ["GRUP_LG1", "GRUP_LG2", "GRUP_LG3", "GRUP_LG4", "GRUP_T02"]}} }
SEED_MIN_WEIGHT_2 = { "new_code_blocks": { "GRUP_LG4": "GRUP LG4           2.200 0.500 9.0011.6050.00 1    1.001.00     0.500N490.00", **{k:v for k,v in SEED_BASELINE["new_code_blocks"].items() if k not in ["GRUP_LG4"]}}}

# 重量最大的方案
SEED_MAX_WEIGHT_1 = { "new_code_blocks": { "GRUP_LG2": "GRUP LG2          10.000 0.450 9.0011.6050.00 1    1.001.00     0.500N490.006.15", "GRUP_T02": "GRUP T02          10.000 0.780 9.0011.6035.00 1    1.001.00     0.500N490.00", "GRUP_T03": "GRUP T03          10.000 0.520 9.0111.6035.00 1    1.001.00     0.500N490.00", **{k:v for k,v in SEED_BASELINE["new_code_blocks"].items() if k not in ["GRUP_LG2", "GRUP_T02", "GRUP_T03"]}} }

# UC最小的方案
SEED_MIN_UC_1 = { "new_code_blocks": { "GRUP_LG4": "GRUP LG4          10.000 0.450 9.0011.6050.00 1    1.001.00     0.500N490.00", **{k:v for k,v in SEED_BASELINE["new_code_blocks"].items() if k not in ["GRUP_LG4"]}} }
SEED_MIN_UC_2 = { "new_code_blocks": { "GRUP_LG2": "GRUP LG2          10.000 0.450 9.0011.6050.00 1    1.001.00     0.500N490.006.15", **{k:v for k,v in SEED_BASELINE["new_code_blocks"].items() if k not in ["GRUP_LG2"]}} }

# UC最大的方案
SEED_MAX_UC_1 = { "new_code_blocks": { "GRUP_LG1": "GRUP LG1           2.200 0.500 9.0011.6050.00 1    1.001.00     0.500N490.005.00", "GRUP_LG4": "GRUP LG4          10.000 0.450 9.0011.6050.00 1    1.001.00     0.500N490.00", **{k:v for k,v in SEED_BASELINE["new_code_blocks"].items() if k not in ["GRUP_LG1", "GRUP_LG4"]}} }

# 疲劳寿命最长的方案
SEED_MAX_FATIGUE_1 = { "new_code_blocks": { "GRUP_LG1": "GRUP LG1          10.000 0.450 9.0011.6050.00 1    1.001.00     0.500N490.005.00", **{k:v for k,v in SEED_BASELINE["new_code_blocks"].items() if k not in ["GRUP_LG1"]}} }
SEED_MAX_FATIGUE_2 = { "new_code_blocks": { "GRUP_LG3": "GRUP LG3          10.000 0.450 9.0011.6050.00 1    1.001.00     0.500N490.006.75", **{k:v for k,v in SEED_BASELINE["new_code_blocks"].items() if k not in ["GRUP_LG3"]}} }

# 疲劳寿命最短的方案
SEED_MIN_FATIGUE_1 = { "new_code_blocks": { "GRUP_LG3": "GRUP LG3          10.000 0.450 9.0011.6050.00 1    1.001.00     0.500N490.006.75", "GRUP_LG4": "GRUP LG4           2.200 0.586 9.0011.6050.00 1    1.001.00     0.500N490.00", **{k:v for k,v in SEED_BASELINE["new_code_blocks"].items() if k not in ["GRUP_LG3", "GRUP_LG4"]}} }


# 2. 将所有精英种子汇集到一个列表中，用于初始化种群
INITIAL_SEEDS = [
    SEED_BASELINE,
    SEED_MIN_WEIGHT_1,
    SEED_MIN_WEIGHT_2,
    SEED_MAX_WEIGHT_1,
    SEED_MIN_UC_1,
    SEED_MIN_UC_2,
    SEED_MAX_UC_1,
    SEED_MAX_FATIGUE_1,
    SEED_MAX_FATIGUE_2,
    SEED_MIN_FATIGUE_1,
]

logging.info(f"成功加载并定义了 {len(INITIAL_SEEDS)} 个内存中的精英种子方案用于初始种群生成。")

# --- 修改结束 ---


def _parse_and_modify_line(line, block_name):
    """
    辅助函数，用于解析并随机修改 GRUP 或 PGRUP 卡片行。
    保持扩大的随机扰动范围以增强探索能力。
    """
    # (此函数保持不变，无需修改)
    try:
        keyword = block_name.split()[0]

        if keyword == "GRUP":
            key_part = line[0:4]
            group_name = block_name.split()[1]
            group_part = f" {group_name:<13}"
            od_str, wt_str = line[18:24], line[25:30]
            rest_of_line = line[31:]
            od_val, wt_val = float(od_str), float(wt_str)

            if random.choice([True, False]):
                od_val *= random.uniform(0.6, 1.4) 
                od_val = np.clip(od_val, 10.0, 48.0)
            else:
                wt_val *= random.uniform(0.6, 1.4) 
                wt_val = np.clip(wt_val, 0.5, 2.5)

            new_line = f"{key_part}{group_part}{od_val:>6.3f} {wt_val:>5.3f} {rest_of_line}"
            return new_line[:len(line)]

        elif keyword == "PGRUP":
            part1 = line[0:11]
            full_value_part = line[11:]
            separator = 'I' if 'I' in full_value_part else ''
            
            if separator:
                thick_str, rest_of_line = full_value_part.split(separator, 1)
            else:
                thick_str, rest_of_line = line[11:17].strip(), line[17:]
            
            thick_val = float(thick_str) * random.uniform(0.8, 1.2)
            thick_val = np.clip(thick_val, 0.250, 0.750)

            new_thick_str = f"{thick_val:<6.4f}"
            return f"{part1}{new_thick_str}{separator}{rest_of_line}"

    except Exception as e:
        logging.error(f"在 _parse_and_modify_line 中处理 '{line}' 时出错: {e}", exc_info=True)
        return line

    return line


def generate_initial_population(config, seed):
    """
    V3 - 初始种群生成逻辑更新。
    使用新的 INITIAL_SEEDS 列表。
    """
    np.random.seed(seed)
    random.seed(seed)
    population_size = config.get('optimization.pop_size')
    initial_population = []

    # 1. 直接将所有精英种子方案加入初始种群 (确保不重复)
    seen_seeds = set()
    for seed_candidate in INITIAL_SEEDS:
        if len(initial_population) >= population_size:
            break
        # 使用JSON字符串作为唯一标识
        candidate_str = json.dumps(seed_candidate, sort_keys=True)
        if candidate_str not in seen_seeds:
            initial_population.append(json.dumps(seed_candidate))
            seen_seeds.add(candidate_str)
            
    # 2. 通过扰动种子方案来填充剩余的种群名额
    while len(initial_population) < population_size:
        base_candidate = copy.deepcopy(random.choice(INITIAL_SEEDS))
        
        # 随机选择1到3个块进行修改
        num_modifications = random.randint(1, 3)
        blocks_to_modify_keys = random.sample(list(base_candidate["new_code_blocks"].keys()), num_modifications)

        for block_to_modify_key in blocks_to_modify_keys:
            block_to_modify_name = block_to_modify_key.replace("_", " ")
            original_sacs_line = base_candidate["new_code_blocks"][block_to_modify_key]
            modified_sacs_line = _parse_and_modify_line(original_sacs_line, block_to_modify_name)
            base_candidate["new_code_blocks"][block_to_modify_key] = modified_sacs_line
        
        initial_population.append(json.dumps(base_candidate))

    return initial_population

# ... (RewardingSystem 类 和 _transform_objectives 函数保持不变) ...

class RewardingSystem:
    # (此类的所有代码保持不变，无需修改)
    def __init__(self, config):
        self.config = config
        self.sacs_project_path = config.get('sacs.project_path')
        self.logger = logging.getLogger(self.__class__.__name__)
        self.modifier = SacsFileModifier(self.sacs_project_path)
        self.runner = SacsRunner(project_path=self.sacs_project_path)
        self.objs = config.get('goals', [])
        self.obj_directions = {obj: config.get('optimization_direction')[i] for i, obj in enumerate(self.objs)}

    def evaluate(self, items):
        invalid_num = 0
        for item in items:
            try:
                raw_value = item.value
                
                try:
                    json_str = raw_value
                    if '<candidate>' in raw_value:
                        json_str = raw_value.split('<candidate>', 1)[1].rsplit('</candidate>', 1)[0].strip()
                    modifications = json.loads(json_str)
                    new_code_blocks = modifications.get("new_code_blocks")
                except (json.JSONDecodeError, IndexError) as e:
                    self.logger.warning(f"从候选体解析JSON失败: {raw_value}. 错误: {e}")
                    self._assign_penalty(item, "无效的JSON或候选体格式")
                    invalid_num += 1
                    continue

                if not new_code_blocks or not isinstance(new_code_blocks, dict):
                    self.logger.warning(f"无效的候选体格式: 'new_code_blocks' 缺失或不是字典. 值: {item.value}")
                    self._assign_penalty(item, "无效的候选体结构")
                    invalid_num += 1
                    continue
                
                if not self.modifier.replace_code_blocks(new_code_blocks):
                    self._assign_penalty(item, "文件修改失败")
                    invalid_num += 1
                    continue

                analysis_result = self.runner.run_analysis(timeout=300)
                
                if not analysis_result.get('success'):
                    self.logger.warning(f"SACS分析候选体失败。原因: {analysis_result.get('error', '未知错误')}")
                    sacs_error_msg = str(analysis_result.get('error', '未知错误'))
                    self._assign_penalty(item, f"SACS运行失败: {sacs_error_msg[:200]}")
                    invalid_num += 1
                    continue
                
                weight_res = calculate_sacs_volume(self.sacs_project_path)
                uc_res = get_sacs_uc_summary(self.sacs_project_path)
                ftg_res = get_sacs_fatigue_summary(self.sacs_project_path)

                is_uc_valid = uc_res.get('status') in ['success', 'success_no_data']
                if not (weight_res.get('status') == 'success' and is_uc_valid and ftg_res.get('status') == 'success'):
                    self.logger.warning("在SACS运行后，指标提取失败。")
                    self._assign_penalty(item, "指标提取失败")
                    invalid_num += 1
                    continue

                original = {
                    'weight': weight_res['total_volume_m3'],
                    'uc': uc_res.get('max_uc', 999.0),
                    'fatigue': ftg_res.get('min_life_years', 0.0)
                }

                transformed = self._transform_objectives(original)
                # 使用 np.mean 替代 np.sum，使分数范围回到 [0, 1] 区间
                overall_score = 1.0 - np.mean(list(transformed.values()))

                results = {
                    'original_results': original,
                    'transformed_results': transformed,
                    'overall_score': overall_score
                }
                item.assign_results(results)

            except Exception as e:
                self.logger.critical(f"评估项目 '{getattr(item, 'value', 'N/A')}' 时发生错误: {e}",
                                     exc_info=True)
                self._assign_penalty(item, f"评估时发生错误: {e}")
                invalid_num += 1

        log_dict = { "invalid_num": invalid_num, "repeated_num": 0 }
        return items, log_dict

    def _assign_penalty(self, item, reason=""):
        penalty_score = 999
        original = {}
        for obj in self.objs:
            original[obj] = penalty_score if self.obj_directions[obj] == 'min' else -penalty_score

        transformed = {obj: 1.0 for obj in self.objs}
        overall_score = -1.0 # 最差的分数

        results = {
            'original_results': original,
            'transformed_results': transformed,
            'overall_score': overall_score,
            'error_reason': reason
        }
        item.assign_results(results)

    def _transform_objectives(self, original_results):
        transformed = {}
        # 假设w, uc, ftg的期望范围来自配置文件或者分析
        w_min, w_max = 2.0, 4.0
        uc_min, uc_max = 0.7, 1.0
        ftg_min, ftg_max = 20, 300
    
        w = np.clip(original_results.get('weight', w_max), w_min, w_max)
        transformed['weight'] = (w - w_min) / (w_max - w_min)
        
        uc_raw = original_results.get('uc', uc_max)
        if uc_raw > uc_max:
             # 如果UC超限，施加惩罚，使其标准化值大于1
             uc = uc_max + (uc_raw - uc_max) * 5.0 # 乘以惩罚因子
        else:
             uc = uc_raw
        uc_clipped = np.clip(uc, uc_min, uc_max + (999-uc_max)*5.0) # 允许惩罚后的值
        transformed['uc'] = (uc_clipped - uc_min) / (uc_max - uc_min)

        ftg = np.clip(original_results.get('fatigue', ftg_min), ftg_min, ftg_max)
        # 疲劳是越大越好，所以需要反向归一化
        normalized_ftg = (ftg - ftg_min) / (ftg_max - ftg_min)
        transformed['fatigue'] = 1.0 - normalized_ftg # 值越小越好

        return transformed
