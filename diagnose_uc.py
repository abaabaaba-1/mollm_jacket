# diagnose_uc.py
import logging
from problem.sacs.sacs_interface_uc import get_detailed_uc_analysis

# 配置日志，以便看到详细输出
logging.basicConfig(level=logging.INFO)

def find_max_bending_culprit():
    """
    分析SACS数据库，找出导致最高弯曲UC的构件。
    """
    print("--- 开始诊断：寻找最大弯曲UC的来源 ---")
    
    # 确保此处的路径是正确的
    sacs_project_path = "/mnt/d/wsl_sacs_exchange/demo06_project/Demo06" 
    
    # 使用我们已有的工具来获取详细的UC数据
    detailed_uc_res = get_detailed_uc_analysis(sacs_project_path)

    if not detailed_uc_res or detailed_uc_res.get('status') != 'success':
        print("错误：无法获取详细的UC分析结果。请确保SACS已成功运行并且sacsdb.db文件存在。")
        return

    member_data = detailed_uc_res.get('member_uc', {})
    if not member_data:
        print("错误：未在数据库中找到任何杆件的UC数据。")
        return

    max_bending_uc = -1
    culprit_member = None

    # 遍历所有构件，找到弯曲UC最高的那个
    for member_name, data in member_data.items():
        current_bending_uc = max(data.get('yy_bending_uc', 0.0), data.get('zz_bending_uc', 0.0))
        if current_bending_uc > max_bending_uc:
            max_bending_uc = current_bending_uc
            culprit_member = {
                'name': member_name,
                **data
            }

    if culprit_member:
        print("\n--- 诊断结果 ---")
        print(f"最大弯曲UC的来源构件是: {culprit_member['name']}")
        print(f"最大弯曲UC (bending_uc_max): {max_bending_uc:.6f}")
        print("\n详细UC分量:")
        print(f"  - max_uc:            {culprit_member['max_uc']:.6f}")
        print(f"  - axial_uc:          {culprit_member['axial_uc']:.6f}")
        print(f"  - yy_bending_uc:     {culprit_member['yy_bending_uc']:.6f}")
        print(f"  - zz_bending_uc:     {culprit_member['zz_bending_uc']:.6f}")

        print("\n请检查此构件属于哪个GRUP，并确认该GRUP是否在config.yaml的'optimizable_blocks'列表中。")
    else:
        print("未找到任何有效的弯曲UC数据。")

if __name__ == "__main__":
    # 运行一次基准模型的SACS分析，然后运行此脚本
    find_max_bending_culprit()
