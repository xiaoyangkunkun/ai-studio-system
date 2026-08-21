#!/bin/bash
# 一键备份脚本:迁移/灾难恢复用
# 用法:bash backup_all.sh [输出目录,默认 ~/backup]
OUT="${1:-~/backup}"
STAMP=$(date +%Y%m%d_%H%M)
DIR="$OUT/hermes-backup-$STAMP"
mkdir -p "$DIR" "$DIR/docs"

echo "===== Hermes 服务器完整备份 ====="
echo "输出目录: $DIR"

# 1. Hermes 程序(含 weixin.py 补丁;重装后 diff 还原)
if [ -d /usr/local/lib/hermes-agent ]; then
    tar czf "$DIR/hermes-agent-code.tar.gz" \
        -C /usr/local/lib/hermes-agent \
        --exclude='venv' --exclude='__pycache__' --exclude='.git' \
        gateway/platforms/weixin.py gateway/ 2>/dev/null || true
    echo "✓ hermes-agent 关键代码(含微信补丁)"
fi

# 2. ${HERMES_HOME:-$HOME/.hermes} 核心(配置/密钥/记忆/技能/会话/cron/平台/插件/钩子)
if [ -d ${HERMES_HOME:-$HOME/.hermes} ]; then
    tar czf "$DIR/hermes-dotdir.tar.gz" \
        -C ${HERMES_HOME:-$HOME/.hermes} \
        --exclude='logs' --exclude='cache' --exclude='audio_cache' \
        --exclude='image_cache' --exclude='*.db-shm' --exclude='*.db-wal' \
        --exclude='hermes-agent' --exclude='venv' --exclude='bin' --exclude='lsp' \
        config.yaml .env auth.json memories skills cron state.db sessions \
        kanban.db kanban SOUL.md platforms pairing plugins hooks scripts \
        projects.db weixin state gateway_state.json channel_directory.json \
        processes.json profiles 2>/dev/null || true
    echo "✓ ${HERMES_HOME:-$HOME/.hermes}(含 SOUL/平台配对/插件/钩子/脚本/项目库/员工 profiles)"
fi

# 3. systemd 服务定义
mkdir -p "$DIR/systemd"
cp -r /etc/systemd/system/hermes-*.service "$DIR/systemd/" 2>/dev/null || true
cp -r /etc/systemd/system/hermes-*.service.d "$DIR/systemd/" 2>/dev/null || true
cp -r /etc/systemd/system/clash* "$DIR/systemd/" 2>/dev/null || true
cp -r /etc/systemd/system/syncthing* "$DIR/systemd/" 2>/dev/null || true
cp -r /etc/systemd/system/bing-search-bridge* "$DIR/systemd/" 2>/dev/null || true
echo "✓ systemd 服务定义"

# 4. 代理与搜索配置
cp /etc/clash/config.yaml "$DIR/clash-config.yaml" 2>/dev/null && echo "✓ clash 配置" || echo "⚠ clash 配置缺失"

# 4b. 宝塔相关(仅备份 nginx 配置,防万一;面板/网站为空不备)
if [ -d /www/server/nginx/conf ]; then
    tar czf "$DIR/baota-nginx.tar.gz" -C /www/server/nginx conf 2>/dev/null
    echo "✓ nginx 配置(宝塔,空站点仅备配置)"
else
    echo "— 无宝塔面板,跳过"
fi

# 5. 知识库与散落文档
tar czf "$DIR/vault.tar.gz" -C /root vault 2>/dev/null && echo "✓ vault 知识库" || echo "⚠ vault 缺失"
cp ~/*.md "$DIR/docs/" 2>/dev/null || true
[ -n "$(ls -A "$DIR/docs" 2>/dev/null)" ] && echo "✓ 散落文档" || echo "⚠ 无散落文档"

# 6. 环境信息记录(新机器参照)
{
    echo "备份时间: $(date)"
    echo "主机名: $(hostname)"
    echo "公网域名: {{SYNC_DOMAIN}} (IP {{SERVER_IP}})"
    echo "系统: Ubuntu 22.04 (新机也装 22.04)"
    echo "Hermes 版本: $(/usr/local/lib/hermes-agent/venv/bin/hermes --version 2>/dev/null | head -1)"
    echo "注意: 新机器公网IP会变, 需更新: Syncthing 设备地址/安全组/UFW"
} > "$DIR/README.txt"
echo "✓ README 环境说明"

# 7. 校验
echo "===== 备份完成, 文件清单 ====="
ls -lh "$DIR/"
echo "总大小: $(du -sh "$DIR" | cut -f1)"
echo "✅ 建议: 把整个 $DIR 下载到本地电脑保存(如 scp -r root@{{SYNC_DOMAIN}}:$DIR .)"

# 8. 保留策略:只保留最近 4 份备份
cd "$OUT" && ls -dt hermes-backup-* 2>/dev/null | tail -n +5 | xargs -r rm -rf
echo "✅ 已清理旧备份,保留最近 4 份"
