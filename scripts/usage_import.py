#!/usr/bin/env python3
"""DeepSeek 官方用量数据包导入脚本 v2(2026-08-15 分账升级)。
用法:python3 usage_import.py <zip路径>
v2 变更:按 api_key_name 拆分 → 主表(合计)+ 各 key 分文件(vault/用量/<key>/<月>.md)。
主表一天一行合计;分表每个 key 一天一行。新 key 自动建目录。
"""
import csv, sys, os, re, zipfile, datetime
from collections import defaultdict

VAULT_USAGE = '~/vault/用量'

KEY_LABEL = {
    'hermes-server': '服务器主引擎',
    'hermes-win': 'Windows 端',
    'hermes-claude-code': '技术员·Claude',
    'mimo-sk': 'MiMo按量',
    'mimo-tp': 'MiMo套餐',
}

def parse_zip(zip_path):
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
        cost_f = next((n for n in names if n.startswith('cost-')), None)
        amount_f = next((n for n in names if n.startswith('amount-')), None)
        if not cost_f or not amount_f:
            raise ValueError(f'压缩包缺少 cost/amount CSV: {names}')
        m = re.search(r'(\d{4}-\d{2}-\d{2})', cost_f)
        day = m.group(1) if m else datetime.date.today().isoformat()
        with z.open(cost_f) as f:
            cost_rows = list(csv.DictReader(f.read().decode('utf-8-sig').splitlines()))
        with z.open(amount_f) as f:
            amt_rows = list(csv.DictReader(f.read().decode('utf-8-sig').splitlines()))
    return day, cost_rows, amt_rows

def summarize_by_key(day, cost_rows, amt_rows):
    """按 key 聚合 amount;cost 无 key 字段,按请求数比例分摊"""
    amt = defaultdict(lambda: defaultdict(int))
    for r in amt_rows:
        amt[r['api_key_name']][r['type']] += int(r['amount'])
    total_cost = sum(float(r['cost']) for r in cost_rows)
    total_req = sum(a.get('request_count', 0) for a in amt.values())
    result = {}
    for key, a in amt.items():
        req = a.get('request_count', 0)
        hit = a.get('input_cache_hit_tokens', 0)
        miss = a.get('input_cache_miss_tokens', 0)
        out = a.get('output_tokens', 0)
        cost = round(total_cost * (req / total_req), 2) if total_req else 0.0
        result[key] = {
            'day': day, 'req': req, 'input': hit + miss, 'output': out,
            'cache_hit': hit, 'cost': cost, 'label': KEY_LABEL.get(key, key),
        }
    return result

def fmt_money(c):
    return f'{c:.2f}'

def update_file(path, day, row_lines):
    """把当天的行写入文件(新增或覆盖当天行)"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        txt = open(path, encoding='utf-8').read()
    else:
        txt = ''
    # 替换当天已有行(day 开头),否则在表尾追加
    inserted = False
    new_txt = []
    for line in txt.split('\n'):
        if line.startswith(f'| {day} '):
            new_txt.extend(row_lines)
            inserted = True
        else:
            new_txt.append(line)
    txt = '\n'.join(new_txt)
    if not inserted:
        # 找到表头分隔行(|---)后第一行数据前插入
        lines = txt.split('\n')
        for i, ln in enumerate(lines):
            if ln.startswith('|---') and i + 1 < len(lines):
                lines[i+1:i+1] = row_lines
                break
        else:
            # 文件还没表头:追加表头+数据
            head = '| 日期 | Key | 用途 | 请求 | 输入 | 输出 | 缓存命中 | 费用¥ |\n|---|---|---|---|---|---|---|---|\n'
            lines = (lines + [head]).copy() if lines else [head]
        txt = '\n'.join(lines)
    open(path, 'w', encoding='utf-8').write(txt)

def update_vault(day, per_key):
    ym = day[:7]
    # 主表:一天一行合计
    total_req = sum(v['req'] for v in per_key.values())
    total_cost = sum(v['cost'] for v in per_key.values())
    total_in = sum(v['input'] for v in per_key.values())
    total_out = sum(v['output'] for v in per_key.values())
    total_hit = sum(v['cache_hit'] for v in per_key.values())
    sub = ' · '.join('%s ¥%.2f' % (k, v['cost']) for k, v in per_key.items())
    main_row = ['| %s | %d | %s | %s | %s | %.2f | %s |' % (day, total_req, f'{total_in:,}', f'{total_out:,}', f'{total_hit:,}', total_cost, sub)]
    update_file(os.path.join(VAULT_USAGE, f'{ym}.md'), day, main_row)
    # 分表:每 key 一行
    for key, v in per_key.items():
        row = [f'| {day} | {key} | {v["label"]} | {v["req"]} | {v["input"]:,} | {v["output"]:,} | {v["cache_hit"]:,} | {fmt_money(v["cost"])} |']
        update_file(os.path.join(VAULT_USAGE, key, f'{ym}.md'), day, row)
    return total_cost

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('用法: python3 usage_import.py <zip路径>'); sys.exit(1)
    day, c, a = parse_zip(sys.argv[1])
    per_key = summarize_by_key(day, c, a)
    total = update_vault(day, per_key)
    print(f'✅ {day} 官方数据包已入库(分账拆分):')
    for k, v in per_key.items():
        print(f'  {k} ({v["label"]}): 请求{v["req"]} | 输入{v["input"]:,} | 输出{v["output"]:,} | 缓存命中{v["cache_hit"]:,} | ¥{v["cost"]:.2f}')
    print(f'  合计 ¥{total:.2f}')
