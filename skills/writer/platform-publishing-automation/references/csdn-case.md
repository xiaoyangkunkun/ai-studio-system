---
title: "CSDN 案例(2026-08-15 实测跑通,首篇文章已发布)"
created: 2026-08-20
updated: 2026-08-20
type: note
---
# CSDN 案例(2026-08-15 实测跑通,首篇文章已发布)

## 关键值(从官方前端 bundle 逆向,2026-08-15 抓取)

- 发布端点:`POST https://bizapi.csdn.net/blog-console-api/v3/mdeditor/saveArticle`(旧编辑器)
- 备选端点:`/blog-console-api/v1/postedit/saveArticle`(新创作中心)
- X-Ca-Key = `203803574`(硬编码在官方 JS)
- appSecret = `9znpamsyl2c7cdrr9sas0le9vbc3r6ba`
- 来源 bundle:csdnimg.cn 的 mp_v3 主 JS 与 editor 主 JS(前端更新后需重新抓取)

## 阿里云网关签名(stringToSign)

```
METHOD + "\n" + Accept + "\n" + (空 Content-MD5) + "\n" + Content-Type + "\n" + (空 date) + "\n"
+ "x-ca-key:<key>\n" + "x-ca-nonce:<uuid>\n" + 去域名后的 URL path
signature = Base64(HMAC-SHA256(stringToSign, appSecret))
```

Header: `Cookie`(登录态)、`Accept: */*`、`Content-Type: application/json;charset=UTF-8`、`X-Ca-Key`、`X-Ca-Nonce`(uuid)、`X-Ca-Signature`、`X-Ca-Signature-Headers: x-ca-key,x-ca-nonce`

## saveArticle body(草稿/发布通用)

```json
{"id": "", "title": "标题", "markdowncontent": "# md原文", "content": "<p>HTML</p>",
 "readType": "public", "level": 0, "tags": "AI,大模型", "status": 2,
 "type": "original", "categories": "", "Description": "", "source": "pc_mdeditor",
 "is_new": 1, "pubStatus": "draft"}
```

- draft:`pubStatus=draft` + `status=2`;publish:`pubStatus=publish` + `status=0`
- `id` 传草稿 ID = 更新已有;不传 = 新建
- 成功返回:`{"code":200, "msg":"success", "data":{"id":..., "url":...}}`
- 错误:`请登录后操作!`(401)= cookie 过期;`400300011` = 今日发布达上限(约 10 篇/日)

## 登录(cookie)要点

- 一体化单进程脚本:playwright headless + 真实 UA + 隐藏 webdriver 的 init_script
- 等 `.login-code-wechat img` 的 src 变 `data:image` 开头,再 base64 解码存图(容器出现 ≠ 内容画好)
- 登录检测:URL 离开 `passport.csdn.net` 且连续 3 次轮询稳定,才存 cookie
- 二维码 1-2 分钟过期;cookie 有效期数周~数月

## 其他入口实测

- `editor.csdn.net/md/`:登录态下浏览器访问 403(openresty WAF 拦自动化指纹);curl 带 UA 200
- `mp.csdn.net/mp_blog/creation/editor`:200,普通请求不被拦
- `blog.csdn.net/nav/write`:521 不可用
- `api.csdn.net` / `open.csdn.net`:已死(开放平台废弃)
- mermaid 发布页不渲染(编辑器预览正常,发布后显示代码);内嵌 HTML 服务端零过滤可用但移动端突兀

## 排版规范(CSDN 实测渲染能力)

- ✅ 编号 h2/h3 标题(侧边目录自动)、代码块语言标记+文件名注释、表格对齐、引用块、emoji、KaTeX
- ❌ mermaid(截图上传代替)
- 段落 50-150 字;坑用 `> ⚠️` 引用块;关键结论加粗
