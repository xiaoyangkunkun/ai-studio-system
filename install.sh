#!/bin/bash
# AI工作室系统 安装脚本 v1.0
# 一键部署 Hermes Agent + Obsidian + Cron 工作室体系
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
VAULT_PATH="${VAULT_PATH:-$HOME/vault}"

echo "═══════════════════════════════════════════════"
echo "  AI工作室系统 安装脚本 v1.0"
echo "═══════════════════════════════════════════════"
echo ""
echo "安装目录: $HERMES_HOME"
echo "Vault路径: $VAULT_PATH"
echo ""

# ========== Step 1: 检查依赖 ==========
echo "▶ Step 1/6: 检查依赖..."

if ! command -v hermes &> /dev/null; then
    echo "❌ 未安装 Hermes Agent"
    echo "   请先安装: curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash"
    exit 1
fi
echo "  ✅ Hermes Agent 已安装"

if ! command -v python3 &> /dev/null; then
    echo "❌ 未安装 Python3"
    exit 1
fi
echo "  ✅ Python3 已安装"

if ! command -v node &> /dev/null; then
    echo "⚠️  未安装 Node.js（部分功能需要）"
fi

# ========== Step 2: 创建目录结构 ==========
echo ""
echo "▶ Step 2/6: 创建目录结构..."

mkdir -p "$HERMES_HOME"/{scripts,skills,profiles/{researcher,writer}/{memories,skills}}
mkdir -p "$VAULT_PATH"/{00-Inbox,wiki/{entities,concepts,comparisons,raw},流程,工作室/{员工,项目报告},工作室产出/{方案架构师·知远/调研报告,写作员·墨白},复盘/员工/{方案架构师·知远,写作员·墨白,军师},日志/每日,用量,博客,entities}

echo "  ✅ 目录结构已创建"

# ========== Step 3: 复制脚本 ==========
echo ""
echo "▶ Step 3/6: 部署脚本..."

if [ -d "$SCRIPT_DIR/scripts" ]; then
    cp "$SCRIPT_DIR/scripts/"*.py "$HERMES_HOME/scripts/" 2>/dev/null || true
    cp "$SCRIPT_DIR/scripts/"*.sh "$HERMES_HOME/scripts/" 2>/dev/null || true
    chmod +x "$HERMES_HOME/scripts/"*.sh 2>/dev/null || true
    echo "  ✅ $(ls "$HERMES_HOME/scripts/"*.{py,sh} 2>/dev/null | wc -l) 个脚本已部署"
else
    echo "  ⚠️  scripts/ 目录不存在，跳过"
fi

# ========== Step 4: 复制技能 ==========
echo ""
echo "▶ Step 4/6: 部署技能..."

SKILL_COUNT=0
for role in public researcher writer; do
    if [ -d "$SCRIPT_DIR/skills/$role" ]; then
        for skill_dir in "$SCRIPT_DIR/skills/$role"/*/; do
            skill_name=$(basename "$skill_dir")
            mkdir -p "$HERMES_HOME/skills/$skill_name"
            cp -r "$skill_dir"* "$HERMES_HOME/skills/$skill_name/" 2>/dev/null || true
            SKILL_COUNT=$((SKILL_COUNT + 1))
        done
    fi
done
echo "  ✅ $SKILL_COUNT 个技能已部署"

# ========== Step 5: 复制Profile和Vault ==========
echo ""
echo "▶ Step 5/6: 部署Profile和Vault..."

# Profiles
for profile in researcher writer; do
    if [ -f "$SCRIPT_DIR/profiles/$profile/SOUL.md" ]; then
        mkdir -p "$HERMES_HOME/profiles/$profile"
        cp "$SCRIPT_DIR/profiles/$profile/SOUL.md" "$HERMES_HOME/profiles/$profile/"
        [ ! -f "$HERMES_HOME/profiles/$profile/memories/MEMORY.md" ] && \
            mkdir -p "$HERMES_HOME/profiles/$profile/memories" && \
            echo "# $profile 记忆" > "$HERMES_HOME/profiles/$profile/memories/MEMORY.md"
        echo "  ✅ $profile profile 已部署"
    fi
done

# Vault文档（不覆盖已有文件）
if [ -d "$SCRIPT_DIR/vault" ]; then
    cp -rn "$SCRIPT_DIR/vault/"* "$VAULT_PATH/" 2>/dev/null || true
    echo "  ✅ Vault文档已部署（不覆盖已有文件）"
fi

# ========== Step 6: 生成配置 ==========
echo ""
echo "▶ Step 6/6: 生成配置..."

if [ ! -f "$HERMES_HOME/config.yaml" ]; then
    if [ -f "$SCRIPT_DIR/config-template.yaml" ]; then
        cp "$SCRIPT_DIR/config-template.yaml" "$HERMES_HOME/config.yaml"
        echo "  ⚠️  已生成 config.yaml，请编辑填入你的 API Key 等配置"
    fi
else
    echo "  ℹ️  config.yaml 已存在，跳过（如需重置请手动删除后重新运行）"
fi

if [ ! -f "$HERMES_HOME/.env" ]; then
    if [ -f "$SCRIPT_DIR/env-template" ]; then
        cp "$SCRIPT_DIR/env-template" "$HERMES_HOME/.env"
        echo "  ⚠️  已生成 .env，请编辑填入你的环境变量"
    fi
else
    echo "  ℹ️  .env 已存在，跳过"
fi

# ========== 完成 ==========
echo ""
echo "═══════════════════════════════════════════════"
echo "  ✅ 安装完成！"
echo "═══════════════════════════════════════════════"
echo ""
echo "下一步："
echo "  1. 编辑 $HERMES_HOME/.env 填入 API Key"
echo "  2. 编辑 $HERMES_HOME/config.yaml 完善配置"
echo "  3. 运行 hermes doctor 检查环境"
echo "  4. 参考 cron/README.md 配置定时任务"
echo "  5. 运行 hermes 开始使用"
echo ""
echo "文档: docs/使用手册.md"
echo ""
