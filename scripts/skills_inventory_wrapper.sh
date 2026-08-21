#!/bin/bash
# 每晚更新:能力目录 + 知识库目录 + 定时任务清单 + 技能库镜像:成功静默,失败告警
LOG=~/backup/inventory.log
PY=/usr/local/lib/hermes-agent/venv/bin/python3
if $PY ${HERMES_HOME:-$HOME/.hermes}/scripts/skills_inventory.py >> "$LOG" 2>&1 \
   && $PY ${HERMES_HOME:-$HOME/.hermes}/scripts/kb_inventory.py >> "$LOG" 2>&1 \
   && $PY ${HERMES_HOME:-$HOME/.hermes}/scripts/cron_inventory.py >> "$LOG" 2>&1 \
   && /usr/local/lib/hermes-agent/venv/bin/python3 ${HERMES_HOME:-$HOME/.hermes}/scripts/mirror_skills.py >> "$LOG" 2>&1; then
    :  # 成功:静默
else
    echo "【目录更新失败 ⚠️】$(date '+%Y-%m-%d %H:%M') 详见 $LOG"
fi
