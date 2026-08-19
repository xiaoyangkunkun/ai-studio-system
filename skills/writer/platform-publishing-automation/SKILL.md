---
name: platform-publishing-automation
description: Use when 自动发布到无官方API平台。逆向前端JS找内部接口直调,绕开浏览器WAF。
---

# 内容平台发布自动化(内部 API 直调法)

> 2026-08-15 在 CSDN 上完整跑通并发布首篇文章。适用:目标平台没有官方写作 API,但有网页编辑器(内部保存接口必存在)。

## 核心原则(老大定的规矩,必须遵守)

1. **先调研再动手**:落地类任务禁止直接埋头试错。先派调研员(知远)逆向根因/找现成方案,拿到可落地结论再实施。CSDN 案例:直接部署现成 MCP 踩坑 7+ 轮(全是浏览器 WAF 问题),调研逆向出 API 后一次成功。
2. **能 API 直调就不要浏览器模拟**:浏览器自动化(headless/Selenium/Playwright)会被平台 WAF 按指纹拦截(CSDN 实测:editor.csdn.net 登录态 403,伪装 webdriver 只能过无登录态);纯 HTTP 直调内部 API 无浏览器、无 WAF 可拦、内存零负担。
3. **人工触发,不自动发布**:固定时间/固定频率会被风控识别为自动化。发布间隔不规律、频率克制(参考:每日 ≤10 篇),由用户掌控时机。
4. **交付「从零搭建手册」**:机制落地后交付可复刻文档(完整代码/命令/踩坑速查,换台机器照着 30-60 分钟能重建),不只流程记录。用户已将此设为长期交付标准(画像第 34 条)。

## 标准流程

1. **调研阶段(派知远,~10 分钟)**:
   - 逆向官方前端 bundle:web_extract 抓编辑器页引用的主 JS(如 csdnimg.cn 的 bundle),搜索保存/发布接口端点 + 签名参数(X-Ca-Key/appSecret 常硬编码在 JS 里)
   - 找发布端点(如 `bizapi.csdn.net/blog-console-api/v3/mdeditor/saveArticle`)+ body 结构(从 editor 源码的 save 函数提取)
   - 对比现成工具(GitHub star/更新时间/维护状态),但先确认其技术栈是否撞 WAF
   - 实测替代入口(不同域名可能 WAF 策略不同)
2. **登录凭证(一次性,~10 分钟)**:扫码登录一体化脚本(单进程!):
   - 生成二维码 → 等 img src 变 `data:image` 再解码存图(容器出现 ≠ 内容画好)
   - 严格登录检测:URL 离开 passport 域且连续 3 次稳定,再存 cookie
   - cookie 落盘(权限 600),后续发布器读取;数周~数月过期后重扫
3. **发布器(纯 Python,无浏览器)**:requests/urllib 直调 + 网关签名(见 references/csdn-case.md 的阿里云网关 stringToSign 格式),draft/publish 由 body 字段控制(如 `pubStatus` + `status`)
4. **验证闭环**:存草稿 → 平台后台审核 → 按草稿 ID 更新为发布(发布器传 id 参数,避免新建重复)
5. **交付**:流程文档(怎么用)+ 从零搭建手册(怎么复刻)+ 技能/脚本沉淀

## 踩坑速查(CSDN 实测)

| 现象 | 原因 | 解决 |
|---|---|---|
| 编辑器域名 403(openresty) | WAF 拦自动化浏览器指纹 | 弃浏览器方案,API 直调 |
| 二维码图片空白 | 截图太早(loading 态,img src 为空) | 等 src 变 data:image 再解码 |
| 登录确认"请先运行 csdn_login" | 多次 python -c 独立进程,状态不共享 | 一体化单进程脚本 |
| cookie 永远无效 | cookie 路径写死作者本机路径 | 改为部署机本地路径 |
| 网关签名不过 | stringToSign 拼接错 | 严格按 METHOD\nAccept\n空\nContent-Type\n空\nx-ca-key\nx-ca-nonce\npath |
| cookie 过期 | 数周~数月 | 重跑扫码脚本 |

## 支持文件

- `references/csdn-case.md` — CSDN 完整案例:端点、签名参数值、body 字段、登录脚本要点、实测坑
- `templates/csdn_publish.py` — 发布器模板(复制即用,可改造为其他平台)

## 相关

- CSDN 专属技能:`csdn-blog-automation`(员工创建,含 CSDN 排版规范)
- 完整手册:vault/流程/CSDN博客自动发布-从零搭建手册.md
- 文章 md 目录:vault/博客/<专栏>/
