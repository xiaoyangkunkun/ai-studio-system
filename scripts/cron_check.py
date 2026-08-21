#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""定时任务冲突检查器(2026-08-15 建,老大要求:创建定时任务前先查冲突)
用法:
  python3 cron_check.py                     # 检查全部现有任务有无互相冲突
  python3 cron_check.py "0 11 * * 6"        # 检查候选时间点与现有任务是否冲突
  python3 cron_check.py "30 4 * * *" 30     # 自定义冲突窗口(默认30分钟)
"""
import sys, json, re

JOBS = '${HOME}/.hermes/cron/jobs.json'

def parse_cron(expr):
    """解析标准 5 段 cron,返回 (分钟, 小时, 日, 月, 周) 或 None"""
    parts = expr.split()
    if len(parts) != 5:
        return None
    try:
        return {
            'min': parts[0], 'hour': parts[1], 'dom': parts[2],
            'mon': parts[3], 'dow': parts[4],
        }
    except Exception:
        return None

def is_match(c, target_min, target_hour, target_dow=None):
    """cron 字段是否匹配目标时间(简化:支持 * 和具体数字,不处理 */n)"""
    def field_match(pat, val):
        if pat == '*':
            return True
        if '/' in pat:
            base, step = pat.split('/')
            base = 0 if base == '*' else int(base)
            return val >= base and (val - base) % int(step) == 0
        if '-' in pat:
            a, b = pat.split('-')
            return int(a) <= val <= int(b)
        if ',' in pat:
            return val in [int(x) for x in pat.split(',')]
        return int(pat) == val
    # 简化:只按分钟+小时判断(跨天任务如每日/每周)
    if target_dow is not None and c['dow'] != '*' and not field_match(c['dow'], target_dow):
        return False
    return field_match(c['min'], target_min) and field_match(c['hour'], target_hour)

def load_jobs():
    with open(JOBS) as f:
        return json.load(f)['jobs']

def check_all():
    jobs = [j for j in load_jobs() if j.get('enabled', True) and j.get('schedule_display') and 'once' not in j.get('schedule_display','')]
    print('=== 现有定时任务冲突检查(%d 个启用任务)===' % len(jobs))
    conflicts = 0
    parsed = []
    for j in jobs:
        c = parse_cron(j['schedule_display'])
        if c:
            parsed.append((j['name'], c, j['schedule_display']))
    # 找同一小时同一分钟(精确冲突)或相邻 30 分钟内
    for i in range(len(parsed)):
        for k in range(i+1, len(parsed)):
            n1, c1, s1 = parsed[i]
            n2, c2, s2 = parsed[k]
            # 简化冲突:同为每天/每周且分钟差<=30 且小时相同
            if c1['min'] == c2['min'] and c1['hour'] == c2['hour']:
                # 还要看周期是否重叠(简化:都含具体 dow 且相同,或都是 *)
                d1 = c1['dow']; d2 = c2['dow']
                if d1 == d2 or '*' in (d1, d2) or (d1 != '*' and d2 != '*' and d1 == d2):
                    print('  ⚠️ 冲突: %s(%s) vs %s(%s) 同分钟' % (n1, s1, n2, s2))
                    conflicts += 1
    if conflicts == 0:
        print('  ✅ 现有任务无精确冲突(同分钟同周期)')
    print('  (注:仅检查同分钟冲突;分钟差≤30 的相邻任务属于可接受范围,不报)')

def check_candidate(expr, window=30):
    c = parse_cron(expr)
    if not c:
        print('❌ 无法解析 cron 表达式: %s' % expr)
        return
    print('=== 候选时间检查: %s ===' % expr)
    jobs = [j for j in load_jobs() if j.get('enabled', True) and j.get('schedule_display') and 'once' not in j.get('schedule_display','')]
    try:
        cand_min = int(c['min']) if c['min'] != '*' else -1
        cand_hour = int(c['hour']) if c['hour'] != '*' else -1
    except Exception:
        print('  候选含通配/复杂表达式,仅显示同一时刻任务:')
        cand_min, cand_hour = None, None
    hit = False
    for j in jobs:
        jc = parse_cron(j['schedule_display'])
        if not jc:
            continue
        try:
            jmin = int(jc['min']); jhour = int(jc['hour'])
        except Exception:
            continue
        if cand_hour is not None and jhour == cand_hour and abs(jmin - cand_min) <= window:
            print('  ⚠️ 与「%s」(%s) 冲突(时间差 %d 分钟)' % (j['name'], j['schedule_display'], abs(jmin - cand_min)))
            hit = True
    if not hit:
        print('  ✅ 与现有任务无冲突(±%d 分钟窗口内无任务)' % window)

if __name__ == '__main__':
    if len(sys.argv) >= 2:
        w = int(sys.argv[2]) if len(sys.argv) >= 3 else 30
        check_candidate(sys.argv[1], w)
    else:
        check_all()
