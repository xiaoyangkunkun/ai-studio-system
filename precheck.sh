#!/bin/bash
# ══════════════════════════════════════════════════
#  AI工作室系统 · 环境预检脚本
#  用法: bash precheck.sh
#  在 deploy.sh 之前运行，检测环境是否满足要求
# ══════════════════════════════════════════════════

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}  ✅ $1${NC}"; }
warn() { echo -e "${YELLOW}  ⚠️  $1${NC}"; }
fail() { echo -e "${RED}  ❌ $1${NC}"; }

echo ""
echo "═══════════════════════════════════════════════"
echo "  AI工作室系统 · 环境预检"
echo "═══════════════════════════════════════════════"
echo ""

ERRORS=0

# 1. 操作系统
echo "▶ 操作系统"
if [ -f /etc/os-release ]; then
    . /etc/os-release
    echo "  系统: $PRETTY_NAME"
    if [[ "$ID" == "ubuntu" && "$VERSION_ID" == "22.04" ]]; then
        ok "Ubuntu 22.04"
    elif [[ "$ID" == "ubuntu" ]]; then
        warn "Ubuntu $VERSION_ID（建议 22.04）"
    else
        warn "$PRETTY_NAME（可能不兼容，建议 Ubuntu 22.04）"
    fi
else
    warn "无法识别操作系统"
fi

# 2. 权限
echo ""
echo "▶ 权限"
if [ "$EUID" -eq 0 ]; then
    ok "root 用户"
else
    warn "非 root 用户，某些操作需要 sudo"
    sudo -n true 2>/dev/null && ok "sudo 免密" || { fail "sudo 需要密码，请用 root 或配置免密 sudo"; ERRORS=$((ERRORS+1)); }
fi

# 3. 网络
echo ""
echo "▶ 网络"
curl -s --max-time 5 https://github.com > /dev/null 2>&1 && ok "GitHub 可达" || { fail "GitHub 不可达，无法安装 Hermes"; ERRORS=$((ERRORS+1)); }
curl -s --max-time 5 https://api.openai.com > /dev/null 2>&1 && ok "OpenAI API 可达" || warn "OpenAI API 不可达（如用其他提供商可忽略）"
ping -c 1 -W 2 8.8.8.8 > /dev/null 2>&1 && ok "外网连通" || warn "外网可能受限"

# 4. 磁盘
echo ""
echo "▶ 磁盘"
DISK_FREE=$(df -BG / | awk 'NR==2{print $4}' | tr -d 'G')
echo "  可用空间: ${DISK_FREE}G"
if [ "$DISK_FREE" -ge 10 ]; then
    ok "磁盘空间充足"
elif [ "$DISK_FREE" -ge 5 ]; then
    warn "磁盘空间偏少（建议 10G+）"
else
    fail "磁盘空间不足 5G，无法安装"
    ERRORS=$((ERRORS+1))
fi

# 5. 内存
echo ""
echo "▶ 内存"
MEM_TOTAL=$(free -m | awk '/Mem:/{print $2}')
echo "  总内存: ${MEM_TOTAL}MB"
if [ "$MEM_TOTAL" -ge 2000 ]; then
    ok "内存充足"
elif [ "$MEM_TOTAL" -ge 1000 ]; then
    warn "内存偏少（建议 2G+），可能卡顿"
else
    fail "内存不足 1G，无法运行"
    ERRORS=$((ERRORS+1))
fi

# 6. 已有依赖
echo ""
echo "▶ 已有依赖"
command -v python3 &> /dev/null && ok "Python3 $(python3 --version 2>&1 | awk '{print $2}')" || warn "Python3 未安装（deploy.sh 会自动装）"
command -v node &> /dev/null && ok "Node.js $(node --version 2>&1)" || warn "Node.js 未安装（deploy.sh 会自动装）"
command -v git &> /dev/null && ok "Git $(git --version 2>&1 | awk '{print $3}')" || warn "Git 未安装（deploy.sh 会自动装）"
command -v hermes &> /dev/null && ok "Hermes $(hermes --version 2>&1)" || warn "Hermes 未安装（deploy.sh 会自动装）"

# 7. 检查是否已有 .hermes
echo ""
echo "▶ 已有安装"
if [ -d "$HOME/.hermes" ]; then
    warn "~/.hermes 已存在，deploy.sh 不会覆盖已有配置"
else
    ok "全新安装"
fi

# 结果
echo ""
echo "═══════════════════════════════════════════════"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}  ✅ 环境检查通过，可以运行 deploy.sh${NC}"
else
    echo -e "${RED}  ❌ 发现 $ERRORS 个问题，请先修复后再部署${NC}"
fi
echo "═══════════════════════════════════════════════"
echo ""
