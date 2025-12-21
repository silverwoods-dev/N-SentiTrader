# N-SentiTrader PRD (Merged Draft)

Status: DRAFT — Integrated additions from `n-sentitrader-prd-addendum-collection-dashboard.md` and `n-sentitrader-prd-update-draft.md`.

> 주의: 이 파일은 통합 초안입니다. 원본 `docs/prd/n-sentitrader-prd.md`는 변경하지 않았습니다. 작업(태스크)으로 전환하지 말고 사용자 확인을 기다려주세요.


## 우선순위 및 지침 준수

- 본 프로젝트에서 에이전트(자동화 도구 포함)가 수행하는 모든 작업은 `/home/dev/stock_words/.github/copilot-instructions.md`의 규칙을 최우선으로 준수해야 합니다.
- 특히 문서·지침·검토 요청 시 기본 커뮤니케이션 언어는 한국어로 하며, 운영 환경은 Docker 컨테이너, 개발 환경은 `uv` 기반의 `venv`를 우선 고려합니다.
- 테스트 계획은 PRD/Tasks 워크플로우에 따라 `docs/tasks/n-sentitrader-tasks.md`의 항목으로 등록하고 실행·검증합니다. 임시 문서는 아카이브 처리 후 TASKS에 링크합니다.


## 1. 개요(Overview)
- **한 줄 요약:** 뉴스 텍스트 마이닝을 통해 단어별 영향력을 수치화한 동적 감성사전을 구축하고, 이를 바탕으로 특정 종목이 익일 시장 대비 초과 수익(Alpha)을 낼지 예측하는 시스템.
- **배경:**
  - 기존 감성 분석의 단순 긍/부정 이분법 한계 극복.
  - 금융 시장 특성을 반영하여 단어의 영향력(Magnitude)과 유효 기간(Time Decay)을 수치화할 필요성.
- **목표:**
  - **동적 감성사전:** 주간 학습(Lasso)과 일간 보정(Buffer)을 결합한 이원화 모델 구축.
  - **초과 수익 예측:** 시장 지수(Benchmark) 대비 초과 수익 여부(Binary Classification) 예측.
  - **신뢰성 확보:** 정교한 데이터 매칭(시장별 지수)과 현실적인 시차 적용(달력일 기준).


## 2. 대상 사용자 및 사용 시나리오
- **주요 사용자:**
  - **시스템 관리자:** 매일 아침 자동 생성된 리포트 정합성 확인, 주간 모델 성능 모니터링.
  - **투자자/트레이더:** 예측 리포트의 '매수' 신호와 근거(Top 3 키워드)를 참고하여 장 시초가 매매 수행.
- **사용 시나리오:**
  - "내일 삼성전자가 KOSPI 지수보다 더 오를지 예측하고 싶다."
  - "최근 '밸류업' 관련 뉴스가 시장에 미치는 긍/부정 점수가 어떻게 변했는지 확인하고 싶다."
  - "주말 동안 발생한 악재가 월요일 장에 얼마나 반영될지 미리 파악하고 싶다."


## 3. 범위(Scope: In / Out)
- **In Scope:**
  - **데이터:** 국내 포털 금융 뉴스(제목, 본문), KOSPI/KOSDAQ 전 종목 OHLCV 및 시장 지수.
  - **핵심 로직:**
    - **N-gram 분석:** 단어(Unigram)뿐만 아니라 구문(Bigram, Trigram) 단위의 감성 분석 수행.
    - **시장 매칭:** KOSPI 종목 ↔ KOSPI 지수, KOSDAQ 종목 ↔ KOSDAQ 지수 비교.
    - **시간 감쇠:** 거래일이 아닌 **달력일(Calendar Day)** 기준 감쇠 적용 (주말 효과 반영).
    - **사용자 사전:** '2차전지', '밸류업' 등 금융 신조어 처리.
  - **인프라:** Docker Container 기반의 독립 실행 환경.
    - **VPN:** Cloudflare WARP (IP Rotation) 적용.
- **Out of Scope:**
  - 실시간 스트리밍 데이터 처리 (Daily Batch로 제한).
  - 해외 주식 및 ETF (초기 버전은 국내 개별 종목 한정).
  - 웹 프론트엔드 개발 (CLI 및 JSON/File 리포트 위주) — 다만 관리자 대시보드(내부 관리자용)는 포함.


## 4. 데이터 모델 및 스키마 설계
PostgreSQL 15+ 기반의 스키마를 사용합니다.

- **주요 테이블:**
  - `tb_stock_master`: 종목 코드, 종목명, 시장 구분(KOSPI/KOSDAQ).
  - `tb_market_index`: 일자, 시장구분, 종가, 등락률.
  - `tb_daily_price`: 일자, 종목코드, OHLCV, 등락률, **초과 수익률(Y)**.
  - `tb_news_content`: 뉴스 원문, 제목 해시(중복방지), **전처리된 토큰(JSONB)**.
  - `tb_news_mapping`: 뉴스ID-종목코드 매핑, **시장 반영일(Impact Date)**.
  - `tb_sentiment_dict`: 단어, 가중치(Beta), 버전(날짜), 소스(Main/Buffer).
- **데이터 원칙:**
  - 원시 텍스트는 최소 3년 보관.
  - **벡터/분석 데이터는 최소 1년 보관.**
  - 학습용(D-7일 이전)과 추론용(최근 7일) 데이터 뷰(View) 분리.
  - **사용자 사전:** `user_dic.csv`는 소스 코드와 분리하여 별도 관리하며, 서버 재기동 없이 로드 가능해야 함.


## 5. 시스템 아키텍처 및 파이프라인
Docker Compose를 통해 App 컨테이너와 DB 컨테이너가 격리된 네트워크에서 통신합니다.

- **Runtime:** Python 3.10-slim (Docker)
- **Database:** PostgreSQL 15-alpine
- **Data Processing:** Polars (대용량 텍스트 고속 처리), Mecab (C++ 기반 고속 형태소 분석)
- **Scheduling:** APScheduler (컨테이너 내부 데몬 스케줄링)
- **Directory Standard:** `/app/data` (영구 저장), `/app/output` (리포트 출력)
- **Pipeline (요약):**
  1. **Collector:** 뉴스 주소 수집 → 중복 제거 → URL 저장.
  2. **Body Collector:** 주소 목록 기반 본문 수집(제목/본문/메타) → 수집 완료 표시.
  3. **Preprocessor/Tokenizer:** 토크나이징 및 전처리 → `preprocessed=true` 표기.
  4. **Learner:** 주간/일간 학습(메인/버퍼 단어사전 구축).
  5. **Predictor:** 사전 매칭 및 점수 산출 → 리포트 생성.


## 6. MCP 도구 사용 전략
- **filesystem:** 프로젝트 구조 탐색 및 파일 읽기/쓰기. 대규모 변경 시 사용자 승인 필요.
- **context7:** 최신 라이브러리(Polars, Scikit-learn 등) 사용법 및 Best Practice 조회.
- **PostgreSQL (Optional):** DB 쿼리 검증 및 스키마 마이그레이션 지원.


## 7. 구현 범위 및 모듈 구조
### 7.1 모듈 A: 데이터 수집기 (Collector)
- **FR-A01:** 포털 금융 뉴스 주소 수집 (제목/본문은 별도 본문 수집기에서 처리).
- **FR-A02:** 주가 및 시장 지수(KOSPI/KOSDAQ) 수집.
- **FR-A03:** 뉴스 중복 제거 (유사도 90% 이상).
- **FR-A04:** 학습/추론 데이터셋 분리 뷰 제공.
- **FR-A05:** 타겟 라벨링 (시장 지수 대비 초과 수익 여부).
- **FR-A06:** VPN IP Rotation (대량 수집 시 차단 방지).
- **FR-A07:** 과거 데이터 수집 (Cold Start 해결을 위한 대량 수집 유틸리티).

### 7.2 모듈 B: 학습 및 감성사전 구축기 (Learner)
- **FR-B01:** Mecab 형태소 분석 및 N-gram (1~3) 생성 (단어 및 구문 학습).
- **FR-B02:** Main 모델 학습 (Lasso, 주간, 3개월 데이터).
- **FR-B03:** Buffer 모델 학습 (일간, 최근 데이터 반영).
- **FR-B04:** 사전 병합 및 EMA 업데이트.
- **FR-B05:** OOV(미등록 단어) 모니터링 및 로그.

### 7.3 모듈 C: 예측 및 리포팅 (Predictor)
- **FR-C01:** 달력일(Calendar Day) 기준 시간 감쇠 적용.
- **FR-C02:** 앙상블 점수 산출 및 매수/관망 신호 생성.
- **FR-C03:** OOV 비율 과다 시 예외 처리.
- **FR-C04:** 데일리 리포트 생성 (JSON/Markdown/Parquet).
- **FR-C05:** 신뢰도 점수(Confidence) 산출 및 시각화.
- **FR-C06:** 감성 트렌드, 키워드 클라우드, 영향 뉴스 표기.
- **FR-C07:** 대시보드 (관리자용 모니터링 및 사용자 리포트 뷰).


## 8. 품질 기준 및 평가 방법
- **성능 목표 (KPI):**
  - **방향성 정확도:** 매수 신호 시 실제 상승 확률 **55% 이상**.
  - **안정성:** 전체 프로세스 08:30 이전 완료 (장 시작 전).
  - **가동률:** **99% 이상 (데이터 수집 실패 시 Rollback 포함).**
- **테스트 전략:** Unit Test, Backtesting(과거 1년 데이터)
- **수락 기준:** 데이터 누수 방지, OOV 비율 30% 미만 등.


## 9. 오픈 이슈 및 향후 과제
- 뉴스 저작권 검토 필요.
- 장중 실시간 속보 반영은 향후 과제.
- ETF/해외 주식 확장, LLM 적용 검토.


## 10. 아키텍처 분해 및 운영 지침 (요약)
- 목적: 단일 `core` 컨테이너 리스크 완화, 단계적 마이크로서비스 마이그레이션.
- 권장 서비스 분해: `collector`, `tokenizer`, `preprocessor`, `learner`, `predictor`, `dashboard`, `vpn/proxy`.
- MeCab/사전 운영: `base-mecab` 이미지, CI 아티팩트, ConfigMap/PVC 마운트, 핫리로드 전략.
- 배포 권장: 로컬 `docker-compose` → 운영 `Kubernetes`(HPA, StatefulSet, PVC, Secrets).


## 11. 수집·전처리·학습·예측 및 관리자 대시보드 — 상세 요구사항 (DRAFT, 통합)

아래는 수집 저장 과정을 세분화하고, 관리자 대시보드를 통해 작업을 생성·관리·모니터링하는 통합 요구사항입니다. 이 문서는 Draft이며 작업 전환은 사용자 승인 필요.

### 11.1 개요 및 목적
- 목적: 수집 저장 과정을 세분화(주소수집→본문수집→전처리→학습→예측)하고, 초기 Backfill과 일간 Incremental 수집을 분리 운영하며, 관리자 웹 대시보드로 수집작업을 제어·모니터링.

### 11.2 주소 수집 (Address Collector)
- 기능: 키워드/종목코드로 검색된 뉴스 목록에서 뉴스 주소(URL)만 수집.
- 저장: URL 정규화 → 해시 기반 중복 체크 → DB 저장(`tb_news_url`/초기 `tb_news_content`).
- 스케줄: Backfill(역순 최신→과거) 및 Daily Incremental(매일 새벽).

### 11.3 주소 증분 수집
- 주기적 검색으로 기존 목록에 없는 주소를 추가.

### 11.4 본문 수집 (Body Collector)
- 기능: `pending`/`collected=false` URL에 대해 제목·본문·메타 수집.
- 성공: 원문 저장 → `collected=true`.
- 실패: 재시도(예: 3회, 지수적 백오프) → 실패시 `error` 및 `tb_news_errors` 기록.
- 배치 점검: 실패 항목 분류(삭제된 URL, 포맷 변경 등).

### 11.5 구조 변화 대응
- 수집 실패 사례를 구조 유형별로 분류하여 멀티-패턴 파서 또는 스마트 적응 기법 학습 자료로 사용.

### 11.6 원문 저장 원칙
- 수집된 제목·본문은 원문으로 보관.

### 11.7 토크나이징(Preprocessor)
- 미전처리 레코드에 대해 주기적 배치 토크나이징 수행.
- 완료 표기: `preprocessed=true` 또는 `tokens`(JSONB) 업데이트.
- 오류 시 재시도/수동검토 플로우.

### 11.8 전처리 연계 및 학습 파이프라인
- 전처리 완료 데이터는 Learner와 Predictor 파이프라인으로 전달.

### 11.9 단어사전 학습 정책
- 메인: 최대 1년~최소 3개월 데이터 기반 주간 학습.
- 버퍼: 최근 데이터 반영(일간/수시).
- 버전/소스 태깅 필수.

### 11.10 예측 및 리포트
- 메인+버퍼 앙상블(예: Main 0.7 / Buffer 0.3).
- 리포트: 앙상블/메인/버퍼 결과, 영향 단어(긍정 10 / 부정 10) 및 영향 뉴스(긍정 10 / 부정 10), 제목/일자/URL 포함.

### 11.11 리포트 저장 및 대시보드
- 일별 리포트 저장 및 웹 대시보드 제공.
- 뷰: 일/주/월(기본: 주). 요일별 예측·실제 비교 포함.

### 11.12 Backfill ↔ Daily 등록 및 동작 관례
- Backfill: 지난 1년치 역순 수집(초기 부트스트랩).
- Daily: 매일 새벽 증분 수집.
- Backfill이 생성하는 대상은 즉시 `daily_targets`에 자동 등록되며, 기본은 `paused`이나 Backfill 생성 시 `run_daily_during_backfill`(`auto_activate_daily`) 옵션으로 병렬 실행 선택 가능.
- 권장 `daily_targets` 필드: `target_id`, `params`, `backfill_registered_at`, `backfill_completed_at`, `daily_registered_at`, `status`, `activation_requested_at`, `auto_activate_daily`.
- 관리자는 대시보드에서 활성화/일시중지/삭제/예약 활성화 가능.

### 11.13 관리자 대시보드 기능(상세)
- CRUD: 작업 생성(키워드/종목코드, Backfill/Daily), 시작/중지, 삭제.
- 모니터링: 진행률(총/처리/성공/실패), 상태, 최근 에러 샘플.
- 제어: 재시작, 강제중단, 실패 항목 재시도, 활성화 예약.
- 권한: 관리자 전용 제어(RBAC).

### 11.14 동시성·확장성 요구사항
- 요구: Address/Body Collector는 다중 인스턴스 동시 실행 가능, 큐 길이·대상량·시스템 부하·외부 rate-limit을 고려해 유동적 확장/축소 가능.
- 권장 아키텍처:
  - 메시지 큐 기반 워커풀(RabbitMQ/Redis Streams/Kafka) — 권장.
  - Docker Compose: 개발용 `--scale worker=N` 가능하나 동적 오토스케일 제한.
  - Kubernetes: 운영환경 권장(HPA, VPA).
- 운영 고려사항: Backpressure, politeness rate-limit, 모니터링(Prometheus/Grafana), 분산 트레이싱(Jaeger).

### 11.15 작업·메트릭 저장소
- `jobs`, `job_logs`, `daily_targets`, `tb_news_errors` 테이블 설계 권장.

### 11.16 실패·재시도 및 알림
- URL 실패 재시도(최대 3회, 지수적 백오프). 재시도 후 실패는 `tb_news_errors` 기록.
- 장기 Backfill 완료/중단/심각오류 알림(이메일/슬랙).
- 대시보드 실시간(또는 1분 주기) 상태 업데이트.

### 11.17 검증·수용 기준
- Backfill: 기간 내 URL 목록 95% 이상 수집 완료.
- Daily: 신규 URL 중복 없이 등록.
- 확장성: N개의 워커로 초당 M개 이상 처리(예: N=5, M≥50 URLs/sec) — 성능시험으로 확정.
- 대시보드: 관리자 권한으로 작업 제어/진행률 확인 가능.

### 11.18 타당성 조사(요청 시 수행)
- 필요 시 외부 레퍼런스(공식 문서, 산업 블로그, 논문 등)를 조사하여 구현 권장안 및 타당성 근거를 문서화.


---

파일 생성 완료: `docs/prd/n-sentitrader-prd-merged.md`.

다음으로 무엇을 하시겠습니까?
- `apply_to_main` : 이 통합 초안을 `docs/prd/n-sentitrader-prd.md`로 병합(덮어쓰기 또는 섹션 삽입)하도록 재시도합니다. (권장: 리뷰 후 진행)
- `Proceed with research` : 외부 레퍼런스 조사 후 인용·첨부합니다.
- `Edit` : 초안 수정 지시(구체 항목 지목).
