#!/usr/bin/env bash
# 规则体检 wrapper:输出规则文档清单+更新时间,供体检 agent 分析
cd ${VAULT_PATH:-/root/vault}/工作室
echo "===== 规则文档清单(更新时间) ====="
ls -lt ${VAULT_PATH:-/root/vault}/工作室/*.md ${VAULT_PATH:-/root/vault}/工作室/员工/*.md 2>/dev/null | awk '{print $6, $7, $8, $NF}'
echo ""
echo "===== cron 任务数 ====="
python3 -c "
import json
with open('/root/.hermes/cron/jobs.json') as f:
    data = json.load(f)
jobs = data['jobs']
print(f'共 {len(jobs)} 个定时任务')
for j in sorted(jobs, key=lambda x: x.get('schedule_display','')):
    print(f\"  {j.get('name','?')}: {j.get('schedule_display','')}\")
" 2>&1 | head -25
echo ""
echo "===== 员工守则文件 ====="
ls ${VAULT_PATH:-/root/vault}/工作室/员工/ 2>/dev/null