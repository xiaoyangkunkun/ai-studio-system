#!/usr/bin/env python3
"""生成定时任务清单到 vault(每晚自动更新)。读取 ~/.hermes/cron/jobs.json。"""
import json, os, datetime

JOBS = os.path.expanduser('${HOME}/.hermes/cron/jobs.json')
OUT = '${VAULT_PATH:-/root/vault}/entities/定时任务清单.md'

d = json.load(open(JOBS, encoding='utf-8'))
jobs = d.get('jobs', []) if isinstance(d, dict) else d

def fmt_time(ts):
    if not ts:
        return '-'
    try:
        return str(ts)[:16].replace('T', ' ')
    except Exception:
        return str(ts)[:16]

def job_type(j):
    if j.get('no_agent') and j.get('script'):
        return '脚本'
    if j.get('script'):
        return '脚本+AI'
    return 'AI 任务'

def job_state(j):
    if not j.get('enabled', True):
        return '⏸ 暂停'
    st = j.get('state', '')
    if st == 'completed':
        return '✅ 已完成'
    if st == 'paused':
        return '⏸ 暂停'
    if j.get('repeat') == 'once' and j.get('last_run_at'):
        return '✅ 已完成'
    return '🟢 运行中'

def schedule_human(j):
    sd = j.get('schedule_display') or j.get('schedule') or '-'
    return sd

now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
active = [j for j in jobs if job_state(j) == '🟢 运行中']
inactive = [j for j in jobs if job_state(j) != '🟢 运行中']

lines = ['---', 'title: 定时任务清单', f'created: {now[:10]}', f'updated: {now[:10]}',
         'type: entity', 'tags: [工具, 效率]', 'sources: []', '---', '',
         '# ⏰ 定时任务清单', '',
         f'> 自动生成: {now} | 任务总数: **{len(jobs)}**(运行中 {len(active)})',
         '> 每晚更新。任务定义在服务器 ~/.hermes/cron/jobs.json。', '', ]

lines += ['## 🟢 运行中', '', '| 任务 | 时间 | 类型 | 状态 | 下次运行 |', '|---|---|---|---|---|']
for j in sorted(active, key=lambda x: x.get('next_run_at') or ''):
    lines.append(f"| **{j.get('name','?')}** | {schedule_human(j)} | {job_type(j)} | {job_state(j)} | {fmt_time(j.get('next_run_at'))} |")
lines += ['', '---', '', '## ⏸ 暂停/已完成', '']
if inactive:
    lines.append('| 任务 | 时间 | 类型 | 状态 | 上次运行 |')
    lines.append('|---|---|---|---|---|')
    for j in sorted(inactive, key=lambda x: x.get('name') or ''):
        lines.append(f"| **{j.get('name','?')}** | {schedule_human(j)} | {job_type(j)} | {job_state(j)} | {fmt_time(j.get('last_run_at'))} |")
else:
    lines.append('(无)')
lines += ['', '---', '', '**相关笔记**:[[index]] · [[能力目录]] · [[知识库目录]]', '']

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print(f'OK 定时任务清单已更新: {len(jobs)} 个任务(运行中 {len(active)}) -> {OUT}')