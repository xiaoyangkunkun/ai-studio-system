#!/usr/bin/env python3
"""夜间任务完成情况检查 - 6:00 AM 运行。
查询 executions.db 中 00:00-06:00 窗口内的执行记录，报告失败/异常。"""
import sqlite3, os, datetime, json

DB = os.path.expanduser('~/.hermes/cron/executions.db')
JOBS_FILE = os.path.expanduser('~/.hermes/cron/jobs.json')

if not os.path.exists(DB):
    print("[SILENT]")
    exit(0)

# 读取 job_id → name 映射
job_names = {}
if os.path.exists(JOBS_FILE):
    with open(JOBS_FILE) as f:
        data = json.load(f)
    jobs = data if isinstance(data, list) else data.get('jobs', [])
    for j in jobs:
        job_names[j.get('id', '')] = j.get('name', j.get('id', '')[:8])

now = datetime.datetime.now()
today = now.strftime('%Y-%m-%d')
window_start = f"{today}T00:00:00"
window_end = f"{today}T07:00:00"

conn = sqlite3.connect(DB)
cursor = conn.execute("""
    SELECT job_id, status, started_at, finished_at, error
    FROM executions
    WHERE claimed_at >= ? AND claimed_at < ?
    ORDER BY claimed_at
""", (window_start, window_end))

results = cursor.fetchall()
conn.close()

if not results:
    print("[SILENT]")
    exit(0)

failed = []
errors = []
completed = 0

for job_id, status, started, finished, error in results:
    name = job_names.get(job_id, job_id[:8])
    if status == 'completed':
        completed += 1
    elif status == 'failed':
        failed.append(f"❌ {name}: {error or '未知错误'}")
    else:
        errors.append(f"⚠️ {name}: 状态={status}")

if failed or errors:
    print(f"【夜间任务检查 🌙】{today}")
    print(f"✅ 完成: {completed} 个")
    if failed:
        print(f"❌ 失败: {len(failed)} 个")
        for f in failed:
            print(f"  {f}")
    if errors:
        print(f"⚠️ 异常: {len(errors)} 个")
        for e in errors:
            print(f"  {e}")
else:
    print(f"【夜间任务检查 🌙】{today}")
    print(f"全部完成 ✅（{completed} 个任务）")
