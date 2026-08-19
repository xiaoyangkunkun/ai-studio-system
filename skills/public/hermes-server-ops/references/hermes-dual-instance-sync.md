# 双 Hermes 主从同步(服务器 ↔ Windows)

场景:用户在同一局域网/异地有第二个 Hermes 实例(Windows 电脑),希望两端"拥有同样的记忆和技能",且**以服务器为权威**。2026-08-12 实施验证。

## 架构决策

- **知识库(vault)**:双向(sendreceive)—— 共同大脑,两端都写
- **记忆 + 技能**:单向主从 —— 服务器 sendonly,Windows receiveonly,服务器权威
- **会话/config/cron/.env**:各端独立,不同步(state.db 是 SQLite,双写会损坏;密钥/平台配置各端不同)
- 用户偏好:重要信息无论在哪端聊,由服务器端沉淀(微信)或进知识库(三端共享);Windows 端自己沉淀的经"投稿箱"审核后并入主脑

## Syncthing 文件夹配置(服务器端)

```python
# API 添加 sendonly 文件夹,只共享给目标设备(devices 含本机+目标机)
f = dict(模板配置)  # GET /rest/config/folders/vault 做模板
f['id'] = 'memories'; f['path'] = '~/.hermes/memories'
f['type'] = 'sendonly'
f['devices'] = [{'deviceID': WIN_DEV, ...}]
PUT /rest/config/folders/memories
# 同样:skills → ~/.hermes/skills
```

- 每个文件夹内放 `.stignore` 排除 `*.lock`、`*.tmp`(锁文件同步会干扰 Hermes 写记忆)
- Windows 端接受时选 **Receive Only(仅接收)**

## ⚠️ 关键坑:Windows Hermes 的 home 路径

**Windows 上 HERMES_HOME 是 `C:\Users\<user>\AppData\Local\hermes`,不是 `~/.hermes`!**
- 迁移包/提示词若让用户放 `.hermes\`,同步过去的内容 Hermes 根本读不到
- 正确做法:先确认 HERMES_HOME(环境变量或询问 Windows 端 Hermes),Syncthing 文件夹 path 直接指向 `AppData\Local\hermes\memories`、`...\skills`
- 症状:文件同步成功、状态 idle,但 Hermes 记忆/技能没变化 → 查路径是否对

## Receive Only 模式的语义

- 服务器改动 → 自动推给 Windows ✅
- Windows 本地改动 → 不反向同步,服务器下次推送会覆盖(本机改动丢失)
- **后果**:Windows 端自己沉淀的记忆会被覆盖 → 本机特有环境信息(GitHub 直连受限、本地软件等)放 **vault**(双向)而非 memories
- 冲突几乎不发生(单向);同名技能冲突时 Windows 端留 `.sync-conflict` 副本

## 技能加载与 .bundled_manifest

- 同步的 skills 目录带 `.bundled_manifest`(服务器内置清单),Windows 端加载时按它判定"内置"并去重显示内置版 —— 同名沉淀技能可能被"吃掉"(表现为 local 技能数 < 沉淀技能数)
- 验证:Windows 端 `hermes skills list`,对比沉淀技能是否都在;缺失时检查 manifest 干扰

## 投稿箱机制(Windows 沉淀技能回流)

1. Windows 端沉淀技能 → 复制到 vault/投稿箱/(双向同步,服务器可见)
2. 服务器每周 cron 审核(每周日 19:00):读 SKILL.md 判断通用性
   - 通用(跨平台方法论)→ `cp -r 到 ~/.hermes/skills/<分类>/` → sendonly 自动广播回 Windows
   - 不通用(依赖 Windows 特有环境)→ 不并入,投稿箱清理,Windows 本地保留
3. 成本:同步 0 token;每周审核约 1 万 tokens(≈1 分钱)

## ⚠️ platforms 门控:并入前必须改通用,否则"并入=无效"

Hermes 按 SKILL.md frontmatter 的 `platforms` 字段按宿主 OS 过滤技能加载(2026-08 实测:4 个 `platforms: [linux]` 的沉淀技能被 Windows 端正确过滤,`hermes skills list` 不显示,属预期设计)。

- **坑**:Windows 端沉淀的技能 frontmatter 大概率是 `platforms: [windows]`(或没写)。直接并入服务器后,Linux 端 Hermes 同样会把它过滤掉 → 广播回 Windows 的只是它本来就有的,并入了个寂寞。
- **修复**:投稿审核 cron 并入前,把目标技能 frontmatter 的 `platforms` 改为 `[linux, windows]`(或去掉该字段 = 全平台)。
- 反向同理:服务器端 Linux 专属技能(apt/systemctl 运维类)保持 `platforms: [linux]` 是**正确**的,Windows 端自动不加载;用户要看内容走 Obsidian 技能库镜像(文件不门控)。

## 技能库镜像会污染知识库目录/index

把 `~/.hermes/skills` 镜像到 `vault/技能库/`(Obsidian 可翻全文)后,必须**双向排除**,否则 85 个 SKILL.md 会被当笔记:
- `kb_inventory.py` 的 `SKIP_DIRS` 加 `'技能库'`
- "知识库整理"cron 的 prompt 排除列表加 `技能库/`(否则登记进 index.md)
- 镜像脚本只复制**沉淀技能**(对比 `.bundled_manifest` 判定非内置);⚠️ 嵌套分类目录(如 `mlops/evaluation/<skill>`)用 shell 一层遍历会误把 `evaluation` 当技能名 —— 用 Python 递归找 SKILL.md,技能名取 SKILL.md 所在目录名

## Windows 端接受文件夹时遇到的坑(客户端侧)

- **folder marker missing**:目标目录已有内容但缺 `.stfolder` → 手动创建空 `.stfolder` 文件即可
- **revert 只更新索引不落盘**:清空目录 + 重建配置 + revert 后才真正拉取
- **双进程启动卡死**:杀进程后干净重启单实例(SyncTrayzor + 手动进程并存)

## 完整执行顺序(验证过)

1. 服务器:API 建 sendonly 文件夹(memories/skills)+ .stignore
2. 服务器:建 vault/投稿箱/ + README
3. Windows:确认 HERMES_HOME → 接受文件夹(receiveonly)→ 路径指向真实 home
4. Windows:备份本机旧 memories/skills → 等同步 → 验证 MEMORY.md/技能数
5. 服务器:配投稿审核 cron(每周日)
6. 收尾:Windows 本机环境信息写 vault(entities/Windows环境.md),别放 memories
