-- TASK-038: 재무 팩터 기반 멀티 타겟 모델 확장 (Multi-Factor Research)
-- tb_stock_fundamentals 테이블 생성 (수정: FK column name fix)

CREATE TABLE IF NOT EXISTS public.tb_stock_fundamentals (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL REFERENCES tb_stock_master(stock_code),
    base_date DATE NOT NULL,
    per NUMERIC(15, 2),
    pbr NUMERIC(15, 2),
    roe NUMERIC(15, 2),
    market_cap BIGINT, -- 시가총액 (원)
    sector VARCHAR(100), -- 업종/섹터 분류
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_code, base_date)
);

CREATE INDEX IF NOT EXISTS idx_fundamentals_code_date ON tb_stock_fundamentals(stock_code, base_date);
