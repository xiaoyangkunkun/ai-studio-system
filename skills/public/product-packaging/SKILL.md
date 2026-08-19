---
name: product-packaging
description: "Package internal AI systems as sellable product kits."
version: 1.0.0
tags: [product, packaging]
---

# AI 系统产品化打包

## When to Use
- 把内部系统打包成可售卖的产品
- 把团队配置/流程/技能抽象成通用模板
- 创建一键部署脚本

## 核心原则

**抽取 = 原样复刻 + 去私有 + 路径参数化**

不是重新设计，是复制实际系统，去掉私有内容，让路径可配置。

## ⚠️ 关键教训（2026-08-18/19 实战）

### 原则：原样复刻，不重新设计

用户要的是原样复刻：
- 目录结构原样不动（`工作室/`、`流程/`、`产出/`...）
- 文件名原样不动（`组织架构.md`、`SOUL.md`、`每日流程.md`...）
- 读写机制原样不动（脚本、Cron、Skills 分层）
- 只改内容：去掉私有，路径参数化

**错误做法**：设计 M1-M8 模块、创建新目录结构、重写文件
**正确做法**：`cp -r vault/ 产品包/vault/` → 批量替换私有关键词 → 参数化路径

### 何时"推倒重来"vs 修补旧模板

如果旧产品模板审计出 **3类以上问题**（如：重复脚本、个人残留、config缺失、目录不全、install.sh bug），修补成本 > 重建成本，应推倒重来。

判断信号：
- `grep -rl "私有关键词" 产品模板/ | wc -l` > 10 → 残留太多
- 旧模板文件数 < 实际系统文件数的 50% → 严重缺失
- install.sh 有 P0 bug 且用户不想修 → 重建更快

推倒重来时，先做**结构化审计**（见下方），再出方案给用户确认。

### 结构化审计方法（推倒重来前必做）

分5个维度独立审计，每个维度一条命令：

| 维度 | 审计命令 | 对比目标 |
|------|---------|---------|
| 脚本 | `ls scripts/ \| wc -l` | 实际 scripts/ 数量 |
| 技能 | `find skills/ -name SKILL.md \| wc -l` | 实际 skills/ 数量 |
| 员工 | `ls profiles/*/SOUL.md` | SOUL 行数和内容完整度 |
| 配置 | `wc -l config.yaml` | 实际 config 段落数 |
| vault | `find vault/ -maxdepth 2 -type d \| sort` | 目录完整性 |

审计结果用表格对比，让用户一目了然差距在哪。然后再出分Phase方案。

### 去私有要彻底

批量替换后必须验证：`grep -rl "私有关键词" vault/ | wc -l` 必须 = 0
常见遗漏：wiki/analytics JSON、.canvas 文件、复盘目录里的旧文件

### SOUL 文件不能简化

产品包的 SOUL 不能是精简版，必须包含：
- 派活机制（派单前4问、材料传递规则）
- 来源标注规范
- 复盘模板
- 产出目录规范
我们实战中调研员 SOUL 从 43 行补到 80+ 行才够用

## 打包清单

### 1. 目录结构（原样复制）
- 复制实际 vault 目录结构
- 保留所有文件名
- 清空具体产出文件（让用户自己积累）
- 保留目录结构

### 2. 脚本（路径参数化）
- 复制实际脚本
- 硬编码路径改为环境变量读取
- 验证 import 通过

### 3. SOUL 文件（去私有）
- 替换私有称呼（老大→用户、狗头军师→主AI助手）
- 替换私有员工名（知远→调研员、墨白→写作员）
- 删除私有 ID/地址
- 保留通用铁律和工作流程

### 4. 技能包（分层）
```
skills/public/        # 公共技能
skills/researcher/    # 调研员专属
skills/writer/        # 写作员专属
```

### 5. 用户画像（通用版）
- 保留通用习惯
- 留自定义入口
- 去个人偏好

### 6. install.sh（一键部署）
6步：安装Hermes → 配LLM → 部署vault → 部署脚本 → 创建profile+SOUL+skills → 配cron

## 去私有检查清单

### 批量替换规则
```
老大→用户、狗头军师→主AI助手
知远→调研员、墨白→写作员、小端→执行员
[伴侣名称]→伴侣（或直接删除）
```

### 必须删除的
- ID/chat_id/UUID/Notion数据库ID
- IP地址/域名
- 私有项目名（[伴侣名称]等）
- 具体产出文件（用户自己积累）
- wiki/analytics JSON（自动生成）
- .canvas 文件（含私有引用）
- 复盘目录里的旧文件

### 必须保留的
- 目录结构（原样）
- 文件名（原样）
- 流程文档（通用化后保留）
- 铁律（保留核心规则）
- Skills 分层结构（public/researcher/writer）

## 验证

1. `bash -n install.sh` 语法通过
2. `python3 -c "import script_name"` 各脚本通过
3. `grep -rl "老大\|狗头军师\|知远\|墨白\|若雪" vault/ | wc -l` = 0
4. `grep -c "OBSIDIAN_VAULT_PATH" scripts/*.py` 每个脚本都有环境变量读取
