#!/usr/bin/env python3
"""必应搜索桥接服务 — 模拟 SearXNG JSON API,后端走国内可达的 cn.bing.com。

Hermes 的 web_search(searxng backend)会请求:
    GET /search?q=<query>&format=json&pageno=1
期望返回 {"results": [{"title","url","content","score"}]}

用途:服务器在国内,海外搜索 API(DuckDuckGo/Google/Tavily 等)不可达,
cn.bing.com 可达,故用本桥接把必应结果包装成 SearXNG 格式。

零第三方依赖(python3 标准库),systemd 常驻 127.0.0.1:8888。
"""
import json
import re
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"
PORT = 8899
TIMEOUT = 15
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def bing_search(query: str, limit: int = 10) -> list:
    """抓取 cn.bing.com 搜索结果并解析为 SearXNG 格式条目(兜底引擎)。"""
    url = ("https://cn.bing.com/search?q=" + urllib.parse.quote(query)
           + "&count=" + str(limit) + "&setlang=zh-hans")
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept-Language": "zh-CN,zh;q=0.9",
    })
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return []

    results = []
    seen = set()
    for m in re.finditer(r'<li class="b_algo".*?</li>', html, re.S):
        block = m.group(0)
        tm = re.search(r'<h2[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                       block, re.S)
        if not tm:
            continue
        u = tm.group(1).strip()
        title = re.sub(r"<[^>]+>", "", tm.group(2)).strip()
        if not title or u in seen:
            continue
        seen.add(u)
        pm = re.search(r"<p[^>]*>(.*?)</p>", block, re.S)
        desc = re.sub(r"<[^>]+>", "", pm.group(1)).strip() if pm else ""
        results.append({
            "title": title,
            "url": u,
            "content": desc,
            "score": -len(results),
        })
        if len(results) >= limit:
            break
    return results


def so360_search(query: str, limit: int = 10) -> list:
    """抓取 360 搜索(so.com)结果 — 中文相关性优于必应,主引擎。"""
    url = "https://www.so.com/s?q=" + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept-Language": "zh-CN,zh;q=0.9",
    })
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return []

    results = []
    seen = set()
    for m in re.finditer(r'<li class="res-list".*?</li>', html, re.S):
        block = m.group(0)
        tm = re.search(r'<h3[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                       block, re.S)
        if not tm:
            continue
        u = tm.group(1).strip()
        title = re.sub(r"<[^>]+>", "", tm.group(2)).strip()
        if not title or u in seen:
            continue
        seen.add(u)
        pm = re.search(r'<p class="res-desc[^"]*"[^>]*>(.*?)</p>', block, re.S)
        desc = re.sub(r"<[^>]+>", "", pm.group(1)).strip() if pm else ""
        # so.com/link 跳转链接保留原样(Hermes 会用它抓取)
        results.append({
            "title": title,
            "url": u,
            "content": desc,
            "score": -len(results),
        })
        if len(results) >= limit:
            break
    return results


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/healthz":
            self._send_json({"ok": True})
            return
        if parsed.path != "/search":
            self.send_response(404)
            self.end_headers()
            return
        params = urllib.parse.parse_qs(parsed.query)
        q = (params.get("q") or [""])[0].strip()
        if not q:
            self._send_json({"results": []})
            return
        try:
            # 主引擎:360(中文相关性好);失败/结果为空时兜底必应
            results = so360_search(q)
            if not results:
                results = bing_search(q)
            self._send_json({"results": results})
        except Exception as exc:  # noqa: BLE001
            self._send_json({"results": [], "error": str(exc)})

    def _send_json(self, data: dict) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args) -> None:  # 安静模式
        pass


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Bing search bridge listening on {HOST}:{PORT}", flush=True)
    server.serve_forever()
