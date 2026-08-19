---
name: obsidian-vault-organization
description: "Use when 用户要整理知识库/目录(文件挤在一起、建子目录归类、目录重组)。"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [obsidian, vault, organization, directory, 目录整理]
---

# Obsidian Vault 目录整理(知识库归位)

整理 Obsidian 知识库目录结构:文件多了挤在一起时,建子目录归类。核心是"移动前必查、移动后必更",保证链接不断、脚本不坏、cron 不丢路径。

## When to use

- 用户说"知识库整理/目录整理/文件多了挤在一起/推荐创建目录放一起"
- vault 某目录文件数 >10 需要拆分
- 任何涉及移动 vault 文件的操作

## 关键事实(本用户 vault,已验证)

- 全库用**文件名式 `[[wikilinks]]`** → 移动文件不断链(Obsidian 按文件名解析)
- 自动生成文件(kb_inventory.py / skills_inventory.py / cron_inventory.py / habit 脚本写入):定时任务清单、能力目录、知识库目录、用户画像 —— **不能移动**,脚本硬编码路径
- flow_signal_extract.py 引用 `工作室/组织架构.md` —— 不能移动
- 目录层级上限 4 层(用户规矩),整理后保持 2-3 层
- 每日 3:30「知识库整理」cron 已含拥挤度检查(>10 文件只报告不移动)

## Workflow

### 1. 扫描现状(先看再动)

```bash
# 一级目录拥挤度(直接文件数,不递归)
for d in $(find ~/vault -maxdepth 1 -type d | grep -v "\.obsidian\|\.st\|\.trash"); do
  echo "$(find "$d" -maxdepth 1 -type f | wc -l)  $d"
done | sort -rn
# 二级目录
for d in $(find ~/vault -maxdepth 2 -type d | grep -v "\.obsidian\|\.st\|\.trash"); do ... done
# 根目录散落文件
find ~/vault -maxdepth 1 -type f -name "*.md"
```

### 2. 移动前三查(必须全部通过)

1. **查链接类型**:`grep -rn "\[\[[^]]*/"` —— 有路径式链接 `[[目录/文件]]` 就不能随便移(要同步改);只有文件名式才安全
2. **查脚本硬编码路径**:`grep -rl "<文件名>" ~/.hermes/scripts/` —— 被脚本引用的文件不能动
3. **查 cron prompt 硬编码路径**:`python3 -c` 读 `~/.hermes/cron/jobs.json`,找 prompt/script 里出现待移动文件名的 job —— 移动后必须同步更新该 job 的 prompt(用 cronjob update)

### 3. 给方案 → 等确认(用户规矩:先规划确认再执行)

- 输出对比表:目录 | 现文件数 | 拆分子目录 | 移动文件清单
- 明确标注"硬约束:XXX 不能动(脚本/cron 依赖)"
- 用户确认后才执行;用户说"只拆 X 和 Y"就按局部方案做

### 4. 执行移动

```bash
cd ~/vault && mkdir -p "目录/子目录" && mv "目录/文件.md" "目录/子目录/"
```

### 5. 移动后必更(三件事)

1. **更新受影响 cron prompt**:移动文件在 jobs.json 里有硬编码路径 → `cronjob update` 改路径(本会话实例:每周复盘引用 `工作室/模型接入与观察规划.md`,移到 `工作室/项目报告/` 后 prompt 同步改)
2. **重生成知识库目录**:`python3 ~/.hermes/scripts/kb_inventory.py`(自动按新路径重建)
3. **log.md 追加变更记录**:格式 `- YYYY-MM-DD | 做了什么`(SCHEMA.md 规矩:每次操作必须记录)

## 拆分建议模板(实测好用)

- `entities/` 混合环境配置+排障记录 → `entities/环境配置/` + `entities/排障记录/`
- `流程/` 混合教程+日常流程 → `流程/从零搭建手册/`
- `工作室/` 混合组织+项目报告 → `工作室/项目报告/`
- 标准:整理后每个目录 ≤8 个直接文件

## Pitfalls

- **别动自动生成文件**:定时任务清单/能力目录/知识库目录/用户画像 是脚本每夜重写的,移动=脚本写回旧路径,目录会"复活"
- **.stversions/.stfolder/.trash 不是内容目录**,统计和移动都要排除
- 移动后 Obsidian 打开中的文件会短暂显示断链,属正常,重载即可
- 用户确认用词"12装,4再讨论"= 1、2 执行,4 继续讨论 —— 严格按用户点名的范围执行
- 整理完主动报告"脚本依赖文件均未动"消除用户顾虑

## 相关

- `obsidian`(bundled,只讲读写笔记,不讲重组)
- `obsidian-markdown`(bundled,语法)
- `skill-curation`(技能导入,不是 vault 整理)

## 知识管理系统(2026-08-17 新增)

vault 现有知识管理系统组件:
- `Dashboard.md` — 知识中枢主页,嵌入Bases/Canvas/analytics
- `知识总览.base` — 全库知识表格/卡片视图
- `项目管理.base` — 工作室产追踪
- `知识地图.canvas` — 知识网络可视化
- `00-Inbox/` — 统一入库入口,AI每晚分类
- `classify_inbox.py` — Inbox AI分类脚本(cron 3:00)
- `health_report.py` — 健康度评分(cron 3:10)
- `graph_snapshot.py` — Graph增长追踪
- `hidden_connections.py` — 隐藏关联发现

整理目录时注意不要破坏这些组件的路径引用。
