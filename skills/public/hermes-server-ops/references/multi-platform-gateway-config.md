# 多平台 Gateway 配置备忘

## 语言控制:display.personality

config.yaml 中 `display.personality` 会作为系统提示词注入所有平台的对话:

```yaml
display:
  personality: "你用中文回复所有消息，简洁直接，不废话。"
```

不设此项时模型可能用英文回复(尤其是 MiMo 等模型)。设置后所有平台(微信/QQ/webhook)生效。

优先级: `HERMES_EPHEMERAL_SYSTEM_PROMPT` 环境变量 > `display.personality` > `agent.system_prompt`

## Home Channel 配置

每个平台可以设 home channel,cron 结果和跨平台消息会推送到这里:

```yaml
gateway:
  platforms:
    qqbot:
      home_channel: "070F2C85C507AF3AE3EBDB282C342F36"  # QQ 用户 ID
    weixin:
      home_channel: "{{WEIXIN_CHAT_ID}}"  # 微信用户 ID
```

⚠️ 配置路径是 `gateway.platforms.<platform>.home_channel`,不是 `home_channel.<platform>`。错误路径 `hermes config set home_channel.qqbot xxx` 会写入 config 但 gateway 不读。

查看已配对用户 ID: `hermes pairing list`

## 平台策略配置

`dm_policy` / `group_policy` 控制谁可以和 bot 对话:

| 值 | 行为 |
|---|---|
| `open` | 任何人可对话(需同时设 `GATEWAY_ALLOW_ALL_USERS=true` 或 `QQ_ALLOW_ALL_USERS=true`,否则 gateway 拒绝启动) |
| `pairing` | 新用户发消息触发配对请求,管理员 approve 后才可对话(推荐) |
| `allowlist` | 仅白名单用户可对话 |
| `disabled` | 禁用此入口 |

⚠️ **open policy 必须配合 allow-all 环境变量**:qqbot 配了 `dm_policy: open` 但没设 `GATEWAY_ALLOW_ALL_USERS` → gateway 拒绝启动,日志: `ERROR gateway.run: Refusing to start: qqbot has dm_policy/group_policy set to 'open' but neither GATEWAY_ALLOW_ALL_USERS nor QQ_ALLOW_ALL_USERS is enabled`

## 多平台会话隔离

各平台的聊天记录独立(不同 session key),但共享:
- memory/user profile
- 模型/API key
- 技能/知识库
- 定时任务

同时在多个平台对话不会冲突,但模型是串行处理的,一边跑长任务时另一边会排队。

## 平台内存开销

每个平台适配器是 gateway 单进程内的模块(非独立进程),内存开销极小(~1-2MB 连接状态)。三个平台(微信+QQ+webhook)总开销 <5MB,对 1.6G 服务器无压力。真正的内存大头是 LLM 推理会话和 MCP server。
