# N-SentiTrader (N-센티트레이더)

## 🚀 한국어 뉴스 기반 주식 감성 분석 및 하이브리드 예측 시스템

> **[교육용 프로젝트]** 본 프로젝트는 AI 서비스 개발자 양성과정의 훈련생들을 위해 설계된 <b>'화이트박스(White-Box) 머신러닝'</b> 기반의 실무형 주식 예측 플랫폼입니다.

[![GitHub Repo](https://img.shields.io/badge/GitHub-N--SentiTrader-blue?style=flat-square&logo=github)](https://github.com/silverwoods-dev/N-SentiTrader)
[![Python Version](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-Framework-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker)](https://www.docker.com)

---

## 📋 목차
1. [프로젝트 철학: 왜 화이트박스인가?](#프로젝트-철학-왜-화이트박스인가)
2. [전처리 파이프라인 (BERT & 필터링)](#전처리-파이프라인-bert--필터링)
3. [핵심 알고리즘: Lasso 회귀와 감성 사전](#핵심-알고리즘-lasso-회귀와-감성-사전)
4. [AWO (Adaptive Window Optimization) 엔진](#awo-adaptive-window-optimization-엔진)
5. [시스템 아키텍처 및 마이크로서비스 설계](#시스템-아키텍처-및-마이크로서비스-설계)
6. [빠른 시작 가이드](#빠른-시작-가이드)
7. [향후 과제 및 한계점](#향후-과제-및-한계점)

---

## 🏛️ 프로젝트 철학: 왜 화이트박스인가?

본 프로젝트는 입문자들이 AI의 블랙박스(Black-Box) 안을 들여다보고, <b>"왜 이 모델이 BUY 신호를 보냈는가?"</b> 에 대해 수학적/논리적 근거를 제시할 수 있도록 설계되었습니다.

### 1. 설명 가능성 (XAI, Explainable AI)
- **전통적 ML vs. LLM**: 최근 LLM(GPT-4 등)은 높은 성능을 보이지만, 그 판단 근거를 추적하기 어렵습니다. 
- **Lasso 회귀의 역할**: Lasso(L1 규제)는 불필요한 단어의 가중치를 0으로 만듭니다. 결과적으로 <b>수익률에 직접적인 기여를 하는 핵심 키워드(Feature)</b>만 살아남아, 사용자가 직접 감성 사전을 눈으로 확인하고 검증할 수 있습니다.

### 2. 학습 효율성
- **일반 PC 환경**: 수억 개의 파라미터를 가진 모델 대신, 수만 개의 토큰을 다루는 경량 모델을 통해 일반적인 데스크탑 환경에서도 전체 학습-검증-배포 루프를 경험할 수 있습니다.

> **[Industry Trend]** 금융 업계는 규제와 투명성을 중시하므로, 단순히 예측력이 높은 모델보다 <b>"설명 가능한 모델"</b>을 선호하는 경향이 있습니다. (XAI는 핀테크 보안 및 심사 분야의 핵심 트렌드입니다.)

---

## 🛠️ 전처리 파이프라인 (BERT & 필터링)

데이터의 노이즈를 제거하고 정확도를 높이기 위해 다음과 같은 고도화된 전처리를 수행합니다.

### 🧠 BERT 기반 뉴스 추출 요약 (`NewsSummarizer`)
대부분의 뉴스 기사에는 기자명, 사진 설명, 지난 뉴스 요약 등 불필요한 정보가 30~50%를 차지합니다.
- **작동 원리**: `KR-FinBERT`를 사용하여 문장별 임베딩을 생성한 후, 전체 문서의 중심 벡터와 가장 유사한(Global Importance) **상위 3개 문장**을 추출합니다.
- **도입 효과**: 텍스트의 핵심(Main Topic)에 집중함으로써 Lasso 모델이 가짜 상관관계(Spurious Correlation)에 빠지는 것을 방지합니다.

### 🎯 종목 관련도 필터링
- 모든 뉴스를 무분별하게 학습하지 않습니다. 뉴스 내 종목명의 출현 빈도와 위치 기반의 **Relevance Score**를 계산하여, 특정 임계값 이상의 뉴스만 학습 데이터로 포함시킵니다.

---

## 📈 핵심 알고리즘: Lasso 회귀와 감성 사전

### L1 정규화(Lasso)를 선택한 이유
주식 뉴스는 <b>희소성(Sparsity)</b>이 강합니다. 하루에 수천 개의 단어가 언급되지만, 실제 주가에 영향을 미치는 단어는 소수입니다.
- **수식**: $minimize: ||y - X\beta||^2 + \alpha||\beta||_1$
- **특징**: $\alpha$ 값이 커질수록 영향력이 적은 단어의 $\beta$(가중치)는 정확히 0이 됩니다. 이는 모델이 가볍고 명확해지는 효과를 줍니다.

### Hybrid v2 모델 (감성 + 기술적 지표)
단순 뉴스 감성만으로는 <b>기술적 매물대(Support/Resistance)</b>를 설명할 수 없습니다. 
- **Combined Features**: 뉴스 감성 점수에 **RSI(14), MACD, 이동평균선** 데이터를 결합하여 정성적 데이터(뉴스)와 정량적 데이터(차트)를 동시에 반영합니다.

---

## 🎯 AWO (Adaptive Window Optimization) 엔진

시장은 항상 변합니다. 1년 전의 데이터가 지금도 유효할까요? AWO는 이 질문에 답하기 위해 개발되었습니다.

### 1. 2차원 그리드 서치 (Window × Alpha)
- **Window (3~12개월)**: 모델이 기억해야 할 과거의 길이를 탐색합니다.
- **Alpha (규제 강도)**: 단어 사전을 얼마나 엄격하게 관리할지 결정합니다.

### 2. 도입 이유와 타당성
금융 시장은 <b>비정상성(Non-stationarity)</b>을 띱니다. AWO는 최근 시장의 패턴에 가장 적합한 윈도우 크기를 <b>Walk-Forward Validation</b>을 통해 동적으로 산출하여, 모델이 시장의 변화(<b>Regime Shift</b>)에 즉각 대응할 수 있게 합니다.

---

## 🏗️ 시스템 아키텍처 및 마이크로서비스 설계

프로젝트는 **안정성**과 **확장성**을 위해 17개의 Docker 컨테이너로 구성된 마이크로서비스 아키텍처(MSA)를 지향합니다.

### 각 워커(Worker)의 역할
- **Address Worker**: 새로운 뉴스의 URL을 발견하고 큐에 삽입 (경량/고속)
- **Body Worker**: 뉴스 본문을 스크랩하고 클린징 (I/O 집중)
- **Summarizer (BERT)**: 딥러닝 모델로 요약 생성 (GPU/메모리 집중)
- **Learner (AWO)**: ML 학습 및 검증 루프 자동화 (CPU 멀티코어 집중)

### 왜 MSA인가?
1. **자원 격리**: BERT 모델은 많은 GPU 메모리(또는 RAM)를 소모합니다. 크롤링 워커와 분리함으로써 하나가 죽어도 시스템 전체가 붕괴되지 않습니다.
2. **기술 다양성**: 크롤링은 고성능 비동기 라이브러리를, 학습은 `scikit-learn`과 `polars`를 사용하는 등 각 파트에 최적화된 언어/라이브러리를 독립적으로 사용할 수 있습니다.
3. **병렬성**: `RabbitMQ`를 통한 작업 분배로, 수집량이 늘어나면 워커 컨테이너 수만 늘려 대응할 수 있습니다.

---

## 🚀 빠른 시작 가이드

```bash
# 1. 저장소 클론 및 설정
git clone https://github.com/silverwoods-dev/N-SentiTrader.git
cd N-SentiTrader
cp .env.sample .env

# 2. 실행 (Docker 필요)
docker-compose up -d --build

# 3. 데이터 동기화
docker exec -it n_senti_dashboard python -m src.scripts.sync_stock_master
```

---

## ⚠️ 향후 과제 및 한계점

- **선형 모델의 한계**: Lasso는 선형 회귀이므로 단어 간의 복잡한 상호작용(예: "호재인 줄 알았으나 악재")을 완벽히 포착하기 어렵습니다. 이를 보완하기 위해 BERT 임베딩 비중을 높이는 연구가 필요합니다.
- **지연 시간(Latency)**: BERT 요약 및 모델 최적화에는 상당한 시간이 소요됩니다. 실시간 대응을 위해 경량화(Quantization) 기술 도입이 필요합니다.
- **데이터 편향**: 뉴스 제목의 자극적인 헤드라인(Clickbait)이 모델에 과적합(Overfitting)될 위험이 있습니다.

---

### 👨‍💻 기여 및 문의
본 프로젝트는 교육적 목적을 위해 상시 열려 있습니다. 궁금한 점이나 제안 사항은 Issue를 통해 남겨주세요.

*Designed for the Next Generation of AI Developers.*
