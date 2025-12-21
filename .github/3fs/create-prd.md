<!-- .github/3fs/create-prd.md -->

# 목적

이 리포지토리(n-sentitrader-3fs)는  
**「N-SentiTrader: 뉴스 텍스트 마이닝 기반 동적 감성사전 및 주가 예측 시스템」**을 구축하는 것을 목표로 합니다.

이 프로젝트는 다음의 핵심 기술 스택을 기반으로 합니다:
- **Infra:** Docker Container + Ubuntu + PostgreSQL 15+
- **Core:** Python 3.10+ (Polars, Mecab-ko, Scikit-learn Lasso)
- **Methodology:** Dual-Track Ensemble (Main/Buffer) + Time Decay + 3-File System

이 파일은 GitHub Copilot Agent(이하 “에이전트”)가  
**새 PRD를 생성하거나 기존 PRD를 갱신할 때 반드시 따라야 할 규칙**을 정의합니다.

PRD는 항상 다음 경로에 작성합니다.

- `docs/prd/n-sentitrader-prd.md`

---

# PRD 생성/갱신 지침

1. 사용자가 새로운 기능/요구사항/구조 변경을 요청하면, 코드를 바로 수정하지 말고 **먼저 PRD를 생성 또는 갱신**해야 합니다.
2. PRD는 **명세(Spec)** 이며, 이 리포지토리에서 **코드는 PRD를 따릅니다.**
3. PRD 변경 후에는 `.github/3fs/generate-tasks.md` 규칙에 따라 **TASK 목록을 반드시 갱신**합니다.
4. 모든 작업은 `copilot-instructions.md`의 **핵심 운영 원칙**을 최우선으로 따릅니다.

---

# PRD 파일 구조

에이전트는 `docs/prd/n-sentitrader-prd.md`를 아래 섹션 구조로 유지해야 합니다.

1. 개요(Overview)
2. 대상 사용자 및 사용 시나리오
3. 범위(Scope: In / Out)
4. 데이터 모델 및 스키마 설계
5. 시스템 아키텍처 및 파이프라인
6. 기술 스택 (Tech Stack)
7. 데이터베이스 스키마 (Database Schema)
8. 테스트 전략 (Test Strategy)
9. 사고 이력 및 향후 과제 (Incident History & Future Tasks)

아래는 각 섹션에 포함해야 할 내용 가이드입니다.

---

## 1. 개요(Overview)

- **한 줄 요약:** 뉴스 단어의 영향력을 수치화한 동적 감성사전을 구축하고, 이를 통해 특정 종목의 익일 시장 초과 수익률(Alpha)을 예측하는 시스템.
- **배경:**
  - 기존 감성 분석의 단순 긍/부정 이분법 한계 극복.
  - 단어의 영향력(Magnitude)과 유효 기간(Time Decay)을 반영한 금융 특화 사전 필요.
- **목표:**
  - 주간 학습(Lasso)과 일간 보정(Buffer)을 결합한 이원화 모델 구축.
  - 시장 지수(Benchmark) 대비 초과 수익 여부(Binary Classification) 예측.

---

## 2. 대상 사용자 및 사용 시나리오

- **주요 사용자:**
  - 시스템 관리자 (모델 학습 상태 및 서버 모니터링)
  - 퀀트 트레이더/분석가 (장 시작 전 매매 시그널 참고)
- **대표 사용 시나리오:**
  - “내일 삼성전자가 코스피 지수보다 더 오를지 예측하고 싶다.”
  - “최근 '2차전지' 관련 키워드가 시장에 미치는 감성 점수가 어떻게 변했는지 확인하고 싶다.”
  - “어제 발생한 돌발 악재가 오늘 주가에 얼마나 반영될지(Buffer Model) 보고 싶다.”

---

## 3. 범위(Scope: In / Out)

- **In Scope:**
  - **데이터:** 국내 포털(네이버/다음) 금융 뉴스, KOSPI/KOSDAQ 전 종목 OHLCV.
  - **인프라:** Docker Compose 기반의 App 및 PostgreSQL 컨테이너 구성.
  - **핵심 로직:**
    - 시간 감쇠(Time Decay): 주말을 포함한 달력일(Calendar Day) 기준 적용.
    - 시장 매칭: KOSPI 종목은 KOSPI 지수와, KOSDAQ 종목은 KOSDAQ 지수와 비교.
    - 사용자 사전: '밸류업', '2차전지' 등 금융 신조어 처리.
  - **출력:** JSON 포맷의 데일리 리포트.
- **Out of Scope:**
  - 실시간 스트리밍 처리 (Daily Batch로 제한).
  - 해외 주식 및 ETF (초기 버전은 국내 개별 종목 한정).
  - 복잡한 웹 프론트엔드 (CLI 및 JSON 출력 위주).

---

## 4. 데이터 모델 및 스키마 설계

PostgreSQL 15+ 기반의 스키마 설계를 명시합니다.

- **주요 테이블:**
  - `tb_stock_master`: 종목 코드, 시장 타입(KOSPI/KOSDAQ).
  - `tb_daily_price`: 종가, 등락률, **초과 수익률(Excess Return)**.
  - `tb_news_raw`: 뉴스 원문, 발행일시, **전처리된 키워드(JSONB)**.
  - `tb_sentiment_dict`: 단어, 베타 계수, 버전, 소스(Main/Buffer).
- **데이터 원칙:**
  - 모든 경로는 Docker 내부 경로(`/app/data` 등)를 기준으로 서술.
  - 정형 데이터와 비정형 데이터(뉴스)의 조인 전략 명시.

---

## 5. 시스템 아키텍처 및 파이프라인

3단계 파이프라인의 흐름을 기술합니다.

1.  **Collector (수집):**
    - 매일 자정~새벽 수행.
    - 학습용(과거)과 추론용(최근) 데이터 분리 적재.
2.  **Learner (학습):**
    - **Track A (Main):** 주 1회, 과거 3개월 데이터, Lasso 회귀(자동 검증).
    - **Track B (Buffer):** 매일, 최근 3일 데이터, 변동성 가중치 기반 급등 키워드 포착.
    - **Update:** EMA(지수이동평균)를 이용한 사전 점수 갱신.
3.  **Predictor (예측):**
    - 매일 08:30 수행.
    - 앙상블 가중치($w_1, w_2$) 적용 후 최종 매수/관망 신호 생성.

---

## 6. MCP 도구 사용 전략

- **filesystem MCP:**
  - `src/` 내의 Python 모듈 읽기/쓰기.
  - `docs/prd/`, `docs/trd/` 문서 관리.
  - `docker-compose.yml` 및 설정 파일 관리.
- **PostgreSQL 연동 (via Python script):**
  - 직접적인 DB 쿼리 실행보다는 `src/utils/db.py` 등을 통한 간접 제어 권장.
  - 스키마 변경(DDL) 시에는 마이그레이션 스크립트 작성 필수.
- **Command Line:**
  - Docker 빌드 및 실행 테스트(`docker-compose up`) 관련 가이드.

---

## 7. 구현 범위 및 모듈 구조

- **핵심 모듈 (`src/`):**
  - `collector.py`: Polars 활용 고속 데이터 로딩.
  - `preprocessor.py`: Mecab-ko + 사용자 사전 로드 및 전처리.
  - `learner.py`: Scikit-learn Lasso 학습 및 사전 생성.
  - `predictor.py`: 앙상블 로직 및 JSON 리포트 생성.
  - `utils.py`: DB 연결(SQLAlchemy) 및 공통 함수.
- **설정 및 환경:**
  - `config/config.yaml`: 시스템 상수(Lasso Alpha, Decay Lambda 등).
  - `Dockerfile` & `docker-compose.yml`: 배포 환경.
- **테스트 (`tests/`):**
  - TDD 원칙 준수.

---

## 8. 품질 기준 및 평가 방법

- **정량적 기준:**
  - 방향성 정확도(Precision) **55% 이상**.
  - 백테스팅 시 시장 지수 대비 **초과 수익(Alpha) 발생**.
- **안정성 기준:**
  - 데이터 수집 실패 시 롤백(Rollback) 메커니즘 정상 동작 확인.
  - 예측 리포트가 장 시작 전(08:30)까지 생성 완료될 것.

---

## 9. 오픈 이슈 및 향후 과제

- **사용자 사전 유지보수:** 신조어(OOV) 자동 탐지 및 등록 프로세스 고도화.
- **해외 확장:** 미국 주식(S&P500) 데이터 파이프라인 추가 계획.
- **모델 개선:** Transformer(BERT/FinBERT) 기반의 문맥 분석 도입 검토.

---

# 에이전트 작업 규칙 요약

1. 새로운 기능/요구사항이 생기면 **반드시 이 파일 규칙에 따라 PRD를 먼저 작성/갱신**합니다.
2. PRD 변경 내용이 정리되면, `.github/3fs/generate-tasks.md` 규칙으로 TASK를 생성/갱신합니다.
3. PRD가 모호하거나 구체성이 부족하면, 구현을 진행하지 말고 PRD를 더 구체화합니다. (TRD 참조 권장)
4. PRD와 실제 구현(코드/인프라)이 항상 일치하도록, 변경 시마다 PRD를 최신 상태로 유지합니다.