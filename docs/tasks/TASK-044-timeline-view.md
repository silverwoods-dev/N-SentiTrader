## TASK-044: Validator 대시보드 Timeline View 구현 (Validator Timeline View Implementation)
STATUS: PENDING

- 타입: feature / UI-UX
- 관련 PRD 섹션: "12. Validator 대시보드 고도화", "12.2 Timeline View"
- 우선순위: P0
- 예상 난이도: L
- 목적:
  - 감성 사전 단어의 시간에 따른 beta 값 변화를 시각화하여 모델 업데이트 추적 및 시장 키워드 트렌드 분석을 지원합니다.
  - 단어 사전의 진화를 추적하여 모델의 학습 과정과 시장 변화를 직관적으로 이해할 수 있도록 합니다.

- 상세 작업 내용:
  - [ ] **[Backend] 시계열 데이터 API 구현:**
    - [ ] `GET /api/validator/timeline/words`: 주요 단어(Top 20)의 시간별 beta 값 조회
    - [ ] `GET /api/validator/timeline/vanguard`: 최근 7일 내 신규 진입 단어 조회
    - [ ] `GET /api/validator/timeline/derelict`: 최근 7일 내 퇴출된 단어 조회
    - [ ] 날짜 범위 파라미터 지원 (기본: 최근 30일)
  
  - [ ] **[Frontend] 탭 네비게이션 구조 구현:**
    - [ ] Validator 페이지에 3단 탭 추가: Current / Timeline / Performance
    - [ ] HTMX 기반 탭 전환 (페이지 새로고침 없이 콘텐츠 교체)
    - [ ] 탭 상태 URL 파라미터로 유지 (북마크 가능)
  
  - [ ] **[Frontend] 단어 가중치 히트맵 구현:**
    - [ ] Chart.js Matrix Plugin 활용
    - [ ] X축: 시간(일 단위), Y축: 주요 단어(Top 20)
    - [ ] 색상 농도: beta 값의 강도 (긍정: Indigo, 부정: Crimson)
    - [ ] 호버 시 상세 정보 표시 (날짜, 단어, beta 값)
  
  - [ ] **[Frontend] 신규/퇴출 단어 리스트:**
    - [ ] Vanguard (신규 진입) 섹션: 최근 7일 내 새로 등장한 단어
    - [ ] Derelict (퇴출) 섹션: beta 값이 0으로 수렴한 단어
    - [ ] 각 단어에 진입/퇴출 날짜 표시
    - [ ] 트렌드 아이콘 적용 (↑ 신규, ↓ 퇴출)
  
  - [ ] **[Frontend] 이벤트 마커 구현:**
    - [ ] 뉴스 발생량이 평소 대비 2배 이상인 지점 표시
    - [ ] 주가 변동성이 컸던 지점 표시
    - [ ] 수직선 + 라벨로 시각화
    - [ ] 클릭 시 해당 날짜의 주요 뉴스 헤드라인 표시
  
  - [ ] **[Database] 데이터 집계 최적화:**
    - [ ] Materialized View 또는 캐싱 레이어 검토
    - [ ] 히트맵 데이터 사전 집계 (일 단위)
    - [ ] 성능 테스트 (30일 데이터 로딩 시간 \u003c 2초)

- 변경 예상 파일/모듈:
  - `src/dashboard/routers/validator.py` (신규 API 엔드포인트)
  - `src/dashboard/templates/validator.html` (탭 구조 추가)
  - `src/dashboard/templates/validator/timeline.html` (신규 템플릿)
  - `src/dashboard/static/js/timeline-chart.js` (신규 Chart.js 설정)
  - `src/dashboard/data_helpers.py` (시계열 데이터 헬퍼 함수)

- 완료 기준 (Acceptance Criteria):
  - [ ] Validator 페이지에서 Timeline 탭 클릭 시 히트맵이 정상 표시됨
  - [ ] 주요 단어(Top 20)의 beta 값 변화가 시간 순서대로 시각화됨
  - [ ] 신규/퇴출 단어 리스트가 정확하게 표시됨
  - [ ] 이벤트 마커 클릭 시 해당 날짜의 뉴스가 팝업으로 표시됨
  - [ ] 30일 데이터 로딩 시간이 2초 이내
  - [ ] 모바일 반응형 레이아웃 지원

- 기술적 근거:
  - Chart.js Matrix Plugin: https://www.chartjs.org/chartjs-chart-matrix/
  - Chart.js Time Scale: https://www.chartjs.org/docs/latest/axes/cartesian/time.html
  - HTMX Tab Pattern: https://htmx.org/examples/tabs-hateoas/

Progress Log:
  - 2025-12-21 15:45: PRD 12.2 섹션 기반으로 TASK-044 수립. 3FS 워크플로우 준수.
