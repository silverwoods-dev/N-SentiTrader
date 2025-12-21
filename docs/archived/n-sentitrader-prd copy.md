# N-SentiTrader PRD (Final Merged Draft)

Status: DRAFT — Integrated content from `n-sentitrader-prd.md` and `n-sentitrader-prd-merged.md`.

> 주의: 이 파일은 두 문서의 통합 초안입니다. 원본 파일들은 변경하지 않았습니다. 작업(태스크)으로 전환하지 말고 사용자 확인을 기다려주세요.

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
- **Data Processing:** Polars, Mecab
- **Scheduling:** APScheduler
- **Pipeline (요약):** Collector → Body Collector → Preprocessor → Learner → Predictor

## 6. MCP 도구 사용 전략
- **filesystem:** 프로젝트 구조 탐색 및 파일 읽기/쓰기. 대규모 변경 시 사용자 승인 필요.
- **context7:** 최신 라이브러리 사용법 조회.

## 7. 구현 범위 및 모듈 구조
(중복되는 항목 및 상세 내용은 `n-sentitrader-prd-merged.md` 참조)

## 8. 품질 기준 및 평가 방법
- KPI: 방향성 정확도 55% 이상, 전체 프로세스 08:30 이전 완료, 가동률 99% 이상.

## 9. 오픈 이슈 및 향후 과제
- 뉴스 저작권 검토, 장중 실시간 속보 반영, ETF/해외 주식 확장, LLM 도입 검토.

## 10. 아키텍처 분해 및 운영 지침 (요약)
- 서비스 분해: collector, tokenizer, preprocessor, learner, predictor, dashboard, vpn/proxy
- MeCab 운영: base-mecab 이미지 및 CI 아티팩트 권장
- 배포 권장: docker-compose → Kubernetes

## 11. 통합 상세 요구사항 (collection → preprocessing → learner → predictor → dashboard)
(여기에 통합된 상세 요구사항이 포함되어 있습니다; 자세한 항목은 `n-sentitrader-prd-merged.md` 파일을 참고하세요.)

---

파일 생성 완료: `docs/prd/n-sentitrader-prd-final.md`.

다음으로 원하시는 작업을 알려주세요:
- `apply_to_main`: 이 파일의 내용을 `docs/prd/n-sentitrader-prd.md`로 반영(덮어쓰기 또는 섹션 대체).
- `Proceed with research`: 외부 레퍼런스 조사를 시작하여 근거를 첨부.
- `Edit`: 초안 수정 지시(구체 항목 지정).
