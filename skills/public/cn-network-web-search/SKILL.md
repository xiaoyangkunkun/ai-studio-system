---
name: cn-network-web-search
description: "Use when a CN/GFW server needs Hermes web_search working."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [china, gfw, web-search, searxng, bing, bridge, hermes-config]
---

# CN Network Web Search (国内网络搜索桥接)

When a Hermes server runs in mainland China, built-in web search providers
fail because their backends are unreachable: Google, DuckDuckGo, HuggingFace,
Exa, Tavily, Firecrawl and even public SearXNG instances all time out (curl
returns `000`). The one major engine that **is** reachable is
`https://cn.bing.com` (HTTP 200, ~0.4s). Chinese media sites (量子位, 机器之心)
are also mostly JS-rendered / anti-bot, so direct scraping is unreliable —
though their RSS feeds (e.g. `https://www.qbitai.com/feed`) usually work.

The fix: run a tiny zero-dependency Python HTTP server that scrapes
**360 搜索 (so.com) as primary engine + cn.bing.com as fallback** and returns
results in the **SearXNG JSON format**, then point Hermes' `web` toolset at
it via the `searxng` backend. No Docker, no pip deps, ~9 MB RAM, survives
reboots via systemd.

**Engine choice (2026-08 lesson):** cn.bing.com's Chinese long-tail query
relevance is terrible — "福州餐厅推荐" returns 福州市百科/旅游攻略/政府网站,
never restaurants. 360 搜索 (so.com) returns highly relevant Chinese results
for the same query. Bridge now tries `so360_search()` first, falls back to
`bing_search()` when empty.

## When to use

- `web_search` tool is missing from the session (toolset not enabled) OR
- `web_search` returns errors/empty while `curl https://cn.bing.com` succeeds
- Server located in mainland China / behind GFW; any overseas API times out

## Setup (3 parts)

### 1. Deploy the bridge service

Copy `scripts/bing_search_bridge.py` to `~/.hermes/scripts/` (or anywhere),
then register as a systemd service (adjust port if 8899 is taken — note
宝塔面板/BT-Panel commonly occupies 8888):

```bash
cp scripts/bing_search_bridge.py ~/.hermes/scripts/
chmod +x ~/.hermes/scripts/bing_search_bridge.py

cat > /etc/systemd/system/bing-search-bridge.service << 'EOF'
[Unit]
Description=Bing Search Bridge (SearXNG-compatible API for Hermes web_search)
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 ~/.hermes/scripts/bing_search_bridge.py
Restart=always
RestartSec=3
User=root

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now bing-search-bridge
curl -s http://127.0.0.1:8899/healthz        # expect {"ok": true}
```

Quick manual test in SearXNG API shape:

```bash
curl -s 'http://127.0.0.1:8899/search?q=test&format=json&pageno=1' | python3 -m json.tool | head
```

### 2. Configure Hermes

```bash
# enable the web toolset (takes effect in NEW sessions only)
hermes tools enable web

# point the searxng backend at the bridge
hermes config set web.backend searxng
hermes config set web.search_backend searxng

# SEARXNG_URL goes in .env (secret-style file), NOT config.yaml
echo 'SEARXNG_URL=http://127.0.0.1:8899' >> ~/.hermes/.env
```

Restart the gateway so messaging-platform sessions pick up the web toolset:
`systemctl restart hermes-gateway` (WeChat disconnects briefly, auto-reconnects).

### 3. Verify end-to-end (before trusting it)

```bash
cd /usr/local/lib/hermes-agent && /usr/local/lib/hermes-agent/venv/bin/python -c "
import os; os.environ['SEARXNG_URL'] = 'http://127.0.0.1:8899'
from tools.web_tools import web_search_tool
print(web_search_tool('2026 最新国产大模型', limit=5)[:500])"
```

Expect structured results (title/url/description/position). Also check
`web_tools._get_backend()` returns `searxng` and `check_web_api_key()` is True.

## Pitfalls

- **Tool changes are per-session.** `hermes tools enable web` only affects
  sessions started after the change. The current CLI session keeps its old
  toolset; tell the user to open a new session, and restart the gateway for
  messaging platforms.
- **Bing query quality (fixed with 360).** cn.bing.com's Chinese long-tail
  relevance is poor: "福州餐厅推荐" returns 城市百科/旅游攻略 (generic city
  results), and even www.bing.com?mkt=zh-CN is the same. **360 搜索
  (https://www.so.com/s?q=...) is the primary engine** — highly relevant
  Chinese results (verified 2026-08 for restaurant/food queries). Fallback
  order: so360 → cn.bing. If a Chinese query still looks off, give concrete
  keywords and multi-round search. Note so.com result URLs are
  `so.com/link?m=...` jump links — they 302-redirect to the target; follow
  redirects (curl -L) when extracting.
- **Port collisions.** 8888 is BT-Panel's default; 9119 is Hermes dashboard.
  Pick a free port and update both the script and SEARXNG_URL.
- **`sh: line 1: [ ...` errors** in `~/.hermes/logs/mcp-stderr.log` during MCP
  startup are a *separate* problem from web search — that is the Debian
  `npx` shim failing under Hermes' filtered env. Not related to this bridge.
- **360 对英文/特定词/长尾查询支持差(2026-08-15 实测)** — "MiMo V2.5 LMArena"、
  "OpenCompass 分数"、"artificialanalysis.ai MiMo" 等查询反复返回小米官网等泛站结果。
  对策:web_search 只用于中文泛查询;英文/榜单/特定站点的查询直接用 Tavily API curl:
  `curl -s "https://api.tavily.com/search" -H "Content-Type: application/json" -d '{"api_key":"<KEY from ~/.hermes/.env>","query":"...","search_depth":"advanced","max_results":8}'`
  Tavily 对 artificialanalysis.ai、venturebeat.com、superclueai.com 等站点抓取效果好。
  JS 渲染榜单纯文本取不到时,优先搜第三方转载(如知乎评测引用榜单数字)或官方 GitHub 数据源。
- **Don't use public SearXNG instances** — every one tested from a CN server
  timed out (searx.be, searxng.site, paulgo.io, search.bus-hit.me → 000).
- **web_extract 需要独立后端(已修复 2026-08-13)** — searxng 是 search-only
  (`supports_extract() == False`),报错
  `SearXNG is a search-only backend and cannot extract URL content`。
  **根因**:`web.extract_backend` 未配置,回退到 searxng。**修复**:
  `web.backend`/`web.search_backend` 保持 searxng(搜索不动),
  单独给 extract 配一个支持抓取的后端:
  ```bash
  hermes config set web.extract_backend tavily
  echo 'TAVILY_API_KEY=tvly-...' >> ~/.hermes/.env
  ```
  可选后端 firecrawl / tavily / exa / parallel(全部要 API key,全部有
  免费额度;Tavily 免费约 1000 次/月,国内直连可达无需代理,2026-08-13
  实测 example.com/知乎/腾讯云全通)。**生效方式:当前会话立即生效,
  无需重启 gateway**(与 search toolset 的 per-session 不同)。备用 key
  存档模式与验证命令见 `references/tavily-extract-cn.md`。反爬站
  (如 workbuddy.cn 官网)即使换 Tavily 也可能 `Failed to fetch`,属站点
  问题不是配置问题。

## References

- `scripts/bing_search_bridge.py` — the zero-dependency bridge server
  (SearXNG-format JSON API over cn.bing.com; also serves `/healthz`).
- `references/gfw-research-methodology.md` — adaptive research patterns when
  web_search returns garbage on CN servers (direct URL extraction strategy,
  multi-language parallel search, cascade extraction from known sources).
- `references/mcp-integration-cn.md` — Hermes MCP setup quirks hit while
  wiring Notion MCP on a CN server (config set storing strings instead of
  lists, Debian npx shim failing under Hermes' filtered env, workspace-root
  page creation limits for internal integrations) plus the proven cron
  pattern for daily/weekly journal reviews.
- `references/tavily-extract-cn.md` — web_extract 独立后端的完整修复细节:
  Tavily 配置/双 key 存档/curl 连通性预检/实测站点清单(含反爬站失败案例)。
