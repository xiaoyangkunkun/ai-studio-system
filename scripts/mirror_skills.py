#!/usr/bin/env python3
"""把沉淀技能(非内置)全文镜像到 vault/技能库/。递归处理嵌套分类目录。"""
import os, shutil

SRC = '/root/.hermes/skills'
DST = '/root/vault/技能库'
BUNDLED = os.path.join(SRC, '.bundled_manifest')

# 内置技能名集合
bundled = set()
if os.path.isfile(BUNDLED):
    for line in open(BUNDLED, encoding='utf-8'):
        n = line.strip().split(':')[0].strip()
        if n:
            bundled.add(n)

def find_skills(dirpath):
    """返回 [(分类, 技能名, 技能目录绝对路径)],递归。分类=第一层目录名。"""
    out = []
    for entry in sorted(os.listdir(dirpath)):
        full = os.path.join(dirpath, entry)
        if entry.startswith('.'):
            continue
        if os.path.isdir(full):
            if os.path.isfile(os.path.join(full, 'SKILL.md')):
                cat = os.path.relpath(dirpath, SRC).split(os.sep)[0]
                out.append((cat, entry, full))
            else:
                out.extend(find_skills(full))
    return out

skills = find_skills(SRC)
sediment = [(c, n, p) for c, n, p in skills if n not in bundled]
archived = [(c, n, p) for c, n, p in sediment if '.archive' in p]
active = [(c, n, p) for c, n, p in sediment if '.archive' not in p]

# 清空重建
shutil.rmtree(DST, ignore_errors=True)
os.makedirs(DST)

for cat, name, path in active:
    dst_dir = os.path.join(DST, cat)
    os.makedirs(dst_dir, exist_ok=True)
    shutil.copytree(path, os.path.join(dst_dir, name), dirs_exist_ok=True)

print(f'OK: 沉淀技能 {len(active)} 个已镜像(归档 {len(archived)} 跳过) -> {DST}')
