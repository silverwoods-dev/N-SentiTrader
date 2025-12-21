-- src/db/schema.sql

-- 1. 종목 마스터
CREATE TABLE IF NOT EXISTS tb_stock_master (
    stock_code VARCHAR(10) PRIMARY KEY,
    stock_name VARCHAR(100),
    market_type VARCHAR(10), -- 'KOSPI' or 'KOSDAQ'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 일별 주가 및 초과 수익률
CREATE TABLE IF NOT EXISTS tb_daily_price (
    date DATE,
    stock_code VARCHAR(10),
    close_price DECIMAL,
    return_rate DECIMAL,
    excess_return DECIMAL, -- (종목등락률 - 시장지수등락률)
    PRIMARY KEY (date, stock_code),
    FOREIGN KEY (stock_code) REFERENCES tb_stock_master(stock_code)
);

-- 3. 뉴스 URL 관리 (중복 방지 및 상태 관리)
CREATE TABLE IF NOT EXISTS tb_news_url (
    url_hash VARCHAR(64) PRIMARY KEY, -- SHA256 hash of URL
    url TEXT NOT NULL,
    source VARCHAR(50),
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'collected', 'failed'
    published_at_hint DATE, -- 수집 시점의 날짜 힌트 (네이버 검색 결과 등)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    collected_at TIMESTAMP
);

-- 4. 뉴스 본문 데이터
CREATE TABLE IF NOT EXISTS tb_news_content (
    url_hash VARCHAR(64) PRIMARY KEY,
    title TEXT,
    content TEXT,
    published_at TIMESTAMP,
    keywords JSONB, -- 전처리된 키워드 리스트
    FOREIGN KEY (url_hash) REFERENCES tb_news_url(url_hash)
);

-- 5. 뉴스-종목 매핑 (다대다)
CREATE TABLE IF NOT EXISTS tb_news_mapping (
    url_hash VARCHAR(64),
    stock_code VARCHAR(10),
    PRIMARY KEY (url_hash, stock_code),
    FOREIGN KEY (url_hash) REFERENCES tb_news_url(url_hash),
    FOREIGN KEY (stock_code) REFERENCES tb_stock_master(stock_code)
);

-- 6. 감성 사전 (학습 결과)
CREATE TABLE IF NOT EXISTS tb_sentiment_dict (
    stock_code VARCHAR(10),
    word VARCHAR(100),
    beta DECIMAL,
    version VARCHAR(20),
    source VARCHAR(20), -- 'Main' or 'Buffer'
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (stock_code, word, version, source),
    FOREIGN KEY (stock_code) REFERENCES tb_stock_master(stock_code)
);

-- 7. 작업(Job) 관리
CREATE TABLE IF NOT EXISTS jobs (
    job_id SERIAL PRIMARY KEY,
    job_type VARCHAR(20), -- 'backfill', 'daily'
    params JSONB,
    status VARCHAR(20), -- 'running', 'completed', 'failed'
    progress DECIMAL DEFAULT 0,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- 8. Daily 수집 대상 관리
CREATE TABLE IF NOT EXISTS daily_targets (
    target_id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) UNIQUE,
    status VARCHAR(20) DEFAULT 'paused', -- 'active', 'paused', 'pending'
    backfill_completed_at TIMESTAMP,
    activation_requested_at TIMESTAMP,
    auto_activate_daily BOOLEAN DEFAULT FALSE,
    optimal_lag INT DEFAULT 1, -- 분석을 통해 도출된 최적 시차
    FOREIGN KEY (stock_code) REFERENCES tb_stock_master(stock_code)
);

-- 9. 뉴스 수집 에러 로그
CREATE TABLE IF NOT EXISTS tb_news_errors (
    error_id SERIAL PRIMARY KEY,
    url_hash VARCHAR(64),
    error_msg TEXT,
    retry_count INT DEFAULT 0,
    occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 10. 예측 결과 및 성과
CREATE TABLE IF NOT EXISTS tb_predictions (
    prediction_id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10),
    prediction_date DATE,
    sentiment_score DECIMAL,
    prediction INT, -- 1: 상승(Alpha > 0), 0: 하락(Alpha <= 0)
    actual_alpha DECIMAL, -- 실제 실현된 초과 수익률
    is_correct BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (stock_code) REFERENCES tb_stock_master(stock_code)
);

-- TASK-032: 인덱스 추가 (Timeline View 성능 최적화)
CREATE INDEX IF NOT EXISTS idx_sentiment_dict_updated_at 
ON tb_sentiment_dict(stock_code, source, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_sentiment_dict_word_version
ON tb_sentiment_dict(word, version, source);

-- 11. 감성 사전 메타데이터 (버전 관리 및 최적화 정보)
CREATE TABLE IF NOT EXISTS tb_sentiment_dict_meta (
    stock_code VARCHAR(10),
    version VARCHAR(20),
    source VARCHAR(20), -- 'Main', 'Buffer'
    lookback_months INT, -- 학습에 사용된 개월수 (AWO 연동)
    train_start_date DATE,
    train_end_date DATE,
    metrics JSONB, -- {hit_rate: 0.55, avg_alpha: 0.001, ...}
    is_active BOOLEAN DEFAULT FALSE, -- 현재 예측에 사용 중인 버전 여부
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (stock_code, version, source),
    FOREIGN KEY (stock_code) REFERENCES tb_stock_master(stock_code)
);

-- 12. 시스템 검증(Backtest) 작업 관리
CREATE TABLE IF NOT EXISTS tb_verification_jobs (
    v_job_id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10),
    v_type VARCHAR(20) DEFAULT 'walk-forward',
    params JSONB, -- {train_months: 2, test_months: 1, step_days: 1}
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'running', 'completed', 'failed'
    progress DECIMAL DEFAULT 0,
    result_summary JSONB, -- {final_hit_rate: 0.58, total_days: 30, ...}
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (stock_code) REFERENCES tb_stock_master(stock_code)
);

-- 13. 시스템 검증 상세 결과
CREATE TABLE IF NOT EXISTS tb_verification_results (
    result_id SERIAL PRIMARY KEY,
    v_job_id INT,
    target_date DATE,
    predicted_score DECIMAL,
    actual_alpha DECIMAL,
    is_correct BOOLEAN,
    used_version VARCHAR(20),
    FOREIGN KEY (v_job_id) REFERENCES tb_verification_jobs(v_job_id) ON DELETE CASCADE
);
