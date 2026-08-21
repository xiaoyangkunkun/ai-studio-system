#!/bin/bash
# 生成 Windows Hermes 迁移专用包(不含 Linux 专属配置/微信凭据)
set -e
STAMP=$(date +%Y%m%d)
OUT=/root/backup/hermes-windows-migration-$STAMP
PKG=/root/backup/hermes-windows-migration-$STAMP.zip
rm -rf "$OUT" "$PKG"
mkdir -p "$OUT/sessions"

H=/root/.hermes

# 1. 记忆(全局共享,Windows 端直接可用)
cp -r "$H/memories" "$OUT/" && echo "✓ memories"

# 2. 技能(跨平台;README 说明可剔除 Linux 专属)
cp -r "$H/skills" "$OUT/" && echo "✓ skills"

# 3. SOUL 设定
cp "$H/SOUL.md" "$OUT/" && echo "✓ SOUL.md"

# 4. 会话历史(state.db + sessions)
cp "$H/state.db" "$OUT/" && echo "✓ state.db"
cp -r "$H/sessions/." "$OUT/sessions/" 2>/dev/null || true
echo "✓ sessions"

# 5. API Key 提取(不含微信/浏览器/调试类)
grep -E "^(DEEPSEEK_API_KEY|DEEPSEEK_BASE_URL|NOTION_API_KEY)=" "$H/.env" > "$OUT/api-keys.txt" || true
echo "✓ api-keys.txt(DeepSeek/Notion)"

# 6. 迁移说明
cat > "$OUT/README-Windows.md" <<'EOF'
# Windows Hermes 迁移说明

本包内容:记忆、技能、SOUL 设定、会话历史、API Key。
⚠️ 不含:config.yaml、微信凭据(Windows 端勿接微信,避免与服务器冲突)、Linux 专属配置。

## 迁移步骤(Windows)

1. **先备份** Windows 原有配置:
   `copy C:\Users\<你的用户名>\.hermes C:\Users\<你的用户名>\.hermes.bak`(或手动复制)

2. 解压本包到临时目录。

3. 复制以下内容到 `C:\Users\<你的用户名>\.hermes\`(覆盖/合并):
   - `memories\`  → 记忆(核心!)
   - `skills\`    → 技能(可选择性删除 Linux 运维类,如 hermes-server-ops)
   - `SOUL.md`    → 灵魂设定
   - `state.db` + `sessions\` → 会话历史(可选,用于检索服务器端历史对话)

4. **合并 API Key**:用记事本打开 `api-keys.txt`,把其中 KEY=值 追加到
   Windows 的 `C:\Users\<你的用户名>\.hermes\.env` 中(不要覆盖整个 .env!)

5. **不要覆盖** Windows 已有的 `config.yaml`(平台/路径配置不同)。

6. 知识库(vault):无需从本包恢复,Syncthing 已同步到 Windows。

7. 重启 Windows 上的 Hermes,验证:问它"你知道我的服务器配置吗?"或"我的记忆里有什么"。

## 验证清单
- [ ] 新会话能说出你的偏好/服务器信息(记忆生效)
- [ ] skills 命令能看到技能列表
- [ ] 可选:session_search 能搜到服务器历史会话
EOF
echo "✓ README-Windows.md"

# 7. 打包 zip
cd /root/backup && zip -rq "$PKG" "$(basename "$OUT")" && echo "✓ 打包完成"
ls -lh "$PKG"
