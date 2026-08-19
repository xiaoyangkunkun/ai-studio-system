#!/bin/bash
# ══════════════════════════════════════════════════
#  AI工作室系统 · 一键部署脚本
#  用法: bash deploy.sh
#  前提: Ubuntu 22.04 + root权限
# ══════════════════════════════════════════════════
set -e

# ===== 颜色 =====
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "${GREEN}  ✅ $1${NC}"; }
warn() { echo -e "${YELLOW}  ⚠️  $1${NC}"; }
fail() { echo -e "${RED}  ❌ $1${NC}"; exit 1; }

echo ""
echo "═══════════════════════════════════════════════"
echo "  AI工作室系统 · 一键部署"
echo "═══════════════════════════════════════════════"
echo ""

# ===== 交互式配置 =====
echo "📝 开始配置（直接回车用默认值）"
echo ""

read -p "  API密钥: " API_KEY
read -p "  API地址 [https://api.openai.com/v1]: " API_URL
API_URL="${API_URL:-https://api.openai.com/v1}"
read -p "  模型名称 [gpt-4o]: " MODEL
MODEL="${MODEL:-gpt-4o}"
read -p "  城市 [Fuzhou]: " CITY
CITY="${CITY:-Fuzhou}"
read -p "  微信Chat ID（可选，回车跳过）: " WEIXIN_ID
read -p "  Dashboard用户名 [admin]: " DASH_USER
DASH_USER="${DASH_USER:-admin}"
read -s -p "  Dashboard密码: " DASH_PASS
echo ""

# 生成随机secret
DASH_SECRET=$(openssl rand -hex 32)
# 生成密码哈希（简单版，实际用hermes doctor生成更好）
DASH_HASH=""

echo ""
echo "═══════════════════════════════════════════════"
echo "  开始部署..."
echo "═══════════════════════════════════════════════"
echo ""

# ===== Step 1: 系统依赖 =====
echo "▶ Step 1/8: 安装系统依赖..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-pip python3-venv nodejs npm git curl wget >/dev/null 2>&1
ok "系统依赖已安装"

# ===== Step 2: 安装 Hermes =====
echo ""
echo "▶ Step 2/8: 安装 Hermes Agent..."
if command -v hermes &> /dev/null; then
    ok "Hermes 已安装 ($(hermes --version 2>/dev/null || echo 'unknown'))"
else
    curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
    source ~/.bashrc 2>/dev/null || true
    ok "Hermes 已安装"
fi

# ===== Step 3: 创建目录结构 =====
echo ""
echo "▶ Step 3/8: 创建目录结构..."

HERMES_HOME="$HOME/.hermes"
VAULT_PATH="$HOME/vault"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$HERMES_HOME"/{scripts,skills,profiles/{researcher,writer}/{memories,skills}}
mkdir -p "$VAULT_PATH"/{00-Inbox,wiki/{entities,concepts,comparisons,raw},流程,工作室/{员工,项目报告},工作室产出/{方案架构师·知远/调研报告,写作员·墨白},复盘/员工/{方案架构师·知远,写作员·墨白,军师},日志/每日,用量,博客,entities}

ok "目录结构已创建"

# ===== Step 4: 部署脚本 =====
echo ""
echo "▶ Step 4/8: 部署脚本..."

if [ -d "$SCRIPT_DIR/scripts" ]; then
    cp "$SCRIPT_DIR/scripts/"*.py "$HERMES_HOME/scripts/" 2>/dev/null || true
    cp "$SCRIPT_DIR/scripts/"*.sh "$HERMES_HOME/scripts/" 2>/dev/null || true
    chmod +x "$HERMES_HOME/scripts/"*.sh 2>/dev/null || true
    SCRIPT_COUNT=$(ls "$HERMES_HOME/scripts/"*.{py,sh} 2>/dev/null | wc -l)
    ok "$SCRIPT_COUNT 个脚本已部署"
else
    warn "scripts/ 目录不存在，跳过"
fi

# ===== Step 5: 部署技能 =====
echo ""
echo "▶ Step 5/8: 部署技能..."

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
ok "$SKILL_COUNT 个技能已部署"

# ===== Step 6: 部署 Profile 和 Vault =====
echo ""
echo "▶ Step 6/8: 部署 Profile 和 Vault..."

for profile in researcher writer; do
    if [ -f "$SCRIPT_DIR/profiles/$profile/SOUL.md" ]; then
        mkdir -p "$HERMES_HOME/profiles/$profile"
        cp "$SCRIPT_DIR/profiles/$profile/SOUL.md" "$HERMES_HOME/profiles/$profile/"
        [ ! -f "$HERMES_HOME/profiles/$profile/memories/MEMORY.md" ] && \
            mkdir -p "$HERMES_HOME/profiles/$profile/memories" && \
            echo "# $profile 记忆" > "$HERMES_HOME/profiles/$profile/memories/MEMORY.md"
        ok "$profile profile 已部署"
    fi
done

if [ -d "$SCRIPT_DIR/vault" ]; then
    cp -rn "$SCRIPT_DIR/vault/"* "$VAULT_PATH/" 2>/dev/null || true
    ok "Vault 文档已部署"
fi

# ===== Step 7: 生成配置 =====
echo ""
echo "▶ Step 7/8: 生成配置..."

# 生成 .env
cat > "$HERMES_HOME/.env" << ENVEOF
# AI工作室系统 环境变量
YOUR_API_KEY=$API_KEY
YOUR_BASE_URL=$API_URL
YOUR_MODEL=$MODEL
WEIXIN_CHAT_ID=$WEIXIN_ID
CITY=$CITY
DASHBOARD_USER=$DASH_USER
DASHBOARD_SECRET=$DASH_SECRET
ENVEOF
ok ".env 已生成"

# 生成 config.yaml（如果不存在）
if [ ! -f "$HERMES_HOME/config.yaml" ]; then
    if [ -f "$SCRIPT_DIR/config-template.yaml" ]; then
        cp "$SCRIPT_DIR/config-template.yaml" "$HERMES_HOME/config.yaml"
        # 替换配置值
        sed -i "s|{{YOUR_API_KEY}}|$API_KEY|g" "$HERMES_HOME/config.yaml"
        sed -i "s|{{YOUR_BASE_URL}}|$API_URL|g" "$HERMES_HOME/config.yaml"
        sed -i "s|{{YOUR_MODEL}}|$MODEL|g" "$HERMES_HOME/config.yaml"
        sed -i "s|{{DASHBOARD_USER}}|$DASH_USER|g" "$HERMES_HOME/config.yaml"
        sed -i "s|{{DASHBOARD_SECRET}}|$DASH_SECRET|g" "$HERMES_HOME/config.yaml"
        ok "config.yaml 已生成并配置"
    fi
else
    warn "config.yaml 已存在，跳过"
fi

# ===== Step 8: 验证 =====
echo ""
echo "▶ Step 8/8: 验证..."

# 检查 hermes
if command -v hermes &> /dev/null; then
    ok "hermes 命令可用"
else
    warn "hermes 命令不可用，可能需要 source ~/.bashrc"
fi

# 检查目录
[ -d "$VAULT_PATH" ] && ok "Vault 目录存在" || warn "Vault 目录缺失"
[ -d "$HERMES_HOME/scripts" ] && ok "Scripts 目录存在" || warn "Scripts 目录缺失"
[ -d "$HERMES_HOME/skills" ] && ok "Skills 目录存在" || warn "Skills 目录缺失"

# 检查配置
[ -f "$HERMES_HOME/.env" ] && ok ".env 已配置" || warn ".env 缺失"
[ -f "$HERMES_HOME/config.yaml" ] && ok "config.yaml 已配置" || warn "config.yaml 缺失"

# ===== 完成 =====
echo ""
echo "═══════════════════════════════════════════════"
echo -e "${GREEN}  ✅ 部署完成！${NC}"
echo "═══════════════════════════════════════════════"
echo ""
echo "📊 部署统计:"
echo "  脚本: $SCRIPT_COUNT 个"
echo "  技能: $SKILL_COUNT 个"
echo "  Profile: 2 个 (researcher + writer)"
echo "  Vault: $VAULT_PATH"
echo ""
echo "🚀 下一步:"
echo "  1. 运行 hermes doctor 检查环境"
echo "  2. 运行 hermes 启动"
echo "  3. 输入 '你好' 测试"
echo "  4. hermes -p researcher -q '测试' 测试派活"
echo ""
echo "📚 文档:"
echo "  使用手册: $SCRIPT_DIR/docs/使用手册.md"
echo "  Cron配置: $SCRIPT_DIR/cron/README.md"
echo ""
