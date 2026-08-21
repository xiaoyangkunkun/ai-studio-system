#!/usr/bin/env python3
# 在四个分类页面下创建数据库(Notion Create Database API)
import json, os, re, sys, urllib.request, urllib.error

os.environ.setdefault('HTTPS_PROXY', 'http://127.0.0.1:7890')
os.environ.setdefault('HTTP_PROXY', 'http://127.0.0.1:7890')

cfg = open('/root/.hermes/config.yaml').read()
m = re.search(r'NOTION_TOKEN:\s*["\']?([^"\'\s]+)', cfg)
if not m:
    print('ERROR: NOTION_TOKEN not found in config.yaml'); sys.exit(1)
token = m.group(1)
print('token loaded: %s...%s' % (token[:6], token[-4:]))

def api(path, payload, version='2025-09-03'):
    req = urllib.request.Request('https://api.notion.com' + path,
        data=json.dumps(payload).encode(),
        headers={'Authorization': 'Bearer ' + token,
                 'Notion-Version': version,
                 'Content-Type': 'application/json'},
        method='POST')
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try: body = json.loads(e.read())
        except Exception: body = {'message': str(e)}
        return e.code, body

DBS = [
    ("记录类", "3b9c4892-f916-805b-b042-cd33cdc41c25", "记录", {
        "标题": {"title": {}},
        "日期": {"date": {}},
        "类型": {"select": {"options": [{"name": "待办"}, {"name": "习惯打卡"}, {"name": "记账"}, {"name": "健康"}, {"name": "其他"}]}},
        "内容": {"rich_text": {}},
        "状态": {"select": {"options": [{"name": "进行中"}, {"name": "已完成"}]}},
    }),
    ("知识类", "3b9c4892-f916-80cc-9e1d-d55f9639a45a", "知识", {
        "标题": {"title": {}},
        "分类": {"select": {"options": [{"name": "见闻"}, {"name": "收藏"}, {"name": "经验"}, {"name": "读书"}, {"name": "其他"}]}},
        "日期": {"date": {}},
        "内容": {"rich_text": {}},
        "来源": {"url": {}},
    }),
    ("提醒类", "3b9c4892-f916-80e2-b2a5-c5095821d714", "提醒", {
        "标题": {"title": {}},
        "提醒时间": {"date": {}},
        "状态": {"select": {"options": [{"name": "待提醒"}, {"name": "已提醒"}, {"name": "已取消"}]}},
        "备注": {"rich_text": {}},
    }),
    ("查询类", "3b9c4892-f916-8093-b66a-fb3d05f98175", "常用资料", {
        "标题": {"title": {}},
        "分类": {"select": {"options": [{"name": "账号"}, {"name": "地址"}, {"name": "证件"}, {"name": "偏好"}, {"name": "其他"}]}},
        "内容": {"rich_text": {}},
        "更新时间": {"date": {}},
    }),
]

for folder, page_id, title, props in DBS:
    payload = {
        "parent": {"type": "page_id", "page_id": page_id},
        "title": [{"type": "text", "text": {"content": title}}],
        "properties": props,
    }
    status, resp = api('/v1/databases', payload)
    if status == 200 and resp.get('id'):
        print('OK  [%s] %s -> database_id=%s' % (folder, title, resp['id']))
    else:
        print('FAIL[%s] %s -> HTTP %s: %s' % (folder, title, status, resp.get('message', resp)))
