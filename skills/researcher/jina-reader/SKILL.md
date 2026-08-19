---
name: jina-reader
description: "Use when web_extract fails on JS-rendered pages — convert URL to markdown via r.jina.ai."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [research, web, extraction]
---

# Jina Reader(URL → Markdown)

当 web_extract(Tavily)抓取失败或页面是 JS 渲染(SPA)时,用 r.jina.ai 兜底转 Markdown。

## When to Use
- web_extract 返回 "Failed to fetch url" / 空内容
- 页面是 JS 渲染(curl 拿到空壳,如 WorkBuddy 官网)
- 需要把 URL 快速转成干净文本

## 用法
```bash
# 基础:URL 直接拼在 r.jina.ai/ 后
curl -s --max-time 20 "https://r.jina.ai/<完整URL>"

# 绕过缓存快照(要最新内容)
curl -s -H "x-no-cache: true" "https://r.jina.ai/<完整URL>"
```

返回内容带 `Title:` / `URL Source:` 头,正文是 markdown,可直接用。

## 注意
- 免费无 key,国内直连可用(已验证 2026-08-13)
- 免费层有速率限制,批量抓取要加间隔(约 20 req/分钟)
- 对 PDF/图片页效果差,用 ocr-and-documents 替代

## 验证
```bash
curl -s "https://r.jina.ai/https://example.com"   # 应返回 markdown 正文
```
