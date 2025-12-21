# PRD Addendum — Collection Workflow & Admin Dashboard

Status: DRAFT — For review. Do NOT start tasks; await user confirmation.

## 목적
지난 1년치 뉴스의 초기가입(Backfill)과 매일 새벽의 증분(Incremental) 수집을 분리하고, 이를 생성·관리·모니터링할 수 있는 관리자용 웹 대시보드를 PRD에 추가합니다. 또한, Backfill로 생성된 수집 대상은 자동으로 일간 수집 대상 목록에 등록되어 관리 가능해야 합니다.

## 요구사항 (요약)

1) 수집 시점 및 타입
- 초기 Backfill(One-time):
  - 범위: "최근 1년치" 뉴스(검색 키워드 또는 종목코드별). 
  - 실행 시점: 시스템 초기화 시 수동으로 또는 관리자 대시보드에서 명시적 생성.
  - 동작: 최신 일자부터 과거로 점진적(역순)으로 수집 진행.
  - 중단 조건: 1년치 목록(또는 사용자 지정 범위)이 완성되면 더 이상 Backfill을 주기적으로 실행하지 않음(단, 수집 범위 변경 시 재실행 가능).

- 일간 Incremental(Continuous):
  - 범위: 전일(또는 마지막 완료 시점) 이후에 공개된 새로운 뉴스 목록.
  - 실행 빈도: 매일 새벽(운영 시간 정책에 따름).
  - 동작: 매일 실행되어 신규 URL을 수집/저장하고, 중복은 제거함.

2) 관리자용 웹 대시보드 기능
- 수집 작업(Job) CRUD: 키워드/종목코드 입력으로 Backfill 혹은 Daily 수집 작업을 생성, 시작/중지, 삭제 가능.
- 작업 유형 지정: Backfill(One-time) / Daily(Recurring).
- 작업 모니터링: 진행률(예: 총 URL/처리된 URL/성공/실패), 상태(pending/running/paused/completed/error), 최근 에러 샘플 확인.
- 작업 제어: 수동 재시작, 강제 중단, 실패 URL 재시도 트리거.
- 권한: 관리자만 작업 생성/삭제/중단 가능(간단한 역할 기반 권한 모듈 필요).

3) Backfill → Daily 자동 등록
- Backfill으로 생성된 대상(키워드/종목코드)은 바로 `daily_targets` 관리 목록에 **자동으로 추가**되지만, 기본적으로 `paused`(혹은 `pending_activation`) 상태로 등록됩니다. 다만, Backfill 수행 중에도 Daily 작업을 병렬로 실행할지 여부를 Backfill 생성 시 `run_daily_during_backfill`(또는 `auto_activate_daily`) 옵션으로 선택할 수 있도록 합니다. 이 옵션의 기본값은 `false`이며, `true`로 설정하면 Backfill 진행 중에도 Daily 스케줄이 즉시 활성화되어 신규 뉴스에 대해 일간 수집이 병렬로 수행됩니다.
- `daily_targets` 엔트리는 다음 메타를 포함해야 합니다: `target_id`, `params`(키워드/종목코드), `backfill_registered_at`, `backfill_completed_at`, `daily_registered_at`(자동 등록 시점), `status`(paused/active/disabled), `activation_requested_at`(관리자가 스케줄을 지정한 경우).
- 관리자는 대시보드에서 자동으로 추가된 `daily_targets`를 즉시 활성화하거나, 특정 시점에 활성화되도록 예약할 수 있습니다. 자동 활성화 옵션은 Backfill 생성 시 선택적 플래그(`auto_register_daily=true/false`, `auto_activate_daily=true/false`)로 제공하며, 기본 권장은 `auto_register_daily=true` 및 `auto_activate_daily=false`입니다.
- 자동 등록 목록은 `daily_targets` 관리 뷰에서 진행/중단/삭제 및 상태 전환(activate/pause) 가능.

4) 상태·메트릭 저장소
- 작업 메타: `jobs` 테이블(또는 관리용 Redis/Task DB)에 job_id, type, params, created_by, schedule, last_run, status, progress 등 저장.
- 수행 로그: `job_logs` 테이블에 실행별 요약(실행시간, 처리수, 오류수) 보관.

5) 실패·재시도 정책
- 각 URL 수집 실패 시 재시도(예: 3회, exponential backoff)를 적용.
- 재시도 이후에도 실패한 URL은 `tb_news_errors` 또는 `job_failed_items`로 기록되어 수동 검토 대상이 됨.

6) 운영·알림
- 장기 백필 작업(수시간~수일 소요) 상태는 이메일/슬랙 알림으로 통지(완료/중단/심각오류).
- 대시보드는 작업 진행중인 경우 실시간(또는 1분 주기) 업데이트.

7) 자동화 규칙(옵션)
- Backfill 작업 생성 시, 관리자 옵션으로 `auto_register_daily`(자동 등록 여부)와 `auto_activate_daily`(자동 활성화 여부)를 제공하되, 권장 기본값은 `auto_register_daily=true` 및 `auto_activate_daily=false`입니다(즉, 자동으로 `daily_targets`에 추가하지만 초기 상태는 `paused`).
- Backfill이 끝난 대상에 대해 Daily 수집 주기(매일 새벽, 또는 운영자 지정 시간)를 설정 가능하며, 관리자는 대시보드에서 개별 `daily_targets`의 활성화 스케줄을 수정할 수 있습니다.

8) 검증·수용 기준
- Backfill 작업: 지정한 기간(예: 1년) 내 URL 목록이 95% 이상 수집 완료(중복/삭제 이슈 제외).
- Daily 작업: 매일 새벽 수집 시 신규 URL을 정확히 찾아내고, DB에 중복 없이 등록해야 함.
- 대시보드: 작업 생성/중단/삭제 및 진행률 확인이 관리자 권한으로 정상 작동.

---

**동시성 및 확장성 요구사항**

- 요구: 뉴스 주소 수집기(Address Collector)와 뉴스 본문 수집기(Body Collector)는 여러 인스턴스가 동시에 동작할 수 있어야 하며, 고정 개수 대신 수집 대기열(backlog), 수집할 키워드 개수, 시스템 부하(CPU/메모리), 외부 서비스(포털) rate-limit 상황 등을 고려하여 유동적으로 늘리거나 줄일 수 있어야 합니다.
- 설계 권장안:
  - 아키텍처 1 (권장): 메시지 큐 기반 워커 풀(예: RabbitMQ, Redis Streams, Kafka).
    - 주소 수집기는 수집 대상 URL/작업을 큐에 넣고, 복수의 Body Collector(워커)가 큐에서 작업을 소비(consume)해 병렬 처리.
    - 워커는 상태가 없도록(stateless) 설계하여 컨테이너 복제/스케일이 쉬움.
    - 오토스케일은 워커 수를 큐 대기열 길이 또는 외부 메트릭(시스템 부하, 처리 지연)에 따라 조정.
  - 아키텍처 2 (간편): Docker Compose로 고정 레플리카(n) 운영.
    - `docker-compose up --scale worker=N`으로 여러 인스턴스를 띄울 수 있으나, Compose 자체는 동적 오토스케일 기능이 제한적임.
    - 간단한 자동화(스크립트 또는 외부 오케스트레이터)로 `docker-compose` 레플리카 수를 조절 가능.
  - 아키텍처 3 (프로덕션 권장): Kubernetes + HPA/Vertical Pod Autoscaler.
    - HPA를 사용해 CPU/메모리/큐 길이 등으로 자동 스케일링을 적용.

- 운영 고려사항:
  - Backpressure: 큐 길이 임계치 초과 시 신규 작업 수집 속도 제한 또는 일시 중지 로직 필요.
  - Rate-limiting / politeness: 포털 서비스 차단 방지를 위해 호스트별/엔드포인트별 요청 속도 제한 적용.
  - 모니터링: 각 워커의 처리율(URLs/sec), 실패율, 재시도 횟수, 큐 길이, 시스템 리소스 지표를 수집(Prometheus/Grafana 권장).
  - 로그·트레이싱: 실패 URL은 `tb_news_errors`에 저장하고, 분산 트레이싱(예: Jaeger)으로 지연 원인 분석.

- 구현 영향(도커 컴포즈 관련 답변):
  - 네, `docker-compose`로 여러 인스턴스를 띄워 병렬 처리 구현은 가능하지만, 동적 자동 확장(autoscale)은 기본적으로 제공되지 않습니다. 단기/개발 환경에서는 `docker-compose --scale`로 충분할 수 있으나, 운영 환경에서의 동적 스케일링·리소스 조정은 `Kubernetes` 또는 외부 오케스트레이터를 권장합니다. 메시지 큐 기반으로 설계하면 `docker-compose` 환경에서도 워커 수를 손쉽게 늘리거나 줄일 수 있어 운영 편의성이 개선됩니다.

- 수용 기준(예시, 확장성 관련):
  - 시스템은 N개의 워커를 띄워서 초당 M개 이상의 URL을 안정적으로 처리(예: N=5로 M≥50 URLs/sec)해야 함(구체 수치는 향후 성능 테스트로 확정).
  - 워커 수 증감에 따라 처리율이 비례 개선되는지(비용 대비 효율) 모니터링으로 검증.


## 참고(다음 단계—연구/검증)
- 필요 시 다음 항목에 대해 외부 자료(공식 레퍼런스, 산업 블로그, 논문 등)를 조사하여, 각 요구사항의 타당성 근거와 권장 구현 방식을 문서화하겠습니다:
  - 대용량 Backfill 수행 전략(분할·병렬화·속도 조절, politeness).
  - URL 중복 판별 및 정규화(best practices).
  - 스케줄러(예: APScheduler, Airflow)와 단순 cron 기반 배치의 장단점.
  - 관리자 대시보드 UX 패턴(작업 모니터링/제어), 보안 요구사항.

---

Do NOT execute any collection jobs or create tasks; this is a draft PRD addendum. Reply with 'Proceed with research' to allow me to fetch external references and append validated citations to this draft, or reply 'Edit' to request changes to the draft.
