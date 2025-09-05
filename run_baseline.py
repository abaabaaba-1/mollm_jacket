# run_baseline.py (Final Version with Path Correction)

import sys
import os
import argparse
import random
import json
import copy
import numpy as np

# ----------------- 路径修正代码 [开始] -----------------
# 动态地将项目根目录（MOLLM-MAIN）添加到Python的搜索路径中
# 这确保了脚本总能找到 'model', 'algorithm', 'problem' 等模块
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# ----------------- 路径修正代码 [结束] -----------------


# --- 核心：从现有框架导入我们需要的类和函数 ---
# 现在这些导入应该可以正常工作了
from model.MOLLM import MOLLM, ConfigLoader
from algorithm.MOO import MOO
from algorithm.base import Item
# 从评估器中导入关键的非LLM变异函数，这是我们基线算子的核心
from problem.sacs.evaluator import _parse_and_modify_line


class BaselineMOO(MOO):
    """
    基线多目标优化类，继承自原始的MOO类。
    它重写了生成后代(offspring)的逻辑，使用传统的遗传算子替代LLM。
    """
    def __init__(self, reward_system, llm, property_list, config, seed):
        # 直接调用父类的初始化方法，尽管我们不会使用llm对象
        super().__init__(reward_system, llm, property_list, config, seed)
        self.mutation_prob = config.get('baseline.mutation_prob', 0.2)
        self.crossover_prob = config.get('baseline.crossover_prob', 0.8)
        print("--- BaselineMOO in a classic Genetic Algorithm mode is activated ---")
        print(f"Mutation probability: {self.mutation_prob}, Crossover probability: {self.crossover_prob}")


    def baseline_genetic_operator(self, parent_list: list) -> tuple:
        """
        实现经典的交叉和变异算子，替代LLM调用。
        返回与原始mating函数兼容的元组格式。
        """
        parent1, parent2 = parent_list[0], parent_list[1]
        
        # 将父代的字符串值（JSON）解析为字典
        try:
            design1 = json.loads(parent1.value)
            design2 = json.loads(parent2.value)
        except json.JSONDecodeError:
            print(f"Warning: Failed to decode parent JSON. Skipping operation.")
            # 返回原始父代以避免崩溃
            return [copy.deepcopy(parent1), copy.deepcopy(parent2)], None, None

        # 创建两个新的子代设计
        offspring_design1 = {"new_code_blocks": {}}
        offspring_design2 = {"new_code_blocks": {}}

        all_keys = list(design1["new_code_blocks"].keys())

        # --- 交叉 (Crossover) ---
        # 对每个基因（代码块），随机从一个父代继承
        for key in all_keys:
            if random.random() < 0.5:
                offspring_design1["new_code_blocks"][key] = design1["new_code_blocks"][key]
                offspring_design2["new_code_blocks"][key] = design2["new_code_blocks"][key]
            else:
                offspring_design1["new_code_blocks"][key] = design2["new_code_blocks"][key]
                offspring_design2["new_code_blocks"][key] = design1["new_code_blocks"][key]

        # --- 变异 (Mutation) ---
        for offspring_design in [offspring_design1, offspring_design2]:
            if random.random() < self.mutation_prob:
                # 随机选择一个或多个基因进行变异
                num_mutations = random.randint(1, max(1, len(all_keys) // 10))
                keys_to_mutate = random.sample(all_keys, num_mutations)
                
                for key in keys_to_mutate:
                    original_line = offspring_design["new_code_blocks"][key]
                    block_name = key.replace("_", " ")
                    # 使用从evaluator.py导入的函数进行随机扰动
                    mutated_line = _parse_and_modify_line(original_line, block_name)
                    offspring_design["new_code_blocks"][key] = mutated_line

        # 将子代设计转换回JSON字符串，并创建Item对象
        offspring1_str = json.dumps(offspring_design1)
        offspring2_str = json.dumps(offspring_design2)
        
        new_items = [self.item_factory.create(offspring1_str), self.item_factory.create(offspring2_str)]
        
        # 返回与原始框架兼容的格式（prompt和response为None）
        return new_items, None, None

    def generate_offspring(self, population: list, offspring_times: int) -> list:
        """
        重写生成后代的函数。
        这里我们不使用多线程，因为基线算子很快，且为了代码清晰。
        """
        parents_pairs = [random.sample(population, 2) for _ in range(offspring_times)]
        
        tmp_offspring = []
        for parents in parents_pairs:
            # 决定是执行交叉还是直接复制父代（这里简化为总是交叉变异）
            # if random.random() < self.crossover_prob:
            child_pair, _, _ = self.baseline_genetic_operator(parents)
            # else:
            #     child_pair = [copy.deepcopy(p) for p in parents]

            tmp_offspring.extend(child_pair)

        self.generated_num += len(tmp_offspring)
        
        # 注意：这里我们不像原版那样调用self.llm_calls，因为没有LLM调用
        
        if len(tmp_offspring) == 0:
            return []

        # 复用原始的评估和历史记录逻辑
        offspring = self.evaluate(tmp_offspring)
        # self.history.push的prompt和response参数为None
        prompts = [None] * len(parents_pairs)
        responses = [None] * len(parents_pairs)
        # a bit of a hack to fit the original structure
        generations = [tmp_offspring[i:i+2] for i in range(0, len(tmp_offspring), 2)]
        self.history.push(prompts, generations, responses)
        
        return offspring

    def update_experience(self):
        """
        对于基线模型，经验总结步骤被跳过。
        """
        # print("Skipping experience update for baseline model.")
        pass


class BaselineMOLLM(MOLLM):
    """
    用于运行基线实验的顶层控制器。
    """
    def run(self):
        """
        重写run方法，以实例化我们自定义的BaselineMOO而不是原始的MOO。
        """
        if self.resume:
            # 恢复功能仍可使用，但请确保恢复的是基线模型的存档
            self.load_from_pkl(self.save_path)

        # --- 关键修改：实例化BaselineMOO ---
        moo = BaselineMOO(self.reward_system, self.llm, self.property_list, self.config, self.seed)
        
        # 后续流程完全复用原始MOO类的run方法逻辑
        init_pops, final_pops = moo.run()
        
        self.history.append(moo.history)
        self.final_pops.append(final_pops)
        self.init_pops.append(init_pops)
        
        print("\nBaseline run finished.")


def main():
    # 设置命令行参数解析
    parser = argparse.ArgumentParser(description='Run Baseline MOO model for SACS optimization.')
    parser.add_argument('config', type=str, nargs='?', default='sacs/config.yaml', help='Path to the configuration file (e.g., config.yaml)')
    parser.add_argument('--seed', type=int, default=42, help='Random seed for reproducibility')
    parser.add_argument('--resume', action='store_true', help='Resume training from the last checkpoint')
    args = parser.parse_args()

    # --- 启动基线模型 ---
    # 我们使用一个专为基线模型调整的配置对象
    # 1. 加载原始配置
    config = ConfigLoader(args.config)
    # 2. 修改保存后缀，防止覆盖LLM版本的结果
    original_suffix = config.get('save_suffix', 'sacs_block_gen')
    config.config['save_suffix'] = f"{original_suffix}_baseline_GA"
    # 3. (可选)为基线添加特定参数
    if 'baseline' not in config.config:
        config.config['baseline'] = {
            'mutation_prob': 0.3,
            'crossover_prob': 0.7
        }
    
    print(f"Results will be saved with suffix: {config.get('save_suffix')}")

    # 实例化并运行基线控制器
    baseline_runner = BaselineMOLLM(config=config, resume=args.resume, eval=False, seed=args.seed)
    baseline_runner.run()


if __name__ == "__main__":
    main()

