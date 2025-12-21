# docker/tokenizer/Dockerfile
FROM python:3.12-slim-bookworm

# 1. 시스템 의존성 및 Mecab 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    mecab \
    libmecab-dev \
    mecab-ko-dic \
    && rm -rf /var/lib/apt/lists/*

# 2. uv 설치
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 3. 작업 디렉토리 설정
WORKDIR /app

# 4. 사용자 사전 컴파일
# 시스템 사전 경로 확인 필요 (보통 /usr/lib/x86_64-linux-gnu/mecab/dic/mecab-ko-dic)
COPY data/user_dic.csv /app/data/user_dic.csv
RUN /usr/lib/mecab/mecab-dict-index \
    -d /usr/lib/x86_64-linux-gnu/mecab/dic/mecab-ko-dic \
    -u /app/data/user.dic \
    -f utf-8 -t utf-8 \
    /app/data/user_dic.csv

# 5. 의존성 설치
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache

# 6. 소스코드 복사
COPY . .

# 7. 환경변수 설정
ENV PATH="/app/.venv/bin:$PATH"
ENV MECAB_DIC_PATH="/usr/lib/x86_64-linux-gnu/mecab/dic/mecab-ko-dic"
ENV MECAB_USER_DIC_PATH="/app/data/user.dic"

# 8. 실행
CMD ["uv", "run", "src/tokenizer_service.py"]
