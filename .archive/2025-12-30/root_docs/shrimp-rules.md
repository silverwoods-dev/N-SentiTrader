# N-SentiTrader Project — AI Agent Operational Rules (shrimp-rules.md)

이 문서는 N-SentiTrader 프로젝트의 일관성과 안전성, 그리고 **3-File System (3FS)**의 엄격한 준수를 보장하기 위해 정의된 최상위 지침입니다. 에이전트는 모든 작업 시 아래의 내용을 숙지하고 예외 없이 따라야 합니다.

---

## 1. 핵심 운영 원칙 (Core Principles)

### [필수] Sequential Thinking (ST) 기반 사고
- **모든 복잡한 작업은 `sequentialthinking` 도구를 사용하여 단계별로 수행한다.**
- 문제 분석 -> 가설 수립 -> 검증 -> 구현 -> 회고의 과정을 투명하게 기록한다.
- 단순한 코드 수정이라도 영향 범위가 넓다면 반드시 ST를 통해 사고 과정을 공유한다.

### [엄금] 파괴적 작업 금지 (Safety First)
- **파일 삭제(`rm`), 데이터베이스 초기화(`DROP`), 대규모 코드 삭제 등 파괴적인 작업은 원칙적으로 금지한다.**
- 반드시 필요한 경우, ST를 통해 필연성을 증명하고 **사용자의 명시적인 승인**을 얻은 후 실행한다.

### [절차] 3-File System (3FS) 준수
- **명세 우선 (SDD):** 모든 변경은 `PRD` -> `TASK` -> `구현` 순서를 반드시 따른다.
- **테스트 우선 (TDD):** 핵심 로직은 `테스트 작성` -> `실패(Red)` -> `구현` -> `성공(Green)` -> `리팩터링` 순서를 따른다.
- **최소 변경:** 문제의 근본 원인을 해결하되, 불필요한 대규모 리팩터링은 지양한다.

---

## 2. 3FS 단계별 상세 지침

### 1단계: PRD 생성 및 갱신 (`create-prd.md` 지침 준수)
- **경로:** `docs/prd/n-sentitrader-prd.md`
- **지침:** 새로운 기능/요구사항/구조 변경 요청 시, 코드를 수정하기 전 **먼저 PRD를 생성 또는 갱신**한다. PRD는 이 프로젝트의 **최상위 명세(Spec)**이며 코드는 이를 따른다.
- **필수 섹션 구조:**
  1. 개요 (Overview): 한 줄 요약, 배경, 목표 포함
  2. 대상 사용자 및 사용 시나리오: 시스템 관리자 및 퀀트 분석가 관점
  3. 범위 (Scope: In / Out): 명확한 기능적 경계 설정
  4. 데이터 모델 및 스키마 설계: 도메인 분석 및 핵심 엔티티
  5. 시스템 아키텍처 및 파이프라인: 모듈별 상호작용 및 데이터 흐름
  6. 기술 스택 (Tech Stack): Infra, Core, Methodology 정의
  7. 데이터베이스 스키마 (Database Schema): SQL 형식 참조 포함
  8. 테스트 전략 (Test Strategy): Backend(pytest), Frontend(Playwright)
  9. 사고 이력 및 향후 과제 (Incident History & Future Tasks)

### 2단계: TASK 목록 생성 및 갱신 (`generate-tasks.md` 지침 준수)
- **경로:** `docs/tasks/n-sentitrader-tasks.md`
- **지침:** PRD 변경 후, 작업의 **최소 기능 단위(Atomic)**를 정의한다. 
- **필수 구성 요소 및 템플릿:**
  - **ID:** `TASK-001`, `TASK-002` 순차적 부여
  - **STATUS:** PENDING, IN_PROGRESS, COMPLETED (체크박스와 일치 필수)
  - **타입 & 섹션:** chore, fix, feature / 관련 PRD 섹션 명시
  - **우선순위 & 난이도:** P0~P2 / S, M, L
  - **목적 & 상세 내용:** 작업의 이유와 구체적인 체크리스트(`[ ]`)
  - **변경 예상 파일:** 수정 또는 생성될 모듈 경로
  - **완료 기준 (AC):** 검증 가능한 구체적 수치 또는 통과 조건
  - **Progress Log:** 타임스탬프와 함께 작업 이력 기록

### 3단계: 작업 실행 및 실시간 보고 (`process-task-list.md` 지침 준수)
- 작업을 시작할 때 해당 TASK의 STATUS를 `IN_PROGRESS`로 변경한다.
- **실시간 갱신:** 하위 작업 완료 즉시 체크박스(`[x]`)를 업데이트한다.
- **결과 검증:** `verify_task` 도구 사용 전, 수동으로 `pytest` 또는 `Playwright` 테스트를 실행하여 완료 기준을 확인한다.
- **완료 처리:** 모든 체크박스가 채워졌을 때 STATUS를 `COMPLETED`로 변경하고 마감 로그를 남긴다.

---

## 3. 기술 컨벤션 및 환경 규칙

### 환경 관리 (uv & Docker)
- **패키지 관리:** 모든 환경에서 `uv`를 사용한다. `pip` 직접 사용을 엄금한다.
- **서비스 운영:** 모든 실행 서비스는 Docker 컨테이너화하며, `restart: always` 정책을 유지한다.
- **경로 및 설정:** 하드코딩 대신 `pathlib`을 사용하고, 설정은 `config.yaml` 또는 `.env`로 관리한다.

### UI/UX 디자인 에스테틱
- **Premium Design:** Bento Grid, Tailwind CSS, HTMX, Lucide Icons를 필수 활용한다.
- **Aesthetics:** 고급스러운 컬러 팔레트와 부드러운 애니메이션을 적용하여 전문가용 수준의 UX를 제공한다.

---

## 4. 금지 사항 및 자가 점검 (Prohibitions)

- ❌ **PRD/TASK 업데이트 없는 코드 직접 수정 (가장 심각한 위반)**
- ❌ 테스트(AC) 통과 확인 없이 TASK 완료 처리
- ❌ STATUS는 COMPLETED나 체크박스는 `[ ]`인 불일치 상태
- ❌ Progress Log 없는 TASK 마감
- ❌ 단순 MVP 수준의 평범한 UI 제작
