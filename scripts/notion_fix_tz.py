#!/usr/bin/env python3
# 修正泡脚提醒的时间为北京时间(带 +08:00 时区)
import json, os, re, urllib.request, urllib.error

os.environ.setdefault('HTTPS_PROXY', 'http://127.0.0.1:7890')
os.environ.setdefault('HTTP_PROXY', 'http://127.0.0.1:7890')

cfg = open('/root/.hermes/config.yaml').read()
token = re.search(r'NOTION_TOKEN:\s*["\']?([^"\'\s]+)', cfg).group(1)

def api(method, path, payload=None, version='2025-09-03'):
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

PAGE = '3b9c4892-f916-8136-9eea-c9c555e641eb'
st, body = api('PATCH', '/v1/pages/' + PAGE, {
    'properties': {'提醒时间': {'date': {'start': '2026-08-11T22:00:00+08:00'}}}
})
print('PATCH -> %s' % st)
if st == 200:
    d = body['properties']['提醒时间']['date']
    print('now stored as:', d.get('start'))
else:
    print('err:', body.get('message'))
