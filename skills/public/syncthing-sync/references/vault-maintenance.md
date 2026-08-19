# Vault 自维护体系与中文化迁移(2026-08 实测)

## 每晚自动化流水线

```
23:00 知识库整理(cron 0e391f8cf946,agent 模式)
      → 扫描 vault → 更新 index.md(新笔记登记/已删移除/总页数)
      → 检查补双链(每页≥2)→ 追加 log.md → 微信推送 3-5 行
23:30 目录每日更新(cron 6b86d3070421,no_agent)
      → skills_inventory.py(能力目录)
      → kb_inventory.py(知识库目录)
      → cron_inventory.py(定时任务清单)
20:00 用户习惯整理(cron de283d301896,script+daily_chat_extract.py)
      → 观察文档 ~/用户习惯观察.md → 推送微信 → 用户确认后更新 entities/用户画像.md
每周日 3:00 自动备份(no_agent,失败告警)
每月 1 号 9:00 备份打包发微信(agent,script=monthly_backup_send.sh)
```

## 脚本要点(均在 ~/.hermes/scripts/)

- `skills_inventory.py` — 递归 walk skills 目录找 SKILL.md;内置判定读 `.bundled_manifest`(每行 `name:hash`);中文描述用 CN 映射 dict(未收录回退原文 desc);输出带 frontmatter + 双链。
- `kb_inventory.py` — walk vault,SKIP_DIRS 必须含 `raw/.obsidian/.stfolder/.stversions/.trash/.git`;摘要取正文第一个非标题/非列表/非代码块行(截 40 字);SKIP_FILES 排除目录文档自身和 SCHEMA.md。
- `cron_inventory.py` — 读 `~/.hermes/cron/jobs.json`(dict 含 jobs 列表);状态判定:enabled=False 或 state=completed 或 (repeat=once 且 last_run_at)→ 非运行中。
- no_agent wrapper 模式:`if 脚本 >> log 2>&1; then :; else echo 告警; fi` — 成功静默,失败才推送。

## 中文化迁移清单(改文件名是联动操作)

1. 全库链接替换:定义 LINK_MAP(`[[旧名]]`→`[[新名]]`),遍历所有 .md(排除 raw/.obsidian/.stfolder/.stversions/.trash),replace + 正则清理已删笔记的引用行。
2. 脚本 OUT 路径:3 个 inventory 脚本里的输出路径和文档内互链要同步改中文。
3. cron prompt 引用:`cronjob update` 改 prompt 里的旧文件路径(如 user-profile.md → 用户画像.md)。
4. 记忆引用:`memory replace` 改旧路径。
5. SCHEMA.md 命名规范同步更新。
6. 验证:grep 确认无 `[[英文残留名]]`;`find` 确认结构;Syncthing `db/status` 确认同步(手机端完成度会从低到高,正常)。

## 沉淀技能判定

- `.bundled_manifest` 记录出厂技能;`skills list` 的 count 含 .archive 归档项,活跃数要看目录扫描。
- 本机沉淀(2026-08):hermes-server-ops、hermes-headless-server、social-trend-monitoring、cn-network-web-search、syncthing-sync(及归档的 syncthing-p2p-sync)。

## 用户偏好(固化)

- 重要决定先问再做("先问我确认"明确说过多次)。
- 解决完整流程后主动询问是否归档文档到知识库并发微信。
- 习惯/要求沉淀进 vault 文档(用户画像.md),不进长期记忆。
- 能力目录与知识库目录分开维护、互相链接。
