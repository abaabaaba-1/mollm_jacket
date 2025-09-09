#
# test_weight_calculation.py
#
import os
import sys
import logging
import time

# --- 设置环境，以便可以导入 problem/sacs 目录下的模块 ---
# 假设此脚本在项目根目录
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(current_dir) 
except:
    # 兼容一些无法获取__file__的环境
    sys.path.append(os.getcwd())

# --- 配置日志，方便查看详细信息 ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')

# --- 关键配置：修改为您的本地 SACS 项目路径 ---
SACS_PROJECT_PATH = "/mnt/d/wsl_sacs_exchange/demo06_project/Demo06"

def run_test():
    """
    运行测试，对比新旧两种重量/体积计算方法。
    """
    start_time = time.time()
    print("\n" + "=" * 60)
    print("  SACS 重量/体积计算方法对比测试 (最终版)  ")
    print("=" * 60)
    print(f"测试项目路径: {SACS_PROJECT_PATH}\n")

    # 检查项目路径是否存在
    if not os.path.isdir(SACS_PROJECT_PATH):
        print(f"错误: 项目路径 '{SACS_PROJECT_PATH}' 不存在。请修改脚本中的 SACS_PROJECT_PATH。")
        return

    # --- 导入要测试的模块 ---
    try:
        from problem.sacs.sacs_interface_weight import calculate_sacs_volume
        from problem.sacs.sacs_interface_weight_improved import calculate_sacs_weight_from_db
    except ImportError as e:
        print(f"错误: 无法导入计算模块。请确保 test_weight_calculation.py 的位置正确，")
        print(f"并且 'problem/sacs/' 目录下存在 'sacs_interface_weight.py' 和 'sacs_interface_weight_improved.py'。")
        print(f"详细错误: {e}")
        return

    # --- 测试旧方法 ---
    print("\n--- 1. 测试旧方法 (基于 sacinp.demo06 几何解析) ---")
    old_volume = None
    try:
        old_method_result = calculate_sacs_volume(SACS_PROJECT_PATH)
        if old_method_result.get("status") == "success":
            old_volume = old_method_result.get("total_volume_m3", 0)
            print(f"  [成功] 旧方法计算结果: {old_volume:.6f} m^3")
        else:
            print(f"  [失败] 旧方法执行失败: {old_method_result.get('error')}")
    except Exception as e:
        logging.exception("  [异常] 旧方法执行时发生严重错误:")


    # --- 测试新方法 ---
    print("\n--- 2. 测试新方法 (基于 sacsdb.db + 精确公式) ---")
    new_volume = None
    try:
        new_method_result = calculate_sacs_weight_from_db(SACS_PROJECT_PATH)
        if new_method_result.get("status") == "success":
            new_volume = new_method_result.get("total_volume_m3", 0)
            print(f"  [成功] 新方法计算结果: {new_volume:.6f} m^3")
            print(f"         (数据库中总杆件数: {new_method_result.get('total_members_in_db')}, "
                  f"成功处理杆件数: {new_method_result.get('processed_members')})")
        else:
            print(f"  [失败] 新方法执行失败: {new_method_result.get('error')}")
    except Exception as e:
        logging.exception("  [异常] 新方法执行时发生严重错误:")


    # --- 对比结果 ---
    print("\n" + "=" * 60)
    print("  对比分析  ")
    print("=" * 60)

    if old_volume is not None and new_volume is not None:
        difference = new_volume - old_volume
        if old_volume > 0:
            percentage_diff = (difference / old_volume) * 100
        else:
            percentage_diff = float('inf')

        print(f"旧方法 (近似公式): {old_volume:.6f} m^3")
        print(f"新方法 (精确公式): {new_volume:.6f} m^3")
        print("-" * 30)
        print(f"绝对差异: {difference:.6f} m^3")
        print(f"相对差异: {percentage_diff:+.2f}%")

        print("\n分析:")
        print("1. 差异主要来自管状截面面积公式: 旧(πDt) vs 新(πt(D-t))。新公式更精确。")
        print("2. 新方法直接使用数据库中的杆件长度，避免了自己解析几何可能引入的误差。")
        print("=> 结论: 新方法的结果在物理上更精确，是后续优化的可靠基准。")

    else:
        print("\n无法进行对比，因为至少有一种方法未能成功计算出结果。")
    
    end_time = time.time()
    print(f"\n测试总耗时: {end_time - start_time:.2f} 秒。")

# 确保 run_test 函数在顶层，并且能被调用
if __name__ == "__main__":
    run_test()
