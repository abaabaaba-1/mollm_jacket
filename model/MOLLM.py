# MOLLM.py (Corrected Version)

import yaml
import json
from model.LLM import LLM
import os
import pickle
from algorithm.MOO import MOO
from eval import eval_mo_results, mean_sr
import pandas as pd
import importlib

class ConfigLoader:
    def __init__(self, config_path="config.yaml"):
        config_path = os.path.join('problem', config_path)
        self.config = self._load_config(config_path)

    def _load_config(self, config_path):
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        return config

    def get(self, key, default=None):
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, {})
            else: # If value is not a dict, can't go deeper
                return default
        if value == {}:
            return default
        return value
    
    def to_string(self, config=None, indent=0):
        """Recursively format the configuration dictionary as a string."""
        if config is None:
            config = self.config
        lines = []
        for key, value in config.items():
            if isinstance(value, dict):
                lines.append(" " * indent + f"{key}:")
                lines.append(self.to_string(value, indent + 2))
            else:
                lines.append(" " * indent + f"{key}: {value}")
        return "\n".join(lines)

class MOLLM:
    def __init__(self, config='base.yaml', resume=False, eval=False, seed=42, objectives=None, directions=None):
        if isinstance(config, str):
            self.config = ConfigLoader(config)
        else:
            self.config = config
        
        # --- START OF CORRECTIONS ---

        # [MODIFIED] 将 resume 和 seed 标志直接存入 config 对象中
        # 这样，当我们将 config 传递给 MOO 类时，它能获取到这些关键参数。
        self.config.config['resume'] = resume
        self.config.config['seed'] = seed

        print('goals, directs', self.config.get('goals'), self.config.get('optimization_direction'))
        if objectives is not None:
            print(f'objectives  {objectives} directions {directions}')
            self.config.config['goals'] = objectives
            assert directions is not None, "Directions must be provided if objectives are overridden."
            self.config.config['optimization_direction'] = directions
            print('goals, directs', self.config.get('goals'), self.config.get('optimization_direction'))
        
        self.property_list = self.config.get('goals')

        if not eval:
            module_path = self.config.get('evalutor_path')
            module = importlib.import_module(module_path)
            RewardingSystem = getattr(module, "RewardingSystem")
            self.reward_system = RewardingSystem(config=self.config)
        
        self.llm = LLM(model=self.config.get('model.name'))
        self.seed = seed
        self.history = []
        self.init_pops = []
        self.final_pops = []
        self.start_index = 0
        
        # [MODIFIED] 不再截断 model_name，使用完整的名称来构建路径，与 MOO.py 保持一致。
        model_name = self.config.get('model.name')
        self.save_dir = os.path.join(self.config.get('save_dir'), model_name)
        
        self.save_suffix = self.config.get('save_suffix')
        self.resume = resume

        # [MODIFIED] 将 'save_path' 重命名为 'summary_path' 以避免混淆。
        # 这个路径是 MOLLM 类自己保存最终总结文件的地方，不应与 MOO 的检查点路径混用。
        self.summary_path = os.path.join(self.save_dir, '_'.join(self.property_list) + '_' + self.save_suffix + '.pkl')
        
        # --- END OF CORRECTIONS ---

        self.results = {
            'mean success num': 0,
            'mean success rate': 0,
            'success num each problem': []
        }
    
    def run(self):
        # --- START OF CORRECTIONS ---

        # [REMOVED] 删除了在 MOLLM层面 进行的加载尝试。
        # 这是导致 FileNotFoundError 的直接原因。
        # if self.resume:
        #     self.load_from_pkl(self.save_path) # This was the error source

        # [CORRECTED] 创建 MOO 实例。由于 resume 和 seed 已在 config 中，
        # MOO 内部的逻辑可以正确地进行“新运行”或“恢复运行”的决策。
        moo = MOO(
            reward_system=self.reward_system, 
            llm=self.llm, 
            property_list=self.property_list, 
            config=self.config, 
            seed=self.seed
        )
        
        # --- END OF CORRECTIONS ---

        init_pops, final_pops = moo.run()
        self.history.append(moo.history)
        self.final_pops.append(final_pops)
        self.init_pops.append(init_pops)

        # 评估和保存最终结果（可选，可在运行结束后手动触发）
        # self.evaluate()
        # self.save_to_pkl(self.summary_path)

    def load_evaluate(self):
        # 注意：这里加载的是 MOLLM 的总结文件，而不是 MOO 的检查点
        self.load_from_pkl(self.summary_path) 
        r = self.evaluate()
        print(r)

    def evaluate(self):
        obj = {
            'init_pops': self.init_pops,
            'final_pops': self.final_pops,
        }
        r = eval_mo_results(self.dataset, obj, ops=self.property_list)
        mean_success_num, mean_success_rate, new_sr = mean_sr(r)
        print(f'mean success number: {mean_success_num:.4f}, new mean success rate {new_sr:.4f}, mean success rate: {mean_success_rate:.4f}')
        self.results = {
            'mean success num': mean_success_num,
            'new mean success rate': new_sr,
            'mean success rate': mean_success_rate,
            'success num each problem': r
        }
        return r

    def save_to_pkl(self, filepath, i=0):
        """保存 MOLLM 的最终运行总结"""
        data = {
            'history': self.history,
            'init_pops': self.init_pops,
            'final_pops': self.final_pops,
            'evaluation': self.results,
            'properties': self.property_list
        }
        # 确保目录存在
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
        
        # 避免在循环中频繁打印
        if i % 10 == 0 or i == 0:
            print(f"MOLLM summary data saved to {filepath}")

    def load_from_pkl(self, filepath):
        """加载 MOLLM 的最终运行总结"""
        if not os.path.exists(filepath):
            print(f"Warning: Summary file not found at {filepath}, creating new history.")
            self.history = []
            self.init_pops = []
            self.final_pops = []
            self.start_index = 0
            return None

        with open(filepath, 'rb') as f:
            obj = pickle.load(f)
        self.history = obj.get('history', [])
        self.init_pops = obj.get('init_pops', [])
        self.final_pops = obj.get('final_pops', [])
        self.start_index = len(self.init_pops)
        print(f"MOLLM summary data loaded from {filepath}")
        return obj

