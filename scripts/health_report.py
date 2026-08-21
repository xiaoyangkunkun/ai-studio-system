#!/usr/bin/env python3
"""
知识健康度指标脚本
计算孤立笔记率、链接密度、标签覆盖率等健康指标。
零成本纯Python，cron每晚运行。
"""
import os
import re
import json
from collections import defaultdict
from pathlib import Path
from datetime import datetime

VAULT = Path("/root/vault")
OUTPUT_DIR = VAULT / "wiki" / "analytics"

def extract_wikilinks(content: str) -> set:
    return set(re.findall(r'\[\[([^\]|#]+?)(?:[|#][^\]]*)?\]\]', content))

def extract_tags(content: str) -> set:
    """提取标签（frontmatter + inline）"""
    tags = set()
    # frontmatter tags
    fm_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if fm_match:
        tags_section = re.search(r'^tags:\s*\n((?:\s*-\s*.+\n?)+)', fm_match.group(1), re.MULTILINE)
        if tags_section:
            tags.update(re.findall(r'-\s*(.+)', tags_section.group(1)))
    # inline tags
    tags.update(re.findall(r'(?:^|\s)#([a-zA-Z\u4e00-\u9fff][\w\u4e00-\u9fff/]*)', content))
    return tags

def extract_frontmatter(content: str) -> dict:
    """提取frontmatter"""
    fm = {}
    fm_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if fm_match:
        for line in fm_match.group(1).split('\n'):
            if ':' in line:
                key, val = line.split(':', 1)
                fm[key.strip()] = val.strip().strip('"').strip("'")
    return fm

def analyze_vault(vault: Path) -> dict:
    """分析整个vault的健康度"""
    stats = {
        'total_notes': 0,
        'notes_with_links': 0,
        'notes_with_tags': 0,
        'notes_with_frontmatter': 0,
        'total_links': 0,
        'total_tags': set(),
        'orphan_notes': [],  # 无入链也无出链的笔记
        'dead_links': [],    # 链接到不存在的笔记
        'old_notes': [],     # 超过30天未更新的笔记
        'large_notes': [],   # 超过5000字的笔记
        'tag_usage': defaultdict(int),
        'dir_stats': defaultdict(lambda: {'count': 0, 'links': 0}),
    }
    
    all_notes = set()
    link_targets = defaultdict(set)  # target -> set(sources)
    note_data = {}
    
    # 第一遍：收集所有笔记
    for md_file in vault.rglob("*.md"):
        if any(p.startswith('.') for p in md_file.parts):
            continue
        if md_file.name.startswith('_'):
            continue
        note_name = md_file.stem
        all_notes.add(note_name)
        note_data[note_name] = {
            'path': md_file,
            'links_out': set(),
            'tags': set(),
            'has_frontmatter': False,
            'mtime': datetime.fromtimestamp(md_file.stat().st_mtime),
            'size': md_file.stat().st_size,
        }
    
    # 第二遍：分析内容
    for note_name, data in note_data.items():
        try:
            content = data['path'].read_text(encoding='utf-8')
            links = extract_wikilinks(content)
            tags = extract_tags(content)
            fm = extract_frontmatter(content)
            
            data['links_out'] = links
            data['tags'] = tags
            data['has_frontmatter'] = bool(fm)
            
            for link in links:
                link_targets[link].add(note_name)
            
            stats['total_links'] += len(links)
            stats['total_tags'].update(tags)
            stats['notes_with_tags'] += (1 if tags else 0)
            stats['notes_with_frontmatter'] += (1 if fm else 0)
            
            for tag in tags:
                stats['tag_usage'][tag] += 1
            
            # 目录统计
            rel = data['path'].relative_to(vault)
            top_dir = rel.parts[0] if len(rel.parts) > 1 else 'root'
            stats['dir_stats'][top_dir]['count'] += 1
            stats['dir_stats'][top_dir]['links'] += len(links)
            
        except Exception:
            continue
    
    stats['total_notes'] = len(all_notes)
    stats['notes_with_links'] = sum(1 for d in note_data.values() if d['links_out'])
    
    # 找孤立笔记（无出链且无入链）
    for note in all_notes:
        has_out = bool(note_data[note]['links_out'])
        has_in = bool(link_targets.get(note))
        if not has_out and not has_in:
            stats['orphan_notes'].append(note)
    
    # 找死链
    for source, targets in [(n, d['links_out']) for n, d in note_data.items()]:
        for target in targets:
            if target not in all_notes:
                stats['dead_links'].append({'source': source, 'target': target})
    
    # 找老旧笔记（30天未更新）
    cutoff = datetime.now().replace(hour=0, minute=0, second=0)
    from datetime import timedelta
    cutoff = cutoff - timedelta(days=30)
    for note, data in note_data.items():
        if data['mtime'] < cutoff:
            stats['old_notes'].append({'note': note, 'last_modified': data['mtime'].strftime('%Y-%m-%d')})
    
    # 找大笔记（>5000字）
    for note, data in note_data.items():
        if data['size'] > 15000:  # ~5000中文字
            stats['large_notes'].append({'note': note, 'size_kb': round(data['size']/1024, 1)})
    
    stats['total_tags'] = len(stats['total_tags'])
    stats['orphan_notes'].sort()
    stats['old_notes'].sort(key=lambda x: x['last_modified'])
    stats['large_notes'].sort(key=lambda x: x['size_kb'], reverse=True)
    stats['dead_links'] = stats['dead_links'][:20]  # 只保留前20个
    
    return stats

def calculate_health_score(stats: dict) -> dict:
    """计算健康度评分（0-100）"""
    total = stats['total_notes']
    if total == 0:
        return {'score': 0, 'grade': 'N/A', 'details': {}}
    
    scores = {}
    
    # 1. 链接覆盖率（30分）：有链接的笔记比例
    link_coverage = stats['notes_with_links'] / total
    scores['链接覆盖率'] = min(30, link_coverage * 45)  # 67%得30分
    
    # 2. 孤立率（25分）：越少越好
    orphan_rate = len(stats['orphan_notes']) / total
    scores['无孤立笔记'] = max(0, 25 - orphan_rate * 50)  # 0%得25分，50%得0分
    
    # 3. 标签覆盖率（15分）
    tag_coverage = stats['notes_with_tags'] / total
    scores['标签覆盖率'] = min(15, tag_coverage * 25)  # 60%得15分
    
    # 4. Frontmatter覆盖率（15分）
    fm_coverage = stats['notes_with_frontmatter'] / total
    scores['元数据完整'] = min(15, fm_coverage * 25)
    
    # 5. 死链比例（15分）：越少越好
    dead_rate = len(stats['dead_links']) / max(1, stats['total_links'])
    scores['无死链'] = max(0, 15 - dead_rate * 150)  # 10%得0分
    
    total_score = sum(scores.values())
    
    if total_score >= 80:
        grade = '🟢 健康'
    elif total_score >= 60:
        grade = '🟡 一般'
    elif total_score >= 40:
        grade = '🟠 需关注'
    else:
        grade = '🔴 需改善'
    
    return {'score': round(total_score, 1), 'grade': grade, 'details': scores}

def main():
    print("🏥 知识健康度扫描开始...")
    
    stats = analyze_vault(VAULT)
    health = calculate_health_score(stats)
    
    print(f"\n{'='*50}")
    print(f"📊 知识健康度报告")
    print(f"{'='*50}")
    print(f"总评分: {health['score']}/100 {health['grade']}")
    print(f"")
    print(f"📝 笔记总数: {stats['total_notes']}")
    print(f"🔗 链接总数: {stats['total_links']}")
    print(f"🏷️  标签种类: {stats['total_tags']}")
    print(f"")
    print(f"📈 分项得分:")
    for name, score in health['details'].items():
        print(f"  {name}: {score:.1f}")
    print(f"")
    print(f"⚠️  问题发现:")
    print(f"  孤立笔记: {len(stats['orphan_notes'])} 篇 ({len(stats['orphan_notes'])/max(1,stats['total_notes'])*100:.1f}%)")
    print(f"  死链: {len(stats['dead_links'])} 个")
    print(f"  老旧笔记(>30天): {len(stats['old_notes'])} 篇")
    print(f"  大笔记(>5000字): {len(stats['large_notes'])} 篇")
    
    # 输出到文件
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    output_file = OUTPUT_DIR / f"health-report-{today}.md"
    
    lines = [
        f"# 知识健康度报告 - {today}",
        "",
        f"> 扫描时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"> 总评分: **{health['score']}/100 {health['grade']}**",
        "",
        "## 概览",
        "",
        f"| 指标 | 数值 |",
        f"|------|------|",
        f"| 笔记总数 | {stats['total_notes']} |",
        f"| 链接总数 | {stats['total_links']} |",
        f"| 标签种类 | {stats['total_tags']} |",
        f"| 有链接的笔记 | {stats['notes_with_links']} ({stats['notes_with_links']/max(1,stats['total_notes'])*100:.1f}%) |",
        f"| 有标签的笔记 | {stats['notes_with_tags']} ({stats['notes_with_tags']/max(1,stats['total_notes'])*100:.1f}%) |",
        f"| 孤立笔记 | {len(stats['orphan_notes'])} ({len(stats['orphan_notes'])/max(1,stats['total_notes'])*100:.1f}%) |",
        f"| 死链 | {len(stats['dead_links'])} |",
        "",
        "## 分项得分",
        "",
    ]
    for name, score in health['details'].items():
        bar = '█' * int(score) + '░' * (30 - int(score))
        lines.append(f"- {name}: {score:.1f} {bar}")
    
    if stats['dead_links']:
        lines.extend(["", "## 死链（需修复）", ""])
        for dl in stats['dead_links'][:10]:
            lines.append(f"- [[{dl['source']}]] → `{dl['target']}` (不存在)")
    
    if stats['orphan_notes']:
        lines.extend(["", "## 孤立笔记（建议添加链接）", ""])
        for note in stats['orphan_notes'][:15]:
            lines.append(f"- [[{note}]]")
    
    output_file.write_text('\n'.join(lines), encoding='utf-8')
    print(f"\n✅ 报告已保存: {output_file}")
    
    # JSON供cron使用
    json_file = OUTPUT_DIR / "health-report-latest.json"
    json_file.write_text(json.dumps({
        'date': today,
        'score': health['score'],
        'grade': health['grade'],
        'stats': {k: v if not isinstance(v, (set, defaultdict)) else list(v) 
                  for k, v in stats.items()},
    }, ensure_ascii=False, indent=2, default=str), encoding='utf-8')

if __name__ == "__main__":
    main()
