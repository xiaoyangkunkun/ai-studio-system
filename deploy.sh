#!/bin/bash
# ══════════════════════════════════════════════════
#  AI工作室系统 · 一键部署脚本 v4.0
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
echo "  AI工作室系统 · 一键部署 v4.0"
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

# 1.4 资源检查（修复14：精确到MB）
DISK_FREE_MB=$(df -m / | awk 'NR==2{print $4}')
[ "$DISK_FREE_MB" -ge 5120 ] || fail "磁盘空间不足5G（当前${DISK_FREE_MB}MB）"

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
HERMES_VENV="/usr/local/lib/hermes-agent/venv"

# 3.1 系统依赖
echo "  安装系统包..."
apt-get update -qq 2>/dev/null
apt-get install -y -qq python3 python3-pip python3-venv git curl wget 2>/dev/null || warn "部分系统包安装失败"

# 3.1.1 Node.js/npm（可选）
if ! command -v node &> /dev/null; then
    echo "  安装 Node.js..."
    if curl -fsSL https://deb.nodesource.com/setup_18.x -o /tmp/nodesource_setup.sh 2>/dev/null; then
        bash /tmp/nodesource_setup.sh 2>/dev/null && apt-get install -y -qq nodejs 2>/dev/null || true
    fi
    if ! command -v node &> /dev/null; then
        apt-get install -y -qq nodejs npm 2>/dev/null || warn "Node.js 安装失败（非关键）"
    fi
fi
command -v node &> /dev/null && ok "Node.js $(node --version 2>&1)" || warn "Node.js 未安装"
ok "系统依赖"

# 3.1.2 Syncthing（可选）
if ! command -v syncthing &> /dev/null; then
    echo "  安装 Syncthing..."
    ST_VERSION=$(curl -s https://api.github.com/repos/syncthing/syncthing/releases/latest 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin)['tag_name'])" 2>/dev/null || echo "")
    if [ -n "$ST_VERSION" ]; then
        ST_URL="https://github.com/syncthing/syncthing/releases/download/${ST_VERSION}/syncthing-linux-amd64-${ST_VERSION}.tar.gz"
        curl -sL "$ST_URL" -o /tmp/syncthing.tar.gz 2>/dev/null && \
        tar xzf /tmp/syncthing.tar.gz -C /tmp 2>/dev/null && \
        cp /tmp/syncthing-*/syncthing /usr/local/bin/ 2>/dev/null && \
        chmod +x /usr/local/bin/syncthing && \
        rm -rf /tmp/syncthing* && \
        ok "Syncthing $ST_VERSION" || warn "Syncthing 安装失败（非关键）"
    else
        warn "无法获取 Syncthing 版本（非关键）"
    fi
fi

# 创建 Syncthing systemd 服务
if command -v syncthing &> /dev/null && [ ! -f /etc/systemd/system/syncthing.service ]; then
    cat > /etc/systemd/system/syncthing.service << 'STEOF'
[Unit]
Description=Syncthing
After=network.target

[Service]
User=root
ExecStart=/usr/local/bin/syncthing serve --no-browser --home=/root/.config/syncthing
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
STEOF
    systemctl daemon-reload
    systemctl enable syncthing 2>/dev/null || true
    ok "Syncthing 服务已配置"
fi

# 初始化Syncthing并配置同步目录
if command -v syncthing &> /dev/null; then
    echo "  初始化 Syncthing..."
    # 创建配置目录
    mkdir -p /root/.config/syncthing
    # 生成默认配置（如果不存在）
    if [ ! -f /root/.config/syncthing/config.xml ]; then
        syncthing generate --config=/root/.config/syncthing 2>/dev/null || true
    fi
    # 启动Syncthing服务
    systemctl start syncthing 2>/dev/null || true
    sleep 3
    # 添加同步文件夹（vault包含wiki、流程、工作室等所有内容）
    if [ -d "$VAULT_PATH" ]; then
        # 使用Syncthing CLI添加文件夹（如果可用）
        syncthing cli config folders add --path="$VAULT_PATH" --label="Vault" --id="vault" 2>/dev/null || true
        ok "Syncthing已配置同步: $VAULT_PATH"
    fi
    # 同步Obsidian插件配置（包括studio hub）
    OBSIDIAN_DIR="$HOME/.obsidian"
    if [ -d "$OBSIDIAN_DIR" ]; then
        syncthing cli config folders add --path="$OBSIDIAN_DIR" --label="Obsidian-Plugins" --id="obsidian-plugins" 2>/dev/null || true
        ok "Syncthing已配置同步: $OBSIDIAN_DIR"
    fi
fi

# 3.1.3 PDF工具（可选）
if ! command -v wkhtmltopdf &> /dev/null; then
    echo "  安装 PDF 工具..."
    apt-get install -y -qq wkhtmltopdf fonts-noto-cjk 2>/dev/null && \
        ok "wkhtmltopdf + 中文字体" || warn "PDF工具安装失败（非关键）"
fi

# 3.2 Python依赖（修复11：统一安装到系统Python）
echo "  安装Python包..."
PIP_OPTS=""
[ -n "$PROXY" ] && PIP_OPTS="--proxy $PROXY"

pip3 install $PIP_OPTS markdown python-dotenv httpx prompt_toolkit rich croniter openai 2>/dev/null || \
    pip3 install markdown python-dotenv httpx prompt_toolkit rich croniter openai 2>/dev/null || true

# tomllib 兼容性（修复8：修复bytes/str）
PYTHON_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if [[ "$PYTHON_VER" < "3.11" ]]; then
    pip3 install tomli 2>/dev/null || true
    SITE_DIR=$(python3 -c "import site; print(site.getsitepackages()[0])")
    if [ ! -f "$SITE_DIR/tomllib.py" ]; then
        cat > "$SITE_DIR/tomllib.py" << 'TOMLEOF'
from tomli import load
def loads(s):
    if isinstance(s, str):
        s = s.encode()
    return load(s)
TOMLEOF
        ok "tomllib 兼容层（Python 3.10）"
    fi
fi
ok "Python依赖"

# 3.3 Hermes
echo "  安装Hermes..."
INSTALL_TIMEOUT="${INSTALL_TIMEOUT:-300}"

if command -v hermes &> /dev/null; then
    ok "Hermes已安装: $(hermes --version 2>&1 | head -1)"
else
    curl -fsSL https://hermes-agent.nousresearch.com/install.sh -o /tmp/install_hermes.sh
    if [ "${SKIP_HERMES_INSTALL:-0}" = "1" ]; then
        warn "SKIP_HERMES_INSTALL=1，跳过Hermes安装"
    else
        echo "  安装超时限制: ${INSTALL_TIMEOUT}秒"
        if [ "$INSTALL_TIMEOUT" -gt 0 ] 2>/dev/null; then
            timeout "$INSTALL_TIMEOUT" bash /tmp/install_hermes.sh 2>&1 | tail -5 \
                || warn "Hermes安装超时或失败"
        else
            bash /tmp/install_hermes.sh 2>&1 | tail -5
        fi
    fi
    source ~/.bashrc 2>/dev/null || true

    HERMES_BIN=$(find /usr/local/bin /usr/local/lib/hermes-agent -name hermes -type f 2>/dev/null | head -1)
    if [ -n "$HERMES_BIN" ]; then
        ln -sf "$HERMES_BIN" /usr/local/bin/hermes
        chmod +x "$HERMES_BIN"
    fi
    command -v hermes &> /dev/null && ok "Hermes安装成功" || fail "Hermes安装失败"
fi

# 3.3.1 Hermes venv依赖（修复11：统一路径）
if [ -d "$HERMES_VENV" ] && [ -f "$HERMES_VENV/bin/pip" ]; then
    echo "  安装Hermes venv依赖..."
    "$HERMES_VENV/bin/pip" install rich httpx prompt_toolkit croniter openai 2>/dev/null || true
    ok "Hermes venv依赖"
elif [ -d "$HERMES_VENV" ]; then
    warn "venv目录存在但pip不可用，尝试重建..."
    python3 -m venv "$HERMES_VENV" --clear 2>/dev/null || true
    "$HERMES_VENV/bin/pip" install rich httpx prompt_toolkit croniter openai 2>/dev/null || true
    ok "Hermes venv依赖（重建）"
else
    warn "venv目录不存在，跳过venv依赖安装"
fi

# 3.3.2 Python 3.10正则兼容性修复（修复7：检查venv Python）
HERMES_PYTHON_VER=$("$HERMES_VENV/bin/python3" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "3.11")
if [[ "$HERMES_PYTHON_VER" < "3.11" ]]; then
    echo "  修复Python 3.10正则兼容性..."
    python3 -c "
import glob
files = glob.glob('/usr/local/lib/hermes-agent/**/*.py', recursive=True)
fixed = 0
for f in files:
    try:
        with open(f, 'r') as fh:
            content = fh.read()
        new_content = content.replace(']++', ']+').replace(']*+', ']*').replace(']?+', ']?')
        if new_content != content:
            with open(f, 'w') as fh:
                fh.write(new_content)
            fixed += 1
    except: pass
print(f'  修复了 {fixed} 个文件')
" 2>/dev/null || true
    ok "正则兼容性修复"
fi

echo ""

# ===== 阶段4: 部署资产 =====
step "阶段4/7: 部署资产"

# 4.1 目录结构
echo "  创建目录..."
mkdir -p "$HERMES_HOME"/{scripts,skills,profiles/{researcher,writer}/{skills,memories}}
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

# 4.3 部署技能（修复6：只部署到全局skills目录）
echo "  部署技能..."
SKILL_COUNT=0

# public → 全局skills目录
if [ -d "$SCRIPT_DIR/skills/public" ]; then
    for skill_dir in "$SCRIPT_DIR/skills/public"/*/; do
        skill_name=$(basename "$skill_dir")
        cp -r "$skill_dir" "$HERMES_HOME/skills/$skill_name" 2>/dev/null || true
        SKILL_COUNT=$((SKILL_COUNT + 1))
    done
fi

# 角色专属技能 → 全局skills目录
for role in researcher writer; do
    [ -d "$SCRIPT_DIR/skills/$role" ] || continue
    for skill_dir in "$SCRIPT_DIR/skills/$role"/*/; do
        skill_name=$(basename "$skill_dir")
        cp -r "$skill_dir" "$HERMES_HOME/skills/$skill_name" 2>/dev/null || true
        SKILL_COUNT=$((SKILL_COUNT + 1))
    done
done
ok "$SKILL_COUNT 个技能"

# 4.4 部署Profile
echo "  部署Profile..."
for role in researcher writer; do
    [ -f "$SCRIPT_DIR/profiles/$role/SOUL.md" ] || continue
    cp "$SCRIPT_DIR/profiles/$role/SOUL.md" "$HERMES_HOME/profiles/$role/"
    mkdir -p "$HERMES_HOME/profiles/$role/memories"
    [ ! -f "$HERMES_HOME/profiles/$role/memories/MEMORY.md" ] && \
        echo "# $role 记忆" > "$HERMES_HOME/profiles/$role/memories/MEMORY.md"
    # 创建profile的config.yaml（delegation需要）
    cat > "$HERMES_HOME/profiles/$role/config.yaml" << PROFILEEOF
model:
  base_url: "$API_URL"
  default: "$MODEL"
  provider: custom
  api_key: "$API_KEY"
PROFILEEOF
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

# 5.1 .env（修复3：加引号，修复10：改为追加模式）
if [ -f "$HERMES_HOME/.env" ]; then
    # 备份现有.env
    cp "$HERMES_HOME/.env" "$HERMES_HOME/.env.bak.$(date +%Y%m%d%H%M%S)"
    # 删除已存在的变量
    for var in YOUR_API_KEY YOUR_BASE_URL YOUR_MODEL WEIXIN_CHAT_ID CITY DASHBOARD_USER DASHBOARD_SECRET; do
        sed -i "/^${var}=/d" "$HERMES_HOME/.env"
    done
fi

# 追加新变量（修复3：加双引号）
cat >> "$HERMES_HOME/.env" << ENVEOF
# AI工作室系统 环境变量（deploy.sh自动生成）
YOUR_API_KEY="$API_KEY"
YOUR_BASE_URL="$API_URL"
YOUR_MODEL="$MODEL"
WEIXIN_CHAT_ID="$WEIXIN_ID"
CITY="$CITY"
DASHBOARD_USER="$DASH_USER"
DASHBOARD_SECRET="$DASH_SECRET"
ENVEOF
ok ".env"

# 5.2 config.yaml（修复2：不产生重复delegation段）
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

    # 验证占位符
    if grep -q '{{YOUR_\|{{DASHBOARD_' "$HERMES_HOME/config.yaml" 2>/dev/null; then
        warn "config.yaml 仍有未替换的占位符，请手动检查"
    else
        ok "config.yaml"
    fi

    # 添加delegation配置（修复2：检查是否已存在）
    if ! grep -q 'delegation:' "$HERMES_HOME/config.yaml" 2>/dev/null; then
        cat >> "$HERMES_HOME/config.yaml" << DELEGEOF

delegation:
  max_iterations: 50
  model: "$MODEL"
  provider: custom
  api_key: "$API_KEY"
  workdir: "$VAULT_PATH"
DELEGEOF
        ok "delegation配置"
    fi
elif [ "$NEED_CONFIG" -eq 0 ]; then
    warn "config.yaml 已存在且无占位符，跳过"
else
    warn "config-template.yaml 缺失，跳过 config.yaml 生成"
fi

echo ""

# ===== 阶段5.5: 启动Gateway（Cron创建需要Gateway运行）=====
echo "  启动 Gateway..."
if systemctl is-active hermes-gateway.service &>/dev/null; then
    ok "Gateway 已运行（systemctl）"
elif hermes gateway restart &>/dev/null 2>&1; then
    ok "Gateway 已启动"
else
    pkill -9 -f 'hermes.*run' 2>/dev/null || true
    sleep 2
    nohup hermes gateway run > /tmp/gw.log 2>&1 &
    sleep 3
    if ps aux | grep -q '[h]ermes.*gateway'; then
        ok "Gateway 已启动（手动）"
    else
        warn "Gateway 启动失败，Cron任务可能无法创建"
    fi
fi

echo ""

# ===== 阶段6: 创建Cron =====
step "阶段6/7: 创建定时任务"

CRON_MODEL="$MODEL"
CRON_PROVIDER="custom"

# 修复4：添加幂等性检查
create_cron() {
    local name="$1"; shift
    # 检查同名任务是否已存在
    if hermes cron list 2>/dev/null | grep -q "Name:.*$name"; then
        warn "$name（已存在，跳过）"
        return 0
    fi
    hermes cron create --name "$name" --model "$CRON_MODEL" --provider "$CRON_PROVIDER" "$@" 2>/dev/null \
        && ok "$name" || warn "$name 创建失败"
}

if command -v hermes &> /dev/null; then
    # 修复5：添加--deliver参数
    DELIVER_OPT=""
    [ -n "$WEIXIN_ID" ] && DELIVER_OPT="--deliver weixin:$WEIXIN_ID"

    create_cron "每日晨报" "0 8 * * *" \
        $DELIVER_OPT \
        "你是每日晨报助手。查看天气、昨日用量、待办事项。用中文输出，条目式。天气用 curl wttr.in/${CITY}?format=3 获取。"

    create_cron "服务器监控" "*/30 * * * *" \
        $DELIVER_OPT \
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
        "运行流程优化脚本，提取流程改进信号。"

    create_cron "产出Watchdog" "*/10 * * * *" \
        --script "watchdog_inbox.py" \
        "运行 watchdog_inbox.py 监听产出目录。"

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
[ -d "$HERMES_HOME/skills" ] && ok "Skills 目录" || { warn "Skills 缺失"; ERRORS=$((ERRORS+1)); }
[ -f "$HERMES_HOME/.env" ] && ok ".env 配置" || { warn ".env 缺失"; ERRORS=$((ERRORS+1)); }
[ -f "$HERMES_HOME/config.yaml" ] && ok "config.yaml" || { warn "config.yaml 缺失"; ERRORS=$((ERRORS+1)); }
[ -f "$HERMES_HOME/profiles/researcher/SOUL.md" ] && ok "调研员 SOUL" || { warn "调研员缺失"; ERRORS=$((ERRORS+1)); }
[ -f "$HERMES_HOME/profiles/writer/SOUL.md" ] && ok "写作员 SOUL" || { warn "写作员缺失"; ERRORS=$((ERRORS+1)); }

# 验证hermes status
if hermes status &> /dev/null 2>&1; then
    ok "hermes status 正常"
else
    warn "hermes status 报错（可能 config.yaml 未配置 API 密钥）"
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

echo ""
echo "═══════════════════════════════════════════════"
echo "  后续步骤"
echo "═══════════════════════════════════════════════"
echo ""
echo "  1. 验证部署："
echo "     hermes status          # 检查状态"
echo "     hermes cron list       # 查看定时任务"
echo "     hermes dashboard       # 打开Dashboard"
echo ""
echo "  2. 如遇问题："
echo "     hermes doctor          # 诊断常见问题"
echo "     hermes logs --tail 50  # 查看最近日志"
echo ""
