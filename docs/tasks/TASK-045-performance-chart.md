## TASK-045: Performance Trend 차트 개선 (Performance Trend Chart Enhancement)
STATUS: COMPLETED

- 타입: feature / UI-UX
- 관련 PRD 섹션: "9.2 Performance Trend 차트 개선 요구사항"
- 우선순위: P1
- 예상 난이도: M
- 목적:
  - Quant Hub 대시보드의 Performance Trend 차트에서 발생하는 X축 날짜 중복 문제를 해결하고, 시각적 정보를 보강하여 사용자 경험을 개선합니다.

- 상세 작업 내용:
  - [x] **[Backend] Time Scale 적용 및 데이터 집계:**
    - [x] 같은 날짜의 여러 예측이 있을 경우 최신 값 (MAX(created_at)) 선택
    - [x] 데이터 구조를 `{x: '2025-10-20', y: 0.45}` 형식으로 변경
    - [x] `data_helpers.py`에 날짜별 집계 함수 추가
  
  - [x] **[Frontend] Chart.js Time Scale 적용:**
    - [x] `type: 'time'` 설정으로 X축 변경
    - [x] `spanGaps` 옵션으로 주말/공휴일 갭 처리
    - [x] 날짜 포맷 설정 (`MMM DD` 형식)
  
  - [x] **[Frontend] Annotation 플러그인 활용:**
    - [x] Y=0 기준선 추가 (Break-even Line)
    - [x] 평균 Alpha 선 추가 (Average Performance Line)
    - [x] 라벨 및 스타일링 적용
  
  - [x] **[Frontend] 거래일/휴일 시각적 구분:**
    - [x] `actual_alpha = NULL`인 경우 Point Style 변경 (삼각형)
    - [x] 또는 배경 영역 표시 (Box Annotation)
  
  - [x] **[Frontend] 동적 색상 및 스타일링:**
    - [x] Alpha 값에 따른 동적 색상 (양수: 초록, 음수: 빨강)
    - [x] Tooltip 개선 (날짜, 예측 점수, 실제 Alpha, 정확도 표시)
  
  - [x] **[Frontend] 이중 축 스케일 제거:**
    - [x] Alpha 값에 10배 곱하는 로직 제거
    - [x] Y축 단위를 실제 백분율(%)로 표시

- 변경 예상 파일/모듈:
  - `src/dashboard/data_helpers.py` (데이터 집계 로직)
  - `src/dashboard/templates/validator.html` (Chart.js 설정)
  - `src/dashboard/static/js/performance-chart.js` (신규 또는 인라인 스크립트)

- 완료 기준 (Acceptance Criteria):
  - [x] X축에 날짜 중복이 없이 깔끔하게 표시됨
  - [x] Y=0 기준선과 평균선이 표시됨
  - [x] 주말/공휴일이 시각적으로 구분됨
  - [x] Tooltip에 상세 정보가 표시됨
  - [x] 실제 Alpha 값이 정확하게 표시됨 (10배 곱하기 제거)

- 기술적 근거:
  - Chart.js Time Scale: https://www.chartjs.org/docs/latest/axes/cartesian/time.html
  - Chart.js Annotation Plugin: https://www.chartjs.org/chartjs-plugin-annotation/

Progress Log:
  - 2025-12-21 15:50: PRD 9.2 섹션 기반으로 TASK-045 수립.
  - 2025-12-21 15:55: Chart.js Annotation 플러그인 적용, 동적 색상, Tooltip 개선 완료.
  - 2025-12-21 15:56: 대시보드 재시작 및 기능 검증 완료.
