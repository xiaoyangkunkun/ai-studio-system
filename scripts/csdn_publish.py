#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CSDN API 直调发布器(2026-08-15,基于知远逆向的网关签名)
用法: python3 csdn_publish.py <md文件> [draft|publish]
依赖: markdown(hermes venv 有);cookie 在 /root/.hermes/data/csdn_cookies.json
"""
import json, uuid, base64, hashlib, hmac, sys, pathlib, datetime
import urllib.request

COOKIE_FILE = '/root/.hermes/data/csdn_cookies.json'
API = 'https://bizapi.csdn.net/blog-console-api/v3/mdeditor/saveArticle'
X_CA_KEY = '203803574'
APP_SECRET = '9znpamsyl2c7cdrr9sas0le9vbc3r6ba'


def load_cookie_header():
    cookies = json.load(open(COOKIE_FILE, encoding='utf-8'))
    pairs = [f"{c['name']}={c['value']}" for c in cookies
             if c.get('domain', '').endswith('csdn.net')]
    return '; '.join(pairs)


def make_signature(method, path, content_type, uuid_str):
    string_to_sign = (
        method + '\n' + '*/*' + '\n' + '' + '\n' + content_type + '\n' + '' + '\n'
        + 'x-ca-key:' + X_CA_KEY + '\n'
        + 'x-ca-nonce:' + uuid_str + '\n'
        + path
    )
    return base64.b64encode(
        hmac.new(APP_SECRET.encode(), string_to_sign.encode(), hashlib.sha256).digest()
    ).decode()


def md_to_html(md_text):
    import markdown
    return markdown.markdown(md_text, extensions=['tables', 'fenced_code'])


def parse_frontmatter(text):
    fm = {}
    if text.startswith('---'):
        parts = text.split('---', 2)
        if len(parts) >= 3:
            for line in parts[1].strip().splitlines():
                if ':' in line:
                    k, v = line.split(':', 1)
                    fm[k.strip()] = v.strip().strip('"').strip("'")
            return fm, parts[2].strip()
    return fm, text


def main():
    if len(sys.argv) < 2:
        print('用法: python3 csdn_publish.py <md文件> [draft|publish]')
        sys.exit(1)
    md_path = sys.argv[1]
    pub = sys.argv[2] if len(sys.argv) > 2 else 'draft'
    # 可选第三参数:草稿 ID(更新已有文章/草稿,避免新建重复)
    article_id = sys.argv[3] if len(sys.argv) > 3 else ''
    text = open(md_path, encoding='utf-8').read()
    fm, body_md = parse_frontmatter(text)
    title = fm.get('title', pathlib.Path(md_path).stem)
    tags = fm.get('tags', '').strip('[]').replace('"', '').replace('，', ',')
    body = {
        "id": article_id, "title": title, "markdowncontent": body_md,
        "content": md_to_html(body_md), "readType": "public", "level": 0,
        "tags": tags, "status": 2 if pub == 'draft' else 0,
        "type": "original", "categories": "", "Description": "",
        "source": "pc_mdeditor", "is_new": 1, "pubStatus": pub,
    }
    uid = str(uuid.uuid4())
    content_type = 'application/json;charset=UTF-8'
    path = '/blog-console-api/v3/mdeditor/saveArticle'
    sig = make_signature('POST', path, content_type, uid)
    headers = {
        'Cookie': load_cookie_header(),
        'Accept': '*/*',
        'Content-Type': content_type,
        'X-Ca-Key': X_CA_KEY,
        'X-Ca-Nonce': uid,
        'X-Ca-Signature': sig,
        'X-Ca-Signature-Headers': 'x-ca-key,x-ca-nonce',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    req = urllib.request.Request(API, data=json.dumps(body).encode(), headers=headers, method='POST')
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        result = json.loads(resp.read().decode())
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except urllib.error.HTTPError as e:
        print('HTTP', e.code, e.read().decode()[:500])
        sys.exit(1)


if __name__ == '__main__':
    main()
