---
title: "搜索桥接 HTML 解析结构(维护参考)"
created: 2026-08-20
updated: 2026-08-20
type: note
---
# 搜索桥接 HTML 解析结构(维护参考)

bing_search_bridge.py 的两个引擎解析结构(2026-08 验证)。

## 360 搜索(so.com)— 主引擎

- 结果项:`<li class="res-list">...</li>`(不是 b_algo!)
- 标题:`<h3 ...><a href="..." ...>标题</a>`,有时 a 有 `target="_blank"` 重复属性
- 摘要:`<p class="res-desc...">...</p>`(class 可能带后缀,用 `res-desc[^"]*`)
- URL:多为 `so.com/link?m=<base64>` 跳转链接(302 到目标站);抓取目标内容需 follow redirect(curl -L)
- 解析正则:
  ```python
  r'<li class="res-list".*?</li>'           # 结果块(需 re.S)
  r'<h3[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>'  # url+title
  r'<p class="res-desc[^"]*"[^>]*>(.*?)</p>'           # 摘要
  ```
- 无结果时(如反爬/改版)返回空列表 → 桥接自动 fallback 到 cn.bing(handler 里已接线)

## cn.bing.com — 兜底引擎

- 结果项:`<li class="b_algo">...</li>`
- 标题:`<h2><a href="...">...</a>`
- 摘要:`<p>...</p>`(块内第一个 p)
- ⚠️ 中文长尾查询相关性差(福州餐厅推荐 → 城市百科/旅游攻略),所以只做兜底

## 诊断速查

- `curl -s "http://127.0.0.1:8899/search?q=测试&format=json"` 看返回
- 页面抓取:`curl -s "https://www.so.com/s?q=..." -H "User-Agent: ..."` 后 grep class 结构
- 引擎改版特征:结果数骤降/标题缺失 → 先看页面结构再改正则
- 改完 `systemctl restart bing-search-bridge`(此服务重启不受安全策略拦截)
