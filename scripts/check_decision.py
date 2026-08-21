#!/usr/bin/env python3
"""决策通道监视:待决策.md 有新问题(比已决策.md 新)时输出其内容触发 agent;否则静默。"""
import os

D = '${VAULT_PATH:-/root/vault}/决策通道'
ask = os.path.join(D, '待决策.md')
ans = os.path.join(D, '已决策.md')

if os.path.exists(ask) and os.path.exists(ans):
    if os.path.getmtime(ask) > os.path.getmtime(ans):
        print(open(ask, encoding='utf-8').read())