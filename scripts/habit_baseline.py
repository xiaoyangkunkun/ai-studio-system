#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""画像指纹基线生成/校验(2026-08-14 体检机制配套)
用途:防止每晚习惯整理覆盖体检成果(合并/删除/重写都会改变 hash)
用法:
  habit_baseline.py make   # 生成基线(体检重构后手动跑)
  habit_baseline.py check  # 校验基线 vs 画像现状,输出锁定/正常指令
"""
import sys, os, re, json, hashlib

IMG = '~/vault/entities/用户画像.md'
BASE = '~/.hermes/data/habit_baseline.json'

def parse_items(path):
    """提取画像 '✅ 已确认的习惯与要求' 小节下的编号条目"""
    items = {}
    try:
        text = open(path, encoding='utf-8').read()
    except Exception:
        return items
    # 找到已确认小节
    m = re.search(r'## ✅ 已确认的习惯与要求\n(.*?)(?=\n## |\Z)', text, re.S)
    if not m:
        return items
    section = m.group(1)
    for line in section.split('\n'):
        lm = re.match(r'^\s*(\d+)\.\s+(.*)', line)
        if lm:
            items[lm.group(1)] = lm.group(2).strip()
    return items

def item_hash(content):
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:12]

def make():
    items = parse_items(IMG)
    baseline = {
        'updated': '2026-08-14',
        'count': len(items),
        'items': {k: item_hash(v) for k, v in items.items()}
    }
    json.dump(baseline, open(BASE, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f'基线已生成:{BASE} | 条目数={len(items)}')

def check():
    if not os.path.exists(BASE):
        print('【基线缺失】首次运行,建议先 make;本次正常执行但无法防覆盖。')
        return
    baseline = json.load(open(BASE, encoding='utf-8'))
    current = parse_items(IMG)
    changed = False
    reasons = []
    # 对比条目集合与 hash
    for k, v in current.items():
        if k in baseline['items']:
            if item_hash(v) != baseline['items'][k]:
                changed = True
                reasons.append(f'条目 {k} 内容已变更(重写/优化)')
        else:
            changed = True
            reasons.append(f'条目 {k} 为新增')
    for k in baseline['items']:
        if k not in current:
            changed = True
            reasons.append(f'条目 {k} 已被删除/合并')
    if changed:
        new_max = max((int(k) for k in current.keys()), default=0)
        next_no = new_max + 1
        print(f'【画像已被人工重构】基线({baseline["updated"]})与现状不一致:')
        for r in reasons[:8]:
            print(f'  - {r}')
        print(f'【执行规则(硬性)】只允许追加新条目(新编号={next_no}起);禁止修改/删除/重排任何旧条目;旧条目一律保持原样。')
    else:
        print('【画像与基线一致】正常追加新习惯(编号续排)。')

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'check'
    if cmd == 'make':
        make()
    else:
        check()
