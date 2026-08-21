#!/usr/bin/env python3
"""
死链检测+修复脚本
检测链接到不存在笔记的Wikilink，可选择自动创建stub文件。
"""
import os
import re
from pathlib import Path
from datetime import datetime

VAULT = Path(os.environ.get("VAULT_PATH", os.path.expanduser(os.environ.get("VAULT_PATH", os.path.expanduser("~/vault")))))

def extract_wikilinks(content):
    return set(re.findall(r"\[\[([^\]|#]+?)(?:[|#][^\]]*)?\]\]", content))

def main():
    import sys
    auto_fix = "--fix" in sys.argv

    print(" ...")
    print("Vault: " + str(VAULT))

    # 收集所有存在的笔记
    existing_notes = set()
    for md_file in VAULT.rglob("*.md"):
        if any(p.startswith(".") for p in md_file.parts):
            continue
        existing_notes.add(md_file.stem)

    # 扫描所有链接
    dead_links = []
    total_files = 0
    total_links = 0

    for md_file in sorted(VAULT.rglob("*.md")):
        if any(p.startswith(".") for p in md_file.parts):
            continue
        if md_file.name.startswith("_"):
            continue

        total_files += 1
        try:
            content = md_file.read_text(encoding="utf-8")
            links = extract_wikilinks(content)
            total_links += len(links)

            for link in links:
                if link not in existing_notes:
                    dead_links.append({
                        "source": str(md_file.relative_to(VAULT)),
                        "target": link
                    })
        except Exception:
            continue

    print("\n :")
    print("  : " + str(total_files) + " , " + str(total_links) + " ")
    print("  : " + str(len(dead_links)) + " ")

    if dead_links:
        print("\n :")
        for dl in dead_links:
            print("  " + dl["source"] + " -> " + dl["target"])

        if auto_fix:
            print("\n ...")
            today = datetime.now().strftime("%Y-%m-%d")
            created = 0

            # 按target分组，一次创建一个stub
            targets = set(dl["target"] for dl in dead_links)
            for target in sorted(targets):
                stub_path = VAULT / (target + ".md")
                if not stub_path.exists():
                    content = "---\n"
                    content += 'title: "' + target + '"\n'
                    content += "created: " + today + "\n"
                    content += "updated: " + today + "\n"
                    content += "type: stub\n"
                    content += "status: placeholder\n"
                    content += "---\n\n"
                    content += "# " + target + "\n\n"
                    content += "> stub\n"
                    stub_path.write_text(content, encoding="utf-8")
                    created += 1
                    print("  [OK] : " + str(stub_path.relative_to(VAULT)))

            print("\n " + str(created) + " stub")
        else:
            print("\n:  python3 fix_dead_links.py --fix stub")

if __name__ == "__main__":
    main()
