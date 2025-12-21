---
description: N-SentiTrader 프로젝트의 3-File System (3FS) 작업 프로세스
---

# N-SentiTrader 3FS 작업 워크플로우

이 워크플로우는 요구사항 분석부터 최종 검증까지 **PRD -> TASK -> 구현**의 3단계를 엄격히 수행하도록 보장합니다.

## STEP 1: 요구사항 분석 및 PRD 업데이트
**지침서: `create-prd.md`**
// turbo
1. 사용자의 요청(기능/요구사항/구조 변경) 확인 시 코드를 바로 수정하지 않습니다.
2. `docs/prd/n-sentitrader-prd.md`를 열고 명세를 최신화합니다.
3. **필수 포함 항목:** 개요, 사용자 시나리오, 범위(In/Out), 데이터 모델, 아키텍처, 기술 스택, DB 스키마, 테스트 전략, 향후 과제.
4. 모든 섹션에 "한 줄 요약" 및 "목표"가 명확히 기재되었는지 확인합니다.

## STEP 2: 태스크 목록 생성 및 동기화
**지침서: `generate-tasks.md`**
// turbo
1. PRD 변경 완료 후, `docs/tasks/n-sentitrader-tasks.md`를 업데이트합니다.
2. **TASK 정의 원칙:**
   - 최소 기능 단위(Atomic)로 분해
   - `TASK-00X` 형식의 ID 순차 부여
   - 관련 PRD 섹션, 우선순위, 난이도, 변경 예정 파일 명시
   - 구체적인 완료 기준(Verification Criteria) 설정 (예: 스크린샷 확인, 특정 테스트 통과)
3. `shrimp-task-manager`의 `split_tasks` 도구를 사용하여 시스템 태스크를 동기화합니다.

## STEP 3: 태스크 실행 및 실시간 보고
**지침서: `process-task-list.md`**
// turbo
1. 실행할 TASK를 선택하고 `execute_task` 도구를 통해 가이드를 받습니다.
2. 작업 시작 시 STATUS를 `IN_PROGRESS`로 변경합니다.
3. **구현 프로세스:**
   - **Test First:** 로직 구현 전 테스트 코드를 먼저 작성합니다.
   - **실시간 갱신:** 하위 단계 완료 시 TASK 파일의 `[ ]`를 즉시 `[x]`로 업데이트합니다.
   - **사고 기록:** 의사결정 및 Red/Green 과정을 `Progress Log`에 남깁니다.

## STEP 4: 검증 및 마감
// turbo
1. 모든 완료 기준(AC)에 대해 `pytest` 등을 실행하여 수동 검증을 완료합니다.
2. `verify_task` 도구로 최종 점수와 요약을 제출합니다.
3. TASK 파일의 STATUS를 `COMPLETED`로 변경하고 마감 로그를 기록합니다.

## STEP 5: 형상관리 (Git Commit & Push)
**지침: AngularJS Commit Convention 준수**
// turbo
1. 테스트가 완료되고 기능 구현이 확정되면 형상관리 절차를 진행합니다.
2. 변경된 파일들을 스테이징합니다: `git add .`
3. **표준 커밋 메시지 형식**에 맞춰 작성합니다:
   - **형식:** `<type>: <description> (TASK-00X)`
   - **Type 종류:**
     - `feat`: 새로운 기능 추가
     - `fix`: 버그 수정
     - `docs`: 문서 수정 (PRD, TASK 등)
     - `style`: 코드 포맷팅, 세미콜론 누락 등 (코드 변경 없음)
     - `refactor`: 코드 리팩토링
     - `test`: 테스트 코드 추가 및 수정
     - `chore`: 빌드 업무, 패키지 매니저 설정 등
   - **예시:** `feat: implement daily target deletion api (TASK-017)`
4. 원격 저장소에 푸시합니다: `git push origin [branch_name]`

## 주의사항
핵심 준수 사항
- **3FS 일관성:** 문서와 구현이 단 1%라도 다를 경우, 구현이 아닌 문서를 먼저 수정하십시오.
- **환경 일관성:** 모든 코드는 `uv` 및 `Docker` 환경에서 검증되어야 합니다.
- **디자인 품질:** UI 작업 시 프리미엄 디자인 원칙(`shrimp-rules.md`)을 상시 참조하십시오.
