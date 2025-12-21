<!-- .github/copilot-instructions.md — Repository-wide Copilot Agent guidelines (concise) -->

# Copilot Instructions — Repository Guidelines

본 문서는 에이전트가 이 리포지토리에서 일관되고 안전한 방식으로 협업하기 위한 **최상위 운영 원칙**을 정의합니다. 모든 작업은 이 가이드라인을 최우선으로 따릅니다.

---

## 1) 핵심 운영 원칙 (Core Principles)

### [필수] Sequential Thinking (ST) 기반 사고
- **모든 복잡한 작업은 `sequentialthinking` 도구를 사용하여 단계별로 수행합니다.**
- 문제 분석 -> 가설 수립 -> 검증 -> 구현 -> 회고의 과정을 투명하게 기록합니다.
- 단순한 코드 수정이라도 영향 범위가 넓다면 반드시 ST를 통해 사고 과정을 공유합니다.

### [엄금] 파괴적 작업 금지 (Safety First)
- **파일 삭제(`rm`), 데이터베이스 초기화(`DROP`), 대규모 코드 삭제 등 파괴적인 작업은 원칙적으로 금지합니다.**
- 반드시 필요한 경우:
  1. ST를 통해 삭제의 필연성과 대안 부재를 증명합니다.
  2. 예상되는 부작용과 복구 계획을 수립합니다.
  3. **사용자의 명시적인 승인**을 얻은 후 실행합니다.

### [절차] 3-File System (3FS) 준수
- **명세 우선(SDD):** 모든 변경은 PRD(`docs/prd/`) -> TASK(`docs/tasks/`) -> 구현 순서를 따릅니다.
- **테스트 우선(TDD):** 핵심 로직은 테스트 작성 -> 실패 -> 구현 -> 리팩터링 순서를 따릅니다.
- **최소 변경:** 문제의 근본 원인을 해결하되, 불필요한 대규모 리팩터링은 지양합니다.

---

## 2) 기술 및 환경 컨벤션

### 환경 관리 (uv & Docker)
- **패키지 관리:** 모든 환경(로컬/Docker)에서 `uv`를 사용합니다. `pip` 직접 사용을 금지합니다.
- **서비스 운영:** 모든 실행 서비스는 Docker 컨테이너화하며, `restart: always` 정책을 적용합니다.
- **데이터 보존:** DB 데이터는 호스트 권한 충돌 방지를 위해 **Named Volume**을 사용합니다.

### 구현 및 커뮤니케이션
- **언어:** 문서/주석은 **한국어**, 코드 식별자는 **영어**를 사용합니다.
- **사용자 소통:** 모든 질문, 확인, 보고는 한국어로 명확하고 간결하게 수행합니다.
- **최신성 유지:** 구현 전 `context7`을 사용하여 라이브러리의 최신 API와 Best Practice를 확인합니다.

---

## 3) 3FS 실행 매뉴얼 (참고 원본)
상세한 단계별 절차는 아래 문서를 따릅니다.
- PRD 생성/갱신: [.github/3fs/create-prd.md](./3fs/create-prd.md)
- TASK 생성/갱신: [.github/3fs/generate-tasks.md](./3fs/generate-tasks.md)
- TASK 수행 절차: [.github/3fs/process-task-list.md](./3fs/process-task-list.md)

---

## 4) 결론
이 문서는 리포지토리의 '헌법'입니다. 이 원칙을 준수함으로써 명세 기반의 안전하고 재현 가능한 개발 흐름을 유지합니다.