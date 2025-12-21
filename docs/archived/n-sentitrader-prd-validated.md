# N-SentiTrader — Validated Requirements (Draft)

Status: DRAFT — Research-backed validation of `n-sentitrader-prd.md`. Do NOT convert to tasks; await user confirmation.

## 목적
- 본 문서는 기존 PRD 요구사항을 외부 권위 자료(문서·가이드·베스트프랙티스)에 근거해 검증하고, 누락·선결조건·충돌을 식별하여 요구사항을 정교화한다.

## 가정(Assumptions)
- 배포 환경은 초기에는 Docker Compose, 장기적으로는 Kubernetes로 마이그레이션 가능.
- 배치 주기는 일간(Daily) 기준이며, Backfill 작업은 별도의 일괄 작업으로 취급.
- 핵심 NLP 도구는 MeCab(한국어는 mecab-ko-dic)이며, 반드시 런타임에 사용할 사전(.dic)과 mecab 바이너리를 컨테이너에 포함해야 함(참조: MeCab 공식 설치 가이드).

## 참고/출처
- 스케줄링: Apache Airflow (배치·백필 중심 워크플로우) — https://airflow.apache.org/docs/
- 경량 스케줄러: APScheduler (단일 프로세스/간단 cron-style 스케줄) — https://apscheduler.readthedocs.io/
- 메시지 브로커: RabbitMQ 문서(브로커 운영/모니터링) — https://www.rabbitmq.com/docs
- 오토스케일링: Kubernetes HPA (정책·안정화·custom-metrics) — https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/
- 크롤링 윤리 및 robots.txt 가이드: Google Search Central — https://developers.google.com/search/docs/advanced/robots/intro
- NLP(MeCab): MeCab 공식 페이지(사전 설치·user-dic 빌드) — https://taku910.github.io/mecab/
- 모니터링: Prometheus + Grafana — https://prometheus.io/docs/, https://grafana.com/docs/

(참고 링크는 요구사항 본문 각 항목에서 재인용)

## 주요 검증 결과 요약
1. MeCab 관련
   - 요구사항: 컨테이너에서 MeCab을 바로 사용 가능해야 함.
   - 검증/권장: MeCab 본체와 시스템 사전(또는 mecab-ko-dic) 및 사용자 사전(`user_dic.csv`)을 이미지 빌드 시 컴파일하거나, 운영시점에 마운트 가능한 사전 아티팩트를 제공해야 함(참조: MeCab 설치·사전 빌드 절차). 런타임 에러(‘cannot find mecabrc’ 등)는 이미지에 사전/설정 누락에서 기인.
   - 요구사항 보완: `base-mecab` 베이스이미지 또는 Dockerfile에서 `mecab`, `mecab-ipadic/mecab-ko-dic` 설치 단계 포함. 사용자 사전은 `mecab-dict-index`로 빌드한 `.dic` 결과물을 CI 아티팩트로 관리하고, 컨테이너는 이를 `/var/lib/mecab/dic`로 마운트하거나 복사.

2. 스케줄링·백필(Backfill) vs Daily semantics
   - 검증: Airflow는 복잡한 배치/백필/의존성 DAG 관리에 적합(참조: Airflow docs). APScheduler는 단일 프로세스 내 경량 스케줄링(예: Daily trigger) 용도에 적합.
   - 권장 분리: 장기 보존과 복잡한 종속성·백필(재실행·태스크 종속)이 필요하면 Airflow를 채택; 초기 경량 운영(단일 서버, 단순 Cron-like 일일 트리거)은 APScheduler로 시작하되, 백필은 별도 배치(또는 Airflow로 전환)로 설계.
   - Backfill→Daily 충돌 처리 권고안: PRD에서 제안한 대로 Backfill이 새 Daily 항목을 "즉시 등록(auto-add)"하되, Backfill 진행 중에는 Daily 스케줄러가 해당 항목에 대해 중복 실행하지 않도록 `in_backfill` 상태 플래그 또는 `run_daily_during_backfill` 옵션을 사용해 제어.

3. 수집기(Collector) 확장성·동시성
   - 검증: 단일 프로세스 크롤러는 확장 한계가 명확. 프로덕션급 확장에는 메시지 브로커(예: RabbitMQ, Redis Streams, Kafka) + 워커 풀 패턴 권장(참조: RabbitMQ docs, Kafka docs).
   - 권장: 수집 요청을 큐에 넣고 워커가 Pull/ack 방식으로 처리. 큐 길이, 처리 지연, 실패율을 모니터링 지표로 설정하여 오토스케일링(예: K8s HPA on custom metric `queue_length`)을 적용.
   - 동시성 요구사항 상세: Collector는 동시 N 인스턴스에서 동작 가능해야 하며, 동일 뉴스에 대한 중복수집을 피하기 위해 원문 해시 기반의 전역 중복 검사(DB 레벨 UNIQUE 또는 distributed lock)를 적용.

4. 데이터베이스 연결 및 구성
   - 검증: 컨테이너 내부에서 `localhost`로 Postgres를 참조하면 안 됨 — Compose 서비스명(host) 또는 클러스터 DNS 사용 권장.
   - 권장: 환경변수 `DB_HOST`는 Compose 서비스명(예: `db`) 또는 K8s 서비스 이름으로 설정. 연결 풀러(예: `psycopg2` + `sqlalchemy` pool, 또는 `pgbouncer`) 사용 권장. 마이그레이션(DDL)은 별도 관리(예: Alembic)로 표준화.

5. 크롤링 폴리시 및 법적/윤리적 고려
   - 검증: robots.txt 준수, 적절한 User-Agent 표기, 요청률 제한과 백오프 필요(참조: Google robots guide, scraping best practices).
   - 요구사항 보완: 각 타깃 도메인별 `crawl_delay` 정책 적용, 실패 시 exponential backoff, IP 차단 방지 로직, 저작권·서비스 약관 검토 프로세스 포함.

6. 모니터링·알림
   - 권장 스택: Prometheus 수집 + Grafana 대시보드(시스템 지표, 큐 길이, 작업 실패율, MeCab 오류율, 전체 파이프라인 지연) — 참조 Prometheus/Grafana 문서.
   - 알림: Alertmanager/Grafana Alerts로 장애·에러 비율·백필 실패·큐 과부하 알림 전송(Slack/Email).

7. 관측 가능한 지표(권장)
   - Collector: 요청 수, 성공/실패, 평균 처리시간, 큐 대기시간
   - Tokenizer/MeCab: 초기화 실패 수, 처리율(문서/s), 평균 처리시간
   - Learner: 학습 작업 소요시간, 모델 버전별 성능(RMSE/Accuracy), 학습 데이터 크기
   - Predictor: 예측 지연, 예측 성공률, 배치별 처리건수

8. 데이터 일관성·아이덴티티
   - 권장: 뉴스 원문 해시(sha256)로 중복 제거, `tb_news_mapping`은 뉴스ID→종목코드 매핑(다대다)을 명확히 하여 재수집시 동일 매핑 재활용.
   - 정합성 검사: 매일 리포트에서 `news_count` vs `mapped_count` 불일치 시 경고 발생.

9. Backfill 동작 및 우선순위(구체안)
   - Backfill 절차:
     1) Backfill은 별도 Job으로 인식(Backfill Job ID 발급).
     2) Backfill 시작 시 기존 Daily 대상 자동 등록(요구대로 `auto_activate_daily=true`), 단 `in_backfill` 플래그가 켜져 있는 동안 Daily 스케줄러는 해당 대상 실행을 보류.
     3) Backfill 완료 후 `in_backfill` 제거 및 Daily 스케줄러 정상 복귀.
   - 검증: 이 설계는 중복 처리 방지(중복 Daily실행)와 즉시 활성화 요구 모두를 만족하도록 타협함.

10. 요구사항 간 선결조건(우선순위)
   - (A) 인프라 기본: DB, Broker, Artifact Storage(사전 .dic), 모니터링(기본 Prometheus) 가용성 확보 — 선행작업.
   - (B) MeCab 사전 빌드·배포 파이프라인 확보 — MeCab 기반 모듈들의 정상 동작을 위해 필수.
   - (C) Collector 큐 통합 및 중복 감지(뉴스 해시) 구현 — 데이터 중복·정합성 방지.
   - (D) Daily 스케줄러 및 Backfill 조정 로직: `in_backfill` 상태 기법 적용.

11. 충돌 사례 및 권고 처리방식
   - 충돌: Backfill이 "즉시 등록"하면서 동시에 Daily 스케줄러가 같은 항목을 처리하려는 중복 실행 문제.
     - 권고 처리: Backfill 모드 우선(Backfill은 데이터를 덮어쓸 수 있으므로 Backfill 중에는 Daily를 보류). 사용자가 다르게 원하면 `run_daily_during_backfill=true` 옵션으로 강제 실행 허용.
   - 충돌: MeCab 사전 업데이트와 런타임 토크나이저 버전 불일치.
     - 권고 처리: 사용자 사전 빌드는 CI에서 `.dic`로 컴파일하고, 버전 태그(예: `user-dic:v2025-12-18`)를 붙여서 배포. 런타임은 명시된 버전만 사용.

12. 수용 기준(Acceptance Criteria)
   - Daily 런타임: 모든 Daily pipeline은 08:30 이전 종료(지표로 검증).
   - 정확도: 예측 방향성(상승/하락) 55% 이상(Dev baseline), 주간 리포트의 모델 성능 지표 제공.
   - 신뢰성: MeCab 초기화 오류 0건(주간), Collector 실패율 < 2%.
   - 가용성: 전체 서비스 가동률 99% (월간 기준).

13. 구현 권장 스택(요약)
   - Collector: Python + requests/Playwright(선택) → 메시지 브로커(권장 RabbitMQ/Redis Streams)
   - Tokenizer: MeCab(mecab-ko-dic) packaged image or base-mecab image
   - Scheduler: 초기 APScheduler for Daily lightweight, Airflow for complex backfill / DAGs
   - Storage: Postgres 15+, migrations via Alembic
   - Monitoring: Prometheus + Grafana + Alertmanager
   - Container orchestration: Start with Docker Compose for dev, Kubernetes for prod with HPA on queue_length/custom metrics

14. 추가 권장사항(운영·보안)
   - DB credentials: Vault or sealed secrets, 환경변수(임시) 대신 비밀관리 권장
   - 크롤러 User-Agent 식별 및 contact email 표기
   - 법적: 뉴스 사용 계약·저작권 검토 문서화

---

## 파일 위치 및 다음 단계
- 초안 저장: [docs/prd/n-sentitrader-prd-validated.md](docs/prd/n-sentitrader-prd-validated.md)
- 다음(사용자 승인 필요): 요구사항 반영(원본 PRD 덮어쓰기) 또는 항목별 수정 지시.


---

작성자 노트: 위 권장사항은 수집된 공식 문서(링크 포함)를 기반으로 하였고, 운영환경(현재 저장소)에서 관찰된 이슈(MeCab 초기화, DB host 사용 등)를 반영해 우선순위와 선결조건을 정했습니다. 충돌 처리 방식 중 선택을 원하시면 어느 정책을 우선 적용할지 알려주세요.
