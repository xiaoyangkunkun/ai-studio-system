#!/usr/bin/env python3
# 重建四个分类数据库(2022-06-28 Create Database API,属性才能保存)+ 写入泡脚提醒
import json, os, re, urllib.request, urllib.error

os.environ.setdefault('HTTPS_PROXY', 'http://127.0.0.1:7890')
os.environ.setdefault('HTTP_PROXY', 'http://127.0.0.1:7890')

cfg = open('/root/.hermes/config.yaml').read()
token = re.search(r'NOTION_TOKEN:\s*["\']?([^"\'\s]+)', cfg).group(1)

def api(method, path, payload=None, version='2022-06-28'):
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

# 1. 归档四个裸库
OLD_DBS = [
    ('记录', 'a1293ad0-77e8-44bd-a11e-564542c88569'),
    ('知识', 'fa84cc81-06be-4e27-9b4d-9e922915bc18'),
    ('提醒', 'c73ad1f0-6de1-4207-ab3b-bd9da2136c99'),
    ('常用资料', '69be9352-f109-426d-b44f-263409bfcfa7'),
]
for name, dbid in OLD_DBS:
    st, body = api('PATCH', '/v1/pages/' + dbid, {'archived': True}, '2025-09-03')
    print('archived old [%s] -> %s' % (name, st))

# 2. 用 2022-06-28 重建四个库
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

new_ids = {}
for folder, page_id, title, props in DBS:
    payload = {
        "parent": {"type": "page_id", "page_id": page_id},
        "title": [{"type": "text", "text": {"content": title}}],
        "properties": props,
    }
    st, body = api('POST', '/v1/databases', payload)
    if st == 200 and body.get('id'):
        new_ids[title] = body['id']
        # 验证属性
        st2, ds = api('GET', '/v1/data_sources/' + body['id'], version='2025-09-03')
        if st2 == 200:
            pnames = list(ds.get('properties', {}).keys())
            ok = all(k in pnames for k in props)
            print('CREATED [%s] id=%s props=%s %s' % (folder, body['id'], pnames, 'OK' if ok else 'MISSING!'))
        else:
            print('CREATED [%s] id=%s (verify failed %s)' % (folder, body['id'], ds.get('message')))
    else:
        print('FAIL [%s] %s -> %s: %s' % (folder, title, st, body.get('message')))

# 3. 写入泡脚提醒
rem_id = new_ids.get('提醒')
if rem_id:
    payload = {
        "parent": {"type": "database_id", "database_id": rem_id},
        "properties": {
            "标题": {"title": [{"text": {"content": "泡脚"}}]},
            "提醒时间": {"date": {"start": "2026-08-11T22:00:00"}},
            "状态": {"select": {"name": "待提醒"}}
        }
    }
    st, body = api('POST', '/v1/pages', payload)
    print('reminder page -> %s %s' % (st, body.get('id') or body.get('message')))
