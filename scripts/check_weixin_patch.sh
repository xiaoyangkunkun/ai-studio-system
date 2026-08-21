#!/bin/bash
# 微信限流修复补丁检查/重打脚本 — Hermes 升级后运行
# 用法: bash check_weixin_patch.sh   (输出 OK=补丁在, REAPPLIED=已重打, NEEDS_HELP=异常)
set -e

FILE=/usr/local/lib/hermes-agent/gateway/platforms/weixin.py
PATCH=/root/backup/weixin-cooldown-wait.patch
MARK="2026-08-15 修复"

echo "=== 微信限流补丁检查 $(date '+%F %T') ==="

# 1. 文件存在?
if [ ! -f "$FILE" ]; then
  echo "❌ weixin.py 不存在,检查 Hermes 安装路径"
  exit 2
fi

# 2. 补丁是否还在
COUNT=$(grep -c "$MARK" "$FILE" || true)
if [ "$COUNT" -ge 2 ]; then
  echo "✅ 补丁已生效($COUNT 处标记),无需处理"
  exit 0
fi

# 3. 失效 → 备份并重打
echo "⚠️ 补丁失效(标记 $COUNT 处),开始重打..."
cp "$FILE" "/root/backup/weixin.py.bak-$(date +%Y%m%d-%H%M%S)"
cd /usr/local/lib/hermes-agent
if patch -p1 --dry-run < "$PATCH" >/dev/null 2>&1; then
  patch -p1 < "$PATCH"
  python3 -m py_compile gateway/platforms/weixin.py
  echo "✅ 补丁已重打,语法通过"
  echo "重启 gateway: echo \"bash /root/.hermes/scripts/restart_gw_once.sh\" | at now + 1 minute"
else
  echo "❌ 补丁无法干净应用(源码可能已变化),需人工处理:"
  echo "   diff /root/backup/weixin.py.bak-20260815-231323 $FILE | head -50"
  exit 3
fi
