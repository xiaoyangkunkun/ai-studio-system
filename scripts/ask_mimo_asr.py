#!/usr/bin/env python3
"""MiMo ASR 语音识别 - Hermes Command Provider 适配版。
占位符: {input_path} {output_path} {format} {language} {model}
Hermes 会把音频文件路径传入 {input_path}，转录结果写入 {output_path}。
"""
import sys, json, base64, urllib.request, urllib.error, os, re

API_KEY = ''
BASE_URL = 'https://token-plan-cn.xiaomimimo.com/v1'
MODEL = 'mimo-v2.5-asr'

def _load_key():
    global API_KEY
    if API_KEY:
        return
    API_KEY = os.environ.get('MIMO_TP_KEY', '')
    if not API_KEY:
        cfg_path = os.path.expanduser('~/.hermes/profiles/researcher/config.yaml')
        if os.path.exists(cfg_path):
            with open(cfg_path) as f:
                m = re.search(r"api_key:\s*(tp-\S+)", f.read())
                if m:
                    API_KEY = m.group(1)

def transcribe(audio_path, audio_format='mp3'):
    _load_key()
    with open(audio_path, 'rb') as f:
        audio_b64 = base64.b64encode(f.read()).decode()

    data = json.dumps({
        'model': MODEL,
        'messages': [{'role': 'user', 'content': [
            {'type': 'input_audio', 'input_audio': {'data': audio_b64, 'format': audio_format}}
        ]}],
        'max_tokens': 2000
    }).encode()

    req = urllib.request.Request(
        f'{BASE_URL}/chat/completions',
        data=data,
        headers={'api-key': API_KEY, 'Content-Type': 'application/json'})

    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read())
        return d['choices'][0]['message']['content']

if __name__ == '__main__':
    # 支持两种调用方式:
    # 1. Hermes command provider: python3 ask_mimo_asr.py --audio {input_path} --out {output_path}
    # 2. 直接调用: python3 ask_mimo_asr.py <音频文件>

    audio_path = None
    output_path = None
    fmt = 'mp3'

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '--audio' and i + 1 < len(args):
            audio_path = args[i + 1]; i += 2
        elif args[i] == '--out' and i + 1 < len(args):
            output_path = args[i + 1]; i += 2
        elif args[i] == '--format' and i + 1 < len(args):
            fmt = args[i + 1]; i += 2
        elif not args[i].startswith('-'):
            audio_path = args[i]; i += 1
        else:
            i += 1

    if not audio_path:
        print('用法: python3 ask_mimo_asr.py --audio <音频文件> --out <输出文件>', file=sys.stderr)
        sys.exit(1)

    result = transcribe(audio_path, fmt)

    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result)
        print(f'OK: {output_path}')
    else:
        print(result)
