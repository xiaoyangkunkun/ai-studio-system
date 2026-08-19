# Markdown → PDF on a headless Ubuntu server (verified 2026-08)

Use when the user asks for a document as PDF and the server has no LaTeX/pandoc.
Works with Chinese via system Noto fonts.

## Install

```bash
apt-get install -y wkhtmltopdf fonts-noto-cjk
```

`fonts-noto-cjk` is already present on many Ubuntu servers (`fc-list :lang=zh` to
check). No font config needed — wkhtmltopdf picks up system fonts.

## Steps

### 1. md → HTML

The module is `markdown` (package `python-markdown`). `import markdown_py` →
ModuleNotFoundError — that name does not exist. Use the Hermes venv python or any
python3 with the markdown package:

```python
import markdown
html = markdown.markdown(open('doc.md', encoding='utf-8').read(), extensions=['tables'])
page = '''<!DOCTYPE html><html><head><meta charset="utf-8"><style>
body{font-family:"Noto Sans CJK SC","Noto Serif CJK SC",sans-serif;max-width:720px;margin:30px auto;padding:0 30px;color:#222;line-height:1.7}
h1{color:#8b0000;border-bottom:3px solid #8b0000;padding-bottom:8px}
h2{color:#8b0000;margin-top:28px}
table{border-collapse:collapse;width:100%;margin:12px 0}
th,td{border:1px solid #ccc;padding:8px 10px;text-align:left;font-size:14px}
th{background:#f5f0e6}
blockquote{background:#faf6ef;border-left:4px solid #c9a86a;margin:12px 0;padding:8px 16px;color:#555}
</style></head><body>''' + html + '''</body></html>'''
open('doc.html', 'w', encoding='utf-8').write(page)
```

### 2. HTML → PDF

```bash
wkhtmltopdf --encoding utf-8 --enable-local-file-access -s A4 \
  --margin-top 15mm --margin-bottom 15mm doc.html out.pdf
```

- `--enable-local-file-access` is REQUIRED when reading local HTML (wkhtmltopdf
  0.12.6 default blocks local files).
- Chinese renders automatically once Noto CJK fonts are installed.
- Emoji usually render via `fonts-noto-color-emoji` (installed by default on
  Ubuntu 22.04 desktop-ish images; if boxes appear, drop emoji from the doc).

## Pitfalls

- `import markdown_py` → ModuleNotFoundError. Correct: `import markdown`.
- Missing `--enable-local-file-access` → blank/refused page.
- No CJK font → tofu boxes; install `fonts-noto-cjk`.
- wkhtmltopdf is deprecated upstream but works fine for simple documents;
  don't upgrade to it for complex layouts (use weasyprint/reportlab then).
