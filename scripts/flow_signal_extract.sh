#!/usr/bin/env bash
# 流程推荐信号提取(wrapper):扫描上周 cron 输出/失败记录/文档滞后,输出结构化信号
# 背景:2026-08-14 知远调研产出;script 字段只能纯名,参数写死在 wrapper 内
cd ~/.hermes/scripts
python3 flow_signal_extract.py
