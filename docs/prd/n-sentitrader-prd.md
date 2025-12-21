<!-- docs/prd/n-sentitrader-prd.md -->

# 1. 개요(Overview)

- **한 줄 요약:** 뉴스 텍스트 마이닝을 통해 단어별 영향력을 수치화한 동적 감성사전을 구축하고, 이를 바탕으로 특정 종목의 익일 시장 초과 수익률(Expected Alpha)의 **방향과 강도**를 예측하는 시스템.
- **배경:** 단순 긍/부정 이분법을 넘어, 금융 시장의 특성을 반영한 단어별 영향력(Magnitude)과 유효 기간(Time Decay)을 수치화하여 실질적인 수익률(Magnitude) 예측 모델을 구축함.
- **핵심 목표:**
  - **이원화 동적 사전:** 주간 단위의 메인 사전(Lasso)과 일 단위의 버퍼 사전(최근 이슈 보정)을 결합.
  - **관리 효율화:** 일회성 대량 수집(Backfill)과 자동 증분 수집(Daily)의 명확한 분리 및 제어.
  - **검증 자동화:** 6개월 데이터(4개월 학습/2개월 검증) 기반의 Walk-forward 검증 프로세스 및 최적 학습 윈도우 탐색 연구.
  - **운영 안정성:** MeCab 기반 토크나이징의 재현성 확보 및 08:30 매매 시그널 생성 데드라인 준수.

# 2. 대상 사용자 및 사용 시나리오

- **시스템 관리자:** 수집 Job 관리, 인프라 성능 모니터링, 수동 재시도 및 중단 제어.
- **퀀트 분석가:** 모델 예측 결과 검증, 단어별 영향력 변화 모니터링, 최종 투자 의사결정 참고.
- **사용 시나리오:**
  1. **Job 생성:** 관리자가 특정 종목의 최근 1년치 뉴스를 수집하는 Backfill Job을 생성함. (종목 코드 입력 시 네이버 증권을 통해 종목명을 자동 조회하여 등록)
  2. **자동 등록:** Backfill 성공 시 해당 종목은 `Daily Targets`에 자동 등록됨 (옵션에 따라 'Active' 즉시 전환 가능).
  3. **데일리 파이프라인:** 매일 새벽 자동 수집 -> 토크나이징 -> 버퍼 사전 업데이트 -> 익일 Alpha 예측 -> 리포트 생성 (08:30 완료).
  4. **성능 검증:** 분석가가 검증 UI에서 지난 1개월간의 예측 정확도(Hit Rate)와 수익률 커브를 확인하고 모델 파라미터를 조정함.
  5. **감성 사전 추적:** 분석가가 Validator 대시보드의 Timeline View에서 주요 단어의 beta 값 변화를 시계열 차트로 확인하고, 모델 업데이트가 예측 정확도에 미친 영향을 분석함.

# 3. 범위 (Scope: In / Out)

## 3.1 포함 범위 (In-Scope)
- **수집:** 네이버 금융 뉴스 종목별 수집 (Backfill/Daily). RabbitMQ 기반 비동기 처리.
- **분석:** Lasso 회귀 기반 동적 감성 사전(Weekly) + EMA 기반 버퍼 사전(Daily).
- **검증:** Walk-forward 시뮬레이션을 통한 일반화 성능 측정.
- **제공:** Bento Grid 기반 관리자 대시보드 및 검증용 지표 가시화.

## 3.2 제외 범위 (Out-of-Scope)
- **실매매:** 자동 주문 및 체결 로직 (예문: API 주문 연동 등은 추후 과제).
- **포트폴리오:** 다수 종목 조합 및 비중 조절 로직.
- **SNS 분석:** 텔레그램, 유튜브 등 소셜 데이터 수집 (네이버 뉴스에 한함).

# 4. 데이터 모델 및 스키마 설계

## 4.1 데이터 처리 및 Alpha 계산
- **Alpha 정의:** $Alpha = r_{stock} - r_{benchmark}$ (BenchMark: 종목별 마켓 타입에 따라 KOSPI/KOSDAQ 자동 선정).
- **Timezone:** 모든 수집 및 분석 일자는 한국 시간(KST)을 기준으로 하며, 주말/공휴일 개장일 데이터 매핑 로직 포함.

## 4.2 기술 스택 (Tech Stack)
- **Backend:** Python 3.10+, FastAPI, `uv` 패키지 매니저.
- **Data:** Polars (고속 처리), Scikit-learn (Lasso), Mecab-ko.
- **Infra:** Docker (Multi-stage Build), PostgreSQL 15, RabbitMQ (Queue).
- **Frontend:** HTMX, Tailwind CSS, Lucide Icons, Chart.js (성능 시각화).

## 4.3 운영 정책
- **DeadLine:** 매일 오전 08:30까지 모든 분석 및 예측 결과가 DB에 확정 저장되어야 함.
- **MeCab 관리:** 사용자 사전 업데이트 시 CI 단에서 바이너리 빌드 및 `base-mecab` 이미지 갱신 후 롤잉 업데이트.
- **Failure Policy:** 수집 실패 시 3회 재시도 후 관리자에게 알림(DashBoard Error Segment).
- **Anti-Blocking Strategy:** 네이버의 IP 기반 차단을 우회하기 위해 Cloudflare WARP를 활용함. 호스트(Ubuntu) 서버 수준에서 WARP를 **Socks5 Proxy Mode**로 구동하고, 수집기 컨테이너에서 이 프록시를 경유하여 외부 요청(Naver News)을 송신하는 전략을 채택함. 이를 통해 내부 시스템(DB, MQ) 통신 성능은 유지하면서 외부 수집 트래픽만 IP를 마스킹함.

# 5. 시스템 아키텍처 (Architecture)

1. **Collector Layer:** Address/Body 워커가 독립적으로 작동하며 DB 및 MQ와 통신. 외부 뉴스 수집 시 호스트의 Cloudflare WARP Proxy(SOCKS5)를 경유하여 차단 위험을 최소화함.
2. **Analysis Layer (Learner):** 주간/일간 배치 작업으로 감성 사전 생성 및 DB 저장.
3. **Serving Layer (Predictor):** 저장된 사전을 기반으로 실시간에 가까운 점수 도출 및 예측 결과 제공.
4. **Presentation Layer (Dashboard):** HTMX를 이용한 동적 상태 업데이트 및 시각화 데이터 렌더링. 탭 기반 네비게이션(Current/Timeline/Performance) 도입.

# 6. 테스트 및 수용 지표

- **유닛/통합 테스트:** `pytest` 및 `Playwright` 기반 시나리오 테스트.
- **성능 지표(Acceptance Criteria):**
  - **방향성 정확도(Hit Rate):** 55% 이상 (검증 기간 1개월 기준).
  - **수익률 상관관계(Correlation):** 예측 점수(Score)와 실제 Alpha 간의 양의 상관관계 확보.
  - **예측 오차(MAE/RMSE):** 지속적인 모델 튜닝을 통한 수익률 예측 오차 최소화.
  - 전체 뉴스 수집 실패율 2% 미만 유지.

## 6.4 모니터링 및 메트릭 (Monitoring & Metrics)
- **인프라:** Prometheus (Metrics 스토리지) + Grafana (Visual Dashboard).
- **수집 메트릭:**
  - **Queue Depth:** RabbitMQ 각 큐별 대기 메시지 건수.
  - **Worker Throughput:** 초당 URL 추출 및 본문 수집 처리 건수.
  - **Error Rate:** 403 Forbidden(차단) 및 네트워크 에러율.
- **분석 메트릭:**
  - **Pipeline Latency:** Daily 배치 분석 및 연구 스크립트 소요 시간.
  - **Prediction Drift:** 예측 값이 특정 방향으로 편향되는지 실시간 감지.

# 7. 최적 학습 윈도우 연구 (Training Window Optimization)

- **연구 배경:** 단어 사전의 영향력이 시점으로부터 어느 기간까지 유효한지(Time Decay)를 정량적으로 파악하여, 학습 데이터의 범위를 최적화함. 지나치게 긴 학습 기간은 과적합(Overfitting)을 유발할 수 있으며, 짧은 기간은 일반화에 실패할 수 있음.
- **실험 설계:**
  - 대상 종목: 삼성전자(005930) 및 주요 타겟.
  - 데이터 범위: 최근 1년 뉴스 데이터 수집.
  - 변수: 학습 윈도우 크기 (1개월 ~ 12개월, 1개월 단위 증가).
  - 지표: 2개월 검증 기간 동안의 Hit Rate 및 상관관계 극대화 지점 포착.
- **연구 결과 (Preliminary):**
  - 단기(30일) 윈도우는 Hit Rate가 저조(0%)하여 과소적합/불안정성을 보임.
  - 중기(90일) 윈도우에서 성능 개선(>50%)이 관찰됨.
  - `src/scripts/research_window_optimization.py` 도구를 통해 주기적인(월간) 최적화 배치 작업을 권장함.
- **활용 계획:** 산출된 최적 윈도우를 `AnalysisManager`의 기본 학습 기간으로 고정 및 자동 조정 로직 도입. 현재는 보수적으로 **90일**을 기본값으로 제안.

# 8. 사고 이력 및 향후 과제 (Incident History & Future Tasks)

## 8.1 사고 이력 (Incident History)
- **[2025-12-15] MeCab 라이브러리 의존성 충돌:** MeCab-ko 설치 시 빌드 환경 차이로 인한 런타임 에러 발생. -> Docker Multi-stage build 도입 및 base-mecab 이미지 분리로 해결.
- **[2025-12-18] 뉴스 수집 누락 이슈:** Backfill 도중 중복 URL 처리 오류로 일부 데이터 유실. -> URL Hash PK 제약조건 및 `ON CONFLICT DO NOTHING` 강화로 해결.
- **[2025-12-21] 마이그레이션 실패 및 데이터 정합성 오류:** 제공된 SQL 덤프(`\restrict` 포함)와 대상 시스템(PostgreSQL 15) 간 호환성 문제로 데이터 복원 실패. 또한 App Code(`intensity` 컬럼 참조)와 DB Schema 간 불일치 확인. -> **표준 백업 절차 수립(Docs)** 및 **Schema Sync** 필요.
- **[2025-12-21] Worker 무한 재시작 (CrashLoop):** `docker-compose.yml`의 `HTTPS_PROXY` 설정이 로컬 WARP 환경과 불일치하여 `uv` 패키지 다운로드 실패. -> **Proxy 설정 비활성화**로 해결.

## 8.2 향후 과제 (Future Tasks)
- **Migration Stability:** 표준화된 DB 백업/복원 가이드라인 마련 (`--inserts` 옵션 권장).
- **LLM 통합:** 뉴스 본문 요약 및 핵심 이벤트를 추론하여 Lasso 피처 보강.
- **Auto-scaling:** 수집 큐 부하에 따른 Worker 컨테이너 자동 증설 (K8s HPA).
- **Multi-Source:** 네이버 외 해외 핀비즈, 주요 경제지 웹사이트 수집 채널 확장.

## 8.3 최근 코드 변경 요약 (2025-12-19)

### 변경 #1: Lasso 학습 출력 정렬 및 부정 단어 표시 개선 (TASK-030)
- **항목:** Lasso 학습 출력 정렬 및 부정 단어 표시 개선
- **배경:** `src/scripts/run_lasso_training.py`의 결과 출력에서 부정 단어(음수 계수)가 리스트 뒤쪽에 표시되어 '가장 부정적인 단어'가 바로 보이지 않는 문제가 있었습니다. 또한 Lasso 계수가 0에 매우 근접한 항목이 `-0.0` 형태로 표시되어 혼동을 일으켰습니다.
- **조치:** 출력 정렬을 개선하여 부정 단어는 '가장 음수(가장 부정적) → 덜 음수' 순으로 표시되도록 수정했습니다. 또한 출력 로직에서 양수/음수 필터를 명확히 분리하여 의미없는 근접 0 항목은 부정 리스트에서 제외합니다.
- **영향 범위:** `src/scripts/run_lasso_training.py` (출력만 변경), `src/learner/*` (모델 로직은 불변)
- **검증 방법:** `src/scripts/run_lasso_training.py`를 컨테이너 내에서 실행하여 출력의 'Top 10 Negative Words'가 음수 값이 큰 순서대로 정렬되고, `-0.0`과 같은 근접 0 값이 상단에 노출되지 않음을 확인합니다.

### 변경 #2: 검증 대시보드 단어 정렬 개선 (TASK-031)
- **항목:** `/validator` 대시보드의 Top Influencers 섹션 표시 로직 개선
- **배경:** 현재 `get_senti_dict_top` 함수는 절대값 기준으로 정렬(`ABS(beta) DESC`)하여 긍정/부정 단어가 섞여 표시되며, 사용자가 '가장 부정적인 단어'를 직관적으로 파악하기 어려웠습니다.
- **조치:** 긍정 단어(beta > 0)와 부정 단어(beta < 0)를 별도 쿼리로 분리하고, 부정 단어는 'beta ASC'(가장 음수부터) 정렬을 적용하여 명확성을 개선합니다. 또한 예측기(Predictor)에도 임계값 필터링을 추가하여 노이즈를 제거합니다.
- **영향 범위:** `src/dashboard/app.py`, `src/dashboard/templates/validator.html`, `src/predictor/scoring.py`
- **검증 방법:** `/validator` 페이지에서 Main/Buffer Dictionary 섹션을 확인하여 긍정/부정 단어가 각각 올바른 순서(긍정: 큰→작은, 부정: 작은→큰)로 표시되는지 검증합니다.

# Appendix A: Cloudflare WARP Installation (Ubuntu 24.04)

네이버 수집 차단 우회를 위한 인프라 설정 방법입니다.

1. **GPG 키 및 저장소 등록**
   ```bash
   curl -fsSL https://pkg.cloudflareclient.com/pubkey.gpg | sudo gpg --yes --dearmor --output /usr/share/keyrings/cloudflare-warp-archive-keyring.gpg
   echo "deb [signed-by=/usr/share/keyrings/cloudflare-warp-archive-keyring.gpg] https://pkg.cloudflareclient.com/ $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/cloudflare-client.list
   ```

2. **패키지 설치 및 서비스 시작**
   ```bash
   sudo apt-get update && sudo apt-get install -y cloudflare-warp
   sudo systemctl enable --now warp-svc
   ```

3. **기기 등록 및 프록시 모드 설정**
   ```bash
   warp-cli registration new
   warp-cli mode proxy
   warp-cli connect
   ```

4. **연결 확인**
   ```bash
   # 호스트에서 확인
   curl -x socks5h://127.0.0.1:40000 https://www.cloudflare.com/cdn-cgi/trace | grep warp
   ```
   *결과에 `warp=on`이 포함되어야 합니다.*

5. **Docker 컨테이너 연동**
   수집기(`address_worker`, `body_worker`)를 `network_mode: host`로 설정하고 환경 변수에 `HTTPS_PROXY=socks5h://127.0.0.1:40000`를 추가하여 호스트의 WARP 프록시에 직접 접근하도록 구성합니다.

---

# 9. 사고 이력 및 향후 과제 (Incident History & Future Tasks)

## 9.1 주요 변경 이력

### 변경 #1: Lasso 출력 정렬 로직 개선 (TASK-030)
- **날짜:** 2025-12-19
- **문제:** 부정 단어 정렬 시 -0.0에 가까운 값이 상위에 표시되어 혼란 발생
- **해결:** `run_lasso_training.py`에서 긍정/부정 단어를 분리하여 긍정은 DESC, 부정은 ASC 정렬로 수정
- **영향:** 학습 결과의 가독성 및 신뢰도 향상

### 변경 #2: Validator 대시보드 긍정/부정 분리 (TASK-031)
- **날짜:** 2025-12-19
- **문제:** Top Influencers 섹션에서 긍정/부정 단어가 혼재되어 표시
- **해결:** `src/dashboard/app.py`에 `get_senti_dict_pos_neg()` 함수 추가, 4개 리스트(Main Positive/Negative, Buffer Positive/Negative)로 분리 표시
- **영향:** UI/UX 개선, 단어별 영향력 방향성 즉시 파악 가능

### 변경 #3: 백테스트 모니터링 및 제어 기능 강화 (TASK-033~035)
- **날짜:** 2025-12-21
- **배경:** 백테스트(AWO Scan) 등록 후 중단하거나 삭제하는 기능이 부재하여 관리 효율성이 떨어짐. 또한 중복 등록 시 실행 상태 파악이 어려움.
- **요구사항:**
  - **제어 기능:** 실행 중인 백테스트 중단(Stop) 및 작업 레코드 삭제(Delete) 기능 추가.
  - **상태 관리:** `stopped` 상태를 추가하여 중단된 작업을 명시적으로 표시.
  - **중복 방지:** 동일 종목에 대해 이미 `running` 상태인 작업이 있을 경우 추가 실행을 제한하거나 사용자에게 알림.
  - **UI 개선:** 모니터링 페이지에 중단/삭제 버튼 추가 및 실시간 상태 반영 강화.
- **영향:** 시스템 자원 관리 최적화 및 사용자 운영 편의성 증대.

### 변경 #4: Validator 대시보드 구조 개선 및 Timeline View 추가 (TASK-032 계획)
- **배경:** tb_sentiment_dict 테이블의 복합 PK로 인해 단어 중복 표시 문제 및 시계열 추적 기능 부재.
- **요구사항:** 
  - **탭 네비게이션:** Current View / Timeline View / Performance View 3단 구성.
  - **Current View:** 최신 버전만 표시 (중복 제거). 긍정/부정 단어 분리 및 트렌드 아이콘 적용.
  - **Timeline View:** 주요 단어의 beta 값 변화를 Chart.js Time Scale로 시각화.
  - **기술적 근거:** Chart.js 공식 문서 및 NN/g 대시보드 디자인 원칙 준수.
- **상세 명세:** `docs/prd/validator-dashboard-improvement-spec.md`의 내용을 기반으로 구현.
- **우선순위:** P0

## 9.2 Performance Trend 차트 개선 요구사항

### 9.2.1 현재 문제점 (Current Issues)

1. **X축 날짜 중복 문제**
   - 같은 날짜에 여러 버전의 예측이 존재할 경우 Chart.js labels 배열에 중복 날짜가 표시됨
   - 예: `['10-20', '10-20', '10-21']` → 사용자 혼란 유발

2. **일 단위 집계 부재**
   - `tb_predictions` 테이블에서 prediction_date가 같은 여러 행이 있을 경우 집계하지 않고 모두 표시
   - 어떤 값이 최신인지, 어떤 기준으로 선택해야 하는지 불명확

3. **거래일/휴일 구분 없음**
   - `actual_alpha`가 NULL인 경우 (주말/공휴일) 시각적 구분이 없음
   - 뉴스는 365일 존재하지만 주가 데이터는 거래일만 존재하는 불일치

4. **이중 축 스케일 비직관성**
   - Alpha 값에 10배를 곱하여 표시 (`alphas.map(a => a * 10)`)
   - 사용자가 실제 수익률을 직관적으로 파악하기 어려움

5. **시각적 정보 부족**
   - Y=0 기준선 없음 (알파 양수/음수 구분 어려움)
   - 평균 성과선 없음 (전체 성과 수준 파악 불가)
   - Tooltip에 예측 정확도, 날짜 등 상세 정보 부족

### 9.2.2 개선 요구사항 (Improvement Requirements)

#### R1. Time Scale 적용 및 데이터 집계
- **요구사항:** Chart.js의 Time Scale (`type: 'time'`)을 사용하여 날짜 중복 문제 해결
- **데이터 구조 변경:**
  ```javascript
  datasets: [{
    label: 'Sentiment Score',
    data: [{x: '2025-10-20', y: 0.45}, {x: '2025-10-21', y: 0.52}, ...]
  }]
  ```
- **백엔드 집계 로직:**
  - 같은 날짜의 여러 예측이 있을 경우 **최신 값** (MAX(created_at)) 선택
  - 또는 **평균값** 사용 (설정 가능)
- **근거:** Chart.js 공식 문서 - Time Scale with `spanGaps` 옵션
- **우선순위:** P0 (사용자 혼란 해소)

#### R2. 거래일/휴일 시각적 구분
- **요구사항:** Missing Data (actual_alpha = NULL) 처리
- **방법 1 - spanGaps 사용:**
  ```javascript
  options: {
    spanGaps: 1000 * 60 * 60 * 24 * 2  // 2일 이내 갭 자동 연결
  }
  ```
- **방법 2 - Point Style 구분:**
  ```javascript
  pointStyle: function(ctx) {
    return ctx.raw.is_trading_day ? 'circle' : 'triangle';
  }
  ```
- **방법 3 - 배경 영역 표시:**
  - Box Annotation으로 주말 영역을 반투명 회색으로 표시
- **근거:** Chart.js 공식 문서 - spanGaps, Scriptable Point Styles
- **우선순위:** P1 (데이터 정확성)

#### R3. Annotation 플러그인 활용
- **요구사항:** 기준선 및 평균선 추가
- **구현:**
  ```javascript
  plugins: {
    annotation: {
      annotations: {
        zeroLine: {
          type: 'line',
          yMin: 0,
          yMax: 0,
          borderColor: 'rgba(0, 0, 0, 0.3)',
          borderWidth: 2,
          borderDash: [5, 5],
          label: {
            display: true,
            content: 'Break-even',
            position: 'end'
          }
        },
        avgLine: {
          type: 'line',
          yMin: avgAlpha,
          yMax: avgAlpha,
          borderColor: 'rgba(255, 165, 0, 0.5)',
          borderWidth: 1,
          label: {
            display: true,
            content: 'Avg Alpha',
            position: 'start'
          }
        }
      }
    }
  }
  ```
- **근거:** Chart.js Annotation Plugin 공식 문서
- **우선순위:** P1 (시각적 가독성)

#### R4. 동적 색상 및 스타일링
- **요구사항:** Alpha 값에 따른 동적 색상
- **구현:**
  ```javascript
  datasets: [{
    label: 'Actual Alpha',
    segment: {
      borderColor: ctx => ctx.p0.parsed.y > 0 ? '#10b981' : '#ef4444',
      backgroundColor: ctx => ctx.p0.parsed.y > 0 ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)'
    }
  }]
  ```
- **근거:** Chart.js Scriptable Options 공식 문서
- **우선순위:** P2 (UX 개선)

#### R5. Tooltip 커스터마이징
- **요구사항:** 상세 정보 표시
- **표시 정보:**
  - 날짜 (YYYY-MM-DD 형식)
  - 감성 점수
  - 실제 Alpha (백분율)
  - 예측 정확도 (is_correct)
  - 거래일 여부
- **구현:**
  ```javascript
  plugins: {
    tooltip: {
      callbacks: {
        title: (context) => {
          return new Date(context[0].parsed.x).toLocaleDateString('ko-KR');
        },
        label: (context) => {
          const data = context.raw;
          return [
            `감성 점수: ${data.score.toFixed(4)}`,
            `실제 Alpha: ${(data.alpha * 100).toFixed(2)}%`,
            `예측: ${data.is_correct ? '정확' : '부정확'}`,
            `거래일: ${data.is_trading_day ? 'Y' : 'N'}`
          ];
        }
      }
    }
  }
  ```
- **근거:** Chart.js Tooltip Callbacks 공식 문서
- **우선순위:** P1 (정보 전달)

#### R6. 이중 축 스케일 최적화
- **요구사항:** Alpha 10배 곱하기 제거 및 명확한 축 레이블
- **구현:**
  ```javascript
  scales: {
    y: {
      type: 'linear',
      position: 'left',
      title: {
        display: true,
        text: 'Sentiment Score'
      },
      ticks: {
        callback: (value) => value.toFixed(2)
      }
    },
    y1: {
      type: 'linear',
      position: 'right',
      title: {
        display: true,
        text: 'Alpha (%)'
      },
      ticks: {
        callback: (value) => `${(value * 100).toFixed(2)}%`
      },
      grid: {
        drawOnChartArea: false
      }
    }
  }
  ```
- **근거:** 사용자 직관성 향상 (실제 값 표시)
- **우선순위:** P1 (데이터 정확성)

#### R7. 날짜 범위 선택 기능
- **요구사항:** 7D / 30D / 90D / 전체 버튼 추가
- **구현:**
  - HTMX 버튼으로 `/validator/performance?stock_code={code}&range={7d|30d|90d|all}` 호출
  - 백엔드에서 `LIMIT` 조건 동적 적용
- **근거:** Timeline View 탭과 일관된 UX
- **우선순위:** P2 (사용자 편의성)

### 9.2.3 기술적 타당성 검증 (Technical Feasibility)

**검증 항목:**
- ✅ Chart.js Time Scale: 공식 문서 확인 완료 (`type: 'time'`, `spanGaps` 옵션)
- ✅ Annotation Plugin: chartjs-plugin-annotation CDN 추가 필요
- ✅ Scriptable Options: backgroundColor, borderColor 등 동적 설정 지원
- ✅ Tooltip Callbacks: 커스텀 레이블 및 포맷팅 지원
- ✅ 백엔드 집계: PostgreSQL `DISTINCT ON` 또는 `ROW_NUMBER()` 윈도우 함수 사용

**의존성:**
- Chart.js 4.x (이미 사용 중)
- chartjs-adapter-date-fns (이미 추가됨)
- chartjs-plugin-annotation (신규 추가 필요)

**성능 영향:**
- Time Scale 사용 시 데이터 포인트 수 제한 권장 (최대 500개)
- Decimation 플러그인으로 대량 데이터 자동 샘플링

### 9.2.4 수용 기준 (Acceptance Criteria)

- [ ] **AC1:** X축에 날짜 중복이 없어야 함 (같은 날짜는 1개만 표시)
- [ ] **AC2:** 주말/휴일이 시각적으로 구분되어야 함 (Point Style 또는 영역 표시)
- [ ] **AC3:** Y=0 기준선이 표시되어야 함
- [ ] **AC4:** Alpha 값이 실제 값으로 표시되어야 함 (10배 곱하기 없음)
- [ ] **AC5:** Tooltip에 날짜, 점수, 알파, 정확도가 모두 표시되어야 함
- [ ] **AC6:** 7D/30D/90D 범위 선택 버튼이 정상 작동해야 함
- [ ] **AC7:** Chart.js 렌더링 시간이 1초 이내여야 함 (500 포인트 기준)

### 9.2.5 구현 우선순위 (Implementation Priority)

**Phase 1 (P0 - 필수):**
1. R1: Time Scale 적용 및 데이터 집계
2. R6: 이중 축 스케일 최적화

**Phase 2 (P1 - 중요):**
3. R3: Y=0 기준선 추가
4. R5: Tooltip 커스터마이징
5. R2: 거래일/휴일 구분 (spanGaps 방식)

**Phase 3 (P2 - 권장):**
6. R4: 동적 색상 스타일링
7. R7: 날짜 범위 선택 기능

---

## 9.3 백필 수집 전략 최적화 (Optimized Backfill Collection Strategy)

### 9.3.1 현재 문제점 (Current Issues)
- **증분 백필 시 중복 탐색:** 기존에 3개월치 데이터를 수집한 종목에 대해 6개월로 기간을 늘려 백필을 수행할 경우, 현재 로직(최신순 수집)은 이미 수집된 최근 3개월치를 먼저 다시 훑은 뒤에야 과거 3~6개월치 구간에 도달함.
- **리소스 낭비:** 이미 DB에 존재하는 URL들을 중복 체크하느라 네이버 검색 요청 권한(Rate Limit)을 소진하고, 실제 새로운 데이터 수집이 지연됨.

### 9.3.2 개선 요구사항 (Improvement Requirements)
- **지능형 수집 순서 (Intelligent Date Ordering):**
    - **최초 수집 (First-time Backfill):** 종목 등록 후 첫 수집 시에는 현재와 같이 **최신순(Backward)**으로 수집하여 분석에 즉시 활용 가능한 최신 데이터를 먼저 확보함.
    - **증분 수집 (Incremental Backfill):** 이미 수집 이력이 있는 종목에 대한 추가 백필 요청 시, 요청 범위의 **가장 과거 일자부터(Forward)** 수집을 시작함.
- **기대 효과:**
    - 새로운(과거의) 데이터를 즉시 발견하고 수집하므로 Job의 실질적 진행도가 초반에 집중됨.
    - 이미 수집된 구간에 도달하더라도 Job의 후반부이므로 사용자 대기 시간이 단축됨.

### 9.3.3 기술적 구현 방안
- **이력 확인:** `AddressCollector.handle_job` 시작 시 `daily_targets`의 `backfill_completed_at` 또는 `tb_news_mapping` 존재 여부를 확인하여 '최초' 여부 판별.
- **루프 제어:** `range(days)` 루프 내에서 처리 방향(Direction)에 따라 `target_date` 계산 공식 변경.
    - Backward: `end_date - timedelta(days=i)` (i: 0 -> days-1)
    - Forward: `(end_date - timedelta(days=days-1)) + timedelta(days=i)` (i: 0 -> days-1)

---

# 10. 향후 과제 (Future Tasks)

- **신조어 자동 등록:** OOV(Out-of-Vocabulary) 키워드 자동 탐지 및 사용자 사전 업데이트 프로세스
- **해외 주식 지원:** 미국 S&P500 종목 대상 뉴스 수집 및 감성 분석 확장
- **Transformer 모델 실험:** BERT/FinBERT 기반 문맥 분석과 Lasso 기반 단어 점수 비교 연구
- **A/B 테스팅:** Main/Buffer 앙상블 가중치 최적화를 위한 실험 프레임워크 구축

# 11. 대시보드 이원화 및 전문가용 분석 도구 (Dashboard Bifurcation)

### 11.1 이원화 목적 (Bifurcation Goals)
- **운영 대시보드 (Operational Dashboard):** 뉴스 수집의 안정성, 워커 상태, MQ 부하, 에러 로그 등 인프라 및 프로세스 모니터링에 집중 (대상: SRE/운영팀).
- **분석 대시보드 (Analytical Dashboard - Quant Hub):** 감성 사전의 질적 평가, Lasso 모델의 계수 분포, 예측 정확도(Alpha), 최적 학습 윈도우 연구 결과 등 데이터 사이언스 지표에 집중 (대상: 데이터 분석가/퀀트).

### 11.2 분석 대시보드(Quant Hub) 전용 요구사항
- **독립적 엔트리 포인트:** 기존 `/validator`를 `/analytics` 또는 별도의 전문가용 서브 도메인급 UI로 격상.
- **Lasso 모델 가시화:** 
    - 계수(Beta)의 전체적인 통계량 (Sparsity, Max/Min, 분포 차트).
    - Main 사전 vs Buffer 사전의 상관관계 분석.
- **심층 리포트:** 개별 예측 성공/실패 사례에 대한 형태소 레벨의 기여도 분석(Local Explanation) 도구 추가.

### 11.3 단어사전 생명주기 관리 (Dictionary Lifecycle & Versioning)
- **버전 이력 조회:** 종목별/소스별(Main, Buffer)로 생성된 모든 단어사전의 생성 시점, 학습 파라미터, 당시의 검증 성과를 리스트 형태로 제공.
- **버전 고정 및 롤백 (Pinning/Rollback):** 성능 이슈 발생 시, 시스템이 추천하는 최신 버전 외에 관리자가 검증된 과거 버전을 '서비스용'으로 수동 지정할 수 있는 UI 제공.

### 11.4 학습 윈도우 자동 최적화 (Auto-Window Optimization, AWO)
- **최적 윈도우 탐색 전략 (Two-stage Exploration):**
    - **1단계: 전수 스캐닝 (Exhaustive Initial Scan):** 시스템 도입 초기 또는 충분한 데이터(1년 이상)가 쌓인 종목에 대해 1개월부터 11개월까지 1개월 단위로 모든 윈도우 크기를 적용. 
        - 방법: 각 $n$개월 학습셋 구성 후, 최근 1개월 데이터를 1일씩 롤링하며 예측/검증 수행.
    - **2단계: 지능형 동적 샘플링 (Intelligent Dynamic Sampling):** 1단계를 통해 도출된 최적 윈도우($W_{best}$)를 기준으로, 차기 검증 시에는 $W_{best}$ 주변부 및 시스템이 판단한 유의미한 구간(근거 기반 임의의 개월수)으로 케이스를 좁혀가며 효율적으로 검증 수행.
- **최적 가중치/기간 판별:** 윈도우별 검증 성과(Hit Rate, Alpha 안정성)를 비교하여 최적점을 자동 선택.
- **데이터 소거 (Data Culling):** 영향력이 유실된 오래된 뉴스를 학습 셋에서 배제하는 최적 포인트를 모델 스스로 결정.

### 11.5 시스템 구성 검증 (Walk-forward Backtesting UI)
- **백테스팅 잡 등록:** 관리자가 시스템의 전반적인 구성을 검증하기 위한 시뮬레이션 작업을 등록하고 관리할 수 있는 환경 제공.
- **시나리오 설정:** "최근 3개월 뉴스 중 2개월 학습 / 1개월 검증 (1일 단위 롤링 업데이트)"과 같은 구체적인 검사 기간 및 스텝 설정 가능.
- **성능 증빙 레포트:** 롤링 업데이트 시뮬레이션을 통해 산출된 Hit Rate, 수익률 커브, 지표 안정성을 종합 레포트로 자동 생성. 이는 현재 구축 중인 시스템의 로직(사전 이원화 등)이 실제 시장 데이터에서 유효함을 입증하는 근거로 활용.

### 11.6 기술적 구현 방안
- **라우팅 분리:** `src/dashboard/app.py` 내에서 운영 관련 API와 분석 관련 API를 로직적으로 분리 (APIRouter 활용).
- **검증 전용 테이블 도입:** `tb_verification_jobs` 및 `tb_verification_reports` 등을 추가하여 백테스팅 데이터와 실제 운영 데이터의 혼선 방지.
- **비동기 처리:** 대량의 학습/검증이 필요한 백테스팅 작업은 전용 Worker를 통해 비동기로 처리하고 대시보드에서 진행률 모니터링.
# 12. 분석 대시보드(Quant Hub) UI/UX 고도화 요건

### 12.1 배경 및 목적
전문가용 대시보드는 정밀한 데이터를 제공해야 하지만, 단순히 많은 숫자와 복잡한 선 차트만으로는 시장의 '맥락(Context)'을 빠르게 파악하기 어려움. 퀀트 분석가가 모델의 판단 근거를 직관적으로 이해하고, 사전의 진화 과정을 한눈에 파악할 수 있도록 시각적 언어를 재정의함.

### 12.2 뷰(View)별 상세 고도화 요건

#### R12.1: Current View - "감성 에너지 및 근거 제시"
- **감성 에너지 게이지(Polarity Gauge):** 현재 종목의 총 긍정 베타와 절대값 기준 총 부정 베타의 합을 비교하여, 시장의 에너지가 어느 쪽으로 편중되어 있는지 반원 게이지로 표시.
- **중요도 기반 워드맵(Saliency Map):** 단순히 리스트를 보여주는 대신, 베타의 절대값 크기를 폰트 크기로 치환한 워드 클라우드 형태의 UI 도입. (긍정: Indigo, 부정: Crimson 색상 적용)
- **추론 근거 연결(Grounding):** 특정 단어 클릭 시, 해당 단어가 포함되어 오늘(혹은 해당 일자)의 감성 점수에 기여한 실제 뉴스 헤드라인 리스트를 팝업 또는 사이드바에 표시. 

#### R12.2: Timeline View - "단어 사전의 진화 추적"
- **단어 가중치 히트맵(Word Weight Heatmap):** 다수의 단어를 선 차트로 그릴 때 발생하는 시각적 혼란(Spaghetti Chart)을 방지하기 위해 히트맵 도입.
    - X축: 시간(일 단위), Y축: 주요 단어(Top 20), 색상 농도: 베타 값의 강도.
- **신규/퇴출 단어 리스트(Vanguard & Derelict):** 최근 7일 내에 사전에 새로 진입했거나(Vanguard), 영향력이 0으로 수렴하여 퇴출된(Derelict) 단어들을 별도로 하이라이트하여 시장 키워드의 세대교체를 감지.
- **이벤트 마커(Event Annotation):** 타임라인 차트 상에 뉴스 발생량이 평소보다 2배 이상 높았던 지점이나 주가 변동성이 컸던 지점을 수직선으로 표시하여 사전 변화와의 상관관계 파악 지원.

#### R12.3: Performance View - "예측 신뢰도 분석"
- **알파 상관관계 산점도(Alpha Correlation Plot):** 예측 점수(X축)와 익일 실제 Alpha(Y축)의 산점도를 그리고, 회귀선(Regression Line)과 결정계수($R^2$)를 표시하여 모델의 설명력을 시각화.
- **AWO 의사결정 근거 가시화:** 1~11개월 전수 스캔 결과 중 왜 특정 윈도우가 선택되었는지(윈도우별 Hit Rate 비교 바 차트)를 보여주어 자동 최적화 결과에 대한 신뢰도 부여.
- **예측 신뢰 지수(Reliability Index):** 뉴스 수집량의 충분성, 모델 가중치의 안정성 등을 종합하여 현재의 예측 시그널이 얼마나 '신뢰할 만한지'를 백분율로 표시.

### 12.3 기술적 검토 및 구현 전략
- **시각화 라이브러리:** Chart.js Matrix Plugin (히트맵용), D3.js 또는 CSS 기반 Scaling (워드맵용) 활용.
- **데이터 집계 최적화:** 히트맵이나 산점도 데이터는 연산량이 많으므로 별도의 Materialized View 또는 캐싱 레이어를 통해 대시보드 로딩 성능 유지.
- **상태 안내 브레드크럼:** AWO 엔진이 백그라운드에서 동작 중일 때 "최적화 진행 중(Optimizing...)" 상태를 상단에 노출하여 사용자에게 데이터 갱신 시점을 인지시킴.

# 13. 예측 목표 재정의 및 멀티 팩터 확장 (Prediction Target & Multi-Factor)

### 13.1 모델 예측 목표의 실질적 전환 (Regression-First)
- **현행:** Lasso 회귀로 수익률(Alpha)을 학습하지만, 최종 출력은 이진 분류(상승/하락)로 편향되어 있음.
- **개선:** 모델의 본질인 **회귀(Regression)** 성능을 전면에 내세움. 
    - **예측치(Expected Alpha):** 단순 '상승' 대신 "익일 +0.45% Alpha 예상"과 같은 수치형 기대 수익률을 기본값으로 사용.
    - **6-스테이트 정밀 시그널 (6-State Signal Taxonomy):** 단순히 점수의 크기뿐만 아니라, 긍정/부정 에너지의 총합(Intensity)과 순에너지(Net Score)를 교차 분석하여 다음 6단계 상태로 세분화함.

| 상태 (Status) | 정의 (Definition) | 시장 맥락 (Context) | 시각적 표현 |
| :--- | :--- | :--- | :--- |
| **강한 매수 (Strong Buy)** | Net Score >> 0 | 압도적인 호재로 강력한 상승 압력 | Indigo / Deep Blue |
| **신중한 매수 (Cautious Buy)** | Net Score > 0 | 완만한 호재 또는 반등 시그널 | Light Blue / Cyan |
| **관망 (Observation)** | Intensity $\approx$ 0 | 주요 뉴스 부재, 거래량 및 관심 저조 | Grey / Slate |
| **복합 상태 (Mixed)** | Intensity >> 0, Net $\approx$ 0 | 강력한 호재와 악재의 충돌, 변동성 폭발 전조 | Amber / Orange Dash |
| **신중한 매도 (Cautious Sell)** | Net Score < 0 | 완만한 악재 또는 차익 실현 매물 | Coral / Salmon |
| **강한 매도 (Strong Sell)** | Net Score << 0 | 압도적인 악재로 강력한 하락 압력 | Crimson / Red |

- **분류 로직:**
    - `Net Score = Positive_Score + Negative_Score` (Beta 가중치 합계)
    - `Sentiment Intensity = |Positive_Score| + |Negative_Score|`
    - `Intensity`가 임계값 이하일 경우 -> **관망**
    - `Intensity`가 높으나 `|Net Score|`가 낮을 경우 -> **복합 상태**
    - 그 외 `Net Score`의 임계 구간에 따라 매수/매도/신중 단계 결정

### 13.2 종속 변수 및 피처 확장 (Financial Factors Integration)
- **재무 팩터 결합:** 뉴스 감성 데이터뿐만 아니라, 종목의 기본적/기술적 지표를 피처로 추가하여 예측력을 보강함.
    - **주요 팩터:** PER(주가수익비율), PBR, 시가지총액 대비 거래대금 비율, 섹터 베타(Sector Beta).
- **멀티 타겟 학습 (Future):** 단순 Alpha 외에도 변동성(Volatility) 또는 거래량 폭발 가능성을 동시에 예측하는 다중 목적 함수(Multi-objective) 고려.

### 13.3 시각화 및 검증 로직 정합성 확보
- **Performance View 라벨링 수정:** '예측(상승/하락)' 문구를 '기대수익률(Expected Alpha)'로 변경하고, Y축 단위를 실제 백분율(%)로 일원화.
- **분산형 검증:** Hit Rate(방향) 외에도 Scatter Plot을 통한 예측치와 실제치의 선형성(Linearity)을 품질 지표로 추가함.

### 13.4 이상치 관리 및 규제 강화 (Outlier Management & Regularization)

- **Lasso 규제 강도 최적화 (Regularization Strength):**
    - **가설:** 기존 `alpha=0.0001`은 과적합 위험이 높고 계수가 불안정함.
    - **조치:** 기본 `alpha`를 **0.005**로 상향 조정하고, AWO Scan 시 윈도우 크기와 함께 `alpha` 후보군에 대한 교차 검증을 고려함.
    - **기대 효과:** 단어별 계수의 안정성 확보 및 예측치의 비정상적 변동 억제.

- **예측값 클리핑 및 윈저라이징 (Winsorization/Clipping):**
    - **배경:** 단일 호재성 뉴스가 과도하게 중첩될 경우 +4000%와 같은 비상식적인 `expected_alpha`가 산출될 수 있음.
    - **로직:**
        - **Hard Clipping:** 모든 `expected_alpha`는 일일 최대 변동폭 제한(예: +/- 15%)을 초과할 수 없음.
        - **Soft Warning:** 예측치가 특정 임계값(예: +/- 5%)을 초과할 경우, 모델의 신뢰도(Confidence Level)를 낮게 표시하고 관리자에게 경고 로그를 남짐.
    - **구현:** `Predictor.predict_advanced` 함수 내 최종 출력 전 단계에 적용.

- **성과 지표 고도화 (Refined Metrics):**
    - **MAE (Mean Absolute Error):** 단순히 방향(Hit Rate)뿐만 아니라, 예측한 Alpha 수치와 실제 Alpha 수치 간의 절대 오차를 핵심 지표로 관리.
    - **Prediction Stability Index (PSI):** 수집된 뉴스 양의 변동에 따라 예측값이 급격하게 튀지 않는지 안정성 지표 도입.

# Appendix B: AWO 기반 모델 자동 갱신 프로세스 (AWO Model Promotion)

1. **Scan Phase:** `AWOEngine`이 1~11개월 윈도우 전수 조사 수행. (Job 등록)
2. **Evaluation Phase:** 각 윈도우별 Hit Rate 및 MAE를 기반으로 최적 윈도우($W_{best}$) 선정.
3. **Promotion Phase:** $W_{best}$를 사용하여 전체 데이터에 대해 최종 학습(Training) 수행 후, 해당 버전을 `is_active = TRUE`로 설정하여 Production에 배포.
4. **Monitoring:** 배포 후 1주일간의 실시간 예측 성과를 모니터링하여 Drift 발생 시 이전 버전으로 롤백.
