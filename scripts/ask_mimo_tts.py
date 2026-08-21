#!/usr/bin/env python3
"""MiMo TTS 语音合成 - Hermes Command Provider 适配版。
占位符: {input_path} {text_path} {output_path} {format} {voice} {model} {speed}
Hermes 会把待合成文本写入 {input_path} 文件，音频输出到 {output_path}。

音色克隆: --voice xiaoai 使用小爱同学音色 (--clone-ref 指定参考音频)
"""
import sys, json, base64, urllib.request, urllib.error, os, re

API_KEY = ''
BASE_URL = 'https://token-plan-cn.xiaomimimo.com/v1'
MODEL = 'mimo-v2.5-tts'

# 预置克隆音色映射: voice_name -> reference_audio_path
CLONE_VOICES = {
    'xiaoai': os.path.expanduser('~/.hermes/voices/xiaoai_reference.mp3'),
    'ruoxue': os.path.expanduser('~/.hermes/voices/ruoxue_reference.wav'),
}

# 预置风格音色: voice_name -> (base_voice, style_prompt)
STYLE_VOICES = {
    'ruoxue_tw': ('冰糖', '台湾女生跟男朋友打电话，声音甜软，语速轻快，尾音撒娇上扬，带着满满的想念和开心，像好久没见终于听到他声音的那种又高兴又有点委屈的感觉'),
}

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

def synthesize(text, voice='冰糖', audio_format='wav', style=None, clone_ref=None):
    """合成语音。clone_ref 为参考音频路径时启用音色克隆。"""
    _load_key()
    messages = []

    # 音色克隆模式: 传入参考音频
    if clone_ref and os.path.exists(clone_ref):
        with open(clone_ref, 'rb') as f:
            ref_audio = base64.b64encode(f.read()).decode()
        ext = os.path.splitext(clone_ref)[1].lower().lstrip('.')
        ref_format = 'mp3' if ext in ('mp3',) else 'wav' if ext in ('wav',) else 'mp3'
        user_content = [
            {'type': 'input_audio', 'input_audio': {'data': ref_audio, 'format': ref_format}},
            {'type': 'text', 'text': '用这个声音的音色来说'}
        ]
        if style:
            user_content.append({'type': 'text', 'text': f'语气风格：{style}'})
        messages.append({'role': 'user', 'content': user_content})
    else:
        # 内置音色模式
        if style:
            messages.append({'role': 'user', 'content': style})

    messages.append({'role': 'assistant', 'content': text})

    payload = {
        'model': MODEL,
        'messages': messages,
        'audio': {'format': audio_format}
    }
    # 内置音色才传 voice 参数，克隆模式不传
    if not clone_ref:
        payload['audio']['voice'] = voice

    data = json.dumps(payload).encode()

    req = urllib.request.Request(
        f'{BASE_URL}/chat/completions',
        data=data,
        headers={'api-key': API_KEY, 'Content-Type': 'application/json'})

    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.loads(r.read())
        audio_data = d['choices'][0]['message'].get('audio', {})
        if 'data' in audio_data:
            return base64.b64decode(audio_data['data'])
        return None

if __name__ == '__main__':
    # 支持两种调用方式:
    # 1. Hermes command provider: python3 ask_mimo_tts.py --text-file {input_path} --out {output_path}
    # 2. 直接调用: python3 ask_mimo_tts.py "要合成的文本" --output xxx.wav

    text = None
    text_file = None
    output_path = '/tmp/mimo_tts_output.mp3'
    voice = '茉莉'
    fmt = 'mp3'
    style = None
    clone_ref = None

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '--text-file' and i + 1 < len(args):
            text_file = args[i + 1]; i += 2
        elif args[i] == '--out' and i + 1 < len(args):
            output_path = args[i + 1]; i += 2
        elif args[i] == '--voice' and i + 1 < len(args):
            voice = args[i + 1]; i += 2
        elif args[i] == '--clone-ref' and i + 1 < len(args):
            clone_ref = args[i + 1]; i += 2
        elif args[i] == '--format' and i + 1 < len(args):
            fmt = args[i + 1]; i += 2
        elif args[i] == '--style' and i + 1 < len(args):
            style = args[i + 1]; i += 2
        elif args[i] == '--output' and i + 1 < len(args):
            output_path = args[i + 1]; i += 2
        elif not args[i].startswith('-'):
            text = args[i]; i += 1
        else:
            i += 1

    # 预置克隆音色: --voice xiaoai 自动查找参考音频
    if voice in CLONE_VOICES and not clone_ref:
        clone_ref = CLONE_VOICES[voice]

    # 预置风格音色: --voice ruoxue_tw 自动设置 base_voice + style
    if voice in STYLE_VOICES:
        base_voice, default_style = STYLE_VOICES[voice]
        voice = base_voice
        if not style:
            style = default_style

    # 从文件读取文本（Hermes command provider 模式）
    if text_file and os.path.exists(text_file):
        with open(text_file, 'r', encoding='utf-8') as f:
            text = f.read().strip()

    if not text:
        print('用法: python3 ask_mimo_tts.py --text-file <文本文件> --out <输出音频>', file=sys.stderr)
        print('  或: python3 ask_mimo_tts.py "文本" --output xxx.wav', file=sys.stderr)
        sys.exit(1)

    # 确保输出格式与文件扩展名一致
    if output_path.endswith('.mp3'):
        fmt = 'mp3'
    elif output_path.endswith('.wav'):
        fmt = 'wav'
    elif output_path.endswith('.ogg'):
        fmt = 'wav'  # MiMo 不支持 ogg，用 wav 后转换

    audio = synthesize(text, voice, fmt, style, clone_ref=clone_ref)
    if audio:
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(audio)
        print(f'OK: {output_path} ({len(audio)} bytes)')
    else:
        print('ERROR: No audio data returned', file=sys.stderr)
        sys.exit(1)
