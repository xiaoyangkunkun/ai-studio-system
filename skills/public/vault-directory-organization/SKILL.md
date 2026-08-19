---
name: vault-directory-organization
description: "Use when 整理 Obsidian 知识库目录结构。含移动前安全检查与脚本路径排雷。"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [obsidian, vault, directory, organization, 知识库整理]
---

# Vault 目录整理(Obsidian 知识库目录重组)

用户知识库(~/vault)文件变多、单目录拥挤时,拆分子目录归类。已被每日 3:30「知识库整理」cron 集成:该任务只**报告**拥挤候选,用户确认后由本流程**执行**移动。

## When to Use

- 用户说"知识库整理 / 目录整理 / 文件多了挤在一起 / 推荐建目录"
- 每日 3:30 知识库整理任务报告了【目录拥挤度候选】,用户确认执行

## 拥挤度阈值

- 单目录**直接文件数 >10**(不含子目录递归)→ 建议拆子目录
- 拆法:按类型/主题分(如 环境配置 vs 排障记录 vs 清单),不做时间分片

## 移动前安全检查(必做,缺一不可)

1. **确认链接风格**: 全库 `[[wikilink]]` 若都是**文件名式**(`[[Windows环境]]` 无路径前缀)→ 移动文件不断链,安全。检查有无路径式链接:`search_files` pattern `\[\[[^\]]*/`(含 `/` 的链接)——有则移动会断链,需同步改写。
2. **脚本硬编码路径排雷**: `grep -rn "~/vault" ~/.hermes/scripts/*.py ~/.hermes/scripts/*.sh` → 被引用的文件**不能动**(或同步改脚本)。已知硬编码:定时任务清单/能力目录/知识库目录/用户画像(cron_inventory/skills_inventory/kb_inventory/habit_baseline 输出)、工作室/组织架构.md(flow_signal_extract 引用)。
3. **cron prompt 硬编码路径排雷**: 读 ~/.hermes/cron/jobs.json,搜待移动文件名 → 命中任务的 prompt 里有绝对路径,移动后必须同步更新(实测:每周复盘任务 prompt 硬编码了 `~/vault/工作室/模型接入与观察规划.md`)。用 python3 读 jobs.json 改 `prompt` 字段,json.dump 保存。
4. 检查 `migrate_vault.py` 类历史迁移脚本:只映射旧文件名,不影响(确认不再运行即可)。

## 执行

```bash
cd ~/vault
mkdir -p "entities/环境配置" "流程/从零搭建手册"  # 目标子目录
mv "entities/Windows环境.md" "entities/环境配置/"
# ... 逐个移动,完成后 ls 验证
```

移动后:
- 重生成知识库目录:`venv/bin/python3 ~/.hermes/scripts/kb_inventory.py`(自动重扫全库,无需手改)
- 追加变更到 ~/vault/log.md(格式:`- YYYY-MM-DD | 目录整理:...`)
- 更新被命中的 cron prompt 路径(jobs.json)
- 三端 Syncthing 自动同步,无需手动;Windows 端 Obsidian 文件名链接不受影响

## 已落地的目录结构(2026-08)

- `entities/环境配置/`:Windows环境、同步配置、服务器迁移手册、远程操控WindowsHermes方案、域名接入改造清单
- `entities/排障记录/`:微信限流排障记录、应急恢复手册
- `流程/从零搭建手册/`:CSDN自动发布、DeepSeek、Gemini、Kimi 教程
- `工作室/项目报告/`:数字员工可行性报告、落地全记录、模型接入与观察规划
- entities/ 原地保留:定时任务清单、能力目录、知识库目录、用户画像(自动生成,脚本写路径,永不移动)

## 定时任务联动

- 每日 3:30「知识库整理」(job 0e391f8cf946)第 5 步做拥挤度检查:**只报告不移动**(防脚本路径/三端同步踩坑),候选列在输出中 → 用户确认 → 本技能执行。
- 决策规则:目录 >10 文件但类型单一(如日志按日期)→ 可不拆;类型混杂才拆。

## 实体重命名（全库批量替换）

当需要重命名一个"实体"（人名/岗位/项目名）时，不只是改目录——要改所有引用。实测流程：

### 执行步骤
1. **grep 定位所有引用**: `grep -rln "旧名称" ~/vault/ ~/.hermes/skills/ ~/.hermes/profiles/` 找到全部引用文件
2. **分类文件**:
   - **活跃文件**（.md、SKILL.md、SOUL.md、.canvas）→ 必须改
   - **目录路径**（`工作室产出/旧名/`、`复盘/员工/旧名/`）→ 视情况改（改目录名则路径也改）
   - **自动/备份文件**（.stversions/、.curator_backups/、.obsidian/plugins/、state.db）→ 不改
   - **历史归档**（wiki/raw/、wiki/analytics/）→ 通常不改（保持历史状态）
3. **先改目录，再改引用**: `mv` 重命名目录 → 批量替换文件内容
4. **批量替换脚本**: 用 `execute_code` 写 Python 脚本，逐文件读→替换→写回，跳过 binary/backup
5. **grep 验证**: 最终 `grep -rn "旧名称" ... | grep -v 路径 | grep -v backup | wc -l` 确认零遗留
6. **更新关键文档的迭代日志**: 组织架构/员工档案追加变更记录

### 注意事项
- **路径替换要小心**: 如果目录也改了，文件内容里的路径引用要跟着改；如果目录不改，路径引用保持原样
- **Obsidian workspace 文件**（.obsidian/workspace.json）不需要手动改，重新打开 Obsidian 会自动更新
- **Syncthing 会自动同步**: 改完后三端自动生效，不需要手动操作
- **.obsidian/plugins/ 下的 data.json**（studio-hub、ai-knowledge-os）是插件缓存，会随 Obsidian 重建索引自动更新

## 坑

- 移动前漏查脚本路径 → 凌晨定时任务写错地方(本次已踩:每周复盘任务硬编码路径,已同步更新)。
- 只移动文件不重生成 知识库目录.md → index 显示旧路径(虽然链接仍有效,但目录文档过时)。
- .obsidian/.stfolder/.stversions/.trash 目录永不动。
- 批量重命名时只改了文件内容没改目录（或反过来）→ 路径断裂，Obsidian wikilink 失效。
- 批量替换漏掉 skill 文件/SOUL.md/canvas → 员工调度时引用旧名导致任务写错产出路径。
