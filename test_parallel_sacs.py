# test_uc_extractor.py
"""
针对 sacs_interface_uc.py 模块的独立测试脚本。

该脚本旨在隔离并诊断 UC 值提取逻辑中可能存在的问题。
它通过创建模拟数据库和连接真实数据库两种方式，对 UCValueExtractor 类进行全面测试。

功能：
1. 测试在理想情况下的数据提取（使用手动创建的模拟数据库）。
2. 测试在无数据或数据库结构错误情况下的健壮性。
3. 尝试连接并从项目真实的数据库中提取数据，以重现并诊断实际遇到的问题。
4. 打印详细的调试信息，包括数据库路径、表结构和查询结果。
"""

import os
import sqlite3
import unittest
from pathlib import Path
import logging

# --- 导入待测试的模块 ---
# 确保此脚本可以找到 problem.sacs.sacs_interface_uc
try:
    from problem.sacs.sacs_interface_uc import UCValueExtractor
except ImportError:
    print("错误：无法导入 'problem.sacs.sacs_interface_uc'。请确保此脚本与 'problem' 目录在同一顶级目录下。")
    exit(1)

# --- 基本配置 ---
# !!! 重要：请将此路径修改为您SACS项目的真实路径 !!!
REAL_PROJECT_PATH = "/mnt/d/wsl_sacs_exchange/demo06_project/Demo06"
TEST_DB_NAME = "test_sacsdb.db"

# 配置日志，使其打印所有级别的消息
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger("UC_TESTER")


def setup_mock_db_with_data(db_path: Path):
    """创建一个包含模拟数据的测试数据库"""
    if db_path.exists():
        db_path.unlink()
    
    log.info(f"正在创建模拟数据库: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 创建与SACS数据库相似的表
    log.info("创建 R_POSTMEMBERRESULTS 表...")
    cursor.execute("""
    CREATE TABLE R_POSTMEMBERRESULTS (
        MemberName TEXT,
        MaxUC REAL,
        AxialUC REAL,
        YYBendingUC REAL,
        ZZBendingUC REAL,
        TotalShearUC REAL,
        VonMisesUC REAL,
        LocalBucklingUC REAL
    );
    """)

    # 插入一些模拟数据
    log.info("插入模拟数据...")
    mock_data = [
        ('MEMB01', 0.85, 0.4, 0.45, 0.3, 0.1, 0.7, 0.2),
        ('MEMB02', 1.15, 0.7, 0.45, 0.5, 0.2, 0.9, 0.6), # 一个超标的杆件
        ('MEMB03', 0.50, 0.2, 0.30, 0.2, 0.05, 0.4, 0.1),
        ('MEMB04', 0.95, 0.5, 0.45, 0.4, 0.15, 0.8, 0.3), # 一个高风险杆件
        ('MEMB01', 0.80, 0.3, 0.50, 0.2, 0.1, 0.7, 0.2), # 重复的杆件名，测试去重逻辑
        ('MEMB05', None, None, None, None, None, None, None), # 测试空值处理
        ('MEMB06', 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0), # 测试0值过滤
    ]
    cursor.executemany("INSERT INTO R_POSTMEMBERRESULTS VALUES (?, ?, ?, ?, ?, ?, ?, ?)", mock_data)

    conn.commit()
    conn.close()
    log.info("模拟数据库创建完毕。")


def setup_mock_db_empty(db_path: Path):
    """创建一个不包含目标表的空数据库"""
    if db_path.exists():
        db_path.unlink()
    
    log.info(f"正在创建空的模拟数据库: {db_path}")
    conn = sqlite3.connect(db_path)
    # 不创建任何表
    conn.close()
    log.info("空的模拟数据库已创建。")


class TestUCExtractor(unittest.TestCase):

    def setUp(self):
        """为每个测试用例设置环境"""
        self.test_dir = Path("./uc_test_workspace")
        self.test_dir.mkdir(exist_ok=True)

    def tearDown(self):
        """清理测试环境"""
        import shutil
        shutil.rmtree(self.test_dir)

    def test_01_extraction_with_mock_data(self):
        """测试1: 使用包含数据的模拟数据库进行提取"""
        log.info("\n" + "="*20 + " 测试1: 模拟数据提取 " + "="*20)
        db_path = self.test_dir / TEST_DB_NAME
        setup_mock_db_with_data(db_path)

        extractor = UCValueExtractor(work_dir=str(self.test_dir))
        # 强制指定测试数据库的路径
        extractor.db_path = db_path
        
        summary = extractor.get_uc_summary()
        
        self.assertEqual(summary['status'], 'success')
        self.assertAlmostEqual(summary['max_uc'], 1.15)
        self.assertEqual(summary['total_members'], 4) # 验证去重和0值过滤是否成功
        self.assertEqual(summary['critical_members'], 1)
        self.assertEqual(summary['high_risk_members'], 2) # MEMB01(0.85) 和 MEMB04(0.95)
        
        log.info(f"测试1结果: {summary}")
        log.info("测试1通过！")

    def test_02_extraction_with_empty_db(self):
        """测试2: 使用不包含目标表的数据库"""
        log.info("\n" + "="*20 + " 测试2: 空数据库处理 " + "="*20)
        db_path = self.test_dir / TEST_DB_NAME
        setup_mock_db_empty(db_path)

        extractor = UCValueExtractor(work_dir=str(self.test_dir))
        extractor.db_path = db_path

        summary = extractor.get_uc_summary()
        
        # 期望SQLite抛出 "no such table" 错误
        self.assertEqual(summary['status'], 'failed')
        self.assertIn('no such table: R_POSTMEMBERRESULTS', summary['error'])

        log.info(f"测试2结果: {summary}")
        log.info("测试2通过！")

    def test_03_extraction_with_no_db_file(self):
        """测试3: 数据库文件不存在的情况"""
        log.info("\n" + "="*20 + " 测试3: DB文件不存在 " + "="*20)
        non_existent_dir = self.test_dir / "non_existent"
        
        extractor = UCValueExtractor(work_dir=str(non_existent_dir))
        summary = extractor.get_uc_summary()

        self.assertEqual(summary['status'], 'failed')
        self.assertEqual(summary['error'], '未找到有效的UC数据')
        
        log.info(f"测试3结果: {summary}")
        log.info("测试3通过！")

    def test_04_real_db_investigation(self):
        """测试4: 诊断真实项目数据库"""
        log.info("\n" + "="*20 + " 测试4: 诊断真实数据库 " + "="*20)
        
        real_db_path = Path(REAL_PROJECT_PATH) / "sacsdb.db"
        if not real_db_path.exists():
            log.warning(f"真实数据库文件不存在: {real_db_path}。跳过此测试。")
            self.skipTest("真实数据库文件不存在")
        
        log.info(f"将使用真实的数据库: {real_db_path}")

        # 第一步：手动检查数据库结构
        log.info("--- 步骤 A: 手动检查表结构 ---")
        try:
            conn = sqlite3.connect(real_db_path)
            cursor = conn.cursor()
            
            # 列出所有表名
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            log.info(f"数据库中存在的表: {[t[0] for t in tables]}")
            
            # 检查 R_POSTMEMBERRESULTS 表是否存在
            if ('R_POSTMEMBERRESULTS',) in tables:
                log.info("表 'R_POSTMEMBERRESULTS' 存在。")
                # 查看该表的列信息
                cursor.execute("PRAGMA table_info(R_POSTMEMBERRESULTS);")
                columns = cursor.fetchall()
                log.info(f"'R_POSTMEMBERRESULTS' 的列定义: {[c[1] for c in columns]}")
                
                 # 查看该表中的前5行数据
                cursor.execute("SELECT * FROM R_POSTMEMBERRESULTS LIMIT 5;")
                sample_data = cursor.fetchall()
                if sample_data:
                    log.info(f"表中的示例数据 (前{len(sample_data)}行): {sample_data}")
                else:
                    log.warning("表 'R_POSTMEMBERRESULTS' 中没有数据！")
            else:
                log.error("关键错误: 表 'R_POSTMEMBERRESULTS' 不存在！")

            conn.close()
        except Exception as e:
            log.error(f"手动检查数据库失败: {e}")

        # 第二步：使用 extractor 模块进行提取
        log.info("\n--- 步骤 B: 使用 UCValueExtractor 模块进行提取 ---")
        extractor = UCValueExtractor(work_dir=REAL_PROJECT_PATH)
        # 我们直接调用内部方法以获得更详细的调试输出
        uc_data = extractor.extract_uc_values()

        # 打印详细的返回结果
        import json
        log.info("UCValueExtractor.extract_uc_values() 返回的完整结果:")
        log.info(json.dumps(uc_data, indent=2))
        
        log.info("\n--- 诊断结论 ---")
        if uc_data['summary']['total_members'] == 0:
            log.warning("诊断结果: 提取器未能从数据库中找到任何有效的UC记录。")
            log.warning("可能的原因：")
            log.warning("1. SACS分析因模型不稳定等原因，跳过了代码检查步骤，导致没有UC数据写入数据库。")
            log.warning("2. 查询语句 `SELECT ... FROM R_POSTMEMBERRESULTS WHERE MaxUC IS NOT NULL AND MaxUC > 0` 过滤掉了所有记录。")
            log.warning("请检查上面 '步骤 A' 中打印的表数据，确认 'MaxUC' 列是否全为 NULL 或 0。")
        else:
            log.info("诊断结果: 提取器似乎成功提取了数据。如果上层调用仍然失败，请检查上层逻辑。")
        
        # 这个测试没有硬性的断言，其主要目的是提供诊断信息
        self.assertIsNotNone(uc_data)


if __name__ == '__main__':
    unittest.main()
