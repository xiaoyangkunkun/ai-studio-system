---
title: "任务：重构AI工作室产品包deploy.sh"
created: 2026-08-22
updated: 2026-08-22
type: note
---
# 任务：重构AI工作室产品包deploy.sh

## 背景
产品包位置：/root/vault/产品模板/
GitHub：xiaoyangkunkun/ai-studio-system

知远审计报告发现14个问题，需要重构deploy.sh。

## 问题清单

1. **Gateway重启逻辑双重错误** — `pkill -9 -f 'hermes.*run'` 会杀死systemd管理的gateway进程，导致两个进程竞争端口；验证命令 `ps aux | grep -q 'hermes.*gateway' | grep -v grep` 永远返回false
2. **config.yaml产生重复delegation段** — config-template.yaml已有delegation段，deploy.sh又追加一个
3. **.env值未加引号** — 如果API_KEY含特殊字符会断
4. **Cron无幂等性** — 重复部署产生重复任务
5. **Cron缺--deliver参数** — 用户收不到微信推送
6. **Skills部署到不存在的default profile** — 应该只部署到全局skills目录
7. **正则修复目标Python错误** — 应该检查venv Python而非系统Python
8. **tomllib shim的bytes/str错误** — loads(s)应该处理str→bytes转换
9. **XIAOMI_API_KEY硬编码** — 非小米用户会出错
10. **.env完全覆盖** — 丢失用户已有配置
11. **Python包安装位置不一致** — venv路径应该统一为/usr/local/lib/hermes-agent/venv
12. **Cron任务不完整** — 缺少晚间复盘、习惯整理等任务
13. **不检查SearXNG可用性** — web_search静默失败
14. **磁盘检查精度不足** — df -BG取整可能误判

## 要求
1. 尽量在一个脚本里
2. 解决所有14个问题
3. 输出重构后的完整deploy.sh代码
4. 代码清晰、可维护

## 当前deploy.sh位置
/root/vault/产品模板/deploy.sh

## 相关文件
- /root/vault/产品模板/config-template.yaml
- /root/vault/产品模板/env-template
- /root/vault/产品模板/precheck.sh
