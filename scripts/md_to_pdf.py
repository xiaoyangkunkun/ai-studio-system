#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""md → PDF 转换工具(2026-08-15)
用法: python3 md_to_pdf.py <input.md> <output.pdf>
依赖: markdown(hermes venv)+ wkhtmltopdf(系统)
"""
import sys, subprocess, pathlib, markdown

def main():
    if len(sys.argv) < 3:
        print('用法: md_to_pdf.py <输入.md> <输出.pdf>')
        return
    src, dst = sys.argv[1], sys.argv[2]
    text = pathlib.Path(src).read_text(encoding='utf-8')
    # 去掉 frontmatter
    if text.startswith('---'):
        parts = text.split('---', 2)
        body = parts[2] if len(parts) > 2 else text
    else:
        body = text
    html = markdown.markdown(body, extensions=['tables', 'fenced_code'])
    css = """<meta charset="utf-8"><style>
    body{font-family:"Noto Sans CJK SC","Microsoft YaHei",sans-serif;max-width:820px;margin:24px auto;padding:0 20px;line-height:1.7}
    h1{border-bottom:2px solid #333;padding-bottom:8px}
    h2{margin-top:28px;border-left:4px solid #1a73e8;padding-left:10px}
    code{background:#f5f5f5;padding:2px 5px;border-radius:3px}
    pre{background:#f8f8f8;padding:12px;border-radius:6px;overflow-x:auto}
    table{border-collapse:collapse;width:100%}
    td,th{border:1px solid #ddd;padding:6px 10px;font-size:14px}
    th{background:#f0f0f0}
    blockquote{border-left:4px solid #f0a020;background:#fffbea;margin:0;padding:8px 14px}
    </style>"""
    html_file = pathlib.Path(dst).with_suffix('.html')
    html_file.write_text(css + html, encoding='utf-8')
    r = subprocess.run(['which', 'wkhtmltopdf'], capture_output=True, text=True)
    if r.returncode != 0:
        print('NO_WKHTMLTOPDF 未安装')
        return
    r = subprocess.run(['wkhtmltopdf', '--encoding', 'utf-8', '--enable-local-file-access', str(html_file), dst], capture_output=True, timeout=120)
    if r.returncode == 0:
        print(f'PDF OK: {dst} ({pathlib.Path(dst).stat().st_size} bytes)')
    else:
        print('PDF_FAIL:', r.stderr.decode()[-300:])

if __name__ == '__main__':
    main()
