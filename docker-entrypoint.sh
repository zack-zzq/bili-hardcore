#!/bin/sh
# 确保数据目录存在且可写
mkdir -p "${DATA_DIR:-/app/data}"
exec "$@"
