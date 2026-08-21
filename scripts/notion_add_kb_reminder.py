#!/usr/bin/env python3
# 写入"配置知识库"提醒到 Notion 提醒库
import json, os, re, urllib.request, urllib.error

os.environ.setdefault('HTTPS_PROXY', 'http://127.0.0.1:7890')
os.environ.setdefault('HTTP_PROXY', 'http://127.0.0.1:7890')

cfg = open('/root/.hermes/config.yaml').read()
token = re.search(r'NOTION_TOKEN:\s*["\']?([^"\'\s]+)', cfg).group(1)

payload = {
    "parent": {"type": "database_id", "database_id": "3b9c4892-f916-8111-89a1-c420a26bb342"},
    "properties": {
        "标题": {"title": [{"text": {"content": "配置 Obsidian 知识库"}}]},
        "提醒时间": {"date": {"start": "2026-08-12T09:00:00+08:00"}},
        "状态": {"select": {"name": "待提醒"}},
        "备注": {"rich_text": [{"text": {"content": "装 Obsidian(用户)→ 建 vault+接同步(我)→ 测试读写(我)"}}]}
    }
}
r = urllib.request.Request('https://api.notion.com/v1/pages',
    data=json.dumps(payload).encode(),
    headers={'Authorization': 'Bearer ' + token, 'Notion-Version': '2025-09-03',
             'Content-Type': 'application/json'}, method='POST')
try:
    with urllib.request.urlopen(r, timeout=40) as resp:
        body = json.loads(resp.read())
    print('OK page_id=%s' % body.get('id'))
except urllib.error.HTTPError as e:
    print('FAIL %s: %s' % (e.code, e.read().decode()[:300]))
