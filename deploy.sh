#!/bin/bash
# ══════════════════════════════════════════════════
#  AI工作室系统 · 一键部署脚本 v3.0
#  用法: bash deploy.sh [--auto] [--env 文件]
#  前提: Ubuntu 22.04 + root权限
# ══════════════════════════════════════════════════
set -e

# ===== 阶段0: 初始化 =====
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
ok()   { echo -e "${GREEN}  ✅ $1${NC}"; }
warn() { echo -e "${YELLOW}  ⚠️  $1${NC}"; }
fail() { echo -e "${RED}  ❌ $1${NC}"; exit 1; }
step() { echo -e "${CYAN}▶ $1${NC}"; }

# 解析命令行参数
AUTO_MODE=0
ENV_FILE=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --auto) AUTO_MODE=1; shift ;;
        --env) ENV_FILE="$2"; shift 2 ;;
        *) shift ;;
    esac
done

# 加载配置（优先级：环境变量 > --env文件 > 交互输入）
load_config() {
    local env_file="${1:-}"
    [ -n "$env_file" ] && [ -f "$env_file" ] && source "$env_file"

    API_KEY="${API_KEY:-${YOUR_API_KEY:-}}"
    API_URL="${API_URL:-${YOUR_BASE_URL:-https://api.openai.com/v1}}"
    MODEL="${MODEL:-${YOUR_MODEL:-gpt-4o}}"
    CITY="${CITY:-Fuzhou}"
    WEIXIN_ID="${WEIXIN_ID:-${WEIXIN_CHAT_ID:-}}"
    DASH_USER="${DASH_USER:-${DASHBOARD_USER:-admin}}"
    DASH_PASS="${DASH_PASS:-}"
    PROXY="${PROXY:-${https_proxy:-${HTTPS_PROXY:-}}}"
}

# 检测代理
detect_proxy() {
    if [ -n "$PROXY" ]; then
        ok "代理已配置: $PROXY"
        return 0
    fi
    if curl -s --max-time 5 https://github.com > /dev/null 2>&1; then
        ok "无需代理即可访问外网"
        return 0
    fi
    warn "未配置代理且外网不可达"
    echo "  建议: export https_proxy=http://127.0.0.1:7890"
    return 1
}

echo ""
echo "═══════════════════════════════════════════════"
echo "  AI工作室系统 · 一键部署 v3.0"
echo "═══════════════════════════════════════════════"
echo ""

# ===== 阶段1: 预检 =====
step "阶段1/7: 环境预检"

# 1.1 产品包完整性
echo "  检查产品包完整性..."
MISSING=0
for dir in scripts skills profiles vault; do
    [ -d "$SCRIPT_DIR/$dir" ] || { warn "$dir/ 目录缺失"; MISSING=$((MISSING+1)); }
done
[ -f "$SCRIPT_DIR/config-template.yaml" ] || { warn "config-template.yaml 缺失"; MISSING=$((MISSING+1)); }
[ -f "$SCRIPT_DIR/env-template" ] || { warn "env-template 缺失"; MISSING=$((MISSING+1)); }
[ $MISSING -gt 0 ] && fail "产品包不完整，请确认下载完整后重试"
ok "产品包完整"

# 1.2 代理检测
detect_proxy || true

# 1.3 系统检查
if [ -f /etc/os-release ]; then
    . /etc/os-release
    [[ "$ID" == "ubuntu" ]] && ok "Ubuntu $VERSION_ID" || warn "非Ubuntu系统"
fi

[ "$EUID" -eq 0 ] || fail "需要root权限运行"

# 1.4 资源检查
DISK_FREE=$(df -BG / | awk 'NR==2{print $4}' | tr -d 'G')
[ "$DISK_FREE" -ge 5 ] || fail "磁盘空间不足5G"

MEM_TOTAL=$(free -m | awk '/Mem:/{print $2}')
[ "$MEM_TOTAL" -ge 1000 ] || fail "内存不足1G"

ok "环境检查通过"
echo ""

# ===== 阶段2: 配置收集 =====
step "阶段2/7: 配置收集"

load_config "$ENV_FILE"

# 交互模式下提示输入
if [ "$AUTO_MODE" -eq 0 ] && [ -t 0 ]; then
    [ -z "$API_KEY" ] && read -p "  API密钥: " API_KEY
    [ -z "$API_KEY" ] && fail "API密钥不能为空"

    read -p "  API地址 [$API_URL]: " _input
    API_URL="${_input:-$API_URL}"

    read -p "  模型名称 [$MODEL]: " _input
    MODEL="${_input:-$MODEL}"

    read -p "  城市 [$CITY]: " _input
    CITY="${_input:-$CITY}"

    read -p "  微信Chat ID（可选，回车跳过）: " _input
    WEIXIN_ID="${_input:-$WEIXIN_ID}"

    read -p "  Dashboard用户名 [$DASH_USER]: " _input
    DASH_USER="${_input:-$DASH_USER}"

    [ -z "$DASH_PASS" ] && read -s -p "  Dashboard密码: " DASH_PASS
    echo ""
else
    [ -z "$API_KEY" ] && fail "非交互模式下必须设置 API_KEY 或 YOUR_API_KEY 环境变量"
    [ -z "$DASH_PASS" ] && DASH_PASS=$(openssl rand -hex 16)
fi

DASH_SECRET=$(openssl rand -hex 32)
DASH_PASS_HASH=$(echo -n "$DASH_PASS" | sha256sum | awk '{print $1}')

ok "配置收集完成"
echo ""

# ===== 阶段3: 安装依赖 =====
step "阶段3/7: 安装依赖"

HERMES_HOME="$HOME/.hermes"
VAULT_PATH="$HOME/vault"

# 3.1 系统依赖
echo "  安装系统包..."
apt-get update -qq 2>/dev/null
apt-get install -y -qq python3 python3-pip python3-venv git curl wget 2>/dev/null || warn "部分系统包安装失败"

# 3.1.1 Node.js/npm（可选，失败不阻塞部署）
if ! command -v node &> /dev/null; then
    echo "  安装 Node.js..."
    # 尝试 NodeSource 18.x（Ubuntu 默认 nodejs 版本太旧）
    if curl -fsSL https://deb.nodesource.com/setup_18.x -o /tmp/nodesource_setup.sh 2>/dev/null; then
        bash /tmp/nodesource_setup.sh 2>/dev/null && apt-get install -y -qq nodejs 2>/dev/null || true
    fi
    # fallback: 系统自带 nodejs
    if ! command -v node &> /dev/null; then
        apt-get install -y -qq nodejs npm 2>/dev/null || warn "Node.js 安装失败（非关键，部分脚本可能不可用）"
    fi
fi
command -v node &> /dev/null && ok "Node.js $(node --version 2>&1)" || warn "Node.js 未安装"
ok "系统依赖"

# 3.2 Python依赖
echo "  安装Python包..."
# 设置代理（如果已配置）
PIP_OPTS=""
[ -n "$PROXY" ] && PIP_OPTS="--proxy $PROXY"

# 核心依赖：markdown(md转PDF), python-dotenv(环境变量), httpx(HTTP客户端)
# prompt_toolkit(交互式CLI), tomli(TOML解析，Python<3.11需要)
pip3 install $PIP_OPTS markdown python-dotenv httpx prompt_toolkit 2>/dev/null || \
    pip3 install markdown python-dotenv httpx prompt_toolkit 2>/dev/null || true

# tomllib 兼容性：Python 3.11+ 内置 tomllib，3.10 需要 tomli
PYTHON_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYTHON_MINOR=$(echo "$PYTHON_VER" | cut -d. -f2)
if [ "$PYTHON_MINOR" -lt 11 ] 2>/dev/null; then
    pip3 install $PIP_OPTS tomli 2>/dev/null || pip3 install tomli 2>/dev/null || true
    # 创建 tomllib 兼容别名（让 import tomllib 在 3.10 上也能用）
    SITE_DIR=$(python3 -c "import site; print(site.getsitepackages()[0])" 2>/dev/null)
    if [ -n "$SITE_DIR" ] && [ ! -f "$SITE_DIR/tomllib.py" ] && [ -f "$SITE_DIR/tomli/__init__.py" ]; then
        cat > "$SITE_DIR/tomllib.py" << 'TOMLEOF'
"""tomllib compatibility shim for Python < 3.11"""
from tomli import load as _load
def load(fp):
    return _load(fp.read())
def loads(s):
    return _load(s)
TOMLEOF
        ok "tomllib 兼容层（Python $PYTHON_VER）"
    fi
fi
ok "Python依赖"

# 3.3 Hermes
echo "  安装Hermes..."
if command -v hermes &> /dev/null; then
    ok "Hermes已安装: $(hermes --version 2>&1 | head -1)"
else
    curl -fsSL https://hermes-agent.nousresearch.com/install.sh -o /tmp/install_hermes.sh
    # 超时保护：默认300秒，可通过 INSTALL_TIMEOUT 自定义
    # 设 SKIP_HERMES_INSTALL=1 跳过安装（已手动安装时）
    INSTALL_TIMEOUT="${INSTALL_TIMEOUT:-300}"
    if [ "${SKIP_HERMES_INSTALL:-0}" = "1" ]; then
        warn "SKIP_HERMES_INSTALL=1，跳过Hermes安装"
    else
        echo "  安装超时限制: ${INSTALL_TIMEOUT}秒（设 INSTALL_TIMEOUT=0 取消限制）"
        if [ "$INSTALL_TIMEOUT" -gt 0 ] 2>/dev/null; then
            timeout "$INSTALL_TIMEOUT" bash /tmp/install_hermes.sh 2>&1 | tail -5 \
                || warn "Hermes安装超时或失败（${INSTALL_TIMEOUT}秒），请手动安装后重试"
        else
            bash /tmp/install_hermes.sh 2>&1 | tail -5
        fi
    fi
    source ~/.bashrc 2>/dev/null || true

    # 确保hermes命令可用
    HERMES_BIN=$(find /usr/local/bin /usr/local/lib/hermes-agent /root/.hermes/bin -name hermes -type f 2>/dev/null | head -1)
    if [ -n "$HERMES_BIN" ]; then
        ln -sf "$HERMES_BIN" /usr/local/bin/hermes
        chmod +x "$HERMES_BIN"
    fi

    command -v hermes &> /dev/null && ok "Hermes安装成功" || fail "Hermes安装失败"
fi

echo ""

# ===== 阶段4: 部署资产 =====
step "阶段4/7: 部署资产"

# 4.1 目录结构
echo "  创建目录..."
mkdir -p "$HERMES_HOME"/{scripts,skills,profiles/{default,researcher,writer}/{skills,memories}}
mkdir -p "$VAULT_PATH"/{00-Inbox,wiki/{entities,concepts,comparisons,raw},流程,工作室/{员工,项目报告},工作室产出/{调研员·知远/调研报告,写作员·墨白},复盘/员工/{方案架构师·知远,写作员·墨白,军师},日志/每日,用量,博客,entities}
ok "目录结构"

# 4.2 部署脚本
echo "  部署脚本..."
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

# 4.3 部署技能（按角色）
echo "  部署技能..."
SKILL_COUNT=0

# public → default profile
if [ -d "$SCRIPT_DIR/skills/public" ]; then
    for skill_dir in "$SCRIPT_DIR/skills/public"/*/; do
        skill_name=$(basename "$skill_dir")
        cp -r "$skill_dir" "$HERMES_HOME/profiles/default/skills/$skill_name" 2>/dev/null || true
        SKILL_COUNT=$((SKILL_COUNT + 1))
    done
fi

# 角色专属技能
for role in researcher writer; do
    [ -d "$SCRIPT_DIR/skills/$role" ] || continue
    for skill_dir in "$SCRIPT_DIR/skills/$role"/*/; do
        skill_name=$(basename "$skill_dir")
        cp -r "$skill_dir" "$HERMES_HOME/profiles/$role/skills/$skill_name" 2>/dev/null || true
        SKILL_COUNT=$((SKILL_COUNT + 1))
    done
done
ok "$SKILL_COUNT 个技能"

# 4.4 部署Profile
echo "  部署Profile..."
for role in researcher writer; do
    [ -f "$SCRIPT_DIR/profiles/$role/SOUL.md" ] || continue
    cp "$SCRIPT_DIR/profiles/$role/SOUL.md" "$HERMES_HOME/profiles/$role/"
    [ ! -f "$HERMES_HOME/profiles/$role/memories/MEMORY.md" ] && \
        echo "# $role 记忆" > "$HERMES_HOME/profiles/$role/memories/MEMORY.md"
done
ok "2 个员工Profile"

# 4.5 部署Vault
echo "  部署Vault..."
if [ -d "$SCRIPT_DIR/vault" ]; then
    cp -rn "$SCRIPT_DIR/vault/"* "$VAULT_PATH/" 2>/dev/null || true
    ok "Vault知识库"
fi

# 4.6 部署主Agent SOUL
echo "  部署主Agent SOUL..."
if [ -f "$SCRIPT_DIR/vault/SOUL.md" ]; then
    cp "$SCRIPT_DIR/vault/SOUL.md" "$HERMES_HOME/SOUL.md"
    ok "主Agent SOUL"
fi

echo ""

# ===== 阶段5: 生成配置 =====
step "阶段5/7: 生成配置"

# 5.1 .env
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

# 5.2 config.yaml（不存在或含未替换占位符时重新生成）
NEED_CONFIG=0
if [ ! -f "$HERMES_HOME/config.yaml" ]; then
    NEED_CONFIG=1
elif grep -q '{{' "$HERMES_HOME/config.yaml" 2>/dev/null; then
    warn "config.yaml 存在但包含未替换占位符，重新生成"
    NEED_CONFIG=1
fi

if [ "$NEED_CONFIG" -eq 1 ] && [ -f "$SCRIPT_DIR/config-template.yaml" ]; then
    cp "$SCRIPT_DIR/config-template.yaml" "$HERMES_HOME/config.yaml"

    # 替换所有占位符
    sed -i "s|{{YOUR_API_KEY}}|$API_KEY|g" "$HERMES_HOME/config.yaml"
    sed -i "s|{{YOUR_BASE_URL}}|$API_URL|g" "$HERMES_HOME/config.yaml"
    sed -i "s|{{YOUR_MODEL}}|$MODEL|g" "$HERMES_HOME/config.yaml"
    sed -i "s|{{DASHBOARD_USER}}|$DASH_USER|g" "$HERMES_HOME/config.yaml"
    sed -i "s|{{DASHBOARD_PASSWORD_HASH}}|$DASH_PASS_HASH|g" "$HERMES_HOME/config.yaml"
    sed -i "s|{{DASHBOARD_SECRET}}|$DASH_SECRET|g" "$HERMES_HOME/config.yaml"

    # 验证：确保没有残留的 {{ 占位符
    if grep -q '{{YOUR_\|{{DASHBOARD_' "$HERMES_HOME/config.yaml" 2>/dev/null; then
        warn "config.yaml 仍有未替换的占位符，请手动检查"
    else
        ok "config.yaml"
    fi
elif [ "$NEED_CONFIG" -eq 0 ]; then
    warn "config.yaml 已存在且无占位符，跳过"
else
    warn "config-template.yaml 缺失，跳过 config.yaml 生成"
fi

echo ""

# ===== 阶段6: 创建Cron =====
step "阶段6/7: 创建定时任务"

CRON_MODEL="$MODEL"
CRON_PROVIDER="custom"

if command -v hermes &> /dev/null; then
    create_cron() {
        local name="$1"; shift
        hermes cron create --name "$name" --model "$CRON_MODEL" --provider "$CRON_PROVIDER" "$@" 2>/dev/null \
            && ok "$name" || warn "$name（可能已存在）"
    }

    # 注意: schedule 和 prompt 是位置参数，不是 --schedule/--prompt 选项
    # 格式: hermes cron create [options] schedule [prompt]

    create_cron "每日晨报" "0 8 * * *" \
        "你是每日晨报助手。查看天气、昨日用量、待办事项。用中文输出，条目式。天气用 curl wttr.in/${CITY}?format=3 获取。"

    create_cron "服务器监控" "*/30 * * * *" \
        --script "server_watch.sh" --no-agent

    create_cron "Token用量结算" "10 0 * * *" \
        --script "token_report.py" --no-agent

    create_cron "Inbox AI分类" "0 3 * * *" \
        --script "classify_inbox.py" \
        "运行 classify_inbox.py 对 Inbox 目录的文件进行AI分类，将文件移动到合适的目录。"

    create_cron "知识库健康度" "10 3 * * *" \
        --script "knowledge_health_check.sh" \
        "运行知识库健康检查脚本，报告知识库状态和问题。"

    create_cron "知识库整理" "30 3 * * *" \
        "运行 fix_frontmatter.py 和 fix_dead_links.py 修复知识库问题。"

    create_cron "每周备份" "0 3 * * 0" \
        --script "weekly_backup.sh" --no-agent

    create_cron "目录更新" "30 4 * * *" \
        --script "skills_inventory_wrapper.sh" --no-agent

    create_cron "夜间检查" "30 7 * * *" \
        --script "night_check.py" --no-agent

    create_cron "习惯体检" "30 5 * * 6" \
        --script "habit_check.sh" \
        "运行习惯检查脚本，分析用户的习惯执行情况并给出建议。"

    create_cron "流程优化" "30 5 * * 0" \
        --script "flow_signal_extract.sh" \
        "运行流程信号提取脚本，分析工作流程中的瓶颈和优化机会。"

    create_cron "产出Watchdog" "*/10 * * * *" \
        --script "watchdog_inbox.py" \
        "监控工作室产出目录，检查是否有新产出需要处理。"

    CRON_COUNT=$(hermes cron list 2>/dev/null | grep -c "✅\|⏸\|❌" || echo 0)
    ok "共 $CRON_COUNT 个定时任务"
else
    warn "hermes 不可用，跳过 cron 创建"
fi

echo ""

# ===== 阶段7: 验证 =====
step "阶段7/7: 验证部署"

ERRORS=0
command -v hermes &> /dev/null && ok "hermes 命令" || { warn "hermes 命令不可用"; ERRORS=$((ERRORS+1)); }
[ -d "$VAULT_PATH" ] && ok "Vault 目录" || { warn "Vault 目录缺失"; ERRORS=$((ERRORS+1)); }
[ -d "$HERMES_HOME/scripts" ] && ok "Scripts 目录" || { warn "Scripts 缺失"; ERRORS=$((ERRORS+1)); }
[ -d "$HERMES_HOME/profiles/default/skills" ] && ok "Skills 目录" || { warn "Skills 缺失"; ERRORS=$((ERRORS+1)); }
[ -f "$HERMES_HOME/.env" ] && ok ".env 配置" || { warn ".env 缺失"; ERRORS=$((ERRORS+1)); }
[ -f "$HERMES_HOME/config.yaml" ] && ok "config.yaml" || { warn "config.yaml 缺失"; ERRORS=$((ERRORS+1)); }
[ -f "$HERMES_HOME/profiles/researcher/SOUL.md" ] && ok "调研员 SOUL" || { warn "调研员缺失"; ERRORS=$((ERRORS+1)); }
[ -f "$HERMES_HOME/profiles/writer/SOUL.md" ] && ok "写作员 SOUL" || { warn "写作员缺失"; ERRORS=$((ERRORS+1)); }

# 验证 hermes 命令可用性
if command -v hermes &> /dev/null; then
    # 确保 hermes venv 中的依赖已安装
    HERMES_VENV="$HERMES_HOME/venv"
    if [ -d "$HERMES_VENV" ]; then
        "$HERMES_VENV/bin/pip" install -q markdown python-dotenv httpx prompt_toolkit 2>/dev/null || true
        # tomllib 兼容
        if [ "$PYTHON_MINOR" -lt 11 ] 2>/dev/null; then
            "$HERMES_VENV/bin/pip" install -q tomli 2>/dev/null || true
        fi
    fi
    # 测试 hermes status（不阻塞部署）
    if hermes status &> /dev/null 2>&1; then
        ok "hermes status 正常"
    else
        warn "hermes status 报错（可能 config.yaml 未配置 API 密钥，部署后手动检查）"
    fi
fi

echo ""
echo "═══════════════════════════════════════════════"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}  ✅ 部署完成！全部检查通过${NC}"
else
    echo -e "${YELLOW}  ⚠️  部署完成，$ERRORS 项需注意${NC}"
fi
echo "═══════════════════════════════════════════════"
echo ""
echo "📊 统计: 脚本 $SCRIPT_COUNT 个 | 技能 $SKILL_COUNT 个 | Cron ${CRON_COUNT:-0} 个"
echo ""
echo "═══════════════════════════════════════════════"
echo "  后续步骤"
echo "═══════════════════════════════════════════════"
echo ""
echo "  1. 重启 Gateway 使配置生效："
echo "     方法A: hermes gateway restart"
echo "     方法B: pkill -f 'hermes.*gateway' && hermes gateway start"
echo "     方法C: 重启终端后运行 hermes gateway start"
echo ""
echo "  2. 验证部署："
echo "     hermes status          # 检查状态"
echo "     hermes cron list       # 查看定时任务"
echo "     hermes dashboard       # 打开Dashboard"
echo ""
echo "  3. 如遇问题："
echo "     hermes doctor          # 诊断常见问题"
echo "     hermes logs --tail 50  # 查看最近日志"
echo ""
