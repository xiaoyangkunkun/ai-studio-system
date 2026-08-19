---
name: markdown-to-pdf
description: "Use when user wants a document as PDF (整理成文档发给我/最好PDF)."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [pdf, markdown, wkhtmltopdf, chinese, document]
    related_skills: [ocr-and-documents, pdf, docx]
---

# Markdown → PDF (中文, wkhtmltopdf)

When the user asks for a document "最好 PDF" / "整理成文档发给我", generate a
PDF from markdown. Verified chain on Ubuntu (2026-08): markdown → HTML →
wkhtmltopdf, with Noto CJK fonts for Chinese.

## When to use

- User wants a polished deliverable (PDF) rather than a .md attachment
- Content is mostly text/tables (no fancy layouts) — 2-page Chinese doc ≈ 100KB

## Steps

```bash
# 1. deps (one-time)
apt-get install -y wkhtmltopdf fonts-noto-cjk
fc-list :lang=zh | head -1      # confirm CJK font present

# 2. md → HTML (python module is `markdown`, NOT markdown_py)
/usr/local/lib/hermes-agent/venv/bin/python -c "
import markdown
html = markdown.markdown(open('in.md', encoding='utf-8').read(), extensions=['tables'])
page = '<!DOCTYPE html><html><head><meta charset=\"utf-8\"><style>' \
       'body{font-family:\"Noto Sans CJK SC\",sans-serif;max-width:720px;margin:30px auto;padding:0 30px;color:#222;line-height:1.7}' \
       'h1,h2{color:#8b0000}' \
       'table{border-collapse:collapse;width:100%;margin:12px 0}th,td{border:1px solid #ccc;padding:8px 10px;font-size:14px}' \
       'blockquote{background:#faf6ef;border-left:4px solid #c9a86a;padding:8px 16px}' \
       '</style></head><body>' + html + '</body></html>'
open('out.html','w',encoding='utf-8').write(page)"

# 3. HTML → PDF
wkhtmltopdf --encoding utf-8 --enable-local-file-access \
  -s A4 --margin-top 15mm --margin-bottom 15mm out.html out.pdf

# 4. deliver (WeChat etc.): MEDIA:/abs/path/out.pdf
```

## Pitfalls

- **PDF 只用于微信/外部交付,发完即弃**:知识库(vault)只存 md,PDF 生成后放 /tmp 或发完删除,严禁存进 vault(用户 2026-08-13 明确要求:知识库能直接打开 md,不需要 PDF)
- **CJK font**:CSS MUST set `font-family:"Noto Sans CJK SC"` — otherwise Chinese
  renders as tofu boxes. `fonts-noto-cjk` is preinstalled on most Ubuntu servers;
  verify with `fc-list :lang=zh` before blaming wkhtmltopdf.
- **`--enable-local-file-access`** is required for local HTML input.
- Module name is `markdown` — `import markdown_py` fails.
- wkhtmltopdf needs the CSS inline in the HTML (no external stylesheet) or
  the local-file flag; inline style is simplest.
- **发微信的文档必须 PDF(用户纠正 2026-08-13)**:微信打不开 .md 附件。知识库内部存 md 没关系,但任何发给微信的文档一律转 PDF 后 `MEDIA:/abs/path/out.pdf` 交付。这是硬性用户偏好,不是可选格式。

## Verify

```bash
ls -lh out.pdf        # expect ~100KB for 2-page Chinese doc
wkhtmltopdf prints "Printing pages (N/N)" + Done
```
