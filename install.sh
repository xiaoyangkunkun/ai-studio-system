#!/bin/bash
# 兼容入口，实际调用 deploy.sh
exec bash "$(dirname "$0")/deploy.sh" "$@"
