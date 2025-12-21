<!-- .github/3fs/generate-tasks.md -->

# 목적

이 파일은 에이전트가 **PRD(n-sentitrader-prd.md) 내용을 기반으로 구현 TASK 목록을 생성/갱신**할 때  
따라야 할 규칙을 정의합니다.

TASK 목록은 아래 파일에 작성합니다.

- `docs/tasks/n-sentitrader-tasks.md`

---

# TASK 기본 형식

각 TASK 항목은 아래 형식을 따릅니다.

```text
## TASK-00X: 한 줄 설명 (예: PostgreSQL 스키마 초기화 및 Docker 연동)
STATUS: NOT_STARTED  # NOT_STARTED | IN_PROGRESS | COMPLETED

- 타입: feature | refactor | bugfix | chore | doc | test
- 관련 PRD 섹션: (예: "4. 데이터 모델 및 스키마 설계")
- 우선순위: P0(필수) | P1(중요) | P2(권장)
- 예상 난이도: S | M | L
- 관련 MCP 도구:
  - 예: filesystem, context7 (최신 라이브러리 참조)
- 목적:
  - 이 TASK를 수행하면 어떤 가치/결과가 나오는지
- 상세 작업 내용:
  - [ ] 구체적 작업 1 (예: DDL 작성)
  - [ ] 구체적 작업 2 (예: Docker Compose 수정)
  - ...
- 변경 예상 파일/모듈:
  - 예: `src/db/schema.sql`, `docker-compose.yml`
- 완료 기준(Acceptance Criteria):
  - [ ] 테스트/검증 기준 1
  - [ ] 테스트/검증 기준 2
Progress Log:
  - (예시) 2025-12-16 초기 작성
```

---

# TASK 생성 절차

에이전트가 TASK를 생성하거나 갱신할 때는 아래 순서를 따릅니다.

## 1. PRD 및 TRD 변경사항 확인

* `docs/prd/n-sentitrader-prd.md` 및 `docs/trd/n-sentitrader-trd.md` 파일에서
  * 새로 추가된 데이터 파이프라인 요구사항
  * 변경된 로직(예: 시간 감쇠 공식 변경)
  * 인프라 설정(Docker/DB) 변경 사항
    을 먼저 확인합니다.

## 2. 기능을 TASK 단위로 분해

* 한 TASK는 **한 번의 PR** 혹은 **단일 모듈 구현** 단위(S/M)를 목표로 합니다.
* 패키지 추가가 필요한 경우, `pip` 대신 `uv add`를 사용하는 작업을 상세 작업 내용에 명시합니다.
* 큰 기능(예: 학습 시스템 구축)은 여러 TASK로 분할합니다.
  * 예: 전처리 모듈 구현 / Lasso 학습 로직 구현 / 사전 업데이트 로직 구현

## 3. 시스템 레이어 관점에서 분류 태그 부여

TASK 설명 또는 목적에 다음과 같은 레이어 태그를 언급하여 작업의 성격을 명확히 합니다.

* Infra (Docker, DB, Config)
* Collector (Data Pipeline)
* Preprocessor (NLP, Mecab)
* Learner (Model, Lasso)
* Predictor (Ensemble, Report)
* Test (TDD, Backtesting)

예:
* “Infra / DB”: 초기 테이블 생성 스크립트 작성
* “Preprocessor / Test”: Mecab 사용자 사전 로딩 테스트

## 4. MCP 사용 계획을 TASK에 명시

각 TASK마다 필요한 MCP 도구를 적습니다.

* `filesystem`:
  * 리포지토리 내 파일 구조 확인 및 `src/`, `tests/` 코드 생성 시 사용
* `context7`:
  * Polars, Scikit-learn, Mecab-ko 등 최신 라이브러리 문법 확인 시 사용
  * **주의:** PostgreSQL 쿼리 문법 확인 등에도 활용 가능

## 5. Test First (TDD) 반영

* 데이터 분석 로직이나 모델링 코드는 결과 검증이 어렵기 때문에 **단위 테스트 작성을 우선**합니다.
* 예:

```text
- 상세 작업 내용:
  - [ ] `tests/test_preprocessor.py`에 Mecab 사용자 사전 로드 테스트 작성
  - [ ] 테스트 실패(Red) 확인 (사전 파일 미존재 등)
  - [ ] `src/preprocessor.py` 구현 및 사전 파일 생성으로 테스트 통과(Green)
```

## 6. 완료 기준(Acceptance Criteria) 구체화

* 단순히 “구현한다”가 아니라, **입출력 데이터의 형태**와 **검증 방법**을 명시합니다.
* 예:

```text
- 완료 기준 (Acceptance Criteria):
  - [ ] Docker 컨테이너 실행 시 PostgreSQL DB가 정상적으로 구동되어야 한다.
  - [ ] `tb_daily_price` 테이블에 KOSPI 지수 데이터가 적재되어야 한다.
  - [ ] `pytest tests/` 수행 시 모든 테스트가 통과해야 한다.
```

---

# 주요 모듈별 TASK 템플릿

프로젝트 특성(데이터 파이프라인, 모델링)에 맞춘 템플릿입니다.

### [템플릿 1] 인프라 및 DB 초기화

```text
## TASK-0X1: Docker 및 PostgreSQL 초기 환경 구축

- 타입: chore
- 관련 PRD/TRD 섹션: "5. 시스템 아키텍처", "4. 데이터 모델"
- 우선순위: P0
- 예상 난이도: M
- 관련 MCP 도구: filesystem

- 목적:
  - 개발 및 배포를 위한 Docker 컨테이너 환경을 구성하고, DB 스키마를 초기화한다.

- 상세 작업 내용:
  - [ ] `docker-compose.yml` 작성 (App, DB 서비스 정의)
  - [ ] `config/init.sql` 작성 (TRD에 정의된 테이블 DDL)
  - [ ] `Dockerfile` 작성 (Mecab, Python 라이브러리 설치)

- 변경 예상 파일/모듈:
  - `docker-compose.yml`, `Dockerfile`, `config/init.sql`

- 완료 기준:
  - [ ] `docker-compose up` 실행 시 에러 없이 컨테이너 2개가 실행된다.
  - [ ] DB 컨테이너 접속 시 `nsentitrader` DB와 테이블들이 생성되어 있다.
```

### [템플릿 2] 데이터 파이프라인 (Collector/Preprocessor)

```text
## TASK-0X2: 뉴스 데이터 전처리 모듈 구현 (Mecab + UserDic)

- 타입: feature
- 관련 PRD 섹션: "3.2 모듈 B: 학습 및 감성사전 구축기"
- 우선순위: P0
- 예상 난이도: M
- 관련 MCP 도구: context7 (Mecab-ko 최신 사용법)

- 목적:
  - 뉴스 본문에서 명사를 추출하고, '2차전지' 같은 신조어를 처리한다.

- 상세 작업 내용:
  - [ ] `tests/test_nlp.py` 작성 (사용자 사전 적용 여부 테스트)
  - [ ] `data/user_dic.csv` 파일 생성 및 키워드 등록
  - [ ] `src/preprocessor.py` 구현 (Mecab 로드 및 명사 추출 로직)

- 변경 예상 파일/모듈:
  - `src/preprocessor.py`, `data/user_dic.csv`

- 완료 기준:
  - [ ] '2차전지' 입력 시 ['2차전지']로 출력되어야 함 (['2차', '전지'] 아님).
  - [ ] Polars DataFrame의 map_elements를 통해 고속 처리가 가능해야 함.
```

### [템플릿 3] 모델링 및 학습 (Learner)

```text
## TASK-0X3: Lasso 기반 감성사전 학습 로직 구현

- 타입: feature
- 관련 PRD 섹션: "3.2 모듈 B - 메인 모델 학습"
- 우선순위: P0
- 예상 난이도: L
- 관련 MCP 도구: context7 (Scikit-learn Lasso 예제)

- 목적:
  - 과거 뉴스 데이터와 수익률을 매핑하여 단어별 감성 점수($\beta$)를 산출한다.

- 상세 작업 내용:
  - [ ] 학습 데이터 로더 구현 (DB -> Polars -> Scikit-learn)
  - [ ] Lasso 모델 파이프라인 구축 (Vectorizer -> Model)
  - [ ] 학습 결과(계수)를 `tb_sentiment_dict`에 저장하는 로직

- 변경 예상 파일/모듈:
  - `src/learner.py`, `src/utils/db.py`

- 완료 기준:
  - [ ] 더미 데이터로 학습 시도 시, 에러 없이 `tb_sentiment_dict`에 데이터가 INSERT 되어야 한다.
  - [ ] 계수가 0인 단어는 사전에 포함되지 않아야 한다.
```

---

# 에이전트 작업 규칙 요약

1. PRD 및 TRD 변경 후에는 **반드시 이 파일 규칙에 따라 TASK 목록을 최신 상태로 유지**합니다.
2. TASK ID는 `TASK-001`, `TASK-002` 순으로 증가시킵니다.
3. 사용자가 “TASK-00X부터 진행해 주세요”라고 하면,
   * `.github/3fs/process-task-list.md` 규칙에 따라 해당 TASK를 수행합니다.
4. **Test First(TDD)**를 적극 활용하여 데이터 파이프라인의 안정성을 확보합니다.
5. **Sequential Thinking 필수 사용:** TASK 분해 및 우선순위 설정 시 사고 과정을 기록합니다.
6. **파괴적 작업 금지:** 기존 TASK를 삭제하거나 대폭 수정할 경우 승인을 요청합니다.