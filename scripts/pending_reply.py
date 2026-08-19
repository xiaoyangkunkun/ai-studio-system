#!/usr/bin/env python3
"""待答复问题管理 - 查询/创建/完成 Notion 待答复项。
用法:
  python3 pending_reply.py list          # 列出所有待答复
  python3 pending_reply.py add "问题内容" # 添加待答复
  python3 pending_reply.py done <page_id> # 标记已答复
"""
import json, os, re, sys, urllib.request, urllib.error

os.environ.setdefault('HTTPS_PROXY', 'http://127.0.0.1:7890')
os.environ.setdefault('HTTP_PROXY', 'http://127.0.0.1:7890')

cfg = open(os.path.expanduser('~/.hermes/config.yaml')).read()
token = re.search(r'NOTION_TOKEN:\s*["\']?([^"\'\s]+)', cfg).group(1)
DB = '3b9c4892-f916-8111-89a1-c420a26bb342'
HEADERS = {'Authorization': 'Bearer ' + token, 'Notion-Version': '2022-06-28', 'Content-Type': 'application/json'}

def api(method, path, data=None):
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(f'https://api.notion.com/v1{path}', data=body, headers=HEADERS, method=method)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def list_pending():
    d = api('POST', f'/databases/{DB}/query', {
        "filter": {"property": "状态", "select": {"equals": "待答复"}},
        "page_size": 50
    })
    items = []
    for page in d.get('results', []):
        props = page.get('properties', {})
        title = ''.join(s.get('plain_text','') for s in props.get('标题',{}).get('title',[]))
        date = (props.get('提醒时间',{}).get('date') or {}).get('start','')
        notes = ''.join(s.get('plain_text','') for s in props.get('备注',{}).get('rich_text',[]))
        items.append({'id': page['id'], 'title': title, 'date': date[:10] if date else '', 'notes': notes})
    return items

def add_reply(question, notes=''):
    d = api('POST', '/pages', {
        "parent": {"database_id": DB},
        "properties": {
            "标题": {"title": [{"text": {"content": f"⏳ {question}"}}]},
            "状态": {"select": {"name": "待答复"}},
            "备注": {"rich_text": [{"text": {"content": notes}}]}
        }
    })
    return d.get('id', '')

def done_reply(page_id):
    d = api('PATCH', f'/pages/{page_id}', {
        "properties": {
            "状态": {"select": {"name": "已完成"}}
        }
    })
    return 'ok' in str(d.get('object', ''))

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        exit(0)
    
    cmd = sys.argv[1]
    if cmd == 'list':
        items = list_pending()
        if not items:
            print('无待答复问题 ✅')
        else:
            print(f'⏳ 待答复（{len(items)}条）：')
            for i, item in enumerate(items, 1):
                date_str = f"（{item['date']} 提出）" if item['date'] else ''
                notes_str = f" | {item['notes']}" if item['notes'] else ''
                print(f'  Q{i}: {item["title"]}{date_str}{notes_str}')
                print(f'      ID: {item["id"]}')
    elif cmd == 'add':
        question = sys.argv[2] if len(sys.argv) > 2 else ''
        notes = sys.argv[3] if len(sys.argv) > 3 else ''
        if question:
            pid = add_reply(question, notes)
            print(f'✅ 已添加: {question} (ID: {pid})')
        else:
            print('用法: pending_reply.py add "问题内容" [备注]')
    elif cmd == 'done':
        page_id = sys.argv[2] if len(sys.argv) > 2 else ''
        if page_id:
            ok = done_reply(page_id)
            print(f'{"✅" if ok else "❌"} 已标记完成')
        else:
            print('用法: pending_reply.py done <page_id>')
