#!/usr/bin/env python3
"""vault 迁移:中文命名 + 主题目录归类 + 删除测试笔记 + 全库链接替换。"""
import os, re, shutil

VAULT = '/root/vault'
RAW = os.path.join(VAULT, 'raw')

# 1. 删除测试笔记
for f in [os.path.join(VAULT, 'concepts', '同步测试.md'),
          os.path.join(VAULT, '这是一条测试能不能同步到服务端的笔记.md')]:
    if os.path.exists(f):
        os.remove(f)
        print(f'🗑 删除 {os.path.relpath(f, VAULT)}')

# 2. 创建主题目录(预留)
for sub in ['旅行', '健康', '学习', '生活', '工作', '项目']:
    os.makedirs(os.path.join(VAULT, 'concepts', sub), exist_ok=True)

# 3. 重命名 + 移动
MOVES = [
    ('concepts/fuzhou-travel-guide.md', 'concepts/旅行/福州旅游攻略.md'),
    ('concepts/weight-loss-plan.md', 'concepts/健康/减肥计划.md'),
    ('concepts/kb-setup-guide.md', 'concepts/学习/知识库搭建全记录.md'),
    ('entities/skills-inventory.md', 'entities/能力目录.md'),
    ('entities/kb-inventory.md', 'entities/知识库目录.md'),
    ('entities/cron-inventory.md', 'entities/定时任务清单.md'),
    ('entities/user-profile.md', 'entities/用户画像.md'),
    ('entities/syncthing-config.md', 'entities/同步配置.md'),
    ('entities/server-migration.md', 'entities/服务器迁移手册.md'),
    ('entities/archive-workflow.md', 'entities/归档工作流.md'),
]
for src, dst in MOVES:
    sp = os.path.join(VAULT, src)
    dp = os.path.join(VAULT, dst)
    if os.path.exists(sp):
        os.makedirs(os.path.dirname(dp), exist_ok=True)
        shutil.move(sp, dp)
        print(f'📦 {src} → {dst}')

# 4. 全库链接替换(排除 raw/)
LINK_MAP = {
    '[[fuzhou-travel-guide]]': '[[福州旅游攻略]]',
    '[[weight-loss-plan]]': '[[减肥计划]]',
    '[[kb-setup-guide]]': '[[知识库搭建全记录]]',
    '[[skills-inventory]]': '[[能力目录]]',
    '[[kb-inventory]]': '[[知识库目录]]',
    '[[cron-inventory]]': '[[定时任务清单]]',
    '[[user-profile]]': '[[用户画像]]',
    '[[syncthing-config]]': '[[同步配置]]',
    '[[server-migration]]': '[[服务器迁移手册]]',
    '[[archive-workflow]]': '[[归档工作流]]',
}
changed = 0
for root, dirs, files in os.walk(VAULT):
    dirs[:] = [d for d in dirs if d not in ('raw', '.obsidian', '.stfolder', '.stversions', '.trash', '.git')]
    for fn in files:
        if not fn.endswith('.md'):
            continue
        p = os.path.join(root, fn)
        txt = open(p, encoding='utf-8').read()
        new = txt
        for old, rep in LINK_MAP.items():
            new = new.replace(old, rep)
        # 清理对已删测试笔记的引用
        new = new.replace(' · [[同步测试]]', '').replace('[[同步测试]] · ', '')
        new = re.sub(r'\n- \[\[同步测试\]\][^\n]*\n', '\n', new)
        new = re.sub(r'\n- \[\[这是一条测试能不能同步到服务端的笔记\]\][^\n]*\n', '\n', new)
        if new != txt:
            open(p, 'w', encoding='utf-8').write(new)
            changed += 1
            print(f'🔗 更新链接: {os.path.relpath(p, VAULT)}')
print(f'链接替换完成,共更新 {changed} 个文件')
print('✅ 迁移完成')
