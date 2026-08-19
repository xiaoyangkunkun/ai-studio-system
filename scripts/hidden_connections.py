#!/usr/bin/env python3
"""
隐藏关联发现脚本
找出没有直接Wikilink但有≥2个共同邻居的笔记对，推荐连接。
零成本纯Python，cron每晚运行。
"""
import os
import re
import json
from collections import defaultdict
from pathlib import Path
from datetime import datetime

VAULT = Path("~/vault")
OUTPUT_DIR = VAULT / "wiki" / "analytics"
MIN_COMMON_NEIGHBORS = 2
MAX_RECOMMENDATIONS = 20

def extract_wikilinks(content: str) -> set:
    """提取笔记中的所有Wikilink目标"""
    return set(re.findall(r'\[\[([^\]|#]+?)(?:[|#][^\]]*)?\]\]', content))

def build_graph(vault: Path) -> dict:
    """构建Wikilink图：{note: set(connected_notes)}"""
    graph = defaultdict(set)
    notes = set()
    
    for md_file in vault.rglob("*.md"):
        # 跳过临时文件和.git
        if any(p.startswith('.') for p in md_file.parts):
            continue
        if md_file.name.startswith('_'):
            continue
            
        note_name = md_file.stem
        notes.add(note_name)
        
        try:
            content = md_file.read_text(encoding='utf-8')
            links = extract_wikilinks(content)
            for link in links:
                graph[note_name].add(link)
                graph[link].add(note_name)  # 双向
        except Exception:
            continue
    
    return dict(graph), notes

def find_hidden_connections(graph: dict, notes: set) -> list:
    """找出隐藏关联：没有直接链接但有≥N个共同邻居的笔记对"""
    recommendations = []
    note_list = sorted(notes)
    
    for i, note_a in enumerate(note_list):
        neighbors_a = graph.get(note_a, set())
        if not neighbors_a:
            continue
            
        for note_b in note_list[i+1:]:
            # 跳过已有直接链接的
            if note_b in neighbors_a:
                continue
                
            neighbors_b = graph.get(note_b, set())
            common = neighbors_a & neighbors_b
            
            if len(common) >= MIN_COMMON_NEIGHBORS:
                recommendations.append({
                    'note_a': note_a,
                    'note_b': note_b,
                    'common_neighbors': sorted(common),
                    'count': len(common)
                })
    
    # 按共同邻居数排序
    recommendations.sort(key=lambda x: x['count'], reverse=True)
    return recommendations[:MAX_RECOMMENDATIONS]

def main():
    print("📊 隐藏关联发现扫描开始...")
    
    graph, notes = build_graph(VAULT)
    total_notes = len(notes)
    total_links = sum(len(v) for v in graph.values()) // 2
    isolated = sum(1 for n in notes if not graph.get(n))
    
    print(f"  笔记总数: {total_notes}")
    print(f"  链接总数: {total_links}")
    print(f"  孤立笔记: {isolated}")
    
    recommendations = find_hidden_connections(graph, notes)
    
    print(f"\n🔗 发现 {len(recommendations)} 个隐藏关联:")
    for r in recommendations:
        print(f"  {r['note_a']} ↔ {r['note_b']} ({r['count']}个共同邻居: {', '.join(r['common_neighbors'][:3])}{'...' if len(r['common_neighbors']) > 3 else ''})")
    
    # 输出到文件
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    output_file = OUTPUT_DIR / f"hidden-connections-{today}.md"
    
    lines = [
        f"# 隐藏关联发现 - {today}",
        "",
        f"> 扫描时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"> 笔记总数: {total_notes} | 链接总数: {total_links} | 孤立笔记: {isolated}",
        "",
        "## 推荐连接",
        ""
    ]
    
    if recommendations:
        for i, r in enumerate(recommendations, 1):
            lines.append(f"### {i}. {r['note_a']} ↔ {r['note_b']} ({r['count']}个共同邻居)")
            lines.append(f"- 共同邻居: {', '.join(['[[' + n + ']]' for n in r['common_neighbors']])}")
            lines.append("")
    else:
        lines.append("暂无隐藏关联发现。")
    
    output_file.write_text('\n'.join(lines), encoding='utf-8')
    print(f"\n✅ 报告已保存: {output_file}")
    
    # 同时输出JSON供其他脚本使用
    json_file = OUTPUT_DIR / "hidden-connections-latest.json"
    json_file.write_text(json.dumps({
        'date': today,
        'stats': {'total_notes': total_notes, 'total_links': total_links, 'isolated': isolated},
        'recommendations': recommendations
    }, ensure_ascii=False, indent=2), encoding='utf-8')

if __name__ == "__main__":
    main()
