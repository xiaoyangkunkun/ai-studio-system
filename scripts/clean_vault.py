#!/usr/bin/env python3
"""
清理空文件/无效文件脚本
删除空的md文件和无内容的stub文件。
"""
import os
from pathlib import Path

VAULT = Path("/root/vault")

def main():
    print(" ...")

    stats = {"total": 0, "empty": 0, "stub": 0, "deleted": 0}
    deleted_files = []

    for md_file in sorted(VAULT.rglob("*.md")):
        if any(p.startswith(".") for p in md_file.parts):
            continue
        if md_file.name.startswith("_"):
            continue

        stats["total"] += 1

        try:
            content = md_file.read_text(encoding="utf-8")
            # 去掉frontmatter后检查内容
            body = content
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    body = parts[2].strip()

            # 空文件（只有frontmatter或完全为空）
            if not body or len(body) < 10:
                stats["empty"] += 1
                deleted_files.append({
                    "file": str(md_file.relative_to(VAULT)),
                    "reason": "",
                    "size": md_file.stat().st_size
                })
                md_file.unlink()
                stats["deleted"] += 1

            # stub文件（只有标题没有正文）
            elif body.startswith("# ") and len(body.split("\n")) <= 3:
                lines = [l for l in body.split("\n") if l.strip()]
                if len(lines) <= 1:
                    stats["stub"] += 1
                    deleted_files.append({
                        "file": str(md_file.relative_to(VAULT)),
                        "reason": "stub",
                        "size": md_file.stat().st_size
                    })
                    md_file.unlink()
                    stats["deleted"] += 1

        except Exception as e:
            print("  [ERR] " + str(md_file.relative_to(VAULT)) + ": " + str(e))

    print("\n :")
    print("  : " + str(stats["total"]) + " ")
    print("  : " + str(stats["empty"]) + " ")
    print("  stub: " + str(stats["stub"]) + " ")
    print("  : " + str(stats["deleted"]) + " ")

    if deleted_files:
        print("\n :")
        for f in deleted_files:
            print("  " + f["file"] + " (" + f["reason"] + ", " + str(f["size"]) + "B)")

if __name__ == "__main__":
    main()
