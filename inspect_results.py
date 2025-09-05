# inspect_results.py (Final Corrected Version)

import pickle
import pandas as pd
import plotly.express as px
import sys
import os

# --- 路径修正 (保持不变) ---
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 这允许pickle正确地反序列化在项目中定义的自定义类
# 比如 'Item' 和 'HistoryBuffer'
from algorithm.base import Item, HistoryBuffer

# --- 1. 定义你的 .pkl 文件路径 ---
pkl_file_path = './moo_results/zgca,gemini-2.5-flash-nothinking/mols/weight_uc_fatigue_sacs_block_gen_baseline_GA_42.pkl'

print(f"正在加载文件: {pkl_file_path}")

# --- 2. 加载 Pickle 文件 ---
try:
    with open(pkl_file_path, 'rb') as f:
        results_dict = pickle.load(f)
except FileNotFoundError:
    print(f"错误: 文件未找到! 请检查路径是否正确: {pkl_file_path}")
    sys.exit(1)
except Exception as e:
    print(f"加载文件时发生错误: {e}")
    sys.exit(1)

print("文件加载成功! 加载的数据类型为:", type(results_dict))
print("结果字典包含的键:", list(results_dict.keys()))

# --- 3. 从 'history' 中提取最后一代替换种群 ---
# **【核心修正】**: 我们要找的不是 'final_pops', 而是 'history' 中的最后一代数据
if 'history' not in results_dict:
    print("错误: 在加载的字典中没有找到 'history' 键。")
    sys.exit(1)

history_buffer = results_dict['history']

# history_buffer.generations 是一个列表，每个元素是一代的种群（一个Item列表）
# 我们取最后一个元素，即为最终的种群
if not history_buffer.generations:
    print("错误: history_buffer 中没有找到任何代的种群数据。")
    sys.exit(1)

final_population = history_buffer.generations[-1]
generation_count = len(history_buffer.generations)

print(f"\n成功从 history 中提取数据。总共有 {generation_count} 代。")
print(f"正在分析最后一代（第 {generation_count} 代）的种群，包含 {len(final_population)} 个个体。")


# --- 4. 将种群数据转换为 Pandas DataFrame (保持不变) ---
# 种群中的每个 'item' 都有一个 'properties' 字典
data_for_df = [item.properties for item in final_population]

df = pd.DataFrame(data_for_df)

# 显示数据的前5行和基本统计信息
print("\n--- 最终种群数据预览 (前5行) ---")
print(df.head())

print("\n--- 数据统计摘要 ---")
print(df.describe())


# --- 5. 可视化种群分布 (3D 交互式散点图) ---
required_cols = ['Structure Weight', 'UC', 'Fatigue Life']
if not all(col in df.columns for col in required_cols):
    print("\n错误: DataFrame中缺少必要的列。可用列:", df.columns)
    print("请检查 `item.properties` 的键名是否正确。")
else:
    print("\n正在生成3D交互式散点图...")
    fig = px.scatter_3d(
        df,
        x='Structure Weight',
        y='UC',
        z='Fatigue Life',
        title='<b>最终种群在目标空间的分布 (基线模型)</b>',
        hover_data=df.columns, # 鼠标悬停时显示所有属性
        labels={
            'Structure Weight': '结构重量 (越小越好)',
            'UC': 'UC (越小越好)',
            'Fatigue Life': '疲劳寿命 (越大越好)'
        }
    )

    fig.update_traces(marker=dict(size=5, opacity=0.8))
    fig.update_layout(
        scene=dict(
            xaxis_title_text='结构重量',
            yaxis_title_text='UC',
            zaxis_title_text='疲劳寿命'
        ),
        margin=dict(r=20, b=10, l=10, t=50)
    )

    fig.show()
    print("图表已生成。请在打开的浏览器窗口中查看。")
