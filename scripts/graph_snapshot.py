#!/usr/bin/env python3
"""
Graph快照追踪脚本
每天记录Wikilink边数、笔记数、标签数，对比昨天，量化"知识增长"。
零成本纯Python，cron每晚运行。
"""
import os
import re
import json
from collections import defaultdict
from pathlib import Path
from datetime import datetime, timedelta

VAULT = Path("~/vault")
OUTPUT_DIR = VAULT / "wiki" / "analytics"
SNAPSHOT_FILE = OUTPUT_DIR / "graph-snapshots.json"

def extract_wikilinks(content: str) -> set:
    return set(re.findall(r'\[\[([^\]|#]+?)(?:[|#][^\]]*)?\]\]', content))

def extract_tags(content: str) -> set:
    tags = set()
    fm_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if fm_match:
        tags_section = re.search(r'^tags:\s*\n((?:\s*-\s*.+\n?)+)', fm_match.group(1), re.MULTILINE)
        if tags_section:
            tags.update(re.findall(r'-\s*(.+)', tags_section.group(1)))
    tags.update(re.findall(r'(?:^|\s)#([a-zA-Z\u4e00-\u9fff][\w\u4e00-\u9fff/]*)', content))
    return tags

def take_snapshot(vault: Path) -> dict:
    """拍摄当前vault的快照"""
    notes = set()
    total_links = 0
    all_tags = set()
    dir_notes = defaultdict(int)
    link_pairs = set()
    
    for md_file in vault.rglob("*.md"):
        if any(p.startswith('.') for p in md_file.parts):
            continue
        if md_file.name.startswith('_'):
            continue
        
        note_name = md_file.stem
        notes.add(note_name)
        
        rel = md_file.relative_to(vault)
        top_dir = rel.parts[0] if len(rel.parts) > 1 else 'root'
        dir_notes[top_dir] += 1
        
        try:
            content = md_file.read_text(encoding='utf-8')
            links = extract_wikilinks(content)
            tags = extract_tags(content)
            
            total_links += len(links)
            all_tags.update(tags)
            
            for link in links:
                pair = tuple(sorted([note_name, link]))
                link_pairs.add(pair)
        except Exception:
            continue
    
    return {
        'date': datetime.now().strftime("%Y-%m-%d"),
        'timestamp': datetime.now().isoformat(),
        'notes_count': len(notes),
        'links_count': total_links,
        'unique_edges': len(link_pairs),
        'tags_count': len(all_tags),
        'dir_distribution': dict(dir_notes),
    }

def load_history() -> list:
    """加载历史快照"""
    if SNAPSHOT_FILE.exists():
        try:
            return json.loads(SNAPSHOT_FILE.read_text(encoding='utf-8'))
        except Exception:
            return []
    return []

def save_history(history: list):
    """保存历史快照"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding='utf-8')

def calculate_trends(history: list) -> dict:
    """计算趋势"""
    if len(history) < 2:
        return {'has_trend': False}
    
    latest = history[-1]
    prev = history[-2]
    
    trends = {
        'has_trend': True,
        'notes_delta': latest['notes_count'] - prev['notes_count'],
        'links_delta': latest['links_count'] - prev['links_count'],
        'edges_delta': latest['unique_edges'] - prev['unique_edges'],
        'tags_delta': latest['tags_count'] - prev['tags_count'],
    }
    
    # 7天趋势
    if len(history) >= 7:
        week_ago = history[-7]
        trends['week_notes_delta'] = latest['notes_count'] - week_ago['notes_count']
        trends['week_links_delta'] = latest['links_count'] - week_ago['links_count']
    
    # 30天趋势
    if len(history) >= 30:
        month_ago = history[-30]
        trends['month_notes_delta'] = latest['notes_count'] - month_ago['notes_count']
        trends['month_links_delta'] = latest['links_count'] - month_ago['links_count']
    
    return trends

def main():
    print("📸 Graph快照追踪开始...")
    
    snapshot = take_snapshot(VAULT)
    history = load_history()
    trends = calculate_trends(history)
    
    # 添加今天的快照
    history.append(snapshot)
    
    # 只保留最近90天
    if len(history) > 90:
        history = history[-90:]
    
    save_history(history)
    
    print(f"\n📊 今日快照:")
    print(f"  笔记数: {snapshot['notes_count']}")
    print(f"  链接数: {snapshot['links_count']}")
    print(f"  唯一边数: {snapshot['unique_edges']}")
    print(f"  标签数: {snapshot['tags_count']}")
    
    if trends['has_trend']:
        print(f"\n📈 对比昨天:")
        for key, label in [('notes_delta', '笔记'), ('links_delta', '链接'), ('edges_delta', '边'), ('tags_delta', '标签')]:
            delta = trends[key]
            arrow = '↑' if delta > 0 else ('↓' if delta < 0 else '→')
            print(f"  {label}: {arrow} {abs(delta)}")
        
        if 'week_notes_delta' in trends:
            print(f"\n📅 7天趋势:")
            print(f"  笔记: {'↑' if trends['week_notes_delta'] > 0 else '↓'} {abs(trends['week_notes_delta'])}")
            print(f"  链接: {'↑' if trends['week_links_delta'] > 0 else '↓'} {abs(trends['week_links_delta'])}")
    
    # 输出报告
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    today = snapshot['date']
    output_file = OUTPUT_DIR / f"graph-snapshot-{today}.md"
    
    lines = [
        f"# Graph快照 - {today}",
        "",
        f"> 记录时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## 今日数据",
        "",
        f"| 指标 | 数值 |",
        f"|------|------|",
        f"| 笔记总数 | {snapshot['notes_count']} |",
        f"| 链接总数 | {snapshot['links_count']} |",
        f"| 唯一边数 | {snapshot['unique_edges']} |",
        f"| 标签种类 | {snapshot['tags_count']} |",
        "",
    ]
    
    if trends['has_trend']:
        lines.extend([
            "## 对比昨天",
            "",
            f"| 指标 | 变化 |",
            f"|------|------|",
            f"| 笔记 | {'+' if trends['notes_delta'] >= 0 else ''}{trends['notes_delta']} |",
            f"| 链接 | {'+' if trends['links_delta'] >= 0 else ''}{trends['links_delta']} |",
            f"| 边 | {'+' if trends['edges_delta'] >= 0 else ''}{trends['edges_delta']} |",
            f"| 标签 | {'+' if trends['tags_delta'] >= 0 else ''}{trends['tags_delta']} |",
            "",
        ])
    
    # 目录分布
    lines.extend(["## 目录分布", ""])
    for dir_name, count in sorted(snapshot['dir_distribution'].items(), key=lambda x: x[1], reverse=True)[:10]:
        bar = '█' * min(count, 30)
        lines.append(f"- `{dir_name}`: {count} {bar}")
    
    # 历史趋势图（文本版）
    if len(history) > 1:
        lines.extend(["", "## 历史趋势（最近30天笔记数）", ""])
        recent = history[-30:]
        max_notes = max(h['notes_count'] for h in recent)
        min_notes = min(h['notes_count'] for h in recent)
        range_notes = max_notes - min_notes if max_notes > min_notes else 1
        
        for h in recent:
            bar_len = int((h['notes_count'] - min_notes) / range_notes * 20) + 1
            date_short = h['date'][5:]  # MM-DD
            lines.append(f"  {date_short} | {'█' * bar_len} {h['notes_count']}")
    
    output_file.write_text('\n'.join(lines), encoding='utf-8')
    print(f"\n✅ 报告已保存: {output_file}")
    print(f"✅ 历史数据: {SNAPSHOT_FILE} ({len(history)}条记录)")

if __name__ == "__main__":
    main()
