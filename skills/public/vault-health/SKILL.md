---
name: vault-health
description: "Obsidian vault知识管理系统：健康度扫描、Inbox分类、Dashboard、Notion同步。Use when 检查/修复/管理知识库。"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [obsidian, vault, health, analytics]
---

# Vault健康度管理

## When to Use
- 用户问"知识库健康度"、"孤立笔记"、"死链"
- 需要扫描/修复vault问题
- 需要追踪知识增长趋势

## 脚本清单

所有脚本在 `~/.hermes/scripts/` 下：

| 脚本 | 功能 |
|------|------|
| `smart_fix.py` | **一键修复**：5Phase因果顺序（frontmatter→去重→死链→孤儿→stub），dry-run默认，--apply执行 |
| `hash_dedup.py` | **哈希去重**：SHA256内容指纹+预摄入门控，防重复浪费token |
| `hidden_connections.py` | 隐藏关联发现（≥2个共同邻居但无直接链接） |
| `health_report.py` | 健康度评分（孤立率/链接密度/死链，0-100分） |
| `graph_snapshot.py` | Graph快照（笔记数/链接数/边数，追踪增长） |
| `fix_frontmatter.py` | 批量补frontmatter |
| `clean_vault.py` | 清理空文件和stub |
| `fix_dead_links.py` | 死链检测（--fix 自动创建stub） |
| `classify_inbox.py` | Inbox AI分类（每晚3:00，集成hash_dedup门控） |
| `watchdog_inbox.py` | 产出目录兜底摘要（每天2:30，检测员工漏写的Inbox条目） |


## Cron集成

- **2:30 产出Watchdog**：检测员工产出目录，自动在Inbox创建摘要
- **3:00 Inbox AI分类**：00-Inbox/ → AI分类 → wiki各目录
- **3:10 健康度扫描**：hidden_connections + health_report + graph_snapshot
- **3:30 知识库整理**：fix_frontmatter + clean_vault + fix_dead_links + wiki目录整理
- **8:00 Notion同步**：Obsidian待办↔Notion提醒双向同步

## 修复策略

- **Smart Fix 一键修复**（推荐）：`python3 smart_fix.py`（dry-run）→ `python3 smart_fix.py --apply`（执行）
  - Phase 1: 补frontmatter+别名 | Phase 2: 去重 | Phase 3: 修死链 | Phase 4: 链孤儿 | Phase 5: 扩展stub
  - 可选 `--phase 1,2` 只跑指定阶段，`--report fix.md` 输出报告
- 全自动：frontmatter补全、空文件清理
- 半自动：死链修复（检测→确认→批量）
- 人工：孤立笔记语义链接、MOC结构

## Pitfalls

- 批量修改前先备份：`cp -r ~/vault ~/vault-backup-$(date +%Y%m%d)`
- 修改集中在服务器端，等Syncthing同步
- 死链大部分来自技能文档示例链接，不需要修复
- classify_inbox.py集成hash_dedup门控，重复文件自动跳过
- watchdog_inbox.py用文件hash去重，不会重复创建Inbox摘要
- smart_fix.py默认dry-run，必须加--apply才执行修改
- hash_dedup.py的MIN_CONTENT_LENGTH=50，短于50字的文件会被门控拦截
- smart_fix.py Phase 3当前只有模糊匹配（编辑距离≤2+标题相似度>0.6），无语义匹配

## 知识管理全链路

```
多源入库(微信/语音/网页/文件/API/员工产出)
    ↓ 00-Inbox/
AI分类(classify_inbox.py, 每晚3:00)
    ↓ wiki/entities|concepts|comparisons|raw/
健康度扫描(health_report.py, 每晚3:10)
    ↓ wiki/analytics/
Dashboard展示(Dashboard.md + 知识总览.base)
    ↓ Obsidian三端同步
知识→产出→复盘→沉淀回wiki
```
