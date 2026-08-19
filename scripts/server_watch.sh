#!/bin/bash
# 服务器健康监控 — 只在异常时输出告警(输出为空 = 安静)
# Hermes cron no_agent watchdog 模式:非空 stdout 原样投递
LC_ALL=C
ALERTS=""

# --- 内存:使用率 > 90% 告警 ---
read total used <<<$(free -m | awk '/^Mem:/{print $2, $3}')
if [ -n "$total" ] && [ "$total" -gt 0 ]; then
  pct=$((used * 100 / total))
  if [ "$pct" -ge 90 ]; then
    ALERTS="${ALERTS}⚠️ 内存使用率 ${pct}% (${used}MB/${total}MB)\n"
  fi
fi

# --- 磁盘:根分区使用率 > 85% 告警 ---
read dpct dused davail <<<$(df -m / | awk 'NR==2{print $5, $3, $4}')
dpct=${dpct%\%}
if [ -n "$dpct" ] && [ "$dpct" -ge 85 ]; then
  ALERTS="${ALERTS}⚠️ 磁盘使用率 ${dpct}% (已用${dused}MB/可用${davail}MB)\n"
fi

# --- 负载:1分钟负载 > 4.0(2核)告警 ---
load1=$(awk '{print $1}' /proc/loadavg)
if awk -v l="$load1" 'BEGIN{exit !(l>4.0)}'; then
  ALERTS="${ALERTS}⚠️ 系统负载偏高: ${load1}\n"
fi

# --- 输出 ---
if [ -n "$ALERTS" ]; then
  echo "【服务器告警 $(date '+%m-%d %H:%M')】"
  echo -e "$ALERTS"
  echo "请检查服务器状态: systemctl status hermes-gateway hermes-dashboard"
fi
