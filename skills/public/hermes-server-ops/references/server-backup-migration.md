---
title: "服务器备份与迁移(ECS 到期换机)"
created: 2026-08-20
updated: 2026-08-20
type: note
---
# 服务器备份与迁移(ECS 到期换机)

场景:阿里云 ECS 到期前完整备份,新机恢复后与原服务器功能一致(Hermes/微信/知识库/定时任务全保留)。2026-08 实测。

## 一键备份脚本
`~/.hermes/scripts/backup_all.sh`(已实测,~14MB/次,保留最近 4 份自动清理):
```
bash ~/.hermes/scripts/backup_all.sh
```
**完整备份清单(含容易遗漏项)**:
- Hermes 代码:`/usr/local/lib/hermes-agent/gateway/platforms/weixin.py`(微信 CDN 补丁,升级会被覆盖)
- `~/.hermes/`:config.yaml、.env(所有密钥)、auth.json(Nous OAuth)、memories、skills、cron、state.db、sessions、kanban.db、kanban、**SOUL.md、platforms(微信配对批准 weixin-approved.json!)、pairing、plugins、hooks、scripts、projects.db、weixin、state、gateway_state.json、channel_directory.json、processes.json、profiles(数字员工知远/墨白 的 SOUL/技能/记忆,~36MB,2026-08-14 曾漏备已补;验证 `tar tzf hermes-dotdir.tar.gz | grep profiles/researcher`)**
- 排除(可重建):logs、cache、audio_cache、image_cache、bin(64M 工具链)、lsp、venv
- systemd:`/etc/systemd/system/hermes-*.service(.d)`、clash*、syncthing*、bing-search-bridge*(含 drop-in 代理注入)
- Clash:`/etc/clash/config.yaml`(机场订阅)
- **宝塔面板(若服务器装了宝塔)**:`/www/server/nginx/conf`、`/www/wwwroot`、`/www/server/panel/data` —— 初次备份时容易完全漏掉
- 数据:`~/vault`(知识库)+ `~/*.md`

## 迁移四步
1. 旧机跑 backup_all.sh → `scp -r root@<旧IP>:~/backup/ .` 下载到本地
2. 新机:Ubuntu 22.04(同版本)→ 官方安装 Hermes → 解包恢复:
   ```
   tar xzf hermes-dotdir.tar.gz -C ~/.hermes/   # 覆盖前先备份新装 .hermes
   tar xzf hermes-agent-code.tar.gz -C /usr/local/lib/hermes-agent/
   cp -r systemd/* /etc/systemd/system/ && systemctl daemon-reload
   ```
3. IP 变化必改:UFW+安全组放行 22/22000(Syncthing)/9119(dashboard);Syncthing 手机/电脑端设备地址改新 IP;机场订阅若过期重新下载覆盖 clash 配置
4. 启动验证:`systemctl enable --now hermes-gateway hermes-dashboard clash syncthing bing-search-bridge`、`hermes doctor`、微信发消息测试

## 关键保证
- 微信 **无需重新扫码配对**:platforms/pairing/weixin-approved.json 已随备份恢复
- 记忆/技能/会话随 dotdir 恢复,"我"还是同一个
- vault 双保险:备份包 + Syncthing 三端同步

## 自动化备份 cron(已配置)
- 每周日 3:00:no_agent + wrapper(`weekly_backup.sh`),成功静默、失败推微信告警;脚本保留最近 4 份
- 每月 1 号 9:00:agent 模式 + `monthly_backup_send.sh`(备份→打包单 tar.gz→最终回复带 `MEDIA:/path` 把备份包发到微信),服务器保留最近 2 个月度包
- 迁移手册文档:vault/entities/server-migration.md(知识库三端可见)

## Windows 迁移包(`pack_windows_migration.sh`,按需生成)
- 内容:memories/、skills/、SOUL.md、state.db + sessions/、api-keys.txt(仅 DeepSeek/Notion,不含微信)、README-Windows.md
- **刻意排除**:config.yaml(不能覆盖,Windows 配置不同)、微信凭据(同一 iLink 账号两端 gateway 会冲突)、Linux 专属(systemd/clash/weixin.py 补丁)
- 用法:用户把 zip 放 Windows,给 Windows 端 Hermes 粘贴**自包含提示词**(解压 → 备份 .hermes → 复制 memories/skills/SOUL/state.db → 追加 api-keys 到 .env → 验证 session_search)。提示词要点:禁止覆盖 config.yaml、跳过 *.lock、同名 key 跳过
- vault 不用迁移包:Syncthing 已三端同步

## 坑与经验
- **backup 脚本不要用 `set -e`**:某步失败(cp 到不存在目录)会静默中断,后续 README 都不生成。改为分步 `|| true` / 显式判断,先 mkdir -p。
- **备份前先"体检"**:宝塔面板/nginx 这类可能"装了没用"——先查站点是否为空(/www/wwwroot 空、vhost 无自定义站点、面板 db 仅默认库)再决定备不备。空壳只备 nginx 配置防万一,别打包整个面板 data(本机实测宝塔为空,仅备 nginx conf)。
- **微信发备份包依赖 weixin.py 上传补丁**:文件经微信 CDN 上传(curl 子进程补丁),补丁失效则月度备份发不出。
- **技能来源判定**:`~/.hermes/skills/.bundled_manifest`(name:hash 每行)= 出厂内置清单;沉淀技能 = 全量 - 内置(再排除 .archive)。生成能力目录/统计沉淀时用此法,勿用 `list_agent_created_skill_names()`(prune_builtins 开启时会把内置也算进去)。
- **知识库自动化编排时间表**(本部署):20:00 用户习惯整理(agent cron,提取当天对话)→ 23:00 知识库整理 → 23:30 三目录更新(`skills_inventory.py`/`kb_inventory.py`/`cron_inventory.py`,生成 vault/entities/skills-inventory.md、kb-inventory.md、cron-inventory.md,no_agent 静默成功/失败告警)→ 每周日 3:00 备份 → 每月 1 日 9:00 备份发微信。
- **三目录脚本要点**:统一 wrapper(`skills_inventory_wrapper.sh`)串三个 py,每晚 23:30 一次跑完;skills-inventory 区分"沉淀技能 vs 内置"(读 `.bundled_manifest`,沉淀放 ⭐ 区表格);kb-inventory 排除 raw/.obsidian/.stfolder/.stversions;cron-inventory 读 `~/.hermes/cron/jobs.json`(dict 含 jobs 列表,字段 id/name/schedule/state/enabled)。
- **用户习惯整理机制**:每晚 20:00 agent cron + `daily_chat_extract.py`,更新 `~/用户习惯观察.md`(候选池,【已确认】/【观察中】两档)并推送微信;**用户确认后**才把条目写入 `vault/entities/user-profile.md`(SOUL.md 素材库)—— 用户明确要求沉淀路径是 Obsidian 文档而非 Hermes 长期记忆(长期记忆维持原机制);是否更新知识库/生成 SOUL.md 均由用户拍板。
