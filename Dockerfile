# Dockerfile
# Stage 1: Builder
FROM python:3.12-slim-bookworm AS builder

# 1. 시스템 의존성 설치 (빌드 도구)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    automake \
    autoconf \
    libtool \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 2. mecab-ko 설치
WORKDIR /build
RUN curl -LO https://bitbucket.org/eunjeon/mecab-ko/downloads/mecab-0.996-ko-0.9.2.tar.gz \
    && tar zxfv mecab-0.996-ko-0.9.2.tar.gz \
    && cd mecab-0.996-ko-0.9.2 \
    && curl -L -o config.guess "http://git.savannah.gnu.org/gitweb/?p=config.git;a=blob_plain;f=config.guess;hb=HEAD" \
    && curl -L -o config.sub "http://git.savannah.gnu.org/gitweb/?p=config.git;a=blob_plain;f=config.sub;hb=HEAD" \
    && ./configure --prefix=/usr/local \
    && make \
    && make install \
    && ldconfig

# 3. mecab-ko-dic 설치
RUN curl -LO https://bitbucket.org/eunjeon/mecab-ko-dic/downloads/mecab-ko-dic-2.1.1-20180720.tar.gz \
    && tar zxfv mecab-ko-dic-2.1.1-20180720.tar.gz \
    && cd mecab-ko-dic-2.1.1-20180720 \
    && ./autogen.sh \
    && ./configure --prefix=/usr/local \
    && make \
    && make install

# Stage 2: Runtime
FROM python:3.12-slim-bookworm

# 런타임 의존성 (MeCab 실행에 필요한 라이브러리)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy MeCab artifacts from builder
COPY --from=builder /usr/local/lib/libmecab.* /usr/local/lib/
COPY --from=builder /usr/local/libexec/mecab /usr/local/libexec/
COPY --from=builder /usr/local/bin/mecab* /usr/local/bin/
COPY --from=builder /usr/local/lib/mecab /usr/local/lib/mecab
COPY --from=builder /usr/local/etc/mecabrc /usr/local/etc/mecabrc

# Update library cache
RUN ldconfig

# uv 설치
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 작업 디렉토리 설정
WORKDIR /app

# 의존성 파일 복사 및 설치
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache

# 8. 소스코드 복사
COPY . .

# 9. 환경변수 설정
ENV PATH="/app/.venv/bin:$PATH"
ENV NS_BASE_DIR="/app"
ENV NS_DATA_PATH="/app/data"
ENV TZ="Asia/Seoul"
ENV PYTHONPATH="/app"

# 10. 실행 (기본값)
CMD ["uv", "run", "main_scheduler.py"]
