#!/bin/bash
# N-SentiTrader Migration Package Creator
# 마이그레이션 패키지 생성 스크립트

set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PACKAGE_NAME="n-sentitrader-migration-${TIMESTAMP}"
OUTPUT_DIR="/Users/dev/CODE/${PACKAGE_NAME}"

echo "=== N-SentiTrader Migration Package Creator ==="
echo "패키지 이름: ${PACKAGE_NAME}"
echo ""

# 1. Create output directory
mkdir -p "${OUTPUT_DIR}"

# 2. Copy project files (excluding unnecessary items)
echo "[1/4] 프로젝트 파일 복사 중..."
rsync -av \
    --exclude='.venv' \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.archive' \
    --exclude='pg_data' \
    --exclude='node_modules' \
    --exclude='.DS_Store' \
    /Users/dev/CODE/N-SentiTrader/ \
    "${OUTPUT_DIR}/project/"

# 3. Perform live database backup (최신 데이터 보장)
echo "[2/4] 데이터베이스 실시간 백업 수행 중... (수 분 소요)"
mkdir -p "${OUTPUT_DIR}/backup"

BACKUP_FILE="${OUTPUT_DIR}/backup/backup_${TIMESTAMP}.dump"

# Check if DB container is running
if ! docker ps | grep -q n_senti_db; then
    echo "Error: n_senti_db container is not running."
    echo "Please start the container first: docker compose up -d n_senti_db"
    exit 1
fi

# Perform live backup
docker exec n_senti_db pg_dump \
    -U myuser \
    -d n_senti_db \
    -F c \
    -f /tmp/backup_${TIMESTAMP}.dump

# Copy from container to host
docker cp n_senti_db:/tmp/backup_${TIMESTAMP}.dump "${BACKUP_FILE}"

# Verify backup
BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
echo "  백업 완료: ${BACKUP_FILE} (${BACKUP_SIZE})"

# Cleanup temp file in container
docker exec n_senti_db rm -f /tmp/backup_${TIMESTAMP}.dump

# 4. Create restore script
echo "[3/4] 복원 스크립트 생성 중..."
cat > "${OUTPUT_DIR}/restore_db.sh" << 'EOF'
#!/bin/bash
# Database Restore Script

echo "=== N-SentiTrader Database Restore ==="

# Find backup file dynamically
BACKUP_FILE=$(ls -t backup/*.dump 2>/dev/null | head -1)

if [ -z "$BACKUP_FILE" ]; then
    echo "Error: No backup file found in backup/ directory"
    exit 1
fi

echo "사용할 백업 파일: ${BACKUP_FILE}"

# Check if container is running
if ! docker ps | grep -q n_senti_db; then
    echo "Error: n_senti_db container is not running."
    echo "Run: docker compose up -d n_senti_db"
    exit 1
fi

# Copy backup to container
echo "[1/3] 백업 파일 복사 중..."
docker cp "${BACKUP_FILE}" n_senti_db:/tmp/restore.dump

# Restore database
echo "[2/3] 데이터베이스 복원 중... (수 분 소요)"
docker exec n_senti_db pg_restore \
    -U myuser \
    -d n_senti_db \
    -c \
    /tmp/restore.dump 2>/dev/null || true

# Verify
echo "[3/3] 복원 확인 중..."
COUNT=$(docker exec n_senti_db psql -U myuser -d n_senti_db -t \
    -c "SELECT COUNT(*) FROM tb_news_content;")
echo "뉴스 콘텐츠 수: ${COUNT}"

# Cleanup
docker exec n_senti_db rm -f /tmp/restore.dump

echo ""
echo "=== 복원 완료 ==="
EOF
chmod +x "${OUTPUT_DIR}/restore_db.sh"

# Create Windows batch version
cat > "${OUTPUT_DIR}/restore_db.bat" << 'EOF'
@echo off
echo === N-SentiTrader Database Restore ===

REM Find backup file (use the first .dump file found)
for %%F in (backup\*.dump) do (
    set BACKUP_FILE=%%F
    goto :found
)
echo Error: No backup file found in backup\ directory
pause
exit /b 1

:found
echo Using backup file: %BACKUP_FILE%

echo [1/3] 백업 파일 복사 중...
docker cp %BACKUP_FILE% n_senti_db:/tmp/restore.dump

echo [2/3] 데이터베이스 복원 중... (수 분 소요)
docker exec n_senti_db pg_restore -U myuser -d n_senti_db -c /tmp/restore.dump

echo [3/3] 복원 확인 중...
docker exec n_senti_db psql -U myuser -d n_senti_db -c "SELECT COUNT(*) FROM tb_news_content;"

docker exec n_senti_db rm -f /tmp/restore.dump

echo.
echo === 복원 완료 ===
pause
EOF

# 5. Create archive
echo "[4/4] 압축 파일 생성 중..."
cd /Users/dev/CODE
tar -czvf "${PACKAGE_NAME}.tar.gz" "${PACKAGE_NAME}"

# Summary
echo ""
echo "=== 마이그레이션 패키지 생성 완료 ==="
echo "폴더: ${OUTPUT_DIR}"
echo "압축파일: /Users/dev/CODE/${PACKAGE_NAME}.tar.gz"
echo ""
echo "패키지 내용:"
du -sh "${OUTPUT_DIR}"/*
echo ""
echo "전송 방법:"
echo "  rsync -avz ${PACKAGE_NAME}.tar.gz user@target-server:/home/user/"
echo "  또는 USB/클라우드로 전송"
