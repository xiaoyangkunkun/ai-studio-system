#!/bin/bash
# ══════════════════════════════════════════════════
#  AI工作室系统 · 一键部署脚本 v2.0
#  用法: bash deploy.sh
#  前提: Ubuntu 22.04 + root权限
# ══════════════════════════════════════════════════
set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
ok()   { echo -e "${GREEN}  ✅ $1${NC}"; }
warn() { echo -e "${YELLOW}  ⚠️  $1${NC}"; }
fail() { echo -e "${RED}  ❌ $1${NC}"; exit 1; }
step() { echo -e "${CYAN}▶ $1${NC}"; }

echo ""
echo "═══════════════════════════════════════════════"
echo "  AI工作室系统 · 一键部署 v2.0"
echo "═══════════════════════════════════════════════"
echo ""

# ===== 文件完整性检查 =====
echo "🔍 检查产品包完整性..."
MISSING=0
for dir in scripts skills profiles vault; do
    [ -d "$SCRIPT_DIR/$dir" ] || { warn "$dir/ 目录缺失"; MISSING=$((MISSING+1)); }
done
[ -f "$SCRIPT_DIR/config-template.yaml" ] || { warn "config-template.yaml 缺失"; MISSING=$((MISSING+1)); }
[ -f "$SCRIPT_DIR/deploy.sh" ] || { warn "deploy.sh 缺失"; MISSING=$((MISSING+1)); }
if [ $MISSING -gt 0 ]; then
    fail "产品包不完整，请确认下载完整后重试"
fi
ok "产品包完整"

# ===== 预检 =====
if [ -f "$SCRIPT_DIR/precheck.sh" ]; then
    echo "🔍 运行环境预检..."
    bash "$SCRIPT_DIR/precheck.sh"
    echo ""
    read -p "  预检完成，继续部署？(y/n): " CONTINUE
    [ "$CONTINUE" != "y" ] && [ "$CONTINUE" != "Y" ] && echo "已取消" && exit 0
    echo ""
fi

# ===== 交互式配置 =====
echo "📝 配置（直接回车用默认值）"
echo ""
read -p "  API密钥: " API_KEY
[ -z "$API_KEY" ] && fail "API密钥不能为空"
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
DASH_SECRET=$(openssl rand -hex 32)

echo ""
echo "═══════════════════════════════════════════════"
echo "  开始部署..."
echo "═══════════════════════════════════════════════"

HERMES_HOME="$HOME/.hermes"
VAULT_PATH="$HOME/vault"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ===== Step 1: 系统依赖 =====
step "Step 1/9: 安装系统依赖..."
sudo apt-get update -qq 2>/dev/null
sudo apt-get install -y -qq python3 python3-pip python3-venv nodejs npm git curl wget 2>/dev/null
ok "系统依赖已安装"

# ===== Step 2: 安装 Hermes =====
step "Step 2/9: 安装 Hermes Agent..."
if command -v hermes &> /dev/null; then
    ok "Hermes 已安装"
else
    curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
    source ~/.bashrc 2>/dev/null || true
    ok "Hermes 已安装"
fi

# ===== 补充: 如果没有 git，提示用 tar.gz 下载 =====
if ! command -v git &> /dev/null; then
    warn "git 不可用，但已通过 apt 安装"
fi

# ===== Step 3: 创建目录 =====
step "Step 3/9: 创建目录结构..."
mkdir -p "$HERMES_HOME"/{scripts,skills,profiles/{researcher,writer}/{memories,skills}}
mkdir -p "$VAULT_PATH"/{00-Inbox,wiki/{entities,concepts,comparisons,raw},流程,工作室/{员工,项目报告},工作室产出/{方案架构师·知远/调研报告,写作员·墨白},复盘/员工/{方案架构师·知远,写作员·墨白,军师},日志/每日,用量,博客,entities}
ok "目录结构已创建"

# ===== Step 4: 部署脚本 =====
step "Step 4/9: 部署脚本..."
if [ -d "$SCRIPT_DIR/scripts" ]; then
    cp "$SCRIPT_DIR/scripts/"*.py "$HERMES_HOME/scripts/" 2>/dev/null || true
    cp "$SCRIPT_DIR/scripts/"*.sh "$HERMES_HOME/scripts/" 2>/dev/null || true
    chmod +x "$HERMES_HOME/scripts/"*.sh 2>/dev/null || true
    SCRIPT_COUNT=$(ls "$HERMES_HOME/scripts/"*.{py,sh} 2>/dev/null | wc -l)
    ok "$SCRIPT_COUNT 个脚本"
else
    warn "scripts/ 不存在，跳过"
    SCRIPT_COUNT=0
fi

# ===== Step 5: 部署技能 =====
step "Step 5/9: 部署技能..."
SKILL_COUNT=0
for role in public researcher writer; do
    [ -d "$SCRIPT_DIR/skills/$role" ] || continue
    for skill_dir in "$SCRIPT_DIR/skills/$role"/*/; do
        skill_name=$(basename "$skill_dir")
        mkdir -p "$HERMES_HOME/skills/$skill_name"
        cp -r "$skill_dir"* "$HERMES_HOME/skills/$skill_name/" 2>/dev/null || true
        SKILL_COUNT=$((SKILL_COUNT + 1))
    done
done
ok "$SKILL_COUNT 个技能"

# ===== Step 6: 部署 Profile + Vault =====
step "Step 6/9: 部署员工和知识库..."
for profile in researcher writer; do
    [ -f "$SCRIPT_DIR/profiles/$profile/SOUL.md" ] || continue
    mkdir -p "$HERMES_HOME/profiles/$profile"
    cp "$SCRIPT_DIR/profiles/$profile/SOUL.md" "$HERMES_HOME/profiles/$profile/"
    [ ! -f "$HERMES_HOME/profiles/$profile/memories/MEMORY.md" ] && \
        mkdir -p "$HERMES_HOME/profiles/$profile/memories" && \
        echo "# $profile 记忆" > "$HERMES_HOME/profiles/$profile/memories/MEMORY.md"
done
ok "2 个员工 Profile (researcher + writer)"

if [ -d "$SCRIPT_DIR/vault" ]; then
    cp -rn "$SCRIPT_DIR/vault/"* "$VAULT_PATH/" 2>/dev/null || true
    ok "Vault 知识库"
fi

# ===== Step 7: 生成配置 =====
step "Step 7/9: 生成配置文件..."

# .env
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
ok ".env"

# config.yaml
if [ ! -f "$HERMES_HOME/config.yaml" ] && [ -f "$SCRIPT_DIR/config-template.yaml" ]; then
    cp "$SCRIPT_DIR/config-template.yaml" "$HERMES_HOME/config.yaml"
    sed -i "s|{{YOUR_API_KEY}}|$API_KEY|g" "$HERMES_HOME/config.yaml"
    sed -i "s|{{YOUR_BASE_URL}}|$API_URL|g" "$HERMES_HOME/config.yaml"
    sed -i "s|{{YOUR_MODEL}}|$MODEL|g" "$HERMES_HOME/config.yaml"
    sed -i "s|{{DASHBOARD_USER}}|$DASH_USER|g" "$HERMES_HOME/config.yaml"
    sed -i "s|{{DASHBOARD_SECRET}}|$DASH_SECRET|g" "$HERMES_HOME/config.yaml"
    ok "config.yaml"
else
    warn "config.yaml 已存在，跳过"
fi

# ===== Step 8: 创建 Cron 任务 =====
step "Step 8/9: 创建定时任务..."

# 获取用户配置的模型
CRON_MODEL="$MODEL"
CRON_PROVIDER="custom"

if command -v hermes &> /dev/null; then
    # 基础任务（不依赖特定脚本）
    hermes cron create --name "每日晨报" --schedule "0 8 * * *" \
        --model "$CRON_MODEL" --provider "$CRON_PROVIDER" \
        --prompt "你是每日晨报助手。查看天气、昨日用量、待办事项。用中文输出，条目式。天气用 curl wttr.in/${CITY}?format=3 获取。" \
        2>/dev/null && ok "每日晨报" || warn "每日晨报（可能已存在）"

    hermes cron create --name "服务器监控" --schedule "*/30 * * * *" \
        --script "server_watch.sh" --no-agent \
        2>/dev/null && ok "服务器监控" || warn "服务器监控"

    hermes cron create --name "Token用量结算" --schedule "10 0 * * *" \
        --script "token_report.py" --no-agent \
        2>/dev/null && ok "Token用量结算" || warn "Token用量结算"

    hermes cron create --name "Inbox AI分类" --schedule "0 3 * * *" \
        --model "$CRON_MODEL" --provider "$CRON_PROVIDER" \
        --script "classify_inbox.py" \
        2>/dev/null && ok "Inbox AI分类" || warn "Inbox AI分类"

    hermes cron create --name "知识库健康度" --schedule "10 3 * * *" \
        --model "$CRON_MODEL" --provider "$CRON_PROVIDER" \
        --script "knowledge_health_check.sh" \
        2>/dev/null && ok "知识库健康度" || warn "知识库健康度"

    hermes cron create --name "知识库整理" --schedule "30 3 * * *" \
        --model "$CRON_MODEL" --provider "$CRON_PROVIDER" \
        --prompt "运行 fix_frontmatter.py 和 fix_dead_links.py 修复知识库问题。" \
        2>/dev/null && ok "知识库整理" || warn "知识库整理"

    hermes cron create --name "每周备份" --schedule "0 3 * * 0" \
        --script "weekly_backup.sh" --no-agent \
        2>/dev/null && ok "每周备份" || warn "每周备份"

    hermes cron create --name "目录更新" --schedule "30 4 * * *" \
        --script "skills_inventory_wrapper.sh" --no-agent \
        2>/dev/null && ok "目录更新" || warn "目录更新"

    hermes cron create --name "夜间检查" --schedule "30 7 * * *" \
        --script "night_check.py" --no-agent \
        2>/dev/null && ok "夜间检查" || warn "夜间检查"

    hermes cron create --name "习惯体检" --schedule "30 5 * * 6" \
        --model "$CRON_MODEL" --provider "$CRON_PROVIDER" \
        --script "habit_check.sh" \
        2>/dev/null && ok "习惯体检" || warn "习惯体检"

    hermes cron create --name "流程优化" --schedule "30 5 * * 0" \
        --model "$CRON_MODEL" --provider "$CRON_PROVIDER" \
        --script "flow_signal_extract.sh" \
        2>/dev/null && ok "流程优化" || warn "流程优化"

    # 产出目录Watchdog
    hermes cron create --name "产出目录Watchdog" --schedule "*/10 * * * *" \
        --model "$CRON_MODEL" --provider "$CRON_PROVIDER" \
        --script "watchdog_inbox.py" \
        2>/dev/null && ok "产出目录Watchdog" || warn "产出目录Watchdog"

    CRON_COUNT=$(hermes cron list 2>/dev/null | grep -c "✅\|⏸\|❌" || echo 0)
    ok "共 $CRON_COUNT 个定时任务"
else
    warn "hermes 不可用，跳过 cron 创建（稍后手动创建）"
fi

# ===== Step 9: 验证 =====
step "Step 9/9: 验证部署..."
echo ""

ERRORS=0
command -v hermes &> /dev/null && ok "hermes 命令" || { warn "hermes 命令不可用"; ERRORS=$((ERRORS+1)); }
[ -d "$VAULT_PATH" ] && ok "Vault 目录" || { warn "Vault 目录缺失"; ERRORS=$((ERRORS+1)); }
[ -d "$HERMES_HOME/scripts" ] && ok "Scripts 目录" || { warn "Scripts 缺失"; ERRORS=$((ERRORS+1)); }
[ -d "$HERMES_HOME/skills" ] && ok "Skills 目录" || { warn "Skills 缺失"; ERRORS=$((ERRORS+1)); }
[ -f "$HERMES_HOME/.env" ] && ok ".env 配置" || { warn ".env 缺失"; ERRORS=$((ERRORS+1)); }
[ -f "$HERMES_HOME/config.yaml" ] && ok "config.yaml" || { warn "config.yaml 缺失"; ERRORS=$((ERRORS+1)); }
[ -f "$HERMES_HOME/profiles/researcher/SOUL.md" ] && ok "调研员 SOUL" || { warn "调研员缺失"; ERRORS=$((ERRORS+1)); }
[ -f "$HERMES_HOME/profiles/writer/SOUL.md" ] && ok "写作员 SOUL" || { warn "写作员缺失"; ERRORS=$((ERRORS+1)); }

echo ""
echo "═══════════════════════════════════════════════"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}  ✅ 部署完成！全部检查通过${NC}"
else
    echo -e "${YELLOW}  ⚠️  部署完成，$ERRORS 项需注意${NC}"
fi
echo "═══════════════════════════════════════════════"
echo ""
echo "📊 统计: 脚本 $SCRIPT_COUNT 个 | 技能 $SKILL_COUNT 个 | Cron $CRON_COUNT 个"
echo ""
echo "🚀 启动:"
echo "  source ~/.bashrc"
echo "  hermes doctor    # 检查环境"
echo "  hermes           # 启动对话"
echo ""
echo "📚 文档: $SCRIPT_DIR/docs/"
echo ""
