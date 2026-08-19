#!/usr/bin/env python3
"""生成能力目录(技能清单)到 vault。
扫描 ~/.hermes/skills/ 所有 SKILL.md(递归),输出中文简述 + 最近更新时间。"""
import os, re, datetime

SKILLS_DIR = os.path.expanduser('~/.hermes/skills')
OUT = '~/vault/entities/能力目录.md'

# 中文简述映射(未收录的用原文描述)
CN = {
    'apple-notes': '苹果备忘录:创建/搜索/编辑笔记', 'apple-reminders': '苹果提醒事项:添加/查看/完成',
    'findmy': '查找我的设备:追踪苹果设备/AirTag', 'imessage': 'iMessage:发送接收信息',
    'claude-code': '委托 Claude Code 写代码/提 PR', 'codex': '委托 OpenAI Codex 写代码/提 PR',
    'computer-use': '后台操控桌面(不抢焦点)', 'hermes-agent': 'Hermes 自身配置/扩展/编排',
    'hermes-headless-server': '无头服务器访问 Hermes 面板', 'hermes-server-ops': '云服务器上部署/运维 Hermes(本机沉淀)',
    'merge-reconciler': '多智能体合并冲突的第三方仲裁', 'opencode': '委托 OpenCode 写代码/审查',
    'architecture-diagram': '深色系 SVG 架构图', 'ascii-art': 'ASCII 艺术:文字横幅/图片转字符画',
    'ascii-video': '视频转彩色 ASCII 动画 MP4/GIF', 'baoyu-infographic': '信息图:21 布局 x 21 风格',
    'claude-design': '一次性 HTML 设计稿(落地页/演示)', 'comfyui': 'ComfyUI 扩散模型出图/视频/音频',
    'design-md': '编写/校验 Google DESIGN.md 规范', 'excalidraw': '手绘风 Excalidraw 图表(架构/流程)',
    'humanizer': '去 AI 味:让文字更像真人写的', 'manim-video': 'Manim 数学/算法动画视频',
    'p5js': 'p5.js 生成艺术/创意编程', 'popular-web-designs': '54 套大厂设计系统(Stripe/Linear 等)',
    'pretext': '无 DOM 文本排版创意演示', 'sketch': '快速 HTML 草图:2-3 版式对比',
    'songwriting-and-ai-music': '写歌 + Suno AI 音乐提示词', 'touchdesigner-mcp': 'MCP 控制 TouchDesigner',
    'sdlc-review': '软件开发生命周期评审', 'email-inbox-triage': '收件箱整理:优先级+安全草稿',
    'himalaya': '命令行收发邮件(IMAP/SMTP)', 'codebase-inspection': '代码库统计:行数/语言/占比',
    'github-auth': 'GitHub 认证配置(HTTPS/SSH/gh)', 'github-code-review': 'PR 代码审查:diff+行内评论',
    'github-issue-to-pr': 'Issue 到 PR 全流程(诚实 CI)', 'github-issues': '创建/分派/标记 GitHub Issue',
    'github-pr-workflow': 'PR 生命周期:分支/提交/CI/合并', 'github-repo-management': '仓库克隆/创建/Fork/Release',
    'gif-search': 'Tenor 搜 GIF(curl+jq)', 'songsee': '音频可视化:频谱/声纹特征',
    'youtube-content': 'YouTube 视频转摘要/文章', 'evaluating-llms-harness': '大模型评测(MMLU/GSM8K 等)',
    'huggingface-hub': 'HuggingFace 模型/数据集下载上传', 'llama-cpp': 'llama.cpp 本地跑 GGUF 模型',
    'serving-llms-vllm': 'vLLM 高吞吐模型服务', 'weights-and-biases': 'W&B 实验跟踪/看板',
    'obsidian': 'Obsidian 知识库读写/搜索/建笔记', 'airtable': 'Airtable 数据操作(curl)',
    'document-to-action-items': '从文档提取义务/期限/任务', 'docx': 'Word 文档创建/编辑/模板',
    'google-workspace': 'Gmail/日历/Drive/表格(gws)', 'maps': '地理编码/路线/时区(OSM)',
    'meeting-action-items': '会议纪要转决策/负责人/工单', 'nano-pdf': '自然语言改 PDF 文字',
    'notion': 'Notion API 页面/数据库操作', 'ocr-and-documents': 'PDF/扫描件文字提取(pymupdf/marker/markitdown)',
    'pdf': 'PDF 创建/读取/合并/表单', 'powerpoint': 'PPT 创建/编辑(python-pptx)',
    'product-price-monitor': '商品/机票价格监控告警', 'teams-meeting-pipeline': 'Teams 会议纪要/回放/订阅',
    'weekly-review-planning': '每周复盘:承诺/停滞/下周计划', 'xlsx': 'Excel 创建/编辑/CSV',
    'arxiv': 'arXiv 论文搜索', 'blogwatcher': '博客/RSS 订阅监控',
    'competitor-news-monitor': '竞对公司新闻监控(带引用)', 'grounded-citations': '答案/文档带可验证引用',
    'llm-wiki': 'Karpathy LLM Wiki:互链知识库', 'research-paper-writing': '写 ML 论文(NeurIPS/ICML/ICLR)',
    'openhue': 'Philips Hue 灯光控制', 'social-trend-monitoring': '社交平台热搜抓取(无 API 用聚合站,本机沉淀)',
    'xurl': 'X/Twitter 官方 API:搜索/发帖/DM', 'cn-network-web-search': '国内网络下让 Hermes 搜索可用(本机沉淀)',
    'dogfood': 'Web 应用探索式 QA 找 bug', 'hermes-agent-skill-authoring': '编写 SKILL.md 规范',
    'inspecting-hermes-desktop-dom': 'CDP 读 Hermes 桌面 DOM/CSS', 'node-inspect-debugger': 'Node.js 调试(--inspect+CDP)',
    'plan': '写计划文档到 .hermes/plans(不执行)', 'python-debugpy': 'Python 调试:pdb+debugpy',
    'requesting-code-review': '提交前审查:安全扫描/质量门', 'simplify-code': '4 智能体并行清理代码改动',
    'spike': '一次性实验验证想法', 'systematic-debugging': '4 阶段根因调试法',
    'test-driven-development': 'TDD:先测试后代码(红-绿-重构)',
}

def parse_frontmatter(path):
    try:
        txt = open(path, encoding='utf-8').read()
    except Exception:
        return None
    m = re.match(r'^---\n(.*?)\n---', txt, re.S)
    if not m:
        return None
    fm = m.group(1)
    name = re.search(r'^name:\s*(.+)$', fm, re.M)
    desc = re.search(r'^description:\s*(.+)$', fm, re.M)
    return {
        'name': name.group(1).strip().strip('"\'') if name else os.path.basename(os.path.dirname(path)),
        'desc': desc.group(1).strip().strip('"\'') if desc else '',
        'mtime': datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d'),
    }

def walk(dirpath, cat):
    """递归找 SKILL.md,返回 (cat, skills) 列表"""
    out = []
    for entry in sorted(os.listdir(dirpath)):
        full = os.path.join(dirpath, entry)
        if entry.startswith('.'):
            continue
        if os.path.isdir(full):
            sp = os.path.join(full, 'SKILL.md')
            if os.path.isfile(sp):
                info = parse_frontmatter(sp)
                if info:
                    info['_path'] = full
                    out.append((cat, info))
            else:
                out.extend(walk(full, cat))
    return out

cats = {}
all_skills = []
for cat in sorted(os.listdir(SKILLS_DIR)):
    cat_dir = os.path.join(SKILLS_DIR, cat)
    if not os.path.isdir(cat_dir) or cat.startswith('.'):
        continue
    found = walk(cat_dir, cat)
    if found:
        cats.setdefault(cat, []).extend(found)
        all_skills.extend(found)

# 内置/沉淀判定:读取 .bundled_manifest
BUNDLED_MANIFEST = os.path.join(SKILLS_DIR, '.bundled_manifest')
bundled = set()
if os.path.isfile(BUNDLED_MANIFEST):
    for line in open(BUNDLED_MANIFEST, encoding='utf-8'):
        n = line.strip().split(':')[0]
        if n:
            bundled.add(n)

def is_archived(relpath):
    return '.archive' in relpath

# 沉淀技能 = 非内置;归档的单独标注
sediment = [(cat, s) for cat, s in all_skills if s['name'] not in bundled]
active_sediment = [(cat, s) for cat, s in sediment if not is_archived(s.get('_path', ''))]
archived_sediment = [(cat, s) for cat, s in sediment if is_archived(s.get('_path', ''))]
builtin = [(cat, s) for cat, s in all_skills if s['name'] in bundled]

total = len(all_skills)
now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

lines = ['---', 'title: 能力目录(技能清单)', f'created: {now[:10]}', f'updated: {now[:10]}',
         'type: entity', 'tags: [工具, 效率]', 'sources: []', '---', '',
         '# 🧰 能力目录(Hermes 技能清单)', '',
         f'> 自动生成: {now} | 技能总数: **{total}**(内置 {len(builtin)} + 沉淀 {len(active_sediment)})',
         '> 沉淀技能 = 本机经验中新增/自研的技能(区别于 Hermes 出厂自带)。',
         '> 知识库内容目录见 [[知识库目录]],总入口 [[index]]。', '',
         '## ⭐ 沉淀技能(本机新增,重点)', '']
if active_sediment:
    lines.append('| 技能 | 说明 | 更新 |')
    lines.append('|---|---|---|')
    for cat, s in active_sediment:
        cn = CN.get(s['name'])
        desc = cn if cn else s['desc']
        lines.append(f"| **{s['name']}** | {desc} | {s['mtime']} |")
else:
    lines.append('(暂无)')
if archived_sediment:
    lines.append('')
    lines.append('**已归档**:' + '、'.join(s['name'] for _, s in archived_sediment))
lines += ['', '---', '', '## 📦 内置技能(按分类)', '']
for cat in sorted(cats):
    items = [s for c, s in builtin if c == cat]
    if items:
        lines.append(f'### {cat}({len(items)})')
        lines.append('')
        for s in items:
            cn = CN.get(s['name'])
            desc = cn if cn else s['desc']
            lines.append(f'- **{s["name"]}**({s["mtime"]})— {desc}')
        lines.append('')
lines += ['---', '', '**相关笔记**:[[index]] · [[知识库目录]] · [[同步配置]]', '']

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print(f'OK 能力目录已更新: {total} 个技能(沉淀 {len(active_sediment)}) -> {OUT}')
