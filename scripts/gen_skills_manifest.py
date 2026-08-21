#!/usr/bin/env python3
"""生成技能矿全量清单:扫描候选仓库所有 SKILL.md,输出 名称|来源|描述 清单。"""
import os, re

ROOTS = ['/root/skills-candidates/awesome-skills-cn', '/root/skills-candidates/skills']
OUT = '/root/skills-candidates/技能矿全量清单.md'

rows = []
for root in ROOTS:
    for dirpath, dirnames, filenames in os.walk(root):
        # 跳过隐藏目录
        dirnames[:] = [d for d in dirnames if not d.startswith('.')]
        if 'SKILL.md' in filenames:
            p = os.path.join(dirpath, 'SKILL.md')
            try:
                txt = open(p, encoding='utf-8', errors='ignore').read()
            except Exception:
                continue
            name = re.search(r'^name:\s*(.+)$', txt, re.M)
            desc = re.search(r'^description:\s*(.+)$', txt, re.M)
            skill_name = name.group(1).strip().strip('"\'') if name else os.path.basename(dirpath)
            desc_text = desc.group(1).strip().strip('"\'') if desc else ''
            # 来源目录(相对 awesome-skills-cn 或 skills 的顶层分类)
            rel = os.path.relpath(dirpath, root)
            top = rel.split(os.sep)[0]
            rows.append((skill_name, top, desc_text[:100], os.path.relpath(dirpath, '/root/skills-candidates')))

rows.sort(key=lambda r: (r[1], r[0]))
with open(OUT, 'w', encoding='utf-8') as f:
    f.write('# 技能矿全量清单\n\n')
    f.write(f'> 生成:2026-08-12 | 技能总数:{len(rows)}\n')
    f.write('> 用途:仓库删除后的检索底档;需要某技能时按"来源目录/路径"可重新获取。\n\n')
    f.write('| # | 技能名 | 来源目录 | 一句话描述 | 路径 |\n')
    f.write('|---|---|---|---|---|\n')
    for i, (n, top, d, path) in enumerate(rows, 1):
        d = d.replace('|', '/').replace('\n', ' ')
        f.write(f'| {i} | {n} | {top} | {d} | {path} |\n')

print(f'完成: {len(rows)} 个技能 → {OUT}')
