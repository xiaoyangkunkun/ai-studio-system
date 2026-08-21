---
title: "AI 工作室系统 - 产品包参考"
created: 2026-08-20
updated: 2026-08-20
type: note
---
# AI 工作室系统 - 产品包参考

## 实际系统规模（2026-08-19 审计）

| 维度 | 实际系统 | 旧产品模板 | 差距 |
|------|---------|-----------|------|
| scripts | 58个 | 41个 | 缺17个 |
| skills | 139个 | 13个 | 严重不足 |
| 员工profiles | 3个（researcher/writer/companion） | SOUL散放vault | 结构不对 |
| cron任务 | 25个启用 | 配置文档（未实际创建） | 无法复制 |
| config.yaml | ~80行（含tts/stt/gateway/delegation） | 17行极简版 | 差距巨大 |
| vault目录 | 完整（wiki/日志/复盘/用量/工作室产出等） | 有但缺子目录 | 需补全 |
| 流程文档 | 16个（含从零搭建手册4篇） | 8个 | 缺少搭建类 |
| 工作室文档 | 11个（含项目报告3篇） | 3个（组织/铁律/流程总览） | 缺少员工档案和报告 |

## 产品包目标结构（v2 推倒重来版）

```
ai-studio-system/
├── README.md                 # 快速开始（15分钟上手）
├── install.sh               # 一键部署（修复VAULT_PATH bug）
├── 使用手册.md              # 完整文档
├── config-template.yaml     # 完整配置模板（从实际config提取，~80行）
├── .env.example             # API key 模板
│
├── scripts/                 # 精选脚本（去个人化，路径参数化）
├── skills/                  # 精选技能包（按角色分）
│   ├── public/              # 通用技能
│   ├── researcher/          # 调研员专属
│   └── writer/              # 写作员专属
│
├── profiles/                # 员工模板
│   ├── researcher/
│   │   ├── SOUL.md          # 完整版（含派活机制/来源标注/复盘模板）
│   │   └── config.yaml
│   └── writer/
│       ├── SOUL.md
│       └── config.yaml
│
├── vault-template/          # vault 骨架（原样复制，清空产出）
│   ├── 00-Inbox/
│   ├── entities/
│   ├── wiki/ (raw/entities/concepts/comparisons)
│   ├── 日志/ (每日/周)
│   ├── 复盘/ (员工/)
│   ├── 用量/
│   ├── 工作室/ (员工/项目报告)
│   ├── 流程/
│   └── Dashboard.md
│
└── docs/                    # 文档（从 vault/流程/ 和 vault/工作室/ 提取）
    ├── 组织架构.md
    ├── 工作室铁律.md
    ├── 流程总览.md
    ├── 每日流程.md
    ├── 知识管理章程.md
    └── 从零搭建手册/
```

## install.sh 6步

1. 安装 Hermes Agent
2. 配置 LLM + config.yaml（用户输入自己的 API Key）
3. 部署 Vault（原样复制 + 创建缺失子目录）
4. 部署脚本（路径参数化，验证 import）
5. 创建 researcher + writer profile + SOUL + skills
6. 创建 Cron 任务

## 关键教训

- **不要重新设计**，原样复刻+去私有
- SOUL 不能精简，必须包含派活机制/来源标注/复盘模板
- install.sh 必须生成 config.yaml，否则 Hermes 无法启动
- 私有数据清理要彻底（grep验证=0残留）
- 旧模板审计出3类以上问题时，推倒重来比修补快
- 推倒重来前先做5维度结构化审计（scripts/skills/profiles/config/vault）
