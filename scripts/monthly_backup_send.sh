#!/bin/bash
# 每月备份并打包为单个 tar.gz,输出文件路径(供 cron agent 发送到微信)
OUT=/root/backup
LOG=$OUT/monthly.log

echo "[$(date '+%Y-%m-%d %H:%M')] 开始每月备份..." >> "$LOG"
if bash /root/.hermes/scripts/backup_all.sh >> "$LOG" 2>&1; then
    LATEST=$(ls -dt "$OUT"/hermes-backup-* 2>/dev/null | head -1)
    if [ -n "$LATEST" ]; then
        PKG="$OUT/hermes-backup-monthly-$(date +%Y%m%d).tar.gz"
        tar czf "$PKG" -C "$OUT" "$(basename "$LATEST")"
        echo "[$(date '+%Y-%m-%d %H:%M')] 打包完成: $PKG" >> "$LOG"
        # 只保留最近 2 个月度包,避免堆积
        ls -t "$OUT"/hermes-backup-monthly-*.tar.gz 2>/dev/null | tail -n +3 | xargs -r rm -f
        echo "$PKG"
    else
        echo "ERROR: 找不到备份目录"
    fi
else
    echo "ERROR: 备份脚本执行失败,详见 $LOG"
fi
