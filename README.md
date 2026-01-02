# N-SentiTrader: 실무형 화이트박스 주식 예측 시스템 (Technical Bible)

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Technology](https://img.shields.io/badge/Tech-FinBERT_|_Lasso_|_RabbitMQ_|_MLX-orange)](https://github.com/silverwoods-dev/N-SentiTrader)
[![Architecture](https://img.shields.io/badge/Architecture-MSA-red)](https://github.com/silverwoods-dev/N-SentiTrader)

## 🎓 훈련생을 위한 기술 총서 (The Ultimate Guide)

> **[프로젝트 선언]** 본 문서는 단순한 "사용 설명서"가 아닙니다. AI 서비스 개발자 양성과정의 훈련생들이 **금융 도메인의 규제(Compliance)**, **대규모 데이터 처리의 병목(Bottleneck)**, 그리고 **하드웨어 가속의 원리(Acceleration)**를 깊이 있게 이해할 수 있도록 설계된 **'기술 백서(Technical Whitepaper)'**입니다. 우리는 "결과"보다 "과정"을, "코드"보다 "설계의 이유"를 설명합니다.

---

## 📋 목차 (Table of Contents)

### Part 1: 철학과 아키텍처 (Philosophy & Architecture)
1.  [🏛️ 왜 화이트박스(White-Box)인가? (XAI와 법적 근거)](#1-왜-화이트박스white-box인가-xai와-법적-근거)
2.  [⚙️ 기술 스택 및 마이크로서비스(MSA) 설계](#2-기술-스택-및-마이크로서비스msa-설계)
3.  [📊 시스템 아키텍처 및 데이터 흐름도](#3-시스템-아키텍처-및-데이터-흐름도)

### Part 2: 데이터 인텔리전스 (Data Intelligence)
4.  [🛡️ 데이터 수집 및 지능형 필터링 전략](#4-데이터-수집-및-지능형-필터링-전략)
5.  [🛠️ 전처리 파이프라인: BERT 요약 및 N-gram 전략](#5-전처리-파이프라인-bert-요약-및-n-gram-전략)

### Part 3: 최적화 엔지니어링 (Scientific Engineering)
6.  [🔬 Deep Dive: 워크플로우 최적화 (Memory & Metrics)](#6-deep-dive-워크플로우-최적화-memory--metrics)
7.  [🚀 Deep Dive: 하드웨어 가속 (MLX & Celer)](#7-deep-dive-하드웨어-가속-mlx--celer)
8.  [📈 핵심 알고리즘: Lasso 회귀와 Time Decay](#8-핵심-알고리즘-lasso-회귀와-time-decay)
9.  [🧬 AWO 엔진: 시장의 비정상성 대응과 안정성 점수](#9-awo-엔진-시장의-비정상성-대응과-안정성-점수)

### Part 4: 운영과 진화 (Operations & Evolution)
10. [🖥️ 프론트엔드 아키텍처: Glassmorphism & Chart.js](#10-프론트엔드-아키텍처-glassmorphism--chartjs)
11. [🛣️ 31단계 개발 히스토리 (Evolutionary Roadmap)](#11-31단계-개발-히스토리-evolutionary-roadmap)
12. [🔄 상세 운영 프로세스 및 좀비 워커 관리](#12-상세-운영-프로세스-및-좀비-워커-관리)
13. [📊 주요 메트릭 및 성과 지표](#13-주요-메트릭-및-성과-지표)
14. [🚀 시작하기 및 개발자 가이드](#14-시작하기-및-개발자-가이드)
15. [⚠️ 향후 과제 (Future Work)](#15-향후-과제-future-work)

---

# Part 1: 철학과 아키텍처

## 1. 🏛️ 왜 화이트박스(White-Box)인가? (XAI와 법적 근거)

### 🧐 배경: 금융권의 '설명 책임' (Accountability)
최근 LLM(GPT-4 등)이 등장했음에도 불구하고, 실무 금융권에서 선형 모델 기반의 화이트박스를 고집하는 이유는 기술적 한계 때문이 아닌, **'법적 생존'** 때문입니다.

#### 법적 근거 (Legal Basis)
1.  **EU AI Act (2024)**: 고위험(High-risk) AI 시스템, 특히 신용 평가 및 금융 서비스에 대해 **"해석 가능성(Interpretability)"**과 **"추적 가능성(Traceability)"**을 의무화했습니다.
2.  **GDPR 제13조-14조**: 정보 주체는 자동화된 의사 결정에 대해 **"유의미한 정보"**를 제공받을 권리가 있습니다. "딥러닝이 그랬어요"는 법적 답변이 될 수 없습니다.
3.  **ECOA (미국 평등신용기회법)**: 대출 거절 시 **구체적인 사유(Adverse Action)**를 명시해야 합니다. (예: "소득 대비 부채 비율 과다" vs "모델 점수 0.3 미달")

### ✅ 화이트박스(Lasso) vs. 블랙박스(LLM) 비교

| 구분 | 화이트박스 (본 프로젝트) | 블랙박스 (딥러닝/LLM) | 비고 |
|------|-------------------------|-------------------|------|
| **해석 가능성** | <b>✅ 완전 투명</b> (Feature Importance 직접 확인) | ❌ 불투명 (Black-box) | 규제 대응 핵심 |
| **학습 제어** | <b>✅ 특성 공학(Feature Engineering) 통제 가능</b> | ❌ 데이터 통제 어려움 (Hallucination) | 신뢰성 |
| **인프라** | <b>✅ CPU/MPS (MacBook Air 구동 가능)</b> | ❌ 고성능 H100 GPU 필수 | 비용 효율성 |
| **데이터 보안** | <b>✅ 100% On-premise (폐쇄망)</b> | ❌ 클라우드 API 전송 (정보 유출 위험) | 보안성 |

> [!TIP]
> **초보 개발자를 위한 팁**: 딥러닝은 'What(결과)'을 잘 맞추지만 'Why(이유)'를 설명하지 못합니다. 금융, 의료, 법률 등 **책임이 따르는 도메인**에서는 설명 가능한 선형 모델이 여전히 강력한 주무기입니다.

---

## 2. ⚙️ 기술 스택 및 마이크로서비스(MSA) 설계

### 🛠️ 코어 기술 스택 (Technology Stack Table)

| 영역 | 기술 | 선정 이유 (Decision Rationale) |
|------|------|--------------------------------|
| **코어 언어** | **Python 3.11** | 비동기(`asyncio`) 성능 개선 및 Type Hinting 강화로 안정성 확보. |
| **데이터 처리** | **Polars** | **Rust** 기반의 고성능 데이터프레임 라이브러리. Pandas 대비 메모리 사용량 1/5, 속도 10배 이상 빠름 (Zero-copy). 대용량 시계열 뉴스 처리에 필수. |
| **ML 엔진** | **Lasso (Celer/MLX)** | 좌표 하강법(Coordinate Descent)의 병렬화 한계를 극복하기 위해 **Celer (Working Set)** 및 **MLX (Apple GPU)** 가속 도입. |
| **형태소 분석** | **MeCab** | KoNLPy 중 속도가 가장 빠르며(C++), **사용자 사전 빌드**가 용이하여 'HBM', 'AI반도체' 등 신조어를 즉시 반영 가능. |
| **메시지 큐** | **RabbitMQ** | **느슨한 결합(Decoupling)** 및 **배압 조절(Backpressure)**. 뉴스 트래픽 폭주 시 서버 다운을 막고 큐에 쌓아두는 완충 장치 역할. |
| **대시보드** | **FastAPI + Jinja2** | 별도의 React 프론트엔드 없이 서버사이드 렌더링(SSR)으로 빠른 개발 속도와 SEO 최적화 달성. |

### 🏢 마이크로서비스(MSA) 도입의 기술적 근거
1.  **자원 격리 (Resource Isolation)**: BERT 요약기(GPU 사용)가 뉴스 수집기(I/O 바운드)의 성능을 저하시키지 않도록 물리적으로 컨테이너를 분리했습니다.
2.  **장애 전파 차단 (Fault Tolerance)**: DB가 죽어도 RabbitMQ가 살아있으면 수집된 뉴스는 유실되지 않고 큐에 보관됩니다. (재처리 보장)

---

## 3. 📊 시스템 아키텍처 및 데이터 흐름도

시스템은 5개의 독립된 레이어와 17개의 Docker 컨테이너로 구성됩니다.

```mermaid
graph TD
    subgraph "External World"
        Naver[Naver News API]
        KRX[KRX Market Data]
    end

    subgraph "Ingestion Layer (Network I/O)"
        Disc[Discovery Service] --> |Schedule| Coll[Collector Workers]
        Coll --> |RabbitMQ| MQ[(Message Queue)]
    end

    subgraph "Brain Layer (Compute Heavy)"
        MQ --> Pre[Preprocessor]
        Pre --> NLP[BERT Summarizer]
        NLP --> Train[Lasso Learner (MLX)]
        Train --> Predict[Predictor Engine]
    end

    subgraph "Persistence Layer"
        Train --> DB[(PostgreSQL)]
        Predict --> DB
        DB --> Cache[(Redis/Local Cache)]
    end

    subgraph "Visualization"
        DB --> Dash[Expert Dashboard]
        DB --> Grafana[Grafana Monitoring]
    end
```

---

# Part 2: 데이터 인텔리전스

## 4. 🛡️ 데이터 수집 및 지능형 필터링 전략

### 📡 지능형 공백 탐지 (Gap Detection)
단순한 크롤링이 아닙니다. 시스템은 **'데이터의 연속성'**을 스스로 감시합니다.
- **로직**: Trading Calendar와 DB의 뉴스 수집 일자를 대조하여 `Count=0`인 날짜(Gap)를 자동으로 식별합니다.
- **복구**: **One-Click Backfill** 버튼을 통해 해당 기간의 뉴스만 정밀 타격하여 수집합니다.

### 🎯 종목별 정밀 필터링 (Relevance Scoring)
"삼성전자" 검색어에 "삼성전자 냉장고 출시" 기사가 섞이면 주가 예측은 망가집니다. 이를 막기 위해 **휴리스틱 채점 알고리즘**을 적용했습니다.

| 필터링 항목 | 가중치 | 상세 설명 |
|------|---|---|
| **Title Match** | **0.4** | 헤드라인에 종목명이 있는가? (가장 강력한 시그널) |
| **First Para** | **0.3** | 기사의 첫 문단(리드문)에 종목명이 등장하는가? |
| **Density** | **0.3** | 본문 전체 대비 종목명 언급 빈도 (노이즈 판별) |

$$ Score = (0.4 \times Title) + (0.3 \times Lead) + (0.3 \times Density) $$

---

## 5. 🛠️ 전처리 파이프라인: BERT 요약 및 N-gram 전략

## 🧠 BERT 기반 추출 요약 (Extractive Summarization)
금융 뉴스 데이터의 50%는 '노이즈'(광고, 기자 이메일, 무관한 시황)입니다. 이를 제거하지 않으면 모델 성능은 결코 오르지 않습니다 (GIGO).

### Why Extractive? (왜 추출 요약인가?)
- **생성 요약(GPT)**: "삼성전자가 30% 올랐다"고 없는 말을 지어낼(Hallucination) 위험이 있습니다.
- **추출 요약(BERT)**: 원문의 문장을 **그대로 발췌**하므로 데이터의 **무결성(Integrity)**이 보장됩니다. 본 프로젝트는 `KR-FinBERT`를 이용해 문맥상 가장 중요한 3문장을 추출합니다.

## 🧬 N-gram 전략: 문맥의 반전을 포착하라
한국어는 **교착어**입니다. 단어 하나만으로는 의미가 왜곡됩니다.
- **Unigram (1-gram)**: `하락` → (부정)
- **Trigram (3-gram)**: `하락` + `폭` + `둔화` → (강한 긍정: 바닥 신호)

우리는 1, 2, 3-gram을 모두 생성하여 이러한 **문맥 반전(Sentiment Inversion)**을 포착합니다.

---

# Part 3: 최적화 엔지니어링 (Scientific Engineering)

## 6. 🔬 Deep Dive: 워크플로우 최적화 (Memory & Metrics)

초기 모델은 12개월 데이터를 학습할 때 **OOM(Out of Memory)**이 발생했습니다. 철저한 프로파일링을 통해 다음과 같은 최적화를 수행했습니다. (참고: `docs/workflow_optimization.md`)

| 최적화 항목 | 변경 전 (Before) | 변경 후 (After) | 개선 효과 | 근거 (Rationale) |
|------------|-----------------|-----------------|-----------|------------------|
| **Max Features** | 50,000개 | **15,000개** | 메모리 60% 절감 | 학술 연구상 8,000개 이상에서 성능 포화 (Diminishing Returns) |
| **N-gram** | (1, 3) | **(1, 2)** | 특성 수 40% 감소 | Trigram의 추가 이득 대비 메모리 비용이 과다함 |
| **Lags** | 5일 | **3일** | 특성 수 40% 감소 | 금융 정보의 유효 반감기는 통상 3일 이내 (Efficient Market) |
| **Min DF** | 3 | **5** | 노이즈 대폭 감소 | 5개 미만 문서에 등장하는 단어는 통계적 유의성이 없음 |

---

## 7. 🚀 Deep Dive: 하드웨어 가속 (MLX & Celer)

Apple Silicon(M1/M2/M3)의 성능을 100% 끌어내기 위해 Scikit-learn을 버리고 고성능 엔진을 도입했습니다. (참고: `docs/mlx_research_report.md`)

### A. Celer (Working Set Algorithm)
Lasso는 수만 개의 변수 중 대부분이 0이 되는 희소(Sparse) 모델입니다.
- **원리**: 모든 변수를 매번 미분하지 않고, 0이 아닐 확률이 높은 **활성 집합(Working Set)**만 추려내어 연산합니다.
- **효과**: Scikit-learn 대비 **10~50배** 속도 향상.

### B. MLX (Apple Silicon Native)
- **Unified Memory**: CPU와 GPU가 메모리를 공유하므로, 데이터를 GPU로 복사(Copy)하는 병목이 **"Zero"**입니다.
- **FISTA 알고리즘**: L1 규제항(미분 불가능)을 해결하기 위해 **FISTA(Fast Iterative Shrinkage-Thresholding Algorithm)**를 구현하여 GPU 병렬 처리를 극대화했습니다. 10만 건 뉴스 학습을 수 분 내에 완료합니다.

---

## 8. 📈 핵심 알고리즘: Lasso 회귀와 Time Decay

### 📉 Lasso(L1) 정규화
$$ \min_{\beta} \left( \|y - X\beta\|^2_2 + \alpha \|\beta\|_1 \right) $$
**$\alpha$ (Alpha)** 값을 조절하여 영향력이 적은 단어의 가중치를 **완전히 0**으로 만듭니다. 이를 통해 수천 개의 단어 중 정말 중요한 **'시장 주도 키워드'**만 남깁니다.

### ⏳ Time Decay: 정보의 유통기한
$$ Weight = e^{-\lambda \times \text{days}} $$
오늘의 뉴스가 3일 전 뉴스보다 중요합니다. **Hong & Stein (1999)**의 연구에 따라 지수적 감쇠(Exponential Decay)를 적용하여 과거 정보의 과적합을 막습니다.

---

## 9. 🧬 AWO 엔진: 시장의 비정상성 대응과 안정성 점수

금융 시장은 끊임없이 변합니다(**Non-stationarity**). 영원한 승리 전략은 없습니다.

### 🎯 Adaptive Window Optimization (AWO-2D)
매주 토요일 새벽, 시스템은 수만 가지 파라미터 조합(Window Size x Alpha)을 시뮬레이션(Walk-forward)하여 **"지금 이 순간 시장에 가장 잘 맞는 설정"**을 찾습니다.

### 📐 안정성 점수 (Stability Score)
단순 수익률(Hit Rate) 1등은 위험합니다(Overfitting). 우리는 '주변 파라미터와 비슷한 성능을 내는가?'를 봅니다.
$$ Stability = \mu(HitRate) - \sigma(HitRate) $$
평균 성능이 높으면서 변동성이 낮은 **Golden Parameter**를 선택합니다.

---

# Part 4: 운영과 진화

## 10. 🖥️ 프론트엔드 아키텍처: Glassmorphism & Chart.js

### 💎 Glassmorphism Design
현대적인 금융 대시보드를 위해 **Glassmorphism (유리 질감)** UI를 채택했습니다.
- **CSS 기법**: `backdrop-filter: blur(12px)`와 반투명 `rgba` 배경색을 조합하여 데이터가 배경 위에 떠 있는 듯한 깊이감(Depth)을 줍니다.
- **UX 철학**: 복잡한 금융 데이터를 눈의 피로 없이 오래 볼 수 있도록 다크 모드와 네온 컬러(Lucide Icons)를 조합했습니다.

### 📊 Chart.js Multi-Axis
- **재무 차트**: 주가(Bar)와 PER/PBR(Line)은 스케일이 다릅니다. 이중 Y축(Dual Y-Axis)을 구현하여 서로 다른 단위의 지표를 하나의 차트에서 직관적으로 비교합니다.

---

## 11. 🛣️ 31단계 개발 히스토리 (Evolutionary Roadmap)

### MVP 단계 (P1-P5)
- **P1**: `datetime_helper` 구현. 시계열 데이터의 기준점 확립.
- **P4**: Time Decay 초기 모델 적용.

### 자동화 및 최적화 (P6-P15)
- **P6**: `MasterOrchestrator` 도입. 수집-학습-예측 프로세스 자동 연결.
- **P9**: **Ordered Lasso** 도입. 시간 순서를 고려한 정규화.
- **P14**: 뉴스 중복 제거 로직(URL Hash) 구현. 데이터 무결성 확보.

### 인프라 확장 (P16-P25)
- **P17**: RabbitMQ 큐 분리 (`verification_daily` vs `jobs`). 긴급 작업과 배치 작업 격리.
- **P21**: Grafana 4x4 그리드 대시보드 구축. 시스템 가시성 확보.

### 지능화 및 고도화 (P26-P31)
- **P26**: Gap Detection & One-Click Backfill. 운영 편의성 극대화.
- **P29**: **MLX & Celer** 도입. 학습 속도 100배 향상.
- **P31**: 레거시 파일 아카이빙 및 코드베이스 안정화.

> [!IMPORTANT]
> **교훈**: 이 로드맵은 MVP에서 출발하여 OOM, 속도 저하, 좀비 워커 등 실제 운영 이슈를 하나씩 해결해온 **"살아있는 기록"**입니다.

---

## 12. 🔄 상세 운영 프로세스 및 좀비 워커 관리

### 🧟‍♂️ 좀비 워커(Zombie Worker) 탐지 시스템
분산 환경에서 워커가 조용히 죽는 문제(Silent Fail)를 해결하기 위해 **Heartbeat 패턴**을 구현했습니다.
1. **Pulse**: 모든 워커는 30초마다 Redis/DB에 생존 신고를 보냅니다.
2. **Monitor**: 모니터링 서비스가 90초 이상 신고가 없는 워커를 감지합니다.
3. **Alert**: Grafana 대시보드에 적색 경보를 띄우고 관리자에게 알림을 보냅니다.

---

## 13. 📊 주요 메트릭 및 성과 지표

| Metric | Value | Description |
|--------|-------|-------------|
| **Hit Rate** | **53.5% ~ 58.2%** | AWO 최적화 및 종목별 변동성에 따라 상이함. |
| **Data Cleaning** | **45%** | BERT 요약 및 필터링을 통해 제거된 노이즈 비율. |
| **Inference Latency** | **< 0.2s** | 사전 학습된 계수(Coefficient)를 활용한 초고속 연산. |
| **Training Speed** | **~10 min** | MLX/Celer 가속 적용 시 (10만 건 기준). |

---

## 14. 🚀 시작하기 및 개발자 가이드

### ⚙️ 시스템 설치
```bash
# 1. 환경 설정
cp .env.sample .env

# 2. 실행 (Docker Compose)
docker-compose up -d --build

# 3. 데이터 동기화 (필수)
docker exec -it n_senti_dashboard python -m src.scripts.sync_stock_master
```

### 👨‍💻 학습 제언
1.  `src/learner/lasso.py`에서 `alpha` 값을 변경하며 단어 사전의 변화(Sparsity)를 관찰해보십시오.
2.  `src/nlp/tokenizer.py`에서 N-gram 설정을 1, 2, 3으로 바꿔가며 메모리 사용량을 비교해보십시오.

---

## 15. ⚠️ 향후 과제 (Future Work)
- **Quantization**: BERT 모델의 양자화를 통해 추론 속도를 더욱 개선해야 합니다.
- **Transformer-based Prediction**: 선형 모델의 한계를 넘어, 문맥을 더 깊이 이해하는 Transformer 기반 예측 모델과의 앙상블이 필요합니다.

---

# Appendix A: Code Gallery (Implementation Details)

백서에서 설명한 핵심 로직의 실제 구현체(Implementation Snippets)입니다.

### 1. Stability Score Calculation (AWO 엔진)
단순 수익률이 아닌, '안정성'을 평가하는 수식의 Python 구현입니다.
```python
def calculate_stability_score(results):
    """
    안정성 점수 = (0.6 * 평균 수익률) + (0.4 * (1 - 정규화된 MAE)) - (1.0 * 수익률 표준편차)
    """
    mean_hit_rate = np.mean([r['hit_rate'] for r in results])
    std_hit_rate = np.std([r['hit_rate'] for r in results])
    norm_mae = normalize_mae([r['mae'] for r in results])
    
    # 표준편차에 패널티(1.0)를 강하게 부여하여 '들쭉날쭉한' 모델을 탈락시킴
    stability_score = (0.6 * mean_hit_rate) + (0.4 * (1 - norm_mae)) - (1.0 * std_hit_rate)
    return stability_score
```

### 2. Gap Detection Query (데이터 인텔리전스)
거래일(Trading Day) 대비 뉴스 수집량이 0인 날짜를 찾아내는 로직입니다.
```sql
-- "거래일인데 뉴스가 하나도 없는 날" 찾기
SELECT 
    m.date as trading_date 
FROM 
    market_calendar m 
LEFT JOIN 
    news_count n ON m.date = n.date 
WHERE 
    m.is_market_open = true 
    AND n.count IS NULL; 
-- 결과: 2024-12-25 (크리스마스 누락 확인 -> 자동 백필 트리거)
```

### 3. FISTA Algorithm (MLX 가속)
Scikit-learn의 단점을 극복하기 위해 MLX로 구현한 **고속 반복 수축-임계 알고리즘**입니다.
```python
def lasso_fista(X, y, alpha, max_iter=1000):
    # MLX(GPU) Tensor로 변환 (Zero-copy)
    w = mx.zeros(X.shape[1])
    t = 1.0
    
    for _ in range(max_iter):
        # 1. Gradient Descent Step
        w_prev = w
        grad = X.T @ (X @ w - y)
        w_t = w - learning_rate * grad
        
        # 2. Proximal Step (Soft Thresholding) -> L1 규제 적용
        # 작은 가중치를 0으로 만드는 핵심(Sparsity) 단계
        w = mx.sign(w_t) * mx.maximum(mx.abs(w_t) - alpha * learning_rate, 0)
        
        # 3. FISTA Acceleration (Momentum)
        t_next = (1 + mx.sqrt(1 + 4 * t**2)) / 2
        w = w + ((t - 1) / t_next) * (w - w_prev)
        t = t_next
    return w
```

---

# Appendix B: Advanced Troubleshooting

운영 중 발생할 수 있는 주요 장애와 해결 가이드입니다.

### Q1. "메모리 부족(OOM)으로 컨테이너가 죽습니다."
*   **원인**: 12개월 이상의 뉴스(수십 기가바이트)를 한 번에 `Lasso`에 밀어넣었을 때 발생.
*   **1단계 해결**: `docker-compose.yml`에서 Redis/Postgres 메모리 제한 확인.
*   **2단계 해결**: `src/learner/config.py`에서 `MAX_FEATURES`를 15,000으로 하향 조정. (성능 영향 미미함)
*   **3단계 해결**: `BATCH_SIZE` 변수를 통해 시계열 데이터를 3개월 단위로 쪼개서 로딩(Chunk Loading).

### Q2. "일부 워커가 멈춰있는데 로그가 없습니다 (Zombie Worker)."
*   **진단**: RabbitMQ 관리자 페이지(15672 포트)에서 `Unacked` 메시지가 쌓여있는지 확인.
*   **해결**: 
    1.  `docker restart n_senti_collector_1` (강제 재시작)
    2.  `admin` 페이지에서 **"Purge Queue"** 실행하여 독성 메시지(Poison Message) 제거.
    3.  향후 방지: `heartbeat_monitor.py`가 자동으로 좀비 감지 후 Slack 알림을 보냅니다.

---

**N-SentiTrader**
*Code with Reason, Trade with Logic.*
