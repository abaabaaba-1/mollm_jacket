# 测试运行（不实际执行）
python run_all_baselines.py --dry-run

# 运行所有baseline，使用默认seed=42
python run_all_baselines.py

# 运行特定的baseline
python run_all_baselines.py --baselines ga sms nsga2

# 运行GA的多个seed
python run_all_baselines.py --baselines ga --seeds 42 43 44 45 46

# 运行所有baseline，每个5个不同的seed
python run_all_baselines.py --seeds 42 43 44 45 46


python main.py sacs_section_jk/config.yaml --seed 43

# 1️⃣ 测试运行（1分钟）
python run_all_baselines.py --problem geo_jk --baselines ga --dry-run

# 2️⃣ 单个baseline（2-3小时）
python run_all_baselines.py --problem geo_jk --baselines ga

# 3️⃣ 对比多个算法（6-9小时）
python run_all_baselines.py --problem geo_jk --baselines ga nsga2 sms

# 4️⃣ 所有baseline（10-15小时）
python run_all_baselines.py --problem geo_jk

# 5️⃣ 多随机种子统计（50-75小时）
python run_all_baselines.py --problem geo_jk --seeds 42 43 44 45 46


几何 JK（MOLLM 42/60/62/101，已删除旧文件）：已在宿舍运行
python3 run_all_baselines.py --problem geo_jk --algorithms mollm --seeds 42 60 62 101

几何 PF（MOLLM+基线 80/90/101 已清空）：80已运行
python3 run_all_baselines.py --problem geo_pf --algorithms mollm ga nsga2 sms --seeds 80 90 101
截面 PF（MOLLM+基线 80/90/101 已清空）：
python3 run_all_baselines.py --problem section_pf --algorithms mollm ga nsga2 sms --seeds 80 90 101
截面 JK（MOLLM seeds 42/43/44 已清空）：
python3 run_all_baselines.py --problem section_jk --algorithms mollm --seeds 42 43 44

git status
git add .
git commit -m "1221"
git push origin main