#!/usr/bin/env python3
"""
Watchdog脚本：监听工作室产出目录，自动在Inbox创建摘要。
作为员工prompt的兜底保障。
"""
import os
import time
import hashlib
from pathlib import Path
from datetime import datetime

VAULT = Path("~/vault")
INBOX = VAULT / "00-Inbox"
WATCH_DIRS = [
    VAULT / "工作室产出" / "调研员·知远" / "调研报告",
    VAULT / "工作室产出" / "写作员·墨白",
]
STATE_FILE = Path("~/.hermes/data/watchdog_state.json")

def load_state():
    if STATE_FILE.exists():
        import json
        return json.loads(STATE_FILE.read_text())
    return {}

def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    import json
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))

def get_file_hash(file_path):
    return hashlib.md5(file_path.read_bytes()).hexdigest()

def create_inbox_summary(file_path, author, source_type):
    """在Inbox创建摘要文件"""
    today = datetime.now().strftime("%Y-%m-%d")
    title = file_path.stem

    # 读取文件前500字作为摘要
    content = file_path.read_text(encoding="utf-8")
    # 去掉frontmatter
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            content = parts[2].strip()
    summary = content[:200].replace("\n", " ").strip()

    # 检查Inbox是否已有同名文件（防重复）
    inbox_file = INBOX / f"auto-{file_path.stem}.md"
    if inbox_file.exists():
        return False

    # 创建摘要
    md_content = f"""---
title: "{title}"
created: {today}
type: inbox
source: {source_type}
author: {author}
status: inbox
tags: [{source_type}]
auto_generated: true
---
# {title}
{summary}...

原始路径：{file_path.relative_to(VAULT)}
"""
    inbox_file.write_text(md_content, encoding="utf-8")
    return True

def scan_and_process():
    """扫描产出目录，处理新文件"""
    state = load_state()
    new_files = 0

    for watch_dir in WATCH_DIRS:
        if not watch_dir.exists():
            continue

        for md_file in watch_dir.rglob("*.md"):
            file_key = str(md_file.relative_to(VAULT))
            file_hash = get_file_hash(md_file)

            # 检查是否是新文件或已修改
            if file_key in state and state[file_key] == file_hash:
                continue

            # 确定作者和类型
            if "调研员" in file_key:
                author = "知远"
                source_type = "research"
            elif "写作员" in file_key:
                author = "墨白"
                source_type = "writing"
            else:
                continue

            # 创建Inbox摘要
            if create_inbox_summary(md_file, author, source_type):
                print(f"  [NEW] {file_key}")
                new_files += 1

            # 更新状态
            state[file_key] = file_hash

    save_state(state)
    return new_files

def main():
    print("Watchdog: 扫描产出目录...")

    new_files = scan_and_process()

    if new_files > 0:
        print(f"发现 {new_files} 个新文件，已在Inbox创建摘要")
    else:
        print("无新文件")

if __name__ == "__main__":
    main()
