#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
set -a
. ./.env
set +a
mkdir -p backups
umask 077
timestamp=$(date +%Y%m%d-%H%M%S)
docker compose exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > "backups/ylaw-survey-$timestamp.dump"
echo "已创建 backups/ylaw-survey-$timestamp.dump"
