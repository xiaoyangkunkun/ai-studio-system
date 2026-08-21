---
title: "Weixin CDN TLS-fingerprint block — full debugging path & patches"
created: 2026-08-20
updated: 2026-08-20
type: note
---
# Weixin CDN TLS-fingerprint block — full debugging path & patches

Verified 2026-08-11 on an Aliyun ECS running Hermes gateway (personal WeChat via iLink).

## Symptom timeline (what you will see)

1. User sends a file (PDF/image) to the bot via WeChat.
2. Gateway log shows the DOWNLOAD failing:
   `gateway.platforms.weixin: file download failed: Cannot connect to host novac2c.cdn.weixin.qq.com:443 [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE]`
3. User asks "did you get my PDF?" — nothing arrived.
4. If you fix only downloads, SENDING a file back fails identically:
   `send_document failed to=...: Cannot connect to host novac2c.cdn.weixin.qq.com:443 [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE]`
   (upload path: `_upload_ciphertext` POSTs encrypted media to the same CDN)

## Root cause

WeChat CDN (novac2c.cdn.weixin.qq.com) rejects Python's TLS ClientHello fingerprint (JA3-style detection). aiohttp AND urllib fail even on a DIRECT connection; curl succeeds. NOT a proxy problem, NOT a certificate problem — a TLS-fingerprint block on Python's OpenSSL ClientHello.

## Diagnostics (30 seconds)

```bash
# 1. Network path fine? (fast 4xx = reachable)
curl -s --max-time 8 -o /dev/null -w "%{http_code}\n" https://novac2c.cdn.weixin.qq.com/

# 2. Python TLS fingerprint blocked? (FAIL = confirmed)
venv/bin/python -c "import urllib.request; urllib.request.urlopen('https://novac2c.cdn.weixin.qq.com/', timeout=8)"

# Run #2 both with and without HTTPS_PROXY to rule the proxy out entirely:
#   direct:  env -u HTTPS_PROXY -u HTTP_PROXY -u ALL_PROXY venv/bin/python -c ...
#   proxied: HTTPS_PROXY=http://127.0.0.1:7890 ... (same FAIL expected)
```
curl OK + Python FAIL (in both proxy modes) ⇒ TLS-fingerprint block. TLS 1.2/1.3 pinning does NOT help — only changing the client (curl) works.

## Patch — /usr/local/lib/hermes-agent/gateway/platforms/weixin.py

Two functions, both switch to a curl subprocess with aiohttp fallback:

### 1) `_download_bytes` (downloads)

```python
async def _do_download() -> bytes:
    try:
        proc = await asyncio.create_subprocess_exec(
            "curl", "-sS", "-L", "--http1.1", "--retry", "3", "--retry-all-errors",
            "--max-time", str(max(1, int(timeout_seconds))),
            "-A", "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            url,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"curl download failed ({proc.returncode}): {stderr.decode(errors='replace')[:200]}")
        return stdout
    except FileNotFoundError:
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.read()
```

### 2) `_upload_ciphertext` (uploads)

```python
async def _do_upload() -> str:
    try:
        proc = await asyncio.create_subprocess_exec(
            "curl", "-sS", "-f", "-X", "POST", "--http1.1",
            "--retry", "3", "--retry-all-errors", "--max-time", "120",
            "-H", "Content-Type: application/octet-stream",
            "--data-binary", "@-", "-D", "-", "-o", "-",
            upload_url,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate(ciphertext)
        if proc.returncode != 0:
            raise RuntimeError(f"curl upload failed ({proc.returncode}): {stderr.decode(errors='replace')[:200]}")
        # WeChat CDN may OMIT the trailing blank line after headers —
        # partition(b"\r\n\r\n") fails; scan raw stdout with regex instead.
        match = re.search(rb"(?im)^x-encrypted-param:\s*([^\r\n]+)", stdout)
        if match:
            return match.group(1).decode(errors="replace").strip()
        raise RuntimeError(f"CDN upload missing x-encrypted-param header: {stdout[:200]}")
    except FileNotFoundError:
        async with session.post(upload_url, data=ciphertext, headers={"Content-Type": "application/octet-stream"}) as response:
            if response.status == 200:
                encrypted_param = response.headers.get("x-encrypted-param")
                if encrypted_param:
                    await response.read()
                    return encrypted_param
                raw = await response.text()
                raise RuntimeError(f"CDN upload missing x-encrypted-param header: {raw[:200]}")
            raw = await response.text()
            raise RuntimeError(f"CDN upload HTTP {response.status}: {raw[:200]}")
```

## Pitfalls hit during this fix (all real, all cost a round-trip)

1. **First curl attempt used HTTP/2** → `curl download failed (92): HTTP/2 stream 1 was not closed cleanly` — WeChat CDN's HTTP/2 handling is flaky for downloads. Pin `--http1.1`. (Root-path probes pass on both versions; the 92 only shows on real file streams.)
2. **Upload response parsing**: first version split with `partition(b"\r\n\r\n")` — failed against the real CDN (no trailing blank line), error showed the whole response as "body". Fixed by regex over raw stdout; verified against BOTH a standard server and the CDN-style header block.
3. **curl `-f` flag**: needed so non-2xx fails the subprocess (curl exits 0 on HTTP errors otherwise).
4. **Sanity check before restart**: `py_compile` the file, and unit-test the upload parser against a local mock server (python http.server returning an `x-encrypted-param` header) before scheduling the gateway restart.

## Verification after restart

- Ask the user to re-send the file → gateway log shows successful media handling, file appears under `~/.hermes/cache/documents/`.
- Ask the agent to send a file back (e.g. a markdown doc) → `[Weixin] Delivering 1 non-image MEDIA attachment(s)` with no error line.

## Defense in depth (proxy bypass, still worth having)

Even with the curl patch, keep WeChat CDN traffic out of the Clash proxy:
- Clash rules: `DOMAIN-SUFFIX,weixin.qq.com / wx.qq.com / qlogo.cn / qpic.cn → 🇨🇳 国内网站 (direct)`
- gateway drop-in NO_PROXY: append `.weixin.qq.com,.wechat.com,.weixin.com,.qlogo.cn,.qpic.cn,.wx.qq.com`

## Upgrade survival

`hermes-agent` upgrades overwrite `gateway/platforms/weixin.py`. After every upgrade: re-apply both patches, `py_compile`, and restart the gateway (see SKILL.md "Restarting the gateway" for the atd pattern when the user is not at a shell).
