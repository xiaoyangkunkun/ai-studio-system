---
title: "Obsidian Vault 归档流程(2026-08 实测,服务器 ~/vault)"
created: 2026-08-20
updated: 2026-08-20
type: note
---
# Obsidian Vault 归档流程(2026-08 实测,服务器 ~/vault)

## Vault 结构(遵循 SCHEMA.md)
```
~/vault/
├── SCHEMA.md          # 规范总纲(命名/frontmatter/标签/阈值/更新策略)
├── index.md           # 总目录,新页面必须登记
├── log.md             # 操作日志,每次归档必追加
├── concepts/          # 概念/主题页
├── entities/          # 实体页(人/事/物)
├── comparisons/       # 对比页(表格优先)
├── queries/           # 查询/复盘页
├── raw/               # 原始资料,只读,永不修改
└── .obsidian/         # Obsidian App 配置(自动)
```

## SCHEMA 关键约定
- 文件命名:小写字母+连字符,无空格(如 `weight-loss-plan.md`、`fuzhou-travel-guide.md`)
- 每页 YAML frontmatter:
  ```yaml
  ---
  title: 页面标题
  created: YYYY-MM-DD
  updated: YYYY-MM-DD
  type: entity | concept | comparison | query | summary
  tags: [来自登记体系]
  sources: [raw/来源文件.md]
  confidence: high | medium | low   # 可选
  ---
  ```
- 每页至少 2 条 `[[wikilinks]]` 出链(通常链到 index.md 及相关页)
- 标签先登记后使用(SCHEMA 有分类体系:生活:健康/饮食/运动/旅行/家居;学习:AI/编程/读书/笔记法;工作:项目/效率/工具;元:对比/时间线/预测/待整理)

## 归档标准流程(新内容入库)
1. **原始文件备份** → `raw/` 目录(只读来源,保留原名)
2. **建整理页** → `concepts/` 或 `entities/` 下,文件名规范化(英文连字符),内容 = frontmatter + 完整正文
   - 正文首段或结尾加双链,如 `相关:[[other-page]] · [[index]]`
3. **更新 index.md** → 在对应分区(## Concepts 等)加一行:`- [[page-name]] — 一句话摘要`;更新"最后更新/总页数"
4. **追加 log.md** → `- YYYY-MM-DD HH:MM | 操作描述(文件、来源、动作)`

## 同步确认
- 归档后等 5-10 秒,用 Syncthing API 确认手机端完成度:
  ```bash
  curl -s -H "X-API-Key: $KEY" "http://127.0.0.1:8384/rest/db/completion?folder=<id>&device=<手机设备ID>" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('completion'),'%')"
  ```
- 手机 Obsidian 打开 vault 即可看到新笔记(Syncthing 自动同步)

## 陷阱
- 中文文件名不规范(SCHEMA 要求英文连字符)→ 归档时重命名,raw/ 保留原名
- 忘记更新 index/log → 破坏规范,检索时找不到
- 双链少于 2 条 → 不符合 SCHEMA
- raw/ 只读:修正一律写在整理页,不改 raw
