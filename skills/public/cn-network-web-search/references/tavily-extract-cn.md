# Tavily extract 后端(国内服务器,2026-08-13 实测)

## 背景

CN 服务器上 web_search 用 searxng bridge(见 SKILL.md)正常,但 `web_extract`
报 `SearXNG is a search-only backend and cannot extract URL content`。
根因:`web.extract_backend` 未配置时回退到 searxng,而 searxng 只搜不抓。

## 配置(3 行,当前会话立即生效,无需重启 gateway)

```bash
# 1. 选 extract 后端(可选 firecrawl/tavily/exa/parallel,都要 key,都有免费额度)
hermes config set web.extract_backend tavily
# 2. key 放 .env(secret 文件,不放 config.yaml)
echo 'TAVILY_API_KEY=tvly-...' >> ~/.hermes/.env
# 3. 验证:直接用 web_extract 工具抓一个真实页面
```

- 搜索配置(`web.backend` / `web.search_backend` = searxng)**保持不动**,
  三个键相互独立,只改 extract 不影响搜索。
- 生效机制:web_extract 每次调用动态解析 provider(registry),因此
  **当前会话立即生效**——不像 `hermes tools enable` 那样 per-session。

## 免费额度与 key 管理

- Tavily 免费层约 1000 次/月(注册 app.tavily.com,邮箱即可)。
- **双 key 存档模式**:一个主 key + 一个备用 key(不同邮箱注册),都写进
  .env(如 `TAVILY_API_KEY_2=`),主 key 额度将尽时切换;等于双倍免费额度。

## 先测 key 与连通性(curl,不依赖 Hermes)

```bash
curl -s --max-time 12 -X POST "https://api.tavily.com/extract" \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"urls":["https://example.com"]}'
# HTTP 200 + results[].raw_content = 通
```

- **国内直连可达**(实测 1.1s,无需 Clash 代理)。

## 实测结果(2026-08-13)

| URL | 结果 |
|---|---|
| example.com | ✅ 全文 |
| zhuanlan.zhihu.com 教程 | ✅ 3.3 万字全文 |
| cloud.tencent.com 产品页 | ✅ 全文(官方一手资料) |
| workbuddy.cn 官网 | ❌ `Failed to fetch url`(JS 渲染+反爬,站点问题非配置问题) |

## 注意

- 抓下来的全文会存 `~/.hermes/cache/web/<domain>-<hash>.md`,
  大页用 read_file 分页读中间部分。
- JS 渲染 + 强反爬的站(如 workbuddy.cn)即使换后端也可能抓不到;
  此时可改用 web_search 拿官方信息片段,或让用户补充一手资料。
