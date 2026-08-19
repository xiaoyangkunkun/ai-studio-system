# Proactive delivery to messaging platforms (verified on Weixin/WeChat)

Goal: Hermes initiates messages instead of only replying. Two mechanisms, both verified end-to-end on the weixin platform.

## One-off: `hermes send`

- `hermes send --list` shows available targets (e.g. `weixin:{{WEIXIN_CHAT_ID}} (dm)`); bare platform name = home channel.
- `hermes send -t weixin:<user_id> "text"` → `Sent to weixin home channel (chat_id: …)`. No agent/LLM involved; uses the gateway's stored credentials.

## Scheduled: cron jobs

- CLI: `hermes cron create '<schedule>' '<self-contained prompt>' --name <n> --deliver weixin:<user_id>` (deliver formats: `origin`, `local`, `telegram`, `discord`, `signal`, or `platform:chat_id`).
- cronjob tool: `action=create` with `deliver='weixin:<user_id>'`; `repeat=1` for one-shot tests.
- Agent jobs: the prompt must be FULLY self-contained (fresh session, no chat context). Instruct `curl --max-time 10`, say "state clearly when a fetch failed, never invent content", and "output the deliverable only". Runs are hard-interrupted at 3 minutes.
- no_agent watchdog jobs: the script IS the job. Non-empty stdout is delivered verbatim; EMPTY stdout = silent — the classic "only message when something is wrong" pattern. Zero tokens.
  - **Pitfall: `script` must be a path RELATIVE to `~/.hermes/scripts/`** (e.g. `server_watch.sh`). Absolute or `~`-relative paths are rejected with `Script path must be relative to ~/.hermes/scripts/`.
- Verify before relying on a recurring job: fire a one-shot test (`schedule='2m'`, `repeat=1`), then check `hermes cron list` / cronjob `action=list` → `last_status: ok`, `last_delivery_error: null`, `state: completed`. Delivery to a gateway platform works even when the job was created from a CLI-only session (deliver targets the gateway-connected platform, not the origin terminal).

## Watchdog script pattern (server health)

- Accumulate `ALERTS` from awk over `free -m`, `df -m /`, `/proc/loadavg`; echo only when non-empty; `LC_ALL=C` for locale-safe parsing.
- Example thresholds (2-core box): mem ≥90%, root disk ≥85%, 1-min load > 4.0.
- Known-good deployed example: `~/.hermes/scripts/server_watch.sh`.

## Ordering gotcha

Messages sent to the bot BEFORE its pending pairing request is approved are dropped. Order: approve pairing (`hermes pairing approve weixin <request-id>`) → then user re-sends → then verify via `journalctl -u hermes-gateway` (`response ready: platform=weixin …` in `~/.hermes/logs/agent.log` confirms the reply was dispatched).
