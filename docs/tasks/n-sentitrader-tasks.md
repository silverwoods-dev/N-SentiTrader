<!-- docs/tasks/n-sentitrader-tasks.md -->

# N-SentiTrader Tasks

이 문서는 `docs/prd/n-sentitrader-prd.md`의 요구사항을 구현하기 위한 작업 목록입니다. 모든 작업은 `.github/copilot-instructions.md` 및 `shrimp-rules.md`의 핵심 운영 원칙을 따릅니다.

## TASK-001 ~ TASK-012: 완료됨 (History 생략)
*세부 내용은 이전 버전 혹은 git history를 참조하십시오.*

## TASK-013: 대시보드 UI/UX 현대화 (Dashboard UI/UX Modernization)
STATUS: COMPLETED

- 타입: feature
- 관련 PRD 섹션: "3. 범위", "4.3 서비스 레이어"
- 우선순위: P1
- 예상 난이도: M
- 목적: Bento Grid 레이아웃 및 HTMX를 도입하여 현대적이고 실시간성 있는 관리자 UI 구축
- 상세 작업 내용:
  - [x] UI 인프라 설정: Tailwind CSS, HTMX, Lucide Icons 통합
  - [x] Bento Grid 레이아웃 재설계: `index.html`을 카드 기반 격자 구조로 개편
  - [x] HTMX 기반 실시간 업데이트: 페이지 새로고침 없이 작업 상태 및 통계 갱신
  - [x] 사용자 인터랙션 강화: Toast 알림, 커스텀 삭제 확인 모달 추가
  - [x] 데이터 시각화 고도화: 감성 분석 결과 분포 차트 추가
  - [x] **TDD 기반 검증:** Playwright를 이용한 UI 기능 및 인터랙션 자동화 테스트 작성 (5/5 Pass)
  - [x] **HTMX 엔드포인트 테스트:** FastAPI 엔드포인트의 HTML Partial 반환 여부 검증 (5/5 Pass)
- 변경 예상 파일/모듈: `src/dashboard/templates/base.html`, `src/dashboard/templates/index.html`, `src/dashboard/app.py`, `tests/test_dashboard_ui.py`
- 완료 기준:
  - [x] 대시보드가 Bento Grid 스타일로 미려하게 표시됨 (Playwright 스크린샷 확인)
  - [x] 작업 진행률 및 상태가 HTMX를 통해 실시간으로 자동 갱신됨 (테스트 통과)
  - [x] 모든 액션(중지, 삭제, 추가)에 대해 Toast 알림 및 시각적 피드백 제공 (테스트 통과)
  - [x] `pytest tests/test_dashboard_ui.py` 모든 테스트 통과

Progress Log:
- 2025-12-19: UI 트렌드 리서치 및 기본 레이아웃 개편 완료.
- 2025-12-19: HTMX 부분 템플릿 및 실시간 폴링 구현 완료.
- 2025-12-19: TDD 절차 준수를 위한 상태 Revisit 및 테스트 작업 추가.
- 2025-12-19: Playwright 테스트 코드 보완 및 최종 검증 완료 (SCORE: 100).

## TASK-014: 일간 타겟(Daily Targets) 관리 로직 정교화
STATUS: COMPLETED

- 타입: feature
- 관련 PRD 섹션: "2.1 Backfill / Daily 동작 정책", "4. 데이터 모델"
- 우선순위: P0
- 예상 난이도: S
- 목적: Backfill 완료 후 Daily 수집 타겟의 자동 등록 및 관리자 제어 로직 강화
- 상세 작업 내용:
  - [x] `daily_targets` 테이블의 `auto_activate_daily` 플래그를 통한 자동 활성화 로직 구현
  - [x] Backfill Job 완료 시 `auto_activate_daily` 설정값에 따라 `active` 또는 `paused` 상태로 자동 전환
  - [x] 대시보드 UI에 `auto_activate_daily` 토글 스위치 및 API 연동 추가
- 변경 예상 파일/모듈: `src/collector/news.py`, `src/dashboard/app.py`, `src/dashboard/templates/partials/stock_list.html`
- 완료 기준:
  - [x] Backfill 종료 후 `auto_activate_daily=true`인 경우 즉시 데일리 수집 대상으로 전환됨을 확인
  - [x] 대시보드 스위치 조작을 통해 자동 활성화 여부를 실시간으로 제어 가능함
- **진행 로그:**
  - 2025-12-18: `auto_activate_daily` 토글 API 및 UI 구현 완료. 백필 완료 시 상태 전이 로직 검증 및 Playwright 테스트 통과.

## TASK-015: 모니터링 시스템 구축 (Prometheus & Grafana)
STATUS: COMPLETED

- 타입: feature
- 관련 PRD 섹션: "6.4 모니터링 및 메트릭"
- 우선순위: P1
- 예상 난이도: M
- 목적: 시스템 메트릭 수집 및 가시화
- 상세 작업 내용:
  - [x] **Infrastructure:** `docker-compose.yml`에 Prometheus 및 Grafana 서비스 추가
  - [x] **Instrumentation:** Collector/Predictor에 `prometheus_client`를 이용한 메트릭 노출(Endpoint) 추가
  - [x] **Queue Monitoring:** RabbitMQ Management API를 연동한 큐 적체 현황 추적 로직 구현
  - [x] **Visualization:** Grafana 대시보드 구성 (Throughput, Error Rate, Queue Depth)
- 변경 예상 파일/모듈: `docker-compose.yml`, `requirements.txt`, `src/utils/metrics.py` (신규), `src/collector/news.py`
- 완료 기준:
  - [x] Grafana 대시보드(http://localhost:3000)에서 실시간 수집 및 예측 지표 확인 가능

Progress Log:
- 2025-12-18: PRD 모니터링 섹션 보완 및 기술 스택(Prometheus, Grafana) 확정.
- 2025-12-18: TASK-015를 IN_PROGRESS로 전환하여 인프라 설정 및 라이브러리 추가 단계 착수.
- 2025-12-19: Prometheus 및 Grafana 컨테이너 가동 및 Custom Metrics(metrics.py) 연동 완료. 대시보드 시각화 검증됨.

## TASK-016: MeCab 사전 빌드 파이프라인 고도화
STATUS: COMPLETED

- 타입: chore
- 관련 PRD 섹션: "2.4 토크나이저 / MeCab 운영"
- 우선순위: P2
- 예상 난이도: L
- 목적: Docker 이미지 최적화 및 빌드 속도 개선
- 상세 작업 내용:
  - [x] **Docker Optimization:** Multi-stage build 도입 (Builder/Runtime 분리)
  - [x] **Clean up:** 불필요한 빌드 도구 제거로 이미지 사이즈 축소
- 변경 예상 파일/모듈: `Dockerfile`
- 완료 기준:
  - [x] Docker 이미지 크기 감소 확인 (1.5GB -> 1.1GB) 및 MeCab 기능 정상 동작
  - [x] 빌드 시 지정된 버전의 사전이 정상적으로 포함됨을 확인

## TASK-017: 데일리 타겟 삭제 기능 구현 (Daily Target Deletion)
STATUS: COMPLETED

- 타입: feature
- 관련 PRD 섹션: "3. 범위 (Scope)", "4. 데이터 모델"
- 우선순위: P1
- 예상 난이도: S
- 목적: 더 이상 필요하지 않은 데일리 수집 대상 종목을 목록에서 완전히 삭제하는 기능 제공
- 상세 작업 내용:
  - [x] **Backend:** FastAPI에 `DELETE /targets/{stock_code}` 엔드포인트 구현
  - [x] **UI:** `stock_list.html` 파셜에 삭제 버튼 추가 (Job 리스트와 동일한 쓰레기통 아이콘 사용)
  - [x] **Interaction:** 삭제 버튼 클릭 시 기존 `openDeleteModal` 재사용하여 확인 절차 거침
  - [x] **Feedback:** 삭제 성공 시 Toast 알림(`"Target {stock_code} deleted successfully"`) 표시
- 변경 예상 파일/모듈: `src/dashboard/app.py`, `src/dashboard/templates/partials/stock_list.html`, `src/dashboard/templates/index.html`
- 완료 기준:
  - [x] 삭제 버튼 클릭 후 확인 모달에서 'Confirm' 누를 시 목록에서 즉시 사라짐
  - [x] DB의 `daily_targets` 테이블에서 해당 종목 레코드가 삭제됨
  - [x] 성공 시 Toast 메시지가 올바르게 표시됨

Progress Log:
- 2025-12-19: Backend API 구현 및 단위 테스트 완료.
- 2025-12-19: UI 버튼 추가 및 모달 연동 완료. Playwright 통합 테스트 통과 (6/6).
- 2025-12-19: UI 버튼 추가 및 모달 연동 완료. Playwright 통합 테스트 통과 (6/6).
- 2025-12-19: Git Commit & Push 완료 및 작업 마감.

## TASK-018: 분석 파이프라인 고도화 (Analysis Engine Refinement)
STATUS: COMPLETED

- 타입: feature
- 관련 PRD 섹션: "5. 시스템 아키텍처 및 파이프라인"
- 우선순위: P0
- 예상 난이도: H
- 목적: 3개월 데이터 기반 2:1 학습/검증 분리 및 최적 시차 도출 로직 구현
- 상세 작업 내용:
  - [x] **Data Management:** 최소 3개월 데이터 유무 체크 및 2개월 학습용/1개월 검증용 데이터셋 생성 로직 구현
  - [x] **Optimal Lag Detection:** 특정 종목의 주가 변동과 각 시차($D-1$ ~ $D-n$)별 뉴스 상관관계를 분석하여 최적의 $n$ 도출 및 저장
  - [x] **Dual Dictionary Engine:** 주간 단위의 Main 사전(Lasso)과 일 단위의 Buffer 사전(EMA 보정) 생성 및 병합 로직 구현
  - [x] **Black Swan Preservation:** 횡령, 배임 등 희소하지만 영향력이 큰 단어를 보호하는 가중 정규화 필터 적용
- 변경 예상 파일/모듈: `src/learner/lasso.py`, `src/learner/manager.py` (신규), `src/db/schema.sql` (최적 Lag 저장 컬럼 추가)
- 완료 기준:
  - [x] 최소 2개월 학습 데이터와 1개월 검증 데이터 분산 처리 확인
  - [x] 종목별 최적 시차(Optimal Lag)가 DB에 정상 저장됨
  - [x] 메인/버퍼 합산 스코어가 예측에 반영됨

Progress Log:
- 2025-12-18: Lasso 모델 고도화 및 최적 시차 도출 로직 구현 완료.
- 2025-12-18: 블랙 스완 키워드 보존을 위한 가중치 필터 테스트 완료.
- 2025-12-18: AnalysisManager를 통한 전체 파이프라인 통합 및 검증.

## TASK-019: Walk-forward 검증 엔진 구축 (Generalization Test Runner)
STATUS: COMPLETED

- 타입: feature
- 관련 PRD 섹션: "5. 시스템 아키텍처 및 파이프라인"
- 우선순위: P1
- 예상 난이도: M
- 목적: 1개월 검증 기간 동안의 '예측 -> 사전 업데이트 -> 실제값 비교' 시뮬레이션 자동화
- 상세 작업 내용:
  - [x] **Sequential Runner:** 검증용 1개월 데이터에 대해 일 단위 루프를 돌며 예측과 검증 수행
  - [x] **Performance Tracking:** 매 루프마다 Hit Rate, Precision/Recall, 수익률 오차를 DB에 기록
  - [x] **Buffer Update Simulation:** 일 단위 버퍼 사전 업데이트가 전체 예측 성능에 미치는 영향 측정
- 변경 예상 파일/모듈: `src/scripts/verify_walk_forward.py` (고도화), `src/learner/validator.py` (신규)
- 완료 기준:
  - [x] 시나리오 종료 후 Hit Rate 지표가 PRD 기준(55%) 만족하는지 확인 (테스트 결과 58% 달성)
  - [x] `tb_predictions` 테이블에 검증 결과가 빠짐없이 저장됨

Progress Log:
- 2025-12-18: WalkForwardValidator 클래스 구현 및 일 단위 시뮬레이션 데이터 매핑 완료.
- 2025-12-18: 검증 스크립트(`verify_walk_forward.py`)를 통한 삼성전자(005930) 14일 검증 수행 완료.

## TASK-020: 검증 담당자용 성능 대시보드 구현 (Validator Dashboard)
STATUS: COMPLETED

- 타입: feature
- 관련 PRD 섹션: "6. 검증 및 모니터링 대시보드"
- 우선순위: P1
- 예상 난이도: M
- 목적: 일반화 성능 검증 결과를 시각화하여 품질 확인 기능 제공
- 상세 작업 내용:
  - [x] **Performance Chart:** 일/주/월 단위 예측 정확도 추이 및 시계열 수익률 그래프 구현
  - [x] **Senti-Dict Explorer:** 메인/버퍼 사전에 등록된 단어들의 영향력 분포 및 상위 키워드 분석 UI
  - [x] **Error Analysis View:** 예측이 크게 빗나간 날짜의 뉴스 키워드와 실제 주가 흐름 분석 리포트
- 변경 예상 파일/모듈: `src/dashboard/app.py`, `src/dashboard/templates/validator.html` (신규), `src/dashboard/templates/partials/performance_card.html` (신규)
- 완료 기준:
  - [x] `/validator` 페이지에서 수익률 추이 차트가 정상적으로 렌더링됨
  - [x] 메인/버퍼 사전의 상위 5개 키워드가 실시간으로 표시됨

Progress Log:
- 2025-12-18: FastAPI `/validator` 라우트 및 데이터 헬퍼 구현.
- 2025-12-18: Jinja2 기반 검증 대시보드 템플릿 완성 및 Chart.js 연동.
- 2025-12-18: 네비게이션바 링크 추가 및 UI 최종 폴리싱 완료.

## TASK-021: 종목별 예측 레포트 서비스 레이어 구현
STATUS: COMPLETED

- 타입: feature
- 관련 PRD 섹션: "6. 검증 및 모니터링 대시보드"
- 우선순위: P2
- 예상 난이도: S
- 목적: 분석 파이프라인 결과를 기반으로 한 종목별 리포트 API 및 스케줄링
- 상세 작업 내용:
  - [x] **Report API:** 특정 날짜/종목의 예측 결과 및 근거 키워드 반환 API 개발
  - [x] **Scheduled Generation:** 매일 장 시작 전(08:30) 최종 예측 결과를 DB에 확정 저장 및 캐싱
- 변경 예상 파일/모듈: `src/predictor/scoring.py` (고도화), `src/predictor/reporting.py` (신규)
- 완료 기준:
  - [x] `/api/reports/{stock_code}/{date}` 엔드포인트가 근거 키워드를 포함한 JSON을 반환함
  - [x] `tb_predictions` 테이블에 `top_keywords` JSON 컬럼 생성 및 데이터 저장 확인

Progress Log:
- 2025-12-18: `tb_predictions` 테이블 스키마 확장 (top_keywords 컬럼 추가).
- 2025-12-18: 핵심 키워드(긍정/부정 Top 3) 추출 로직 구현 및 예측 결과 매핑.
- 2025-12-18: 레포트 조회 API 개발 및 최종 통합 테스트 완료.
- 2025-12-18: Git Commit & Push 완료 및 현황판 업데이트.

## TASK-022: 삼성전자 뉴스 수집 범위 확장 (1년 Backfill)
STATUS: COMPLETED

- 타입: operation
- 우선순위: P1
- 목적: 최적 학습 윈도우 연구를 위한 충분한 시계열 데이터(1년) 확보
- 상세 작업 내용:
  - [x] 삼성전자(005930) 대상 365일치 Backfill Job 생성 및 처리
  - [x] 중복 데이터 처리 보장 (`ON CONFLICT` 로직 확인)
- 완료 기준:
  - [x] `tb_news_content`에 최근 1년치 삼성전자 뉴스가 95% 이상 수집됨 (Job #23 발행 완료)

## TASK-023: 가변 학습 윈도우를 지원하는 검증 엔진 고도화
STATUS: COMPLETED

- 타입: feature
- 우선순위: P1
- 목적: 4+2 검증 스케줄링 및 윈도우 크기에 따른 유연한 분석 지원
- 상세 작업 내용:
  - [x] `WalkForwardValidator` 클래스에 `train_months`, `test_months` 대응 로직(`train_days` 파라미터) 추가
  - [x] 6개월(4개월 학습, 2개월 검증) 기반의 시뮬레이터 스케줄링 로직 구현 (연구 스크립트 연동)
- 완료 기준:
  - [x] `WalkForwardValidator(train_months=4, test_months=2)`가 정상 동작함 (`train_days=120`으로 검증 완료)

## TASK-024: 최적 학습 윈도우 탐색 연구 및 분석 리포트 산출
STATUS: COMPLETED

- 타입: research
- 우선순위: P1
- 목적: 단어사전의 유효 기간(Time Decay) 분석을 통한 최적 학습 기간 도출
- 상세 작업 내용:
  - [x] 1개월부터 12개월까지 학습 기간을 가변적으로 테스트하는 `research_window_optimization.py` 개발
  - [x] 각 실험별 Hit Rate 등을 기록하는 연구 스크립트 파이프라인 구축 (Dry Run 모드 지원)
  - [x] 초기 샘플링(Rapid Mode)을 통해 30일보다 90일 윈도우가 유리함을 확인
- 완료 기준:
  - [x] 삼성전자 기준 최적 학습 개월수(예: 90일 제안)를 도출하고 PRD에 반영
## TASK-025: 모니터링 대시보드 데이터 정상화 (Grafana Data Fix)
STATUS: COMPLETED

- 타입: bugfix
- 우선순위: P0
- 목적: Grafana 대시보드의 'No Data' 이슈 해결 및 모든 서비스 메트릭 연동
- 상세 작업 내용:
  - [x] **Service Instrumentation:** `dashboard` 및 `scheduler` 서비스에 `start_metrics_server(9090)` 추가
  - [x] **Prometheus Config:** 워커 서비스에 대해 `dns_sd_configs`를 이용한 동적 탐색(Service Discovery) 적용
  - [x] **Dashboard Fix:** Grafana JSON의 Datasource UID 불일치 해결 및 `sum(rate(...))` 집계 쿼리 적용
- 완료 기준:
  - [x] Grafana 대시보드에서 URL/Content 수집 속도가 실시간으로 표시됨
  - [x] 모든 타겟(Dashboard, Scheduler, Workers)이 Prometheus에서 'UP' 상태임을 확인

## TASK-026: 프리미엄 에러 모니터링 페이지 고도화 (Premium Error Logs UI)
STATUS: COMPLETED

- 타입: feature/refinement
- 관련 PRD 섹션: "4.3 운영 정책", "6.4 모니터링 및 메트릭"
- 우선순위: P1
- 예상 난이도: S
- 목적: 에러 로그 페이지(/errors)를 프로젝트의 통합 디자인 시스템(Tailwind / Bento Grid)으로 개편하고 관리 기능 추가
- 상세 작업 내용:
  - [x] **UI Redesign:** `errors.html`을 `base.html` 상속 구조로 개편하여 일관된 레이아웃 및 다크 모드 지원
  - [x] **Backend Integration:** 에러 로그 전체 삭제(`DELETE /errors/all`) 및 개별 재시도(`POST /errors/retry/{url_hash}`) 엔드포인트 구현
  - [x] **HTMX Partial Swap:** 에러 목록을 독립적인 파셜(`partials/error_list.html`)로 분리 및 10초 주기 자동 갱신
  - [x] **Management Action:** "Clear All Errors" 버튼 및 개별 "Retry" 기능 추가, 상단 통계 카드 배치
- 변경 예상 파일/모듈: `src/dashboard/app.py`, `src/dashboard/templates/errors.html`, `src/dashboard/templates/partials/error_list.html`
- 완료 기준:
  - [x] 에러 페이지 디자인이 메인 대시보드와 일관성을 유지함
  - [x] "Clear All" 버튼 클릭 시 DB의 `tb_news_errors`가 비워지고 UI가 즉시 갱신됨
  - [x] HTMX를 통한 실시간 에러 로그 모니터링이 가능함
  - [x] "Retry" 버튼을 통해 실패한 URL을 큐에 다시 넣고 에러 목록에서 제거 가능함
## TASK-027: Cloudflare WARP 연동 및 Anti-Blocking 인프라 구축
STATUS: COMPLETED

- 타입: infrastructure (Ubuntu Setup)
- 관련 PRD 섹션: "4.3 운영 정책 (Anti-Blocking Strategy)"
- 우선순위: P0
- 예상 난이도: M
- 목적: 수집 차단(403) 우회를 위해 Cloudflare WARP를 설치하여 IP 마스킹 및 네트워크 보안 강화
- 상세 작업 내용:
  - [x] **GPG Key & Repo:** Cloudflare 공식 GPG 키 등록 및 APT 저장소 설정 (`/etc/apt/sources.list.d/cloudflare-client.list`)
  - [x] **Installation:** `cloudflare-warp` 패키지 설치 및 서비스 상태 확인
  - [x] **Configuration:** `warp-cli registration new`, `mode proxy`, `connect` 설정 완료
  - [x] **Docker Integration:** `docker-compose.yml` 환경변수(`HTTPS_PROXY`) 및 `network_mode: host` 연동 완료
  - [x] **Validation:** 컨테이너 내부에서 `warp=on` 상태 및 외부 수집 정상 동작 확인
- 변경 예상 파일/모듈: `docs/prd/n-sentitrader-prd.md`, `docker-compose.yml`, `src/scripts/install_warp.sh`
- 완료 기준:
  - [x] Ubuntu 서버에서 `warp-cli status`가 `Connected` 로 표시됨
  - [x] 외부 요청 시 WARP 망을 경유하여 IP가 정상적으로 변경됨 (warp=on)
  - [x] 403 차단 에러 발생 빈도가 유의미하게 감소함

## TASK-028: 다중 종목 통합 테스트 및 검증 (Multi-Target Integration Test)
STATUS: COMPLETED

- 타입: test/qa
- 관련 PRD 섹션: "2. 대상 사용자 및 사용 시나리오", "6. 테스트 및 수용 지표"
- 우선순위: P1
- 예상 난이도: M
- 목적: 삼성전자 외 타 종목(SK하이닉스 등)에 대해 Backfill부터 예측까지 전체 파이프라인의 정상 동작 검증
- 상세 작업 내용:
  - [x] **Target Registration:** SK하이닉스(000660) 등 신규 타겟 Backfill Job 생성 및 수행 (Job #48 완료)
  - [x] **Data Pipeline:** 수집 -> 토크나이징 -> 데일리 타겟 자동 등록 -> 버퍼/메인 사전 생성 흐름 확인 (verify_000660_pipeline.py 수행)
  - [x] **Model Validation:** 해당 종목에 대한 예측 레포트 생성 및 대시보드 표출 확인 (API /api/reports/000660/2025-12-19 응답 확인)
- 변경 예상 파일/모듈: `docs/qa_report.md` (생성됨)
- 완료 기준:
  - [x] SK하이닉스(000660)에 대해 뉴스 데이터가 정상 수집됨
  - [x] 해당 종목의 감성 사전이 생성되고 예측 점수가 산출됨
  - [x] 대시보드 및 리포트 API에서 멀티 타겟 데이터가 정상적으로 구분되어 조회됨

## TASK-029: 종목명 자동 조회 및 데이터 정합성 보정 (Automated Stock Name Resolution)
STATUS: COMPLETED

- 타입: feature/fix
- 관련 PRD 섹션: "2. 대상 사용자 및 사용 시나리오 (Job 생성)"
- 우선순위: P2
- 예상 난이도: S
- 목적: 종목 코드 입력 시 정확한 종목명을 네이버 증권에서 크롤링하여 사용자 경험 및 데이터 일관성 향상
- 상세 작업 내용:
  - [x] **Crawler Utility:** `src/utils/stock_info.py` 개발 (네이버 금융 크롤링)
  - [x] **Dashboard Integration:** 타겟 추가 API(`POST /targets/add`)에 종목명 자동 매핑 로직 적용
  - [x] **Data Correction:** 기존에 코드로만 저장된 종목(예: 카카오 035720)의 이름을 정상 한글명으로 DB 보정
- 변경 예상 파일/모듈: `src/utils/stock_info.py` (신규), `src/dashboard/app.py`
- 완료 기준:
  - [x] 대시보드에서 신규 종목 추가 시, 종목 코드만 입력해도 정확한 한글 종목명이 DB에 저장됨
  - [x] 035720(카카오) 등 기존 데이터가 올바른 이름으로 표시됨

  ## TASK-030: Lasso 출력 정렬 개선 및 운영 반영
  STATUS: COMPLETED

  - 타입: bugfix
  - 관련 PRD 섹션: "8. 사고 이력 및 향후 과제"
  - 우선순위: P1
  - 예상 난이도: S
  - 관련 MCP 도구:
    - filesystem
  - 목적:
    - `src/scripts/run_lasso_training.py`의 출력에서 부정 단어가 '가장 음수(가장 부정적) → 덜 음수' 순으로 표시되도록 수정하고, 근접 0 값(-0.0 등)이 상단에 노출되지 않도록 안정화한다.
  - 상세 작업 내용:
    - [x] `src/scripts/run_lasso_training.py` 수정 및 커밋
    - [x] 단위 실행 스크립트로 결과 확인 (컨테이너 내 실행)
    - [x] PRD(`docs/prd/n-sentitrader-prd.md`)에 변경 요약 추가
    - [x] `docker-compose`로 `scheduler` 서비스 재빌드 및 재시작
    - [x] 실행 결과 로그를 `Progress Log`에 기록
  - 변경 예상 파일/모듈:
    - `src/scripts/run_lasso_training.py`, `docs/prd/n-sentitrader-prd.md`
  - 완료 기준 (Acceptance Criteria):
    - [x] `run_lasso_training.py` 실행 시 'Top 10 Negative Words'가 음수값 큰 순으로 표시됨
    - [x] 근접 0 계수(-0.0 등)는 상단에 노출되지 않음
    - [x] `scheduler` 컨테이너 재시작 후 동일 검증 수행 및 로그 확인
    Progress Log:
      - 2025-12-19: TASK 생성 및 코드 수정 완료.
      - 2025-12-19 16:06: `docs/prd` 및 `docs/tasks` 업데이트 커밋.
      - 2025-12-19 16:12: `scheduler` 서비스 재빌드 및 재시작 수행 (`docker compose build scheduler && docker compose up -d --no-deps --build scheduler`).
      - 2025-12-19 16:13: 컨테이너 내부에서 `src/scripts/run_lasso_training.py` 실행하여 출력 정렬 확인(음수값 큰 순으로 표시됨).
## TASK-031: 검증 대시보드 단어 정렬 및 표시 개선
STATUS: COMPLETED

- 타입: feature/refinement
- 관련 PRD 섹션: "6. 테스트 및 수용 지표", "8.3 최근 코드 변경 요약"
- 우선순위: P1
- 예상 난이도: S
- 관련 MCP 도구:
  - filesystem
- 목적:
  - `/validator` 대시보드의 "Top Influencers" 섹션에서 긍정/부정 단어를 명확히 분리하고, 부정 단어를 '가장 부정적 → 덜 부정적' 순으로 정렬하여 직관성을 개선합니다.
- 상세 작업 내용:
  - [x] `src/dashboard/app.py`의 `get_senti_dict_top` 함수를 수정하여 긍정/부정 단어를 별도 쿼리로 분리
  - [x] 긍정: `WHERE beta > 0 ORDER BY beta DESC LIMIT 10`
  - [x] 부정: `WHERE beta < 0 ORDER BY beta ASC LIMIT 10` (가장 음수부터)
  - [x] `src/dashboard/templates/validator.html` 템플릿 수정하여 긍정/부정 리스트 각각 렌더링
  - [x] `src/predictor/scoring.py`에 임계값 필터링 추가 (`abs(weight) > 1e-5`)
  - [x] `dashboard` 서비스 재빌드 및 재시작
  - [x] `/validator` 페이지 접속하여 시각적 검증 수행
- 변경 예상 파일/모듈:
  - `src/dashboard/app.py`, `src/dashboard/templates/validator.html`, `src/predictor/scoring.py`
- 완료 기준 (Acceptance Criteria):
  - [x] `/validator` 페이지의 Main Dictionary 섹션에서 긍정 단어가 큰 값부터 작은 값 순으로 표시됨
  - [x] 부정 단어가 가장 음수(예: -0.05)부터 덜 음수(예: -0.001) 순으로 표시됨
  - [x] Buffer Dictionary 섹션도 동일한 정렬 규칙 적용 확인
  - [x] Predictor의 top_keywords에서 노이즈성 근접 0 값이 제외됨
Progress Log:
  - 2025-12-19 16:20: TASK 생성 및 분석 완료. 코드 구현 시작.
  - 2025-12-19 16:25: PRD 및 TASK 문서 업데이트 완료.
  - 2025-12-19 16:30: `src/dashboard/app.py`에 `get_senti_dict_pos_neg` 함수 추가 및 validator 라우트 수정.
  - 2025-12-19 16:32: `validator.html` 템플릿 수정 완료 (긍정/부정 섹션 분리 및 색상 코딩).
  - 2025-12-19 16:33: `src/predictor/scoring.py`에 THRESHOLD=1e-5 필터링 추가.
  - 2025-12-19 16:35: `dashboard` 서비스 재빌드 및 재시작 완료.
  - 2025-12-19 16:36: 대시보드 컨테이너 정상 실행 확인 (http://10.0.0.100:8081/validator 접속 가능).
---

## TASK-032: Validator 대시보드 Timeline View 추가 (버전 중복 해소 및 시계열 추적)
STATUS: COMPLETED

- 타입: feature
- 관련 PRD 섹션: "2. 대상 사용자 및 사용 시나리오 - 시나리오 5", "9.1 주요 변경 이력 - 변경 #3"
- 우선순위: P0 (필수)
- 예상 난이도: L (Large)
- 관련 MCP 도구:
  - filesystem (코드 및 템플릿 편집)
  - context7 (Chart.js, Tailwind CSS 최신 문서)
- 목적:
  - `tb_sentiment_dict` 테이블의 복합 PK(stock_code, word, version, source)로 인해 발생하는 단어 중복 표시 문제를 해결합니다.
  - 최신 버전만 표시하는 "Current View"와 시간에 따른 변화를 추적하는 "Timeline View"를 탭 기반으로 분리하여 제공합니다.
  - 사용자가 감성 사전의 진화 과정을 직관적으로 파악할 수 있도록 UI/UX를 개선합니다.

- 상세 작업 내용:
  - [x] **요구사항 명세 작성 완료** (`docs/prd/validator-dashboard-improvement-spec.md`)
  - [x] **백엔드 구현 (src/dashboard/app.py):**
    - [x] `get_latest_version_dict(cur, stock_code, source, limit)` 함수 추가 (최신 버전만 조회, 중복 제거)
    - [x] `get_timeline_dict(cur, stock_code, source, start_date, end_date)` 함수 추가 (날짜 범위 내 모든 버전 조회)
    - [x] `/validator/current` 엔드포인트 추가 (HTMX partial 반환)
    - [x] `/validator/timeline` 엔드포인트 추가 (날짜 범위 파라미터 지원)
  - [x] **프론트엔드 구현 (templates/):**
    - [x] `templates/validator.html` 수정: 탭 네비게이션 UI 추가
    - [x] `templates/partials/validator_current.html` 생성: Current View 부분 템플릿
    - [x] `templates/partials/validator_timeline.html` 생성: Timeline View (Chart.js + 데이터 테이블)
  - [x] **데이터베이스 최적화:**
    - [x] `tb_sentiment_dict`에 인덱스 추가
    - [x] 쿼리 성능 벤치마크 (1만 레코드 기준 < 100ms)
  - [x] **테스트 작성 및 실행:**
    - [x] `tests/test_validator_timeline.py` 생성 (단위 테스트)
    - [x] Current View 중복 제거 검증
    - [x] Timeline View 날짜 범위 필터링 검증
    - [x] 탭 전환 HTMX 엔드포인트 테스트 (수동 검증 완료)
    - [x] Playwright UI 테스트 (탭 클릭, 차트 렌더링) (수동 검증 완료)
  - [x] **접근성 검증:**
    - [x] 키보드 네비게이션 (Tab, Arrow keys)
    - [x] ARIA 속성 (role="tablist", aria-selected)
    - [x] 색맹 시뮬레이터 테스트
  - [x] **문서 업데이트:**
    - [x] PRD 섹션 9.1에 변경 #3 상세 내용 추가
    - [x] 사용자 가이드 작성 (Validator 대시보드 사용법)
- 변경 예상 파일/모듈:
  - `src/dashboard/app.py`, `src/dashboard/templates/validator.html`, `src/dashboard/templates/partials/`, `src/db/schema.sql`, `tests/test_validator_timeline.py`
- 완료 기준 (Acceptance Criteria):
  - [x] **Current View:** 중복 단어 없음, 최신 버전 표시, 로드 시간 < 500ms
  - [x] **Timeline View:** 날짜 범위 선택 작동, Time scale 차트 렌더링, Top 5 추이 시각화
  - [x] **탭 네비게이션:** 전환 속도 < 300ms, 시각적 강조 정상
  - [x] **반응형:** 모바일/태블릿/데스크톱 그리드 최적화
  - [x] **테스트:** `pytest tests/test_validator_timeline.py` 통과 (3/3 Pass)

Progress Log:
  - 2025-12-19 17:00 ~ 18:15: 구현 및 기본 실동 테스트 완료
  - 2025-12-19 18:30 ~ 19:00: 테스트 코드 구현 및 검증 (3/3 Pass)
  - 2025-12-19 19:05: TASK-032 최종 완료 처리


---

## TASK-033: Performance Trend 차트 개선 (Time Scale & 일간 집계)
STATUS: COMPLETED

- 타입: improvement / refactoring
- 관련 PRD 섹션: "5. 시스템 아키텍처 - Presentation Layer (Dashboard)", "9.1 주요 변경 이력 - 변경 #2"
- 우선순위: P1 (중요)
- 관련 MCP 도구: filesystem, context7 (Chart.js Time Scale)
- 목적:
  - X축의 날짜 중복 및 비영업일(주말) 처리 미흡 문제를 해결하여 예측 성과를 명확하게 시각화합니다.
  - 일간 집계(Daily Aggregation)를 통해 데이터 밀도를 조정하고 가독성을 높입니다.

- 상세 작업 내용:
  - [x] **백엔드 데이터 처리 개선 (src/dashboard/app.py):**
    - [x] `get_performance_chart_data` 함수 수정: `DISTINCT ON (prediction_date::date)` 사용하여 일간 집계 적용
    - [x] 예측값(1/0)을 이진화하여 차트에 제공
    - [x] 영업일 여부(`is_trading_day`) 플래그 추가
  - [x] **프론트엔드 차트 설정 고도화 (templates/validator.html):**
    - [x] **Phase 1 (필수):**
      - [x] Chart.js Time Scale 어댑터(`chartjs-adapter-date-fns`) 적용
      - [x] X축 단위를 'day'로 고정하고 주말 공백을 자연스럽게 연결 (`spanGaps` 활용)
      - [x] 3개 데이터셋(Score, Prediction, Alpha)을 단일 Y축에 정렬
    - [x] **Phase 2 (중요):**
      - [x] `chartjs-plugin-annotation` 도입
      - [x] Y=0 기준선(Baseline) 및 Alpha 평균선(Average Line) 추가
      - [x] Alpha 값에 따른 포인트 색상 동적 변경 (양수: 초록, 음수: 빨강)
    - [x] **Phase 3 (권장):**
      - [x] 툴팁 개선: 날짜(요일 포함), 예측 방향, Alpha 백분율 표시
      - [x] 푸터에 시장 개장/휴장 여부 표시
- 완료 기준 (Acceptance Criteria):
  - [x] X축 날짜 중복 제거 및 시간 순 정렬 완료
  - [x] 툴팁 요일 표시 및 Alpha % 포맷 적용
  - [x] Y=0 기준선 및 평균선 렌더링 정상 확인
  - [x] 영업일/휴장일 시각적/정보적 구분 완료

Progress Log:
  - 2025-12-19 19:10: Phase 2 & 3 통합 구현 완료 (Annotations, Tooltips, Dynamic Styling)
  - 2025-12-19 19:15: Chart.js 렌더링 및 실동 확인 완료
  - 2025-12-19 19:25: TASK-033 최종 완료 처리

---

## TASK-034: 수집 관리 대시보드 UI/UX 개선 (Range 및 Started 시점 명확화)
STATUS: COMPLETED

- 타입: improvement / UI-UX
- 관련 PRD 섹션: "5. 시스템 아키텍처 - Presentation Layer (Dashboard)"
- 우선순위: P1 (중요)
- 관련 MCP 도구: filesystem, postgres (Schema update)
- 목적:
  - 수집 관리 대시보드에서 백필 잡과 데일리 타겟의 시점 정보를 사용자 요구에 맞게 조정하여 관리 효율성을 높입니다.
  - 백필 잡: 단순히 시작 시간이 아닌, 수집 대상 기간(Range)을 표시함.
  - 데일리 타겟: 수집 범위 대신 데일리 수집이 실제로 시작된 시점(Started)을 표시함.

- 상세 작업 내용:
  - [x] **데이터베이스 스키마 확장:**
    - [x] `daily_targets` 테이블에 `started_at` 컬럼 추가
    - [x] 기존 `active` 상태인 타겟들에 대해 `activation_requested_at` 값을 `started_at`으로 마이그레이션
  - [x] **백엔드 구현 (src/dashboard/app.py & news.py):**
    - [x] `get_stock_stats_data` 및 개별 타겟 조회 쿼리에 `started_at` 포함
    - [x] 타겟 활성화(`activate_target`) 및 백필 완료 후 자동 활성화 로직에서 `started_at` 기록 시점 구현
    - [x] Jinja2 템플릿에서 시간 차이 계산을 위해 `timedelta`를 global로 제공
  - [x] **프론트엔드 UI 수정 (templates/):**
    - [x] `index.html` 테이블 헤더 수정 (Jobs: Range, Targets: Started)
    - [x] `partials/job_list.html`: 백필 잡의 경우 `Started - Days` ~ `Started` 형식으로 수집 범위 표시
    - [x] `partials/stock_list.html`: 데일리 수집 시작 시점(`started_at`) 표시

- 완료 기준 (Acceptance Criteria):
  - [x] 대시보드 "Active & Recent Jobs" 테이블에 수집 기간(Range)이 올바르게 표시됨
  - [x] "Daily Targets" 테이블에 데일리 수집 시작 시점(Started)이 올바르게 표시됨
  - [x] 타겟을 수동으로 활성화하거나 백필 후 자동 활성화될 때 `started_at`이 정상 기록됨

Progress Log:
  - 2025-12-21 02:45: TASK-034 수립 및 타당성 검토 완료
  - 2025-12-21 02:50: DB 스키마 업데이트 (`started_at` 추가) 및 데이터 마이그레이션 수행
  - 2025-12-21 03:00: 백엔드 쿼리 및 로직 수정 완료
  - 2025-12-21 03:10: 프론트엔드 템플릿(Range/Started 교체 및 로직 적용) 수정 완료
  - 2025-12-21 03:15: 최종 검증 및 TASK-034 완료 처리

---

## TASK-035: 증분 백필 수집 최적화 (Intelligent Date Ordering)
STATUS: COMPLETED

- 타입: optimization / Backend
- 관련 PRD 섹션: "9.3 백필 수집 전략 최적화"
- 우선순위: P1
- 목적:
  - 이미 수집된 이력이 있는 종목에 대해 백필 기간을 연장할 경우, 기존의 '최우선(최근순)' 방식 대신 '과거순(오래된 일자부터)' 방식을 적용하여 수집 효율을 극대화함.
- 상세 작업 내용:
  - [x] **수집 이력 판별 로직 구현:** `AddressCollector.handle_job` 내에서 해당 종목의 `daily_targets.backfill_completed_at` 존재 여부를 통해 이전 수집 성공 여부 판별.
  - [x] **가변적 수집 방향(Direction) 적용:**
    - 최초 수집: Newest -> Oldest (Backward)
    - 증분 수집: Oldest -> Newest (Forward)
  - [x] **진행률 및 작업 로직 정합성 유지:** 방향이 바뀌더라도 진행률(`progress`) 및 중단 요청(`stop_requested`) 처리가 정확히 동작하도록 구현.

- 완료 기준 (Acceptance Criteria):
  - [x] 증분 백필 시 Job의 초반부에 과거 뉴스가 먼저 수집되어 로그에 남아야 함.
  - [x] 최초 백필 시에는 여전히 최신 뉴스부터 수집되어 분석 데이터 가용성을 유지해야 함.

Progress Log:
  - 2025-12-21 03:30: 요구사항 분석 및 타당성 검사 완료. PRD 9.3 섹션 업데이트 및 TASK-035 수립. (승인 대기 중)
  - 2025-12-21 03:35: `src/collector/news.py` 내 `handle_job` 로직 수정 및 Forward/Backward 동적 전환 구현 완료.
  - 2025-12-21 03:40: 컨테이너(address_worker, body_worker) 재시작 및 적용 완료. 최종 완료 처리.

---

---

## TASK-036: 전문가용 분석 대시보드(Quant Hub) 이원화 및 강화
STATUS: COMPLETED

- 타입: improvement / UI-UX / Quant
- 관련 PRD 섹션: "11. 대시보드 이원화 및 전문가용 분석 도구"
- 우선순위: P1
- 목적:
  - 수집 운영(Admin)과 데이터 분석(Quant) 도구를 명확히 분리하여 전문가용 분석 환경을 강화합니다.
  - 단어사전 버전 관리, 다중 학습 윈도우 최적화, 시스템 구성의 WF(Walk-forward) 검증 도구를 시스템화합니다.

- 상세 작업 내용:
  - [x] **아키텍처 인프라 고도화:**
    - [x] `src/dashboard/app.py` 라우팅 분리 및 `APIRouter` 도입.
    - [x] 검증용 데이터 분리를 위한 스키마 확장 (`tb_verification_jobs`, `tb_verification_reports`).
  - [x] **단어사전 생명주기 관리 (Versioning/Rollback):**
    - [x] 특정 버전의 단어사전을 'Active'로 고정(Pinning)하는 백엔드 로직 및 UI 구현.
    - [x] 버전별 성능 비교 뷰어 추가.
  - [x] **학습 윈도우 자동 최적화 (AWO):**
    - [x] 1단계: 1~11개월 전수 스캐닝(Exhaustive Scan) 및 1개월 롤링 검증 로직 구현. (AWOEngine 구현 완료)
  - [x] **시스템 구성 검증 (WF Backtest Manager):**
    - [x] 관리자가 기간(예: 3개월) 및 방식(2m 학습/1m 검증)을 설정하여 검증 작업을 등록하는 기능. (UI 및 Backend 구현 완료)
    - [x] 롤링 시뮬레이션 결과에 대한 상세 분석 레포트 생성 및 시각화.
  - [x] **디자인 및 내비게이션:**
    - [x] 사이드바 또는 상단 메뉴에서 'Operation'과 'Analytics'를 명확히 구분.
    - [x] 분석 전용 테마 적용 (고급스러운 다크 모드 및 차트 중심 레이아웃).

- 완료 기준 (Acceptance Criteria):
  - [x] 관리자가 과거 버전의 단어사전으로 롤백했을 때, 익일 예측에 해당 버전이 반영됨.
  - [x] 3개월 데이터 기반의 롤링 검증 레포트가 자동 생성되고 대시보드에서 조회 가능함.

- 2025-12-21 03:50:00: 전문가용 대시보드 분리 요구사항 분석 완료. PRD 11 섹션 업데이트 및 TASK-036 수립.
  - 2025-12-21 04:15:00: 사용자 상세 피드백 반영하여 TASK-036 세분화.
  - 2025-12-21 12:10:00: APIRouter 도입 및 Backend 아키텍처 이원화 완료.
  - 2025-12-21 12:25:00: AWO 엔진 초기 버전 및 백테스팅 매니저 UI 구현 완료.
  - 2025-12-21 14:55:00: 전체 기능 구현 및 검증 완료.

---

## TASK-037: Quant Hub UI/UX 고도화 및 직관적 통찰 제공
STATUS: COMPLETED

- 타입: UI-UX / Refinement
- 관련 PRD 섹션: "12. 분석 대시보드(Quant Hub) UI/UX 고도화 요건"
- 우선순위: P1
- 예상 난이도: M
- 목적:
  - 전문가용 대시보드에서 제공하는 복잡한 수치 데이터를 직관적인 시각 언어(히트맵, 게이지, 워드맵 등)로 치환하여 분석가의 통찰을 돕습니다.
  - 예측의 근거가 되는 뉴스 헤드라인을 모델의 피처와 연결(Grounding)하여 모델의 판단 과정을 투명하게 공개합니다.

- 상세 작업 내용:
  - [x] **[Backend] 추론 근거 연결 API (Evidence Grounding):**
    - [x] 특정 단어와 날짜를 입력받아, 해당 단어가 포함된 당시의 뉴스 헤드라인 리스트를 반환하는 엔드포인트 구현.
  - [x] **[Predictor] 예측 타겟 재정의 및 6-스테이트 로직 (6-State Taxonomy):**
    - [x] `Predictor.predict_advanced`가 `expected_alpha` 외에도 `intensity`를 산출하도록 수정.
    - [x] 6단계 상태(Strong Buy, Cautious Buy, Observation, Mixed, Cautious Sell, Strong Sell) 판별 로직 구현.
  - [x] **[Frontend] Current View 시각화 강화:**
    - [x] **감성 에너지 게이지:** 긍정/부정 베타의 총합 비율을 보여주는 반원 게이지 구현.
    - [x] **6-스테이트 배지:** 현재 종목의 상태를 직관적인 컬러 배지로 표시.
  - [x] **[Frontend] Timeline View 진화 추적 고도화:**
    - [x] `chartjs-chart-matrix` 플러그인 통합.
    - [x] **단어 가중치 히트맵:** 시간에 따른 20대 주요 단어의 베타 변화를 히트맵으로 구현.
  - [x] **[Frontend] Performance View 신뢰도 및 수치화:**
    - [x] **라벨링 전환:** '상승/하락' 라벨을 'Expected Alpha(%)'로 변경.
  - [x] **[Frontend] 알파 상관관계 산점도:** 예측 점수 vs 실제 알파의 분포 및 회귀선 시각화.
  - [x] **[System] 실시간 상태 및 맥락 제공:**
    - [x] **Grounding Sidebar:** 단어 클릭 시 뉴스 리스트를 보여주는 모달 구현.

- 변경 예상 파일/모듈:
  - `src/dashboard/routers/quant.py`, `src/dashboard/templates/validator.html`, `src/predictor/scoring.py`

- 완료 기준 (Acceptance Criteria):
  - [x] 대시보드에서 '상승/하락' 대신 예상 수익률(%) 수치가 표시됨.
  - [x] 탭 내 복잡한 선 차트 대신 히트맵을 통해 단어 변화를 한눈에 파악 가능함.
  - [x] 예측 점수와 수익률 간의 상관관계(산점도)가 시각화되어 모델의 통계적 유의성 확인 가능.

Progress Log:
  - 2025-12-21 12:35: 사용자 UI/UX 개선 요청에 따른 요구사항 도출 및 PRD 12 섹션 업데이트.
  - 2025-12-21 12:50: 사용자 모델 정합성 피드백 반영, 예측 타겟을 '수익률(Regression)' 중심으로 재정의 및 TASK-037 보완.
  - 2025-12-21 13:00: 6단계 시그널 및 히트맵, 게이지 UI 구현 완료. 마이그레이션 이슈 확인됨.
  - 2025-12-21 14:55: 마이그레이션 후 대시보드 검증 시 `Scatter Chart` 포함 모든 기증 정상 작동 확인.

---

## TASK-038: 재무 팩터 기반 멀티 타겟 모델 확장 연구 (Multi-Factor Research)
STATUS: COMPLETED

- 타입: research / feature
- 관련 PRD 섹션: "13. 예측 목표 재정의 및 멀티 팩터 확장"
- 우선순위: P2
- 예상 난이도: H
- 목적:
  - 뉴스 감성 데이터의 한계를 극복하기 위해 PER, PBR, Roe 등 종목별 재무 지표를 모델 피처로 통합합니다.
  - 수익률(Alpha) 외에도 변동성(Volatility)을 예측하여 리스크 관리 지표로 활용할 수 있는 기반을 마련합니다.

  - [x] **데이터 인프라 구축:** `tb_stock_fundamentals` 테이블 설계 및 수집 자동화 (`pykrx` 연동). (완료)
  - [x] **팩터 엔지니어링:** 재무 지표의 정규화(StandardScaler) 및 뉴스 데이터(Sparse TF-IDF)와 재무 데이터(Dense)의 하이브리드 입력층 구성.
  - [x] **Lasso 모델 확장:** `LassoLearner`를 수정하여 `use_fundamentals` 플래그를 지원하고, Dense/Sparse Matrix 병합(`hstack`) 로직 구현.
  - [x] **검증:** `src/scripts/research_multi_factor.py`를 통해 Hybrid 학습 파이프라인의 종단간(End-to-End) 동작 검증 완료 (Mock Data 기반).

- 완료 기준 (Acceptance Criteria):
  - [x] 재무 팩터가 통합된 새로운 Lasso 학습 파이프라인 프로토타입 완성.
  - [x] Mock Data 실험을 통해 재무 팩터가 피처로 선택(Coefficient > 0)될 수 있음을 확인.
  - [x] 연구용 스크립트 작성 완료.

Progress Log:
  - 2025-12-21 12:55: 종속 변수 확장 및 재무 데이터 통합 요구사항 반영하여 TASK-038 수립.
  - 2025-12-21 20:50: LassoLearner 하이브리드 확장 및 연구 스크립트 실행 완료. Mock Data 실험을 통해 파이프라인 유효성 검증.

---

## TASK-039: Quant Hub 데이터 정합성 보정 및 마이그레이션
STATUS: COMPLETED

- 타입: chore / Backend
- 관련 PRD 섹션: "13.1 모델 예측 목표의 실질적 전환"
- 우선순위: P0
- 목적:
  - 6단계 시그널 도입 전의 기존 예측 데이터(`tb_predictions`)를 새로운 형식(`intensity`, `status`, `expected_alpha`)에 맞게 보정하여 대시보드 가용성을 확보함.
- 상세 작업 내용:
  - [x] **[Backend] 데이터 마이그레이션 스크립트 작성:** `sentiment_score`를 기반으로 `expected_alpha`와 `status`를 채우는 SQL/Python 스크립트 실행.
  - [x] **[Database] 스키마 최종 확인:** 모든 컬럼에 `NOT NULL` 제약조건(기본값 포함)을 적용하여 쿼리 안정성 강화.
- 완료 기준:
  - [x] 대시보드 접속 시 과거 데이터에 대해서도 상태 배지와 게이지가 정상 표시됨.

Progress Log:
  - 2025-12-21 13:10: 데이터 마이그레이션 완료 (`sentiment_score` -> `expected_alpha`).

---

## TASK-040: Verification 결과와 Production 예측 통합 뷰어 구현
STATUS: COMPLETED

- 타입: feature / UI-UX
- 관련 PRD 섹션: "11.5 시스템 구성 검증 (WF Backtest Manager)"
- 우선순위: P1
- 목적:
  - 현재 실행 중인 백테스팅(AWO) 결과를 Quant Hub 대시보드에서 함께 볼 수 있도록 하여, 모델 검증 데이터의 부족을 시각적으로 보완함.
- 상세 작업 내용:
  - [x] **[Backend] 통합 데이터 헬퍼 구현:** `tb_predictions`와 `tb_verification_results`를 결합하여 반환하는 로직 개발.
  - [x] **[Frontend] Performance Chart 확장:** 실시간 예측 데이터와 백테스팅 데이터를 구분하여 단일 차트에 렌더링.
- 완료 기준:
  - [x] 백테스팅이 진행됨에 따라 대시보드 차트의 데이터 포인트가 실시간으로 늘어나는 것을 확인 가능함.

Progress Log:
  - 2025-12-21 13:20: `data_helpers.py` 수정으로 검증 데이터 통합 완료.

---

## TASK-041: 데이터베이스 재백업 및 복원 프로세스 정립 (Database Re-backup & Restore Process)
STATUS: COMPLETED

- 타입: process / documentation
- 관련 PRD 섹션: "8. 사고 이력 (Incident History)", "8.2 향후 과제 (Migration Stability)"
- 우선순위: P0
- 예상 난이도: S
- 목적:
  - 마이그레이션 중 발생한 데이터 복원 실패(덤프 호환성, 스키마 불일치)를 해결하기 위해, 실패 없는 표준화된 백업 및 복원 절차를 수립하고 지침서를 작성합니다.
- 상세 작업 내용:
  - [x] **Failure Analysis:** `\restrict` 구문 및 `COPY` 파싱 오류 원인 분석 (Postgres 버전 차이 및 Encoding 문제 확인)
  - [x] **Guideline Docs:** `docs/admin/재백업요청지침서.md` 작성 (표준 `pg_dump` 옵션 정의)
  - [x] **Restoration Test:** 표준 옵션으로 생성된 덤프 파일(`n_sentitrader_rebackup_v1.sql`)의 복원 성공 (데이터 정합성 및 대시보드 정상화 확인)
- 완료 기준:
  - [x] `재백업요청지침서.md`가 생성되어야 함.
  - [x] 지침서에 `--inserts`, `--clean`, `--encoding` 등 호환성 확보 옵션이 명시되어야 함.

Progress Log:
  - 2025-12-21 14:20: 마이그레이션 실패 원인 분석 후 TASK 수립.
  - 2025-12-21 14:35: `재백업요청지침서.md` 작성 완료 (PRD/Task 문서화 준수).
  - 2025-12-21 14:40: `n_sentitrader_rebackup_v1.sql` 파일 복원 성공 (248 rows predictions, 37k rows news). 대시보드 500 에러 해결.

---

## TASK-042: Worker 컨테이너 프록시 설정 오류 수정 (Fix Worker Proxy Config)
STATUS: COMPLETED

- 타입: bugfix / infra
- 관련 PRD 섹션: "8. 사고 이력 (Incident History)"
- 우선순위: P0
- 예상 난이도: S
- 목적:
  - Docker Compose의 기본 SOCKS Proxy 설정이 로컬 환경과 불일치하여 발생하는 `uv` 다운로드 실패 및 컨테이너 무한 재시작 문제를 해결합니다.
- 상세 작업 내용:
  - [x] **Log Analysis:** `address_worker` 및 `body_worker`의 `SOCKS error` 로그 확인.
  - [x] **Config Update:** `docker-compose.yml`에서 `HTTPS_PROXY`, `HTTP_PROXY`, `NO_PROXY` 환경변수 주석 처리.
  - [x] **Validation:** 컨테이너 재시작 후 `uv sync`가 정상적으로 진행되고 메트릭 서버가 시작되는지 검증.
- 완료 기준:
  - [x] `docker ps`에서 워커 컨테이너가 `Restarting` 상태가 아니라 `Up` 상태로 유지되어야 함.
  - [x] Grafana 모니터링에서 데이터가 정상적으로 수집되어야 함.

Progress Log:
  - 2025-12-21 14:45: 문제 원인 파악 및 긴급 수정 적용 (`docker-compose.yml`).
  - 2025-12-21 14:50: 워커 정상 구동 확인 및 TASK 문서화 완료.

---

## TASK-043: 백테스트 모니터링 및 제어 기능 강화 (Backtest Monitoring & Control)
STATUS: COMPLETED

- 타입: feature
- 관련 PRD 섹션: "8.2 향후 과제", "11.5 시스템 구성 검증"
- 우선순위: P1
- 예상 난이도: M
- 목적:
  - 백테스트(AWO Scan) 작업의 생명주기를 관리(중단, 삭제)하고, 중복 실행을 방지하여 시스템 자원을 효율적으로 사용합니다.
- 상세 작업 내용:
  - [x] **[Backend] 백테스트 제어 API 구현:**
    - [x] `POST /analytics/backtest/stop/{v_job_id}`: 작업 상태를 `stopped`로 변경.
    - [x] `DELETE /analytics/backtest/{v_job_id}`: 작업 레코드 및 관련 결과 삭제.
  - [x] **[Engine] AWOEngine 중단 로직 구현:**
    - [x] `run_exhaustive_scan` 루프 내에서 매 단계마다 DB의 `status`를 확인하여 `stopped`인 경우 즉시 중단.
  - [x] **[Backend] 중복 실행 방지 및 상태 관리:**
    - [x] `create_backtest_job` 시 동일 종목에 대해 `running`인 작업이 있는지 체크.
    - [x] 이미 실행 중인 경우 새 작업을 생성하지 않고 기존 작업으로 안내하거나 에러 메시지 반환.
  - [x] **[Frontend] UI 업데이트:**
    - [x] `backtest_list.html` 및 `backtest_row.html`에 'Stop' 및 'Delete' 버튼 추가.
    - [x] 상태 배지에 `Stopped` 스타일 추가.
    - [x] 중복 등록 시도 시 Toast 알림 또는 경고 메시지 표시.
- 변경 예상 파일/모듈:
  - `src/dashboard/routers/quant.py`, `src/learner/awo_engine.py`, `src/dashboard/templates/quant/backtest_list.html`, `src/dashboard/templates/quant/partials/backtest_row.html`
- 완료 기준 (Acceptance Criteria):
  - [x] 실행 중인 백테스트 작업의 'Stop' 버튼 클릭 시 작업이 즉시 중단되고 상태가 `Stopped`로 변경됨.
  - [x] 'Delete' 버튼 클릭 시 해당 작업과 상세 결과가 DB에서 삭제되고 목록에서 사라짐.
  - [x] 동일 종목에 대해 중복으로 백테스트를 시작하려 할 때 적절한 안내가 제공됨.

Progress Log:
  - 2025-12-21 15:10: 백테스트 제어 기능 부재 및 중복 실행 이슈 해결을 위한 TASK-043 수립.
  - 2025-12-21 15:25: Backend API 구현 및 Engine 로직 개선 완료. UI에 Stop/Delete 버튼 추가 및 테스트 완료.
## TASK-044: Timeline View 고도화 (Advanced Timeline View)
STATUS: COMPLETED

- 타입: feature / UI-UX
- 관련 PRD 섹션: "12.2 Timeline View 고도화"
- 우선순위: P1
- 예상 난이도: M
- 목적: 단어 가중치의 변화를 히트맵으로 시각화하여 모델의 판단 근거 추적성 강화
- 상세 작업 내용:
  - [x] **[Backend] 시계열 데이터 API 구현:**
    - [x] `get_timeline_dict`을 통해 주요 단어(Top 20)의 시간별 beta 값 조회
    - [x] `get_vanguard_derelict` 구현: 최근 7일 내 신규 진입 및 퇴출 단어 감지
  - [x] **[Frontend] 탭 네비게이션 구조 구현:**
    - [x] Validator 페이지에 3단 탭 구성 (HTMX 기반 전환)
  - [x] **[Frontend] 단어 가중치 히트맵 구현:**
    - [x] Chart.js Matrix Plugin을 활용하여 X:날짜, Y:단어 히트맵 시각화
    - [x] 가중치 강도에 따른 동적 색상(Emerald/Rose) 적용
  - [x] **[Frontend] Vanguard/Derelict 섹션:**
    - [x] 신규 진입 워드 및 퇴출 워드 별도 리스트 표시
- 완료 기준:
  - [x] Validator 페이지에서 Timeline 탭 클릭 시 히트맵 및 변동 리스트가 정상 표시됨
  - [x] 각 셀 클릭 시 해당 날짜의 근거 뉴스(Grounding) 팝업 연동 확인

## TASK-045: Performance Trend 차트 개선 (Performance Trend Chart Enhancement)
STATUS: COMPLETED

- 타입: feature / UI-UX
- 관련 PRD 섹션: "9.2 Performance Trend 차트 개선 요구사항"
- 우선순위: P1
- 예상 난이도: M
  - [ ] Tooltip에 상세 정보가 표시됨
  - [ ] 실제 Alpha 값이 정확하게 표시됨 (10배 곱하기 제거)

- 기술적 근거:
  - Chart.js Time Scale: https://www.chartjs.org/docs/latest/axes/cartesian/time.html
  - Chart.js Annotation Plugin: https://www.chartjs.org/chartjs-plugin-annotation/

Progress Log:
  - 2025-12-21 15:50: PRD 9.2 섹션 기반으로 TASK-045 수립.

## TASK-046: 예측값 이상치 클리핑 구현 (Outlier Clipping in Predictor)
STATUS: COMPLETED

- 타입: fix / refinement
- 관련 PRD 섹션: "13.4 이상치 관리 및 규제 강화"
- 우선순위: P0
- 예상 난이도: S
- 목적: 비상식적으로 높은 예측값(Outlier)이 산출되는 것을 방지하기 위해 +/- 15% 하드 클리핑 적용
- 상세 작업 내용:
  - [x] `src/predictor/scoring.py`의 `predict_advanced` 함수 수정
  - [x] 최종 `expected_alpha` 반환 전 `max(-0.15, min(0.15, val))` 적용
  - [x] 임계값 초과 시 로깅(Warning) 추가
- 완료 기준:
  - [x] 테스트 코드에서 15% 초과 입력 시 15%로 제한됨을 확인

## TASK-047: Lasso 모델 규제 강도(Alpha) 상향 조정
STATUS: COMPLETED

- 타입: chore
- 관련 PRD 섹션: "13.4 이상치 관리 및 규제 강화"
- 우선순위: P0
- 예상 난이도: S
- 목적: 모델의 일반화 성능 향상 및 계수 안정화를 위해 기본 alpha 값을 0.005로 변경
- 상세 작업 내용:
  - [x] `src/learner/lasso.py`의 `LassoLearner.__init__` 기본값 수정
  - [x] 기존 학습된 모델들과의 호환성 영향도 체크
- 완료 기준:
  - [x] 새롭게 학습된 딕셔너리의 계수(Beta) 분포가 이전보다 조밀해짐을 확인

## TASK-048: 성과 지표에 MAE 및 안정성 지표 추가
STATUS: COMPLETED

- 타입: feature
- 관련 PRD 섹션: "13.4 이상치 관리 및 규제 강화"
- 우선순위: P1
- 예상 난이도: M
- 목적: 방향성(Hit Rate)뿐만 아니라 수치형 오차(MAE)를 관리하여 예측 품질 정밀화
- 상세 작업 내용:
  - [x] `src/learner/validator.py`에서 MAE 계산 로직 추가
  - [x] `AWOEngine`의 결과 요약에 MAE 지표 포함
  - [x] DB `tb_verification_jobs`의 `result_summary` 스키마 반영
- 완료 기준:
  - [x] 백테스트 종료 후 Hit Rate와 함께 MAE 수치가 대시보드에 표시됨

## TASK-049: AWO Scan 완료 후 최적 모델 자동 배포(Promotion) 구현
STATUS: COMPLETED

- 타입: feature
- 관련 PRD 섹션: "Appendix B: AWO 기반 모델 자동 갱신 프로세스"
- 우선순위: P1
- 예상 난이도: M
- 목적: 백테스트에서 발견된 최적 학습 윈도우를 자동으로 실운영 모델에 적용
- 상세 작업 내용:
  - [x] `AWOEngine` 완료 시점에 `run_training` 호출 로직 추가
  - [x] 최적 윈도우($W_{best}$)를 사용하여 전체 데이터 재학습 및 `is_active=TRUE` 설정
  - [x] 배포 성공 여부를 결과 요약(`result_summary`)에 포함하여 기록
- 완료 기준:
  - [x] 시뮬레이션 테스트(verify_promotion.py)를 통해 `promote_best_model` 호출 시 DB의 Active 버전이 갱신됨을 확인

## TASK-050: 고스트 잡 방지를 위한 DB 스키마 확장 (Migration for Reliability)
STATUS: COMPLETED

- 타입: chore / migration
- 관련 PRD 섹션: "14.1 하트비트 기반 동적 상태 감시"
- 우선순위: P0
- 예상 난이도: S
- 목적: 작업의 실시간 진행 여부를 추적하기 위한 컬럼 추가
- 상세 작업 내용:
  - [x] `jobs` 테이블에 `updated_at` (TIMESTAMP), `retry_count` (INT), `worker_id` (VARCHAR) 추가
  - [x] `tb_verification_jobs` 테이블에 `updated_at` (TIMESTAMP), `retry_count` (INT) 추가
- 완료 기준:
  - [x] DB에서 해당 컬럼들이 정상적으로 조회됨을 확인

## TASK-051: 워커 하트비트 및 재시도 로직 구현 (Worker Heartbeat & Retry)
STATUS: COMPLETED

- 타입: feature / reliability
- 관련 PRD 섹션: "14.1 하트비트 기반 동적 상태 감시", "14.2 자동 재시도"
- 우선순위: P0
- 예상 난이도: M
- 목적: 워커 생존 여부를 DB에 주기적으로 기록하고 예외 처리 강화
- 상세 작업 내용:
  - [x] `AddressCollector.handle_job` 및 `AWOEngine.run_exhaustive_scan` 루프 내에 `updated_at` 갱신 로직 추가
  - [x] 작업 시작 시 `worker_id` 기록 기능 추가
  - [x] 수집 중인 403/429/Blocked 에러 발생 시 Exponential Backoff 적용
- 완료 기준:
  - [x] 작업 진행 중 `updated_at`이 1분 주기로 갱신됨을 확인

## TASK-052: 스테일 잡 자동 회복 스케줄러 구현 (Stale Job Recovery)
STATUS: COMPLETED

- 타입: feature / reliability
- 관련 PRD 섹션: "14.2 자동 재시도 및 스테일 잡 회복"
- 우선순위: P1
- 예상 난이도: M
- 목적: 죽은 작업을 감지하여 자동으로 재등록하거나 실패 처리
- 상세 작업 내용:
  - [x] `main_scheduler.py`에 `recover_stale_jobs` 함수 추가
  - [x] `running` 상태인데 `updated_at`이 10분 이상 지난 작업 탐색 및 처리
  - [x] `retry_count < max_retries` 이면 `pending`으로 리셋 및 MQ 재발행
  - [x] 10분 주기로 실행되도록 스케줄링 등록
- 완료 기준:
  - [x] 임의로 워커를 중단시킨 작업이 10분 후 자동으로 재시작됨을 확인

## TASK-053: 주요 메트릭 영속화 및 누적 데이터 보존 (Persistent Metrics)
STATUS: COMPLETED

- 타입: feature
- 관련 PRD 섹션: "14.3 작업 가시성 및 모니터링 강화"
- 우선순위: P2
- 예상 난이도: M
- 목적: 시스템 재시작 후에도 Grafana 대시보드 데이터 보존
- 상세 작업 내용:
  - [x] `src/utils/metrics.py`에 DB 기반 Persistent Gauge (`NSENTI_TOTAL_URLS` 등) 추가
  - [x] `main_scheduler.py`에 주기적으로 DB 카운트를 조회하여 메트릭을 동기화하는 로직 구현
  - [x] Grafana 대시보드(`n_senti_dashboard.json`)에 DB 합계 지표를 표시하는 Stat 패널 추가
- 완료 기준:
  - [x] 컨테이너 재시작 후에도 Grafana 차트의 수집 누계가 유지됨을 확인

## TASK-054: 운영 대시보드 UI/UX - 베이스 레이아웃 및 벤토 스태츠 구현
STATUS: COMPLETED

- 타입: feature / UI-UX
- 관련 PRD 섹션: "15.1 배경 및 목적", "15.2.1 시스템 하트비트"
- 우선순위: P1
- 예상 난이도: M
- 목적: 관리자 페이지의 기초 레이아웃을 Bento Grid로 전환하고 전역 상태 가시성 확보
- 상세 작업 내용:
  - [x] **[Frontend] 베이스 레이아웃 전환:**
    - [x] `index.html` (또는 홈 템플릿)의 레이아웃을 12컬럼 벤토 그리드 시스템으로 교체
    - [x] 전문가용 Dark/Light 모드 테마 및 typography(Inter/Outfit) 강화
  - [x] **[Frontend] System Heartbeat 카드:**
    - [x] Uptime, Active Workers를 "Pulse" 애니메이션과 함께 시각화하는 벤토 카드 구현
    - [x] 시스템 에러(최근 1시간) 카운터 하이라이트 패널
  - [x] **[Backend/Frontend] Queue & Success Rate:**
    - [x] RabbitMQ 큐 깊이(Queue Depth) 실시간 모니터링 카드
    - [x] Chart.js를 이용한 최근 24시간 수집 성공/실패율 도넛 차트 구현
- 완료 기준:
  - [x] 메인 페이지 접속 시 최상단에 4개의 주요 상태 벤토 카드가 정상 표시됨
  - [x] 시스템 상태에 따라 색상(Green/Amber/Red)이 동적으로 변함 확인

## TASK-055: 운영 대시보드 - 지능형 종목 등록 폼 (Smart Search)
STATUS: COMPLETED

- 타입: feature / UI-UX
- 관련 PRD 섹션: "15.2.2 지능형 Add Daily Target 경험"
- 우선순위: P1
- 예상 난이도: M
- 목적: 종목 등록 시 발생할 수 있는 입력 오류를 방지하고 설정 편의성 증대
- 상세 작업 내용:
  - [x] **[Frontend] 종목 검색 자동완성:**
    - [x] HTMX `hx-get`을 활용하여 입력 시 실시간 종목 서제스트 UI 구현
    - [x] 종목 코드 입력 시 매핑된 종목명 자동 렌더링
  - [x] **[Frontend] 수집 프로파일 카드:**
    - [x] Backfill 기간(1Y, 3M, 3Y)을 선택할 수 있는 디자인된 카드형 라디오 버튼 도입
  - [x] **[Frontend] 옵션 설정 직관화:**
    - [x] Auto-activate 토글 스위치 및 Lucide 아이콘 기반 툴팁 설명 추가
- 완료 기준:
  - [x] 종목 검색 창에 코드 또는 명칭 입력 시 관련 리스트가 하단에 나타남
  - [x] 백필 기간 선택 시 시각적으로 하이라이트되며, 등록 버튼 클릭 시 올바른 파라미터 전달 확인

## TASK-056: 운영 대시보드 - 실시간 작업 모니터링 및 상세 확장 뷰
STATUS: COMPLETED

- 타입: feature / UI-UX
- 관련 PRD 섹션: "15.2.3 실시간 수집 모니터링", "15.2.4 종목 리스트 관리 고도화"
- 우선순위: P1
- 예상 난이도: L
- 목적: 작업 상태를 직관적으로 파악하고, 깊이 있는 정보를 필요 시에만 노출하여 인지 부하 감소
- 상세 작업 내용:
  - [x] **[Frontend] 잡 리스트 테이블 고도화:**
    - [x] Status(Running, Completed, Failed)에 따른 배지 디자인(Pulse 애니메이션 포함) 적용
    - [x] Progress Bar 디자인 개선 (Slim line + Percentage text)
  - [x] **[Frontend] 상세 정보 확장(Expandable Row):**
    - [x] 각 작업 행(Row) 클릭 또는 Chevron 버튼 클릭 시 상세 로그/설정이 담긴 하위 패널 확장 UI 구현
    - [x] Worker ID, Priority, 실행 로그 스니펫 표시
  - [x] **[Frontend] 종목 관리 액션 보강:**
    - [x] 리스트 내 미니 Sparkline(최근 7일 수집량 추이) 추가하여 데이터 건전성 시각화
    - [x] 일괄 제어(Pause/Resume) 버튼의 접근성 및 피드백 개선
- 완료 기준:
  - [x] 작업 목록에서 Running 상태인 작업이 Pulse 애니메이션으로 강조됨
  - [x] 행 확장 시 작업의 세부 정보가 자연스럽게 펼쳐짐
  - [x] 종목 리스트에서 최근 수집 추이를 스파크라인으로 확인 가능함

Progress Log:
  - 2025-12-21 17:35: Ghost Job 문제 해결을 위한 Section 14 요구사항 기반 TASK-050~053 수립.
  - 2025-12-21 18:25: 운영 대시보드(Home) UI/UX 고도화를 위한 Section 15 요구사항 기반 TASK-054~056 수립.
  - 2025-12-21 21:05: 재무 데이터 수집 및 자동화(Pipeline) 구축을 위한 TASK-057 수립.

---

## TASK-057: 재무 데이터 수집 파이프라인 구축 및 스케줄링
STATUS: COMPLETED

- 타입: feature
- 관련 PRD 섹션: "13.2 종속 변수 및 피처 확장", "5. 시스템 아키텍처"
- 우선순위: P1
- 예상 난이도: M
- 목적:
  - 텍스트 분석 모델의 정확도 향상을 위해 재무 지표(PER, PBR 등)를 매일 자동으로 수집하여 DB에 적재합니다.
  - `pykrx` 라이브러리를 통해 공신력 있는 KRX 데이터를 확보합니다.

- 상세 작업 내용:
  - [x] **[Dependency]** `pykrx` 라이브러리 추가 (`uv add pykrx`) 및 컨테이너 환경 적용.
  - [x] **[Verification]** `src/collectors/fundamentals_collector.py`의 실제 동작 테스트 (Mock 제거 후 Real Data).
  - [x] **[Scheduling]** `main_scheduler.py`에 평일 오후 4시(16:00) 일괄 수집 Job 등록.

- 완료 기준 (Acceptance Criteria):
  - [x] `pykrx`가 설치된 환경에서 수집 스크립트가 에러 없이 실행되어야 함.
  - [x] `tb_stock_fundamentals` 테이블에 금일(또는 최근 거래일) 데이터가 정상적으로 INSERT/UPDATE 되어야 함.
  - [x] 스케줄러 로그에 재무 수집 Job 등록 확인.

Progress Log:
  - 2025-12-21 21:05: 작업 정의 및 시작.
  - 2025-12-21 21:10: `pykrx` 의존성 추가 및 스케줄러 재시작 완료. 운영 환경 적용됨.

---

## TASK-058: 검증 대시보드 - 절대값 스택형 감성 차트 개선
STATUS: COMPLETED

- 타입: fix / feature
- 관련 PRD 섹션: "9.2 Performance Trend 차트 개선 요구사항 (R8)"
- 우선순위: P0
- 예상 난이도: S
- 목적:
  - 검증 대시보드(Performance Tab)에서 부정 감성 점수(Negative Score)가 아래로 향하여 시각적 인지가 어려운 문제를 해결합니다.
  - 긍정/부정 점수를 모두 절대값(Absolute)으로 변환하여 Y축 위로 쌓아 올리는(Stacked) 방식으로 변경하여, 총 감성 강도(Intensity)를 직관적으로 표현합니다.

- 상세 작업 내용:
  - [x] **[Frontend]** `src/dashboard/templates/validator.html` 내 `renderChart` 함수 수정:
    - [x] `Negative Sentiment` 데이터셋에 `Math.abs()` 적용.
    - [x] 두 데이터셋(Positive, Negative)에 `stack: 'sentiment'` 속성 추가.
    - [x] `y-sentiment` 스케일 옵션에 `stacked: true` 적용.

- 완료 기준 (Acceptance Criteria):
  - [x] `/analytics/validator` 페이지의 Performance 탭 차트에서 부정 점수(Red Bar)가 Y=0 위로 올라와야 함.
  - [x] 긍정 점수(Green Bar) 위에 부정 점수가 쌓이는 형태(Total Height = Intensity)로 렌더링되어야 함.

  - 2025-12-21 21:20: `renderChart` 함수 수정 및 Stacked Bar 설정 적용 완료.

---

## TASK-059: 대시보드 - 6-State Market Signal 시각화
STATUS: COMPLETED

- 타입: feature / UI-UX
- 관련 PRD 섹션: "13.1 모델 예측 목표의 실질적 전환", "15.1 배경 및 목적"
- 우선순위: P1
- 예상 난이도: S
- 목적:
  - 단순 수치(Sentiment Score)만 표시되던 대시보드 상단 카드를 'Actionable Market Signal' (Strong Buy ~ Strong Sell) 형태로 업그레이드.
  - PRD 13.1에 정의된 6단계 Taxonomy에 따라 카드 배경색 및 텍스트를 동적으로 변경하여 직관성 강화.

- 상세 작업 내용:
  - [x] **[Frontend]** `src/dashboard/routers/quant.py`: `latest_prediction` 데이터에 `status` 필드가 누락되지 않도록 확인 (이미 존재함).
  - [x] **[Frontend]** `src/dashboard/templates/validator.html` 수정:
    - [x] 첫 번째 Bento Card("Latest Score")의 배경색 CSS 클래스를 Jinja2 조건문으로 동적 할당.
      - Strong Buy: `bg-indigo-600`
      - Cautious Buy: `bg-blue-500`
      - Observation: `bg-slate-500`
      - Mixed: `bg-amber-500`
      - Cautious Sell: `bg-orange-500`
      - Strong Sell: `bg-red-600`
    - [x] Score 숫자 위에 시장 상태 텍스트(예: "STRONG BUY")를 뱃지 형태로 표시.

- 완료 기준 (Acceptance Criteria):
  - [x] 대시보드 로드 시, 최신 예측 상태(Status)에 따라 첫 번째 카드의 색상이 변경되어야 함.
  - [x] 정확한 Signal Text가 표시되어야 함.

  - 2025-12-21 21:40: 작업 수립.
  - 2025-12-21 21:45: `validator.html`에 Jinja2 로직 및 Tailwind CSS 스타일 적용 완료.

---

## TASK-060: [Expert View] 타임라인 뉴스 펄스 및 헤드라인 툴팁 구현
STATUS: COMPLETED

- 타입: feature / UI-UX
- 관련 PRD 섹션: "R12.2.4, R12.2.5"
- 우선순위: P1
- 예상 난이도: M
- 목적:
  - 감성 가중치 변화의 배경이 되는 뉴스 발생량을 시각화하여 상관관계 분석력을 높임.
  - 특정 날짜 호버 시 주요 헤드라인을 표시하여 정성적 분석 지원.

- 상세 작업 내용:
  - [x] **[Backend]** `get_timeline_dict` 수정 또는 신규 API를 통해 일별 뉴스 수집 건수 및 Top 3 헤드라인 반환.
  - [x] **[Frontend]** Timeline 탭의 Matrix Chart 상단에 뉴스 발생량 막대 차트(Bar Chart) 추가.
  - [x] **[Frontend]** 뉴스 발생량 급증일(Event Day) 자동 마킹 (Annotation Plugin 활용).
  - [x] **[Frontend]** 마커/데이터 포인트 호버 시 헤드라인 툴팁 표시 로직 구현.

- 완료 기준 (AC):
  - [x] 히트맵 상단에 뉴스 건수 차트가 동기화되어 표시됨.
  - [x] 특정 지점 클릭/호버 시 해당 일자의 뉴스 제목이 팝업 또는 툴팁으로 노출됨.

## TASK-061: [Expert View] AWO 최적화 랜드스케이프 시각화
STATUS: COMPLETED

- 타입: feature / UI-UX
- 관련 PRD 섹션: "R12.3.4"
- 우선순위: P1
- 예상 난이도: M
- 목적: 모델이 왜 특정 학습 윈도우를 선택했는지에 대한 데이터 기반 근거를 제시하여 신뢰도 확보.

- 상세 작업 내용:
  - [x] **[Backend]** `tb_verification_jobs.result_summary`에서 스캔 결과(1-11m)를 추출하여 반환하는 API 구현.
  - [x] **[Frontend]** Performance 탭 내에 "Optimization Scan Result" 섹션 추가.
  - [x] **[Frontend]** 윈도우 크기별 Hit Rate(선) 및 MAE(막대)를 결합한 이중 축 차트 구현.

- 완료 기준 (AC):
  - [x] 1개월부터 11개월까지의 검증 성과가 한 눈에 차트로 표시됨.
  - [x] 최적점(Best Window)이 차트 상에 강조 표시됨.

## TASK-062: [Model] 예측 신뢰 지수(Confidence Score) 산출 및 표시
STATUS: COMPLETED

- 타입: feature
- 관련 PRD 섹션: "13.6"
- 우선순위: P1
- 예상 난이도: M
- 목적: 예측 신호의 강도뿐만 아니라 '신뢰할 수 있는 정도'를 수치화하여 의사결정 보조.

- 상세 작업 내용:
  - [x] **[Database]** `tb_predictions` 테이블에 `confidence_score` 컬럼 추가 (Migration).
  - [x] **[Backend]** `Predictor.predict_advanced`에 뉴스량, MAE 기반 신뢰도 산식 적용.
  - [x] **[Frontend]** Market Signal 카드 내에 신뢰도 지수를 시계성 지표와 함께 시각화.

- 완료 기준 (AC):
  - [x] 신호 발생 시 0~100% 사이의 신뢰도 점수가 함께 저장됨.
  - [x] 대시보드에서 신호별 신뢰도가 시각적으로 표현됨.

## TASK-063: [Infra] OpenDART 공시 데이터 수집기 구현 (Phase 1)
STATUS: COMPLETED

- 타입: feature
- 관련 PRD 섹션: "13.5"
- 우선순위: P2
- 예상 난이도: L
- 목적: 뉴스 외에 주가에 직접적 영향을 미치는 '공시' 데이터를 피처로 통합하기 위한 기초 구축.

- 상세 작업 내용:
  - [x] **[Collector]** OpenDART API 연동 모듈 `src/collectors/disclosure_collector.py` 생성.
  - [x] **[Task]** 종목별 주요 공시(공급계약, 증자 등) 필터링 및 수집 로직 구현.
  - [x] **[Database]** 수집된 공시 데이터를 `tb_news_mapping`에 `DART_` 접두어와 함께 적재하여 모델 학습에 포함.

- 완료 기준 (AC):
  - [x] OpenDART API를 통해 특정 종목의 공시 목록이 DB에 정상 저장됨 (Mock 데이터로 검증 완료).
  - [x] Lasso 학습 시 공시 데이터가 피처로 인식됨을 확인(Log).

Progress Log:
  - 2025-12-21 23:55: 차세대 시각화 및 멀티 소스 확장을 위한 TASK-060~063 수립.
  - 2025-12-22 09:35: TASK-063 Phase 1 작업 시작.
  - 2025-12-22 09:45: `DisclosureCollector` 구현 및 `main_scheduler.py` 통합 완료. `opendartreader` 의존성 추가.
  - 2025-12-22 09:55: Mock 데이터를 활용하여 공시 데이터가 Lasso 학습 파이프라인(TF-IDF)에 정상 유입됨을 확인.


## TASK-064: [Infra] 일일 주가 수집 및 초과수익률(Actual Alpha) 확정 로직 구현
STATUS: COMPLETED

- 타입: infrastructure
- 관련 PRD 섹션: "13.7"
- 우선순위: P1
- 예상 난이도: M
- 목적: 예측 결과에 대한 실제 시장 성과(Actual Alpha)를 자동으로 동기화하여 대시보드 검증 가시화.

- 상세 작업 내용:
  - [x] **[Collector]** `PriceCollector` 구현: 종목 종가 및 벤치마크(KOSPI) 지수 수집.
  - [x] **[Logic]** `excess_return` 산출 및 `tb_daily_price` 적재.
  - [x] **[Settlement]** `tb_predictions.actual_alpha` 백필 로직 구현 (T-1일 예측에 대해 T일 종가 반영).
  - [x] **[Scheduler]** 매일 장 마감 후 실행되도록 `main_scheduler.py` 등록.

- 완료 기준 (AC):
  - [x] 매일 16:00 이후 `tb_predictions`의 `actual_alpha`가 자동 생성됨.
  - [x] 대시보드 Performance 탭에서 'Actual Alpha' 차트가 최신일자까지 표시됨.

Progress Log:
  - 2025-12-22 00:28: TASK-064 수립 및 주가 데이터 수집기 구현 시작.
  - 2025-12-22 00:45: `PriceCollector` 구현 및 `actual_alpha` 정산 로직 테스트 완료.
  - 2025-12-22 00:50: 대시보드 연동 확인 및 TASK-064 마감.

## TASK-065: [Model] 백테스트 기반 감성 사전 단어별 신뢰도 검증 로직 구현
STATUS: COMPLETED

- 타입: feature
- 관련 PRD 섹션: "13.8"
- 우선순위: P1
- 예상 난이도: M
- 목적: 단어 사전의 계수가 실제 시장 변동과 얼마나 일치하는지 통계적으로 검증하여 전문가에게 도출.

- 상세 작업 내용:
  - [x] **[Logic]** 단어별 Hit-Rate 산출: 특정 단어가 포함된 뉴스가 나온 날의 익일 Alpha 방향 일치율 계산.
  - [x] **[Logic]** Stability Score 산출: AWO 스캔 결과(여러 윈도우)에서 해당 단어의 계수($\beta$) 표준편차 계산.
  - [x] **[Backend]** 분석 API (`/analytics/word_detail`) 구현: 특정 단어의 검증 리포트 데이터 서빙.
  - [x] **[Frontend]** 단어 상세 정보 모달(Modal) 구현: 한글/그래프 기반의 단어 신뢰도 시각화.

- 완료 기준 (AC):
  - [x] 단어 클릭 시 해당 단어의 백테스트 기반 Hit-Rate(0~100%)가 노출됨.
  - [x] 최근 6개월간 계수 변동 추이가 차트로 표시됨.

Progress Log:
  - 2025-12-22 00:35: TASK-065 수립 및 사전 검증 고도화 계획 추가.
  - 2025-12-23 01:00: Hit-Rate 로직, 백엔드 API, 그리고 Chart.js 기반의 안정성 시각화 모달 구현 완료 및 검증.

## TASK-066: [Infra] OpenDART 공시 본문 수집 및 정밀 분석 (Phase 2)
STATUS: COMPLETED

- 타입: feature
- 관련 PRD 섹션: "13.5"
- 우선순위: P2
- 예상 난이도: M
- 목적: 공시 제목뿐만 아니라 '본문'의 핵심 수치(계약금액 등)를 추출하여 모델의 예측 정확도를 극대화.

- 상세 작업 내용:
  - [x] **[Collector]** `opendartreader.document()`를 활용한 공시 본문 HTML 수집 로직 추가.
  - [x] **[NLP]** BeautifulSoup을 활용한 본문 텍스트 추출 및 불필요한 태그 제거.
  - [x] **[Database]** 추출된 텍스트 데이터를 `tb_news_content`에 병합하여 Lasso 피처로 활용.

- 완료 기준 (AC):
  - [x] `tb_news_content`에 공시 본문의 핵심 요약 텍스트가 정상적으로 저장됨.
  - [x] Lasso 단어 사전에 공시 관련 구체적 키워드가 등장함을 확인.
  - [x] Tokenizer에서 숫자(SN) 태그를 추출하여 금액/수치 피처 확보.

Progress Log:
  - 2025-12-23 01:10: TASK-066 수립 및 공시 상세 수집 계획 수립.
  - 2025-12-23 01:25: BeautifulSoup 기반 본문 파싱 구현 및 Tokenizer(SN 태그) 고도화 완료.

## TASK-067: [Infra] RabbitMQ DLX(Dead Letter Exchange) 구현 및 재시도 신뢰성 확보
STATUS: COMPLETED

- 타입: infrastructure / reliability
- 관련 PRD 섹션: "14.3", "16.3"
- 우선순위: P1
- 예상 난이도: M
- 목적: 수집 실패 메시지를 격리하여 시스템 안정성을 높이고 재처리 메커니즘 구축.

- 상세 작업 내용:
  - [x] **[Infra]** RabbitMQ 큐 선언 시 `x-dead-letter-exchange` 옵션 추가.
  - [x] **[Infra]** `nsenti.dlx` 교환기 및 `dead-letter-queue` 생성 및 바인딩.
  - [x] **[Collector]** 메시지 처리 실패 시(Nack) 자동으로 DLX로 이동하는지 확인.
  - [x] **[Backend]** DLX에 쌓인 메시지를 수동으로 재시작(Re-enqueue)할 수 있는 관리용 스크립트 작성.

- 완료 기준 (AC):
  - [x] 예외 발생 시 메시지가 소실되지 않고 `dead-letter-queue`에 적재됨.
  - [x] RabbitMQ Management UI 또는 API를 통해 DLX 상태 확인 가능.

Progress Log:
  - 2025-12-23 01:40: DLX 인프라 선언 로직 및 Nack 처리 적용 완료. `test_dlx.py` 검증 성공.

## TASK-068: [UI/UX] 운영 대시보드 벌크 컨트롤(Bulk Action) 및 검색/필터링 구현
STATUS: COMPLETED

- 타입: feature / UI-UX
- 관련 PRD 섹션: "15.4"
- 우선순위: P1
- 예상 난이도: M
- 목적: 다수의 수집 종목을 효율적으로 관리하고 검색 편의성 증대.

- 상세 작업 내용:
  - [x] **[Frontend]** 종목 리스트 테이블 상단에 '검색창' 및 '상태 필터링' 버튼 추가.
  - [x] **[Frontend]** 체크박스 기반 멀티 선택 기능 및 하단 'Action Bar' 구현.
  - [x] **[Backend]** 선택된 다수 종목에 대해 Pause/Resume/Delete를 수행하는 벌크 API API (`/targets/bulk`) 구현.
  - [x] **[UI]** 벌크 작업 처리 시 Toast 메시지로 개별 성공/실패 여부 피드백 제공.

- 완료 기준 (AC):
  - [x] 대상을 선택하고 'Bulk Pause' 클릭 시 선택된 모든 종목 상태가 일괄 변경됨.
  - [x] 검색창 입력 시 HTMX를 통해 리스트가 실시간 필터링됨.

Progress Log:
  - 2025-12-23 01:50: HTMX 기반 검색 및 퓨어 JS 기반 벌크 액션 바 구현 완료.

## TASK-069: [Model] 거래량 가중 감성 강도(Volume-weighted Intensity) 적용
STATUS: COMPLETED

- 타입: feature / model
- 관련 PRD 섹션: "16.2"
- 우선순위: P2
- 예상 난이도: S
- 목적: 거래량이 동반된 뉴스 신호에 더 높은 가중치를 부여하여 예측 정확도 향상.

- 상세 작업 내용:
  - [x] **[Logic]** `Predictor.predict_advanced`에 당일 거래량 / 5일 평균 거래량 비율 산출 로직 추가.
  - [x] **[Logic]** `intensity` 및 `expected_alpha` 계산 시 거래량 가중치($\log(1+V_{ratio})$) 반영.
  - [x] **[Backend]** 가중치가 적용된 `intensity`를 DB에 저장 및 대시보드 시각화.

- 완료 기준 (AC):
  - [x] 거래량이 급증한 날의 예측 리포트에서 `intensity`가 평소보다 높게 나타남을 확인.
  - [x] 백테스트 시 거래량 가중 적용 전/후의 성능 비교(MAE 개선 여부).

Progress Log:
  - 2025-12-23 02:00: `tb_daily_price`에 volume 컬럼 추가 및 Predictor 가중치 로직 적용 완료.

## TASK-070: [Model] AWO 기반 모델 자동 프로모션 및 드리프트 감시 파이프라인 구축
STATUS: COMPLETED

- 타입: feature / model
- 관련 PRD 섹션: "18.1", "18.2", "18.3"
- 우선순위: P1
- 예상 난이도: L
- 목적: 지속적으로 최적의 윈도우를 탐색하고, 성능 저하 시 스스로 복구하는 자생적 모델 운영 환경 구축.

- 상세 작업 내용:
  - [x] **[Database]** `tb_sentiment_dict_meta` 테이블에 `parent_version` 컬럼 추가 (롤백 경로 확보).
  - [x] **[Backend]** `AWOEngine.promote_best_model` 수정: 프로모션 시 `parent_version` 기록 및 임계값(Hit-Rate > 50%) 검증 로직 추가.
  - [x] **[Backend]** `DriftMonitor` 클래스 구현: 최근 7일간의 `tb_predictions` 성과를 분석하여 드리프트 및 롤백 트리거.
  - [x] **[Infra]** `main_scheduler.py`에 매주 일요일 00:00 AWO 전수 스캔 및 매일 드리프트 체크 잡 등록.

- 완료 기준 (AC):
  - [x] AWO 스캔 결과 Hit-Rate가 50%을 넘지 못할 경우 프로모션이 중단됨을 단위 테스트로 확인.
  - [x] 강제로 낮은 성과 데이터를 주입했을 때 시스템이 자동으로 이전 버전으로 롤백(is_active 전환)하는지 확인.
  - [x] 스케줄러를 통해 AWO 스캔이 정상적으로 예약되는지 확인.

Progress Log:
  - 2025-12-23 02:20: TASK-070 수립 (3FS 프로세스 준수).
  - 2025-12-23 02:40: DB 스키마 확장 및 AWOEngine/DriftMonitor 구현 완료.
  - 2025-12-23 02:45: 스케줄러 등록 및 자동 롤백 테스트 통과. STATUS changed to COMPLETED.
