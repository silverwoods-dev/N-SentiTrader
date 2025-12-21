# N-SentiTrader — Integrated PRD (Consolidated)

Status: DRAFT — This file consolidates content from:
- `n-sentitrader-prd.md`
- `n-sentitrader-prd-addendum-collection-dashboard.md`
- `n-sentitrader-prd-merged.md`
- `n-sentitrader-prd-update-draft.md`
- `n-sentitrader-prd-validated.md`

> 주의: 이 문서는 검토용 통합본입니다. 작업(태스크)으로 전환하지 말고 사용자 확인을 기다려주세요.

## 변화 요약 (핵심 결정사항)
- Backfill 동작: Backfill은 즉시 실행(One-time)되어야 한다.
- Daily 등록: Backfill 작업 생성 시 해당 대상은 `daily_targets`에 자동 등록되지만 기본 상태는 `pending` / `paused`(대기) 상태로 등록된다. Daily 실제 시작 시점은 관리자가 대시보드에서 선택(수동 활성화 또는 예약 활성화)한다.
- Backfill 중 Daily 병렬 실행 여부는 Backfill 생성 시 `auto_activate_daily` 플래그로 선택 가능; 기본값은 `false`.
- 모든 MeCab 관련 환경(사전·mecabrc)은 이미지 빌드/CI 아티팩트로 관리하여 런타임 에러를 방지한다.
- Collector는 메시지 큐 기반으로 설계하여 워커풀로 확장 가능하도록 권장한다.

---

## 1. 개요
- 한 줄 요약: 뉴스 텍스트 마이닝을 통해 단어별 영향력을 수치화한 동적 감성사전을 구축하고, 이를 바탕으로 특정 종목의 익일 초과수익(Alpha) 여부를 예측하는 시스템.
- 목표 요약:
  - 동적 감성사전(주간 Lasso + 일간 Buffer)
  - Backfill(초기 대량 수집)과 Daily(일별 증분 수집)의 명확한 분리 및 관리자 제어
  - 운영 안정성(메카브 사전 관리, DB/브로커 구성, 모니터링)

## 2. 핵심 요구사항(통합)
### 2.1 Backfill / Daily 동작 정책 (사용자 요구 반영)
- Backfill: 관리자 또는 초기 배포 시 즉시 실행되는 One-time Job. 범위(예: 최근 1년)는 Job 생성 시 파라미터로 지정.
- Backfill 실행시 다음 동작이 자동으로 수행됨:
  - 대상(키워드/종목코드)은 `daily_targets`에 자동으로 등록되나 기본 상태는 `pending/paused`로 둠(관리자 승인 필요).
  - `auto_register_daily` 기본값: `true`.
  - `auto_activate_daily` 기본값: `false` — 만약 `true`이면 Backfill 중에도 Daily가 병렬로 활성화되어 실행됨(관리자 선택 가능).
- Daily: 관리자 대시보드에서 수동으로 활성화하거나 예약하여 시작 시점을 정할 수 있음. Daily 스케줄러는 `paused` 상태의 `daily_targets`를 활성화 명령 수신 시부터 운영.
- 관리자가 선택한 운영 방식은 대시보드에서 개별 타겟별로 변경 가능.

### 2.2 관리자 대시보드 요구사항
- Job CRUD: Backfill/Daily Job 생성, 시작, 일시중지, 삭제
- 자동 등록 관리: Backfill이 만든 `daily_targets` 목록 확인 및 개별 활성화/예약 기능
- 모니터링: 진행률(총/처리/성공/실패), 최근 에러 샘플, 예상 잔여 시간
- 제어: 실패 항목 수동 재시도, 강제 중단, 재실행
- 권한: 관리자(RBAC)만 Job 제어 가능

### 2.3 수집기(Collector) 및 확장성
- 아키텍처: 주소 수집기(Address Collector) → URL 큐 → 본문 수집기(Body Collector) 워커풀
- 메시지 브로커: RabbitMQ / Redis Streams / Kafka 중 선택(운영 요건에 따라)
- 중복 방지: URL 정규화 + 원문 해시(sha256)로 DB 레벨 중복 체크
- 재시도·백오프: 각 URL 실패 시 지수적 백오프, 최대 재시도 횟수 설정(예: 3회)
- 오토스케일: 큐 길이/사용자 정의 메트릭으로 워커 수 조정(HPA 사용 권장)

### 2.4 토크나이저 / MeCab 운영
- MeCab 본체와 시스템/사용자 사전(mecab-ko-dic, user-dic)은 CI에서 컴파일하여 이미지 아티팩트로 배포하거나 PVC/ConfigMap으로 마운트.
- 권장: 베이스이미지 `base-mecab` 생성(또는 Dockerfile에 설치 단계 포함)
- 사용자 사전 버전 관리: `.dic` 아티팩트에 버전 태그를 부여하고 런타임은 명시된 버전만 사용.

### 2.5 데이터 모델 및 스키마
- 핵심 테이블: `tb_news_content`, `tb_news_url`, `tb_news_mapping`, `tb_daily_price`, `tb_sentiment_dict`, `jobs`, `job_logs`, `daily_targets`, `tb_news_errors`.
- `daily_targets` 필드(권장): `target_id`, `params`, `backfill_registered_at`, `backfill_completed_at`, `daily_registered_at`, `status`, `activation_requested_at`, `auto_activate_daily`.

### 2.6 스케줄러 선택 가이드
- 초기(간단): APScheduler(컨테이너 내부 경량 스케줄러)로 Daily 트리거 운영
- 복잡한 백필·재시도·의존성 관리: Airflow 권장(DAG 기반, 백필/재실행/관찰 용이)
- 권장 전략: 초기엔 APScheduler로 시작, Backfill 워크로드와 종속성이 확장되면 Airflow로 이전 검토

### 2.7 모니터링·알림
- 메트릭 스택: Prometheus 수집 + Grafana 시각화
- 알림: Alertmanager/Grafana Alerts → Slack/Email
- 권장 모니터링 항목: 큐 길이, 워커 처리율, 실패율, MeCab 초기화 오류, Backfill 진행률, Daily 지연

### 2.8 법적·윤리적 요구사항
- robots.txt 준수, User-Agent·contact email 표기, 타깃 서비스의 이용약관·저작권 검토 필요
- 크롤링 스루풋 제어(호스트별 rate-limit, politeness) 및 IP Rotation 정책

### 2.9 검증·수용 기준
- Backfill: 설정 기간(예: 1년) 내 URL 95% 이상 수집 완료
- Daily: 매일 새벽 예정 스케줄 기준으로 신규 URL이 중복 없이 등록될 것
- 파이프라인 시간: 모든 Daily 파이프라인은 08:30 이전 종료 목표
- 정확도: 방향성 예측 55% 이상(Dev baseline)
- 신뢰성: MeCab 초기화 오류 주간 0건(허용치 낮음), Collector 실패율 < 2%

---

## 3. 선결조건 및 우선순위(작업 전 필수 항목)
- 1) 인프라 확보: DB(Postgres), Broker(RabbitMQ/Redis/Kafka), Artifact Storage(PVC/S3), 모니터링(Prometheus)
- 2) MeCab 사전 빌드·배포: CI 파이프라인에서 `.dic` 아티팩트 생성 및 배포
- 3) 큐 기반 Collector 설계 및 중복 체크(해시 기준)
- 4) `daily_targets` 도메인 모델 및 대시보드 스펙 확정

## 4. 요구사항 간 충돌 및 처리 정책
- 충돌: Backfill이 즉시 등록하면서 Daily가 동시에 실행되는 중복 문제
  - 처리정책: 기본은 `auto_activate_daily=false`로 Backfill 우선, 관리자가 대시보드에서 개별 활성화 시 Daily 실행
  - 예외: 운영자가 `auto_activate_daily=true`로 선택한 경우 Backfill 병렬 실행 허용(리스크 수용 필요)
- 충돌: 사전 업데이트 시 토크나이저와 사전 버전 불일치
  - 처리정책: CI에서 `.dic` 빌드 및 버전화, 런타임 지정 버전만 허용. 핫 리로드 전략 및 장애 롤백 플랜 포함

## 5. 파일 및 다음 단계
- 통합본 경로: [docs/prd/n-sentitrader-prd-integrated.md](docs/prd/n-sentitrader-prd-integrated.md)
- 다음(사용자 승인 필요):
  - A) 이 통합본을 `docs/prd/n-sentitrader-prd.md`로 반영(덮어쓰기)
  - B) 항목별 수정(지정 섹션 편집 요청)
  - C) 더 깊은 외부 레퍼런스 추가(Proceed with deeper research)

---

작성자 노트: Backfill 즉시 실행 + Daily는 대기 상태 자동 등록 후 관리자가 활성화한다는 귀하의 지시를 통합했으며, MeCab·큐·스케줄러·모니터링에 대한 검증 결과(공식 문서 기반)도 반영했습니다. 추가로 병합 시 누락된 원본 참조(각 문서의 개별 문장 차이)를 모두 합쳤습니다. 변경을 원하면 구체 섹션 번호를 알려주세요.
