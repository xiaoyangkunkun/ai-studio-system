#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kimi 对话调用器 v5(2026-08-16,双通道 + 异步事件驱动)
用法:
  python3 ask_kimi.py "问题"                          # 文本(WebBridge 通道,快,同步等待)
  python3 ask_kimi.py "问题" --new                    # 新会话
  python3 ask_kimi.py "问题" --async                  # 异步派单(事件驱动,2026-08-16 加):
                                                     #   派单即返回,Windows 侧完成后主动回调
                                                     #   webhook(kimi-reply),服务器不等待
  python3 ask_kimi.py "问题" --image /path/x.png      # ⚠️ 已舍弃(2026-08-15 老大拍板):Playwright 注入不稳定,勿用
  python3 ask_kimi.py "问题" --timeout 240            # 同步模式超时
"""
import sys, subprocess, pathlib, os, time

def scp(src, dst):
    subprocess.run(['scp', '-P', '2222', '-i', '/root/.ssh/id_ed25519_frp', '-o', 'StrictHostKeyChecking=no', src, f'13199@127.0.0.1:{dst}'], capture_output=True, timeout=30)

def kimi_available():
    """探测 Kimi 通道可用性(Windows 在线 + daemon 活着),约 15 秒;60 秒内结果缓存(连续调用省探测)"""
    cache = '/tmp/kimi_avail_cache'
    try:
        if os.path.exists(cache) and time.time() - os.path.getmtime(cache) < 60:
            return open(cache, encoding='utf-8').read().strip() == '1'
    except Exception:
        pass
    try:
        r = subprocess.run(['bash', '-c', 'ssh -p 2222 -i /root/.ssh/id_ed25519_frp -o StrictHostKeyChecking=no -o ConnectTimeout=10 13199@127.0.0.1 \"powershell -Command \\\"& C:\\Users\\13199\\.kimi-webbridge\\bin\\kimi-webbridge.exe status\\\"\"'], capture_output=True, timeout=20)
        out = r.stdout.decode('utf-8', errors='replace')
        ok = '"running":true' in out and '"extension_connected":true' in out
    except Exception:
        ok = False
    try:
        pathlib.Path(cache).write_text('1' if ok else '0', encoding='utf-8')
    except Exception:
        pass
    return ok

def main():
    args = sys.argv[1:]
    if not args:
        print('用法: ask_kimi.py "问题" [--new] [--image 路径] [--timeout 秒]')
        return
    q = args[0]
    opts = args[1:]
    has_image = '--image' in opts
    # 可用性探测:Windows 关机/Chrome 关 → 明确提示走主模型(2026-08-15 用户定前提)
    if '--skip-check' not in opts and not kimi_available():
        print('⚠️ Kimi 通道不可用(Windows 未开机 或 Chrome 未开/daemon 未连)——请走主模型处理,或开机后重试')
        return
    pathlib.Path('/tmp/kimi_q.txt').write_text(q, encoding='utf-8')
    scp('/tmp/kimi_q.txt', 'C:/Users/13199/kimi_q.txt')

    if has_image:
        # ---- Playwright 通道(能传图) ----
        img = opts[opts.index('--image') + 1]
        scp(img, 'C:/Users/13199/kimi_img_pw.bin')
        pw_opts = []
        for i, o in enumerate(opts):
            if o == '--image':
                pw_opts += ['--image', r'C:\Users\13199\kimi_img_pw.bin']
            else:
                pw_opts.append(o)
        ps = f"chcp 65001 > $null; $env:PYTHONIOENCODING='utf-8'; C:\\Users\\13199\\csdn-mcp\\.venv\\Scripts\\python.exe C:\\Users\\13199\\kimi_pw.py --file C:\\Users\\13199\\kimi_q.txt {' '.join(pw_opts)}"
        full = 'ssh -p 2222 -i /root/.ssh/id_ed25519_frp -o StrictHostKeyChecking=no -o ConnectTimeout=15 13199@127.0.0.1 "powershell -Command \\"' + ps.replace('"', '\\"') + '\\""'
        try:
            r = subprocess.run(['bash', '-c', full], capture_output=True, timeout=340)
            out = r.stdout.decode('utf-8', errors='replace').strip()
            if 'REPLY_START' in out and 'REPLY_END' in out:
                print(out.split('REPLY_START', 1)[1].split('REPLY_END', 1)[0].strip())
            else:
                print(out[-900:] or '(empty)')
        except subprocess.TimeoutExpired:
            print('TIMEOUT')
        return

    # ---- WebBridge 通道(文本,快) ----
    pathlib.Path('/tmp/kimi_opts.txt').write_text(' '.join([o for o in opts if o != '--async']), encoding='utf-8')
    scp('/tmp/kimi_opts.txt', 'C:/Users/13199/kimi_opts.txt')

    if '--async' in opts:
        # ---- 异步派单(事件驱动):SSH 触发一次性计划任务,进程不随 SSH 死,立即返回 ----
        cmd = 'ssh -p 2222 -i /root/.ssh/id_ed25519_frp -o StrictHostKeyChecking=no -o ConnectTimeout=15 13199@127.0.0.1 "powershell -ExecutionPolicy Bypass -File C:\\\\Users\\\\13199\\\\trigger_kimi_async.ps1"'
        try:
            r = subprocess.run(['bash', '-c', cmd], capture_output=True, timeout=60)
            out = r.stdout.decode('utf-8', errors='replace').strip()
            if 'SUCCESS' in out:
                print('✅ 已派单给 Kimi(异步,事件驱动):完成自动回调 webhook,无需等待')
                print('   派单详情:', out.splitlines()[0] if out else '(无输出)')
            else:
                print('⚠️ 派单触发失败,输出如下(可重试或改同步):')
                print(out[-300:] if out else '(empty)')
        except subprocess.TimeoutExpired:
            print('⚠️ 派单触发超时,请检查 Windows 侧计划任务 KimiAskAsync 状态')
        return

    cmd = 'ssh -p 2222 -i /root/.ssh/id_ed25519_frp -o StrictHostKeyChecking=no -o ConnectTimeout=15 13199@127.0.0.1 "powershell -ExecutionPolicy Bypass -File C:\\\\Users\\\\13199\\\\run_kimi.ps1"'
    try:
        r = subprocess.run(['bash', '-c', cmd], capture_output=True, timeout=320)
        out = r.stdout.decode('utf-8', errors='replace').strip()
        if 'REPLY_START' in out and 'REPLY_END' in out:
            print(out.split('REPLY_START', 1)[1].split('REPLY_END', 1)[0].strip())
        elif 'STATUS: STILL_GENERATING' in out:
            print('⚠️ Kimi 还在思考(超时),已生成部分:')
            print(out.split('PARTIAL:', 1)[1].strip() if 'PARTIAL:' in out else '(无内容)')
        elif 'STATUS: NO_REPLY' in out:
            print('⚠️ 未获取到回复(可能页面状态异常)')
        else:
            print(out[-800:] if out else '(empty)')
    except subprocess.TimeoutExpired:
        print('TIMEOUT 整体超时,但 Kimi 可能仍在生成——稍后重试可继续')

if __name__ == '__main__':
    main()
