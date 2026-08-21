#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DeepSeek 对话调用器 v2(2026-08-16,WebBridge 通用通道,服务端)
用法:
  python3 ask_deepseek.py "问题"                        # 文本对话(默认当前会话,同步等待)
  python3 ask_deepseek.py "问题" --new                  # 新会话(换任务必用,防串上下文)
  python3 ask_deepseek.py "问题" --async                # 异步派单(事件驱动,2026-08-16 加):
                                                       #   派单即返回,Windows 侧完成后主动回调
                                                       #   webhook(8644),服务器不 SSH 等待,无超时误判
  python3 ask_deepseek.py "问题" --timeout 240          # 同步模式超时(默认 180,上限 300)
  python3 ask_deepseek.py "问题" --skip-check           # 跳过可用性探测(已知在线时)
原理:写问题/参数到文件 → scp → SSH 触发 Windows 侧 ps1 → ds_ask(_async).py(WebBridge)
      → 同步:回复回传;异步:完成事件回调 webhook。中文/引号全部走文件,SSH 命令固定无参数。
      ⚠️ 图片/文件上传:已舍弃(2026-08-15 老大拍板)——WebBridge upload 权限墙(-32000),Playwright 通道需独立登录+验证码,成本不值。
"""
import sys, subprocess, pathlib, os, time

def scp(src, dst):
    subprocess.run(['scp', '-P', '2222', '-i', '${HOME}/.ssh/id_ed25519_frp', '-o', 'StrictHostKeyChecking=no', src, f'13199@127.0.0.1:{dst}'], capture_output=True, timeout=30)

def ds_available():
    """探测 DeepSeek 通道可用性(Windows 在线 + daemon 活着),约 15 秒;60 秒内结果缓存(连续调用省探测)"""
    cache = '/tmp/ds_avail_cache'
    try:
        if os.path.exists(cache) and time.time() - os.path.getmtime(cache) < 60:
            return open(cache, encoding='utf-8').read().strip() == '1'
    except Exception:
        pass
    try:
        r = subprocess.run(['bash', '-c', 'ssh -p 2222 -i ${HOME}/.ssh/id_ed25519_frp -o StrictHostKeyChecking=no -o ConnectTimeout=10 13199@127.0.0.1 \"powershell -Command \\\"& C:\\Users\\13199\\.kimi-webbridge\\bin\\kimi-webbridge.exe status\\\"\"'], capture_output=True, timeout=20)
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
        print('用法: ask_deepseek.py "问题" [--new] [--timeout 秒] [--skip-check]')
        return
    q = args[0]
    opts = args[1:]
    if '--skip-check' not in opts and not ds_available():
        print('⚠️ DeepSeek 通道不可用(Windows 未开机 或 Chrome 未开/WebBridge 未连)——请走主模型处理,或开机后重试')
        return
    pathlib.Path('/tmp/ds_q.txt').write_text(q, encoding='utf-8')
    scp('/tmp/ds_q.txt', 'C:/Users/13199/ds_q.txt')
    pathlib.Path('/tmp/ds_opts.txt').write_text(' '.join([o for o in opts if o != '--async']), encoding='utf-8')
    scp('/tmp/ds_opts.txt', 'C:/Users/13199/ds_opts.txt')

    if '--async' in opts:
        # ---- 异步派单(事件驱动):SSH 触发一次性计划任务,进程不随 SSH 死,立即返回 ----
        cmd = 'ssh -p 2222 -i ${HOME}/.ssh/id_ed25519_frp -o StrictHostKeyChecking=no -o ConnectTimeout=15 13199@127.0.0.1 "powershell -ExecutionPolicy Bypass -File C:\\\\\\\\Users\\\\\\\\13199\\\\\\\\trigger_ds_async.ps1"'
        try:
            r = subprocess.run(['bash', '-c', cmd], capture_output=True, timeout=60)
            out = r.stdout.decode('utf-8', errors='replace').strip()
            if 'SUCCESS' in out:
                print('✅ 已派单给 DeepSeek(异步,事件驱动):完成自动回调 webhook,无需等待')
                print('   派单详情:', out.splitlines()[0] if out else '(无输出)')
            else:
                print('⚠️ 派单触发失败,输出如下(可重试或改同步):')
                print(out[-300:] if out else '(empty)')
        except subprocess.TimeoutExpired:
            print('⚠️ 派单触发超时,请检查 Windows 侧计划任务 DSAskAsync 状态')
        return

    cmd = 'ssh -p 2222 -i ${HOME}/.ssh/id_ed25519_frp -o StrictHostKeyChecking=no -o ConnectTimeout=15 13199@127.0.0.1 "powershell -ExecutionPolicy Bypass -File C:\\\\\\\\Users\\\\\\\\13199\\\\\\\\run_deepseek.ps1"'
    try:
        r = subprocess.run(['bash', '-c', cmd], capture_output=True, timeout=320)
        out = r.stdout.decode('utf-8', errors='replace').strip()
        if 'REPLY_START' in out and 'REPLY_END' in out:
            print(out.split('REPLY_START', 1)[1].split('REPLY_END', 1)[0].strip())
        elif 'STATUS: NOT_LOGGED_IN' in out:
            print('⚠️ DeepSeek 未登录:请在 Windows Chrome 打开 chat.deepseek.com 登录一次(手机验证码或微信扫码),再重试')
        elif 'STATUS: STILL_GENERATING' in out:
            print('⚠️ DeepSeek 还在思考(超时),已生成部分:')
            print(out.split('PARTIAL:', 1)[1].strip() if 'PARTIAL:' in out else '(无内容)')
        elif 'STATUS: NO_REPLY' in out:
            print('⚠️ 未获取到回复(可能页面状态异常)')
        else:
            print(out[-800:] if out else '(empty)')
    except subprocess.TimeoutExpired:
        print('TIMEOUT 整体超时,但 DeepSeek 可能仍在生成——稍后重试可继续')

if __name__ == '__main__':
    main()
