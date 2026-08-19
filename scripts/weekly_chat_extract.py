#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""周复盘预收集脚本(2026-08-15 深度重构):把周复盘要用的数据一次性提取注入 prompt,
agent 只做分析判断和输出,不再逐个翻文件。输出到 stdout,cron 注入。
窗口:7 天整窗(上周日 0:00 → 周六 24:00),周日凌晨 0:45 跑,老大白天醒来即可查看。"""
import sqlite3
import sys
import time
import datetime
import os
import re
import glob

VAULT = '~/vault'
DB = os.path.expanduser('~/.hermes/state.db')
now = datetime.datetime.now()

# ---------- 窗口计算:7 天前 0:00 → 现在(周日凌晨 0:45 跑,覆盖上周日 0:00 → 周六 24:00) ----------
back = 7
start_date = (now.date() - datetime.timedelta(days=back))
start_dt = datetime.datetime.combine(start_date, datetime.time(0, 0))
start = start_dt.timestamp()
end = now.timestamp()
out = []
def emit(section, body):
    out.append("【%s】\n%s" % (section, body if body else "无"))

# ---------- 1. 本周对话 ----------
try:
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
    parts = []
    total = 0
    MAX_CHAT_CHARS = 80000   # 对话注入总量上限
    MAX_MSGS_PER_SESSION = 20  # 每会话最多保留最近 20 条,防止单会话吃光预算
    if sessions:
        parts.append("共 %d 个会话(窗口:%s → 现在)" % (len(sessions), start_dt.strftime('%m-%d %H:%M')))
        for sid, msgs in sessions.items():
            if total > MAX_CHAT_CHARS:
                parts.append("…(对话过长,已截断)")
                break
            s = msgs[0]
            title = (s['title'] or sid)[:40]
            parts.append("\n===== 会话: %s | 来源: %s =====" % (title, s['source']))
            for m in msgs[-MAX_MSGS_PER_SESSION:]:
                content = (m['content'] or '').strip()
                if not content:
                    continue
                if m['role'] == 'user' and content.startswith('[IMPORTANT'):
                    continue
                if content.startswith('⚠ Auxiliary'):
                    continue
                limit = 600 if m['role'] == 'user' else 200
                if len(content) > limit:
                    content = content[:limit] + '…'
                t = time.strftime('%H:%M', time.localtime(m['timestamp']))
                line = "[%s %s] %s" % (t, m['role'], content)
                parts.append(line)
                total += len(line)
                if total > MAX_CHAT_CHARS:
                    parts.append("…(对话过长,已截断)")
                    break
    else:
        parts.append("本周暂无对话记录")
    emit("本周对话提取", "\n".join(parts))
except Exception as e:
    emit("本周对话提取", "提取失败: %s" % e)

# ---------- 2. 用量周汇总 ----------
try:
    month_file = os.path.join(VAULT, '用量', now.strftime('%Y-%m') + '.md')
    if os.path.exists(month_file):
        text = open(month_file, encoding='utf-8').read()
        lines = [l for l in text.splitlines() if l.strip().startswith('|') and re.match(r'\|\s*\d{4}-\d{2}-\d{2}', l)]
        week_lines = []
        for l in lines:
            d = l.split('|')[1].strip()
            try:
                if datetime.datetime.strptime(d, '%Y-%m-%d').date() >= start_date:
                    week_lines.append(l)
            except ValueError:
                pass
        body = "本月用量文件: %s\n本周 %d 天:\n" % (month_file, len(week_lines))
        body += "\n".join(week_lines) if week_lines else "(本周暂无用量数据)"
        emit("用量周汇总", body)
    else:
        emit("用量周汇总", "当月用量文件不存在: %s" % month_file)
except Exception as e:
    emit("用量周汇总", "读取失败: %s" % e)

# ---------- 3. 员工成长记录 ----------
try:
    emp_files = sorted(glob.glob(os.path.join(VAULT, '工作室', '员工', '*.md')))
    parts = []
    for f in emp_files:
        text = open(f, encoding='utf-8').read()
        m = re.search(r'##\s*📈\s*成长记录(.*?)(?=\n##\s|\Z)', text, re.S)
        name = os.path.basename(f).replace('.md', '')
        if m:
            parts.append("◆ %s\n%s" % (name, m.group(1).strip()))
        else:
            parts.append("◆ %s(无成长记录小节)" % name)
    emit("员工成长记录", "\n".join(parts))
except Exception as e:
    emit("员工成长记录", "读取失败: %s" % e)

# ---------- 4. 上周计划回顾 ----------
try:
    wk_files = sorted(glob.glob(os.path.join(VAULT, '日志', '周', '*.md')))
    if wk_files:
        f = wk_files[-1]  # 最近一份(上周)
        text = open(f, encoding='utf-8').read()
        m = re.search(r'##\s*下周计划(.*?)(?=\n##\s|\Z)', text, re.S)
        body = "来源: %s\n" % f
        body += m.group(1).strip() if m else "(该文件无'下周计划'小节,附全文前 800 字)\n" + text[:800]
        emit("上周计划回顾", body)
    else:
        emit("上周计划回顾", "vault/日志/周/ 暂无历史周复盘文件")
except Exception as e:
    emit("上周计划回顾", "读取失败: %s" % e)

# ---------- 5. 模型观察记录表 + 决策问题 ----------
try:
    plan_file = os.path.join(VAULT, '工作室', '模型接入与观察规划.md')
    if os.path.exists(plan_file):
        text = open(plan_file, encoding='utf-8').read()
        obs = re.search(r'###\s*观察记录表(.*?)(?=\n##\s|\Z)', text, re.S)
        dec = re.search(r'##\s*五、决策点(.*?)(?=\n##\s|\Z)', text, re.S)
        body = "来源: %s\n" % plan_file
        body += "【观察记录表】\n" + (obs.group(1).strip() if obs else "无")
        body += "\n【决策问题清单】\n" + (dec.group(1).strip() if dec else "无")
        emit("模型观察记录表与决策清单", body)
    else:
        emit("模型观察记录表与决策清单", "规划文档不存在")
except Exception as e:
    emit("模型观察记录表与决策清单", "读取失败: %s" % e)

# ---------- 6. 健康打卡(本周每日日志) ----------
try:
    parts = []
    for i in range(back + 1):
        d = start_date + datetime.timedelta(days=i)
        f = os.path.join(VAULT, '日志', '每日', d.strftime('%Y-%m-%d') + '.md')
        if os.path.exists(f):
            text = open(f, encoding='utf-8').read()
            m = re.search(r'##\s*健康打卡(.*?)(?=\n##\s|\Z)', text, re.S)
            content = m.group(1).strip() if m else "(无健康打卡小节)"
            parts.append("%s: %s" % (d.strftime('%m-%d'), content))
    emit("健康打卡(本周)", "\n".join(parts) if parts else "本周无每日日志")
except Exception as e:
    emit("健康打卡(本周)", "读取失败: %s" % e)

# ---------- 7. 规则/习惯迭代 ----------
try:
    parts = []
    rule_file = os.path.join(VAULT, '工作室', '规则演变史.md')
    if os.path.exists(rule_file):
        mt = datetime.datetime.fromtimestamp(os.path.getmtime(rule_file))
        parts.append("规则演变史.md(更新于 %s):" % mt.strftime('%m-%d'))
        text = open(rule_file, encoding='utf-8').read()
        parts.append(text[:1200] + ('…' if len(text) > 1200 else ''))
    profile_file = os.path.join(VAULT, 'entities', '用户画像.md')
    if os.path.exists(profile_file):
        mt = datetime.datetime.fromtimestamp(os.path.getmtime(profile_file))
        parts.append("用户画像.md 最后更新: %s" % mt.strftime('%m-%d %H:%M'))
    emit("规则/习惯迭代", "\n".join(parts) if parts else "无")
except Exception as e:
    emit("规则/习惯迭代", "读取失败: %s" % e)

# ---------- 8. 员工自我复盘(2026-08-15 加:周复盘评估员工复盘质量,文件在 vault/复盘/员工/) ----------
try:
    base = os.path.join(VAULT, '复盘', '员工')
    reviews = []
    for name in ('调研员·知远', '写作员·墨白', '技术员·Claude'):
        d = os.path.join(base, name)
        if os.path.isdir(d):
            hits = []
            for root2, _, fs in os.walk(d):
                for f in fs:
                    if f.endswith('.md'):
                        hits.append((os.path.getmtime(os.path.join(root2, f)), os.path.relpath(os.path.join(root2, f), base)))
            hits.sort(reverse=True)
            if hits:
                mtime = time.strftime('%Y-%m-%d', time.localtime(hits[0][0]))
                reviews.append("%s: 最近复盘 %s(%s)" % (name, mtime, hits[0][1]))
            else:
                reviews.append("%s: 尚无自我复盘" % name)
        else:
            reviews.append("%s: 尚无自我复盘" % name)
    emit("员工自我复盘", "\n".join(reviews) if reviews else "无")
except Exception as e:
    emit("员工自我复盘", "读取失败: %s" % e)


print("\n".join(out))
