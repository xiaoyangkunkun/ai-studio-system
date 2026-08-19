#!/usr/bin/env bash
# 习惯整理 wrapper v2:先做基线校验(防覆盖体检成果),再提取对话
# 背景:2026-08-14 体检机制配套——指纹基线,任何画像改动(hash 变)都会锁定旧条目
cd ~/.hermes/scripts

echo "===== 基线校验 ====="
python3 habit_baseline.py check

echo ""
echo "===== 今日对话提取 ====="
python3 daily_chat_extract.py --window-start 2
