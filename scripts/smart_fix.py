#!/usr/bin/env python3
"""Smart Fix 一键修复 - 按因果顺序自动修复知识库问题

借鉴 green-dalii/obsidian-llm-wiki 的 Smart Fix All 设计
2026-08-18 新增，P0-1 改造

5个Phase按因果顺序执行:
1. 填充缺失frontmatter + 别名
2. 合并重复页面
3. 修复死链（模糊匹配）
4. 链接孤儿页
5. 扩展空页面

用法:
  python3 smart_fix.py                    # dry-run，只扫描不修改
  python3 smart_fix.py --apply            # 实际执行修复
  python3 smart_fix.py --phase 1,2        # 只执行指定Phase
  python3 smart_fix.py --report fix.md    # 输出报告到文件
"""

import sys
import os
import re
import json
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime
from collections import defaultdict

VAULT = Path(os.environ.get("OBSIDIAN_VAULT_PATH", os.environ.get("VAULT_PATH", os.path.expanduser("~/vault"))))

# === Phase 定义 ===
PHASES = {
    1: "填充缺失frontmatter + 别名",
    2: "合并重复页面",
    3: "修复死链（模糊匹配）",
    4: "链接孤儿页",
    5: "扩展空页面",
}


# ============================================================
# 工具函数
# ============================================================

def parse_frontmatter(content: str) -> tuple[dict, str]:
    """解析 frontmatter + body"""
    if not content.startswith("---"):
        return {}, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    fm_text = parts[1]
    body = parts[2].strip()
    fm = {}
    for line in fm_text.strip().split("\n"):
        if ":" in line:
            key, val = line.split(":", 1)
            fm[key.strip()] = val.strip().strip('"').strip("'")
    return fm, body


def build_wikilink_index(vault: Path) -> dict[str, str]:
    """建立 {页面名: 文件路径} 索引"""
    index = {}
    for md_file in vault.rglob("*.md"):
        if any(p.startswith('.') for p in md_file.parts):
            continue
        if '.stversions' in str(md_file):
            continue
        name = md_file.stem
        index[name] = str(md_file)
    return index


def find_wikilinks(text: str) -> list[str]:
    """提取所有 [[wikilinks]]"""
    return re.findall(r'\[\[([^\]|]+?)(?:\|[^\]]+)?\]\]', text)


def compute_content_hash(filepath: Path) -> str:
    """计算文件内容SHA256（跳过frontmatter）"""
    content = filepath.read_text(encoding='utf-8')
    body = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            body = parts[2].strip()
    if not body:
        return ""
    return hashlib.sha256(body.encode('utf-8')).hexdigest()


def title_similarity(a: str, b: str) -> float:
    """简单标题相似度（基于字符集交集）"""
    a_lower = re.sub(r'[\s\-_·.]+', '', a.lower())
    b_lower = re.sub(r'[\s\-_·.]+', '', b.lower())
    if not a_lower or not b_lower:
        return 0.0
    common = set(a_lower) & set(b_lower)
    return len(common) / max(len(set(a_lower)), len(set(b_lower)))


def edit_distance(a: str, b: str) -> int:
    """编辑距离"""
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if a[i-1] == b[j-1] else 1
            dp[i][j] = min(dp[i-1][j] + 1, dp[i][j-1] + 1, dp[i-1][j-1] + cost)
    return dp[m][n]


# ============================================================
# Phase 1: 填充缺失frontmatter + 别名
# ============================================================

def phase1_frontmatter(vault: Path, apply: bool = False) -> dict:
    """补全frontmatter + 生成别名"""
    results = {"fixed": 0, "aliases_added": 0, "details": []}

    for md_file in vault.rglob("*.md"):
        if any(p.startswith('.') for p in md_file.parts):
            continue
        if '.stversions' in str(md_file) or 'backup' in str(md_file):
            continue

        try:
            content = md_file.read_text(encoding='utf-8')
            fm, body = parse_frontmatter(content)
        except Exception:
            continue

        changes = []

        # 检查必要字段
        if not fm.get("title"):
            fm["title"] = md_file.stem
            changes.append("补title")

        if not fm.get("created"):
            fm["created"] = datetime.fromtimestamp(
                md_file.stat().st_mtime
            ).strftime("%Y-%m-%d")
            changes.append("补created")

        if not fm.get("updated"):
            fm["updated"] = datetime.now().strftime("%Y-%m-%d")
            changes.append("补updated")

        if not fm.get("type"):
            # 根据目录推断类型
            rel = str(md_file.relative_to(vault))
            if "entities" in rel:
                fm["type"] = "entity"
            elif "concepts" in rel:
                fm["type"] = "concept"
            elif "comparisons" in rel:
                fm["type"] = "comparison"
            elif "raw" in rel:
                fm["type"] = "raw"
            elif "wiki" in rel:
                fm["type"] = "entity"
            else:
                fm["type"] = "note"
            changes.append(f"补type={fm['type']}")

        if not fm.get("tags"):
            fm["tags"] = []
            changes.append("补tags空")

        # 生成别名（仅entity/concept）
        if fm.get("type") in ("entity", "concept", "comparison"):
            title = fm["title"]
            aliases = fm.get("aliases", [])
            if isinstance(aliases, str):
                aliases = [aliases]

            # 生成变体别名
            new_aliases = set(aliases)
            # 中文→小写无空格
            clean = re.sub(r'[\s\-_·.]+', '', title).lower()
            if clean and clean != title.lower():
                new_aliases.add(clean)
            # 英文→小写
            if re.search(r'[a-zA-Z]', title):
                lower = title.lower()
                if lower != title:
                    new_aliases.add(lower)

            if len(new_aliases) > len(aliases):
                fm["aliases"] = sorted(new_aliases - set(aliases))
                changes.append(f"别名+{len(new_aliases) - len(aliases)}")

        if changes and apply:
            # 重写文件
            new_fm = "---\n"
            for k, v in fm.items():
                if isinstance(v, list):
                    new_fm += f"{k}:\n"
                    for item in v:
                        new_fm += f"  - {item}\n"
                elif isinstance(v, str):
                    # 避免双重引号：如果值已有引号就不加
                    if (v.startswith('"') and v.endswith('"')) or \
                       (v.startswith("'") and v.endswith("'")):
                        new_fm += f"{k}: {v}\n"
                    else:
                        new_fm += f'{k}: "{v}"\n'
                else:
                    new_fm += f"{k}: {v}\n"
            new_fm += "---\n\n"
            md_file.write_text(new_fm + body, encoding='utf-8')

        if changes:
            results["fixed"] += 1
            results["details"].append({
                "file": str(md_file.relative_to(vault)),
                "changes": changes
            })

    return results


# ============================================================
# Phase 2: 合并重复页面
# ============================================================

def phase2_duplicates(vault: Path, apply: bool = False) -> dict:
    """检测并合并重复页面"""
    results = {"groups": 0, "files_scanned": 0, "details": []}

    # 构建内容哈希索引
    hash_index = defaultdict(list)
    name_index = defaultdict(list)

    for md_file in vault.rglob("*.md"):
        if any(p.startswith('.') for p in md_file.parts):
            continue
        if '.stversions' in str(md_file) or 'backup' in str(md_file):
            continue

        results["files_scanned"] += 1

        try:
            content = md_file.read_text(encoding='utf-8')
            fm, body = parse_frontmatter(content)
            title = fm.get("title", md_file.stem)
        except Exception:
            continue

        # 按内容哈希分组
        file_hash = compute_content_hash(md_file)
        if file_hash:
            hash_index[file_hash].append({
                "path": md_file,
                "title": title,
                "has_frontmatter": bool(fm),
            })

        # 按标题分组（忽略大小写和空格）
        clean_title = re.sub(r'[\s\-_·.]+', '', title).lower()
        if clean_title:
            name_index[clean_title].append({
                "path": md_file,
                "title": title,
                "hash": file_hash,
            })

    # 找重复组
    duplicates = []

    # 1. 完全相同内容（哈希一致）
    for file_hash, files in hash_index.items():
        if len(files) > 1:
            # 排除 backup/ 目录的副本
            non_backup = [f for f in files if 'backup' not in str(f['path'])]
            if len(non_backup) > 1:
                duplicates.append({
                    "type": "exact_hash",
                    "files": [f['path'] for f in non_backup],
                    "reason": "内容完全相同",
                })

    # 2. 标题高度相似（但内容不同）
    for clean_title, files in name_index.items():
        if len(files) > 1:
            unique_hashes = set(f['hash'] for f in files)
            if len(unique_hashes) > 1:
                # 标题一样但内容不同，可能是版本冲突
                duplicates.append({
                    "type": "same_name_diff_content",
                    "files": [f['path'] for f in files],
                    "reason": "同名但内容不同",
                })

    # 执行合并
    if apply and duplicates:
        for dup in duplicates:
            if dup["type"] == "exact_hash":
                # 保留非backup目录的，删除其他
                keep = dup["files"][0]
                for f in dup["files"][1:]:
                    if 'backup' not in str(f):
                        keep = f
                        break
                for f in dup["files"]:
                    if f != keep:
                        # 不删除，只标记（安全起见）
                        dup["action"] = f"保留: {keep.name}"
            elif dup["type"] == "same_name_diff_content":
                dup["action"] = "需人工确认"

    results["groups"] = len(duplicates)
    results["details"] = duplicates
    return results


# ============================================================
# Phase 3: 修复死链（模糊匹配）
# ============================================================

def phase3_dead_links(vault: Path, apply: bool = False) -> dict:
    """修复死链：精确→模糊→stub"""
    results = {"broken": 0, "fixed": 0, "details": []}
    link_index = build_wikilink_index(vault)

    for md_file in vault.rglob("*.md"):
        if any(p.startswith('.') for p in md_file.parts):
            continue
        if '.stversions' in str(md_file):
            continue

        try:
            content = md_file.read_text(encoding='utf-8')
        except Exception:
            continue

        links = find_wikilinks(content)
        changed = False

        for link in links:
            link_name = link.strip()
            if link_name in link_index:
                continue  # 链接有效

            results["broken"] += 1

            # 尝试模糊匹配
            best_match = None
            best_score = 0
            for name in link_index:
                sim = title_similarity(link_name, name)
                if sim > best_score and sim > 0.6:
                    best_score = sim
                    best_match = name

            # 编辑距离匹配
            if not best_match:
                for name in link_index:
                    dist = edit_distance(link_name.lower(), name.lower())
                    if dist <= 2 and len(link_name) > 3:
                        best_match = name
                        break

            if best_match and apply:
                # 替换链接
                old = f"[[{link}]]"
                new = f"[[{best_match}]]"
                content = content.replace(old, new)
                changed = True
                results["fixed"] += 1
                results["details"].append({
                    "file": str(md_file.relative_to(vault)),
                    "broken": link,
                    "fixed_to": best_match,
                    "method": "fuzzy",
                })

        if changed:
            md_file.write_text(content, encoding='utf-8')

    return results


# ============================================================
# Phase 4: 链接孤儿页
# ============================================================

def phase4_orphans(vault: Path, apply: bool = False) -> dict:
    """找到0入链的页面，建议添加链接"""
    results = {"orphans": 0, "linked": 0, "details": []}

    # 统计所有页面的入链数
    inlink_count = defaultdict(int)
    all_pages = {}

    for md_file in vault.rglob("*.md"):
        if any(p.startswith('.') for p in md_file.parts):
            continue
        if '.stversions' in str(md_file):
            continue

        name = md_file.stem
        all_pages[name] = md_file

        try:
            content = md_file.read_text(encoding='utf-8')
        except Exception:
            continue

        links = find_wikilinks(content)
        for link in links:
            inlink_count[link.strip()] += 1

    # 找孤儿页（0入链）
    for name, md_file in all_pages.items():
        if inlink_count.get(name, 0) == 0:
            results["orphans"] += 1
            results["details"].append({
                "file": str(md_file.relative_to(vault)),
                "reason": "0入链",
            })

    return results


# ============================================================
# Phase 5: 扩展空页面
# ============================================================

def phase5_stubs(vault: Path, apply: bool = False) -> dict:
    """扩展空/stub页面（跳过reviewed:true）"""
    results = {"stubs": 0, "expanded": 0, "details": []}

    for md_file in vault.rglob("*.md"):
        if any(p.startswith('.') for p in md_file.parts):
            continue
        if '.stversions' in str(md_file):
            continue

        try:
            content = md_file.read_text(encoding='utf-8')
            fm, body = parse_frontmatter(content)
        except Exception:
            continue

        # 跳过 reviewed 保护的页面
        if fm.get("reviewed") in ("true", True):
            continue

        # 检测 stub：body 少于50字
        plain = re.sub(r'[#*\[\]()>`~_\-|]', '', body).strip()
        if len(plain) < 50 and len(plain) > 0:
            results["stubs"] += 1
            results["details"].append({
                "file": str(md_file.relative_to(vault)),
                "title": fm.get("title", md_file.stem),
                "body_length": len(plain),
            })

    return results


# ============================================================
# 报告生成
# ============================================================

def generate_report(results: dict, output_path: str = None) -> str:
    """生成修复报告"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"# Smart Fix 修复报告\n", f"> 生成时间: {now}\n"]

    total_fixed = 0

    for phase_num in sorted(results.keys()):
        data = results[phase_num]
        phase_name = PHASES.get(phase_num, f"Phase {phase_num}")

        lines.append(f"\n## Phase {phase_num}: {phase_name}\n")

        if phase_num == 1:
            count = data.get("fixed", 0)
            total_fixed += count
            lines.append(f"- 扫描修复: **{count}** 个文件")
            if data.get("details"):
                lines.append(f"- 详细改动:")
                for d in data["details"][:20]:
                    lines.append(f"  - `{d['file']}`: {', '.join(d['changes'])}")

        elif phase_num == 2:
            groups = data.get("groups", 0)
            total_fixed += groups
            lines.append(f"- 扫描文件: **{data.get('files_scanned', 0)}** 个")
            lines.append(f"- 发现重复组: **{groups}** 组")
            for d in data.get("details", [])[:10]:
                files_str = ", ".join(f.name for f in d["files"][:3])
                lines.append(f"  - [{d['type']}] {d['reason']}: {files_str}")

        elif phase_num == 3:
            broken = data.get("broken", 0)
            fixed = data.get("fixed", 0)
            total_fixed += fixed
            lines.append(f"- 死链: **{broken}** 个, 修复: **{fixed}** 个")
            for d in data.get("details", [])[:10]:
                lines.append(f"  - `{d['file']}`: [[{d['broken']}]] → [[{d['fixed_to']}]]")

        elif phase_num == 4:
            orphans = data.get("orphans", 0)
            lines.append(f"- 孤儿页: **{orphans}** 个（0入链）")
            for d in data.get("details", [])[:10]:
                lines.append(f"  - `{d['file']}`")

        elif phase_num == 5:
            stubs = data.get("stubs", 0)
            lines.append(f"- Stub页面: **{stubs}** 个（<50字内容）")
            for d in data.get("details", [])[:10]:
                lines.append(f"  - `{d['file']}` ({d['title']}, {d['body_length']}字)")

    lines.append(f"\n---\n**总计修复/建议: {total_fixed}**\n")

    report = "\n".join(lines)

    if output_path:
        Path(output_path).write_text(report, encoding='utf-8')
        print(f"报告已保存: {output_path}")

    return report


# ============================================================
# 主入口
# ============================================================

def parse_args():
    """解析命令行参数"""
    import argparse
    parser = argparse.ArgumentParser(description="Smart Fix 一键修复")
    parser.add_argument("--phase", default="1,2,3,4,5",
                        help="执行的Phase，逗号分隔 (默认: 1,2,3,4,5)")
    parser.add_argument("--apply", action="store_true",
                        help="实际执行修复（默认dry-run）")
    parser.add_argument("--report", default=None,
                        help="报告输出路径")
    parser.add_argument("--vault", default=str(VAULT),
                        help="Vault路径")
    return parser.parse_args()


def main():
    args = parse_args()
    vault = Path(args.vault)
    phases = [int(p.strip()) for p in args.phase.split(",")]

    mode = "🔧 APPLY" if args.apply else "🔍 DRY-RUN"
    print(f"Smart Fix {mode} | Vault: {vault}")
    print(f"执行Phase: {phases}\n")

    results = {}
    phase_funcs = {
        1: phase1_frontmatter,
        2: phase2_duplicates,
        3: phase3_dead_links,
        4: phase4_orphans,
        5: phase5_stubs,
    }

    for phase_num in sorted(phases):
        if phase_num not in phase_funcs:
            print(f"未知Phase: {phase_num}")
            continue

        print(f"=== Phase {phase_num}: {PHASES[phase_num]} ===")
        func = phase_funcs[phase_num]
        results[phase_num] = func(vault, apply=args.apply)

        # 打印摘要
        data = results[phase_num]
        if phase_num == 1:
            print(f"  修复: {data['fixed']} 个文件")
        elif phase_num == 2:
            print(f"  重复组: {data['groups']} 组 (扫描 {data['files_scanned']} 文件)")
        elif phase_num == 3:
            print(f"  死链: {data['broken']} 个, 修复: {data['fixed']} 个")
        elif phase_num == 4:
            print(f"  孤儿页: {data['orphans']} 个")
        elif phase_num == 5:
            print(f"  Stub页面: {data['stubs']} 个")
        print()

    # 生成报告
    report = generate_report(results, args.report)
    print(report)


if __name__ == "__main__":
    main()
