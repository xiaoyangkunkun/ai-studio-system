#!/usr/bin/env python3
"""内容哈希去重 - 预摄入门控 + SHA256去重

借鉴 green-dalii/obsidian-llm-wiki 的 Smart Batch Skip + content hash
2026-08-18 新增，P0-3 改造
"""

import hashlib
import json
import re
import sys
from pathlib import Path

# === 配置 ===
VAULT = Path(os.environ.get("VAULT_PATH", os.path.expanduser(os.environ.get("VAULT_PATH", os.path.expanduser("~/vault")))))
HASH_LOG = VAULT / ".hash_log.jsonl"  # 已摄入文件的哈希记录
MIN_CONTENT_LENGTH = 50  # 小于此字数视为无效内容


def compute_content_hash(filepath: str | Path) -> str:
    """计算文件内容的SHA256（跳过frontmatter）"""
    content = Path(filepath).read_text(encoding='utf-8')

    # 跳过 frontmatter (--- ... ---)
    body = content
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            body = parts[2].strip()

    if not body:
        return ""

    return hashlib.sha256(body.encode('utf-8')).hexdigest()


def is_empty_or_stub(filepath: str | Path) -> bool:
    """空文件/纯frontmatter/stub文件检测"""
    content = Path(filepath).read_text(encoding='utf-8')

    # 跳过 frontmatter
    body = content
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            body = parts[2].strip()

    # 去掉 markdown 标记后的纯文本
    plain = re.sub(r'[#*\[\]()>`~_\-|]', '', body).strip()

    return len(plain) < MIN_CONTENT_LENGTH


def build_hash_index(vault_path: str | Path = VAULT) -> dict[str, list[str]]:
    """扫描 vault 中所有 md 文件，建立 {content_hash: [filepath, ...]} 索引"""
    index = {}
    vault = Path(vault_path)

    for md_file in vault.rglob("*.md"):
        # 跳过隐藏目录和 .stversions
        parts = md_file.parts
        if any(p.startswith('.') for p in parts):
            continue
        if '.stversions' in str(md_file):
            continue

        try:
            h = compute_content_hash(md_file)
            if h:
                index.setdefault(h, []).append(str(md_file))
        except Exception:
            continue

    return index


def check_duplicate(filepath: str | Path,
                    hash_index: dict[str, list[str]] | None = None) -> str:
    """
    检查文件是否重复
    返回: 'EXACT' | 'SIMILAR' | 'NEW'
    """
    file_hash = compute_content_hash(filepath)
    if not file_hash:
        return "EMPTY"

    if hash_index is None:
        hash_index = build_hash_index()

    # 完全相同的内容
    if file_hash in hash_index:
        # 排除自身
        others = [f for f in hash_index[file_hash]
                  if str(f) != str(filepath)]
        if others:
            return "EXACT"

    # 标题相同但内容不同（检查同目录下的文件名）
    filepath = Path(filepath)
    title = filepath.stem
    for existing_path in hash_index.get(file_hash, []):
        existing = Path(existing_path)
        if existing.name == filepath.name and existing != filepath:
            return "EXACT"

    return "NEW"


def load_hash_log() -> dict[str, str]:
    """加载已摄入的哈希记录 {sha256: filepath}"""
    log = {}
    if HASH_LOG.exists():
        for line in HASH_LOG.read_text().strip().split('\n'):
            if line.strip():
                try:
                    entry = json.loads(line)
                    log[entry['hash']] = entry['path']
                except (json.JSONDecodeError, KeyError):
                    continue
    return log


def append_hash_log(filepath: str | Path, file_hash: str):
    """追加一条哈希记录"""
    entry = json.dumps({
        "hash": file_hash,
        "path": str(filepath),
        "action": "ingested"
    }, ensure_ascii=False)
    with open(HASH_LOG, 'a', encoding='utf-8') as f:
        f.write(entry + '\n')


def ingest_gate(filepath: str | Path,
                vault_path: str | Path = VAULT) -> dict:
    """
    预摄入门控：检查文件是否允许摄入
    返回: {"allow": bool, "reason": str, "duplicate_of": str|None}
    """
    filepath = Path(filepath)

    # 1. 文件存在性
    if not filepath.exists():
        return {"allow": False, "reason": "文件不存在", "duplicate_of": None}

    # 2. 空文件/stub检查
    if is_empty_or_stub(filepath):
        return {"allow": False, "reason": "空文件或内容过少(<50字)", "duplicate_of": None}

    # 3. 去重检查
    hash_log = load_hash_log()
    file_hash = compute_content_hash(filepath)

    if file_hash in hash_log:
        dup_path = hash_log[file_hash]
        return {"allow": False, "reason": "内容完全相同", "duplicate_of": dup_path}

    # 4. 全新内容，允许摄入
    return {"allow": True, "reason": "新内容", "duplicate_of": None}


def record_ingestion(filepath: str | Path):
    """记录已摄入文件的哈希"""
    file_hash = compute_content_hash(filepath)
    if file_hash:
        append_hash_log(filepath, file_hash)


# === CLI 入口 ===
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法:")
        print("  python3 hash_dedup.py check <file>     # 检查文件是否重复")
        print("  python3 hash_dedup.py gate <file>       # 预摄入门控")
        print("  python3 hash_dedup.py record <file>     # 记录已摄入")
        print("  python3 hash_dedup.py index             # 构建哈希索引")
        sys.exit(1)

    cmd = sys.argv[1]
    target = sys.argv[2] if len(sys.argv) > 2 else None

    if cmd == "check" and target:
        result = check_duplicate(target)
        print(f"结果: {result}")

    elif cmd == "gate" and target:
        result = ingest_gate(target)
        status = "✅ 允许摄入" if result["allow"] else "❌ 跳过"
        print(f"{status} | {result['reason']}")
        if result["duplicate_of"]:
            print(f"  重复于: {result['duplicate_of']}")

    elif cmd == "record" and target:
        record_ingestion(target)
        print(f"✅ 已记录: {target}")

    elif cmd == "index":
        print("构建哈希索引中...")
        idx = build_hash_index()
        print(f"索引完成: {len(idx)} 个唯一内容, {sum(len(v) for v in idx.values())} 个文件")
        # 显示重复文件
        dups = {h: files for h, files in idx.items() if len(files) > 1}
        if dups:
            print(f"\n发现 {len(dups)} 组重复:")
            for h, files in dups.items():
                print(f"  {files[0]}")
                for f in files[1:]:
                    print(f"    ↔ {f}")
        else:
            print("无重复文件")
    else:
        print("未知命令")
        sys.exit(1)
