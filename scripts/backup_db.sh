#!/bin/bash
# scripts/backup_db.sh
# PostgreSQL 데이터베이스 백업 스크립트

BACKUP_DIR="/home/dev/CODE/N-SentiTrader/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="nsentitrader_backup_$TIMESTAMP.sql"

# 백업 디렉토리 생성
mkdir -p $BACKUP_DIR

# .env 파일에서 정보 가져오기
if [ -f "/home/dev/CODE/N-SentiTrader/.env" ]; then
    export $(grep -v '^#' /home/dev/CODE/N-SentiTrader/.env | xargs)
fi

DB_USER=${DB_USER:-myuser}
DB_NAME=${DB_NAME:-n_senti_db}

echo "Starting backup for $DB_NAME..."
docker exec n_senti_db pg_dump -U $DB_USER $DB_NAME > $BACKUP_DIR/$FILENAME

if [ $? -eq 0 ]; then
    echo "Backup completed successfully: $BACKUP_DIR/$FILENAME"
    # 7일 지난 백업 삭제
    find $BACKUP_DIR -name "nsentitrader_backup_*.sql" -mtime +7 -delete
else
    echo "Backup failed!"
    exit 1
fi
