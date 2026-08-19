#!/usr/bin/env python3
"""每日 token 用量结算(月度版):写入 vault/用量/YYYY-MM.md,服务器/Windows 分开统计。

cron 每天 00:10 运行(no_agent)。成功静默;余额低于阈值或失败时 stdout 告警(会被推送)。
Windows 端(8/13 起)有独立脚本写 vault/用量/win/YYYY-MM.md,本脚本结算时读取合并。
"""
import json, os, re, sqlite3, datetime, urllib.request, urllib.error

os.environ.setdefault('HTTPS_PROXY', 'http://127.0.0.1:7890')
os.environ.setdefault('HTTP_PROXY', 'http://127.0.0.1:7890')

DB = '~/.hermes/state.db'
SNAP = '~/.hermes/data/token_snapshots.json'
USAGE_DIR = '~/vault/用量'
WIN_DIR = os.path.join(USAGE_DIR, 'win')
BALANCE_ALERT = 10.0
EXCHANGE = 7.2

def get_totals():
    db = sqlite3.connect(DB)
    r = db.execute("""SELECT
        SUM(CAST(api_call_count AS INTEGER)),
        SUM(CAST(input_tokens AS INTEGER)),
        SUM(CAST(output_tokens AS INTEGER)),
        SUM(CAST(cache_read_tokens AS INTEGER)),
        SUM(CAST(reasoning_tokens AS INTEGER)),
        SUM(CAST(estimated_cost_usd AS REAL))
        FROM session_model_usage""").fetchone()
    db.close()
    return dict(calls=r[0] or 0, inp=r[1] or 0, out=r[2] or 0,
                cr=r[3] or 0, rsn=r[4] or 0, cost=r[5] or 0)

def get_balance():
    cfg = open('~/.hermes/config.yaml').read()
    m = re.search(r'DEEPSEEK_API_KEY[=:]\s*["\']?([^"\'\s]+)', cfg)
    if not m:
        m = re.search(r'DEEPSEEK_API_KEY=([^\s]+)', open('~/.hermes/.env').read())
    key = m.group(1).strip()
    req = urllib.request.Request('https://api.deepseek.com/user/balance',
                                 headers={'Authorization': 'Bearer ' + key})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    bal = 0.0
    for b in data.get('balance_infos', []):
        if b.get('currency') == 'CNY':
            bal = float(b.get('total_balance', 0))
    return bal

def fmt(n):
    return f'{int(n):,}'

def read_win_day(month_file, day):
    """读 Windows 月度文件今天的行,返回(调用,输入,输出,缓存读,¥)或 None"""
    p = os.path.join(WIN_DIR, month_file)
    if not os.path.exists(p):
        return None
    for line in open(p, encoding='utf-8'):
        if line.startswith('| ' + day + ' |'):
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            # 格式:日期|调用|输入|输出|缓存读|推理|¥
            try:
                return (cells[1], cells[2], cells[3], cells[4], cells[6])
            except Exception:
                return None
    return None

def monthly_summary(fname):
    """给指定月份文件生成小计行并追加"""
    p = os.path.join(USAGE_DIR, fname)
    if not os.path.exists(p):
        return
    txt = open(p, encoding='utf-8').read()
    if '月度小计' in txt and '合计' in txt.split('## 月度小计')[1][:200]:
        return
    s_call = s_inp = s_out = s_cr = s_cost = w_call = w_inp = w_out = w_cr = w_cost = 0.0
    for line in txt.splitlines():
        if not line.startswith('| '):
            continue
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) < 12 or not re.match(r'\d{4}-\d{2}-\d{2}', cells[0]):
            continue
        def num(x):
            try:
                return float(x.replace(',', '').replace('¥', ''))
            except Exception:
                return 0.0
        s_call += num(cells[1]); s_inp += num(cells[2]); s_out += num(cells[3])
        s_cr += num(cells[4]); s_cost += num(cells[5])
        w_call += num(cells[6]); w_inp += num(cells[7]); w_out += num(cells[8])
        w_cr += num(cells[9]); w_cost += num(cells[10])
    summary = (f"\n- **服务器**:调用 {int(s_call)} | 输入 {fmt(s_inp)} | 输出 {fmt(s_out)} | "
               f"缓存读 {fmt(s_cr)} | 费用 ¥{s_cost:.2f}\n"
               f"- **Windows**:调用 {int(w_call)} | 输入 {fmt(w_inp)} | 输出 {fmt(w_out)} | "
               f"缓存读 {fmt(w_cr)} | 费用 ¥{w_cost:.2f}\n"
               f"- **合计**:¥{s_cost + w_cost:.2f}\n")
    if '## 月度小计' in txt:
        txt = txt.replace('## 月度小计\n\n', '## 月度小计\n' + summary, 1)
    else:
        txt += '\n## 月度小计\n' + summary
    open(p, 'w', encoding='utf-8').write(txt)

def main():
    today = datetime.date.today().isoformat()
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    ym = yesterday[:7]                     # 2026-08
    yday = yesterday[8:]                   # 12
    t = get_totals()
    try:
        bal = get_balance()
    except Exception:
        bal = None

    snaps = json.load(open(SNAP, encoding='utf-8')) if os.path.exists(SNAP) else {}
    prev = snaps.get(yesterday)
    if prev:
        day = dict(calls=t['calls'] - prev['calls'], inp=t['inp'] - prev['inp'],
                   out=t['out'] - prev['out'], cr=t['cr'] - prev['cr'],
                   rsn=t['rsn'] - prev['rsn'], cost=t['cost'] - prev['cost'])
        first = False
    else:
        # 无昨日基准(部署过渡期):只更新今日基准,跳过结算,保留已有的官方/历史行
        snaps[today] = t
        os.makedirs(os.path.dirname(SNAP), exist_ok=True)
        json.dump(snaps, open(SNAP, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        return

    s_cost = day['cost'] * EXCHANGE
    # Windows 端数据(如已部署)
    win = read_win_day(ym + '.md', yesterday)
    if win:
        w_cost = float(win[4].replace('¥', '')) if win[4] != '-' else 0.0
        wcells = (win[0], win[1], win[2], win[3], win[4])
    else:
        w_cost = 0.0
        wcells = ('-', '-', '-', '-', '-')
    total_cost = s_cost + w_cost
    tag = '(首日=累计口径)' if first else ''
    row = (f"| {yesterday} | {day['calls']} | {fmt(day['inp'])} | {fmt(day['out'])} | "
           f"{fmt(day['cr'])} | {s_cost:.2f} | {wcells[0]} | {wcells[1]} | {wcells[2]} | "
           f"{wcells[3]} | {wcells[4]} | {total_cost:.2f} | {bal if bal is not None else '?'} |")

    os.makedirs(USAGE_DIR, exist_ok=True)
    fname = os.path.join(USAGE_DIR, ym + '.md')
    if os.path.exists(fname):
        txt = open(fname, encoding='utf-8').read()
    else:
        txt = (f"# 📊 Token 用量月报 · {ym.replace('-', '年')} 月\n\n"
               "> 自动结算(每日 00:10)。费用为本地估算,余额为官方实时值。\n\n"
               "## 每日明细\n\n"
               "| 日期 | 服务器调用 | 服务器输入 | 服务器输出 | 服务器缓存读 | 服务器¥ | Windows调用 | Windows输入 | Windows输出 | Windows缓存读 | Windows¥ | 合计¥ | 余额¥ |\n"
               "|---|---|---|---|---|---|---|---|---|---|---|---|---|\n")
    # 插入/更新当日行(在"## "小节之前)
    esc = re.escape('| ' + yesterday + ' |')
    if re.search(esc, txt):
        txt = re.sub(r'\| ' + re.escape(yesterday) + r' \|.*\n', row + '\n', txt)
    else:
        m = re.search(r'\n## ', txt)
        if m:
            txt = txt[:m.start()] + '\n' + row + txt[m.start():]
        else:
            txt = txt.rstrip() + '\n' + row + '\n'
    open(fname, 'w', encoding='utf-8').write(txt)

    # 每月 1 日:给上月文件生成月度小计
    if datetime.date.today().day == 1:
        last = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y-%m')
        monthly_summary(last + '.md')

    # Notion 每日日志页追加用量小节
    try:
        cfg = open('~/.hermes/config.yaml').read()
        m = re.search(r'NOTION_TOKEN:\s*["\']?([^"\'\s]+)', cfg)
        ntoken = m.group(1)
        d, mth = int(yesterday[8:]), int(yesterday[5:7])
        title = f'{mth}月{d}日 复盘'
        q = urllib.request.Request('https://api.notion.com/v1/search',
            data=json.dumps({"query": title, "page_size": 5}).encode(),
            headers={'Authorization': 'Bearer ' + ntoken, 'Notion-Version': '2022-06-28',
                     'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(q, timeout=20) as resp:
            found = json.loads(resp.read()).get('results', [])
        for pg in found:
            props = pg.get('properties', {})
            tprops = props.get('标题', {}).get('title', [])
            if tprops and tprops[0].get('plain_text') == title:
                body = props.get('正文', {}).get('rich_text', [])
                old = body[0].get('plain_text', '') if body else ''
                new = (old + f"\n\n【今日用量】\n"
                       f"- 服务器:调用 {day['calls']} | 输入 {fmt(day['inp'])} | 输出 {fmt(day['out'])} | 缓存读 {fmt(day['cr'])} | ¥{s_cost:.2f}\n"
                       f"- Windows:{' 调用 ' + win[0] + ' | 输入 ' + win[1] + ' | 输出 ' + win[2] + ' | 缓存读 ' + win[3] + ' | ¥' + win[4] if win else ' 无数据'}\n"
                       f"- 合计 ¥{total_cost:.2f}" + (f" | 余额 ¥{bal:.2f}" if bal is not None else ""))
                p = urllib.request.Request('https://api.notion.com/v1/pages/' + pg['id'],
                    data=json.dumps({"properties": {"正文": {"rich_text": [{"text": {"content": new}}]}}}).encode(),
                    headers={'Authorization': 'Bearer ' + ntoken, 'Notion-Version': '2022-06-28',
                             'Content-Type': 'application/json'}, method='PATCH')
                with urllib.request.urlopen(p, timeout=20) as _:
                    pass
                break
    except Exception as e:
        print(f'ERROR Notion 写入失败: {e}')

    if bal is not None and bal < BALANCE_ALERT:
        print(f'⚠️ DeepSeek 余额不足:¥{bal:.2f},请及时充值!')

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'ERROR token 结算失败: {e}')
