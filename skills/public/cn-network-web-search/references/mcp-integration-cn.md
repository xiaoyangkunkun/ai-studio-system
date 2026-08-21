---
title: "Hermes MCP 接入 + Notion 内部集成限制(国内环境实战)"
created: 2026-08-20
updated: 2026-08-20
type: note
---
# Hermes MCP 接入 + Notion 内部集成限制(国内环境实战)

从 2026-08 一次真实接入中沉淀的经验(服务器:国内阿里云, Hermes gateway
以 systemd 运行)。适用:把 Notion 官方 MCP(@notionhq/notion-mcp-server)
接进 Hermes,并用来建数据库/写日志/跑复盘类 cron。MCP 配置坑同样适用于
其他 stdio MCP 服务器。

## 1. 内部集成(internal integration)的关键限制

- **不能在工作区根级创建页面。** 内部集成不是单一用户所有,API 返回:
  `Provide a parent.page_id or parent.database_id parameter to create a page,
  or use a public integration with insert_content capability`。
  解决:parent 用某个已有页面的 `page_id`(如"日常"页),建完后再让用户在
  Notion 里手动拖到根级。
- **必须把页面共享给集成**,否则 API 404:页面 ... 菜单 → Connections →
  选集成名。搜索 API(`POST /v1/search`)能列出已共享的页面/数据库。
- 集成 token 验证:`curl -s https://api.notion.com/v1/users/me -H
  "Authorization: Bearer ntn_..." -H "Notion-Version: 2022-06-28"`。
  返回 bot 对象 + workspace_name 即有效。
- 版本差异:新 API 里"数据库"叫 data source,查询用
  `/v1/data_sources/{id}/query`;但 `mcp_notion_*` 工具的 POST page 接口仍
  接受 `parent.page_id` / `parent.database_id` 两种形式。创建数据库用
  `POST /v1/databases`(parent 为 page_id)。本机实测 2022-06-28 版本头可用。

## 2. Hermes MCP 接入步骤与两个必踩的坑

配置(写入 ~/.hermes/config.yaml 的 mcp_servers):

```yaml
mcp_servers:
  notion:
    command: /usr/bin/node                      # 见坑2,不要用 npx
    args:
      - ~/.nvm/versions/node/v22.23.2/lib/node_modules/@notionhq/notion-mcp-server/bin/cli.mjs
    env:
      NOTION_TOKEN: {{NOTION_TOKEN}}
    connect_timeout: 90
```

**坑 1:`hermes config set` 无法写 list 类型。**
`hermes config set mcp_servers.notion.args '["..."]'` 会把值存成 YAML
字符串(`args: '["..."]'`),Hermes 读取后 `*args` 展开字符串 → 每个字符
变成独立参数(node 收到 `[` 当模块路径,报 `Cannot find module '~/.hermes/['`)。
修法:备份 config.yaml 后,用脚本把那一行从 `args: '[...]'` 改成真正的
YAML 列表(去掉引号),再 `yaml.safe_load` 验证类型是 list。

**坑 2:Debian 的 npx 在 Hermes 过滤环境下必挂。**
systemd 服务的 PATH 指向 Debian node(/usr/bin/npx,npm 10.8.2),其 shim
机制在 Hermes 的过滤 env 下报 `sh: line 1: [: syntax error: '-' unexpected`,
MCP 连接失败("Connection closed")。绕开 npx:直接
`command: /usr/bin/node`,args 指到全局安装的 cli.mjs 绝对路径
(npm install -g @notionhq/notion-mcp-server 后
`~/.nvm/versions/node/v22.23.2/bin/notion-mcp-server` 是 symlink,
直接用 node + 真实 cli.mjs 路径最稳)。

## 3. 排查 MCP 连接失败的工具

- MCP 子进程 stderr → `~/.hermes/logs/mcp-stderr.log`(Hermes 统一重定向,
  每行前有 `starting MCP server 'xxx'` 标记)。这是第一手线索。
- 手动握手测试(不经 Hermes):

```python
import subprocess, json, time, os
env = dict(os.environ); env['NOTION_TOKEN'] = '{{NOTION_TOKEN}}'
p = subprocess.Popen(['npx','-y','@notionhq/notion-mcp-server'],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE, env=env)
time.sleep(3)
p.stdin.write(b'{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"t","version":"1"}}}\n')
p.stdin.flush()
print(p.stdout.readline()[:300])
```

- Hermes 会把 stdio MCP 命令包装成 watchdog(`mcp_stdio_watchdog.py`),
  其孤儿检测用 `--ppid <hermes_pid>`;手动测试时给假 ppid(如 99999)会被
  误判"父进程已死"而杀掉子进程(退出码 241 = -15),这是预期行为不是 bug。
- 验证连接成功:`ps aux | grep cli.mjs` 应看到 watchdog + node 两个进程;
  网关日志无 `MCP server 'notion' failed` 即正常。
- 大包首次下载慢(3 Mbps 带宽):`npx` 首次要下载整个 npm 包,25 秒内
  服务器根本没起来,容易误判"正常"。先 `npm install -g` 预装再连。

## 4. 复盘类 cron 的成熟模式(晚间复盘 + 每周复盘)

- 数据源:SQLite 会话库 `~/.hermes/state.db`(表 sessions / messages,
  role=user/assistant, timestamp 为 epoch 秒)。写一个当日对话提取脚本
  (按本地时区过滤当天,排除 source='cron' 的会话和 `[IMPORTANT` 注入消息),
  作为 cron 的 `script:` 参数,stdout 自动注入 agent prompt。
- 写入目标:在用户"日常"页面下建两个 database——"每日日志"(日期/标题/
  正文/状态)与"每周复盘"(周数/日期范围/正文)。cron prompt 里写死
  database id,要求 agent"先查日期是否已有记录,有则更新无则新建"避免重复。
- 投递到微信:`deliver: weixin:<user_id>`;cron 的最终回复即推送内容。
- 端到端验证:创建任务后立即 `cronjob action=run` 手动触发一次,再
  `POST /v1/databases/{id}/query` 确认落库,比等定时器可靠。
