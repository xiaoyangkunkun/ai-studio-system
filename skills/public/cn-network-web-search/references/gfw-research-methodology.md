---
title: "GFW Research Methodology — Adaptive Patterns"
created: 2026-08-20
updated: 2026-08-20
type: note
---
# GFW Research Methodology — Adaptive Patterns

When web_search on a CN server returns garbage (generic CSDN/GitHub homepage links instead of relevant results), the search backend is working but the results are filtered/unhelpful. This is different from the server being unable to reach search engines.

## The Problem
- `web_search` returns results, but they're all generic homepage links
- `site:github.com` queries return only github.com itself
- Chinese search engines (so.com) work but return irrelevant results for English queries
- Reddit/English sources are unreachable or return only homepage

## Adaptive Strategy (proven 2026-08)

### 1. Extract known authoritative URLs directly
Instead of searching, go straight to known good sources:
- Official documentation sites (e.g., SillyTavern docs, Hermes docs)
- Rentry.co guides (character design, prompt engineering)
- GitHub README files for known projects

```python
web_extract(["https://known-good-url.com/page"], char_limit=8000)
```

### 2. Use broader search queries
- Drop `site:` operators (GFW distorts them)
- Use natural language queries instead of boolean
- Try Chinese keywords for Chinese content
- Try English keywords for English content

### 3. Multi-language parallel search
Run searches in both Chinese and English simultaneously:
- Chinese: "AI女友 提示词 人设" → find CSDN/知乎 articles
- English: "AI companion prompt template SOUL" → find GitHub/Rentry guides

### 4. Search description mining
Even when search results are garbage, sometimes the `description` field contains useful snippets. Always check descriptions.

### 5. Cascading extract
When search fails, extract from a cascade of known sources:
1. Official docs (domain-specific)
2. Rentry.co (community guides)
3. GitHub repos (code examples)
4. CSDN/知乎 (Chinese community)

## Example: AI Companion Research (2026-08-16)
Search failed for all queries. Adapted by:
1. Extracting SillyTavern docs directly → got character card format
2. Extracting rentry.co/alichat → got Ali:Chat style guide
3. Extracting rentry.co/kingbri-chara-guide → got PLists format
4. Extracting Hermes SOUL.md docs → got official persona format
5. Compiled all findings into comprehensive report

## Key Lesson
On CN servers, **direct extraction of known URLs > search**. Maintain a mental catalog of authoritative sources per domain.
