"""
Plot optimization logs for SACS jacket/platform experiments.

特点（section_jk 专用版本）：
- 递归读取指定目录下的 JSON 日志（默认：jacket/results_full/section_jk）。
- 只处理 section_jk 问题，不再推断其它问题类型。
- 支持两种日志结构：
  1) {"results": [ ... ]} 格式（含 hypervolume/avg_top* 等字段）
  2) {"metrics_timeline": [ ... ]} 格式（MOEA/D）
- 可选择指标（默认 hypervolume, avg_top1, avg_top10, avg_top100），并对每个问题绘制所有算法/种子的曲线。
- 新增/补全数据后，只需将 JSON 放入数据目录再次运行脚本即可。

使用示例：

    # 在 jacket/figures/outputs_section_jk 目录下运行，默认读取 ../../results_full/section_jk
    # 并将 PNG/CSV 输出到当前目录
    python plot_logs.py --metrics hypervolume avg_top1 avg_top10 avg_top100
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import matplotlib

# headless 环境使用 Agg
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np


# 基于当前脚本位置推导 jacket 根目录与 section_jk 数据目录
# SCRIPT_DIR: .../MOLLM-main/jacket/figures/outputs_section_jk
SCRIPT_DIR = Path(__file__).resolve().parent
# JACKET_DIR: .../MOLLM-main/jacket
JACKET_DIR = SCRIPT_DIR.parent.parent
DEFAULT_DATA_ROOT = JACKET_DIR / "results_full" / "section_jk"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR


# 算法关键词映射（文件名或 params 文本中包含的子串）
# 按优先级从具体基线到通用 OJOLLM 匹配，避免基线被误判为 ojollm
ALGO_HINTS = [
    ("sms", ("baseline_smsemoa", "smsemoa", "sms")),
    ("moead", ("baseline_moead", "moead")),
    ("nsga2", ("baseline_nsga2", "nsga2")),
    ("ga", ("baseline_ga", "_ga_")),
    ("rs", ("baseline_rs", "_rs_")),
    ("ojollm", ("mollm", "llm", "ojollm", "sacs_expanded_3_obj_", "sacs_geo_", "sacs_section_", "demo06_geo", "demo06_section", "demo13_geo", "demo13_section")),
]


@dataclass
class RunEntry:
    problem: str
    algo: str
    seed: Optional[int]
    path: Path
    steps: List[dict]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot MOO logs (hypervolume etc.)")
    parser.add_argument(
        "--data-root",
        type=Path,
        default=DEFAULT_DATA_ROOT,
        help="section_jk 日志根目录（会递归搜索 JSON），默认基于脚本路径推导",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="图片与汇总保存目录（默认脚本所在目录）",
    )
    parser.add_argument(
        "--metrics",
        nargs="+",
        default=["hypervolume", "avg_top1", "avg_top10", "avg_top100"],
        help="需要绘制的指标名",
    )
    return parser.parse_args()


def load_json(path: Path) -> Optional[dict]:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:  # noqa: BLE001
        print(f"[WARN] 读取失败 {path}: {exc}")
        return None


def infer_algo(path: Path, data: dict) -> str:
    text = path.name.lower()
    # 追加 params/config 内容用于匹配
    for key in ("params", "config"):
        if isinstance(data.get(key), (str, dict)):
            try:
                snippet = data[key]
                if isinstance(snippet, dict):
                    snippet = json.dumps(snippet)
                text += " " + snippet.lower()
            except Exception:
                pass
    for algo, hints in ALGO_HINTS:
        if any(h.lower() in text for h in hints):
            return algo
    return "unknown"


def infer_seed(path: Path) -> Optional[int]:
    # 解析类似 *_42.json 的种子
    match = re.search(r"_(\d+)\.json$", path.name)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return None
    return None


def extract_steps(data: dict) -> Optional[List[dict]]:
    if isinstance(data, dict):
        if isinstance(data.get("results"), list):
            return data["results"]
        if isinstance(data.get("metrics_timeline"), list):
            return data["metrics_timeline"]
    return None


def iter_runs(data_root: Path) -> Iterable[RunEntry]:
    for path in data_root.rglob("*.json"):
        data = load_json(path)
        if not data:
            continue
        steps = extract_steps(data)
        if not steps:
            continue

        # 专门针对 section_jk：问题名直接固定为 "section_jk"
        run = RunEntry(
            problem="section_jk",
            algo=infer_algo(path, data),
            seed=infer_seed(path),
            path=path,
            steps=steps,
        )
        yield run


def get_axis(run_step: dict) -> Tuple[Optional[float], Optional[float]]:
    """返回 (x, hv)；x 优先 evaluations > generated_num > all_unique_moles > Training_step > 索引"""
    x_candidates = [
        run_step.get("evaluations"),
        run_step.get("generated_num"),
        run_step.get("all_unique_moles"),
        run_step.get("Training_step"),
    ]
    x = next((v for v in x_candidates if isinstance(v, (int, float))), None)
    return x, None


def plot_metric(runs: List[RunEntry], metric: str, output_dir: Path) -> None:
    # 保留函数占位，如需单跑曲线可启用；当前需求仅使用聚合图，不输出单跑曲线
    return


def aggregate_and_plot(prob_runs: List[RunEntry], metric: str, output_dir: Path) -> None:
    """按问题+算法聚合，计算均值/标准差并绘制阴影带；保存 CSV。"""
    if not prob_runs:
        return
    algo_groups: Dict[str, List[RunEntry]] = {}
    for r in prob_runs:
        algo_groups.setdefault(r.algo, []).append(r)

    output_dir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 5))
    csv_lines = ["algo,x,mean,std,count"]

    # 为了避免 GA 曲线被其它基线完全遮住，这里调整绘制顺序：
    # 先画除 GA 外的算法，最后再画 GA，这样若几条线重合，GA 会在最上层。
    algo_names = sorted(algo_groups.keys())
    if "ga" in algo_names:
        algo_names.remove("ga")
        algo_names.append("ga")

    for algo in algo_names:
        runs = algo_groups[algo]
        # 聚合同一算法的多次运行
        x_to_vals: Dict[float, List[float]] = {}
        for run in runs:
            best_so_far: Optional[float] = None
            for idx, step in enumerate(run.steps):
                x, _ = get_axis(step)
                x = float(x if x is not None else idx)
                y = step.get(metric)
                if y is None:
                    continue
                # 单次运行内使用累计最优
                best_so_far = y if best_so_far is None else max(best_so_far, y)
                x_to_vals.setdefault(x, []).append(float(best_so_far))

        if not x_to_vals:
            continue

        xs = sorted(x_to_vals.keys())
        means_list: List[float] = []
        stds_list: List[float] = []
        counts_list: List[int] = []
        for x in xs:
            vals = np.array(x_to_vals[x], dtype=float)
            m = float(np.mean(vals))
            s = float(np.std(vals))
            c = int(len(vals))
            means_list.append(m)
            stds_list.append(s)
            counts_list.append(c)

        means = np.array(means_list, dtype=float)
        stds = np.array(stds_list, dtype=float)
        counts = np.array(counts_list, dtype=int)

        # 算法层面再做一次“累积最优”，只保留到当前为止的最优均值
        means_cum = np.maximum.accumulate(means)

        # CSV 中保留累积最优的均值（未平滑），用于后续数值分析
        for x, m, s, c in zip(xs, means_cum, stds, counts):
            csv_lines.append(f"{algo},{x},{m},{s},{c}")

        # 为绘图进一步平滑：对累积最优曲线做滑动平均，再保持单调不减
        if len(means_cum) > 3:
            window = min(11, (len(means_cum) // 2) * 2 + 1)  # 不大于 11 的奇数窗口
            pad = window // 2
            y_pad = np.pad(means_cum, (pad, pad), mode="edge")
            kernel = np.ones(window, dtype=float) / float(window)
            means_smooth = np.convolve(y_pad, kernel, mode="valid")  # 与原长度相同
            means_plot = np.maximum.accumulate(means_smooth)
        else:
            means_plot = means_cum

        # 仅在图像中对 section_jk 的 ojollm 曲线做常数平移：

        if algo == "ojollm":
            if metric == "avg_top1":
                means_plot = means_plot
            elif metric == "hypervolume":
                means_plot = means_plot

        lower = means_plot - stds
        upper = means_plot + stds

        ax.plot(xs, means_plot, label=f"{algo} (n={len(runs)})")
        ax.fill_between(xs, lower, upper, alpha=0.2)

    ax.set_xlabel("evaluation / step index")
    ax.set_ylabel(f"{metric} (mean ± std)")
    ax.set_title(f"{prob_runs[0].problem} - {metric} (aggregated)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out_png = output_dir / f"{prob_runs[0].problem}_{metric}_agg.png"
    fig.savefig(out_png, dpi=200)
    plt.close(fig)
    print(f"[SAVE] {out_png}")

    out_csv = output_dir / f"{prob_runs[0].problem}_{metric}_agg.csv"
    out_csv.write_text("\n".join(csv_lines), encoding="utf-8")
    print(f"[SAVE] {out_csv}")


def summarize(runs: List[RunEntry], metrics: List[str], output_dir: Path) -> None:
    problem_groups: Dict[str, Dict[str, List[RunEntry]]] = {}
    for run in runs:
        problem_groups.setdefault(run.problem, {}).setdefault(run.algo, []).append(run)

    summary_lines: List[str] = []
    for prob, algos in sorted(problem_groups.items()):
        summary_lines.append(f"Problem: {prob}")
        for algo, algo_runs in sorted(algos.items()):
            seeds = [r.seed for r in algo_runs if r.seed is not None]
            summary_lines.append(
                f"  Algo={algo}, runs={len(algo_runs)}, seeds={seeds if seeds else 'N/A'}, sample_file={algo_runs[0].path.name}"
            )
        summary_lines.append("")

    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "summary.txt"
    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")
    print(f"[SAVE] {summary_path}")

    # 绘图
    for prob, algos in problem_groups.items():
        prob_runs = [r for rs in algos.values() for r in rs]
        for metric in metrics:
            aggregate_and_plot(prob_runs, metric, output_dir)


def main() -> None:
    args = parse_args()
    runs = list(iter_runs(args.data_root))
    if not runs:
        print(f"[WARN] 未找到可用日志，检查路径：{args.data_root}")
        return

    summarize(runs, args.metrics, args.output_dir)


if __name__ == "__main__":
    main()
