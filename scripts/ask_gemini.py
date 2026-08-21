#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gemini 对话调用器 v5(2026-08-16,服务器本地直跑,无 Windows 依赖)
用法:
  python3 ask_gemini.py "问题" [--model 模型] [--timeout 秒] [--auto] [--out 路径] [--image 路径/URL]...
  --auto: 根据问题特征自动选模型(分析/对比/推理/长文 → thinking;翻译/查询/简单 → flash)
  显式 --model 优先于 --auto
  --out 路径: 完整回复直接落盘到指定文件(自动建目录),stdout 只回摘要+预览,
              用于长文产出(派单模式:长文落盘、摘要回传,不撑爆上下文)
  --image 路径/URL: 可重复,一次一张或多张;本地文件自动转 base64,URL 直传
              底层 gemini-web2api 支持图片输入(OpenAI image_url 格式)
原理:gemini-web2api 跑在服务器本地(8092 端口,经服务器 Clash 7890 代理出网),
      直连 Gemini 网页内部接口;不再依赖 Windows。
"""
import sys, json, urllib.request, re, base64, mimetypes, os

def load_image_part(src):
    """返回 OpenAI image_url part;本地文件转 base64 data URI,URL/data URI 直传"""
    if src.startswith(('http://', 'https://', 'data:')):
        return {"type": "image_url", "image_url": {"url": src}}
    if not os.path.exists(src):
        raise FileNotFoundError(f'图片文件不存在: {src}')
    mime = mimetypes.guess_type(src)[0] or 'image/png'
    with open(src, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode()
    return {"type": "image_url", "image_url": {"url": f'data:{mime};base64,{b64}'}}

# 深度思考特征词:命中任一 → 用 thinking 模型
DEEP_KEYWORDS = [
    '分析', '对比', '评估', '优缺点', '为什么', '原因', '推理', '论证',
    '方案', '建议', '总结', '综述', '报告', '研究', '权衡', '利弊',
    '推荐', '选型', '判断',
    'compare', 'analy', 'evaluat', 'reason', 'why', 'pros and cons',
    'strategy', 'plan', 'review', 'research', 'decision', 'recommend'
]

def should_use_thinking(q):
    """自动判定:问题含深度思考特征词 → True(用 thinking 模型)"""
    ql = q.lower()
    return any(kw in ql for kw in DEEP_KEYWORDS)

def main():
    args = sys.argv[1:]
    if not args:
        print('用法: ask_gemini.py "问题" [--model 模型] [--timeout 秒] [--auto] [--out 路径] [--image 路径/URL]...')
        return
    q = args[0]
    model = 'gemini-3.7-flash'
    timeout = 180
    auto = False
    out_path = None
    images = []
    opts = args[1:]
    i = 0
    while i < len(opts):
        if opts[i] == '--model' and i + 1 < len(opts):
            model = opts[i + 1]; i += 2
        elif opts[i] == '--timeout' and i + 1 < len(opts):
            timeout = min(int(opts[i + 1]), 300); i += 2
        elif opts[i] == '--auto':
            auto = True; i += 1
        elif opts[i] == '--out' and i + 1 < len(opts):
            out_path = opts[i + 1]; i += 2
        elif opts[i] == '--image' and i + 1 < len(opts):
            images.append(opts[i + 1]); i += 2
        else:
            i += 1
    # --auto 且未显式指定 --model 时,按问题特征自动选
    if auto and '--model' not in opts:
        if should_use_thinking(q):
            model = 'gemini-3.5-flash-thinking'
    # 构造请求体:带图时 content 用 OpenAI 数组格式(text + image_url parts)
    if images:
        try:
            content = [{"type": "text", "text": q}]
            for src in images:
                content.append(load_image_part(src))
        except Exception as e:
            print('⚠️ 图片加载失败:', str(e)[:200])
            return
        body = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": content}]
        }).encode()
    else:
        body = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": q}]
        }).encode()
    req = urllib.request.Request('http://127.0.0.1:8092/v1/chat/completions', data=body,
                                 headers={'Content-Type': 'application/json'}, method='POST')
    try:
        r = json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode())
        msg = r['choices'][0]['message']['content']
        if msg:
            if out_path:
                # 落盘模式:完整内容写文件,stdout 只回摘要+预览(长文产出不撑爆上下文)
                import os
                os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
                with open(out_path, 'w', encoding='utf-8') as f:
                    f.write(msg)
                print(f'✅ 已写入 {out_path}({len(msg)} 字)')
                preview = msg[:500].replace('\n', ' ')
                print(f'摘要: {preview}' + ('…' if len(msg) > 500 else ''))
            else:
                print(msg)  # 完整输出,不截断(Gemini thinking 输出可达 20k 字符)
        else:
            print('⚠️ Gemini 返回空(可能限流或模型问题),请稍后重试')
    except Exception as e:
        err = str(e)
        if 'Connection refused' in err:
            print('⚠️ Gemini 通道不可用(服务器 gemini-web2api 未运行)——请先启动,或走主模型')
        else:
            print('⚠️ Gemini 调用失败:', err[:200])

if __name__ == '__main__':
    main()
