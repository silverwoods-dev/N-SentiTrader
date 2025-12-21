#!/bin/bash
# build_and_run.sh

# 1. 임시 빌드 디렉토리 생성
TMP_DIR="/tmp/n_senti_build"
rm -rf $TMP_DIR
mkdir -p $TMP_DIR

# 2. 필요한 파일만 복사 (pg_data 제외)
echo "Copying files to temporary build directory..."
cp -r src $TMP_DIR/
cp -r data $TMP_DIR/
cp -r scripts $TMP_DIR/
cp *.py $TMP_DIR/
cp pyproject.toml uv.lock Dockerfile .dockerignore $TMP_DIR/

# 3. 빌드
echo "Building Docker image..."
cd $TMP_DIR
docker build -t n-senti-app .

# 4. 실행
echo "Starting containers..."
cd -
docker compose up -d postgres_db rabbitmq
# DB와 MQ가 뜰 때까지 잠시 대기
sleep 5
docker compose up -d dashboard address_worker body_worker
