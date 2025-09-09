import json
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

# --- JSON数据直接嵌入为字符串 ---

# 数据1: weight_uc_fatigue_sacs_block_gen_42.json 的内容
json_data_llm = """
{
    "results": [
        {"all_unique_moles": 40, "llm_calls": 0, "avg_top1": 0.35863095238095244, "hypervolume": 0.01934821428571431},
        {"all_unique_moles": 68, "llm_calls": 20, "avg_top1": 0.35863095238095244, "hypervolume": 0.01934821428571431},
        {"all_unique_moles": 101, "llm_calls": 40, "avg_top1": 0.35863095238095244, "hypervolume": 0.01934821428571431},
        {"all_unique_moles": 130, "llm_calls": 60, "avg_top1": 0.35863095238095244, "hypervolume": 0.01934821428571431},
        {"all_unique_moles": 157, "llm_calls": 80, "avg_top1": 0.35863095238095244, "hypervolume": 0.01934821428571431},
        {"all_unique_moles": 186, "llm_calls": 100, "avg_top1": 0.35863095238095244, "hypervolume": 0.01934821428571431},
        {"all_unique_moles": 216, "llm_calls": 120, "avg_top1": 0.35863095238095244, "hypervolume": 0.01934821428571431},
        {"all_unique_moles": 243, "llm_calls": 140, "avg_top1": 0.35863095238095244, "hypervolume": 0.01934821428571431},
        {"all_unique_moles": 270, "llm_calls": 160, "avg_top1": 0.35863095238095244, "hypervolume": 0.01934821428571431},
        {"all_unique_moles": 305, "llm_calls": 180, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 339, "llm_calls": 200, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 363, "llm_calls": 220, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 392, "llm_calls": 240, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 420, "llm_calls": 260, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 451, "llm_calls": 280, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 478, "llm_calls": 300, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 507, "llm_calls": 320, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 537, "llm_calls": 340, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 571, "llm_calls": 360, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 601, "llm_calls": 380, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 632, "llm_calls": 400, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 662, "llm_calls": 420, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 694, "llm_calls": 440, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 723, "llm_calls": 460, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 755, "llm_calls": 480, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 786, "llm_calls": 500, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 815, "llm_calls": 520, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 844, "llm_calls": 540, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 869, "llm_calls": 560, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 904, "llm_calls": 580, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 933, "llm_calls": 600, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 963, "llm_calls": 620, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 990, "llm_calls": 640, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 1018, "llm_calls": 660, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 1046, "llm_calls": 680, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 1074, "llm_calls": 700, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 1105, "llm_calls": 720, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 1134, "llm_calls": 740, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 1160, "llm_calls": 760, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 1190, "llm_calls": 780, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 1216, "llm_calls": 800, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 1247, "llm_calls": 820, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 1276, "llm_calls": 840, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 1307, "llm_calls": 860, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 1333, "llm_calls": 880, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 1363, "llm_calls": 900, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 1394, "llm_calls": 920, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 1420, "llm_calls": 940, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 1420, "llm_calls": 940, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148}
    ], "params": "..."
}
"""

# 数据2: weight_uc_fatigue_sacs_block_gen_baseline_GA_42.json 的内容
json_data_ga = """
{
    "results": [
        {"all_unique_moles": 40, "llm_calls": 0, "avg_top1": 0.35863095238095244, "hypervolume": 0.01934821428571431},
        {"all_unique_moles": 78, "llm_calls": 0, "avg_top1": 0.3597619047619047, "hypervolume": 0.0197214285714286},
        {"all_unique_moles": 117, "llm_calls": 0, "avg_top1": 0.4065599642857143, "hypervolume": 0.03516478821428576},
        {"all_unique_moles": 154, "llm_calls": 0, "avg_top1": 0.4065599642857143, "hypervolume": 0.03516478821428576},
        {"all_unique_moles": 188, "llm_calls": 0, "avg_top1": 0.4065599642857143, "hypervolume": 0.03516478821428576},
        {"all_unique_moles": 221, "llm_calls": 0, "avg_top1": 0.4065599642857143, "hypervolume": 0.03516478821428576},
        {"all_unique_moles": 250, "llm_calls": 0, "avg_top1": 0.4065599642857143, "hypervolume": 0.03516478821428576},
        {"all_unique_moles": 272, "llm_calls": 0, "avg_top1": 0.4065599642857143, "hypervolume": 0.03516478821428576},
        {"all_unique_moles": 300, "llm_calls": 0, "avg_top1": 0.4065599642857143, "hypervolume": 0.03516478821428576},
        {"all_unique_moles": 322, "llm_calls": 0, "avg_top1": 0.4065599642857143, "hypervolume": 0.03516478821428576},
        {"all_unique_moles": 346, "llm_calls": 0, "avg_top1": 0.4065599642857143, "hypervolume": 0.03516478821428576},
        {"all_unique_moles": 374, "llm_calls": 0, "avg_top1": 0.4065599642857143, "hypervolume": 0.03516478821428576},
        {"all_unique_moles": 401, "llm_calls": 0, "avg_top1": 0.4065599642857143, "hypervolume": 0.03516478821428576},
        {"all_unique_moles": 425, "llm_calls": 0, "avg_top1": 0.4065599642857143, "hypervolume": 0.03516478821428576},
        {"all_unique_moles": 451, "llm_calls": 0, "avg_top1": 0.4065599642857143, "hypervolume": 0.03516478821428576},
        {"all_unique_moles": 478, "llm_calls": 0, "avg_top1": 0.4065599642857143, "hypervolume": 0.03516478821428576},
        {"all_unique_moles": 508, "llm_calls": 0, "avg_top1": 0.4065599642857143, "hypervolume": 0.03516478821428576},
        {"all_unique_moles": 538, "llm_calls": 0, "avg_top1": 0.41478495238095237, "hypervolume": 0.037879034285714326},
        {"all_unique_moles": 560, "llm_calls": 0, "avg_top1": 0.41478495238095237, "hypervolume": 0.037879034285714326},
        {"all_unique_moles": 581, "llm_calls": 0, "avg_top1": 0.41478495238095237, "hypervolume": 0.037879034285714326},
        {"all_unique_moles": 608, "llm_calls": 0, "avg_top1": 0.41478495238095237, "hypervolume": 0.037879034285714326},
        {"all_unique_moles": 636, "llm_calls": 0, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 666, "llm_calls": 0, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 693, "llm_calls": 0, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 720, "llm_calls": 0, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 749, "llm_calls": 0, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 775, "llm_calls": 0, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 804, "llm_calls": 0, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 837, "llm_calls": 0, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 871, "llm_calls": 0, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 900, "llm_calls": 0, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 932, "llm_calls": 0, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 961, "llm_calls": 0, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 990, "llm_calls": 0, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148},
        {"all_unique_moles": 1019, "llm_calls": 0, "avg_top1": 0.4285714285714285, "hypervolume": 0.04242857142857148}
    ], "params": "..."
}
"""

def parse_json_string(json_string):
    """
    解析JSON字符串并返回 'results' 部分。
    """
    try:
        data = json.loads(json_string)
        return data['results']
    except (json.JSONDecodeError, KeyError) as e:
        print(f"错误: 解析JSON字符串失败: {e}")
        return None

def extract_metrics(results, method_name):
    """
    从JOSN结果中提取所需指标，创建一个DataFrame。
    使用 'all_unique_moles' 作为评估次数的代理。
    """
    if not results:
        return pd.DataFrame()

    records = []
    # 为了简化，我们只关心 'all_unique_moles', 'avg_top1', 'hypervolume'
    for entry in results:
        records.append({
            'Evaluations': entry.get('all_unique_moles', 0),
            'Top-1 Score': entry.get('avg_top1', None),
            'Hypervolume': entry.get('hypervolume', None),
            'Method': method_name
        })
    df = pd.DataFrame(records)
    df.dropna(inplace=True)
    df.sort_values(by='Evaluations', inplace=True)
    # 删除重复的评估点，保留最后一个（最新的）值
    df.drop_duplicates(subset=['Evaluations', 'Method'], keep='last', inplace=True)
    return df

def plot_and_save(df, value_column, title, ylabel, filename):
    """
    绘制给定指标的对比图并保存。
    """
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(10, 6))

    sns.lineplot(data=df, x='Evaluations', y=value_column, hue='Method', 
                 marker='o', ax=ax, linewidth=2.5)

    ax.set_title(title, fontsize=16, fontweight='bold')
    ax.set_xlabel('Number of Evaluations (Unique Solutions)', fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.tick_params(axis='both', which='major', labelsize=10)
    
    legend = ax.legend(title='Method', fontsize=11)
    plt.setp(legend.get_title(), fontsize='12')
    
    plt.tight_layout()
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"图像已保存到: {filename}")
    plt.show()

def main():
    # --- 从字符串解析数据 ---
    results_llm = parse_json_string(json_data_llm)
    results_ga = parse_json_string(json_data_ga)

    if results_llm is None or results_ga is None:
        print("缺少数据，程序退出。")
        return

    df_llm = extract_metrics(results_llm, 'MOLLM (Gemini 2.5)')
    df_ga = extract_metrics(results_ga, 'Baseline GA')
    
    # --- 合并数据 ---
    combined_df = pd.concat([df_llm, df_ga], ignore_index=True)

    # --- 绘制 Top-1 Score ---
    plot_and_save(
        df=combined_df,
        value_column='Top-1 Score',
        title='Top-1 Score vs. Number of Evaluations',
        ylabel='Average Top-1 Score',
        filename='top1_score_comparison_from_string.png'
    )

    # --- 绘制 Hypervolume ---
    plot_and_save(
        df=combined_df,
        value_column='Hypervolume',
        title='Hypervolume vs. Number of Evaluations',
        ylabel='Hypervolume (HV)',
        filename='hypervolume_comparison_from_string.png'
    )

if __name__ == '__main__':
    main()
