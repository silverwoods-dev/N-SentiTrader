# N-SentiTrader: 실무형 화이트박스 주식 예측 시스템 (Technical Bible)

[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Env](https://img.shields.io/badge/Env-uv-purple?logo=rust&logoColor=white)](https://github.com/astral-sh/uv)
[![Data](https://img.shields.io/badge/Data-Polars-CD792C?logo=polars&logoColor=white)](https://pola.rs/)
[![ML](https://img.shields.io/badge/ML-MLX-FF0000?logo=apple&logoColor=white)](https://github.com/ml-explore/mlx)
[![Frontend](https://img.shields.io/badge/Frontend-HTMX-black?logo=htmx&logoColor=white)](https://htmx.org/)
[![Docker](https://img.shields.io/badge/Docker-Container-blue?logo=docker&logoColor=white)](https://www.docker.com/)
[![DB](https://img.shields.io/badge/DB-PostgreSQL-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Queue](https://img.shields.io/badge/Queue-RabbitMQ-FF6600?logo=rabbitmq&logoColor=white)](https://www.rabbitmq.com/)
[![Monitoring](https://img.shields.io/badge/Monitoring-Prometheus-E6522C?logo=prometheus&logoColor=white)](https://prometheus.io/)
[![Viz](https://img.shields.io/badge/Viz-Grafana-F46800?logo=grafana&logoColor=white)](https://grafana.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

## 🎓 훈련생을 위한 기술 총서 (The Ultimate Technical Bible)

> <b>[프로젝트 선언]</b>
> 본 문서는 단순한 "사용 설명서"가 아닙니다. AI 서비스 개발자 양성과정의 훈련생들이 <b>금융 도메인의 규제(Compliance)</b>, <b>대규모 데이터 처리의 병목(Bottleneck)</b>, <b>하드웨어 가속의 원리(Acceleration)</b>, 그리고 <b>모던 인프라의 철학(Infrastructure)</b>을 깊이 있게 이해할 수 있도록 설계된 <b>'기술 백서(Technical Whitepaper)'</b>입니다.
>
> 우리는 "결과"보다 "과정"을, "코드"보다 "설계의 이유"를 설명합니다.

---

## 📋 목차 (Table of Contents)

### Part 1: 철학과 아키텍처 (Philosophy & Architecture)
1.  [🏛️ 왜 화이트박스(White-Box)인가? (XAI와 법적 근거)](#1-왜-화이트박스white-box인가-xai와-법적-근거)
2.  [⚙️ 기술 스택 및 마이크로서비스(MSA) 설계](#2-기술-스택-및-마이크로서비스msa-설계)
3.  [📊 시스템 아키텍처 및 데이터 흐름도](#3-시스템-아키텍처-및-데이터-흐름도)

### Part 2: 인프라 엔지니어링 (Infrastructure Engineering)
4.  [⚡ The uv Revolution: 차세대 패키지 관리 혁명](#4-the-uv-revolution-차세대-패키지-관리-혁명)
5.  [🐳 Container Orchestration: 17개 컨테이너의 토폴로지](#5-container-orchestration-17개-컨테이너의-토폴로지)

### Part 3: 데이터 인텔리전스 (Data Intelligence)
6.  [🛡️ 데이터 수집 및 지능형 필터링 전략 (Smart Filtering)](#6-데이터-수집-및-지능형-필터링-전략-smart-filtering)
7.  [🧠 Deep Dive: 지능형 차원 축소 (Dimensionality Reduction by Intelligence)](#7-deep-dive-지능형-차원-축소-dimensionality-reduction-by-intelligence)

### Part 4: 사이언스 엔지니어링 (Scientific Engineering)
8.  [🔬 Deep Dive: 워크플로우 최적화 (Memory & Metrics)](#8-deep-dive-워크플로우-최적화-memory--metrics)
9.  [🚀 Deep Dive: 하드웨어 가속 (MLX & Celer)](#9-deep-dive-하드웨어-가속-mlx--celer)
10. [⚖️ Deep Dive: 하이브리드 앙상블 아키텍처 (Hybrid Ensemble)](#10-deep-dive-하이브리드-앙상블-아키텍처-hybrid-ensemble)
11. [🧬 AWO 엔진: 시장의 비정상성 대응과 안정성 점수](#11-awo-엔진-시장의-비정상성-대응과-안정성-점수)

### Part 5: 모던 프론트엔드 엔지니어링 (Modern Frontend)
12. [🌐 Hypermedia Systems: React 없는 반응형 웹 (HTMX)](#12-hypermedia-systems-react-없는-반응형-웹-htmx)
13. [💎 Glassmorphism UI: 금융 대시보드의 미학](#13-glassmorphism-ui-금융-대시보드의-미학)

### Part 6: 옵저버빌리티와 데브옵스 (Observability & DevOps)
14. [🔭 Prometheus & cAdvisor: 풀스택 모니터링](#14-prometheus--cadvisor-풀스택-모니터링)
15. [🧟 좀비 워커(Zombie Worker) 탐지 및 자가 치유](#15-좀비-워커zombie-worker-탐지-및-자가-치유)

### Part 7: 역사와 운영 (History & Operations)
16. [🛣️ 31단계 개발 히스토리 (The Evolution)](#16-31단계-개발-히스토리-the-evolution)
17. [📊 주요 메트릭 및 성과 지표](#17-주요-메트릭-및-성과-지표)
18. [🚀 시작하기 및 개발자 가이드](#18-시작하기-및-개발자-가이드)

### Appendices (부록)
*   [Appendix A: Code Gallery](#appendix-a-code-gallery)
*   [Appendix B: Troubleshooting](#appendix-b-troubleshooting)

---

# Part 1: 철학과 아키텍처 (Philosophy & Architecture)

## 1. 🏛️ 왜 화이트박스(White-Box)인가? (XAI와 법적 근거)

### 🧐 배경: 금융권의 '설명 책임' (Accountability)
최근 LLM(GPT-4 등)이 등장했음에도 불구하고, 실무 금융권에서 선형 모델 기반의 화이트박스를 고집하는 이유는 기술적 한계 때문이 아닌, <b>'법적 생존'</b> 때문입니다. 수천억 원의 자산을 운용하는 알고리즘이 "왜?"라는 질문에 답하지 못한다면, 그것은 기술이 아니라 '도박'입니다.

#### 📜 법적 근거 (Legal Basis)
1.  <b>EU AI Act (2024)</b>: 고위험(High-risk) AI 시스템, 특히 신용 평가 및 금융 서비스에 대해 <b>"해석 가능성(Interpretability)"</b>과 <b>"추적 가능성(Traceability)"</b>을 강력하게 의무화했습니다. 블랙박스 모델은 규제 준수 비용을 기하급수적으로 높입니다.
2.  <b>GDPR 제13조-14조</b>: 정보 주체는 자동화된 의사 결정에 대해 <b>"유의미한 정보(Meaningful Information)"</b>를 제공받을 권리가 있습니다. "딥러닝 가중치가 그렇다"는 설명은 법적으로 유효하지 않습니다.
3.  <b>ECOA (미국 평등신용기회법)</b>: 대출 거절 시 <b>구체적인 사유(Adverse Action)</b>를 명시해야 합니다. (예: "소득 대비 부채 비율 과다" vs "모델 점수 0.3 미달")

### ✅ 화이트박스(Lasso) vs. 블랙박스(LLM) 비교

| 구분 | 화이트박스 (본 프로젝트) | 블랙박스 (딥러닝/LLM) | 비고 |
|------|-------------------------|-------------------|------|
| <b>해석 가능성</b> | <b>✅ 완전 투명</b> (Feature Importance 직접 확인) | ❌ 불투명 (Black-box) | 규제 대응 핵심 |
| <b>학습 제어</b> | <b>✅ 특성 공학(Feature Engineering) 통제 가능</b> | ❌ 데이터 통제 어려움 (Hallucination) | 신뢰성 |
| <b>인프라</b> | <b>✅ CPU/MPS (MacBook Air 구동 가능)</b> | ❌ 고성능 H100 GPU 필수 | 비용 효율성 |
| <b>데이터 보안</b> | <b>✅ 100% On-premise (폐쇄망)</b> | ❌ 클라우드 API 전송 (정보 유출 위험) | 보안성 |

> [!TIP]
> <b>초보 개발자를 위한 팁</b>: 딥러닝은 'What(결과)'을 잘 맞추지만 'Why(이유)'를 설명하지 못합니다. 금융, 의료, 법률 등 <b>책임이 따르는 도메인</b>에서는 설명 가능한 선형 모델이 여전히 강력한 주무기입니다.

---

## 2. ⚙️ 기술 스택 및 마이크로서비스(MSA) 설계

### 🛠️ 코어 기술 스택 (Technology Stack Table)
본 프로젝트는 <b>최신 기술(State-of-the-Art)</b>과 <b>안정성(Stability)</b>의 균형을 극대화했습니다.

| 영역 | 기술 | 선정 이유 (Engineering Decision) |
|------|------|--------------------------------|
| <b>코어 언어</b> | <b>Python 3.12</b> | 최신 CPython의 JIT 컴파일러 도입 준비 및 비동기(`asyncio`) 성능 최적화 버전을 채택했습니다. (3.11 대비 최대 10% 성능 향상) |
| <b>패키지 관리</b> | <b>uv</b> (by Astral) | 기존 `pip`/`poetry` 대비 <b>100배 빠른 설치 속도</b>. Rust로 작성되어 메모리 안전성을 보장하며, `uv sync`를 통한 <b>결정론적 의존성(Deterministic Dependency)</b> 관리를 실현합니다. |
| <b>데이터 처리</b> | <b>Polars</b> | <b>Rust</b> 기반의 병렬 데이터프레임 라이브러리. Pandas 대비 메모리 사용량 1/5, 속도 10배 이상 빠름 (Zero-copy). 대용량 시계열 뉴스 처리에 필수적입니다. |
| <b>ML 엔진</b> | <b>Lasso (MLX/Celer)</b> | 좌표 하강법(Coordinate Descent)의 병렬화 한계를 극복하기 위해 <b>Celer (Working Set)</b> 및 <b>MLX (Apple GPU)</b> 가속을 도입했습니다. |
| <b>프론트엔드</b> | <b>HTMX</b> | React/Vue의 복잡한 빌드 과정 없이 HTML 속성(`hx-get`)만으로 SPA 수준의 인터랙션을 구현하는 <b>Hypermedia-Driven</b> 아키텍처를 채택했습니다. |
| <b>메시지 큐</b> | <b>RabbitMQ</b> | <b>느슨한 결합(Decoupling)</b> 및 <b>배압 조절(Backpressure)</b>. 뉴스 트래픽 폭주 시 서버 다운을 막고 큐에 쌓아두는 완충 장치 역할. |
| <b>모니터링</b> | <b>Prometheus + Grafana</b> | 단순 로그 수집이 아닌, 시계열 메트릭(TSDB) 기반의 풀스택 옵저버빌리티(Observability)를 구축했습니다. |

---

## 3. 📊 시스템 아키텍처 및 데이터 흐름도

시스템은 5개의 독립된 레이어와 17개의 Docker 컨테이너로 구성됩니다.

```mermaid
graph TD
    subgraph "External_World"
        Naver["Naver News API"]
        KRX["KRX Market Data"]
    end

    subgraph "Ingestion_Layer"
        Disc["Discovery Service"] --> |Schedule| Coll["Collector Workers"]
        Coll --> |RabbitMQ| MQ[("Message Queue")]
    end

    subgraph "Brain_Layer"
        MQ --> Pre["Preprocessor"]
        Pre --> NLP["BERT Summarizer"]
        NLP --> Train["Lasso Learner (MLX)"]
        Train --> Predict["Predictor Engine"]
    end

    subgraph "Persistence_Layer"
        Train --> DB[("PostgreSQL")]
        Predict --> DB
        DB --> Cache[("Redis/Local Cache")]
    end

    subgraph "Visualization"
        DB --> Dash["Expert Dashboard (FastAPI)"]
        DB --> Cadvisor["cAdvisor"]
        Cadvisor --> Prom["Prometheus"]
        Prom --> Grafana["Grafana Monitoring"]
    end
```

---

# Part 2: 인프라 엔지니어링 (Infrastructure Engineering)

## 4. ⚡ The uv Revolution: 차세대 패키지 관리 혁명

### Why uv?
전통적인 `pip`는 느리고, 의존성 충돌(Dependency Hell)에 취약합니다. 우리는 <b>Rust</b>로 작성된 혁신적인 패키지 매니저 `uv`를 전면 도입했습니다.

### 🔒 Docker 컨테이너 내 격리 전략
모든 `Dockerfile`은 `uv run`을 강제합니다.
```dockerfile
# Dockerfile snippet
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache  # 락파일 기반의 엄격한 동기화
CMD ["uv", "run", "python", "main.py"]  # 가상환경 자동 활성화 및 실행
```
- <b>System Python 보호</b>: 컨테이너의 시스템 파이썬(apt로 설치된 패키지들)과 프로젝트 의존성을 완벽하게 격리합니다.
- <b>Lockfile Integrity</b>: `uv.lock` 파일이 모든 패키지의 버전과 해시값을 고정하므로, "내 컴퓨터에선 되는데 서버에선 안 되는" 문제가 원천 차단됩니다.

## 5. 🐳 Container Orchestration: 17개 컨테이너의 토폴로지

`docker-compose.yml`은 단순한 실행 스크립트가 아닌, <b>인프라 토폴로지(Topology)</b>를 정의합니다.

### 🌐 네트워크 격리 (Network Isolation)
- <b>Backend Network</b>: DB, Redis, RabbitMQ는 외부 인터넷과 단절된 내부 네트워크에서만 통신합니다. (보안)
- <b>Monitoring Network</b>: Prometheus와 Grafana는 별도의 네트워크 브리지로 연결되어 운영 트래픽과 모니터링 트래픽을 분리합니다.

### 💾 볼륨 전략 (Data Persistence)
- `n_sentitrader_db_data`: PostgreSQL 데이터 영속성 보장.
- `./src:/app/src`: 개발 시 코드 변경 사항이 컨테이너 재시작 없이 즉시 반영되는 <b>Hot Reloading</b> 환경 구축 (개발 생산성 증대).

---

# Part 3: 데이터 인텔리전스 (Data Intelligence)

## 6. 🛡️ 데이터 수집 및 지능형 필터링 전략 (Smart Filtering)

### 📡 지능형 공백 탐지 (Gap Detection)
단순한 크롤링이 아닙니다. 시스템은 <b>'데이터의 연속성'</b>을 스스로 감시합니다. `Trading Calendar`와 `DB Count`를 교차 검증하여, 시장이 열렸는데 수집된 뉴스가 0건인 날짜를 <b>'Gap'</b>으로 규정하고 즉시 경보를 울립니다.

### 🎯 종목별 정밀 필터링 (Relevance Scoring Formula)
"삼성전자" 검색어에 "삼성전자 냉장고 출시" 기사가 섞이면 주가 예측은 망가집니다. 우리는 <b>지능형 스코어링</b>을 통해 노이즈를 1차적으로 걸러냅니다. (참고: `src/analysis/news_filter.py`)

```mermaid
flowchart TD
    Raw["Raw News"] --> Title{"Title Match?"}
    Title -->|Yes| Score1["Score + 40"]
    Title -->|No| Para{"Lead Para Match?"}
    Para -->|Yes| Score2["Score + 30"]
    Para -->|No| Density{"Density Check"}
    Score1 --> Sum["Total Score"]
    Score2 --> Sum
    Density --> Sum
    Sum --> Decision{"Score > 50?"}
    Decision -->|Yes| Accept["Training Data"]
    Decision -->|No| Reject["Noise"]
```

### 가중치 테이블
| 필터링 항목 | 가중치 | 상세 설명 |
|------|---|---|
| <b>Title Match</b> | <b>0.4</b> | 헤드라인에 종목명이 있는가? (가장 강력한 시그널) |
| <b>First Para</b> | <b>0.3</b> | 기사의 첫 문단(리드문)에 종목명이 등장하는가? |
| <b>Density</b> | <b>0.3</b> | 본문 전체 대비 종목명 언급 빈도 (노이즈 판별) |

$$
Score = (0.4 \times Title) + (0.3 \times Lead) + (0.3 \times Density)
$$

---

## 7. 🧠 Deep Dive: 지능형 차원 축소 (Dimensionality Reduction by Intelligence)

### 🚨 파라미터 폭발(Parameter Explosion)의 진짜 해결책
N-gram(1 .. 3)과 Lag(1 .. 5)를 사용하면 피처의 개수는 수백만 개로 늘어납니다(`features > 1,000,000`). 일반적인 방법은 "N-gram을 2로 줄이자"는 식의 물리적 축소입니다.

하지만 본 프로젝트는 <b>"데이터의 지능"</b>을 이용해 차원을 축소합니다.

### A. 입력 공간의 가지치기 (Input Space Pruning)
단순히 사전 크기를 줄이는 것이 아니라, <b>'모델이 읽어야 할 텍스트의 양'</b> 자체를 줄입니다.
- **Filter First**: 위에서 언급한 Relevance Score로 관련 없는 기사를 아예 버립니다.
- **Summarize Second**: `KR-FinBERT`를 이용해 기사 원문의 상위 3문장만 추출합니다.

### B. BERT 추출 요약의 마법 (Summarization as Compression)
기사 전체(약 2,000자)를 학습하면 불필요한 조사와 부사가 노이즈로 작용합니다.
- **Extraction**: BERT 임베딩 공간에서 문서 중심(Centroid)과 가장 가까운 문장을 찾습니다.
- **Effect**: 정보량(Embedding Distance)은 보존하면서 텍스트 길이(Length)는 1/10로 줄어듭니다.
- **결과**: `vocab_size`를 억지로 줄이지 않아도, 자연스럽게 유의미한 단어들만 남게 되어 <b>희소 행렬(Sparse Matrix)의 품질</b>이 비약적으로 상승합니다. 이것이 바로 <b>"지능형 차원 축소"</b>입니다.

---

# Part 4: 사이언스 엔지니어링 (Scientific Engineering)

## 8. 🔬 Deep Dive: 워크플로우 최적화 (Memory & Metrics)

초기 모델은 12개월 데이터를 학습할 때 <b>OOM(Out of Memory)</b>이 발생했습니다. 철저한 프로파일링을 통해 다음과 같은 최적화를 수행했습니다.

| 최적화 항목 | 변경 전 (Before) | 변경 후 (After) | 개선 효과 | 근거 (Rationale) |
|------------|-----------------|-----------------|-----------|------------------|
| <b>Max Features</b> | 50,000개 | **15,000개** | 메모리 60% 절감 | 학술 연구상 8,000개 이상에서 성능 포화 (Diminishing Returns) |
| <b>N-gram</b> | (1, 3) | **(1, 2)** | 특성 수 40% 감소 | BERT 요약으로 핵심 문장만 남겼기에 Trigram의 효용이 감소함 |
| <b>Lags</b> | 5일 | **3일** | 특성 수 40% 감소 | 금융 정보의 유효 반감기는 통상 3일 이내 (Efficient Market) |
| <b>Min DF</b> | 3 | **5** | 노이즈 대폭 감소 | 5개 미만 문서에 등장하는 단어는 통계적 유의성이 없음 |

---

## 9. 🚀 Deep Dive: 하드웨어 가속 (MLX & Celer)

Apple Silicon(M1/M2/M3)의 성능을 100% 끌어내기 위해 Scikit-learn을 버리고 고성능 엔진을 도입했습니다.

### A. MLX (Apple Silicon Native) - 'Unified Memory'의 승리
- **Zero-Copy**: 기존 CUDA 방식은 CPU $\to$ GPU로 데이터를 복사하는 오버헤드가 큽니다. Apple Unified Memory는 CPU와 GPU가 메모리를 공유하므로 복사가 <b>"0"</b>입니다.
- **FISTA 알고리즘**: L1 규제항(미분 불가능)을 해결하기 위해 <b>FISTA(Fast Iterative Shrinkage-Thresholding Algorithm)</b>를 직접 구현하여 GPU 병렬 처리를 극대화했습니다.

### B. Celer (Working Set Algorithm)
- **Active Set**: 수만 개의 단어 중 실제 가중치가 0이 아닌 단어는 수백 개뿐입니다. Celer는 이 '후보군'만 골라내어 연산하므로 Scikit-learn 대비 <b>50배</b> 빠릅니다.

---

## 10. ⚖️ Deep Dive: 하이브리드 앙상블 아키텍처 (Hybrid Ensemble)

단일 모델의 한계를 넘기 위해 <b>두 가지 두뇌</b>를 결합했습니다. (참고: `src/learner/hybrid_predictor.py`)

```mermaid
flowchart TD
    News["Input News"] --> Filter["Smart Filter"]
    Filter --> CleanNews["Clean News"]
    
    CleanNews --> TFIDF["TF-IDF Vectorizer"]
    CleanNews --> BERT["BERT Embedder"]
    
    TFIDF --> Lasso["Lasso Model"]
    BERT --> Ridge["Ridge Model"]
    
    Lasso --> Pred1["Score A (60%)"]
    Ridge --> Pred2["Score B (40%)"]
    
    Pred1 --> Ensemble(("Weighted Sum"))
    Pred2 --> Ensemble
    Ensemble --> Final["Final Prediction"]
```

### 🧠 Model A: TF-IDF Lasso (The Analyst)
- **역할**: "어떤 단어가 중요한가?" (Feature Selection)
- **특징**: 설명 가능성(Explainability)이 매우 높음. 과적합에 강함.
- **가중치**: <b>60%</b>

### 🧠 Model B: BERT Ridge (The Reader)
- **역할**: "문맥의 뉘앙스는 어떠한가?" (Context Awareness)
- **특징**: `KR-FinBERT`의 임베딩 벡터를 사용하여 단어 간의 복잡한 관계를 이해함.
- **가중치**: <b>40%</b>

### 🤝 앙상블 결합 (Weighted Fusion)
$$
P_{final} = (0.6 \times P_{Lasso}) + (0.4 \times P_{BERT}) + \alpha_{adjustment}
$$
이 구조는 Lasso의 <b>설명력</b>과 BERT의 <b>문맥 이해력</b>을 동시에 취하며, 단일 모델 대비 Hit Rate를 약 5~8%p 향상시켰습니다.

---

## 11. 🧬 AWO 엔진: 시장의 비정상성 대응과 안정성 점수

금융 시장은 끊임없이 변합니다(<b>Non-stationarity</b>). 영원한 승리 전략은 없습니다.

### 🎯 Adaptive Window Optimization (AWO-2D)
매주 토요일 새벽, 시스템은 수만 가지 파라미터 조합(Window Size x Alpha)을 시뮬레이션(Walk-forward)하여 <b>"지금 이 순간 시장에 가장 잘 맞는 설정"</b>을 찾습니다.

### 📐 안정성 점수 (Stability Score)
단순 수익률 1등은 위험합니다. 우리는 '주변 파라미터와 비슷한 성능을 내는가?'를 봅니다.
$$
Stability = \mu(HitRate) - \sigma(HitRate) + (1 - Norm.MAE)
$$
평균 성능이 높으면서 변동성이 낮은 <b>Golden Parameter</b>를 선택합니다.

---

# Part 5: 모던 프론트엔드 엔지니어링 (Modern Frontend)

## 12. 🌐 Hypermedia Systems: React 없는 반응형 웹 (HTMX)

### Why No React?
금융 대시보드는 SEO가 중요하고 초기 로딩이 빨라야 합니다. React/Vue의 무거운 번들링(Webpack/Vite)은 유지보수 비용을 높입니다.

### HTMX 철학: Locality of Behavior (LoB)
우리는 HTML 태그 자체가 행동을 정의하게 했습니다.
```html
<!-- 실제 코드 스니펫 -->
<div hx-get="/analytics/top-signals" 
     hx-trigger="load, every 30s" 
     hx-target="#signal-container">
</div>
```
- **hx-get**: 서버에 데이터를 요청합니다.
- **hx-trigger**: 페이지 로드 시, 그리고 매 30초마다(실시간성).
- **hx-target**: 응답받은 HTML 조각(Fragment)을 이 `div` 안에 끼워 넣습니다.
자바스크립트 한 줄 없이 <b>실시간 업데이트되는 대시보드</b>를 구현했습니다.

## 13. 💎 Glassmorphism UI: 금융 대시보드의 미학

### CSS Implementation
현대적인 Glassmorphism(유리 질감)을 위해 `backdrop-filter` 기술을 사용했습니다.
```css
.glass-panel {
    background: rgba(255, 255, 255, 0.05);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.1);
}
```
이는 데이터가 배경 위에 떠 있는 듯한 깊이감(Depth)을 주어, 장시간 모니터링에도 눈의 피로를 줄여줍니다.

---

# Part 6: 옵저버빌리티와 데브옵스 (Observability & DevOps)

## 14. 🔭 Prometheus & cAdvisor: 풀스택 모니터링

### Architecture
단순히 "서버가 켜졌나"만 보지 않습니다. 우리는 <b>TSDB(Time Series Database)</b>를 통해 시스템의 맥박을 기록합니다.
1.  **cAdvisor**: 17개 도커 컨테이너의 CPU, Memory, Network I/O를 초 단위로 수집합니다.
2.  **Prometheus**: 수집된 메트릭을 Scraping하여 저장합니다.
3.  **Grafana**: PromQL을 사용하여 실시간 대시보드(4x4 Grid)를 렌더링합니다.

### Custom Metrics
Python 애플리케이션 내부에서도 커스텀 메트릭을 노출합니다.
- `news_collected_total`: 수집된 뉴스 수
- `prediction_latency_seconds`: 추론 소요 시간
- `model_training_loss`: 학습 손실값

## 15. 🧟 좀비 워커(Zombie Worker) 탐지 및 자가 치유

분산 환경의 최대 적은 "조용히 죽은 워커(Silent Failure)"입니다.

### Heartbeat Pattern
1. **Pulse**: 모든 워커는 30초마다 Redis 키(`worker:heartbeat:{id}`)를 갱신합니다.
2. **Monitor**: 별도의 감시 프로세스가 90초(`TTL * 3`) 이상 갱신되지 않은 키를 찾습니다.
3. **Action**: 좀비 워커 발견 시 즉시 슬랙 알림을 보내고, 필요시 Docker API를 통해 해당 컨테이너를 재시작(Restart)합니다.

---

# Part 7: 역사와 운영 (History & Operations)

## 16. 🛣️ 31단계 개발 히스토리 (The Evolution)

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

---

## 17. 📊 주요 메트릭 및 성과 지표

| Metric | Value | Description |
|--------|-------|-------------|
| <b>Hit Rate</b> | **53.5% \~ 58.2%** | 하이브리드(Lasso+BERT) 앙상블 적용 시 단일 모델 대비 약 5%p 상승. |
| <b>Data Cleaning</b> | **45%** | 지능형 필터링 및 BERT 요약을 통해 제거된 노이즈 비율. |
| <b>Inference Latency</b> | **< 0.2s** | 사전 학습된 계수(Coefficient)를 활용한 초고속 연산. |
| <b>Training Speed</b> | **\~10 min** | MLX/Celer 가속 적용 시 (10만 건 뉴스 기준). |

---

## 18. 🚀 시작하기 및 개발자 가이드

### ⚙️ 시스템 설치
```bash
# 1. 환경 설정
cp .env.sample .env

# 2. 실행 (Docker Compose)
# uv 및 Python 3.12 이미지가 자동으로 빌드됩니다.
docker-compose up -d --build

# 3. 데이터 동기화 (필수)
# KRX 종목 마스터 및 사용자 사전을 초기화합니다.
docker exec -it n_senti_dashboard uv run python -m src.scripts.sync_stock_master
```

### 👨‍💻 학습 제언
1.  `src/learner/hybrid_predictor.py`에서 `tfidf_weight`와 `bert_weight`를 변경하며 앙상블 효과를 체험해보십시오.
2.  `src/nlp/summarizer.py`의 요약 로직을 비활성화했을 때, 학습 메모리 사용량이 어떻게 폭증하는지 관찰해보십시오.

---

# Appendices (부록)

## Appendix A: Code Gallery

### 1. Stability Score Calculation (AWO 엔진)
```python
def calculate_stability_score(results):
    """안정성 점수 = (0.6 * 평균 수익률) + (0.4 * (1 - 정규화된 MAE)) - (1.0 * 수익률 표준편차)"""
    mean_hit_rate = np.mean([r['hit_rate'] for r in results])
    std_hit_rate = np.std([r['hit_rate'] for r in results])
    norm_mae = normalize_mae([r['mae'] for r in results])
    return (0.6 * mean_hit_rate) + (0.4 * (1 - norm_mae)) - (1.0 * std_hit_rate)
```

### 2. Gap Detection Query (데이터 인텔리전스)
```sql
SELECT m.date as trading_date 
FROM market_calendar m 
LEFT JOIN news_count n ON m.date = n.date 
WHERE m.is_market_open = true AND n.count IS NULL; 
-- 결과: 2024-12-25 (크리스마스 누락 확인 -> 자동 백필 트리거)
```

### 3. FISTA Algorithm (MLX 가속)
```python
def lasso_fista(X, y, alpha, max_iter=1000):
    w = mx.zeros(X.shape[1])
    t = 1.0
    for _ in range(max_iter):
        w_prev = w
        grad = X.T @ (X @ w - y)
        w_t = w - learning_rate * grad
        # Soft Thresholding
        w = mx.sign(w_t) * mx.maximum(mx.abs(w_t) - alpha * learning_rate, 0)
        # Momentum Step
        t_next = (1 + mx.sqrt(1 + 4 * t**2)) / 2
        w = w + ((t - 1) / t_next) * (w - w_prev)
        t = t_next
    return w
```

## Appendix B: Troubleshooting

### Q1. "메모리 부족(OOM)으로 컨테이너가 죽습니다."
*   <b>원인</b>: 12개월 이상의 뉴스(수십 기가바이트)를 한 번에 `Lasso`에 밀어넣었을 때 발생.
*   <b>해결</b>: `src/learner/config.py`에서 `MAX_FEATURES`를 15,000으로 하향 조정하고, `PART 3`의 지능형 필터링이 정상 작동하는지 로그를 확인하십시오.

### Q2. "일부 워커가 멈춰있는데 로그가 없습니다 (Zombie Worker)."
*   <b>해결</b>: RabbitMQ 관리자 페이지(15672 포트)에서 `Unacked` 메시지를 확인하고 `Purge Queue`를 실행하십시오. `heartbeat_monitor` 컨테이너가 실행 중인지 확인하십시오.

---

**N-SentiTrader**
*Code with Reason, Trade with Logic.*
