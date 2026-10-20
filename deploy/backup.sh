#!/usr/bin/env bash
# 每日备份：PostgreSQL 数据库 + 上传文件，保留 7 天。
#
# 使用前提（只需做一次）：
#   1. 创建 /home/myblog/.pgpass，内容：
#      127.0.0.1:5432:my_blog:blog_user:你的数据库密码
#      然后 chmod 600 /home/myblog/.pgpass
#   2. 把本脚本放到 /srv/my_blog/deploy/backup.sh，chmod 755。
#   3. 加到 myblog 用户的 crontab：
#      0 3 * * * /srv/my_blog/deploy/backup.sh >> /srv/backups/backup.log 2>&1
#
# 为什么用 .pgpass：避免把数据库密码写进脚本或 crontab，也避免 psql 交互式提示。

set -euo pipefail

BACKUP_DIR="/srv/backups"
STAMP="$(date +%F)"
mkdir -p "$BACKUP_DIR"

# -F 不是必须的；gzip 压缩后便于长期保存。
pg_dump -h 127.0.0.1 -U blog_user -d my_blog | gzip > "$BACKUP_DIR/my_blog_${STAMP}.sql.gz"

# 上传文件单独打包；-C 切换目录后只打包 uploads，备份包里路径更干净。
tar -czf "$BACKUP_DIR/uploads_${STAMP}.tar.gz" -C /srv/my_blog/backend uploads

# 删除 7 天前的备份。
find "$BACKUP_DIR" -type f -mtime +7 -delete

echo "[$(date -Iseconds)] backup finished: $BACKUP_DIR"
