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

> **[프로젝트 선언]**
> 본 문서는 단순한 "사용 설명서"가 아닙니다. AI 서비스 개발자 양성과정의 훈련생들이 **금융 도메인의 규제(Compliance)**, **대규모 데이터 처리의 병목(Bottleneck)**, **하드웨어 가속의 원리(Acceleration)**, 그리고 **모던 인프라의 철학(Infrastructure)**을 깊이 있게 이해할 수 있도록 설계된 **'기술 백서(Technical Whitepaper)'**입니다.
>
> 우리는 "결과"보다 "과정"을, "코드"보다 "설계의 이유"를 설명합니다. 모든 챕터는 **"왜 이렇게 만들었는가?"**에 대한 치열한 고민의 기록입니다.

---

## 📋 목차 (Table of Contents)

### Part 1: 철학과 동기 (Philosophy & Motivation)
1.  [🏛️ 왜 화이트박스(White-Box)인가? (XAI와 법적 근거)](#1-왜-화이트박스white-box인가-xai와-법적-근거)
2.  [📉 왜 Lasso인가? (희소성의 미학)](#2-왜-lasso인가-희소성의-미학)
3.  [🧠 왜 뉴스 감성인가? (효율적 시장 가설과 정보 비대칭)](#3-왜-뉴스-감성인가-효율적-시장-가설과-정보-비대칭)

### Part 2: 기술 스택 (Technology Stack)
4.  [⚡ The uv Revolution: 차세대 패키지 관리 혁명](#4-the-uv-revolution-차세대-패키지-관리-혁명)
5.  [🐻 Polars vs Pandas: Zero-copy 데이터 처리](#5-polars-vs-pandas-zero-copy-데이터-처리)
6.  [🍎 MLX 가속: Apple Silicon의 잠재력 해방](#6-mlx-가속-apple-silicon의-잠재력-해방)

### Part 3: 데이터 파이프라인 (Data Pipeline)
7.  [🕷️ 뉴스 수집과 N:M 매핑의 딜레마](#7-뉴스-수집과-nm-매핑의-딜레마)
8.  [🛡️ 지능형 필터링: RelevanceScorer 알고리즘 상세](#8-지능형-필터링-relevancescorer-알고리즘-상세)
9.  [✂️ BERT 추출 요약 (NewsSummarizer): Centroid 기법](#9-bert-추출-요약-newssummarizer-centroid-기법)

### Part 4: 특성 공학 (Feature Engineering)
10. [🧮 TF-IDF Vectorization: N-gram(1,3) 전략](#10-tf-idf-vectorization-n-gram13-전략)
11. [⏳ 시차 효과 (Lag Features): 정보의 반감기](#11-시차-효과-lag-features-정보의-반감기)
12. [📉 동적 감쇠 (Dynamic Decay): 시간 가중치 로직](#12-동적-감쇠-dynamic-decay-시간-가중치-로직)
13. [🦢 Black Swan 필터링: 희귀 단어 보호](#13-black-swan-필터링-희귀-단어-보호)

### Part 5: 핵심 알고리즘 (Core Algorithms)
14. [📐 Lasso 회귀의 수학적 원리 (L1 Regularization)](#14-lasso-회귀의-수학적-원리-l1-regularization)
15. [⚡ Celer 엔진: Working Set 알고리즘](#15-celer-엔진-working-set-알고리즘)
16. [🚀 MLX 가속: Metal GPU 연산 구현](#16-mlx-가속-metal-gpu-연산-구현)
17. [⚖️ 하이브리드 앙상블 (Hybrid Ensemble): 6:4의 황금비](#17-하이브리드-앙상블-hybrid-ensemble-64의-황금비)

### Part 6: AWO 엔진 (Adaptive Window Optimization)
18. [🌊 시장의 비정상성 (Regime Shift) 대응](#18-시장의-비정상성-regime-shift-대응)
19. [🔍 2D Grid Search: Window x Alpha](#19-2d-grid-search-window-x-alpha)
20. [📏 안정성 점수 (Stability Score) 공식](#20-안정성-점수-stability-score-공식)
21. [🏆 자동 승격 (Promotion) 메커니즘](#21-자동-승격-promotion-메커니즘)

### Part 7: 메모리 최적화 (Memory Optimization)
22. [💥 OOM 사건 분석 (Case Study)](#22-oom-사건-분석-case-study)
23. [🚿 Generator Streaming: 버퍼 제거](#23-generator-streaming-버퍼-제거)
24. [🌳 Vocabulary Pruning: Min_df와 Max_df](#24-vocabulary-pruning-min_df와-max_df)
25. [📉 Max Features 최적화: 25,000의 법칙](#25-max-features-최적화-25000의-법칙)

### Part 8: 프론트엔드 (Frontend)
26. [🌐 HTMX: Hypermedia-Driven Architecture](#26-htmx-hypermedia-driven-architecture)
27. [💎 Glassmorphism UI: 금융 대시보드의 미학](#27-glassmorphism-ui-금융-대시보드의-미학)

### Part 9: 옵저버빌리티 (Observability)
28. [🔭 Prometheus & cAdvisor: 풀스택 모니터링](#28-prometheus--cadvisor-풀스택-모니터링)
29. [📊 Grafana 대시보드: 시계열 시각화](#29-grafana-대시보드-시계열-시각화)
30. [🧟 좀비 워커 탐지 및 자가 치유 (Self-Healing)](#30-좀비-워커-탐지-및-자가-치유-self-healing)

### Part 10: 운영 가이드 (Operations)
31. [🐳 Docker Compose 토폴로지 (17 Containers)](#31-docker-compose-토폴로지-17-containers)
32. [🔑 환경 변수 설정 (Configuration)](#32-환경-변수-설정-configuration)
33. [🚀 시작하기 (Getting Started)](#33-시작하기-getting-started)

### Appendices (부록)
*   [Appendix A: Code Gallery (Core Implementation)](#appendix-a-code-gallery-core-implementation)
*   [Appendix B: Troubleshooting (FAQ)](#appendix-b-troubleshooting-faq)
*   [Appendix C: Development History (31 Steps)](#appendix-c-development-history-31-steps)

---

# Part 1: 철학과 동기 (Philosophy & Motivation)

## 1. 🏛️ 왜 화이트박스(White-Box)인가? (XAI와 법적 근거)

### 🧐 딥러닝의 유혹과 한계
2024년 현재, AI라고 하면 누구나 Transformer, LLM, LSTM을 떠올립니다. "왜 구식 선형 회귀(Linear Regression)를 쓰나요?"라는 질문은 타당해 보입니다. 딥러닝은 비선형 패턴을 기가 막히게 찾아내고, 예측 성능도 일반적으로 더 높습니다. 하지만 **"금융(Finance)"**이라는 도메인에서는 이야기가 완전히 다릅니다.

### 📜 금융권의 '설명 책임' (Accountability)
수천억 원의 자산을 운용하는 알고리즘이 "왜?"라는 질문에 답하지 못한다면, 그것은 기술이 아니라 '도박'입니다. 실무에서는 다음과 같은 상황이 매일 발생합니다.
> **상황**: 모델이 "내일 삼성전자를 매수하세요"라고 추천했습니다. 펀드 매니저가 묻습니다. "**근거가 뭡니까?**"
>
> **Black-box (Deep Learning)**: "768차원 벡터 공간에서 3번째 레이어의 뉴런 활성화 값이 임계치 0.7을 넘었습니다."
> **White-box (Lasso)**: "최근 3일간 뉴스에서 '수주', '실적 개선', '외국인 매수'라는 키워드가 급증했고, 이 단어들은 과거 85% 확률로 주가 상승과 연관이 있었습니다."

어느 모델을 채택하시겠습니까? 답은 명확합니다.

#### ⚖️ 컴플라이언스와 법적 규제
단순히 설명하기 좋은 것을 넘어, 이제는 법이 강제하고 있습니다.

1.  **EU AI Act (2024)**:
    *   **High-risk AI Systems**: 신용 평가, 보험, 금융 투자는 '고위험' 시스템으로 분류됩니다.
    *   **Transparency Requirements**: 시스템은 사용자에게 "결과의 도출 과정"을 해석 가능한 형태로 제공해야 하며, 이를 위반할 경우 매출의 최대 7%까지 과징금이 부과될 수 있습니다.
2.  **GDPR (Article 13-15)**:
    *   **Right to explanation**: 정보 주체는 자동화된 의사결정의 논리를 알 권리가 있습니다. "알고리즘이 너무 복잡해서 설명할 수 없다"는 변명은 더 이상 통하지 않습니다.
3.  **ECOA (미국 평등신용기회법)**:
    *   대출 거절 시 **'Adverse Action Notice'**를 통해 구체적인 거절 사유(예: 소득 부족, 연체 이력)를 명시해야 합니다. 블랙박스 모델 점수만으로는 이 요건을 충족할 수 없습니다.

## 2. 📉 왜 Lasso인가? (희소성의 미학)

### 🔍 L1 Regularization: 0을 만드는 마법
일반적인 선형 회귀(OLS)나 Ridge 회귀(L2)는 모든 변수에 작은 가중치를 남겨둡니다 (0.0001 같은). 변수가 25,000개라면, 25,000개의 이유가 있는 셈입니다. 이는 인간이 이해할 수 없습니다.

반면, **Lasso (Least Absolute Shrinkage and Selection Operator)**는 가중치의 절댓값 합을 패널티로 사용합니다. 이 제약 조건은 기하학적으로 **마름모 꼴(Diamond shape)**을 그리며, 최적 해가 축(Axis) 위에 맺히게 만드는 성질이 있습니다.
즉, 중요하지 않은 변수의 가중치를 **완벽하게 0**으로 만듭니다.

### 📚 감성 사전의 자동 생성
Lasso를 학습시키면 25,000개의 단어 중 약 100~300개만 남고 나머지는 모두 삭제됩니다.
- `+0.34`: "수주"
- `+0.21`: "흑자전환"
- `-0.45`: "피소"
- `-0.12`: "유상증자"

이 남은 단어 목록 자체가 훌륭한 **Domain-specific Sentiment Dictionary**가 됩니다. 우리는 이것을 "설명력(Explainability)"이라고 부릅니다.

## 3. 🧠 왜 뉴스 감성인가? (효율적 시장 가설과 정보 비대칭)

### 📈 Efficient Market Hypothesis (EMH)
효율적 시장 가설에 따르면, "공개된 모든 정보는 즉시 가격에 반영된다"고 합니다. 그렇다면 뉴스를 보고 매매하는 것은 이미 늦은 게 아닐까요?
- **강형(Strong) EMH**: 내부 정보까지 반영됨. (초과 수익 불가능)
- **준강형(Semi-strong) EMH**: 공개 정보 반영됨. (기술적 분석 무용지물)
- **약형(Weak) EMH**: 과거 가격 정보 반영됨.

### ⚡ 정보 확산의 지연 시간 (Latency Arbitrage)
현실의 시장은 완벽하게 효율적이지 않습니다. 뉴스가 '발행'된 시점과 대중이 이를 '인식'하고 '매매'에 나서는 시점 사이에는 미세한 시차가 존재합니다.
- **기계의 속도 vs 인간의 속도**: 인간 트레이더가 뉴스를 읽고 판단하는 데 10초가 걸린다면, 기계는 0.1초 만에 뉘앙스를 파악할 수 있습니다.
- **N-SentiTrader의 목표**: 우리는 뉴스가 가격에 완전히 반영되기 전(Price-in), **정보 확산의 초기 단계(Initial Diffusion Phase)**에서 발생하는 Alpha를 포착합니다.

---

# Part 2: 기술 스택 (Technology Stack)

본 프로젝트는 단순히 기능 구현에 그치지 않고, **최신 엔지니어링 표준(State-of-the-Art Engineering Standards)**을 준수합니다.

## 4. ⚡ The uv Revolution: 차세대 패키지 관리 혁명

### 🐢 Pain Point: 기존 Python 생태계의 한계
Python 개발자라면 한 번쯤 겪어봤을 고통이 있습니다.
1.  **느린 설치**: `pip install torch`를 실행하면 수십 메가바이트의 파일을 순차적으로 다운로드하느라 커피를 한 잔 마시고 와도 안 끝납니다.
2.  **의존성 지옥**: `pandas` 버전을 올렸더니 `numpy` 버전이 안 맞아서 `scikit-learn`이 깨지는 현상.
3.  **환경 파편화**: `venv`, `poetry`, `conda`, `pipenv`... 도구가 너무 많고 복잡합니다.

### 🐇 Solution: uv (by Astral)
우리는 2024년 등장한 Rust 기반의 패키지 매니저 **uv**를 전격 도입했습니다. 이것은 단순한 도구 교체가 아니라 **워크플로우의 혁명**입니다.

#### 1. 압도적인 속도 (Performance)
`uv`는 Rust로 작성되었으며, 멀티코어를 적극 활용하여 페이로드를 병렬로 다운로드하고 압축을 풉니다.
> **벤치마크**: `pip` 대비 **10~100배** 빠릅니다. Docker 빌드 시간이 5분에서 20초로 단축되었습니다.

#### 2. 결정론적 의존성 해결 (Deterministic Resolution)
`pip freeze > requirements.txt`는 불완전합니다. 하위 의존성(Transitive Dependency)의 버전이 명시되지 않기 때문입니다.
`uv`는 `uv.lock` 파일을 통해 **OS 플랫폼(Mac/Linux/Windows)과 상관없이** 완벽하게 동일한 패키지 그래프를 보장합니다.

```bash
# 개발자가 할 일은 딱 한 줄입니다.
uv sync
```
이 명령어 하나면 가상환경 생성, 패키지 설치, 버전 동기화가 끝납니다.

## 5. 🐻 Polars vs Pandas: Zero-copy 데이터 처리

### 💾 Pandas의 메모리 비효율성
Pandas는 데이터를 메모리에 올릴 때, Python 객체 오버헤드와 비효율적인 문자열 처리로 인해 실제 데이터 크기보다 3~5배 많은 RAM을 소모합니다. 또한 기본적으로 싱글 코어만 사용합니다.
대용량 뉴스 데이터(Text Corpus)를 다루는 우리에겐 치명적입니다.

### 🚀 Polars: Rust 기반의 고성능 DataFrame
1.  **Zero-copy**: Apache Arrow 형식을 기반으로 하여, 데이터를 복사하지 않고 포인터만 전달합니다.
2.  **Lazy Evaluation**: `df.filter().select().groupby()` 체인을 즉시 실행하지 않고, **Query Optimization Plan**을 짠 뒤 한 번에 실행합니다. 불필요한 중간 연산이 사라집니다.
3.  **Parallel Execution**: Rust의 `Rayon` 라이브러리를 통해 모든 CPU 코어를 풀가동합니다.

> **결론**: Pandas 대비 메모리 사용량은 1/5, 속도는 10배 이상 빠릅니다. 데이터 전처리 파이프라인(`src/preprocess/cleaner.py`)의 핵심 엔진입니다.

## 6. 🍎 MLX 가속: Apple Silicon의 잠재력 해방

### 💻 로컬 개발 환경의 제약
학생들이나 입문자들은 고가의 NVIDIA GPU 서버를 가지고 있지 않습니다. 대부분 MacBook Air나 Pro를 사용합니다.
기존의 PyTorch/TensorFlow는 CUDA(NVIDIA) 중심이라 맥북에서는 CPU만 써야 했고, 학습이 너무 느렸습니다.

### 🍏 MLX: Apple의 역습
Apple Research가 공개한 **MLX**는 Apple Silicon(M1/M2/M3 등)의 뉴럴 엔진과 GPU를 직접 제어합니다.
- **Unified Memory Architecture**: CPU와 GPU가 RAM을 공유합니다. 데이터를 GPU로 복사(Copy)하는 병목이 아예 없습니다(Zero-overhead).
- **Metal Shaders**: 우리는 Lasso 구현체(`src/learner/mlx_lasso.py`)에서 행렬 연산을 Metal 셰이더로 최적화하여 맥북에서도 수만 건의 데이터를 순식간에 학습할 수 있게 했습니다.

---

# Part 3: 데이터 파이프라인 (Data Pipeline)

## 7. 🕷️ 뉴스 수집과 N:M 매핑의 딜레마

### 🧩 문제: "삼성전자와 하이닉스의 동맹"
기사 하나가 여러 종목과 관련될 때, 이를 어떻게 저장해야 할까요?
초기 버전은 `tb_news` 테이블에 `stock_code` 컬럼이 있었습니다.
- 기사 A (관련종목: 삼성전자) 저장.
- 기사 A (관련종목: 하이닉스) 저장? -> **URL PK 중복 오류!**

그렇다고 URL을 다르게 저장하면 **데이터 중복**으로 용량이 2배가 됩니다.

### 🗝️ 해결: 정규화(Normalization)와 N:M 테이블
우리는 뉴스 수집 로직(`src/collector/news.py`)을 전면 개편했습니다.

1.  **News Entity (`tb_news_url`)**:
    *   `url_hash` (PK): URL의 SHA-256 해시값.
    *   `title`, `content`, `published_at`: 기사 본문 내용.
    *   **Stock Code 없음!** (종목과 무관하게 기사 그 자체만 저장)

2.  **Relation Entity (`tb_news_mapping`)**:
    *   `id` (PK)
    *   `url_hash` (FK)
    *   `stock_code` (FK)
    *   `relevance_score`

**수집 로직 (Pseudocode)**:
```python
hash = sha256(url)
if not db.exists(hash):
    db.insert_news(title, content, url) # 본문 저장 (최초 1회)

if not db.exists_mapping(hash, stock_code):
    db.insert_mapping(hash, stock_code) # 매핑만 추가
```
이제 하나의 기사가 100개 종목에 연관되어도 본문은 딱 한 번만 저장됩니다. DB 용량이 70% 절감되었습니다.

## 8. 🛡️ 지능형 필터링: RelevanceScorer 알고리즘 상세

### 🚨 Garbage In, Garbage Out
수집된 뉴스의 90%는 노이즈입니다.
- 단순 시황 중계 ("코스피 오늘 상승...")
- 광고성 기사 ("000 회장, 경영 대상 수상")
- 경쟁사 뉴스 ("경쟁사 A, 신제품 출시... 타격 불가피")

딥러닝 모델에 쓰레기 데이터를 넣으면 쓰레기 예측이 나옵니다. 우리는 룰 기반의 강력한 필터인 `RelevanceScorer`(`src/analysis/news_filter.py`)를 개발했습니다.

### 🧮 Scoring Algorithm (코드 해설)

```python
class RelevanceScorer:
    def calculate_score(self, news: News, target_stock: str) -> float:
        score = 0.0
        
        # 1. Position Bias (위치 가중치)
        if target_stock in news.title:
            score += 50  # 제목에 있으면 거의 확실함
        if target_stock in news.content[:200]:
            score += 20  # 첫 문단(Lead)에 있으면 중요함
            
        # 2. Frequency Score (빈도 점수)
        # 많이 언급될수록 좋지만, 무한히 올라가진 않게 Cap을 씌움
        count = news.content.count(target_stock)
        freq_score = min(count * 5, 20) # 최대 20점
        score += freq_score
        
        # 3. Competitor Penalty (경쟁사 페널티)
        # 타겟보다 경쟁사가 더 많이 언급되는 기사는 '노이즈'로 간주
        competitor_count = self.count_competitors(news.content)
        if competitor_count > count * 1.5:
            score -= 30  # 강력한 페널티
            
        return max(score, 0)
```

**판정 기준**:
- `Score >= 30`: **Relevant** (학습 데이터로 채택)
- `Score < 30`: **Irrelevant** (폐기)

이 간단한 로직이 복잡한 BERT 분류기보다 훨씬 빠르고 효율적임이 증명되었습니다.

## 9. ✂️ BERT 추출 요약 (NewsSummarizer): Centroid 기법

### 📉 긴 글은 죄악이다
뉴스 기사는 평균 1500자입니다. 쓸데없는 미사여구, 기자 이메일, 과거 히스토리 등이 포함됩니다.
이걸 그대로 TF-IDF에 넣으면 단어 행렬이 너무 희소(Sparse)해집니다. "3줄 요약"이 필요합니다.

### 🧠 Centroid Summarization (요약의 원리)
우리는 생성형 요약(GPT)이 아닌 **추출 요약(Extractive Summarization)**을 사용합니다. 왜냐하면 GPT는 가끔 없는 사실을 지어내기(Hallucination) 때문입니다. 주식 뉴스에서 숫자를 틀리면 치명적입니다.

**Algorithm Steps (`src/nlp/summarizer.py`)**:
1.  **Splitting**: 기사를 문장 단위로 쪼갭니다 ($S_1, S_2, ..., S_n$).
2.  **Embedding**: `KR-FinBERT` 모델을 통해 각 문장을 768차원 벡터로 변환합니다 ($v_1, v_2, ..., v_n$).
3.  **Centroid Calculation**: 문서 전체의 의미를 대표하는 평균 벡터(무게중심)를 구합니다.
    $$ C = \frac{1}{n} \sum_{i=1}^{n} v_i $$
4.  **Similarity Ranking**: 각 문장이 중심 벡터 $C$와 얼마나 비슷한지(Cosine Similarity) 계산합니다.
    $$ Score_i = \frac{v_i \cdot C}{\|v_i\| \|C\|} $$
5.  **Selection**: 점수가 가장 높은 상위 3개 문장을 뽑아, 원래 순서대로 조합합니다.

이렇게 하면 팩트는 그대로 유지하면서 길이는 1/5로 줄어듭니다.

---

# Part 4: 특성 공학 (Feature Engineering)

## 10. 🧮 TF-IDF Vectorization: N-gram(1,3) 전략

### 🔡 단순 단어(Unigram)의 함정
"상승"이라는 단어는 호재일까요?
- "금리 **상승**" -> 악재 📉
- "매출 **상승**" -> 호재 📈

단어 하나만 봐서는 의미를 알 수 없습니다. 문맥(Context)이 필요합니다.

### 🔗 N-gram (1, 3)
우리는 단어를 1개료(Unigram), 2개로(Bigram), 3개로(Trigram) 묶어서 봅니다.
- `ngram_range=(1, 3)`
- **Unigram**: "금리", "상승"
- **Bigram**: "금리 상승", "상승 우려"
- **Trigram**: "금리 상승 우려"

`Trigram`까지 사용하면 문맥이 명확해지지만, 단어 수(Feature)가 기하급수적으로 늘어나는 단점이 있습니다. 그래서 우리는 `max_features=25000`이라는 강력한 제약 조건을 함께 사용합니다.

## 11. ⏳ 시차 효과 (Lag Features): 정보의 반감기

### 🕒 뉴스는 며칠 동안 살아있나?
오늘(D-day)의 주가는 오늘 뉴스에만 반응할까요? 아닙니다.
어제(D-1) 나온 대박 뉴스는 오늘도 여전히 매수 심리를 자극합니다. 3일 전(D-3) 뉴스도 미약하게나마 영향이 있습니다.

우리는 이를 모델링하기 위해 **Lag Feature**를 생성합니다.
입력 데이터 $X$는 다음과 같이 구성됩니다.

| 날짜 | Word_오늘 | Word_1일전 | Word_2일전 | ... | Word_5일전 |
|------|-----------|------------|------------|-----|------------|
| 1/5 | "매수" 빈도 | "매수" 빈도 | "매수" 빈도 | ... | "매수" 빈도 |

이렇게 하면 모델은 **"3일 전의 '매수' 추천이 오늘의 주가 상승에 미치는 영향력(계수)"**을 학습할 수 있습니다.

## 12. 📉 동적 감쇠 (Dynamic Decay): 시간 가중치 로직

### 📻 뉴스의 유통기한
Lag Feature를 만들 때, 5일 전 뉴스를 오늘 뉴스와 똑같이 취급하면 안 됩니다. 정보는 시간이 지날수록 가치가 떨어집니다.
우리는 **지수 감쇠(Exponential Decay)** 함수를 적용합니다.

$$ W_t = e^{-\lambda \times t} $$

- $t$: 경과 일수 (0, 1, 2, 3, 4, 5)
- $\lambda$: 감쇠율 (Decay Rate). 이 값은 고정되지 않고 AWO 엔진에 의해 **시장의 속도에 맞춰 동적으로 조절**됩니다.
    - 시장이 급변할 때 -> $\lambda$ 증가 (빨리 잊음)
    - 시장이 안정적일 때 -> $\lambda$ 감소 (오래 기억함)

## 13. 🦢 Black Swan 필터링: 희귀 단어 보호

### 🦢 통계의 오류
일반적으로 텍스트 분석에서는 `min_df=3` (최소 3번 이상 등장) 같은 조건으로 희귀 단어를 지웁니다. 오타나 무의미한 고유명사를 없애기 위해서입니다.

하지만 금융에서는 **"희귀하지만 치명적인"** 단어들이 있습니다.
- **"횡령"**, **"배임"**, **"상장폐지"**, **"부도"**, **"전쟁"**

이 단어들은 1년에 한 번 나올까 말까 하지만, 나오면 주가는 하한가를 갑니다. 빈도 기반으로 지워버리면 모델은 이 거대한 위험을 감지하지 못합니다.
우리는 `src/learner/lasso.py` 내의 `CRITICAL_WORDS` 리스트에 이들을 등록하여, `min_df` 조건에 걸리더라도 **삭제되지 않도록 강제(Whitelist)**합니다. 이것이 도메인 지식(Domain Knowledge)의 힘입니다.

---

# Part 5: 핵심 알고리즘 (Core Algorithms)

## 14. 📐 Lasso 회귀의 수학적 원리 (L1 Regularization)

Lasso는 단순한 회귀분석이 아닙니다. 일종의 **최적화 문제(Optimization Problem)**입니다.

$$ \hat{\beta} = \text{argmin}_{\beta} \left( \frac{1}{2N} \sum_{i=1}^{N} (y_i - x_i^T \beta)^2 + \alpha \sum_{j=1}^{p} |\beta_j| \right) $$

1.  **Loss Term (MSE)**: $\sum (y - \hat{y})^2$. 실제 주가와 예측 주가의 차이를 줄이려고 노력합니다.
2.  **Penalty Term (L1)**: $\alpha \sum |\beta|$. 가중치들의 합이 커지는 것을 막습니다.

### 💎 왜 0이 되는가? (Sparsity)
L2 규제(Ridge, 원형 제약조건)와 달리, L1 규제(Lasso)는 제약 영역이 **뾰족한 마름모 꼴**입니다.
이차함수(Loss)의 등고선이 마름모의 **모서리(Vertex)**와 접할 확률이 매우 높습니다. 이 모서리는 축 위에 있으므로, 해당 좌표(변수의 가중치)는 **정확히 0**이 됩니다.
이 수학적 성질 덕분에 우리는 수만 개의 뉴스 단어 중 **진짜 중요한 1%**만 골라낼 수 있습니다.

## 15. ⚡ Celer 엔진: Working Set 알고리즘

### 🐌 Coordinate Descent의 한계
Lasso를 풀 때 보통 좌표 하강법(Coordinate Descent)을 씁니다. 변수가 10만 개면, 10만 번 돌아야 1 epoch가 끝납니다. 너무 느립니다.

### 🏎️ Celer (Constraint Elimination used for Linear Regression)
우리는 `celer` 라이브러리를 사용하여 이를 가속화했습니다.
**핵심 아이디어**: "어차피 답의 99%는 0일 텐데, 0이 아닐 것 같은 녀석들만 먼저 풀자."

1.  **Working Set 선정**: KKT 조건 위반 정도(Dual Gap)를 계산하여, 0이 아닐 가능성이 높은 상위 100개 변수를 뽑습니다.
2.  **Sub-problem**: 10만 개가 아닌 100개 변수만 가지고 Lasso를 풉니다. (순식간에 풀림)
3.  **Check**: 나머지 변수들 중에 KKT 조건을 위반하는 놈이 있는지 봅니다. 있으면 Working Set에 추가하고 다시 풉니다.
4.  **Convergence**: 더 이상 위반하는 변수가 없으면 그것이 전체 문제의 최적해(Global Optimum)와 동일함이 수학적으로 증명되어 있습니다.

이 방식은 수렴 속도를 **10~100배** 가속시킵니다.

## 16. 🚀 MLX 가속: Metal GPU 연산 구현

`sklearn`이나 `celer`는 CPU 기반입니다. 우리는 Apple Silicon의 **GPU**를 놀게 하고 싶지 않았습니다.
우리는 Lasso의 핵심 연산인 **Soft Thresholding Operator**를 Metal로 구현했습니다.

$$ S(z, \gamma) = \text{sgn}(z) \cdot \max(|z| - \gamma, 0) $$

이 수식은 간단해 보이지만, 행렬 $X$의 크기가 $(10000, 25000)$일 때 이 연산을 병렬로 수행하는 것은 GPU가 압도적으로 유리합니다.
`src/learner/mlx_lasso.py`는 이를 `mlx.core` 연산으로 구현하여 **배치 학습(Batch Training)** 속도를 극대화했습니다.

## 17. ⚖️ 하이브리드 앙상블 (Hybrid Ensemble): 6:4의 황금비

### 🤝 Two Brains are Better than One
우리는 두 종류의 모델을 섞어 씁니다.

1.  **Model A: TF-IDF + Lasso (Weight 0.6)**
    *   **접근법**: 키워드 중심 (BoW).
    *   **장점**: 해석력이 뛰어남. "어떤 단어 때문인가?"를 정확히 지목함.
    *   **단점**: "좋지 않다"와 "않 좋지 않다"를 구별 못 할 수 있음 (N-gram으로 어느 정도 보완).

2.  **Model B: FinBERT Embedding + Ridge (Weight 0.4)**
    *   **접근법**: 의미 중심 (Semantic).
    *   **장점**: 문맥과 뉘앙스를 완벽히 이해함.
    *   **단점**: 블랙박스. 설명하기 어려움.

### ⚗️ 앙상블 공식
$$ P_{Final} = 0.6 \cdot P_{Lasso} + 0.4 \cdot P_{BERT} $$

왜 6:4인가? 우리의 최우선 가치는 **화이트박스(설명 가능성)**이기 때문입니다. Lasso가 주도권을 쥐고, BERT가 뒤에서 미묘한 뉘앙스를 보정해주는 구조입니다. 이 비율은 수천 번의 백테스팅(`src/verification/`)을 통해 검증된 황금 비율입니다.

---

# Part 6: AWO 엔진 (Adaptive Window Optimization)

**"가장 훌륭한 전략도 시간이 지나면 낡은 것이 된다."** - 이것은 금융 시장의 불문율입니다.

## 18. 🌊 시장의 비정상성 (Regime Shift) 대응

### 🔄 Regime Shift (체제 전환)
시장은 끊임없이 성격을 바꿉니다.
- **Bull Market (상승장)**: 작은 호재에도 민감하게 반응, 악재는 무시.
- **Bear Market (하락장)**: 호재는 무시, 작은 악재에 투매.
- **High Volatility**: 뉴스의 영향력이 극도로 짧아짐.

고정된 파라미터(예: "항상 6개월치 뉴스를 학습해")를 쓰는 모델은 시장 상황이 바뀌면 성능이 급락합니다. 이를 해결하기 위해 AWO 엔진(`src/learner/awo_engine.py`)을 개발했습니다.

## 19. 🔍 2D Grid Search: Window x Alpha

AWO 엔진은 매주 주말, CPU/GPU를 풀가동하여 다음주에 사용할 **최적의 파라미터**를 찾습니다.

**탐색 공간 (Search Space)**:
1.  **Lookback Window ($W$)**: 학습 데이터 길이를 얼마나 잡을까?
    *   `[1개월, 3개월, 6개월, 12개월]`
    *   짧으면 최신 트렌드 반영(민감), 길면 데이터 부족 해소(안정).
2.  **Regularization Strength ($\alpha$)**: Lasso 규제를 얼마나 세게 걸까?
    *   `[0.01, 0.005, 0.001, 0.0005, ...]`
    *   크면 소수 정예 키워드만 남김(보수적), 작으면 많은 단어를 반영(공격적).

총 $4 \times 5 = 20$개의 평행 우주(시나리오)를 돌려보고 승자를 뽑습니다.

## 20. 📏 안정성 점수 (Stability Score) 공식

단순히 "지난주 수익률 1등"을 뽑으면 될까요? 위험합니다. 우연히(Lucky) 맞춘 것일 수 있습니다. 우리는 **Robustness(견고함)**를 봅니다.

$$ S_{stability} = \mu(HR) - \gamma \cdot \sigma(HR) $$

- $\mu(HR)$: 해당 파라미터 조합의 전진 분석(Walk-forward) 평균 Hit Rate.
- $\sigma(HR)$: 해당 파라미터 *인근* 설정들의 Hit Rate 표준편차.
- $\gamma$: 페널티 계수 (보통 1.0).

**해석**: "나도 잘했지만 내 주변 친구들(파라미터가 약간 다른 모델들)도 다 같이 잘했어야 진짜 실력이다." 즉, 파라미터 공간에서 성능이 뾰족한 산봉우리(Spike)가 아니라 넓은 고원(Plateau)에 위치해야 합니다.

## 21. 🏆 자동 승격 (Promotion) 메커니즘

1.  **Saturday 03:00**: 스케줄러가 `AWO_Worker`를 깨웁니다.
2.  **Scan**: 최근 1년 데이터를 대상으로 20개 조합에 대해 Walk-Forward Test를 수행합니다.
3.  **Score**: 각 조합의 Stability Score를 계산합니다.
4.  **Promote**: 1등 조합의 설정값(예: `Window=3M`, `Alpha=0.005`)을 DB의 `system_config` 테이블에 업데이트합니다.
5.  **Apply**: 월요일 아침부터 모든 예측은 이 새로운 설정으로 수행됩니다.

이 시스템 덕분에 N-SentiTrader는 인간의 개입 없이도 시장 변화에 스스로 적응합니다.

---

# Part 7: 메모리 최적화 (Memory Optimization)

대규모 텍스트 데이터를 다루면서 겪은 **OOM(Out Of Memory)** 문제와 해결 과정을 공유합니다. (Req-MEM-01~04)

## 22. 💥 OOM 사건 분석 (Case Study)

### 🚨 상황
- **Hardware**: AWS t3.large (8GB RAM) 또는 개발자 맥북 (16GB).
- **Data**: 1년치 뉴스 약 30만 건.
- **Code**: `vectorizer.fit_transform(news_list)`
- **Result**: 프로세스가 1분 뒤 조용히 죽음 (`Killed: 9`).

### 🕵️ 원인 분석
`sklearn`의 `TfidfVectorizer`는 입력을 받으면 내부적으로 텍스트 전체를 메모리에 복제하고, 토큰화 과정에서 엄청난 수의 임시 문자열 객체를 생성합니다. 30만 건 뉴스는 원본 텍스트만 500MB지만, 객체 오버헤드와 중간 행렬 생성으로 순간 메모리 사용량이 10GB를 넘깁니다.

## 23. 🚿 Generator Streaming: 버퍼 제거

**해결책 1**: 데이터를 리스트(`list`)에 한꺼번에 담지 않는다.

```python
# [Bad]
all_news = db.fetchall() # 30만 개 리스트가 메모리에 로드됨
vec.fit(all_news)

# [Good]
def news_generator():
    cursor = db.execute("SELECT content FROM tb_news")
    for row in cursor:
        yield row[0] # 한 번에 하나씩만 메모리에 올림

vec.fit(news_generator())
```
Python의 `yield`를 사용하면, Vectorizer는 데이터를 한 줄씩 읽어서 어휘 사전(Vocabulary)만 업데이트하고 원본 텍스트는 즉시 버립니다. 메모리 사용량이 데이터 크기와 무관하게 일정해집니다.

## 24. 🌳 Vocabulary Pruning: Min_df와 Max_df

**해결책 2**: 필요 없는 단어는 아예 사전에 등록하지 않는다.

- **min_df=3**:
    - 전체 뉴스에서 3번 미만 등장한 단어는 오타이거나 무의미한 고유명사일 확률이 99%입니다.
    - 이를 적용하면 단어장 크기가 300만 개에서 10만 개로 1/30 토막 납니다. 메모리 절약의 일등 공신입니다.
- **max_df=0.85**:
    - 85% 이상의 문서에 등장하는 단어("기자", "오늘", "속보" 등)는 정보량이 0인 불용어(Stopword)입니다.
    - 이를 제거하여 고빈도 단어로 인한 Dense Matrix화(메모리 낭비)를 막습니다.

## 25. 📉 Max Features 최적화: 25,000의 법칙

**해결책 3**: 욕심을 버린다.

초기에는 `max_features=50000`을 썼습니다. 하지만 연구 및 실험 결과(Artifact `analysis_workflow_optimization.md`), 25,000개 이상의 단어는 모델 성능 향상에 거의 기여하지 않습니다. 오히려 과적합을 유발합니다.
BERT 요약을 통해 뉴스의 밀도가 높아졌기 때문에, 상위 25,000개 단어만으로도 충분히 모든 경제 상황을 설명할 수 있습니다. 이를 통해 Feature Matrix의 크기를 절반으로 줄였습니다.

---

# Part 8: 프론트엔드 (Frontend)

## 26. 🌐 HTMX: Hypermedia-Driven Architecture

### 🚫 왜 React/Vue를 쓰지 않았나?
요즘 웹 개발 트렌드는 React + Next.js입니다. 하지만 본 프로젝트는 **데이터 분석 및 시각화**가 주 목적이며, 복잡한 클라이언트 상태(User State) 관리가 필요 없습니다.
React를 쓰면 배보다 배꼽이 더 커집니다.
- 별도의 프론트엔드 빌드 파이프라인 (Webpack/Vite)
- 백엔드와 프론트엔드의 API 스키마 동기화 (REST/GraphQL)
- 번들 사이즈 최적화, Hydration 문제 등등...

### ⚡ HTMX: HTML의 부활
우리는 **HTMX**를 사용하여 백엔드(Python/FastAPI) 중심의 개발 생산성을 극대화했습니다.

```html
<!-- HTML이 스스로 API를 호출하고 자신을 업데이트합니다 -->
<button hx-post="/api/predict/A005930" 
        hx-target="#prediction-result" 
        hx-swap="innerHTML"
        class="btn-primary">
    삼성전자 예측 실행
</button>

<div id="prediction-result"></div>
```

이 방식(HATEOAS)의 장점:
1.  **No JavaScript**: JS 코드를 한 줄도 짤 필요가 없습니다.
2.  **Single Language**: Python(Jinja2)에서 로직과 화면을 모두 제어합니다.
3.  **Zero Build**: 수정 후 새로고침하면 끝입니다.

## 27. 💎 Glassmorphism UI: 금융 대시보드의 미학

초보 개발자들이 가장 간과하는 것이 UI/UX입니다. "기능만 되면 그만"이라는 생각은 버려야 합니다. 사용자는 UI가 예쁘면 신뢰감을 가집니다.

### 🎨 Design Tokens
- **Background**: Deep Navy (`#0f172a`) - 장시간 보아도 눈이 편안함.
- **Glass Effect**:
    ```css
    .glass-panel {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    ```
    반투명한 유리 질감을 사용하여 정보의 계층(Layer)을 표현했습니다.
- **Accent Colors**:
    - Bull(상승): Neon Green (`#00ff9d`)
    - Bear(하락): Hot Pink (`#ff0055`)
    - 기존의 칙칙한 빨강/파랑 대신 사이버펑크 스타일의 네온 컬러를 사용하여 "첨단 AI 시스템"의 느낌을 주었습니다.

---

# Part 9: 옵저버빌리티 (Observability)

시스템을 운영한다는 것은 "무엇이 잘못되고 있는지 아는 것"입니다.

## 28. 🔭 Prometheus & cAdvisor: 풀스택 모니터링

### 🏗️ Monitoring Architecture
본 프로젝트는 17개의 컨테이너가 돌아가는 MSA 구조입니다. `docker logs`만 봐서는 전체 상황을 알 수 없습니다.

1.  **Node Exporter**: 호스트 머신(EC2/Mac)의 CPU, RAM, Disk I/O, Network 트래픽을 수집합니다.
2.  **cAdvisor**: 각 Docker 컨테이너별 리소스 사용량을 수집합니다. "누가 메모리를 잡아먹고 있나?"를 알 수 있습니다.
3.  **Prometheus**: 위지표들을 15초마다 긁어와서(Scraping) 시계열 DB에 저장합니다.
4.  **Python Client**: 비즈니스 로직(수집된 뉴스 개수, 모델 적중률 등)을 커스텀 메트릭으로 노출합니다.

## 29. 📊 Grafana 대시보드: 시계열 시각화

Prometheus에 저장된 숫자는 그냥 숫자일 뿐입니다. Grafana를 통해 이를 그래프로 그립니다.

**주요 패널**:
- **Ingestion Rate**: 초당 뉴스 수집 처리량 (EPS).
- **Latency Heatmap**: API 응답 속도 분포.
- **OOM Warning**: 메모리 사용량이 80%를 넘으면 빨간색 경고등 점멸.
- **Prediction Accuracy**: 일별 모델 적중률 추이 그래프.

## 30. 🧟 좀비 워커 탐지 및 자가 치유 (Self-Healing)

### 🧟 Zombie Process
크롤러는 외부 요인(네트워크 단절, 타겟 사이트 변경 등)으로 인해 자주 멈춥니다(Hang). 프로세스는 살아있는데 일은 안 하는 상태, 즉 **좀비**가 됩니다.

### 💓 Heartbeat Pattern
이를 해결하기 위해 자가 치유 시스템을 구축했습니다.

1.  **I am alive**: 모든 워커는 1분마다 Redis의 특정 키(`worker_heartbeat_{id}`)에 현재 시간을 기록합니다.
2.  **Reaper (저승사자)**: 스케줄러 프로세스는 5분마다 Redis를 검사합니다.
3.  **Kill & Revive**: 마지막 기록이 5분 전이라면? 해당 컨테이너 ID를 찾아 `docker restart` 명령을 날립니다.

이로써 개발자가 자는 동안에도 시스템은 스스로 복구하고 돌아갑니다.

---

# Part 10: 운영 가이드 (Operations)

## 31. 🐳 Docker Compose 토폴로지 (17 Containers)

마이크로서비스 아키텍처는 복잡해 보이지만, `docker-compose.yml` 하나로 정의됩니다.

```yaml
services:
  # [Data Layer]
  postgres: ...
  redis: ...
  rabbitmq: ...

  # [Collection Layer] - Scalable
  news_collector_1: ...
  news_collector_2: ...
  news_collector_3: ...
  news_collector_4: ...

  # [Processing Layer] - CPU Intensive
  news_processor_1: ...
  news_processor_2: ...
  
  # [Intelligence Layer]
  learner_worker: ...
  verification_worker: ...
  
  # [Presentation Layer]
  dashboard: ...
  
  # [Monitoring Layer]
  prometheus: ...
  grafana: ...
  cadvisor: ...
  node_exporter: ...
```
총 17개의 컨테이너가 톱니바퀴처럼 맞물려 돌아갑니다.

## 32. 🔑 환경 변수 설정 (Configuration)

보안을 위해 모든 비밀번호와 설정값을 `.env` 파일로 분리했습니다.
프로젝트 루트의 `.env.example`을 복사하여 `.env`를 생성하고 값을 채워주세요.

```ini
# Database
DB_HOST=postgres
DB_PORT=5432
DB_USER=senti_user
DB_PASSWORD=secret_password

# External APIs
NAVER_CLIENT_ID=your_id
NAVER_CLIENT_SECRET=your_secret

# System Tuning
MAX_WORKERS=4
BATCH_SIZE=32
LOG_LEVEL=INFO
```

## 33. 🚀 시작하기 (Getting Started)

### 사전 준비물 (Prerequisites)
- Docker Desktop (필수)
- Git
- Python 3.12 (로컬 실행 시)

### 설치 및 실행 가이드

1.  **Repository Clone**
    ```bash
    git clone https://github.com/silverwoods-dev/N-SentiTrader.git
    cd N-SentiTrader
    ```

2.  **Setup Environment**
    ```bash
    cp .env.example .env
    vi .env  # API 키 입력
    ```

3.  **Build & Run**
    ```bash
    # 처음 실행 시 이미지를 빌드하느라 시간이 좀 걸립니다.
    docker-compose up -d --build
    ```

4.  **Health Check**
    ```bash
    docker-compose ps
    # 모든 컨테이너가 "Up" 상태인지 확인하세요.
    ```

5.  **Access**
    - Web Dashboard: `http://localhost:8081`
    - Grafana: `http://localhost:3000` (ID: admin / PW: admin)
    - RabbitMQ: `http://localhost:15672` (ID: guest / PW: guest)

---

### Appendix A: Code Gallery (Core Implementation)

여기서는 설명만으로는 부족한 핵심 로직의 실제 구현 코드를 보여줍니다.

#### 1. Celer Lasso Training (`src/learner/lasso.py`)
```python
def train_model(X, y, alpha):
    """
    Celer 라이브러리를 사용한 초고속 Lasso 학습
    """
    from celer import Lasso
    
    # max_epochs=100: 수렴하지 않아도 100번 돌면 멈춤 (안전장치)
    # p0=100: Working Set 크기. 처음엔 100개 변수만 봅니다.
    clf = Lasso(
        alpha=alpha,
        max_iter=100,
        max_epochs=1000,
        p0=100,
        prune=True,  # 0이 된 변수는 메모리에서 제거
        verbose=False
    )
    
    clf.fit(X, y)
    
    # 0이 아닌 계수만 추출하여 딕셔너리로 저장
    feature_dict = {}
    for idx, coef in enumerate(clf.coef_):
        if coef != 0:
            feature_dict[idx] = coef
            
    return feature_dict
```

#### 2. Generator-based Vectorization (`src/pipeline/vectorizer.py`)
```python
def get_vectorizer(db_session, min_df=3, max_df=0.85):
    """
    메모리 효율적인 스트리밍 벡터라이저
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    
    # 제너레이터 함수 정의
    def stream_docs():
        query = text("SELECT content FROM tb_news_url")
        # yield_per(1000): DB에서 1000개씩만 끊어서 가져옴 (메모리 보호)
        for row in db_session.execute(query).yield_per(1000):
            yield row[0]
            
    vec = TfidfVectorizer(
        min_df=min_df,
        max_df=max_df,
        max_features=25000,
        ngram_range=(1, 3),
        sublinear_tf=True  # TF 값 스케일링 (빈도수 폭발 방지)
    )
    
    # 리스트 없이 바로 제너레이터 주입
    vec.fit(stream_docs())
    return vec
```

### Appendix B: Troubleshooting (FAQ)

**Q1. `docker-compose up`을 했는데 `db` 컨테이너가 자꾸 죽어요.**
> **A**: 데이터베이스 초기화 스크립트(`init.sql`)에 오류가 있거나, 기존 볼륨 데이터와 충돌하는 경우입니다.
> `docker-compose down -v` 명령어로 볼륨까지 싹 지우고 다시 시도해보세요.

**Q2. 뉴스 수집이 0건이에요.**
> **A**: 네이버 API 키가 만료되었거나 일일 한도(25,000건)를 초과했을 수 있습니다. `.env` 파일의 키를 확인하거나, RabbitMQ 관리자 페이지에서 `news_queue`에 메시지가 쌓여있는지(Consumer가 죽었는지) 확인하세요.

**Q3. 모델 정확도가 50% 언저리에서 안 올라가요.**
> **A**: 정상입니다(?). 주식 예측은 원래 어렵습니다. 53%면 훌륭한 모델입니다. 하지만 50.0%라면 학습 데이터가 너무 적거나, 라벨링(Y값) 생성 로직에 문제가 있는 것입니다. `min_df`를 낮춰보거나 윈도우 사이즈를 늘려보세요.

### Appendix C: Development History (31 Steps)

본 프로젝트가 걸어온 길입니다.

- **Phase 1 (v0.1)**: Requests + BeautifulSoup으로 네이버 뉴스 크롤링 성공.
- **Phase 2 (v0.5)**: PostgreSQL 도입. 중복 데이터 문제 발생.
- **Phase 3 (v1.0)**: URL Hash 기반 N:M 테이블 구조로 DB 리팩토링.
- **Phase 4 (v1.5)**: Konlpy(Mecab) 도입. 형태소 분석 시작.
- **Phase 5 (v2.0)**: Scikit-learn Lasso 모델 학습 성공 (하지만 OOM 발생).
- **Phase 6 (v2.2)**: Generator Streaming 도입으로 OOM 해결.
- **Phase 7 (v3.0)**: RabbitMQ 도입. 수집과 학습의 비동기 분리.
- **Phase 8 (v3.5)**: RelevanceScorer 구현. 노이즈 뉴스 필터링.
- **Phase 9 (v4.0)**: BERT Summarizer 도입. 요약 성능 개선.
- **Phase 10 (v4.5)**: MLX / Celer 가속 엔진 탑재.
- **Phase 11 (v5.0)**: AWO 엔진 완성. 전진 분석 및 자동 승격 시스템 구축.

---

> **N-SentiTrader Project**
> *Developed by Team Silverwoods*
> *For the Next Generation of AI Engineers*
