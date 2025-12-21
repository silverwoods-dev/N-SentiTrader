<!-- .github/3fs/process-task-list.md -->

# 목적

이 파일은 에이전트가 사용자의 요청에 따라  
**특정 TASK(TASK-00X)를 실제로 수행할 때 따라야 할 절차**를 정의합니다.

Test First(TDD)와 MCP 도구 사용, Docker 기반 인프라, 그리고 3-File System 흐름을 엄격히 준수합니다.

---

# TASK 수행 지침

- **항상 작은 변경 단위**로 작업합니다.
- 가능하면 **테스트를 먼저 작성하고(Red), 구현(Green) 후 리팩터링**합니다.
- 모든 작업은 `copilot-instructions.md`의 **핵심 운영 원칙**을 최우선으로 따릅니다.
- **Python 환경 관리:** 모든 환경에서 `uv`를 사용합니다. (`pip` 직접 호출 금지)
- **데이터베이스 검증:** PostgreSQL 변경 시 Python 스크립트나 SQL 클라이언트를 통해 정합성을 검증합니다.
- **경로 처리:** `pathlib`과 환경 변수를 사용하여 Docker/로컬 호환성을 유지합니다.

---

# TASK 처리 절차

사용자가 “TASK-00X를 진행해 주세요”라고 요청하면,  
에이전트는 아래 단계를 순서대로 따릅니다.

---

## 1단계: TASK 컨텍스트 파악

1. `docs/tasks/n-sentitrader-tasks.md`에서
   - 해당 TASK의 목적, 상세 작업, 완료 기준(AC)을 읽습니다.
2. 관련 PRD 및 TRD 섹션 확인
   - `docs/prd/n-sentitrader-prd.md` (요구사항)
   - `docs/trd/n-sentitrader-trd.md` (기술명세, 경로 설정 등)
3. 필요 시 `filesystem` MCP로
   - 관련 코드/문서/테스트 파일의 현재 상태를 확인합니다.

---

## 2단계: 현재 코드/인프라 상태 파악

- `filesystem` MCP를 사용해 다음을 확인합니다.
  - `src/` 하위 모듈 존재 여부
  - `tests/` 하위 테스트 파일 존재 여부
  - `docker-compose.yml` 및 컨테이너 실행 상태 (필요 시)
- 필요한 경우 `context7` MCP로
  - Polars / Mecab-ko / PostgreSQL Driver(psycopg2/SQLAlchemy) 최신 문서를 참조합니다.

---

## 3단계: Test First 계획 수립 및 테스트 작성

데이터 파이프라인 및 모델링 작업은 검증이 까다로우므로 **단위 테스트 작성**을 최우선으로 합니다.

1. 새 기능/수정에 대응되는 테스트 파일 선택:
   - 예: 전처리 관련 → `tests/test_preprocessor.py`
   - 예: 학습 로직 → `tests/test_learner.py`
   - 예: DB 스키마 → `tests/test_db_schema.py`
2. 해당 테스트 파일에 **예상 동작을 정의하는 테스트 코드를 먼저 작성**합니다.
   - 예: "Mecab에 '2차전지'를 넣으면 `['2차', '전지']`가 아니라 `['2차전지']`가 나와야 한다."
3. 테스트를 실행하여 **의도적인 실패(Red)** 상태를 확인합니다.

---

## 4단계: 최소 구현 (Green 상태 만들기)

테스트가 실패하는 것을 확인한 뒤,  
최소한의 구현으로 테스트를 통과시키는 코드를 작성합니다.

- 구현 위치 예시:
  - `src/preprocessor.py` (Mecab 로드)
  - `src/learner.py` (Lasso 학습)
  - `src/utils/db.py` (DB 연결)
- **경로 처리 주의:**
  - TRD에 명시된 대로 `pathlib`과 환경 변수(`NS_DATA_PATH`)를 사용하여 Docker와 로컬 환경 모두에서 동작하도록 작성합니다.
- Docker 환경이 필요한 경우:
  - 코드를 작성한 후 `docker-compose up --build` 명령 등을 제안하여 컨테이너 환경에서 실행해봅니다.

---

## 5단계: 데이터 및 모델 동작 검증

데이터베이스나 모델링 결과와 관련된 TASK라면, 아래를 수행합니다.

- **PostgreSQL 검증:**
  - Python 코드(`src/utils/db_check.py` 등)를 작성하여 테이블 생성 여부, 데이터 적재 건수를 확인합니다.
  - SQL DDL이 정상적으로 실행되었는지 로그를 확인합니다.
- **Mecab/Lasso 모델 검증:**
  - 사용자 사전이 올바르게 로드되었는지 확인하는 스크립트 실행.
  - 학습된 Lasso 모델의 계수($\beta$) 중 0이 아닌 단어가 존재하는지 확인.
- **출력물 확인:**
  - `output/` 폴더에 JSON 리포트가 생성되었는지 파일 시스템으로 확인.

---

## 6단계: 리팩터링 및 문서 반영

- 테스트가 Green인 상태에서
  - 중복 제거, 함수 분리, 변수 이름 개선 등 **리팩터링**을 수행합니다.
- 변경 사항을 문서/PRD에 반영해야 하는 경우:
  - `docs/prd/n-sentitrader-prd.md` 업데이트.
  - `docs/trd/n-sentitrader-trd.md` (기술 스택 변경 시) 업데이트.

---

## 7단계: TASK 상태 업데이트 (필수)

**중요**: TASK 작업 중/완료 시 반드시 아래 규칙을 따라야 합니다. 불일치 발생 시 추적 불가능.

- `docs/tasks/n-sentitrader-tasks.md`에서 아래 원칙에 따라 진행 상황을 **즉시** 반영합니다.

  1. **STATUS 라인 업데이트 (필수)**:
     - 작업 시작 시: `NOT_STARTED` → `IN_PROGRESS`
     - 작업 완료 시: `IN_PROGRESS` → `COMPLETED`
     - COMPLETED로 변경할 때는 모든 하위 체크박스가 `[x]`여야 함 (예외 없음)

  2. **상세 작업 내용 체크박스 (필수, 실시간 갱신)**:
     - 각 하위 작업을 완료하는 **즉시** `[ ]` → `[x]`로 변경
     - 미완료 항목은 절대 `[x]` 처리 금지

  3. **완료 기준(Acceptance Criteria) 체크박스 (필수)**:
     - 각 AC 항목이 검증되면 `[ ]` → `[x]`로 변경
     - 모든 AC가 `[x]`가 아니면 STATUS를 COMPLETED로 변경 불가

  4. **Progress Log 갱신 (필수)**:
     - 주요 진행 단계마다 날짜/시간과 함께 기록
     - 특히 **테스트 실패(Red) → 성공(Green)** 과정을 기록하면 좋습니다.

**금지 사항**:
- ❌ STATUS만 COMPLETED로 변경하고 체크박스는 `[ ]` 상태로 남기기
- ❌ Progress Log 없이 COMPLETED 처리
- ❌ 테스트(AC) 통과 확인 없이 완료 처리

예시(완료 시):
```text
## TASK-002: 뉴스 데이터 전처리 모듈 구현
STATUS: COMPLETED
- 상세 작업 내용:
  - [x] Mecab 사용자 사전(user_dic.csv) 생성
  - [x] Mecab 로더 구현 (Docker 경로 호환)
  - [x] 테스트 코드(test_nlp.py) 작성
- 완료 기준:
  - [x] '2차전지'가 하나의 명사로 추출됨
  - [x] pytest 실행 시 test_nlp.py 통과
Progress Log:
  - 2025-12-16 10:00 TASK 시작
  - 2025-12-16 10:15 테스트 작성 후 Red 확인
  - 2025-12-16 10:45 Mecab 로더 구현 및 Green 확인
  - 2025-12-16 11:00 리팩터링 및 완료
```

---

## 8단계: GitHub 작업 (선택)

GitHub MCP를 사용할 수 있다면 다음을 권장합니다.

* 새 브랜치 생성: `feature/TASK-00X-description`
* 커밋 메시지: `feat: implement preprocessing module (TASK-002)`

---

# 요약 규칙

1. **PRD/TRD → TASK → 실행** 순서를 항상 지킵니다.
2. 가능하면 **테스트 먼저 작성(Test First)**합니다.
3. **Docker 환경**을 고려하여 경로(`pathlib`)와 설정(`config.yaml`)을 다룹니다.
4. **TASK 상태 업데이트는 필수이며 실시간으로 수행**합니다:
   - 체크박스는 완료 즉시 갱신
   - STATUS와 체크박스 상태 일치
   - Progress Log 기록
5. TASK 수행 결과는 항상 문서화하여 "명세와 구현의 일치"를 유지합니다.

**에이전트 자가 점검 체크리스트** (TASK 완료 전 필수 확인):
- [ ] 모든 "상세 작업 내용" 체크박스가 `[x]`인가?
- [ ] 모든 "완료 기준" 체크박스가 `[x]`인가?
- [ ] Progress Log에 완료 기록이 있는가?
- [ ] STATUS가 COMPLETED인가?
- [ ] pytest가 Green인가?