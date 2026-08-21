---
title: "MCP servers (stdio) on a headless Hermes server"
created: 2026-08-20
updated: 2026-08-20
type: note
---
# MCP servers (stdio) on a headless Hermes server

Verified 2026-08 on Aliyun ECS (Ubuntu 22.04, 3 Mbps link, all Hermes processes as
systemd services, root). Use when wiring an external MCP server (e.g. Notion) into
Hermes on a server.

## Config shape

```bash
hermes config set mcp_servers.notion.command "npx"
hermes config set mcp_servers.notion.args '["-y","@notionhq/notion-mcp-server"]'
hermes config set mcp_servers.notion.env.NOTION_TOKEN "{{NOTION_TOKEN}}"
hermes config set mcp_servers.notion.connect_timeout 90
```

Then restart the gateway + dashboard (`systemctl restart hermes-gateway hermes-dashboard`).
MCP discovery happens at process start — **no hot reload**. Cron jobs run in the gateway
process, so they only get the MCP tools after the gateway restart.

## Pitfall 1: `hermes config set` stores lists as STRINGS

`hermes config set mcp_servers.notion.args '["-y","pkg"]'` writes a YAML string
(`args: '["-y","pkg"]'`), not a list. Hermes `_run_stdio` does `args = config.get("args", [])`
then splats `*args` — a string splats into single characters.
Symptom: node dies with `Error: Cannot find module '~/.hermes/['` (each char of the
string became an argv element). Fix: convert that one line to a real YAML list
(backup first):

```python
import re, yaml
p = '~/.hermes/config.yaml'; s = open(p).read()
s = re.sub(r"(^[ \t]+args: )'(\[.*?\])'(.*)$", r"\1\2\3", s, flags=re.M)
open(p, 'w').write(s)
assert isinstance(yaml.safe_load(open(p))['mcp_servers']['notion']['args'], list)
```

## Pitfall 2: npx shims break under the filtered subprocess env

Hermes passes stdio MCP subprocesses a FILTERED env (PATH/HOME/USER/LANG/LC_ALL/TERM/
SHELL/TMPDIR + XDG_* + your `env:` block only — no npm config, no nvm paths).
Debian's `/usr/bin/npx` resolves packages via its own npm prefix and shims through sh;
in this env it dies with `sh: line 1: [: syntax error: '-' unexpected`, and the client
logs `McpError: Connection closed` after 3 attempts
(`state: connecting → parked`). Workaround that works: skip npx entirely, exec the
package entry with node directly:

```bash
npm install -g @notionhq/notion-mcp-server   # preinstall — slow links take minutes
hermes config set mcp_servers.notion.command "/usr/bin/node"
# args = absolute path of the package entry, e.g.:
#   ~/.nvm/versions/node/v22.23.2/lib/node_modules/@notionhq/notion-mcp-server/bin/cli.mjs
# (the ~/.nvm/.../bin/notion-mcp-server symlink also resolves there)
```

Note `_resolve_stdio_command` rewrites bare `npx/npm/node` to whatever `shutil.which`
finds under the filtered PATH — under systemd that is `/usr/bin/npx` (Debian), NOT the
nvm one your interactive shell uses. Prefer absolute paths for command.

## Pitfall 3: "process still running" ≠ "server ready" on slow links

`timeout 25 npx -y pkg` exiting 124 (still running) does NOT mean the server is up —
on a 3 Mbps link npx spends minutes downloading. Hermes' 3 connection attempts fail
within ~10 s → parked. Pre-install the package globally first, then verify with a real
MCP handshake (initialize over stdin) BEFORE restarting the gateway.

## Debugging

- MCP subprocess stderr → `~/.hermes/logs/mcp-stderr.log` (per-attempt
  `starting MCP server 'X'` headers). This is where `sh: line 1: [` shows up.
- Gateway: `journalctl -u hermes-gateway --since "1 minute ago"` → look for
  `WARNING tools.mcp_tool: MCP server 'notion' failed initial connection after 3 attempts`.
- Watchdog wrapper: every stdio server is wrapped in
  `mcp_stdio_watchdog.py --ppid <hermes_pid> -- <cmd>`. Its orphan detection kills the
  child when `getppid() != ppid`. If you smoke-test the wrapper with a FAKE `--ppid`, it
  SIGTERMs the just-spawned child (exit code 241 = -15) — that is correct behavior, not
  a bug. To test the real path, run the node command directly under the filtered env.
- Confirm a live connection: `ps aux | grep cli.mjs` shows
  `mcp_stdio_watchdog.py --ppid <gateway-pid>` + the node child running.
- After a fix: `systemctl restart hermes-gateway`; verify absence of the parking warning.

## Notion-specific notes (via MCP / REST)

- Internal integrations CANNOT create pages at workspace root:
  `parent: {"type":"workspace"}` → 400 `validation_error`
  (`Internal integrations aren't owned by a single user`). Use a `page_id` (or
  `database_id`) parent instead; the user can drag the page to root in the Notion UI.
- If a Notion MCP tool call fails with a bare `McpError('')`, fall back to the REST API
  with the same token: `curl -X POST https://api.notion.com/v1/pages -H "Authorization:
  Bearer {{NOTION_TOKEN}}" -H "Notion-Version: 2022-06-28" -d @payload.json`.
- `Notion-Version: 2022-06-28` works for the operations used here (create page/database,
  query, search).
- **嵌套子库(database-in-database)404**:若某个 database 是另一个 database 页里的内嵌数据源,integration 只共享了父库时,直接 POST/query 子库 ID 返回 404 `object_not_found`(但 `/v1/search` 能看到它)。排查:GET `/v1/databases/<父库ID>` 可访问 → 写父库;或者让用户在 Notion 里把子库单独共享给 integration。记录在记忆里的"提醒库 ID"若报 404,先验证是否为嵌套子库(2026-08 实测:提醒库有两个同名 data source,可写的是父库)。
