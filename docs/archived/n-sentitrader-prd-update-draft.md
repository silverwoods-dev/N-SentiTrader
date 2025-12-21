# N-SentiTrader PRD — Draft Update: Collection / Preprocessing / Learning / Prediction + Admin Dashboard

Status: DRAFT — For review. Do NOT start tasks; await user confirmation.

This draft follows the repository guidance in `.github/copilot-instructions.md` and the PRD conventions in `.github/3fs/create-prd.md`.

## 목표
- 수집·저장 과정을 세분화하여 마이크로서비스(컨테이너) 단위로 분리
- 초기 Backfill(지난 1년)과 매일 증분(Incremental) 수집을 분리 운영
- 관리자가 수집작업을 생성·제어·모니터링할 수 있는 웹 대시보드 제공
- Backfill로 생성된 대상은 `daily_targets`에 자동 등록되나 기본적으로 `paused` 상태로 등록하여 관리자 승인/스케줄로 활성화할 수 있도록 함

## 핵심 요구사항 (요청사항 반영)

1) 주소 수집(Separate Address Collector)
- 기능: 키워드, 주식종목코드 등으로 검색된 뉴스 목록에서 뉴스의 주소(URL)만 수집.
- 저장: URL 정규화(스킴/쿼리 제거 등) → 해시 기반 중복 검사 → DB 저장(예: `tb_news_url` / `tb_news_content` 초기엔 URL만).
- 스케줄: 초기 Backfill(역순 최신→과거), 이후 증분은 주기적(스케줄러) 처리.

2) 주소 증분 수집(Incremental Address Check)
- 기능: 주기적으로(예: 매일/시간 단위) 포털 검색을 수행하여 목록에 없는 주소를 추가.

3) 본문 수집(Body Collector)
- 기능: `collected=false` 또는 `pending` 상태의 URL을 조회하여 제목·본문·메타를 수집.
- 성공: 원문 저장(제목/본문/메타) → `collected=true` 표기.
- 실패: 재시도 정책(예: 3회, 지수적 백오프) → 재시도 후 실패 시 `error`로 표기 및 `tb_news_errors`에 기록.
- 오류 관리: 별도 배치에서 실패 목록 점검(삭제된 주소, 포맷/구조 변경 등 분류).

4) 구조 변화 대응
- 포털 HTML 구조 변화(시기별)로 인한 파싱 실패 사례는 구조 유형별로 분류하여 멀티-패턴 파서 또는 스마트 적응 기법 학습 자료로 활용.

5) 원문 저장
- 원문(제목·본문)은 변형 없이 보관(감리·재처리용).

6) 토크나이징(Preprocessor / Tokenizer)
- 기능: 수집된 뉴스 중 전처리/토크나이징이 되지 않은 레코드를 주기적 배치로 처리.
- 완료 표기: `preprocessed=true` 또는 `tokens`(JSONB) 업데이트.
- 실패 처리: 전처리 오류 시 재시도 또는 수동 검토 플로우.

7) 전처리 연계 및 학습 파이프라인
- 전처리 완료 데이터는 학습(배치)·분석·리포트 파이프라인으로 전달.

8) 단어사전 학습 정책
- 메인 사전: 최대 1년, 최소 3개월치 데이터를 주간 단위로 학습·업데이트.
- 버퍼 사전: 최근(이번주) 데이터의 급변 단어를 반영하기 위한 별도 일간/수시 사전.

9) 예측(Serving) 및 리포트
- 예측 엔진은 메인 + 버퍼 사전을 앙상블하여 점수 산출.
- 리포트에는 앙상블 결과, 메인 단독 결과, 버퍼 단독 결과 모두 포함.
- 영향 단어: 예측에 가장 큰 영향을 준 긍정 단어 10개·부정 단어 10개 및 영향도 표기(부족하면 존재 항목만 표기).
- 영향 뉴스: 상기 단어들을 포함한 뉴스 중 예측에 가장 영향이 큰 뉴스(긍정 10건·부정 10건, 가능 범위만 표시).
- 뉴스 항목: 제목, 일자, 원문 URL 포함.

10) 리포트 보관 및 대시보드
- 일별 리포트(예: JSON/MD/PARQUET) 저장 및 대시보드 제공.
- 뷰: 일/주/월 단위(기본: 주단위). 주단위 리포트에는 지난주 실제 주가, 예측 내용, 예측 평가(오차)를 포함.
- UI: 요일별 예측/실제 비교(가능하면 미래의 아직 오지 않은 요일 예측도 표시).

11) Backfill vs Daily 동작 관례
- Backfill(One-time): 지난 1년치(또는 지정 기간) 역순 수집. 완료 후에는 동일 범위에 대해 주기적 재수행하지 않음(수집 범위 변경 시 재실행 가능).
- Daily Incremental: 매일 새벽(운영 정책에 따름) 전일 이후 공개된 새로운 뉴스 목록 수집.
- Backfill로 추가된 대상은 `daily_targets`에 자동 등록되나 기본 상태는 `paused`(관리자 승인/스케줄로 활성화). 등록 메타에는 `backfill_registered_at`, `backfill_completed_at`, `daily_registered_at`, `status`(paused/active/disabled), `activation_requested_at` 등을 포함.

12) 관리자 웹 대시보드 기능
- CRUD: 수집 작업(Job) 생성(키워드/종목코드), 시작/중지, 삭제.
- 작업 유형: Backfill(One-time) / Daily(Recurring).
- 모니터링: 진행률(총 URL/처리/성공/실패), 상태(pending/running/paused/completed/error), 최근 에러 샘플.
- 제어: 수동 재시작, 강제 중단, 실패 URL 재시도 트리거, 활성화 예약.
- 권한: 관리자 전용 작업 제어(간단한 RBAC 필요).

13) 작업·메트릭 저장소 설계(요약)
- `jobs` 테이블: `job_id`, `type`, `params`, `created_by`, `schedule`, `last_run`, `status`, `progress` 등.
- `job_logs` 테이블: 실행별 요약(실행시간, 처리수, 오류수).
- `daily_targets` 테이블: `target_id`, `params`, `backfill_registered_at`, `backfill_completed_at`, `daily_registered_at`, `status`, `activation_requested_at`.
- `tb_news_errors`: 실패 URL 및 원인 기록.

14) 실패·재시도 및 알림
- URL 실패: 최대 3회 재시도(지수적 백오프). 재시도 후 실패는 `tb_news_errors`에 보관.
- 장기 Backfill 작업(수시간~수일): 완료/중단/심각 오류 시 이메일/슬랙 알림.
- 대시보드: 실시간(또는 1분 주기) 작업 상태 업데이트.

15) 검증·수용 기준(예시)
- Backfill: 지정 기간(예: 1년) 내 URL 목록 95% 이상 수집 완료(중복/삭제 제외).
- Daily: 신규 URL을 중복 없이 정확히 등록.
- 대시보드: 작업 생성/중단/삭제 및 진행률 확인 기능 정상 동작(관리자 권한).

16) 타당성 조사(요청 시 수행)
- 필요 시 아래 항목을 외부 자료로 조사하여 요구사항을 보강합니다:
  - 대용량 Backfill 전략(분할·병렬화·속도 조절, politeness), 분산 큐 활용 방안.
  - URL 정규화·중복 판별(best practices).
  - 스케줄러 선택(예: APScheduler, Airflow, cron 비교).
  - 관리자 대시보드 UX/보안(작업 제어·감시) 패턴.

---

Do NOT execute any collection jobs or create tasks from this draft. Reply with either:
- `Proceed with research` — I will fetch and attach validated external references and citations to this draft; or
- `Edit` — request changes to this draft (indicate which sections to change).

