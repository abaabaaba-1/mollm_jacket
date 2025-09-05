import yaml
import json
from pathlib import Path

# --- 配置 ---
# 确保这个路径指向您的 SACS YAML 文件
PROMPT_YAML_PATH = Path('problem/sacs/sacs.yaml')


def load_prompt_config(path: Path) -> dict:
    """加载并解析YAML配置文件"""
    if not path.exists():
        print(f"错误：找不到YAML文件: {path}")
        print("请确保您在项目的根目录下运行此脚本。")
        exit()
    with open(path, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)


def create_mock_candidate(name: str) -> dict:
    """创建一个逼真的“父代”候选方案，用于填充提示词"""
    # 这些值可以随意修改，以观察它们如何影响提示词
    if name == "parent_1":
        return {
            "performance": {
                "weight": 147.8,
                "uc": 0.98,
                "fatigue": 21.5
            },
            "code_blocks": {
                "GRUP_LG1": "GRUP LG1         40.000 1.250 29.0011.6050.00 1    1.001.00     0.500N490.005.00",
                "PGRUP_P01": "PGRUP P01 0.3500I29.000 0.25036.000                                     490.0000"
            }
        }
    else:  # parent_2
        return {
            "performance": {
                "weight": 160.2,
                "uc": 0.85,
                "fatigue": 45.0
            },
            "code_blocks": {
                "GRUP_LG1": "GRUP LG1         42.000 1.375 29.0011.6050.00 1    1.001.00     0.500N490.005.00",
                "PGRUP_P01": "PGRUP P01 0.4500I29.000 0.25036.000                                     490.0000"
            }
        }


def format_candidate_for_prompt(candidate: dict, title: str) -> str:
    """将候选方案的字典格式化为提示词中可读的文本块"""
    perf_str = "\n".join([f"- {key}: {value}" for key, value in candidate['performance'].items()])
    # 使用 json.dumps 来美化代码块的输出
    code_str = json.dumps(candidate['code_blocks'], indent=4)

    return f"""
--- START OF {title.upper()} DATA ---
{title} Performance Metrics:
{perf_str}

{title} SACS Code Blocks:
{code_str}
--- END OF {title.upper()} DATA ---
"""


def assemble_prompt(config: dict, operator_type: str, candidates: list) -> str:
    """
    根据YAML配置和候选方案，组装最终的提示词。

    :param config: 从YAML加载的配置字典。
    :param operator_type: 'mutation' 或 'crossover'。
    :param candidates: 包含一个或两个模拟候选方案的列表。
    """
    if operator_type not in ['mutation', 'crossover']:
        raise ValueError("Operator type must be 'mutation' or 'crossover'")

    prompt_parts = []

    # 1. 通用描述
    prompt_parts.append(config['description'])

    # 2. 动态数据 (父代候选方案)
    if operator_type == 'mutation':
        prompt_parts.append(format_candidate_for_prompt(candidates[0], "Candidate for Mutation"))
    else:  # crossover
        prompt_parts.append(format_candidate_for_prompt(candidates[0], "Parent 1"))
        prompt_parts.append(format_candidate_for_prompt(candidates[1], "Parent 2"))

    # 3. 特定指令 (Mutation 或 Crossover)
    instruction_key = f'{operator_type}_instruction'
    prompt_parts.append(config[instruction_key])

    # 4. 其它通用要求
    prompt_parts.append("\n--- OBJECTIVES & OUTPUT FORMAT ---")
    prompt_parts.append("Objective Definitions:\n" + config['objective_definitions'])
    prompt_parts.append("\nRequired Output Format:\n" + config['example_output'])
    prompt_parts.append("\nOther Requirements:\n" + config['other_requirements'])

    return "\n\n".join(prompt_parts)


if __name__ == "__main__":
    # 加载YAML配置
    prompt_config = load_prompt_config(PROMPT_YAML_PATH)

    # 创建模拟的父代数据
    parent_1 = create_mock_candidate("parent_1")
    parent_2 = create_mock_candidate("parent_2")

    # --- 组装并打印 "Mutation" 提示词 ---
    mutation_prompt = assemble_prompt(prompt_config, 'mutation', [parent_1])
    print("=" * 80)
    print(" " * 30 + "MUTATION PROMPT")
    print("=" * 80)
    print(mutation_prompt)
    print("\n" * 2)

    # --- 组装并打印 "Crossover" 提示词 ---
    crossover_prompt = assemble_prompt(prompt_config, 'crossover', [parent_1, parent_2])
    print("=" * 80)
    print(" " * 30 + "CROSSOVER PROMPT")
    print("=" * 80)
    print(crossover_prompt)
    print("=" * 80)

