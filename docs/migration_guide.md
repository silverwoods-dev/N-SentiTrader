# N-SentiTrader 마이그레이션 가이드
## Migration Guide for Ubuntu Server & Windows 11

> 이 문서는 N-SentiTrader 프로젝트를 새로운 환경으로 이전하는 방법을 설명합니다.

---

## 📋 사전 준비

### 필요한 파일
| 파일 | 위치 | 크기 | 설명 |
|------|------|------|------|
| **프로젝트 소스** | 전체 폴더 | ~50MB | 코드, 설정, 문서 |
| **DB 백업** | `.backup/backup_2025-12-30.dump` | 213MB | PostgreSQL 덤프 |

### 전송 방법
```bash
# 옵션 1: 압축 후 전송
tar -czvf n-sentitrader-migration.tar.gz \
    --exclude='.venv' \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    .

# 옵션 2: rsync (Ubuntu 대상)
rsync -avz --exclude='.venv' --exclude='.git' \
    /Users/dev/CODE/N-SentiTrader/ \
    user@ubuntu-server:/home/user/N-SentiTrader/
```

---

## 🐧 Ubuntu Server 설치 가이드

### 1. 사전 요구사항 설치

```bash
# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# Docker 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Docker Compose 설치
sudo apt install docker-compose-plugin -y

# 현재 사용자를 docker 그룹에 추가
sudo usermod -aG docker $USER
newgrp docker

# 설치 확인
docker --version
docker compose version
```

### 2. 프로젝트 설정

```bash
# 프로젝트 디렉토리 이동
cd /home/user/N-SentiTrader

# 환경 변수 설정
cp .env.sample .env
nano .env  # 필요한 값 수정

# 데이터 디렉토리 생성
mkdir -p data pg_data
```

### 3. 컨테이너 빌드 및 실행

```bash
# 이미지 빌드
docker compose build

# 컨테이너 시작 (DB만 먼저)
docker compose up -d n_senti_db

# DB 준비 대기 (30초)
sleep 30
```

### 4. 데이터베이스 복원

```bash
# 백업 파일을 컨테이너로 복사
docker cp .backup/backup_2025-12-30.dump n_senti_db:/tmp/

# 데이터베이스 복원
docker exec n_senti_db pg_restore \
    -U myuser \
    -d n_senti_db \
    -c \
    /tmp/backup_2025-12-30.dump

# 복원 확인
docker exec n_senti_db psql -U myuser -d n_senti_db \
    -c "SELECT COUNT(*) FROM tb_news_content;"
```

### 5. 전체 서비스 시작

```bash
# 모든 컨테이너 시작
docker compose up -d

# 상태 확인
docker compose ps

# 로그 확인
docker compose logs -f --tail=50
```

### 6. 접속 확인

| 서비스 | URL | 기본 포트 |
|--------|-----|----------|
| Dashboard | http://서버IP:8081 | 8081 |
| Grafana | http://서버IP:3000 | 3000 |
| RabbitMQ | http://서버IP:15672 | 15672 |

---

## 🪟 Windows 11 Docker Desktop 설치 가이드

### 1. 사전 요구사항

1. **WSL2 설치** (관리자 PowerShell):
```powershell
wsl --install
# 재부팅 후 계속
```

2. **Docker Desktop 설치**:
   - [Docker Desktop 다운로드](https://www.docker.com/products/docker-desktop/)
   - 설치 시 "Use WSL 2 instead of Hyper-V" 옵션 선택
   - 설치 후 재부팅

3. **Docker Desktop 설정**:
   - Settings → Resources → WSL Integration → Enable for your distro
   - Settings → Resources → Memory: 최소 8GB 할당 권장

### 2. 프로젝트 설정

```powershell
# PowerShell에서 실행
cd C:\Projects\N-SentiTrader

# 환경 변수 설정
copy .env.sample .env
notepad .env  # 필요한 값 수정
```

### 3. 줄바꿈 문자 변환 (중요!)

Windows에서는 줄바꿈 문자 차이로 인한 오류가 발생할 수 있습니다:

```powershell
# Git 설정으로 자동 변환 비활성화
git config core.autocrlf false

# 또는 모든 .sh 파일 수동 변환 (Git Bash 사용)
find . -name "*.sh" -exec dos2unix {} \;
```

### 4. 컨테이너 빌드 및 실행

```powershell
# 이미지 빌드
docker compose build

# DB 컨테이너 먼저 시작
docker compose up -d n_senti_db

# 30초 대기
Start-Sleep -Seconds 30
```

### 5. 데이터베이스 복원

```powershell
# 백업 파일 복사
docker cp .backup\backup_2025-12-30.dump n_senti_db:/tmp/

# 데이터베이스 복원
docker exec n_senti_db pg_restore `
    -U myuser `
    -d n_senti_db `
    -c `
    /tmp/backup_2025-12-30.dump

# 복원 확인
docker exec n_senti_db psql -U myuser -d n_senti_db `
    -c "SELECT COUNT(*) FROM tb_news_content;"
```

### 6. 전체 서비스 시작

```powershell
# 모든 컨테이너 시작
docker compose up -d

# 상태 확인
docker compose ps
```

### 7. Windows 방화벽 설정 (필요시)

```powershell
# 관리자 PowerShell
New-NetFirewallRule -DisplayName "N-SentiTrader Dashboard" `
    -Direction Inbound -LocalPort 8081 -Protocol TCP -Action Allow

New-NetFirewallRule -DisplayName "Grafana" `
    -Direction Inbound -LocalPort 3000 -Protocol TCP -Action Allow
```

---

## ⚠️ 문제 해결

### 공통 문제

| 문제 | 원인 | 해결책 |
|------|------|--------|
| `pg_restore: error: input file is too short` | 백업 파일 손상 | 백업 파일 재전송 (바이너리 모드) |
| `connection refused` | DB 미시작 | `docker compose up -d n_senti_db` 후 30초 대기 |
| `permission denied` | 권한 문제 | `chmod -R 755 .` (Linux) |
| `line endings` | CRLF/LF 차이 | `dos2unix` 사용 (Windows) |

### Ubuntu 전용

```bash
# MeCab 설치 오류 시
sudo apt install libmecab-dev mecab-ipadic-utf8 -y

# 포트 충돌 확인
sudo lsof -i :8081
sudo lsof -i :5432
```

### Windows 전용

```powershell
# WSL 메모리 제한 설정 (C:\Users\<user>\.wslconfig)
[wsl2]
memory=8GB
processors=4

# Docker Desktop 재시작 필요
```

---

## ✅ 마이그레이션 체크리스트

- [ ] 소스 코드 전송 완료
- [ ] `.env` 파일 설정
- [ ] Docker/Docker Compose 설치
- [ ] 컨테이너 빌드 성공
- [ ] DB 백업 파일 전송
- [ ] DB 복원 완료
- [ ] 전체 컨테이너 시작
- [ ] Dashboard 접속 확인 (http://localhost:8081)
- [ ] Grafana 접속 확인 (http://localhost:3000)
- [ ] 뉴스 데이터 조회 확인

---

*마이그레이션 관련 문의사항은 담당자에게 연락하세요.*
