---
name: systematic-debugging
description: "Debug errors: understand, research, fix, document."
---

# Systematic Debugging

## When to Use
- API returns unexpected errors (4xx/5xx)
- Feature works in docs but fails in practice
- Same error after 2+ fix attempts

## 4 Phases

### Phase 1: Understand (2 min max)
- Read the FULL error message (not just status code)
- Check: is this a known issue? (search docs/GitHub issues)
- What did the error say? Parse it literally.

### Phase 2: Research (delegate to调研员)
- If Phase 1 doesn't reveal the fix, **dispatch知远**
- Provide: error message + what you tried + what you need to know
- Wait for research results before trying more fixes

### Phase 3: Fix (with research results)
- Apply the researched solution
- Verify with a minimal test case
- If still fails → go back to Phase 2 with new info

### Phase 4: Document
- Write the fix to vault/流程/ or a skill
- Include: error → root cause → solution → prevention

## Anti-Patterns (don't do these)
- ❌ Trying 5+ variations without understanding the error
- ❌ Guessing parameter names ("maybe it's format? voice? audio?")
- ❌ Ignoring error messages and trying random things
- ❌ Repeating the same fix with minor variations

## The Golden Rule
**If you don't understand WHY it failed, you can't fix it. Research first, fix second.**
