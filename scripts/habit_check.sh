#!/usr/bin/env bash
# 习惯体检 wrapper:输出画像现状摘要供体检 agent 分析(script 字段只能纯名,参数写死在此)
cd ~/.hermes/scripts
echo "===== 画像现状 ====="
python3 -c "
import re
t = open('~/vault/entities/用户画像.md', encoding='utf-8').read()
m = re.search(r'## ✅ 已确认的习惯与要求\n(.*?)(?=\n## |\Z)', t, re.S)
sec = m.group(1) if m else ''
lines = [l for l in sec.split('\n') if l.strip()]
print(f'已确认习惯: {len(lines)} 条')
print()
print(t[:3000])
print('...(截断,完整见 ~/vault/entities/用户画像.md)')
"
echo ""
echo "===== 基线信息 ====="
python3 habit_baseline.py check
