#!/bin/sh
set -eu

echo "== 端口监听（只读） =="
ss -lntp | grep -E ':(80|443|8081|8082)\b' || true

echo "== Docker 版本（只读） =="
docker version --format 'client={{.Client.Version}} server={{.Server.Version}}'
docker compose version

echo "== 现有容器（只读） =="
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}'

if ss -lnt | grep -qE ':8082\b'; then
  echo "冲突：8082 已被占用，停止部署。"
  exit 2
fi

echo "检查通过：8082 当前空闲；未执行任何修改。"
