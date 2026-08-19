#!/usr/bin/env python3
"""Token预算 / 语义压缩

借鉴 ikeniborn/obsidian-ai-wiki 的 bounded processing + semantic compression
2026-08-18 新增，P0-2 改造

功能:
- estimate_tokens(): 字符级token估算（误差<15%）
- check_budget(): 检查文本是否超出token预算
- chunk_by_budget(): 按预算自动分批
- compress(): 三档语义压缩（maximum/balanced/minimum）

用法:
  python3 token_budget.py check <file>          # 检查文件token数
  python3 token_budget.py compress <file>       # 压缩后输出
  python3 token_budget.py compress <file> --level minimum  # 最小压缩
  python3 token_budget.py chunk <file1> <file2> # 按预算分批
"""

import sys
import os
import re
from pathlib import Path


def estimate_tokens(text: str) -> int:
    """估算文本token数（字符比例法，误差<15%）

    中文: ~1.5字符/token
    英文: ~0.75字符/token (约1.33 token/word)
    混合: 按比例加权
    """
    if not text:
        return 0

    # 统计中文字符数
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    # 统计英文单词数
    english_words = len(re.findall(r'[a-zA-Z]+', text))
    # 其他字符（数字、标点等）
    other_chars = len(text) - chinese_chars - sum(len(w) for w in re.findall(r'[a-zA-Z]+', text))

    # 估算
    chinese_tokens = chinese_chars / 1.5
    english_tokens = english_words / 0.75
    other_tokens = other_chars / 3.0  # 数字/标点通常合并成token

    return int(chinese_tokens + english_tokens + other_tokens)


def check_budget(texts: list[str],
                 model_limit: int = 8192,
                 reserve: int = 2048) -> dict:
    """检查文本列表是否超出token预算

    Args:
        texts: 文本列表
        model_limit: 模型上下文窗口大小
        reserve: 预留给输出的token数

    Returns:
        dict: {total_tokens, available, over_limit, chunks_needed}
    """
    available = model_limit - reserve
    total = sum(estimate_tokens(t) for t in texts)

    return {
        "total_tokens": total,
        "available": available,
        "over_limit": total > available,
        "chunks_needed": max(1, -(-total // available)),  # ceil division
        "utilization": f"{total/available*100:.1f}%" if available > 0 else "N/A",
    }


def chunk_by_budget(texts: list[str],
                    model_limit: int = 8192,
                    reserve: int = 2048) -> list[list[str]]:
    """按token预算分批，每批不超限

    按文件边界切分，不跨文件。

    Returns:
        list of chunks, each chunk is a list of texts
    """
    available = model_limit - reserve
    chunks = []
    current_chunk = []
    current_tokens = 0

    for text in texts:
        text_tokens = estimate_tokens(text)

        if current_tokens + text_tokens > available and current_chunk:
            chunks.append(current_chunk)
            current_chunk = []
            current_tokens = 0

        current_chunk.append(text)
        current_tokens += text_tokens

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def compress(text: str, level: str = "balanced") -> str:
    """语义压缩

    Args:
        text: 原文
        level: 'maximum' | 'balanced' | 'minimum'

    Returns:
        压缩后的文本
    """
    if level == "maximum":
        return compress_maximum(text)
    elif level == "balanced":
        return compress_balanced(text)
    elif level == "minimum":
        return compress_minimum(text)
    else:
        return text


def compress_maximum(text: str) -> str:
    """Maximum压缩: 仅做格式精简，保留所有语义内容

    策略:
    1. 删除多余空行（保留最多1个）
    2. 删除行尾空格
    3. 精简重复标记
    """
    lines = text.split('\n')
    result = []
    prev_empty = False

    for line in lines:
        stripped = line.rstrip()

        # 删除多余空行
        if not stripped:
            if not prev_empty:
                result.append('')
            prev_empty = True
            continue

        prev_empty = False
        result.append(stripped)

    return '\n'.join(result)


def compress_balanced(text: str) -> str:
    """Balanced压缩: 保留标题+关键段落+数据+结论

    策略:
    1. 保留所有标题行（#开头）
    2. 保留含数字/日期/URL/金额的行（关键数据）
    3. 保留表格
    4. 保留每段的第一句（主题句）
    5. 删除代码块内容（保留首行标记）
    6. 删除引用块详细展开（保留首行）
    """
    lines = text.split('\n')
    result = []
    in_code_block = False
    code_block_lines = 0
    in_quote = False

    for line in lines:
        stripped = line.strip()

        # 代码块处理
        if stripped.startswith('```'):
            in_code_block = not in_code_block
            if in_code_block:
                code_block_lines = 0
                result.append(line)  # 保留 opening ```
            else:
                result.append('```')  # 保留 closing ```
            continue

        if in_code_block:
            code_block_lines += 1
            if code_block_lines <= 2:  # 保留前2行
                result.append(line)
            continue

        # 标题行：保留
        if stripped.startswith('#'):
            result.append(line)
            in_quote = False
            continue

        # 表格行：保留
        if stripped.startswith('|') and '|' in stripped[1:]:
            result.append(line)
            continue

        # 含关键数据的行：保留
        if re.search(r'\d{4}[-/]\d{2}|https?://|\d+\.\d+|[%¥$€]|★|⭐|\d+[千百]万', line):
            result.append(line)
            continue

        # 列表项（带编号或符号）：保留
        if re.match(r'^\s*[-*]\s|^\s*\d+\.\s', line):
            result.append(line)
            continue

        # 空行：保留
        if not stripped:
            result.append('')
            in_quote = False
            continue

        # 引用块：只保留首行
        if stripped.startswith('>'):
            if not in_quote:
                result.append(line)
                in_quote = True
            continue

        in_quote = False

        # 其他行：保留段落第一句
        if stripped and (not result or result[-1].strip() == ''):
            first_sentence = re.split(r'[。！？\.]', stripped)[0]
            if first_sentence and len(first_sentence) > 5:
                result.append(first_sentence + '。')

    return '\n'.join(result)


def compress_minimum(text: str) -> str:
    """Minimum压缩: 仅保留标题+核心结论（1-3句）

    策略:
    1. 保留所有标题行
    2. 保留每个标题下的前1-2句
    3. 保留含"结论/总结/建议"的关键句
    4. 删除所有其他内容
    """
    lines = text.split('\n')
    result = []
    current_heading = None
    sentences_after_heading = 0

    for line in lines:
        stripped = line.strip()

        # 标题行
        if stripped.startswith('#'):
            result.append(line)
            current_heading = stripped
            sentences_after_heading = 0
            continue

        # 关键结论行：始终保留
        if re.search(r'结论|总结|建议|推荐|核心|关键|注意', stripped):
            result.append(stripped)
            continue

        # 标题下的前2句
        if current_heading and sentences_after_heading < 2:
            if stripped and not stripped.startswith('```'):
                sentences_after_heading += 1
                # 截取到第一个句号
                first_sentence = re.split(r'[。！？\.]', stripped)[0]
                if first_sentence and len(first_sentence) > 5:
                    result.append(first_sentence + '。')

    return '\n'.join(result)


def compress_file(filepath: str, level: str = "balanced") -> dict:
    """压缩单个文件，返回统计"""
    path = Path(filepath)
    content = path.read_text(encoding='utf-8')
    original_tokens = estimate_tokens(content)
    compressed = compress(content, level)
    compressed_tokens = estimate_tokens(compressed)

    return {
        "file": str(path),
        "original_tokens": original_tokens,
        "compressed_tokens": compressed_tokens,
        "reduction": f"{(1 - compressed_tokens/original_tokens)*100:.1f}%" if original_tokens > 0 else "0%",
        "compressed_text": compressed,
    }


# === CLI ===
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法:")
        print("  python3 token_budget.py check <file>            # 检查token数")
        print("  python3 token_budget.py compress <file>         # balanced压缩")
        print("  python3 token_budget.py compress <file> --level minimum")
        print("  python3 token_budget.py compress <file> --output <outfile>")
        print("  python3 token_budget.py chunk <file1> <file2>   # 按预算分批")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "check" and len(sys.argv) > 2:
        filepath = sys.argv[2]
        content = Path(filepath).read_text(encoding='utf-8')
        tokens = estimate_tokens(content)
        budget = check_budget([content])
        print(f"文件: {filepath}")
        print(f"Token数: {tokens}")
        print(f"预算: {budget['available']} (模型{8192} - 预留2048)")
        print(f"是否超限: {'是' if budget['over_limit'] else '否'}")
        print(f"利用率: {budget['utilization']}")

    elif cmd == "compress" and len(sys.argv) > 2:
        filepath = sys.argv[2]
        level = "balanced"
        output = None
        i = 3
        while i < len(sys.argv):
            if sys.argv[i] == "--level" and i + 1 < len(sys.argv):
                level = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--output" and i + 1 < len(sys.argv):
                output = sys.argv[i + 1]
                i += 2
            else:
                i += 1

        result = compress_file(filepath, level)
        print(f"文件: {result['file']}")
        print(f"原始: {result['original_tokens']} tokens")
        print(f"压缩: {result['compressed_tokens']} tokens")
        print(f"缩减: {result['reduction']}")

        if output:
            Path(output).write_text(result['compressed_text'], encoding='utf-8')
            print(f"已保存: {output}")
        else:
            print(f"\n--- 压缩结果 ---\n")
            print(result['compressed_text'][:2000])

    elif cmd == "chunk" and len(sys.argv) > 2:
        files = sys.argv[2:]
        texts = []
        for f in files:
            texts.append(Path(f).read_text(encoding='utf-8'))
        chunks = chunk_by_budget(texts)
        print(f"共 {len(files)} 个文件, 分 {len(chunks)} 批:")
        for i, chunk in enumerate(chunks):
            tokens = sum(estimate_tokens(t) for t in chunk)
            print(f"  批次{i+1}: {len(chunk)} 文件, {tokens} tokens")

    else:
        print("未知命令")
        sys.exit(1)
