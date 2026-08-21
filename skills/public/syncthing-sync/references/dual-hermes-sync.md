---
title: "双 Hermes 主从同步与技能投稿闭环(2026-08 实战验证)"
created: 2026-08-20
updated: 2026-08-20
type: note
---
# 双 Hermes 主从同步与技能投稿闭环(2026-08 实战验证)

场景:用户有服务器 Hermes(Ubuntu,阿里云)与 Windows Hermes 两个实例,原则是**以服务器为准**(主从)。本文档记录记忆/技能单向同步的实现、踩坑、以及 Windows 沉淀技能的投稿审核闭环。

## 1. 架构

```
服务器(权威,Ubuntu)                    Windows(分身)
memories/ ──sendonly──► receiveonly ──► %LOCALAPPDATA%\hermes\memories
skills/   ──sendonly──► receiveonly ──► %LOCALAPPDATA%\hermes\skills
vault(知识库) ◄────── sendreceive 双向 ────► D:\ObsidianVault
投稿箱(vault/投稿箱/) ◄── 双向(vault 内) ──► 投稿箱
```

- 记忆/技能:单向(sendonly→receiveonly),服务器权威,Windows 本地改动不回传且会被服务器版覆盖。
- 知识库:双向(共同大脑,两端都写)。
- 会话历史(state.db):**不同步**(SQLite 双端并发写会损坏),各端独立。
- config.yaml/.env/cron:各端独立。

## 2. 用 REST API 建 sendonly 文件夹

```bash
APIKEY=$(grep -oP '(?<=<apikey>)[^<]+' ~/.config/syncthing/config.xml)
WIN="<Windows设备ID>"   # GET /rest/config/devices 查
# 以 vault 文件夹为模板,改 id/path/type/devices 后 PUT
curl -s -H "X-API-Key: $APIKEY" http://127.0.0.1:8384/rest/config/folders/vault -o /tmp/tmpl.json
# python: f['id']='memories'; f['path']='~/.hermes/memories'; f['type']='sendonly'
#         f['devices']=[{'deviceID': WIN, 'introducedBy':'', 'encryptionPassword':''}]
#         f['versioning']={'type':'','params':{},...}  # sendonly 不需要回收站
# PUT /rest/config/folders/memories
```

注意:devices 列表自动含本机(正常,勿删)。type 可选值:`sendreceive`/`sendonly`/`receiveonly`。

## 3. .stignore

memories/ 和 skills/ 目录内放 `.stignore`:
```
// 排除锁文件(双端同时锁会干扰写入)
*.lock
*.tmp
```

## 4. 踩坑(全部实战)

| 坑 | 现象 | 解决 |
|---|---|---|
| 同步路径错误 | Windows 端"磁盘有技能但 Hermes 加载不到" | Windows Hermes home 是 `%LOCALAPPDATA%\hermes`(AppData\Local\hermes),**不是 `~/.hermes`**!同步路径必须指向实际读取位置;改 path 用 PUT 更新文件夹配置,旧位置副本删除 |
| platforms 门控 | Windows 端不加载部分技能 | Hermes 按宿主 OS 过滤技能 frontmatter `platforms`。`platforms: [linux]` 的技能 Windows 端不加载 —— 是设计,不是故障。跨端技能省略 platforms 或含多平台 |
| 重复投稿死循环 | 技能并入服务器后从投稿箱删除 → 下次扫描又投 | Windows 端维护"已投清单"状态文件(记录技能名),扫描时跳过已投过的 |
| 同步未完成就扫描 | 把"服务器已有、本地未删"的旧技能误当新沉淀 | 投稿前先等 memories/skills 的 needBytes=0 |
| 网络抖动重复触发 | 计划任务频繁执行 | 防抖:10 分钟内不重复(状态文件记上次执行时间) |
| 首次同步合并混乱 | Windows 已有本地记忆/技能 | 先备份(.bak)再接受,让服务器全量覆盖 |
| 开机没网 | 投稿脚本连不上 | 等网络最多 5 分钟,TCP 探测服务器 22000;超时静默退出,下次触发再试 |

## 5. 投稿审核闭环(Windows 沉淀技能 → 服务器)

```
Windows 开机/断网重连 → 计划任务触发(**2 触发器,事件驱动**:登录 + 网络事件 Event ID 10000,无固定时间——用户场景是"用才联网、不用断网、常开关机",定时兜底会空跑/漏投,事件驱动最贴合)
  → 防抖 → 等网络 → 等同步(needBytes=0) → 扫描本地 skills
  → 过滤:内置(.bundled_manifest)+ .archive + 已投清单
  → 复制新沉淀技能到 vault/投稿箱/<技能名>/  → 更新已投清单
  → (vault 双向同步,服务器可见)
服务器每周日 19:00 审核 cron:
  → 读投稿箱,判断通用性(是否依赖 Windows 特有环境/服务器是否有使用价值)
  → 通用:复制到 ~/.hermes/skills/<分类>/<技能名>/,并把 frontmatter platforms 改为通用(linux+windows)
    → sendonly 自动广播回 Windows(两端都有)
  → 不通用:删除投稿箱条目(Windows 本地保留)
  → 推送微信汇报(投稿 X / 并入 Y / 不通用 Z)
```

- 内置技能判定:读 `~/.hermes/skills/.bundled_manifest`(格式 `name:hash`/行),非内置即沉淀。
- ⚠️ **投稿必须再排除"服务器已有技能"**(2026-08-13 首次实测教训):服务器单向同步过去的沉淀技能(hermes-server-ops、syncthing-sync、obsidian-* 等)在 Windows 端同样"不在 .bundled_manifest 里",会被误判为新沉淀而误投。首次运行投了 25 个,其中 22 个是服务器已有/内置,1 个 Windows 独有但功能重复,0 个有效 → 全部清理。修复:submit_skills.py 增加排除表 = 读 `D:\ObsidianVault\技能库\`(服务器沉淀技能镜像目录)里的技能名,跳过这些;服务器审核侧同理,发现投稿箱里是服务器已有技能 → 直接清理不并入。
- Windows 端自动投稿脚本要点:`submit_skills.py` 流程见上;Syncthing API key 从 `%LOCALAPPDATA%\Syncthing\config.xml` 读;Python 用 Windows Hermes 自带运行时。
- 用户 Windows 端 Syncthing 版本为 v1.18.1(与服务器 v2.1.3 互通正常,但建议升级)。

## 6. 知识库目录规划(双 Hermes 协同)

- vault 中文命名(≤15字),concepts/ 按主题 2 层封顶(旅行/健康/学习/生活/工作/项目),entities/ 存系统档案。
- `entities/双Hermes技能同步闭环.md`:完整闭环文档(状态总览表 = 已完成 vs 明日待办),用户明天直接发文档即可开工。
- `entities/Windows环境.md`:Windows 本机环境记录(双向同步,不会被 receiveonly 覆盖 —— 记忆里放不下/会被覆盖的本地知识都进这里)。
- 后续计划:frp + OpenSSH Server 实现服务器 SSH 直控 Windows Hermes(替代用户转述),待办已存 Notion。完整方案文档:`vault/entities/远程操控WindowsHermes方案.md`(架构/组件/决策通道/验证计划/可拓展性)。

## 7. 决策通道(双 Hermes 异步问答,2026-08 设计验证)

问题:Windows Hermes 不会返回执行全过程,服务器看不到它的中间输出 —— 解决:**契约式沟通**,只传"问题 → 答案 → 结果",不传过程。

- 载体:`vault/决策通道/`(双向同步,README.md 定义规则):
  - `待决策.md` — Windows Hermes 提问方写入(格式:时间/发起/问题/可选方案/需要)
  - `已决策.md` — 服务器答复方写入(时间/对应问题/决定+理由)
- Windows Hermes 行为规则(写进其本地技能,记忆是 receiveonly 会被覆盖):
  1. 能自主判断 → 选最合理方案继续,事后在回执说明理由
  2. 必须服务器决策 → 写待决策.md,**不询问用户**
  3. 任务开始/结束时检查已决策.md,按答复继续
- 服务器侧:每日检查待决策.md 未处理问题 → 答复 → 有价值的决策沉淀进记忆
- **Token 优化**:每日检查用 cron **monitor_script 模式**(输出 hash 无变化 = 静默 0 token;有新增提问才触发 agent 答复,~1K token/次)
- 验证边界:服务器侧模拟验证(文件结构/处理流程/同步)已通过;**端到端必须实测**(配置完成后第一步:让 Windows Hermes 写测试问题 → 服务器答复 → 它确认收到 → 闭环成立才继续)

## 8. 最高权限决策模式(用户明确偏好)

- 用户授权服务器在所有技术选择上直接决定,不给用户出选择题。
- 给 Windows Hermes(或任何远程 agent)的指令必须写成**确定性步骤**(无"如果…或者…"选项),它只执行不决策。
- 它遇到必须决策的 → 走决策通道(第 7 节),而不是回头问用户。
- 用户唯一保留的人工步骤 = 物理操作(如阿里云安全组点按钮),要给截图级指引。

## 9. 可拓展性:新电脑接入(用户需求)

- 换新电脑要能快速落地同一体系 → 一切 Windows 端配置**源头化、脚本化**:
  - 部署包存 vault:`vault/部署/windows_bootstrap.ps1`(一键完成:接受 memories/skills/vault 文件夹 receiveonly、建投稿脚本+计划任务、开 OpenSSH Server、装 frpc+隧道、写决策通道规则)+ `新电脑接入手册.md`
  - 脚本**变量化**(用户名/路径自动检测,不写死)
  - 服务器端登记新设备 ID → 共享文件夹 → 通信闭环测试 → 上线
- 与服务器迁移手册互为补充(服务器到期→迁移手册;电脑更换→接入手册)。

## 10. Notion 写入(双 Hermes 协同配套)

- MCP post_page 工具不可用(空错误/404)→ 用 curl 直连 `POST /v1/pages`(Notion-Version: 2022-06-28,走 Clash 代理)。
- ⚠️ **嵌套数据库无权限 404**:提醒库存在"可写库"与"无权限嵌套库"两个 ID,搜索 API 能看到嵌套库但写不进去;token 提取用 `grep -m1 NOTION_TOKEN config.yaml | sed` 处理。
- 中文内容 JSON 用 Python 脚本构造请求(避免 shell 转义问题)。
