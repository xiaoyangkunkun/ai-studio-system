# Syncthing 三端同步(Obsidian 知识库)实操经验

场景:Obsidian vault 在 服务器/安卓手机/Windows 三端通过 Syncthing 双向同步。本文件记录实测踩坑(2026-08 验证)。

## 架构
- 服务器:systemd 服务 `syncthing`(root),监听 `*:22000`(公网,UFW+安全组放行),Web UI `127.0.0.1:8384`(仅本机)
- API key 在 `~/.config/syncthing/config.xml`(`<apikey>` 标签),所有 REST 调用带 `-H "X-API-Key: $KEY"`
- 常用 API:`/rest/system/connections`(设备连接)、`/rest/config/folders/{id}`(GET/PUT/DELETE)、`/rest/db/status?folder={id}`、`/rest/events?since=0`(事件流)

## 坑 1:全局发现服务国内不可达
`discovery.syncthing.net` 在阿里云/国内网络连不上(HTTP 000)。服务器对远端设备的地址配成 `dynamic`(靠发现服务)时**永远找不到设备**。
→ 解决:远端设备(手机/电脑)必须配置服务器的**静态地址** `tcp://<公网IP>:22000` 并主动连服务器。任何一端能连上,双向就通。

## 坑 2:文件夹 ID 必须三端一致(最常踩)
Syncthing 靠 folder ID 匹配文件夹,**label/名称随意,ID 必须一致**。Syncthing-Fork(安卓)新建文件夹时 ID **自动生成短 ID**(如 `n898e-75gqg`),用户往往只改 label 和路径,ID 没改 → 服务器端永远收不到同步(FolderRejected 事件)。
- 诊断:events 里出现 `FolderRejected {folder: 'xxx'}` = 该 ID 服务器端不存在
- 方案 A(首选):指导用户把手机端"文件夹 ID"字段手动改成服务器的 ID(该字段可编辑,不是只读)
- 方案 B(用户改不了时):服务器端迁就手机 —— API 改文件夹 ID:
  ```
  GET  /rest/config/folders/vault        # 拿完整配置
  # 修改 JSON 的 id 字段为手机端的短 ID
  PUT  /rest/config/folders/<新ID>       # 提交(200)
  DELETE /rest/config/folders/vault      # 删除旧 ID 配置,避免同路径双文件夹
  ```
  改 ID 后 Syncthing 会把数据当新文件夹重建索引,文件不丢。

## 坑 3:版本控制类型名是 trashcan
配置 File Versioning(回收站)时,`"type": "recycleBin"` 会 500(`requested versioning type "recycleBin" does not exist`)。正确:
```json
"versioning": {"type": "trashcan", "params": {"cleanoutDays": "14"}}
```
删除行为:sendreceive 双向同步下,**任一端的删除会传播到所有端**(保持一致性);trashcan 保护:被删/被覆盖文件进 `.stversions/` 保留 N 天可恢复。建议三端都配,防误删。

## 升级:apt 包太旧,手动换二进制
Debian/Ubuntu apt 的 syncthing 可能停在 v1.18(2024)。最新版从 GitHub releases 拿:
```
# 先查最新 tag(走代理):https://api.github.com/repos/syncthing/syncthing/releases/latest
systemctl stop syncthing        # 必须停,否则 cp 报 Text file busy
cp syncthing-linux-amd64-v2.x.x/syncthing /usr/bin/syncthing
systemctl start syncthing       # 旧 config.xml 自动迁移,设备/文件夹配置保留
```
v2 与旧版协议兼容,升级后手机端(v2.x)连接更稳定。

## 故障排查顺序
1. `rest/system/connections` → 看 connected 状态和 address
2. `rest/events?since=0` → DeviceConnected/Disconnected/FolderRejected/FolderCompletion
3. `rest/db/status?folder=X` → state/globalFiles/localFiles/needFiles(needFiles>0 表示有文件待同步)
4. 公网可达性:服务器上 `timeout 8 bash -c 'echo > /dev/tcp/<公网IP>/22000'`(先 `env -u HTTP_PROXY ...` 绕过代理环境变量,否则测到的是代理)

## 本部署最终配置
- vault:folder id=`vault`(曾短暂改成短 ID 又改回),路径服务器 `~/vault`、手机 `/storage/emulated/0/vault`
- 设备:服务器(MSH2X76...)、手机 Android(BOU5BQA...)、Windows(7XWAT4S...)
- 版本控制:三端 trashcan 14 天
- 完整配置文档:vault/entities/syncthing-config.md(三端同步共享,任何 Hermes 实例可读)
