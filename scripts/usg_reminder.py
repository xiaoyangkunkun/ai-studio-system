#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""周日凌晨用量周总结(no_agent,零 token):读用量账本输出上周 7 天总结。
由 cron 每周日 0:30 触发(结算 0:10 完成后),周日白天老大醒来即可查看。"""
import datetime
import re
import os

VAULT = os.environ.get("VAULT_PATH", os.path.expanduser(os.environ.get("VAULT_PATH", os.path.expanduser("~/vault"))))
now = datetime.datetime.now()
month_file = os.path.join(VAULT, '用量', now.strftime('%Y-%m') + '.md')

lines = []
if os.path.exists(month_file):
    text = open(month_file, encoding='utf-8').read()
    for l in text.splitlines():
        if l.strip().startswith('|') and re.match(r'\|\s*\d{4}-\d{2}-\d{2}', l):
            lines.append(l)

# 窗口:最近 7 天(上周日 → 周六,结算已完成)
start_date = (now.date() - datetime.timedelta(days=7))
week = []
for l in lines:
    d = l.split('|')[1].strip()
    try:
        dt = datetime.datetime.strptime(d, '%Y-%m-%d').date()
    except ValueError:
        continue
    if start_date <= dt < now.date():
        cells = [c.strip() for c in l.split('|')[1:-1]]
        if len(cells) >= 6:
            week.append((d, cells))

week.sort(key=lambda x: x[0])
if not week:
    print("【上周用量总结 📊】\n\n上周暂无用量数据(用量账本为空)。有空发官方数据包我按官方更新~")
else:
    total = sum(float(cells[5].replace('¥', '')) for d, cells in week
                if cells[5].replace('¥', '').replace('.', '').isdigit())
    daily = "\n".join("- %s: ¥%s" % (d, cells[5]) for d, cells in week)
    print("【上周用量总结 📊】(%s 至 %s)\n\n上周合计: ¥%.2f\n\n%s\n\n官方数据包:有空发上周官方 zip/截图,我按官方更新账本;没空按自动统计,不打扰~" % (
        week[0][0], week[-1][0], total, daily))
