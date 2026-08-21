#!/usr/bin/env python3
# 1) 归档 4 个旧裸库 2) 拿 4 个新库的 data_source_id 3) 验证泡脚提醒在库里
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

# 1. 归档旧裸库
OLD = [('记录','a1293ad0-77e8-44bd-a11e-564542c88569'),
       ('知识','fa84cc81-06be-4e27-9b4d-9e922915bc18'),
       ('提醒','c73ad1f0-6de1-4207-ab3b-bd9da2136c99'),
       ('常用资料','69be9352-f109-426d-b44f-263409bfcfa7')]
for name, dbid in OLD:
    st, body = api('PATCH', '/v1/databases/' + dbid, {'archived': True})
    print('archive old [%s] via /v1/databases -> %s %s' % (name, st, body.get('message','')))
    if st != 200:
        st2, body2 = api('PATCH', '/v1/pages/' + dbid, {'in_trash': True})
        print('  retry via /v1/pages -> %s %s' % (st2, body2.get('message','')))

# 2. 新库 data_source_id
NEW = [('记录','3b9c4892-f916-8185-8b83-f140da07c1d7'),
       ('知识','3b9c4892-f916-8178-8de0-eb28e31776b2'),
       ('提醒','3b9c4892-f916-8111-89a1-c420a26bb342'),
       ('常用资料','3b9c4892-f916-8166-bd35-cb8e2f047580')]
for name, dbid in NEW:
    st, body = api('GET', '/v1/databases/' + dbid)
    if st == 200:
        dss = body.get('data_sources', [])
        print('NEW [%s] db=%s ds=%s' % (name, dbid, dss[0]['id'] if dss else 'NONE'))
    else:
        print('NEW [%s] GET failed %s %s' % (name, st, body.get('message','')))

# 3. 验证泡脚提醒(提醒库 query)
st, body = api('POST', '/v1/data_sources/3b9c4892-f916-8111-89a1-c420a26bb342/query', {}, '2025-09-03')
# 用新库 database id 试 data_source 端点
print('query reminder db as ds -> %s' % st)
if st == 200:
    for p in body.get('results', []):
        props = p.get('properties', {})
        t = props.get('标题', {}).get('title', [{}])[0].get('text', {}).get('content', '')
        print('  page: %s | %s' % (t, p.get('id')))
else:
    print('  err:', body.get('message'))
