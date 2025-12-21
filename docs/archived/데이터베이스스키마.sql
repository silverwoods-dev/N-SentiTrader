-- [1] 종목 마스터 (변경 없음)
CREATE TABLE tb_stock_master (
    stock_code      VARCHAR(20) NOT NULL,
    stock_name      VARCHAR(100) NOT NULL,
    market_type     VARCHAR(10) NOT NULL CHECK (market_type IN ('KOSPI', 'KOSDAQ')),
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_stock_master PRIMARY KEY (stock_code)
);

-- [2] 시장 지수 (변경 없음)
CREATE TABLE tb_market_index (
    trade_date      DATE NOT NULL,
    market_type     VARCHAR(10) NOT NULL,
    close_value     DECIMAL(15, 2),
    return_rate     DECIMAL(10, 5),
    CONSTRAINT pk_market_index PRIMARY KEY (trade_date, market_type)
);

-- [3] 일별 주가 (변경 없음)
CREATE TABLE tb_daily_price (
    trade_date      DATE NOT NULL,
    stock_code      VARCHAR(20) NOT NULL,
    close_price     DECIMAL(15, 0),
    return_rate     DECIMAL(10, 5),
    excess_return   DECIMAL(10, 5), -- Target Y
    volume          BIGINT,
    
    CONSTRAINT pk_daily_price PRIMARY KEY (trade_date, stock_code),
    CONSTRAINT fk_price_stock FOREIGN KEY (stock_code) REFERENCES tb_stock_master(stock_code)
);
CREATE INDEX idx_daily_price_date ON tb_daily_price(trade_date);

-- [4] 뉴스 본문 (구조 개선: Stock Code 제거)
CREATE TABLE tb_news_content (
    news_id         BIGSERIAL NOT NULL,
    title           TEXT NOT NULL,
    content         TEXT,
    published_at    TIMESTAMP NOT NULL,
    press           VARCHAR(50),
    url             TEXT,
    title_hash      VARCHAR(32) NOT NULL, -- 중복 제거 키
    keywords        JSONB,                -- 형태소 분석 결과
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT pk_news_content PRIMARY KEY (news_id)
);
CREATE UNIQUE INDEX idx_news_hash ON tb_news_content(title_hash); -- 중복 원천 차단
CREATE INDEX idx_news_gin_keywords ON tb_news_content USING GIN (keywords); -- 키워드 검색 고속화

-- [5] 뉴스-종목 매핑 (신설: N:M 관계 및 시차 처리 해결)
CREATE TABLE tb_news_mapping (
    map_id          BIGSERIAL NOT NULL,
    news_id         BIGINT NOT NULL,
    stock_code      VARCHAR(20) NOT NULL,
    impact_date     DATE NOT NULL, -- [핵심] 시장 반영일 (수집 시 계산됨)
    
    CONSTRAINT pk_news_mapping PRIMARY KEY (map_id),
    CONSTRAINT fk_map_news FOREIGN KEY (news_id) REFERENCES tb_news_content(news_id) ON DELETE CASCADE,
    CONSTRAINT fk_map_stock FOREIGN KEY (stock_code) REFERENCES tb_stock_master(stock_code)
);
-- 학습 시 가장 많이 쓰일 조인 조건 인덱스
CREATE INDEX idx_map_impact_stock ON tb_news_mapping(impact_date, stock_code);

-- [6] 감성사전 (무결성 강화)
CREATE TABLE tb_sentiment_dict (
    dict_id         SERIAL NOT NULL,
    word            VARCHAR(100) NOT NULL,
    score_beta      DECIMAL(10, 5) NOT NULL,
    source          VARCHAR(10) DEFAULT 'MAIN',
    version         VARCHAR(20) NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT pk_sentiment_dict PRIMARY KEY (dict_id),
    CONSTRAINT uq_dict_version_word UNIQUE (version, word) -- [핵심] 중복 방지
);