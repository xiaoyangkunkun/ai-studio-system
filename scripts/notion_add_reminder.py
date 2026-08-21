#!/usr/bin/env python3
# 诊断"提醒"数据库属性 + 直接写入泡脚提醒
import json, os, re, urllib.request, urllib.error

os.environ.setdefault('HTTPS_PROXY', 'http://127.0.0.1:7890')
os.environ.setdefault('HTTP_PROXY', 'http://127.0.0.1:7890')

cfg = open('/root/.hermes/config.yaml').read()
token = re.search(r'NOTION_TOKEN:\s*["\']?([^"\'\s]+)', cfg).group(1)

DB_ID = 'c73ad1f0-6de1-4207-ab3b-bd9da2136c99'

def req(method, path, payload=None, version='2025-09-03'):
    r = urllib.request.Request('https://api.notion.com' + path,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={'Authorization': 'Bearer ' + token, 'Notion-Version': version,
                 'Content-Type': 'application/json'},
        method=method)
    try:
        with urllib.request.urlopen(r, timeout=40) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try: body = json.loads(e.read())
        except Exception: body = {'message': str(e)}
        return e.code, body

# 1. 查看数据库属性
for path in ['/v1/databases/' + DB_ID, '/v1/data_sources/f80d69d5-ba29-4140-84d1-1fed886acbb8']:
    st, body = req('GET', path)
    print('GET %s -> %s' % (path, st))
    if st == 200:
        props = body.get('properties', {})
        print('  properties:', list(props.keys()) if props else '(none in response)')
        break
    else:
        print('  err:', body.get('message'))

# 2. 写入泡脚提醒
payload = {
    "parent": {"type": "database_id", "database_id": DB_ID},
    "properties": {
        "标题": {"title": [{"text": {"content": "泡脚"}}]},
        "提醒时间": {"date": {"start": "2026-08-11T22:00:00"}},
        "状态": {"select": {"name": "待提醒"}}
    }
}
st, body = req('POST', '/v1/pages', payload)
print('POST /v1/pages -> %s' % st)
if st == 200:
    print('OK page_id=%s url=%s' % (body.get('id'), body.get('url')))
else:
    print('err:', body.get('message'))
