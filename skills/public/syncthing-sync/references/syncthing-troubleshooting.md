# Syncthing 故障排查实录(2026-08 实测)

## 场景:手机端显示"已断开连接",服务器 0 设备在线

### 环境
- 阿里云 ECS(2C2G),Ubuntu 22.04,公网 {{SERVER_IP}}
- 服务器 Syncthing v1.18.0(apt 包,2024)→ 升级 v2.1.3(GitHub 最新)
- 手机:Syncthing 安卓版 v2.1.3;另有 Windows 设备
- 服务器注入 Clash 代理(HTTP 7890)

### 排查顺序与发现
1. **端口可达性**:UFW 已放行 22000;`env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY bash -c 'echo > /dev/tcp/{{SERVER_IP}}/22000'` → 通(注意:当前终端有代理环境变量,curl/测试必须 `env -u` 绕过,否则连到 7890)
2. **配置检查**:`GET /rest/config/devices` → 手机/Windows paused=False, addresses=['dynamic'](正常)
3. **事件日志**:`GET /rest/events` → `DeviceDisconnected {'error': 'read timeout', 'id': '7XWAT4S...'}` → 连接能建立但不稳定(小带宽)
4. **发现服务**:`curl https://discovery.syncthing.net/` → HTTP 000(不可达)→ **服务器全局发现失效,永远找不到手机**;必须手机主动连服务器(静态地址)
5. **版本**:v1.18 太老 → 升级 v2.1.3

### 文件夹 ID 不匹配(核心坑)
- 服务器端:folder id=`vault`,path=~/vault
- 手机端新建文件夹:label 可改名,但 **ID 自动生成短 ID**(`n898e-75gqg`),用户重建多次仍是短 ID
- 服务器事件:`FolderRejected {'device': 'BOU5BQA...', 'folder': 'n898e-75gqg'}` + `PendingFoldersChanged added`
- 解决(服务器迁就版):GET vault 配置 → 改 id → PUT /rest/config/folders/n898e-75gqg → DELETE /rest/config/folders/vault(⚠️ 不删旧的会两个文件夹同路径冲突)
- 解决(客户端适配版,用户偏好):手机端编辑文件夹 → **"文件夹 ID" 字段可手动输入**(在"文件夹标签"下面)→ 改成 `vault`

### 恢复服务器端(用户要求保持服务器配置稳定)
- GET /rest/config/folders/n898e-75gqg → 改 id=vault → PUT /rest/config/folders/vault → DELETE /rest/config/folders/n898e-75gqg
- 验证:`GET /rest/config/folders` 只剩 default + vault;`db/status?folder=vault` 数据完好(global/local 一致)

### 验证成功的判定
```bash
# 设备连接
curl -s -H "X-API-Key: $KEY" http://127.0.0.1:8384/rest/system/connections
# 文件夹同步
curl -s -H "X-API-Key: $KEY" "http://127.0.0.1:8384/rest/db/status?folder=vault"
# 手机端完成度(同步成功标志)
curl -s -H "X-API-Key: $KEY" "http://127.0.0.1:8384/rest/db/completion?folder=vault&device=<手机ID>"  # completion=100
```

## 其他要点
- 升级时 `cp: cannot create regular file '/usr/bin/syncthing': Text file busy` → 先 `systemctl stop syncthing`
- 服务名确认:`systemctl is-active syncthing`(不是 syncthing@root)
- 配置目录:~/.config/syncthing/config.xml(apikey、devices、folders 都在此)
- 证书有效期 2046,时间同步正常(NTP active),排除时钟/证书因素
- 手机端 Syncthing 需前台运行,安卓后台易被杀
