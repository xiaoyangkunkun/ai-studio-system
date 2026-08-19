# 海外 API 地区封锁与 Clash 域名级节点分流(CN 服务器实战)

> 案例:Groq(2026-08-15 实测)。通用模式:海外 API 被 Cloudflare/WAF 按地区封锁时,给 Clash 加域名级规则固定到放行地区节点,其他流量不动。

## Groq 封锁特征

- **现象**:`console.groq.com` 与 `api.groq.com` 从大陆直连、香港节点走代理,均返回 **HTTP 403**,响应 ~0.1-0.2s;美国节点 → 200
- **判断口诀**:403 + 毫秒级响应 = 网络通、被 WAF 地区拒绝(不是 DNS/连接问题);若 timeout/000 才是连不通
- **必须带 key 测**:`curl -x http://127.0.0.1:7890 https://api.groq.com/openai/v1/models -H "Authorization: Bearer <key>"`——不带 key 的 403/401 无法区分"认证拒绝"和"地区封锁",带 key 才可信
- 封锁范围是**地区级**不是国别级:香港节点也被拒,只有美国 IP 通。用户注册也要美国节点(香港/日本节点大概率注册页也 403)

## Clash 域名级分流(不全局切节点)

1. 改 `/etc/clash/config.yaml` 的 `rules:` 段**顶部**加一行(出口直接用真实节点名,不经过选择器):
   ```yaml
   - DOMAIN-SUFFIX,groq.com,🇺🇲 美国W01 | IEPL | x1.5
   ```
2. 热加载:`curl -s -X PUT http://127.0.0.1:9090/configs -d '{"path":"/etc/clash/config.yaml"}'`(HTTP 204)
3. 选择器节点切回:`curl -s -X PUT http://127.0.0.1:9090/proxies/%F0%9F%94%B0%20%E9%80%89%E6%8B%A9%E8%8A%82%E7%82%B9 -d '{"name":"🇭🇰 香港W01"}'`(组名 URL 编码)
4. 验证分流:groq.com 走美国(200)、google.com 走香港(200)

## 踩坑

- **查实际出站节点看选择器组的 `now`**:部分订阅 GLOBAL 组显示 DIRECT,真实生效的是规则匹配的选择器组(如 `🔰 选择节点`)——`curl http://127.0.0.1:9090/proxies | jq` 看 type=Selector 且带 `now` 的组
- **patch 工具拒改 `/etc/clash/config.yaml`**(敏感系统路径)→ 用 python 脚本改(先 `cp` 备份,正则定位 `rules:` 行后插入)
- 节点名带 emoji/竖线,脚本里用 Unicode 转义(`\U0001F1FA\U0001F1F2`)或从 proxies API 读真实名
- 订阅节点列表:同一 proxies API 里 type in (Shadowsocks/Vmess/Trojan/Hysteria2) 的条目,按名称找美国/香港/日本节点

## 其他地区封锁 API 的处理顺序

1. 先查官方 docs/status 确认支持地区(别猜)
2. curl 带 key 从直连/香港/美国三路实测(快,一次搞定)
3. 确定放行地区 → Clash 加 DOMAIN-SUFFIX 规则(可多个域名共用一行一条)
4. 测其他流量不受影响(google/hf 仍走原节点)

## Hermes stt.groq 落地要点(同案例,2026-08-15)

- `GROQ_API_KEY` 入 `.env`;stt 自动检测优先级 local(faster-whisper)→ groq → openai,Hermes 原生支持
- 模型用 `whisper-large-v3-turbo`(Groq 有 large-v3 和 turbo 两个)
- **中文输出默认繁体**(whisper 老毛病),prompt 参数对繁简不可靠 → 补丁在 `_transcribe_groq()` 的 `transcript_text` 后接 opencc t2s 转换:
  ```python
  try:
      from opencc import OpenCC
      transcript_text = OpenCC("t2s").convert(transcript_text)
  except Exception:
      pass
  ```
  依赖 `pip install opencc-python-reimplemented`;补丁备份 `~/backup/stt-groq-simplified-chinese.patch`(Hermes 升级覆盖后照着重打)
- 免费档限额(dev 档):约 20 RPM / 2K RPD / 7.2K 秒音频每小时(≈8 小时音频/天,微信语音场景充裕)
- 本地 faster-whisper 在 2G 服务器上按需加载 ~0.4-0.5G 内存,转写瞬间有 OOM 风险 → 云端 API 优先,本地只做断网应急(tiny/base 模型)
