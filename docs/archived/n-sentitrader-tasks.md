# N-SentiTrader Implementation Tasks

## TASK-020: 문서·지침 정렬 (Copilot Instructions 우선 반영)
STATUS: IN-PROGRESS

- 타입: chore
- 관련 PRD 섹션: 우선순위 및 지침 준수
- 우선순위: P0
- 예상 난이도: S
- 목적:
  - `.github/copilot-instructions.md`의 규칙을 프로젝트 전반(문서, 작업흐름, 커뮤니케이션) 우선 반영한다.
- 상세 작업 내용:
  - PRD와 TASKS에 지침 우선순위 문구 추가(완료).
  - 모든 신규 작업은 TASKS에 등록 후 실행.
- 완료 기준:
  - 모든 팀원/에이전트가 지침 파일을 확인하고 이를 준수하도록 문서화됨.

## TASK-021: 토크나이저 테스트 계획 통합
STATUS: IN-PROGRESS

- 타입: chore
- 관련 PRD 섹션: 5. 시스템 아키텍처 및 파이프라인
- 우선순위: P1
- 예상 난이도: S
- 목적:
  - 기존 독립 문서로 생성된 `docs/TEST_PLAN_TOKENIZER.md`를 TASK 흐름으로 통합하거나 아카이브하여 PRD/TASKS 기반으로 테스트가 진행되도록 함.
- 상세 작업 내용:
  - `docs/TEST_PLAN_TOKENIZER.md`를 `docs/archived/`로 이동(아카이브).
  - 아카이브 확인: `docs/archived/TEST_PLAN_TOKENIZER.md` 존재함.
  - TASKS에 토크나이저 관련 구체 작업 항목(도커파일 작성, 빌드, 스모크 테스트) 추가.
  - 단위테스트 추가: `tests/test_tokenizer.py` (토큰화 재현성 확인, 예: '2차전지').
- 완료 기준:
  - 아카이브 파일 생성 및 TASKS에 관련 작업 등록 완료.

## TASK-022: 토크나이저 컨테이너화 및 스모크 테스트
STATUS: IN-PROGRESS

- 타입: feature
- 관련 PRD 섹션: 5, 7.2
- 우선순위: P1
- 예상 난이도: M
- 목적:
  - `src/tokenizer_service.py`를 포함하는 Dockerfile을 작성하고, 이미지 빌드 및 스모크 테스트를 자동화한다.
- 상세 작업 내용:
  - `Dockerfile` 작성(시스템-level `mecab` 및 `mecab-ko-dic` 설치 포함).
  - `docker build` 및 `docker run`로 스모크 테스트 수행.
  - 테스트 결과(성공/실패)와 로그를 TASK 이슈에 첨부.
  - 비고: 서비스 레벨 코드는 이미 존재함(`src/tokenizer_service.py`) — `USER_DIC_PATH`를 worker-level로 로드하도록 패치됨. Dockerfile 및 테스트 스크립트가 필요함.
- 완료 기준:
  - 컨테이너 내에서 `mecab` 명령 및 `/tokenize` 엔드포인트가 정상 동작.


## TASK-001: Project Initialization & Infra Setup
STATUS: COMPLETED

- 타입: chore
- 관련 PRD 섹션: 5. 시스템 아키텍처 및 파이프라인
- 우선순위: P0
- 예상 난이도: S
- 관련 MCP 도구: filesystem
- 목적:
  - 프로젝트 기본 구조와 Docker 기반 실행 환경을 구축하여 개발 준비를 완료한다.
- 상세 작업 내용:
  - [x] `src/`, `tests/`, `data/`, `output/`, `config/` 디렉토리 생성
  - [x] `Dockerfile` 작성 (Python 3.10, Mecab 설치)
  - [x] `docker-compose.yml` 작성 (App + PostgreSQL)
  - [x] `.env` 및 `.env.sample` 설정
- 변경 예상 파일/모듈:
  - `Dockerfile`, `docker-compose.yml`, `.env`, `requirements.txt`
- 완료 기준(Acceptance Criteria):
  - [x] `docker-compose up -d` 실행 시 컨테이너 2개(App, DB)가 정상 구동되어야 함.
  - [x] App 컨테이너 내부에서 `mecab` 명령어가 정상 실행되어야 함.

## TASK-011: Historical Data & Initial Training
STATUS: COMPLETED

- 타입: feature
- 관련 PRD 섹션: 7.1 모듈 A (FR-A07)
- 우선순위: P1
- 예상 난이도: M
- 관련 MCP 도구: context7 (Polars)
- 목적:
  - 서비스 런칭 전, 과거 2년 치 데이터를 수집하고 초기 모델을 학습시킨다.
- 상세 작업 내용:
  - [x] `src/scripts/collect_history.py` 구현 (2024-01-01 ~ 2025-12-17)
  - [x] `src/learner/initial_trainer.py` 구현 (Polars 기반 대용량 학습)
  - [x] 초기 감성 사전(`v1.0_init`) DB 적재 확인
- 변경 예상 파일/모듈:
  - `src/scripts/collect_history.py`, `src/learner/initial_trainer.py`
- 완료 기준(Acceptance Criteria):
  - [x] 수집 스크립트가 중단 후 재시작 시 중복 없이 이어하기가 가능한지 확인.
  - [x] 초기 학습 스크립트가 OOM 없이 2년 치 데이터를 처리하는지 확인.

## TASK-002: Database Schema Design & Migration
STATUS: COMPLETED

- 타입: feature
- 관련 PRD 섹션: 4. 데이터 모델 및 스키마 설계
- 우선순위: P0
- 예상 난이도: S
- 관련 MCP 도구: filesystem, context7 (SQLAlchemy/Polars)
- 목적:
  - 뉴스, 주가, 감성사전 데이터를 저장할 DB 스키마를 정의하고 생성한다. (벡터 데이터 1년 보관 고려)
- 상세 작업 내용:
  - [x] `src/db/schema.sql` 작성 (DDL)
    - `tb_stock_master`, `tb_market_index`, `tb_daily_price`
    - `tb_news_content` (GIN Index), `tb_news_mapping` (Impact Date), `tb_sentiment_dict`
  - [x] DB 연결 유틸리티 (`src/db/connection.py`) 구현
  - [x] 초기화 스크립트 (`init_db.py`) 작성
- 변경 예상 파일/모듈:
  - `src/db/schema.sql`, `src/db/connection.py`
- 완료 기준(Acceptance Criteria):
  - [x] PostgreSQL에 접속하여 4개 테이블이 정상적으로 생성되었는지 확인.
  - [x] JSONB 컬럼(`tb_news_raw.tokens`)에 데이터 삽입/조회 테스트 성공.

## TASK-003: Collector - Stock Price & Market Index
STATUS: COMPLETED

- 타입: feature
- 관련 PRD 섹션: 7.1 모듈 A (FR-A02, FR-A05)
- 우선순위: P1
- 예상 난이도: M
- 관련 MCP 도구: context7 (Finance API)
- 목적:
  - 주가 및 시장 지수 데이터를 수집하고, 초과 수익률(Target Y)을 계산하여 적재한다.
- 상세 작업 내용:
  - [x] `src/collector/stock.py` 구현 (FinanceDataReader 등 활용)
  - [x] KOSPI/KOSDAQ 지수 수집 로직 구현
  - [x] **Target Y 계산 로직 구현:** (개별종목 등락률 - 소속시장 지수 등락률) > 0 ? 1 : 0
  - [x] `tests/test_collector_stock.py` 작성
- 변경 예상 파일/모듈:
  - `src/collector/stock.py`
- 완료 기준(Acceptance Criteria):
  - [x] 특정 일자의 삼성전자(KOSPI) 등락률과 KOSPI 지수 등락률을 비교하여 Y값이 정확히 계산되는지 검증.

## TASK-004: Collector - News Crawler
STATUS: COMPLETED

- 타입: feature
- 관련 PRD 섹션: 7.1 모듈 A (FR-A01, FR-A03)
- 우선순위: P1
- 예상 난이도: M
- 관련 MCP 도구: context7 (BeautifulSoup/Requests)
- 목적:
  - 포털 금융 뉴스를 크롤링하고 중복을 제거하여 DB에 저장한다.
- 상세 작업 내용:
  - [x] `src/collector/news.py` 구현 (크롤링)
  - [x] `tb_news_content` 적재 (Title Hash 중복 방지) 및 `tb_news_mapping` 적재 (Impact Date 계산)
  - [x] `tests/test_collector_news.py` 작성
- 변경 예상 파일/모듈:
  - `src/collector/news.py`
- 완료 기준(Acceptance Criteria):
  - [x] 유사한 기사 2건 입력 시 1건만 저장되는지 테스트.
  - [x] 수집된 기사의 제목, 본문, 날짜가 DB에 정상 적재되는지 확인.
  - [x] **[추가]** 네이버 뉴스 SDS 레이아웃 변경에 따른 Selector 수정 및 검증 완료.

## TASK-005: Preprocessor - Mecab & User Dictionary
STATUS: IN-PROGRESS

- 타입: feature
- 관련 PRD 섹션: 7.2 모듈 B (FR-B01)
- 우선순위: P1
- 예상 난이도: M
- 관련 MCP 도구: context7 (Mecab-ko)
- 목적:
  - 금융 특화 사용자 사전을 적용하여 뉴스 텍스트를 형태소 분석한다.
  - 상세 작업 내용:
  - [x] `data/user_dic.csv` 생성 및 금융 용어('2차전지', '밸류업') 등록
  - [x] `src/nlp/tokenizer.py` 구현 (Mecab Wrapper)
  - [x] 사용자 사전 로딩 및 적용 확인 (런타임/서비스 레벨)
  - [ ] `tests/test_tokenizer.py` 작성 (단위테스트 미작성)
- 변경 예상 파일/모듈:
  - `src/nlp/tokenizer.py`, `data/user_dic.csv`
- 완료 기준(Acceptance Criteria):
  - [ ] '2차전지'가 ['2차', '전지']가 아닌 ['2차전지']로 토큰화되는지 단위테스트로 검증.

- 비고: 런타임/서비스 레벨에서의 사용자사전 적용은 `src/tokenizer_service.py`에 반영되어 있음. 단위테스트(`tests/test_tokenizer.py`)와 컨테이너 기반 재현성 검증이 필요함.

## TASK-006: Learner - Main Model (Lasso)
STATUS: COMPLETED

- 타입: feature
- 관련 PRD 섹션: 7.2 모듈 B (FR-B02)
- 우선순위: P1
- 예상 난이도: L
- 관련 MCP 도구: context7 (Scikit-learn, Polars)
- 목적:
  - 과거 3개월 데이터를 학습하여 장기 감성사전(Main Dictionary)을 구축한다.
- 상세 작업 내용:
  - [x] `src/learner/dataset.py`: 학습 데이터셋(X: TF-IDF, Y: Excess Return) 구성
  - [x] `src/learner/lasso.py`: Lasso 회귀 학습 및 Non-zero Coefficient 추출
  - [x] `tests/test_learner_lasso.py` 작성
- 변경 예상 파일/모듈:
  - `src/learner/lasso.py`
- 완료 기준(Acceptance Criteria):
  - [x] 학습 결과로 생성된 사전 파일에 단어와 가중치가 포함되어야 함.
  - [x] 의미 없는 불용어가 Lasso 규제에 의해 제거(0)되는지 확인.
  - [x] **데이터 누수 방지:** 학습 데이터(D-7일 이전)가 추론 대상일과 겹치지 않는지 검증.
  - [x] **[Refactor]** Pandas -> Polars 전환 완료 (대용량 처리 최적화).

## TASK-007: Learner - Buffer Model (Volatility)
STATUS: COMPLETED

- 타입: feature
- 관련 PRD 섹션: 7.2 모듈 B (FR-B03)
- 우선순위: P2
- 예상 난이도: M
- 관련 MCP 도구: context7 (Polars)
- 목적:
  - 최근 3일간의 급등락 단어를 추출하여 단기 버퍼 사전을 구축한다.
- 상세 작업 내용:
  - [x] `src/learner/buffer.py` 구현
  - [x] 빈도수 상위 10% & 변동성 2배 이상 단어 필터링
  - [x] `tests/test_learner_buffer.py` 작성
- 변경 예상 파일/모듈:
  - `src/learner/buffer.py`
- 완료 기준(Acceptance Criteria):
  - [x] 최근 이슈가 된 키워드(예: '상한가', '공시')가 버퍼 사전에 포착되는지 확인.

## TASK-008: Predictor - Scoring & Time Decay
STATUS: COMPLETED

- 타입: feature
- 관련 PRD 섹션: 7.3 모듈 C (FR-C01, FR-C02)
- 우선순위: P1
- 예상 난이도: L
- 관련 MCP 도구: context7 (Polars)
- 목적:
  - 뉴스에 감성 점수를 부여하고, 달력일 기준 시차 감쇠를 적용하여 최종 점수를 산출한다.
- 상세 작업 내용:
  - [x] `src/predictor/scoring.py` 구현
  - [x] **Time Decay 로직:** `exp(-decay_rate * (current_date - news_date).days)`
  - [x] Main(0.7) / Buffer(0.3) 점수 가중 합산
  - [x] `tests/test_predictor_score.py` 작성
- 변경 예상 파일/모듈:
  - `src/predictor/scoring.py`
- 완료 기준(Acceptance Criteria):
  - [x] 금요일 뉴스가 월요일 예측 시 D-3 가중치로 적용되는지 테스트.
  - [x] OOV 비율이 높을 경우 점수 산출을 중단하고 Unknown 반환.

## TASK-009: Predictor - Reporting & Ensemble
STATUS: COMPLETED

- 타입: feature
- 관련 PRD 섹션: 7.3 모듈 C (FR-C04)
- 우선순위: P2
- 예상 난이도: S
- 관련 MCP 도구: filesystem
- 목적:
  - 최종 예측 결과와 근거(Top Keywords)를 리포트 형태로 생성한다.
- 상세 작업 내용:
  - [x] `src/predictor/report.py` 구현
  - [x] JSON 및 Markdown 리포트 생성
  - [x] `output/` 디렉토리에 저장
- 변경 예상 파일/모듈:
  - `src/predictor/report.py`
- 완료 기준(Acceptance Criteria):
  - [x] 생성된 리포트에 종목명, 예측 신호(매수/관망), 주요 키워드 3개가 포함되어야 함.

## TASK-010: Integration & Automation
STATUS: COMPLETED

- 타입: chore
- 관련 PRD 섹션: 5. 시스템 아키텍처
- 우선순위: P1
- 예상 난이도: M
- 관련 MCP 도구: context7 (APScheduler)
- 목적:
  - 전체 파이프라인을 스케줄러에 등록하여 자동화한다.
- 상세 작업 내용:
  - [x] `main_scheduler.py` 구현 (APScheduler 설정)
  - [x] Job 등록: 수집(00:00), 학습(04:00), 예측(08:30)
  - [x] 통합 테스트 (`tests/test_integration.py`)
- 변경 예상 파일/모듈:
  - `main_scheduler.py`
- 완료 기준(Acceptance Criteria):
  - [x] 스크립트 실행 시 정해진 시각(또는 강제 트리거)에 파이프라인이 순차적으로 실행되어야 함.

## TASK-011: Historical Data Collection Script
STATUS: COMPLETED

- 타입: feature
- 관련 PRD 섹션: 3.1 모듈 A (FR-A06)
- 우선순위: P1
- 예상 난이도: M
- 관련 MCP 도구: context7 (Requests)
- 목적:
  - 초기 학습 데이터 확보를 위해 삼성전자, SK하이닉스의 과거 6개월치 뉴스를 수집한다.
- 상세 작업 내용:
  - [x] `src/collector/news.py`: `crawl_naver_finance_news` 메서드에 `date_limit` 파라미터 추가 및 랜덤 딜레이 적용.
  - [x] `src/scripts/collect_history.py` 작성: 6개월치 수집 실행 스크립트.
- 변경 예상 파일/모듈:
  - `src/collector/news.py`, `src/scripts/collect_history.py`
- 완료 기준(Acceptance Criteria):
  - [x] 6개월 전 날짜의 뉴스까지 수집되고, IP 차단 없이 완료되어야 함.

## TASK-012: Cloudflare WARP Integration for IP Rotation
STATUS: COMPLETED

- 타입: feature
- 관련 PRD 섹션: 3.1 모듈 A (FR-A07)
- 우선순위: P1
- 예상 난이도: M
- 관련 MCP 도구: context7 (Cloudflare WARP)
- 목적:
  - 대량 데이터 수집 시 IP 차단을 회피하기 위해 VPN(WARP)을 이용해 주기적으로 IP를 변경한다.
- 상세 작업 내용:
  - [x] `src/utils/vpn.py`: `CloudflareWARP` 클래스 구현 (connect, disconnect, rotate).
  - [x] `src/scripts/collect_history.py`: 수집 루프 내에서 주기적으로(예: 100페이지마다) IP 회전 호출.
  - [x] Docker 환경 내 WARP 설치 가이드 또는 스크립트 제공.
- 변경 예상 파일/모듈:
  - `src/utils/vpn.py`, `src/scripts/collect_history.py`
- 완료 기준(Acceptance Criteria):
  - [x] 스크립트 실행 중 주기적으로 외부 IP가 변경됨을 로그로 확인.
  - [x] WARP 미설치 환경에서도 예외 없이(기능 비활성화) 동작해야 함.

## TASK-013: Enhanced Daily Report
STATUS: COMPLETED

- 타입: feature
- 관련 PRD 섹션: 7.3 모듈 C (FR-C04, FR-C05, FR-C06)
- 우선순위: P1
- 예상 난이도: M
- 관련 MCP 도구: context7 (Pandas, Markdown)
- 목적:
  - 예측 결과의 설명력을 높이기 위해 상위 키워드, 뉴스 목록, 감성 통계, 신뢰도 점수 등을 리포트에 포함한다.
- 상세 작업 내용:
  - [x] `src/predictor/scoring.py`: 상위 10개 키워드 및 뉴스별 감성 통계 추출 로직 구현.
  - [x] `src/predictor/report.py`: Markdown 리포트 포맷 개선 (트리 구조, Sparkline, Confidence Score).
  - [x] 신뢰도 점수 산출 로직 구현 (뉴스 수, 감성 강도 기반).
- 변경 예상 파일/모듈:
  - `src/predictor/scoring.py`, `src/predictor/report.py`
- 완료 기준(Acceptance Criteria):
  - [x] 리포트에 상위 10개 키워드와 각 키워드별 뉴스 제목, 감성 통계가 출력되어야 함.
  - [x] 신뢰도 점수가 0~100 사이 값으로 표시되어야 함.

## TASK-019: Report Refinement - News Filtering
STATUS: COMPLETED

- 타입: feature
- 관련 PRD 섹션: 7.3 모듈 C (FR-C04)
- 우선순위: P1
- 예상 난이도: S
- 관련 MCP 도구: filesystem
- 목적:
  - 예측 리포트의 뉴스 목록이 너무 길어지는 문제를 해결하기 위해, 긍정/부정 상위 10건씩 분리하여 표시한다.
- 상세 작업 내용:
  - [x] `src/predictor/scoring.py`: 예측 결과에 `top_positive_news`, `top_negative_news` 추가 및 `top_keywords`에서 뉴스 제거.
  - [x] `src/predictor/report.py`: 리포트 생성 시 긍정/부정 뉴스 섹션 추가 및 키워드 표시 방식 변경.
- 변경 예상 파일/모듈:
  - `src/predictor/scoring.py`, `src/predictor/report.py`
- 완료 기준(Acceptance Criteria):
  - [x] 리포트에 "Top 10 Positive News"와 "Top 10 Negative News" 섹션이 구분되어 출력되어야 함.
  - [x] 각 뉴스 항목에 감성 점수(Mean/Sum)가 표시되어야 함.

## TASK-014: Generalization Verification
STATUS: COMPLETED

- 타입: feature
- 관련 PRD 섹션: 7.3 모듈 C (FR-C08)
- 우선순위: P1
- 예상 난이도: M
- 관련 MCP 도구: context7 (FinanceDataReader)
- 목적:
  - 과거 예측(D-1, D-2)의 정확도를 실제 주가와 비교하여 검증하고 리포트를 생성한다.
- 상세 작업 내용:
  - [x] `src/predictor/verifier.py`: 검증 로직 구현 (예측 신호 vs 실제 수익률).
  - [x] `main_scheduler.py`: 매일 장 마감 후(또는 익일) 검증 작업 스케줄링.
  - [x] 검증 결과 리포트 생성 (Markdown/JSON).
- 변경 예상 파일/모듈:
  - `src/predictor/verifier.py`, `main_scheduler.py`
- 완료 기준(Acceptance Criteria):
  - [x] 월요일 예측(BUY)에 대해 화요일 주가가 상승했으면 '성공', 하락했으면 '실패'로 판정되어야 함.

## TASK-015: Streamlit Dashboard
STATUS: COMPLETED

- 타입: feature
- 관련 PRD 섹션: 7.3 모듈 C (FR-C09)
- 우선순위: P2
- 예상 난이도: M
- 관련 MCP 도구: context7 (Streamlit)
- 목적:
  - 웹 대시보드를 통해 일/주/월 단위 예측 결과와 검증 현황을 시각적으로 모니터링한다.
- 상세 작업 내용:
  - [x] `src/dashboard/app.py`: Streamlit 앱 기본 구조 작성.
  - [x] DB 연동 및 리포트 데이터(JSON) 로딩 기능 구현.
  - [x] 예측 결과 탭 및 검증 현황 탭 구현.
  - [x] `docker-compose.yml`: Streamlit 서비스 추가.
- 변경 예상 파일/모듈:
  - `src/dashboard/app.py`, `docker-compose.yml`
- 완료 기준(Acceptance Criteria):
  - [x] 브라우저로 대시보드 접속 시 최신 예측 결과와 과거 검증 성공률이 그래프로 표시되어야 함.

## TASK-016: Backtesting Engine Core
STATUS: COMPLETED

- 타입: feature
- 관련 PRD 섹션: 7.3 모듈 C (FR-C10)
- 우선순위: P1
- 예상 난이도: H
- 관련 MCP 도구: context7 (Pandas)
- 목적:
  - 과거 데이터를 기반으로 모델 학습 및 예측 시뮬레이션을 수행할 수 있는 백테스팅 엔진을 구현한다.
- 상세 작업 내용:
  - [x] `src/backtester/engine.py`: `Backtester` 클래스 구현.
    - 데이터 로드 및 기간 분할 (Train/Test).
    - 시뮬레이션 루프 (날짜별 순회).
    - `Learner` 및 `Predictor` 모듈 호출 인터페이스 정의.
  - [x] `src/backtester/metrics.py`: 성과 지표 계산 (누적 수익률, 승률, MDD).
- 변경 예상 파일/모듈:
  - `src/backtester/engine.py`, `src/backtester/metrics.py`
- 완료 기준(Acceptance Criteria):
  - [x] 지정된 기간(Start~End)에 대해 하루씩 진행하며 학습->예측->검증 프로세스가 에러 없이 동작해야 함.

## TASK-017: Backtesting Scenarios Implementation
STATUS: COMPLETED

- 타입: feature
- 관련 PRD 섹션: 7.3 모듈 C (FR-C10)
- 우선순위: P1
- 예상 난이도: M
- 관련 MCP 도구: context7
- 목적:
  - PRD에 정의된 두 가지 백테스팅 시나리오(Static Split, Rolling Window)를 실행할 수 있는 스크립트를 작성한다.
- 상세 작업 내용:
  - [x] `src/scripts/run_backtest.py`: CLI 인자로 시나리오 선택 기능 구현.
  - [x] **Scenario A (Static):** 6개월 데이터(4개월 학습 -> 2개월 검증) 및 리포트 생성.
  - [x] **Scenario B (Rolling):** 1년 데이터(9개월 학습 -> 3개월 롤링 업데이트/예측/검증) 및 리포트 생성.
- 변경 예상 파일/모듈:
  - `src/scripts/run_backtest.py`
- 완료 기준(Acceptance Criteria):
  - [x] `python run_backtest.py --scenario A` 실행 시 4개월 학습 후 2개월치 예측 결과가 생성되어야 함.
  - [x] `python run_backtest.py --scenario B` 실행 시 매일 모델이 업데이트되며 3개월치 예측 결과가 생성되어야 함.

## TASK-018: Backtesting Report Generation
STATUS: COMPLETED

- 타입: feature
- 관련 PRD 섹션: 7.3 모듈 C (FR-C10)
- 우선순위: P2
- 예상 난이도: M
- 관련 MCP 도구: context7 (Matplotlib/Seaborn)
- 목적:
  - 백테스팅 결과를 분석하여 시각화된 리포트를 생성한다.
- 상세 작업 내용:
  - [x] `src/backtester/report.py`: 백테스팅 결과(CSV)를 읽어 리포트 생성.
  - [x] 누적 수익률 그래프, 일별 승률 변화 그래프 등 시각화.
  - [x] 최종 요약 통계 (Total Return, Win Rate, MDD) 출력.
- 변경 예상 파일/모듈:
  - `src/backtester/report.py`
- 완료 기준(Acceptance Criteria):
  - [x] 백테스팅 완료 후 `output/backtest_report_{date}.md` 및 이미지 파일이 생성되어야 함.

## TASK-020: OOV Handling & Logging
STATUS: COMPLETED

- 타입: feature
- 관련 PRD 섹션: 7.3 모듈 C (FR-C03), 7.2 모듈 B (FR-B05)
- 우선순위: P1
- 예상 난이도: M
- 관련 MCP 도구: context7 (Polars)
- 목적:
  - OOV(미등록 단어) 비율이 높을 경우 예측을 보류(Hold)하고, 신조어를 식별하여 로그를 남긴다.
- 상세 작업 내용:
  - [x] `src/predictor/scoring.py`: OOV 비율 계산 및 임계치(30%) 초과 시 'HOLD' 신호 강제 적용.
  - [x] `src/predictor/scoring.py`: OOV 단어 목록 추출 및 로그 파일(`logs/oov_log.txt`) 또는 DB에 저장.
- 변경 예상 파일/모듈:
  - `src/predictor/scoring.py`
- 완료 기준(Acceptance Criteria):
  - [x] OOV 비율이 31%인 뉴스 데이터에 대해 예측 신호가 'HOLD'로 반환되어야 함.
  - [x] 예측 수행 후 OOV 단어들이 로그에 기록되어야 함.

## TASK-021: Wordcloud Visualization
STATUS: COMPLETED

- 타입: feature
- 관련 PRD 섹션: 7.3 모듈 C (FR-C07)
- 우선순위: P2
- 예상 난이도: S
- 관련 MCP 도구: context7 (Wordcloud)
- 목적:
  - 데일리 리포트에 주요 키워드를 시각적으로 보여주는 워드클라우드 이미지를 첨부한다.
- 상세 작업 내용:
  - [x] `src/predictor/report.py`: `wordcloud` 라이브러리를 사용하여 키워드 빈도/가중치 기반 이미지 생성.
  - [x] 생성된 이미지를 `output/`에 저장하고 Markdown 리포트에 링크 포함.
- 변경 예상 파일/모듈:
  - `src/predictor/report.py`
- 완료 기준(Acceptance Criteria):
  - [x] 리포트 생성 시 `wordcloud_{date}.png` 파일이 생성되고 Markdown에 표시되어야 함.

## TASK-022: Collector Refactoring - Date-based Pagination
STATUS: NOT_STARTED

- 타입: refactor
- 관련 PRD 섹션: 3.1 모듈 A (FR-A06)
- 우선순위: P0
- 예상 난이도: M
- 관련 MCP 도구: context7 (Requests, BeautifulSoup)
- 목적:
  - 네이버 금융 뉴스 목록의 페이지 제한(약 1000페이지)을 우회하여 1년치 이상의 대량 데이터를 수집하기 위해, 날짜 단위로 분할하여 요청하는 로직으로 개선한다.
- 상세 작업 내용:
  - [ ] `src/collector/news.py`: `crawl_naver_finance_news` 메서드 리팩터링.
    - 기존: 페이지 1부터 순차 증가 (Stop Date 도달 시 중단).
    - 변경: 시작일~종료일 범위를 하루(1 Day) 단위로 순회하며 수집.
  - [ ] URL 변경 검토: `item/news_news.naver`가 날짜 필터를 지원하지 않을 경우 `search.naver.com` (뉴스 검색) 또는 다른 엔드포인트로 변경.
  - [ ] `src/scripts/collect_history.py`: 변경된 수집 로직에 맞춰 파라미터(기간) 설정.
- 변경 예상 파일/모듈:
  - `src/collector/news.py`, `src/scripts/collect_history.py`
- 완료 기준(Acceptance Criteria):
  - [ ] 1년치(약 365일) 루프가 정상적으로 돌며, 각 날짜별로 뉴스가 수집되어야 함.
  - [ ] 총 수집된 뉴스 건수가 기존 방식(페이지 제한)보다 월등히 많아야 함 (예: 1년치 > 10,000건).

## TASK-023: Base Image - `base-mecab` 생성
STATUS: TODO

- 타입: infra
- 관련 PRD 섹션: 10. 아키텍처 분해 및 운영 지침
- 우선순위: P0
- 예상 난이도: M
- 목적:
  - MeCab 및 `mecab-ko-dic`과 사용자사전 컴파일 도구(`mecab-dict-index`)를 포함하는 재현 가능한 베이스 이미지를 생성한다.
- 상세 작업 내용:
  - `docker/images/base-mecab/Dockerfile` 작성: MeCab 설치, mecab-ko-dic 설치, locale 및 의존성 설정.
  - 빌드 시 `mecab-dict-index`를 사용할 수 있도록 환경 구성.
  - CI에서 빌드하여 내부 레지스트리에 태그된 이미지를 업로드하는 작업(별도 TASK로 연계).
- 변경 예상 파일/모듈:
  - `docker/images/base-mecab/Dockerfile`, CI 워크플로우(추가)
- 완료 기준(Acceptance Criteria):
  - `docker build -t registry/stock_words/base-mecab:latest docker/images/base-mecab` 명령이 성공하고, 컨테이너 내부에서 `mecab` 명령과 `mecab-dict-index`가 사용 가능해야 함.

## TASK-024: Tokenizer 컨테이너화 및 사용자사전 검증
STATUS: IN-PROGRESS

- 타입: feature
- 관련 PRD 섹션: 10. 아키텍처 분해 및 운영 지침, 5. 시스템 아키텍처
- 우선순위: P0
- 예상 난이도: M
- 목적:
  - `tokenizer`를 별도 서비스로 분리하여 `base-mecab`을 기반으로 빌드하고, `data/user_dic.csv`에 따른 토큰화 재현성을 검증한다.
-- 상세 작업 내용:
  - `docker/tokenizer/Dockerfile`을 `base-mecab` 기반으로 재작성(원격 git clone 제거).
  - 이미지에 기본 사전(.dic) 포함 또는 CI 아티팩트 방식 명시.
  - `USER_DIC_PATH` 환경변수로 런타임 사용자사전 경로를 주입하고 단위테스트(예: '2차전지' 케이스)를 추가.
  - `docker-compose.override.yml`로 로컬 스모크 테스트 설정 추가.
  - 비고: 런타임에서 `USER_DIC_PATH`를 읽어 worker에 로드하는 구현은 `src/tokenizer_service.py`에 반영되어 있음. 다만 Dockerfile 및 테스트 케이스가 필요함.
- 변경 예상 파일/모듈:
  - `docker/tokenizer/Dockerfile`, `tests/test_tokenizer_repro.py`, `docker-compose.override.yml`
- 완료 기준(Acceptance Criteria):
  - 토크나이저 컨테이너를 띄운 후 `POST /tokenize` 호출 시 `data/user_dic.csv`에 등록된 단어(예: '2차전지')가 단일 토큰으로 반환되어야 함.

## TASK-025: CI 파이프라인 - 이미지 빌드 및 토큰화 단위테스트
STATUS: TODO

- 타입: infra
- 관련 PRD 섹션: 10. 아키텍처 분해 및 운영 지침, 8. 품질 기준
- 우선순위: P0
- 예상 난이도: M
- 목적:
  - GitHub Actions(또는 선택 CI)에 베이스 이미지 및 서비스 이미지 빌드, 보안 스캔, 토크나이저 단위테스트를 자동화한다.
- 상세 작업 내용:
  - `ci/build-base-mecab.yml`: base-mecab 이미지 빌드 및 레지스트리 푸시.
  - `ci/build-and-test-tokenizer.yml`: tokenizer 이미지 빌드 후 컨테이너를 띄워 토큰화 단위테스트 실행.
  - 시크릿(레지스트리 자격증명)은 GitHub Secrets로 관리.
- 변경 예상 파일/모듈:
  - `.github/workflows/build-base-mecab.yml`, `.github/workflows/build-tokenizer.yml`
- 완료 기준(Acceptance Criteria):
  - PR 생성 시 CI가 자동으로 이미지 빌드 및 토큰화 단위테스트를 통과해야만 Merge 가능하도록 보호되어야 함.

## TASK-026: Kubernetes/Helm 초안 작성
STATUS: TODO

- 타입: chore
- 관련 PRD 섹션: 10. 아키텍처 분해 및 운영 지침
- 우선순위: P1
- 예상 난이도: M
- 목적:
  - 장기 배포를 위한 Kubernetes 매니페스트(Deployment/Service/ConfigMap/Secret/PVC)와 Helm 차트 템플릿 초안을 작성한다.
- 상세 작업 내용:
  - `helm/n-sentitrader/` 디렉토리 생성: tokenizer, collector, predictor 등 서비스별 Chart 템플릿 생성.
  - `user_dic`은 `ConfigMap`(작은 파일) 또는 `PersistentVolumeClaim`로 마운트하는 예시 제공.
  - readiness/liveness probe, 리소스 요청/제한 예시 추가.
- 변경 예상 파일/모듈:
  - `helm/n-sentitrader/Chart.yaml`, `helm/n-sentitrader/templates/*.yaml`
- 완료 기준(Acceptance Criteria):
  - `helm template helm/n-sentitrader` 명령이 정상적으로 렌더링되어 배포 가능한 매니페스트를 출력해야 함.

## TASK-027: 사용자사전 핫리로드(설계) 및 InitContainer 패턴
STATUS: TODO

- 타입: design
- 관련 PRD 섹션: 10. 아키텍처 분해 및 운영 지침
- 우선순위: P1
- 예상 난이도: M
- 목적:
  - 사용자사전 변경을 운영 중에도 안전하게 반영할 수 있는 핫리로드 패턴(InitContainer 컴파일 또는 모델 swap)을 설계한다.
- 상세 작업 내용:
  - InitContainer로 `user_dic.csv`를 받아 `mecab-dict-index`로 컴파일 후 공유 볼륨에 저장하는 예시 구현안 작성.
  - 런타임에서 교체 시 `Model::swap` 또는 롤링 재시작 방식 중 선택 가이드 제시.
  - 테스트 케이스: 사전 변경 후 토큰화 결과가 예상대로 바뀌는지 검증하는 절차 문서화.
- 변경 예상 파일/모듈:
  - `docs/ops/userdic-hotreload.md`, Helm 템플릿 내 `initContainer` 예시
- 완료 기준(Acceptance Criteria):
  - 문서화된 절차에 따라 initContainer 방식으로 사전이 컴파일되어 tokenizer Pod가 올바르게 해당 사전을 사용해야 함.

## TASK-028: 단계적 마이그레이션 계획 및 스모크 테스트
STATUS: TODO

- 타입: chore
- 관련 PRD 섹션: 10. 아키텍처 분해 및 운영 지침
- 우선순위: P0
- 예상 난이도: M
- 목적:
  - 기존 `core` 컨테이너에서 단계적으로 기능을 분리하는 마이그레이션 계획과 각 단계별 스모크 테스트 체크리스트를 작성한다.
- 상세 작업 내용:
  - 단계 1: `tokenizer` 분리 → 스모크 테스트(토큰화 재현성)
  - 단계 2: `collector` 분리 → 스모크 테스트(수집 파이프라인 통합)
  - 단계 3: `learner`/`predictor` 분리 및 모델 서빙 이전 → 스모크 테스트(예측 정확도 및 리포트)
  - 각 단계별 롤백 절차 및 검증 스크립트 작성.
- 변경 예상 파일/모듈:
  - `docs/migration/migration-plan.md`, `tests/smoke/*`
- 완료 기준(Acceptance Criteria):
  - 각 단계별 스모크 테스트가 정의되어 있고, 담당자가 수동/자동으로 실행하여 통과할 수 있어야 함.
