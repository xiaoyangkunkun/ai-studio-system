---
title: "AI工作室系统"
created: 2026-08-20
updated: 2026-08-21
type: note
---
# AI工作室系统

> AI 驱动的全自动数字员工运营体系。基于 Hermes Agent + Obsidian + Cron，开箱即用。

## 快速开始（5分钟）

```bash
# 1. 安装 git（如果还没装）
sudo apt install -y git

# 2. 克隆产品包
git clone https://github.com/xiaoyangkunkun/ai-studio-system.git
cd ai-studio-system

# 3. 一键部署（交互式，填API密钥等）
bash deploy.sh

# 4. 启动
hermes
```

**没有 git？** 下载压缩包也能用：
```bash
# 下载并解压
curl -sL https://github.com/xiaoyangkunkun/ai-studio-system/archive/refs/heads/main.tar.gz | tar xz
cd ai-studio-system-main
bash deploy.sh
```

deploy.sh 会自动：
- 安装系统依赖和 Hermes Agent
- 部署 58 个脚本 + 35 个技能 + 2 个员工
- 创建 12 个定时任务（带模型配置，避免 drift）
- 生成配置文件

## 包含什么

| 模块 | 内容 | 数量 |
|------|------|------|
| 📜 脚本 | 知识库维护、Token统计、备份运维、习惯管理、AI调用、Notion集成 | 58个 |
| 🎯 技能 | 按角色精选（公共/调研员/写作员） | 35个 |
| 👥 员工 | 调研员 + 写作员（含SOUL人设） | 2个 |
| ⏰ 定时任务 | 晨报、复盘、知识库整理、监控等 | 12个 |
| 📚 文档 | 流程、铁律、架构、使用手册 | 108个 |
| 🗂️ Vault | Obsidian知识库骨架（含wiki） | 完整结构 |

## 系统架构

```
┌─────────────────────────────────────────────────┐
│              AI 工作室系统 v2.2                  │
├─────────────────────────────────────────────────┤
│  ★ 核心层（开箱即用）                           │
│  ├── 工作室架构（组织架构+铁律+流程）           │
│  ├── 知识管理系统（vault+脚本+wiki）            │
│  └── 员工与派活（调研员+写作员+派活机制）       │
├─────────────────────────────────────────────────┤
│  ☆ 运营层（推荐启用）                           │
│  ├── 自动化Cron（12个定时任务）                 │
│  ├── 数据保障（备份+同步）                      │
│  └── 成本控制（Token用量追踪）                  │
├─────────────────────────────────────────────────┤
│  ○ 进阶层（按需）                               │
│  ├── 自我改进（复盘+体检+经验沉淀）             │
│  ├── 内容发布（博客+社交媒体）                  │
│  └── 语音能力（TTS+STT）                        │
└─────────────────────────────────────────────────┘
```

## 员工角色

| 角色 | 职责 | 技能数 |
|------|------|--------|
| 🔍 调研员（知远） | 深度调研、竞品分析、技术验证 | 6个专属 |
| ✍️ 写作员（墨白） | 文章撰写、内容创作、去AI腔 | 6个专属 |
| 🎯 军师（主AI） | 任务调度、团队管理、决策 | 公共技能18个 |

## 配置说明

### 环境变量（.env）

复制 `env-template` 为 `.env`，填入以下配置：

```bash
# 必填
YOUR_API_KEY=your-api-key
YOUR_BASE_URL=https://api.example.com/v1
YOUR_MODEL=your-model-name

# Dashboard
DASHBOARD_USER=admin
DASHBOARD_PASSWORD_HASH=  # 用 hermes doctor 生成
DASHBOARD_SECRET=         # openssl rand -hex 32

# 可选
CITY=Fuzhou
WEIXIN_CHAT_ID=your-chat-id
NOTION_TOKEN=ntn_your_token
```

### 平台配置

在 `config-template.yaml` 中取消注释你需要的平台：

```yaml
# 微信
platforms:
  weixin:
    enabled: true
    extra:
      account_id: "your-account-id"
      token: "your-token"

# QQ Bot
platforms:
  qqbot:
    enabled: true
    extra:
      app_id: "your-app-id"
      client_secret: "your-secret"
```

## 定时任务

| 任务 | 时间 | 说明 |
|------|------|------|
| 每日晨报 | 8:00 | 天气、用量、待办、团队产出 |
| 服务器监控 | */30min | CPU/内存/磁盘 |
| Token用量结算 | 0:10 | 每日用量统计 |
| Inbox AI分类 | 3:00 | 自动分类笔记 |
| 知识库健康度 | 3:10 | 死链、frontmatter检查 |
| 知识库整理 | 3:30 | 修复问题 |
| 每周备份 | 周日3:00 | 全量备份 |
| 目录更新 | 4:30 | 技能清单更新 |
| 夜间检查 | 7:30 | 任务执行情况 |
| 习惯体检 | 周六5:30 | 习惯执行情况 |
| 流程优化 | 周日5:30 | 流程改进建议 |
| 产出Watchdog | */10min | 监听产出目录 |

## 文档

- [使用手册](docs/使用手册.md) — 完整使用指南
- [环境依赖](docs/环境依赖.md) — 系统要求和依赖说明
- [从零部署](docs/使用指南-从零部署.md) — 详细部署步骤
- [Cron配置](cron/README.md) — 定时任务配置
- [组织架构](vault/工作室/组织架构.md) — 团队角色定义
- [工作室铁律](vault/工作室/工作室铁律.md) — 通用规则

## 更新日志

### v2.2 (2026-08-21)
- 修复：Cron任务模型配置（避免model drift）
- 新增：32个脚本（AI调用、Notion集成、知识库管理等）
- 改进：脚本路径参数化（支持自定义路径）
- 改进：配置模板补全（Gateway/platforms/.env）
- 文档：更新README，添加配置说明

### v2.1 (2026-08-19)
- 新增：precheck.sh 环境预检
- 改进：deploy.sh 产品包完整性检查

### v2.0 (2026-08-19)
- 合并 install+deploy
- Cron自动创建
- 完整验证

### v1.0 (2026-08-18)
- 初始版本

## 许可

MIT License
