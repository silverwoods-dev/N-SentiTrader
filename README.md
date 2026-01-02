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
> 우리는 "결과"보다 "과정"을, "코드"보다 "설계의 이유"를 설명합니다.

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

### Appendices
*   [Appendix A: Code Gallery](#appendix-a-code-gallery)
*   [Appendix B: Troubleshooting](#appendix-b-troubleshooting)
*   [Appendix C: Development History (31 Steps)](#appendix-c-development-history-31-steps)

---

# Part 1: 철학과 동기 (Philosophy & Motivation)

## 1. 🏛️ 왜 화이트박스(White-Box)인가? (XAI와 법적 근거)

### 🧐 배경: 금융권의 '설명 책임' (Accountability)
최근 LLM(GPT-4 등)이 등장했음에도 불구하고, 실무 금융권에서 선형 모델 기반의 화이트박스를 고집하는 이유는 기술적 한계 때문이 아닌, **'법적 생존'** 때문입니다. 수천억 원의 자산을 운용하는 알고리즘이 "왜?"라는 질문에 답하지 못한다면, 그것은 기술이 아니라 '도박'입니다.

#### 📜 법적 근거 (Legal Basis)
1.  **EU AI Act (2024)**: 고위험(High-risk) AI 시스템, 특히 신용 평가 및 금융 서비스에 대해 **"해석 가능성(Interpretability)"**과 **"추적 가능성(Traceability)"**을 강력하게 의무화했습니다. 블랙박스 모델은 규제 준수 비용을 기하급수적으로 높입니다.
2.  **GDPR 제13조-14조**: 정보 주체는 자동화된 의사 결정에 대해 **"유의미한 정보(Meaningful Information)"**를 제공받을 권리가 있습니다. "딥러닝 가중치가 그렇다"는 설명은 법적으로 유효하지 않습니다.
3.  **ECOA (미국 평등신용기회법)**: 대출 거절 시 **구체적인 사유(Adverse Action)**를 명시해야 합니다. (예: "소득 대비 부채 비율 과다" vs "모델 점수 0.3 미달")

## 2. 📉 왜 Lasso인가? (희소성의 미학)
수만 개의 단어 중 주가에 영향을 미치는 단어는 극소수입니다.
- **L1 Regularization**: Lasso는 가중치의 절댓값 합을 패널티로 부여하여, 중요하지 않은 변수의 가중치를 **정확히 0**으로 만듭니다.
- **Sparse Matrix**: 결과적으로 `0`이 아닌 단어들만 남게 되어, 사람이 읽고 이해할 수 있는 **'감성 사전'**이 자동으로 생성됩니다.

## 3. 🧠 왜 뉴스 감성인가? (효율적 시장 가설과 정보 비대칭)
- **효율적 시장 가설(EMH)**: 모든 정보는 즉시 가격에 반영됩니다.
- **정보 비대칭**: 하지만 '뉴스'가 나오기 전, 혹은 뉴스가 퍼지는 **초기 확산 단계**에서는 정보의 불균형이 존재합니다. 본 시스템은 이 **Alpha(초과 수익)** 구간을 포착하는 것을 목표로 합니다.

---

# Part 2: 기술 스택 (Technology Stack)

## 4. ⚡ The uv Revolution: 차세대 패키지 관리 혁명

### 🐢 기존의 문제점 (Pip/Poetry)
- **느린 속도**: `pip`는 순차적 다운로드로 인해 대규모 의존성 해결에 수십 분이 걸립니다.
- **의존성 지옥**: `requirements.txt`는 하위 의존성을 보장하지 않아 "어제 되던 코드가 오늘 안 되는" 문제가 발생합니다.

### 🐇 uv의 도입 (Rust-based)
우리는 **Astral** 사가 개발한 `uv`를 전격 도입했습니다.
1.  **압도적인 속도**: Rust의 병렬 처리로 `pip` 대비 **100배** 빠른 설치 속도.
2.  **결정론적 빌드**: `uv.lock` 파일은 OS에 관계없이 완벽하게 동일한 환경을 보장합니다.
3.  **통합 툴체인**: Python 버전 관리, 가상환경, 패키지 설치를 단 하나의 툴로 처리합니다.

## 5. 🐻 Polars vs Pandas: Zero-copy 데이터 처리

### 📊 Pandas의 한계
Pandas는 데이터를 메모리에 올릴 때 불필요한 복사(Copy)를 많이 수행하며, 싱글 코어만 사용합니다. 1GB CSV를 읽으면 RAM을 3~4GB 차지합니다.

### 🚀 Polars의 선택
- **Rust Core**: 메모리 안전성과 속도를 보장합니다.
- **Lazy Evaluation**: 연산 계획을 최적화한 후 실행하여 불필요한 계산을 줄입니다.
- **Parallel Execution**: 모든 CPU 코어를 사용하여 데이터 처리를 가속화합니다.

## 6. 🍎 MLX 가속: Apple Silicon의 잠재력 해방

### 💻 로컬 개발 환경의 혁신
대부분의 ML 학습은 NVIDIA GPU가 필요하지만, 학생들은 MacBook Air를 사용하는 경우가 많습니다.
- **MLX Framework**: Apple이 직접 만든 NumPy 호환 배열 라이브러리입니다.
- **Unified Memory**: CPU와 GPU가 메모리를 공유하여 데이터 전송 오버헤드가 없습니다.
- **Metal Kernel**: `src/learner/mlx_lasso.py`에서 우리는 Lasso 회귀의 좌표 하강법을 Metal 셰이더로 직접 구현하여 속도를 극대화했습니다.

---

# Part 3: 데이터 파이프라인 (Data Pipeline)

## 7. 🕷️ 뉴스 수집과 N:M 매핑의 딜레마

### 🧩 문제 정의
"삼성전자와 SK하이닉스가 HBM 시장에서 격돌했다."
이 기사는 삼성전자 뉴스인가요, 하이닉스 뉴스인가요? 둘 다입니다.
기존 시스템은 URL을 Primary Key로 사용하여, 한 종목에 수집된 기사를 다른 종목이 참조하지 못했습니다.

### 🗝️ 해결: URL Hash 기반 N:M 매핑
1.  **tb_news_url**: URL의 SHA-256 해시를 PK로 하여 기사 원문을 **유일하게(Unique)** 저장합니다.
2.  **tb_news_mapping**: `(url_hash, stock_code)` 쌍을 저장하여 다대다 관계를 구현합니다.
3.  **Cross-Referencing**: 수집기(`AddressCollector`)가 이미 있는 URL을 발견하면, 원문을 다시 긁지 않고 매핑만 추가합니다.

## 8. 🛡️ 지능형 필터링: RelevanceScorer 알고리즘 상세

### 🚨 노이즈 필터링의 중요성
단순히 "삼성전자"가 포함되었다고 모두 학습하면 모델 성능이 떨어집니다. 스팸, 광고, 단순 시황 언급을 걸러내야 합니다.

### 🧮 알고리즘 상세 (Source: `news_filter.py`)

각 뉴스는 다음 공식에 따라 0~100점의 **Relevance Score**를 받습니다.

```math
Score = P_{Bias} + F_{Score} - C_{Penalty}
```

#### 1. 위치 편향 (Position Bias, $P_{Bias}$)
기사의 핵심은 앞부분에 있습니다.
- **Title Hit**: 제목에 종목명(또는 별칭)이 포함되면 `+50점`.
- **Lead Hit**: 첫 문단(First Paragraph, 200자 이내)에 포함되면 `+20점`.

#### 2. 빈도 점수 (Frequency Score, $F_{Score}$)
- `min(Count * 5, 20)`: 종목명이 1번 나올 때마다 5점씩, 최대 20점까지 부여합니다.

#### 3. 경쟁사 페널티 (Competitor Penalty, $C_{Penalty}$)
- 기사 내에서 경쟁사(예: 하이닉스)가 타겟 종목보다 **더 많이** 언급되면 주객전도된 기사입니다.
- 이 경우 `-30점`을 차감합니다. 단, 제목에 타겟 종목이 있다면 `-10점`으로 완화합니다.

#### 4. 결정 (Decision)
- **Score ≥ 30**: 유효한 뉴스(Signal) → 학습 데이터로 사용.
- **Score < 30**: 노이즈(Noise) → 폐기.

## 9. ✂️ BERT 추출 요약 (NewsSummarizer): Centroid 기법

### 📉 차원 축소의 필요성
뉴스 원문은 너무 깁니다. 모든 단어를 학습하면 노이즈가 증가합니다. 사람이 읽을 때처럼 "가장 중요한 3문장"만 남겨야 합니다.

### 🧠 Centroid-based Extraction Algorithm
1.  **Sentence Splitting**: `kss` 또는 정교한 정규식으로 문장을 분리합니다.
2.  **Embedding**: `KR-FinBERT`를 사용하여 모든 문장 $S_i$를 768차원 벡터 $v_i$로 변환합니다.
3.  **Document Centroid**: 문서 전체의 의미 중심 벡터 $C$를 계산합니다.
    ```math
    C = \frac{1}{N} \sum_{i=1}^{N} v_i
    ```
4.  **Ranking**: 각 문장과 중심 벡터 간의 **코사인 유사도(Cosine Similarity)**를 계산합니다.
    ```math
    Sim(v_i, C) = \frac{v_i \cdot C}{\|v_i\| \|C\|}
    ```
5.  **Selection**: 유사도가 가장 높은 상위 $k=3$개 문장만 원문 순서대로 재조합합니다.

---

# Part 4: 특성 공학 (Feature Engineering)

## 10. 🧮 TF-IDF Vectorization: N-gram(1,3) 전략

### 🧬 왜 1-gram이 아닌가?
한국어는 문맥 의존성이 강합니다.
- "상승" (1-gram): 좋음.
- "상승 제한" (2-gram): 나쁨.
- "상승세 둔화 우려" (3-gram): 매우 나쁨.

### ⚙️ 설정값 (Verified in Code)
- **N-gram**: `(1, 3)` (Unigram부터 Trigram까지)
- **Max Features**: `25,000` (메모리 효율과 성능의 타협점)

## 11. ⏳ 시차 효과 (Lag Features): 정보의 반감기

### 🕒 뉴스의 수명
오늘 나온 뉴스는 내일, 모레까지 주가에 잔존 영향을 미칩니다. 이를 모델링하기 위해 **Lag Feature**를 생성합니다.
- `word_L1`: 어제 뉴스의 단어 빈도
- `word_L2`: 그제 뉴스의 단어 빈도
- ...
- `word_L5`: 5일 전 뉴스의 단어 빈도

이로 인해 특성의 개수는 $N_{features} \times N_{lags}$로 증가하지만, 시간의 흐름에 따른 인과의 궤적을 포착할 수 있습니다.

## 12. 📉 동적 감쇠 (Dynamic Decay): 시간 가중치 로직

### 📻 오래된 뉴스는 잊혀진다
5일 전 뉴스가 오늘 뉴스만큼 중요할 수는 없습니다. 우리는 지수 감쇠(Exponential Decay)를 적용합니다.

```math
Weight_t = e^{-\lambda \times t}
```
여기서 $\lambda$(Decay Rate)는 AWO 엔진이 찾아낸 "현재 시장의 망각 속도"입니다.
- **급변하는 시장**: $\lambda$가 큼 (빨리 잊혀짐).
- **안정적인 시장**: $\lambda$가 작음 (오래 기억됨).

## 13. 🦢 Black Swan 필터링: 희귀 단어 보호

### 🦢 희소성 vs 중요성
보통 `min_df=3`으로 희소 단어를 지우지만, "전쟁", "화재", "횡령" 같은 단어는 6개월에 딱 한 번 등장해도 주가를 폭락시킵니다.
이를 **Black Swan Keywords**라고 하며, `lasso.py`에는 `CRITICAL_WORDS` 세트가 정의되어 있어 이 단어들은 빈도와 상관없이 **절대 삭제되지 않도록(Whitelist)** 보호됩니다.

---

# Part 5: 핵심 알고리즘 (Core Algorithms)

## 14. 📐 Lasso 회귀의 수학적 원리 (L1 Regularization)

### 🎯 Objective Function
Lasso(Least Absolute Shrinkage and Selection Operator)는 다음 목적 함수를 최소화합니다.

```math
\min_{\beta} \left( \frac{1}{2N} \| y - X\beta \|_2^2 + \alpha \| \beta \|_1 \right)
```

- **MSE 항 ($\| y - X\beta \|_2^2$)**: 예측 오차를 줄입니다.
- **L1 Penalty ($\alpha \| \beta \|_1$)**: 가중치들의 절댓값 합을 줄입니다.

이 L1 Penalty의 기하학적 특성(마름모 꼴 제약 조건)으로 인해, 최적해의 많은 $\beta_i$가 **정확히 0**이 됩니다. 이것이 Lasso가 "Feature Selector"로 불리는 이유입니다.

## 15. ⚡ Celer 엔진: Working Set 알고리즘

### 🏎️ 문제: 피처가 너무 많다
25,000개 피처 × 5 Lags = 125,000개 변수. 이를 매번 다 계산하는 것은 낭비입니다.

### 💡 해결: Working Set Strategy
1.  **Dual Gap Check**: KKT 조건(최적화 조건)을 위반하는 정도를 계산합니다.
2.  **Working Set 구성**: 위반 정도가 큰(즉, 0이 아닐 확률이 높은) 상위 100개 변수만 고릅니다.
3.  **Sub-problem Solve**: 100개 변수만으로 작은 Lasso 문제를 풉니다.
4.  **Repeat**: 전체 변수에서 다시 위반 여부를 체크합니다.

**Celer** 라이브러리는 이 과정을 통해 전체 데이터를 다루는 것보다 **10~100배** 빠르게 수렴합니다.

## 16. 🚀 MLX 가속: Metal GPU 연산 구현

### 🍎 GPU에서의 Lasso
Apple Silicon의 GPU를 활용하기 위해 우리는 **Soft Thresholding Operator**를 Metal Shader로 구현했습니다.

```python
# Pseudo-code for Soft Thresholding
def soft_threshold(x, lambda_):
    return sign(x) * maximum(abs(x) - lambda_, 0)
```

`src/learner/mlx_lasso.py`는 이 연산을 행렬 단위로 병렬 처리하여, 수천 개의 윈도우를 동시에 백테스팅할 때 압도적인 성능을 발휘합니다.

## 17. ⚖️ 하이브리드 앙상블 (Hybrid Ensemble): 6:4의 황금비

### 🤝 The Best of Both Worlds
- **Model A (Lasso)**: 키워드 기반. 설명력이 좋음. (Weight: 0.6)
- **Model B (BERT-Ridge)**: 문맥 기반. 뉘앙스를 파악함. (Weight: 0.4)

```math
P_{final} = (0.6 \times P_{Lasso}) + (0.4 \times P_{BERT}) + \alpha_{bias}
```

이 가중치는 수많은 실험을 통해 도출된 경험적 최적값(Empirical Best)입니다. Lasso에 더 높은 비중을 두는 이유는 **설명 가능성(Explainability)**을 유지하기 위함입니다.

---

# Part 6: AWO 엔진 (Adaptive Window Optimization)

## 18. 🌊 시장의 비정상성 (Regime Shift) 대응

### 🔄 시장은 살아물이다
"금리 인상"은 2018년엔 악재였지만, 2024년엔 경기 회복의 신호로 해석될 수도 있습니다.
고정된 기간(예: 1년)만 학습하는 모델은 이러한 **체제 전환(Regime Shift)**에 적응하지 못합니다.

## 19. 🔍 2D Grid Search: Window x Alpha

AWO 엔진(`src/learner/awo_engine.py`)은 매주 토요일 다음 두 가지 파라미터의 최적 조합을 탐색합니다.

1.  **Window Size**: 학습 데이터 기간 (1, 3, 6, 12개월)
2.  **Alpha**: 규제 강도 ($10^{-3}, 10^{-4}, 10^{-5}$)

총 $4 \times 3 = 12$가지 시나리오를 과거 데이터에 대해 시뮬레이션(Backtest)합니다.

## 20. 📏 안정성 점수 (Stability Score) 공식

단순히 수익률(Hit Rate) 1등인 파라미터를 고르면 **과적합(Overfitting)**일 수 있습니다. 우리는 **안정성**을 중시합니다.

```math
Stability = \mu(HitRate) - \gamma \cdot \sigma(HitRate)
```

- $\mu(HitRate)$: 해당 설정의 평균 적중률.
- $\sigma(HitRate)$: 해당 설정 인근(Neighbor parameters)에서의 성능 표준편차.
- **의미**: "주변 파라미터가 조금 바뀌어도 여전히 성능이 좋은가?" (즉, Local Optima가 뾰족하지 않고 완만한가?)

## 21. 🏆 자동 승격 (Promotion) 메커니즘

1.  **Scanning**: 모든 조합의 Stability Score 계산.
2.  **Ranking**: 점수 1위 조합 선정 (Golden Parameter).
3.  **Promotion**: 해당 파라미터로 전체 데이터를 재학습하여 `Main Model`로 교체.
4.  **Logging**: 모든 과정은 DB에 기록되어 추후 감사(Audit) 가능.

---

# Part 7: 메모리 최적화 (Memory Optimization)

## 22. 💥 OOM 사건 분석 (Case Study)
### 🚨 Incident Report
- **상황**: 삼성전자 12개월분 뉴스(약 20만 건) 학습 시도.
- **현상**: Python 프로세스 메모리가 12GB를 초과하며 `Killed: 9` 발생.
- **원인**:
    1.  모든 텍스트를 `list`에 담아 RAM에 올림.
    2.  `TfidfVectorizer`가 중간 생성물(Document-Term Matrix)을 Dense하게 처리하려 함.

## 23. 🚿 Generator Streaming: 버퍼 제거
**Fix 1**: 데이터를 리스트에 담지 않고, DB 커서에서 한 줄씩 읽어 바로 Vectorizer에 넘기는 **Generator Pattern**을 적용했습니다 (REQ-MEM-02).

```python
def text_generator():
    for row in db_cursor:
        yield process(row['content'])

# No explicit list in memory!
vectorizer.fit(text_generator())
```

## 24. 🌳 Vocabulary Pruning: Min_df와 Max_df
**Fix 2**: 불필요한 단어를 초장에 잘라냅니다.
- **min_df=3**: 오타 제거. 단어장 크기 40% 감소.
- **max_df=0.85**: 불용어(Stopwords) 제거.

## 25. 📉 Max Features 최적화: 25,000의 법칙
**Fix 3**: `max_features`를 50,000에서 25,000으로 줄였습니다.
- **연구 결과**: 학술적으로도 8,000~15,000개 피처면 감성 분석에 충분합니다. BERT 요약으로 핵심 단어 밀도가 높아졌기 때문에 25,000개면 차고 넘칩니다.

---

# Part 8: 프론트엔드 (Frontend)

## 26. 🌐 HTMX: Hypermedia-Driven Architecture

### 🚫 No React, No Build
본 프로젝트는 **데이터 중심**입니다. 복잡한 클라이언트 상태 관리가 필요 없습니다.
HTMX를 사용하여 HTML 속성만으로 AJAX 요청을 처리합니다.

```html
<div hx-get="/api/news" hx-trigger="load" hx-swap="innerHTML">
  Loading...
</div>
```
이 코드는 페이지 로드 시 `/api/news`를 호출하고, 응답받은 HTML 조각으로 `div` 내용을 교체합니다. JavaScript 한 줄 없이 비동기 UI를 구현했습니다.

## 27. 💎 Glassmorphism UI: 금융 대시보드의 미학
- **Backdrop Filter**: `blur(10px)` 효과로 배경이 은은하게 비치는 유리 질감 구현.
- **Grid System**: CSS Grid로 복잡한 차트와 테이블을 완벽하게 정렬.
- **Responsive**: 모바일에서도 깨지지 않는 유동적 레이아웃.

---

# Part 9: 옵저버빌리티 (Observability)

## 28. 🔭 Prometheus & cAdvisor: 풀스택 모니터링
Docker 컨테이너들의 건강 상태를 실시간으로 감시합니다.
- **cAdvisor**: 컨테이너별 CPU, Memory, Network I/O 수집.
- **Node Exporter**: 호스트 머신의 전체 리소스 수집.

## 29. 📊 Grafana 대시보드: 시계열 시각화
Prometheus가 수집한 데이터를 시각화합니다.
- **Worker Status 패널**: 현재 돌고 있는 크롤러 개수와 처리 속도.
- **Memory Leak 패널**: 메모리 사용량이 계단식으로 증가하는지 감시.

## 30. 🧟 좀비 워커 탐지 및 자가 치유 (Self-Healing)
네트워크 문제로 크롤러가 멈추는(Hang) 경우가 있습니다.
- **Heartbeat**: 워커는 1분마다 Redis에 생존 신고를 합니다.
- **Reaper**: 스케줄러는 생존 신고가 3분 이상 끊긴 워커를 발견하면 Docker API를 통해 해당 컨테이너를 **강제 재시작**합니다.

---

# Part 10: 운영 가이드 (Operations)

## 31. 🐳 Docker Compose 토폴로지 (17 Containers)
`docker-compose.yml`은 전체 시스템의 설계도입니다.

| 서비스 | 개수 | 역할 |
|--------|------|------|
| `postgres` | 1 | 메인 데이터베이스 |
| `redis` | 1 | 메시지 브로커 & 캐시 |
| `rabbitmq` | 1 | 작업 대기열 |
| `dashboard` | 1 | 웹 서버 |
| `news_collector` | 4 | 뉴스 수집 (병렬) |
| `news_processor` | 4 | 뉴스 처리 (병렬) |
| `verification` | 2 | 모델 검증 |
| `scheduler` | 1 | 작업 관리 |
| `monitoring` | 2 | Prom + Grafana |

총 17개의 컨테이너가 오케스트라처럼 협연합니다.

## 32. 🔑 환경 변수 설정 (Configuration)
`.env` 파일에서 모든 설정을 관리합니다.
- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`
- `OPENAI_API_KEY` (Optional)
- `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`

## 33. 🚀 시작하기 (Getting Started)

### Prerequisites
- Docker Desktop installed
- Git installed
- 16GB+ RAM recommended (Minimum 8GB)

### Step-by-Step
1.  **Clone Repository**
    ```bash
    git clone https://github.com/silverwoods-dev/N-SentiTrader.git
    cd N-SentiTrader
    ```

2.  **Environment Setup**
    ```bash
    cp .env.example .env
    # .env 파일을 열어 API 키 등을 수정하세요.
    ```

3.  **Build & Run**
    ```bash
    docker-compose up -d --build
    ```

4.  **Verify**
    - Dashboard: `http://localhost:8081`
    - Grafana: `http://localhost:3000`

---

### Appendix A: Code Gallery

#### 1. Lasso 학습 (`src/learner/lasso.py`)
```python
def train(self, X, y):
    # Celer를 활용한 고속 학습
    model = celer.Lasso(
        alpha=self.alpha,
        max_iter=100,
        verbose=False
    )
    model.fit(X, y)
    
    # 0이 아닌 계수(단어)만 추출
    coefs = model.coef_
    nonzero_indices = np.where(coefs != 0)[0]
    return coefs[nonzero_indices]
```

#### 2. Relevance Scoring (`src/analysis/news_filter.py`)
```python
def calculate_score(title, content):
    score = 0
    if target_name in title: score += 50
    if target_name in content[:200]: score += 20
    
    count = content.count(target_name)
    score += min(count * 5, 20)
    
    return score
```

### Appendix B: Troubleshooting

**Q: 크롤러가 작동하지 않아요.**
A: 네이버 API 할당량(일 25,000건)을 초과했는지 확인하세요. RabbitMQ 관리자 페이지(`localhost:15672`)에서 큐가 쌓여있는지 확인하세요.

**Q: 학습 중 OOM이 발생해요.**
A: `.env`에서 `MAX_FEATURES`를 15,000으로 낮추거나, `BATCH_SIZE`를 줄여보세요.

### Appendix C: Development History (31 Steps)

- **v1.0**: 기본 뉴스 수집 및 저장.
- **v2.0**: 형태소 분석 및 TF-IDF 구현.
- **v3.0**: Lasso 모델 도입 및 감성 사전 구축.
- **v4.0**: BERT 요약 및 하이브리드 모델링.
- **v5.0**: AWO 엔진 및 안정성 점수 도입 (현재).

---

> **Copyright © 2025 Team Silverwoods.**
> *Dedicated to the Future AI Engineers.*
