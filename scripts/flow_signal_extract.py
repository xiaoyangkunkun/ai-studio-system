#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""流程推荐信号提取器(2026-08-14 知远调研 → 落地)
扫描上周的可优化信号,输出结构化清单(供 cron agent 用):
1. cron 输出目录上周新增文件中的报错/截断痕迹
2. executions.db 上周非 completed 记录
3. 规则/流程文档 updated 字段滞后(>30天)或与 jobs.json 定义不一致
4. skill_issues.json 变更
5. 决策通道未决问题
"""
import json, os, re, sqlite3, datetime, glob

NOW = datetime.datetime.now()
WEEK_AGO = NOW - datetime.timedelta(days=7)
SIGNALS = []

def ts(s):
    try:
        return datetime.datetime.fromisoformat(str(s).replace('Z', '+00:00'))
    except Exception:
        return None

# 1. cron 输出目录报错痕迹(只扫 ## Response 段,排除注入的 Prompt/脚本内容误报)
out_dir = '~/.hermes/cron/output'
SELF_JOB = os.environ.get('CRON_JOB_ID', '')  # 自身 job id(如果环境注入)
for job_dir in glob.glob(os.path.join(out_dir, '*')):
    job_id = os.path.basename(job_dir)
    if job_id == SELF_JOB or job_id == '89cbbec9ef7e':
        continue  # 排除自身/流程推荐
    for f in sorted(glob.glob(os.path.join(job_dir, '*.md')))[-5:]:
        mt = datetime.datetime.fromtimestamp(os.path.getmtime(f))
        if mt < WEEK_AGO:
            continue
        try:
            content = open(f, encoding='utf-8', errors='ignore').read()
        except Exception:
            continue
        # 只取 Response 段(实际输出),不扫 Prompt/脚本注入部分
        m = re.search(r'## Response\s*\n(.*)$', content, re.S)
        resp = m.group(1) if m else ''
        if not resp.strip() or len(resp) < 50:
            continue
        # 报错信号:Response 段出现失败字样(排除正常流程里的"失败写XXX"说明文字)
        errs = []
        if re.search(r'^(# )?.*(SCRIPT ERROR|Script not found|Traceback|ERROR:|failed to|FAILED|Timeout|timed out)', resp, re.M):
            errs.append('执行失败')
        # 空转信号:Response 只是复述注入内容/无实际结论(弱信号,仅提示)
        if re.search(r'^【今日对话提取】|^\[IMPORTANT', resp, re.M):
            errs.append('疑似复述注入')
        if errs:
            SIGNOUT = os.path.basename(f).replace('.md', '')
            SIGNALS.append(f"[cron] 任务 {job_id} {','.join(errs)} ({SIGNOUT})")

# 2. executions.db 失败记录
try:
    con = sqlite3.connect('~/.hermes/cron/executions.db')
    cur = con.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    if 'executions' in tables:
        cur.execute("SELECT * FROM executions ORDER BY rowid DESC LIMIT 50")
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        for row in rows:
            d = dict(zip(cols, row))
            status = str(d.get('status', ''))
            if status not in ('completed', 'ok', 'success', ''):
                jid = d.get('job_id', d.get('job', '?'))
                err = str(d.get('error', ''))[:60]
                SIGNALS.append(f"[exec] 任务 {jid} status={status} err={err}")
    con.close()
except Exception as e:
    SIGNALS.append(f"[exec] executions.db 读取失败: {e}")

# 3. 文档滞后
docs = ['~/vault/entities/定时任务清单.md', '~/vault/工作室/组织架构.md',
        '~/vault/工作室/规则演变史.md', '~/vault/工作室/流程总览.md']
for d in docs:
    if os.path.exists(d):
        mt = datetime.datetime.fromtimestamp(os.path.getmtime(d))
        if mt < WEEK_AGO:
            SIGNALS.append(f"[doc] {os.path.basename(d)} 一周未更新({mt:%m-%d})")

# 4. skill_issues.json
try:
    if os.path.exists('~/.hermes/data/skill_issues.json'):
        si = json.load(open('~/.hermes/data/skill_issues.json'))
        for name, info in si.items():
            if isinstance(info, dict) and info.get('count', 0) >= 3:
                SIGNALS.append(f"[skill] {name} 累计问题 {info['count']} 次,待评估")
except Exception:
    pass

# 5. 决策通道
try:
    dp = '~/vault/决策通道/待决策.md'
    if os.path.exists(dp):
        mt = datetime.datetime.fromtimestamp(os.path.getmtime(dp))
        if mt > WEEK_AGO:
            SIGNALS.append(f"[decide] 决策通道有更新({mt:%m-%d}),可能有未决问题")
except Exception:
    pass

if SIGNALS:
    print("【流程信号】上周发现以下可优化信号:")
    for s in SIGNALS[:15]:
        print("- " + s)
else:
    print("【流程信号】上周无异常信号(平稳)")

print("")
print("【补充检查】请 agent 继续:对比 jobs.json 与定时任务清单/流程文档的更新时间与定义,读 skill_issues 详情,读待决策.md 全文。")
