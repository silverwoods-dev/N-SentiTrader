# N-SentiTrader 개발 히스토리
## Development History - 31 Phases

> 이 문서는 N-SentiTrader의 **31개 개발 Phase**를 요약합니다.

---

## Phase 1-5: 기초 구축
- **날짜 처리 시스템**: datetime_helper.py 생성, Time Decay 로직 구현
- **기본 파이프라인**: Collector → Preprocessor → Learner → Predictor 구조 확립

## Phase 6-9: 스마트 파이프라인
- **MasterOrchestrator**: 작업 간 자동 연결 (뉴스 수집 → 학습 자동 트리거)
- **Ordered Lasso**: 시간적 페널티로 허위 상관관계 감소
- **메모리 최적화**: 순차적 데이터 로딩, 토큰 캐시 제한 (20,000)

## Phase 10-12: 운영 자동화
- **경량 일일 재학습**: Golden Parameters 활용
- **프리미엄 대시보드**: Glassmorphism UI, Lucide 아이콘

## Phase 13-18: 신뢰성 강화
- **유령 워커 수정**: 하트비트 프로세스 분리
- **중복 제거**: 뉴스 URL 교차 참조
- **좀비 방지**: 30초 유예 기간 도입

## Phase 20: 워커 인프라 확장
- **전용 큐**: verification_daily (빠른 업데이트) vs verification_jobs (무거운 스캔)
- **워커 스케일링**: Body Worker 4x, Verification Heavy 1x, Light 2x

## Phase 21: Grafana 대시보드 최적화
- **4x4 그리드**: 16개 핵심 컴포넌트 시각화
- **Flow Visualization**: Discovery → Collection → Analysis 파이프라인

## Phase 25: 로컬라이징
- **KST 변환**: 모든 시각에 한국 표준시 적용
- **메트릭 강화**: 뉴스 수집 범위 및 작업 시작 시각 표시

## Phase 26: 지능형 공백 탐지
- **Gap Detection**: 뉴스 0인 날짜 자동 탐지
- **One-Click Fill**: 누락 기간만 정확히 백필

## Phase 27: 좀비 및 메트릭 수정
- **스마트 하트비트**: updated_at 기준 활성 상태 판단
- **메트릭 정리**: 작업 종료 시 BACKTEST_PROGRESS 자동 제거

## Phase 28: 잔여 좀비 디버깅
- **견고한 MQ 체크**: RabbitMQ 연결 실패 시 좀비 경보 억제
- **직렬화 수정**: timestamp JSON 직렬화 오류 해결

## Phase 29: 메모리 최적화
- **Generator 도입**: 토큰화 중간 리스트 메모리 제거
- **min_df=3 복원**: 희귀 노이즈 토큰 가지치기
- **Relevance Filtering**: min_relevance 파라미터 추가

## Phase 30: 대시보드 개선
- **Min Relevance Score**: UI 입력 필드 추가
- **WF_CHECK 제거**: 미사용 옵션 정리

## Phase 31: 코드베이스 정리
- **파일 아카이브**: 34개 파일 (143MB) → .archive/2025-12-30/
- **Deprecated API 수정**: datetime.utcnow() → datetime.now(timezone.utc)

---

*전체 상세 내역은 `walkthrough.md` 참조*
