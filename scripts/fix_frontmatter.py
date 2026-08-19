#!/usr/bin/env python3
"""
批量补全frontmatter脚本
为缺少frontmatter的笔记自动添加基础字段。
"""
import os
import re
from pathlib import Path
from datetime import datetime

VAULT = Path("~/vault")

def has_frontmatter(content):
    return content.startswith("---\n") or content.startswith("---\r\n")

def extract_title(content, file_path):
    match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return file_path.stem

def extract_tags(content):
    tags = set()
    for tag in re.findall(r"(?:^|\s)#([a-zA-Z-][\w-/]*)", content):
        tags.add(tag)
    return sorted(tags)

def guess_type(file_path, content):
    rel = file_path.relative_to(VAULT)
    parts = rel.parts
    if "wiki" in parts:
        if "entities" in parts:
            return "entity"
        elif "concepts" in parts:
            return "concept"
        elif "comparisons" in parts:
            return "comparison"
        elif "raw" in parts:
            return "raw"
    if "" in parts:
        return "review"
    if "" in parts:
        return "output"
    if "" in parts:
        return "process"
    return "note"

def add_frontmatter(file_path):
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return {"status": "error", "error": str(e)}

    if has_frontmatter(content):
        return {"status": "skip", "reason": "rontmatter"}

    if file_path.name.startswith(".") or file_path.name.startswith("_"):
        return {"status": "skip", "reason": ""}

    title = extract_title(content, file_path)
    tags = extract_tags(content)
    note_type = guess_type(file_path, content)
    today = datetime.now().strftime("%Y-%m-%d")

    lines = ["---"]
    lines.append('title: "' + title + '"')
    lines.append("created: " + today)
    lines.append("updated: " + today)
    lines.append("type: " + note_type)
    if tags:
        lines.append("tags:")
        for tag in tags[:5]:
            lines.append("  - " + tag)
    lines.append("---")
    lines.append("")

    new_content = "\n".join(lines) + content
    file_path.write_text(new_content, encoding="utf-8")

    return {"status": "fixed", "title": title, "type": note_type, "tags": len(tags)}

def main():
    print("批量补全frontmatter...")
    print("Vault: " + str(VAULT))

    stats = {"total": 0, "skip": 0, "fixed": 0, "error": 0}
    fixed_files = []

    for md_file in sorted(VAULT.rglob("*.md")):
        if any(p.startswith(".") for p in md_file.parts):
            continue
        if md_file.name.startswith("_"):
            continue

        stats["total"] += 1
        result = add_frontmatter(md_file)

        if result["status"] == "skip":
            stats["skip"] += 1
        elif result["status"] == "fixed":
            stats["fixed"] += 1
            fixed_files.append({
                "file": str(md_file.relative_to(VAULT)),
                "title": result["title"],
                "type": result["type"],
                "tags": result["tags"]
            })
        elif result["status"] == "error":
            stats["error"] += 1
            print("  [ERR] " + str(md_file.relative_to(VAULT)) + ": " + result["error"])

    print("\n :")
    print("  : " + str(stats["total"]) + " ")
    print("  (): " + str(stats["skip"]) + " ")
    print("  : " + str(stats["fixed"]) + " ")
    print("  : " + str(stats["error"]) + " ")

    if fixed_files:
        print("\n[OK] :")
        for f in fixed_files:
            print("  " + f["file"] + " -> [" + f["type"] + "] " + f["title"] + " (" + str(f["tags"]) + ")")

if __name__ == "__main__":
    main()
