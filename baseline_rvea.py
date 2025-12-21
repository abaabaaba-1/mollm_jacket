import sys
import os
import argparse
from typing import List

# ----------------- 路径修正代码 [开始] -----------------
project_root = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# ----------------- 路径修正代码 [结束] -----------------

from model.MOLLM import MOLLM, ConfigLoader
from baseline_ga import BaselineMOO
from model.util import rvea_selection


class RVEABaselineMOO(BaselineMOO):
    """Reference Vector Guided Evolutionary Algorithm (RVEA) style baseline."""

    def __init__(self, reward_system, llm, property_list, config, seed):
        super().__init__(reward_system, llm, property_list, config, seed)
        print("--- RVEA Baseline MOO has been activated (inherits ENHANCED BaselineMOO) ---")

    def select_next_population(self, pop_size: int) -> List:
        whole_population = [item[0] for item in self.mol_buffer if item[0].total is not None]
        if not whole_population:
            return []
        return rvea_selection(whole_population, pop_size)


class RVEABaselineRunner(MOLLM):
    def run(self):
        if self.resume:
            self.load_from_pkl(self.save_path)
        moo = RVEABaselineMOO(self.reward_system, self.llm, self.property_list, self.config, self.seed)
        init_pops, final_pops = moo.run()
        self.history.append(moo.history)
        self.final_pops.append(final_pops)
        self.init_pops.append(init_pops)
        print("\nRVEA baseline run finished.")


def main():
    parser = argparse.ArgumentParser(description='Run RVEA Baseline (config-driven).')
    parser.add_argument('config', type=str, nargs='?', default='sacs_geo_jk/config.yaml',
                        help='Path to the configuration file')
    parser.add_argument('--seed', type=int, default=43, help='Random seed for reproducibility')
    parser.add_argument('--resume', action='store_true', help='Resume training from the last checkpoint')
    args = parser.parse_args()

    cfg_path = args.config
    if cfg_path.startswith('problem/'):
        cfg_path = cfg_path[len('problem/'):]
    config = ConfigLoader(cfg_path)

    original_suffix = config.get('save_suffix', 'sacs_block_gen')
    config.config['save_suffix'] = f"{original_suffix}_baseline_RVEA"
    print(f"Results will be saved with suffix: {config.get('save_suffix')}")
    print(f"Eval budget (optimization.eval_budget) = {config.get('optimization.eval_budget')}")

    baseline_runner = RVEABaselineRunner(config=config, resume=args.resume, eval=False, seed=args.seed)
    baseline_runner.run()


if __name__ == "__main__":
    main()
