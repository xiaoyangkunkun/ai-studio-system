#!/usr/bin/env python3
"""提取对话记录供 cron 使用。窗口可配:默认昨天 23:00 → 当前(晚间复盘用);
习惯整理(20:00 跑)传 --window-start 20,即昨天 20:00 → 当前,避免盲区。
输出到 stdout,cron 会将其注入 agent prompt。"""
import argparse
import sqlite3
import sys
import time
import datetime
import os

parser = argparse.ArgumentParser()
parser.add_argument('--window-start', type=int, default=23,
                    help='窗口起点小时(昨天该小时 → 当前)。复盘=23,习惯整理=20')
args = parser.parse_args()

DB = os.path.expanduser('~/.hermes/state.db')

now = datetime.datetime.now()
# 窗口起点 = 昨天指定小时
start_dt = (now - datetime.timedelta(days=1)).replace(hour=args.window_start, minute=0, second=0, microsecond=0)
start = start_dt.timestamp()
end = now.timestamp()

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()

rows = cur.execute("""
SELECT s.id, s.source, s.title, m.role, m.content, m.timestamp
FROM messages m JOIN sessions s ON s.id = m.session_id
WHERE m.timestamp >= ? AND m.timestamp < ?
  AND m.role IN ('user','assistant')
  AND m.content IS NOT NULL AND length(m.content) > 0
  AND s.source != 'cron'
ORDER BY s.id, m.timestamp
""", (start, end)).fetchall()

sessions = {}
for r in rows:
    sessions.setdefault(r['id'], []).append(r)

if not sessions:
    print("【今日对话提取】%s:今天暂无对话记录。" % now.strftime('%Y-%m-%d'))
    sys.exit(0)

print("【今日对话提取】%s,共 %d 个会话(窗口:%s 起)" % (now.strftime('%Y-%m-%d'), len(sessions), start_dt.strftime('%m-%d %H:%M')))
for sid, msgs in sessions.items():
    s = msgs[0]
    title = (s['title'] or sid)[:40]
    print("\n===== 会话: %s | 来源: %s =====\n" % (title, s['source']))
    for m in msgs:
        content = (m['content'] or '').strip()
        if not content:
            continue
        if m['role'] == 'user' and content.startswith('[IMPORTANT'):
            continue  # 跳过 cron 系统注入消息
        if m['role'] == 'assistant' and content.startswith('⚠ Auxiliary'):
            continue  # 跳过辅助模型报错
        if len(content) > 600:
            content = content[:600] + '…'
        t = time.strftime('%H:%M', time.localtime(m['timestamp']))
        print("[%s %s] %s" % (t, m['role'], content))
