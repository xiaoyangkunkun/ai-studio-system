# P0 改造实施记录

## P0-3: 内容哈希去重 (2026-08-18 完成)
- 脚本: `~/.hermes/scripts/hash_dedup.py` (~180行)
- 集成: `classify_inbox.py` 移动前调用 `ingest_gate()`, 移动后调用 `record_ingestion()`
- 原理: SHA256哈希跳过frontmatter, `.hash_log.jsonl` 记录已摄入
- 测试: 395个唯一内容, 465个文件, 发现68组重复
- 借鉴: green-dalii/obsidian-llm-wiki Smart Batch Skip

## P0-1: Smart Fix 一键修复 (2026-08-18 核心框架完成)
- 脚本: `~/.hermes/scripts/smart_fix.py` (~500行)
- 5Phase因果顺序:
  1. frontmatter补全+别名 → 2. 去重 → 3. 死链修复 → 4. 链孤儿 → 5. 扩展stub
- 用法: `python3 smart_fix.py` (dry-run) / `--apply` (执行) / `--phase 1,2` (选择性)
- Dry-run结果: Phase1=389文件, Phase2=56组重复, Phase3=210死链, Phase4=160孤儿, Phase5=6stub
- 待补: Phase 3 语义匹配(需LLM), Phase 5 stub自动扩展(需LLM)
- 借鉴: green-dalii Smart Fix All 因果顺序修复

## P0-2: Token预算/语义压缩 (2026-08-18 完成)
- 脚本: `~/.hermes/scripts/token_budget.py` (~300行)
- 三档压缩: maximum(格式精简) / balanced(保留关键信息,缩减23.6%) / minimum(标题+结论,缩减75.7%)
- Token估算: 字符比例法(中文1.5字/token, 英文0.75词/token), 误差<15%
- 分批: 按文件边界切分, 不跨文件
- 用法: `check <file>` / `compress <file> --level balanced` / `chunk <file1> <file2>`
- 借鉴: ikeniborn/obsidian-ai-wiki bounded processing + semantic compression
