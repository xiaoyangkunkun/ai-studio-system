# Weixin (personal WeChat) adapter — iLink Bot API

Hermes ships a NATIVE personal-WeChat adapter (`gateway/platforms/weixin.py`) backed by Tencent's official iLink Bot API. Long-polling transport — no public endpoint, webhook, or extra port required. Distinct from WeCom (企业微信), which is the enterprise adapter.

The `@tencent-weixin/openclaw-weixin-cli` npm package the user may mention is an OpenClaw-only installer (`weixin-installer` bin, writes into `~/.openclaw`). Hermes does not need it — native support already exists.

## Setup flow

1. Deps: `aiohttp` + `cryptography` in the Hermes venv (usually already present; verify with `venv/bin/python -c "import aiohttp, cryptography"`).
2. `hermes gateway setup` → select "Weixin / WeChat" → answer "Start QR login now? [Y/n]" → wizard calls `ilink/bot/get_bot_qrcode`.
3. QR display: rendered in-terminal ONLY if the `qrcode` module is installed; otherwise the wizard prints a URL with the note `终端二维码渲染失败: No module named 'qrcode'，请直接打开上面的二维码链接`.
   - The URL looks like `https://liteapp.weixin.qq.com/q/<id>?qrcode=<hex>&bot_type=3` — it opens a page showing the scannable QR.
   - User opens the URL in any browser and scans with WeChat 扫一扫 (or screenshot → 扫一扫 → album), then confirms on the phone.
   - QR is time-limited; the wizard polls `ilink/bot/get_qrcode_status` and refreshes automatically — if it expires, just share the new URL.
4. Credentials auto-save to `~/.hermes/weixin/accounts/` and `WEIXIN_ACCOUNT_ID` (etc.) into `~/.hermes/.env`.
5. Start the gateway (`hermes gateway run`, or `hermes gateway install` for systemd) — the adapter restores credentials and long-polls.

## iLink bot identity limitations (IMPORTANT — set expectations early)

- QR login connects an iLink BOT identity (e.g. `a5ace6fd482e@im.bot`), NOT a fully scriptable ordinary personal account.
- DMs to the bot work reliably. Ordinary WeChat groups generally do NOT deliver events to iLink bot identities — `WEIXIN_GROUP_POLICY` may have no effect regardless of setting (gateway logs a WARNING at startup if it is anything but `disabled`).
- @-mentioning the personal account that scanned the QR is not the same as @-mentioning the bot — separate identities.
- Allowlist flow: have each user DM the bot, read their Weixin user IDs from gateway logs, add them to `WEIXIN_ALLOWED_USERS`, restart gateway.

## Env vars (~/.hermes/.env)

| Var | Meaning |
|---|---|
| `WEIXIN_ACCOUNT_ID` | required; auto-saved from QR login |
| `WEIXIN_TOKEN` | bot token; auto-saved |
| `WEIXIN_DM_POLICY` | `open` (default) / `allowlist` / `disabled` / `pairing` |
| `WEIXIN_ALLOWED_USERS` | comma-separated user IDs (inbound filter, not an invitation system) |
| `WEIXIN_GROUP_POLICY` | default `disabled` — see limitation above |
| `WEIXIN_GROUP_ALLOWED_USERS` | comma-separated GROUP IDs (despite the name) |
| `WEIXIN_HOME_CHANNEL` / `WEIXIN_HOME_CHANNEL_NAME` | cron/notification delivery target |
| `WEIXIN_SPLIT_MULTILINE_MESSAGES` | legacy multi-line splitting |

Config keys live in `config.yaml` under `platforms.weixin.extra` (same names + `base_url` default `https://ilinkai.weixin.qq.com`, `cdn_base_url` default `https://novac2c.cdn.weixin.qq.com/c2c`, `text_batch_delay_seconds` 3.0, `text_batch_split_delay_seconds` 5.0).

## DM pairing approval (wizard default)

The wizard asks "How should direct messages be authorized?" — default is "Use DM pairing approval (recommended)". With pairing enabled:

- The FIRST message from any new user is REJECTED: `WARNING gateway.run: Unauthorized user: <user_id> (…) on weixin` in `journalctl -u hermes-gateway` / `~/.hermes/logs/agent.log`.
- A pending request shows in `hermes pairing list` (platform `weixin`, request id, user id). Approve with `hermes pairing approve weixin <request-id>`; the user is then under "Approved Users" and "recognized automatically on their next message".
- A message sent BEFORE approval is dropped — after approving, have the user send a NEW message.
- If the gateway was never started, inbound messages are not processed at all (no pairing request appears either). Check `systemctl is-active hermes-gateway` before debugging anything else — this is the #1 "I messaged the bot and it didn't reply" cause right after a fresh wizard run.

## Gateway systemd service

`hermes gateway install --system` refuses as root; use `sudo hermes gateway install --system --run-as-user root` (auto-starts). Wizard prompts to start the gateway — answer `n` when installing the service separately.

## Gotchas

- Media moves through an AES-128-ECB encrypted CDN — handled transparently; requires `cryptography`.
- Reply continuity: `context_token` persisted per account+peer in `~/.hermes/weixin/accounts/<account_id>.context-tokens.json`.
- iLink server TLS verified against certifi bundle when available (adapter builds a certifi CA connector).
- Endpoints (useful for debugging): `ilink/bot/get_bot_qrcode`, `get_qrcode_status`, `getupdates`, `sendmessage`, `sendtyping`, `getuploadurl`.
