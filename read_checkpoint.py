# read_checkpoint.py (V4 - 最终兼容版)

import pickle
import pandas as pd
import os
import json
import numpy as np

try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    PLOT_AVAILABLE = True
except ImportError:
    print("警告: 未安装 matplotlib 或 seaborn。将跳过数据可视化部分。")
    print("建议安装: pip install matplotlib seaborn pandas")
    PLOT_AVAILABLE = False

try:
    from algorithm.base import Item, HistoryBuffer
except ImportError:
    class Item: pass
    class HistoryBuffer: pass

pkl_file_path = 'moo_results/zgca,gemini-2.5-flash-nothinking/mols/weight_axial_uc_max_bending_uc_max_sacs_expanded_3_obj_42.pkl'

def analyze_checkpoint(filepath):
    if not os.path.exists(filepath):
        print(f"错误: 文件未找到于 '{filepath}'")
        return

    print(f"--- 正在读取文件: {filepath} ---")
    
    with open(filepath, 'rb') as f:
        data = pickle.load(f, encoding='latin1')

    print("\n文件包含以下主要部分 (keys):")
    print(list(data.keys()))
    
    if 'all_mols' not in data or not data['all_mols']:
        print("\n文件中没有找到 'all_mols' 数据。")
        return
        
    all_candidates = data['all_mols']
    print(f"\n共找到 {len(all_candidates)} 个被评估过的候选方案。")

    extracted_data = []
    for candidate_entry in all_candidates:
        if isinstance(candidate_entry, (list, tuple)) and candidate_entry:
            item = candidate_entry[0]
        else:
            item = candidate_entry
        
        if not hasattr(item, 'value') or not hasattr(item, 'property'):
            continue

        prop = item.property or {}
        info = {'candidate_string': item.value}

        # ======================= [ 核心修复：智能解析逻辑 ] =======================
        # 检查数据是新格式 (嵌套) 还是旧格式 (扁平)
        if 'original_results' in prop:
            # --- 新格式解析 ---
            original_results = prop.get('original_results', {})
            constraint_results = prop.get('constraint_results', {})
            info['weight'] = original_results.get('weight')
            info['axial_uc_max'] = original_results.get('axial_uc_max')
            info['bending_uc_max'] = original_results.get('bending_uc_max')
            info['is_feasible'] = constraint_results.get('is_feasible')
            info['max_uc'] = constraint_results.get('max_uc')
            info['error_reason'] = prop.get('error_reason')
        else:
            # --- 旧格式解析 ---
            info['weight'] = prop.get('weight')
            info['axial_uc_max'] = prop.get('axial_uc_max')
            info['bending_uc_max'] = prop.get('bending_uc_max')
            
            # 从旧数据中推断可行性
            max_uc = None
            if info['axial_uc_max'] is not None and info['bending_uc_max'] is not None:
                # 假设 SACS 运行成功，惩罚值不会出现
                if info['axial_uc_max'] < 100 and info['bending_uc_max'] < 100:
                    max_uc = max(info['axial_uc_max'], info['bending_uc_max'])

            info['max_uc'] = max_uc
            info['is_feasible'] = 1.0 if max_uc is not None and max_uc <= 1.0 else 0.0
            info['error_reason'] = None # 旧格式没有记录错误原因
        # =========================================================================

        extracted_data.append(info)

    if not extracted_data:
        print("\n未能从 'all_mols' 中成功提取任何数据。")
        return

    df = pd.DataFrame(extracted_data)
    df.dropna(subset=['weight', 'axial_uc_max', 'bending_uc_max'], how='all', inplace=True)
    
    print(f"\n--- 种群整体统计 (共 {len(df)} 条有效记录) ---")

    stats = df[['weight', 'axial_uc_max', 'bending_uc_max', 'max_uc']].agg(['mean', 'std', 'min', 'max'])
    print("\n所有有效解的统计数据:")
    print(stats.round(4))
    
    df_feasible = df[df['is_feasible'] == 1.0].copy()
    
    if df_feasible.empty:
        print("\n警告: 在所有候选方案中，没有找到任何可行解 (UC <= 1.0)。")
        if not df.empty:
            df_valid_uc = df[df['max_uc'] < 999].copy()
            if not df_valid_uc.empty:
                # 找出 UC 最接近 1.0 但可能大于1.0的解
                best_infeasible = df_valid_uc.loc[(df_valid_uc['max_uc']-1).abs().idxmin()]
                print("\n最接近可行边界 (UC≈1.0) 的解:")
                print(best_infeasible[['weight', 'axial_uc_max', 'bending_uc_max', 'max_uc']].to_string())
    else:
        print(f"\n恭喜！找到 {len(df_feasible)} 个可行解。")
        print("\n--- 各个单项最优的可行候选方案 ---")
        for col in ['weight', 'axial_uc_max', 'bending_uc_max']:
            if col in df_feasible.columns and not df_feasible[col].empty:
                best_row = df_feasible.loc[df_feasible[col].idxmin()]
                print(f"\n- 目标 '{col}' 的最优解 (最小值):")
                print(best_row[['weight', 'axial_uc_max', 'bending_uc_max', 'max_uc']].to_string())

    if PLOT_AVAILABLE and not df.empty:
        print("\n--- 正在生成数据分布图... ---")
        plt.style.use('seaborn-v0_8-whitegrid')
        
        df['Feasibility'] = df['is_feasible'].apply(lambda x: 'Feasible (UC <= 1)' if x == 1.0 else 'Infeasible (UC > 1 or Fail)')

        g = sns.pairplot(
            df.query('max_uc < 10 and weight < 500'), # 过滤极端值以获得更好的可视化效果
            vars=['weight', 'axial_uc_max', 'bending_uc_max'],
            hue='Feasibility',
            palette={'Feasible (UC <= 1)': 'green', 'Infeasible (UC > 1 or Fail)': 'red'},
            diag_kind='hist', plot_kws={'alpha': 0.6, 's': 30}, height=3
        )
        g.fig.suptitle('种群目标分布 (可行 vs 不可行)', y=1.02, fontsize=16)
        
        save_path = 'checkpoint_analysis_final.png'
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"✅ 可视化图表已保存至: {os.path.abspath(save_path)}")


def find_latest_pkl_file(root_dir):
    all_pkls = [os.path.join(path, name) for path, _, files in os.walk(root_dir) for name in files if name.endswith(".pkl")]
    return max(all_pkls, key=os.path.getmtime) if all_pkls else None


if __name__ == '__main__':
    try:
        search_root = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        search_root = os.getcwd()
    latest_pkl = find_latest_pkl_file(search_root)
    
    if latest_pkl:
        print(f"🔍 自动找到最新的结果文件: {latest_pkl}")
        analyze_checkpoint(latest_pkl)
    else:
        print(f"⚠️ 在目录 {search_root} 中未找到任何 .pkl 文件，请检查路径。")
