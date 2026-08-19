# Token / Cost Usage Tracking (Hermes 本地用量统计)

> 目标:每日记录 token 用量与费用。2026-08 验证:**不需要任何外部 skill/MCP**,
> Hermes 本地 state.db 就有完整数据 —— 但必须用对表。

## 关键发现:state.db 两个口径

| 表 | 口径 | 特征 |
|---|---|---|
| `sessions` | **增量** | input/output/cache_read/reasoning tokens + estimated_cost_usd,只记"新增内容" |
| `session_model_usage` | **完整 API 口径** | 按 session+model+task 分组,`cache_read_tokens` 含每次请求的完整上下文缓存读,与官方计费一致 |

**用错表会差 ~10 倍**:8/12 当天 `sessions` 合计 ¥0.72,官方账单 ¥7.42;
而 `session_model_usage` 累计缓存读 1.85 亿(两天)≈ 官方两天 2 亿+,估算 ¥7.78 vs 官方两天合计基本吻合。

原因:官方按**每次请求的完整上下文**计费(系统提示+记忆+会话历史每次都从缓存读一遍),
sessions 表只记增量。缓存读是大头(主微信会话 1.45 亿)。

## 验证过的查询

```python
import sqlite3
db = sqlite3.connect('~/.hermes/state.db')
rows = db.execute('''SELECT session_id, model,
    SUM(CAST(api_call_count AS INTEGER)), SUM(CAST(input_tokens AS INTEGER)),
    SUM(CAST(output_tokens AS INTEGER)), SUM(CAST(cache_read_tokens AS INTEGER)),
    SUM(CAST(reasoning_tokens AS INTEGER)), SUM(CAST(estimated_cost_usd AS REAL))
    FROM session_model_usage GROUP BY session_id''').fetchall()
```

注意:`session_model_usage` 的 token 字段可能以字符串存储,必须 `CAST(... AS INTEGER)`。
`agent.log` 只有压缩时的 `rough_tokens`(≈5 条/天),没有按请求的 usage —— 不能按天拆分。
`messages.token_count` 是单条消息的,不是计费口径。

## DeepSeek 官方定价 (deepseek-v4-flash, 2026-08 抓取)

- 输入(缓存命中):¥0.02 / 百万 tokens
- 输入(缓存未命中):¥1 / 百万 tokens
- 输出:¥2 / 百万 tokens
- 定价页:https://api-docs.deepseek.com/zh-cn/quick_start/pricing/
- 8/12 官方账单反算:2.019亿×0.02 + 175万×1 + 79.5万×2 ≈ ¥7.38 ≈ 官方 ¥7.42 ✅
- 注意定价页提示"计划近期整体上调,涨幅较大"

### ⚠️ 8/17 峰谷计费涨价(2026-08-15 确认,8/17 0:00 生效)

V4 Flash / V4 Pro 全部改为峰谷计费,高峰 9:00-12:00 + 14:00-18:00,空闲价为高峰一半:

| 模型 | 旧价输出 | 空闲输出 | 高峰输出 |
|---|---|---|---|
| V4 Flash | ¥2/M | ¥4.5/M | ¥9/M |
| V4 Pro | ¥6/M | ¥13.5/M | ¥27/M |

等量输入+输出任务:空闲时段总成本 = 旧价 2 倍,高峰 = 旧价 4 倍。缓存命中输入 0.02→0.05(V4 Flash)。**应对**:批处理/摘要类任务挪到空闲时段(18:00-次日9:00 + 12:00-14:00);实时交互按高峰价预算;计划迁移主模型(2026-08-15 评估 MiMo 开放平台 platform.xiaomimimo.com,key 未配齐前 DeepSeek 留作 fallback)。此表在下次官方调价后作废,重查 pricing 页。

## 官方用量 zip 包导入(usage_import.py, 2026-08-15 实测)

DeepSeek 控制台可下载**官方日用量 zip**(含 `cost-<日期>.csv` + `amount-<日期>.csv`),比本地估算准——用户手动下载发来,`usage_import.py` 自动分账入库:

```bash
python3 ~/.hermes/scripts/usage_import.py <zip路径>
# 输出:按 api_key_name 拆分(hermes-server 服务器主引擎 / hermes-claude-code 技术员 / hermes-win Windows端)+ 合计
# 写入 vault/用量/ 主表 + 各 key 分表
```

- **脚本只收 zip**(`parse_zip` 内部解压),先解压再传 CSV 会报 `BadZipFile`——传原始 zip 路径
- amount.csv 有 `api_key_name` 字段(分账依据);cost.csv 无 key 字段,脚本按请求数比例分摊
- 每次请求成本粗算:命中输入 ~20.9万 tokens(¥0.0004)+ 未命中 ~2.4k + 输出 ~755——**一次普通对话 ≈ ¥0.004-0.05**,一天全部对话 ¥20-30 量级
- 分账 key 标签在脚本 `KEY_LABEL` dict 中,新 key 自动建目录

## balance API(自动查余额)

```bash
curl -s https://api.deepseek.com/user/balance -H "Authorization: Bearer $DEEPSEEK_API_KEY"
# → {"is_available":true,"balance_infos":[{"currency":"CNY","total_balance":"26.33",...}]}
```

没有按天用量明细的公开 API —— 官网控制台"用量"页才有分模型明细(用户手动查)。
**官方 API 只有 balance;每日费用自动统计靠快照差值法(见下)。**

## 自动统计方案:每日快照差值法

1. 每天 23:59 跑脚本:读取 `session_model_usage` 全部累计值(或按 session 维度)+ balance
2. 存快照到统计文件(如 `~/.hermes/data/token_snapshots.json`:日期 → 累计值 + balance)
3. 当日用量 = 今日累计 - 昨日累计(按 session_id+model+task 逐项差分;新会话自然计入)
4. 当日费用 ≈ 差额 × 官方定价(estimated_cost_usd 已是估算,用快照差值更稳)
5. 可选:余额低于阈值(如 ¥10)提醒充值

## 晚间复盘 / 每日日志:用户格式偏好(2026-08-12 强确认)

- **条目式**:每条一行,严禁大段文字段落(用户明确说"不够有条理性,要一条一条")
- **微信不打勾**:明日计划用普通列表 `- 事项`,绝不用 `- [ ]` checkbox(微信无法打勾)
- **默认写入 + 可修改**:复盘/习惯整理直接写入(Notion + 日志区),推送预览,用户说改才重写 —— 不依赖用户记得确认
- **每日日志六小节**:
  ```
  ## 今日概述      (每行一主题,3-6条)
  ## 见闻与收获    (带图标 🤖AI/🔧工具/🌤️天气,2-5条)
  ## 技能/MCP 动态 (当天新增/导入/发现的技能与MCP数量+名称;无则写"今日无新增")
  ## 健康打卡      (用户随时说的运动/体重/饮食;无则"今日无打卡数据",不编造)
  ## 明日计划      (普通列表,1-4条)
  ## 一句话小结    (💬 当天状态一句话)
  ```
- **健康打卡存储**:用户随时说 → 立即写入当天日志文件 `vault/日志/每日/YYYY-MM-DD.md` 的
  "## 健康打卡"小节(实时可见);晚间复盘**以该文件为准**(不重复从对话提取),防止丢/重
- **日志区防污染**:`vault/日志/`(每日/每周)不参与知识库整理 —— kb_inventory.py 的
  SKIP_DIRS 和知识库整理 cron 都要排除它,像 raw/ 一样只存不读
- Notion 同步:同一复盘双写 Notion 每日日志库(ds 3b9c4892-f916-813d-8a38-000b080899ee)+ 日志区 md
