#!/bin/bash
# 知识库健康度三件套扫描
# 每晚3:00运行，汇总结果

echo "=== 知识库健康度扫描 ==="
echo "时间: $(date '+%Y-%m-%d %H:%M')"
echo ""

# 1. 隐藏关联发现
echo "--- 1. 隐藏关联发现 ---"
python3 ${HERMES_HOME:-$HOME/.hermes}/scripts/hidden_connections.py 2>&1
echo ""

# 2. 知识健康度指标
echo "--- 2. 知识健康度指标 ---"
python3 ${HERMES_HOME:-$HOME/.hermes}/scripts/health_report.py 2>&1
echo ""

# 3. Graph快照追踪
echo "--- 3. Graph快照追踪 ---"
python3 ${HERMES_HOME:-$HOME/.hermes}/scripts/graph_snapshot.py 2>&1
echo ""

# 读取最新健康度评分
LATEST_HEALTH=$(cat ${VAULT_PATH:-$HOME/vault}/wiki/analytics/health-report-latest.json 2>/dev/null)
SCORE=$(echo "$LATEST_HEALTH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('score','N/A'))" 2>/dev/null)
GRADE=$(echo "$LATEST_HEALTH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('grade','N/A'))" 2>/dev/null)

# 读取隐藏关联数
LATEST_CONNECTIONS=$(cat ${VAULT_PATH:-$HOME/vault}/wiki/analytics/hidden-connections-latest.json 2>/dev/null)
CONN_COUNT=$(echo "$LATEST_CONNECTIONS" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('recommendations',[])))" 2>/dev/null)

echo "=== 扫描完成 ==="
echo "健康度: $SCORE/100 $GRADE"
echo "隐藏关联: $CONN_COUNT 个"
