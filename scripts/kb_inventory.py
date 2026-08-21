#!/usr/bin/env python3
"""生成知识库内容目录(kb-inventory)到 vault。
扫描 vault 下所有 .md 笔记(排除 raw/.obsidian/.stfolder),输出中文标题 + 类型 + 更新时间 + 一句话摘要。"""
import os, re, datetime

VAULT = '${VAULT_PATH:-/root/vault}'
OUT = os.path.join(VAULT, 'entities', '知识库目录.md')
SKIP_DIRS = {'raw', '.obsidian', '.stfolder', '.stversions', '.git', '.trash', '技能库', '日志', '用量'}
SKIP_FILES = {'知识库目录.md', '能力目录.md', 'SCHEMA.md'}

def first_line_desc(path):
    """取正文第一个非空非标题段落做摘要(截断 40 字)"""
    try:
        txt = open(path, encoding='utf-8').read()
    except Exception:
        return ''
    body = re.sub(r'^---\n.*?\n---', '', txt, flags=re.S).strip()
    for line in body.split('\n'):
        line = line.strip()
        if line and not line.startswith(('#', '>', '|', '-', '*', '![', '`', '```')) and not line.startswith(('---', '**相关')):
            return line[:40]
    return ''

def parse_fm(path):
    try:
        txt = open(path, encoding='utf-8').read()
    except Exception:
        return {}, ''
    m = re.match(r'^---\n(.*?)\n---', txt, re.S)
    fm = {}
    if m:
        for k in ('title', 'type', 'updated', 'created'):
            v = re.search(rf'^{k}:\s*(.+)$', m.group(1), re.M)
            if v:
                fm[k] = v.group(1).strip().strip('"\'')
    return fm, first_line_desc(path)

entries = []  # (relpath, cat, name, fm, desc, mtime)
for root, dirs, files in os.walk(VAULT):
    dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
    for fn in sorted(files):
        if not fn.endswith('.md') or fn in SKIP_FILES:
            continue
        full = os.path.join(root, fn)
        rel = os.path.relpath(full, VAULT)
        cat = os.path.relpath(os.path.dirname(full), VAULT)
        cat = cat if cat != '.' else '根目录'
        fm, desc = parse_fm(full)
        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(full)).strftime('%Y-%m-%d')
        name = fm.get('title') or fn[:-3]
        entries.append((rel, cat, fn[:-3], fm.get('type', ''), name, desc, mtime))

now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
lines = ['---', 'title: 知识库内容目录', f'created: {now[:10]}', f'updated: {now[:10]}',
         'type: entity', 'tags: [工具, 效率]', 'sources: []', '---', '',
         '# 📚 知识库内容目录', '',
         f'> 自动生成: {now} | 笔记总数: **{len(entries)}**',
         '> 能力目录见 [[能力目录]],总入口 [[index]]。', '',
         '## 目录', '']
cats = sorted(set(e[1] for e in entries))
for c in cats:
    n = sum(1 for e in entries if e[1] == c)
    lines.append(f'- {c}({n})')
lines += ['', '---', '']
for c in cats:
    lines.append(f'## {c}')
    lines.append('')
    for rel, cat, fn, typ, name, desc, mtime in sorted([e for e in entries if e[1] == c], key=lambda x: x[5]):
        t = f'[{typ}]' if typ else ''
        d = f' — {desc}' if desc else ''
        lines.append(f'- **{name}**({mtime}){t}{d} `{rel}`')
    lines.append('')
lines += ['---', '', '**相关笔记**:[[index]] · [[能力目录]] · [[同步配置]]', '']

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print(f'OK 知识库目录已更新: {len(entries)} 篇笔记 -> {OUT}')