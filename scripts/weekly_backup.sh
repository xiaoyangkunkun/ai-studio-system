#!/bin/bash
# 每周自动备份 wrapper:成功静默(不推送),失败告警推送
LOG=~/backup/backup.log
if bash ${HERMES_HOME:-$HOME/.hermes}/scripts/backup_all.sh >> "$LOG" 2>&1; then
    # 成功:保持静默(no_agent 模式空输出 = 不打扰)
    :
else
    echo "【备份失败 ⚠️】$(date '+%Y-%m-%d %H:%M') 备份脚本出错,详见 ~/backup/backup.log"
fi
