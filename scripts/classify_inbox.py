#!/usr/bin/env python3
"""
Inbox分类器 - cron每晚运行
扫描00-Inbox/*.md，AI分类后移动到对应目录。
2026-08-18: 集成 hash_dedup 预摄入门控（P0-3）
"""
import os
import re
import json
import subprocess
from pathlib import Path
from datetime import datetime
from hash_dedup import ingest_gate, record_ingestion

VAULT = Path(os.environ.get("VAULT_PATH", os.path.expanduser(os.environ.get("VAULT_PATH", os.path.expanduser("~/vault")))))
INBOX = VAULT / "00-Inbox"
LOG_FILE = VAULT / "wiki" / "log.md"

TARGETS = {
    "entities": VAULT / "wiki" / "entities",
    "concepts": VAULT / "wiki" / "concepts",
    "comparisons": VAULT / "wiki" / "comparisons",
    "raw": VAULT / "wiki" / "raw",
    "flow": VAULT / "流程",
    "output": VAULT / "工作室产出",
    "review": VAULT / "复盘",
}

def extract_frontmatter(content):
    """提取YAML frontmatter"""
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

def classify_with_ai(title, content_preview):
    """调用AI进行分类（用Gemini免费通道）"""
    prompt = f"""你是知识库分类器。根据以下笔记内容，判断它应该归入哪个目录。

笔记标题: {title}
内容预览: {content_preview[:500]}

可选目录:
- entities: 工具/配置/人物/项目（有明确实体，可长期维护）
- concepts: 技术/方法/理论（抽象概念，需要解释）
- comparisons: 方案对比（A vs B结构）
- raw: 原始素材/报告（只读不改，保留原貌）
- flow: 可执行的流程文档
- output: 已完成的交付物（文章/报告）
- review: 经验总结/复盘

请返回JSON格式:
{{"target": "目录名", "name": "文件名(不含.md)", "tags": ["标签1", "标签2"], "summary": "一句话摘要"}}"""

    try:
        result = subprocess.run(
            ["python3", "~/.hermes/scripts/ask_gemini.py", prompt],
            capture_output=True, text=True, timeout=30
        )
        response = result.stdout.strip()
        # 尝试从响应中提取JSON
        json_match = re.search(r'\{[^{}]*\}', response)
        if json_match:
            return json.loads(json_match.group())
    except Exception as e:
        print(f"  AI分类失败: {e}")

    # 默认分类到raw
    return {"target": "raw", "name": title, "tags": [], "summary": ""}

def move_file(file_path, classification):
    """移动文件到目标目录，更新frontmatter"""
    target_dir = TARGETS.get(classification["target"], TARGETS["raw"])
    target_dir.mkdir(parents=True, exist_ok=True)

    new_name = classification.get("name", file_path.stem) + ".md"
    target_path = target_dir / new_name

    # 避免覆盖
    if target_path.exists():
        target_path = target_dir / f"{file_path.stem}.md"

    # 读取原内容
    content = file_path.read_text(encoding="utf-8")
    fm, body = extract_frontmatter(content)

    # 更新frontmatter
    today = datetime.now().strftime("%Y-%m-%d")
    new_fm = "---\n"
    new_fm += f'title: "{classification.get("name", fm.get("title", file_path.stem))}"\n'
    new_fm += f"created: {fm.get('created', today)}\n"
    new_fm += f"updated: {today}\n"
    new_fm += f"type: {classification['target']}\n"
    if classification.get("tags"):
        new_fm += "tags:\n"
        for tag in classification["tags"]:
            new_fm += f"  - {tag}\n"
    if classification.get("summary"):
        new_fm += f'summary: "{classification["summary"]}"\n'
    new_fm += "---\n\n"

    # 写入目标文件
    target_path.write_text(new_fm + body, encoding="utf-8")

    # 删除原文件
    file_path.unlink()

    return target_path

def update_log(action, details):
    """更新log.md"""
    today = datetime.now().strftime("%Y-%m-%d")
    time_now = datetime.now().strftime("%H:%M")
    entry = f"\n- [{today} {time_now}] {action} | {details}\n"

    if LOG_FILE.exists():
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry)
    else:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        LOG_FILE.write_text(f"# Knowledge Log\n{entry}", encoding="utf-8")

def main():
    print("Inbox 分类器启动...")

    if not INBOX.exists():
        print("Inbox目录不存在")
        return

    # 扫描Inbox中的md文件
    files = list(INBOX.glob("*.md"))
    files = [f for f in files if f.name != "README.md"]

    if not files:
        print("Inbox为空，无需分类")
        return

    print(f"发现 {len(files)} 个待分类文件")

    results = {"success": 0, "skip": 0, "error": 0}

    for file_path in files:
        print(f"\n处理: {file_path.name}")

        try:
            content = file_path.read_text(encoding="utf-8")
            fm, body = extract_frontmatter(content)

            # 跳过已处理的
            if fm.get("status") == "processed":
                print(f"  跳过: 已处理")
                results["skip"] += 1
                continue

            # P0-3: 预摄入门控（哈希去重）
            gate = ingest_gate(file_path)
            if not gate["allow"]:
                print(f"  跳过: {gate['reason']}")
                if gate["duplicate_of"]:
                    print(f"    重复于: {gate['duplicate_of']}")
                results["skip"] += 1
                continue

            title = fm.get("title", file_path.stem)

            # AI分类
            classification = classify_with_ai(title, body)
            print(f"  分类: {classification.get('target', 'unknown')} -> {classification.get('name', file_path.stem)}")

            # 移动文件
            target_path = move_file(file_path, classification)
            print(f"  移动: {target_path.relative_to(VAULT)}")

            # P0-3: 记录已摄入哈希
            record_ingestion(target_path)

            # 更新日志
            update_log("inbox_classify", f"{file_path.name} -> {target_path.relative_to(VAULT)}")

            results["success"] += 1

        except Exception as e:
            print(f"  错误: {e}")
            results["error"] += 1

    print(f"\n分类完成: 成功 {results['success']}, 跳过 {results['skip']}, 错误 {results['error']}")

if __name__ == "__main__":
    main()
