---
name: employee-task-pipeline
description: "员工派活完整流程：派活→产出→PDF交付→档案更新。Use when 派员工执行任务并交付。"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [digital-employee, dispatch, pdf, pipeline]
---

# 员工派活完整流水线

## When to Use
- 派知远/墨白执行任务并需要交付PDF给用户
- 需要走完"派活→产出→交付→归档"全流程时

## 流程（四步）

### 1. 派活
```bash
# 后台执行（推荐）
terminal(command="hermes -p researcher chat -q '任务描述'", background=true, notify_on_complete=true)
```
任务描述要自包含：背景、目标、产出目录、格式要求

### 2. 产出确认
- 检查产出文件是否存在、内容是否完整
- 确认产出目录正确：`~/vault/工作室产出/<岗位·名字>/调研报告/<主题>/`

### 3. 写复盘
- 员工自己写（军师不代写）
- 存：`~/vault/复盘/员工/<岗位·名字>/YYYY-MM-DD-<主题>经验总结.md`
- 军师审阅后归档

### 4. Ingest到wiki（知识库闭环）
根据产出内容类型，ingest到对应wiki目录：
- **调研结论/实体信息** → `vault/wiki/entities/` （如Hermes版本信息、QQ Bot能力等）
- **方案对比** → `vault/wiki/comparisons/`
- **新概念定义** → `vault/wiki/concepts/`
- **原始素材** → `vault/wiki/raw/` （只读不改）
- 更新 `vault/wiki/index.md` 和 `vault/wiki/log.md`

### 5. PDF交付（用户要求时）
```bash
# md → HTML（用markdown模块）
/usr/local/lib/hermes-agent/venv/bin/python -c "
import markdown
html = markdown.markdown(open('in.md', encoding='utf-8').read(), extensions=['tables'])
page = '<!DOCTYPE html><html><head><meta charset=\"utf-8\"><style>'
'body{font-family:\"Noto Sans CJK SC\",sans-serif;max-width:720px;margin:30px auto;padding:0 30px;color:#222;line-height:1.7}'
'h1,h2{color:#8b0000}'
'table{border-collapse:collapse;width:100%;margin:12px 0}th,td{border:1px solid #ccc;padding:8px 10px;font-size:14px}'
'blockquote{background:#faf6ef;border-left:4px solid #c9a86a;padding:8px 16px}'
'</style></head><body>' + html + '</body></html>'
open('/tmp/report.html','w',encoding='utf-8').write(page)"

# HTML → PDF
wkhtmltopdf --encoding utf-8 --enable-local-file-access -s A4 --margin-top 15mm --margin-bottom 15mm /tmp/report.html /tmp/report.pdf

# 微信交付
echo "MEDIA:/tmp/report.pdf"
# 发完即弃，PDF不入vault
```

### 6. 档案更新（硬规则）
每次派活交付后，必须更新员工档案页的「📈 成长记录」：
- 文件：`~/vault/工作室/员工/<岗位·名字>.md`
- 格式：`- **YYYY-MM-DD 第N单(任务名)** | 耗时+关键结论+质量评价——合格交付 ✅`

## 关键规则
- **PDF只用于微信交付**：知识库只存md，PDF发完即弃
- **成长记录必更新**：靠流程执行，不靠记性
- **派活命令格式**：`hermes -p researcher chat -q '任务'`（不能用 `researcher "任务"` wrapper）
- **自包含prompt**：员工无当前会话上下文

## 常见错误
- `researcher "任务"` → 报错，必须用 `hermes -p researcher chat -q '任务'`
- PDF存进vault → 违反规则，PDF发完即弃
- 漏更新成长记录 → 硬规则，每次必更新
