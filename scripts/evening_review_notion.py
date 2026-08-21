#!/usr/bin/env python3
"""晚间复盘写 Notion 每日日志:查询今日记录,有则更新,无则新建。"""
import json, sys, urllib.request, urllib.error

def load_token():
    with open('/root/.hermes/.env') as f:
        for line in f:
            line = line.strip()
            if line.startswith('NOTION_API_KEY='):
                return line.split('=', 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("NOTION_API_KEY not found")

TOKEN = load_token()
DS = "3b9c4892-f916-813d-8a38-000b080899ee"   # 查询用 data_source_id
DB = "3b9c4892-f916-8199-a586-fe08da569520"   # 建页用 database_id

def api(path, method='GET', body=None):
    req = urllib.request.Request(
        f"https://api.notion.com{path}", method=method,
        headers={"Authorization": f"Bearer {TOKEN}",
                 "Notion-Version": "2025-09-03",
                 "Content-Type": "application/json"},
        data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, json.loads(r.read().decode() or '{}')
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or '{}')
        except Exception:
            return e.code, {}
    except Exception as e:
        return -1, {"error": str(e)}

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'probe'
    if mode == 'probe':
        # 看库结构和最近几条
        st, res = api(f"/v1/data_sources/{DS}/query", "POST",
                      {"page_size": 3, "sorts": [{"property": "日期", "direction": "descending"}]})
        print("probe 状态:", st)
        if st == 200:
            for it in res.get("results", []):
                props = it.get("properties", {})
                title = ""
                for k, v in props.items():
                    if v.get("type") == "title":
                        title = "".join(t.get("plain_text", "") for t in v.get("title", []))
                date = ""
                for k, v in props.items():
                    if v.get("type") == "date" and v.get("date"):
                        date = v["date"].get("start", "")
                print(f"- {it['id']} | title={title!r} | date={date!r}")
            if res.get("results"):
                props = res["results"][0].get("properties", {})
                print("属性结构:", json.dumps({k: v.get("type") for k, v in props.items()}, ensure_ascii=False))
        else:
            print("错误:", json.dumps(res, ensure_ascii=False)[:600])
    elif mode == 'find':
        # 按日期找今天的记录
        today = sys.argv[2]
        st, res = api(f"/v1/data_sources/{DS}/query", "POST", {
            "filter": {"property": "日期", "date": {"equals": today}},
            "page_size": 5})
        print("find 状态:", st)
        if st == 200:
            for it in res.get("results", []):
                print("PAGE_ID:", it["id"])
            if not res.get("results"):
                print("PAGE_ID: NONE")
        else:
            print("错误:", json.dumps(res, ensure_ascii=False)[:600])
    elif mode == 'create':
        # 新建今日复盘页
        title, body, today = sys.argv[2], sys.argv[3], sys.argv[4]
        payload = {
            "parent": {"database_id": DB},
            "properties": {
                "标题": {"title": [{"text": {"content": title}}]},
                "日期": {"date": {"start": today}},
                "正文": {"rich_text": [{"text": {"content": body}}]},
                "状态": {"select": {"name": "初稿"}},
            },
        }
        st, res = api("/v1/pages", "POST", payload)
        print("create 状态:", st, "| page_id:", res.get("id", ""))
        if st != 200:
            print("错误:", json.dumps(res, ensure_ascii=False)[:800])
    elif mode == 'update':
        # 更新已有页
        page_id, body = sys.argv[2], sys.argv[3]
        payload = {"properties": {
            "正文": {"rich_text": [{"text": {"content": body}}]},
            "状态": {"select": {"name": "初稿"}},
        }}
        st, res = api(f"/v1/pages/{page_id}", "PATCH", payload)
        print("update 状态:", st)
        if st != 200:
            print("错误:", json.dumps(res, ensure_ascii=False)[:800])
