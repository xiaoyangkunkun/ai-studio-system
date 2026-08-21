#!/usr/bin/env python3
"""查询 Notion 提醒库待办,输出今日待办清单(供晨报/提醒使用)。"""
import json, os, re, sys, datetime, urllib.request, urllib.error

os.environ.setdefault('HTTPS_PROXY', 'http://127.0.0.1:7890')
os.environ.setdefault('HTTP_PROXY', 'http://127.0.0.1:7890')

cfg = open('/root/.hermes/config.yaml').read()
token = re.search(r'NOTION_TOKEN:\s*["\']?([^"\'\s]+)', cfg).group(1)
DB = '3b9c4892-f916-8111-89a1-c420a26bb342'  # 提醒库(可写)

today = datetime.date.today().isoformat()

payload = {"page_size": 20}
r = urllib.request.Request(
    f'https://api.notion.com/v1/databases/{DB}/query',
    data=json.dumps(payload).encode(),
    headers={'Authorization': 'Bearer ' + token, 'Notion-Version': '2022-06-28',
             'Content-Type': 'application/json'}, method='POST')
try:
    with urllib.request.urlopen(r, timeout=40) as resp:
        d = json.loads(resp.read())
except urllib.error.HTTPError as e:
    print(f'NOTION_FAIL {e.code}')
    sys.exit(0)

found = 0
for page in d.get('results', []):
    props = page.get('properties', {})
    title = ''
    for seg in props.get('标题', {}).get('title', []):
        title += seg.get('plain_text', '')
    status = ''
    sel = props.get('状态', {}).get('select')
    if sel:
        status = sel.get('name', '')
    date_str = ''
    dt = props.get('提醒时间', {}).get('date')
    if dt and dt.get('start'):
        date_str = dt['start'][:10]
    # 过滤:状态是待提醒/待办,或提醒时间在今天
    if status in ('待提醒', '待办') or date_str == today:
        print(f'- {title} | {date_str or "无日期"} | {status or "无状态"}')
        found += 1

if found == 0:
    print('今日无待办 ✅')
