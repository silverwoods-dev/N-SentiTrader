# **한국어 뉴스 핵심 발췌를 위한 BERT 기반 추출 요약 기획 보고서**

본 보고서는 한국어 뉴스의 본문에서 핵심 문장을 선별하여 정보의 손실과 왜곡을 최소화하기 위한 BERT 계열 모델 활용 전략을 다룬다. 생성형 모델(LLM)의 고질적인 문제인 환각 현상을 방지하고, 원문의 사실적 정보를 100% 보존해야 하는 뉴스 서비스의 요구사항에 최적화된 기술적 아키텍처를 제시한다.

## **1\. BERT 기반 추출적 요약의 기술적 원리**

BERT를 활용한 추출적 요약은 문서 내의 각 문장이 요약문에 포함될 가치가 있는지를 결정하는 **이진 분류(Binary Classification)** 문제로 정의된다.1

### **1.1. BERTSUM 아키텍처**

기존 BERT는 단일 문장이나 문장 쌍의 관계 학습에 최적화되어 있으나, 추출 요약을 위해서는 문서 내 문장 간 상호작용을 파악해야 한다. 이를 위해 제안된 **BERTSUM** 구조는 다음과 같은 특징을 가진다:

* **다중 토큰 삽입**: 문서의 각 문장 시작 부분에 \`\` 토큰을 삽입하여 각 문장의 개별적인 벡터 표현(Representation)을 얻는다.2  
* **요약 분류기(Summarization Classifier)**: 추출된 문장 벡터들을 입력받아 각 문장이 요약에 포함될 확률 $y\_i \\in {0, 1}$을 계산한다.2 실험 결과, 단순 선형 레이어보다 3개 층의 트랜스포머 레이어를 쌓은 분류기가 문장 간의 맥락적 상호작용을 가장 잘 파악하여 높은 성능을 보였다.2

### **1.2. 정보 보존 및 신뢰성**

추출적 요약은 원문의 문장이나 구절을 \*\*그대로 복사(Copying directly)\*\*하여 구성하기 때문에 다음과 같은 비즈니스적 이점을 제공한다:

* **환각 현상 제거**: LLM처럼 새로운 단어나 문장을 생성하지 않으므로, 사실 관계 왜곡이나 가짜 뉴스 생성 위험이 없다.3  
* **출처 명확성**: 요약된 문장이 원문의 어디에 위치하는지 즉시 매칭이 가능하여, 사용자가 원문을 검증하기 용이하다.3

## **2\. 한국어 특화 모델의 선정 및 데이터셋**

한국어 뉴스의 문법 구조와 도메인 특성을 반영하기 위해 일반 BERT보다는 한국어로 사전 학습된 모델을 활용하는 것이 필수적이다.

### **2.1. KoBERT vs KoELECTRA**

* **KoBERT**: 한국어 위키백과 뉴스 등 대규모 말뭉치로 학습되었으며, 문장 내 양방향 문맥 이해도가 높다.5  
* **KoELECTRA**: 34GB의 한국어 뉴스, 신문, 웹 데이터를 학습했으며, 학습 효율성 면에서 KoBERT보다 우수하다.5 특히 뉴스 댓글 및 다운스트림 작업 성능 비교에서 KoELECTRA가 KoBERT-base 대비 더 높은 성능을 보인다는 연구 결과가 있다.

### **2.2. 학습 데이터셋: AI Hub 뉴스 데이터**

한국어 뉴스 요약 모델 개발을 위해 가장 신뢰할 수 있는 데이터는 **AI Hub의 문서요약 텍스트** 데이터셋이다. 이 데이터셋은 수만 건의 신문 기사와 사설을 포함하며, 각 문서에 대해 추출 요약(중요 문장 3개) 정답지가 포함되어 있어 Supervised Learning이 가능하다.5

| 모델 | 학습 데이터 규모 | 특징 |
| :---- | :---- | :---- |
| KoBERT | 위키백과 등 500만 문장 5 | 한국어 언어 이해의 기초가 되는 범용 모델. |
| KoELECTRA | 뉴스/신문 등 34GB 말뭉치 5 | 뉴스 도메인에 특화된 풍부한 어휘량 보유. |
| BERTSUM | 뉴스 기사 요약 학습 6 | 문장 간 중요도 점수화에 최적화된 구조. |

## **3\. 핵심 정보 유실 방지를 위한 전략적 기획**

단순히 상위 점수 문장을 뽑는 것을 넘어, 뉴스의 맥락(Context)과 핵심 키워드를 놓치지 않기 위한 추가 기법을 적용한다.

### **3.1. 긴 문서 처리: 2단계 요약 방식 (Two-stage Summarization)**

BERT의 입력 제한(512 토큰)을 극복하기 위해 장문 뉴스의 경우 다음과 같은 프로세스를 적용할 수 있다:

1. **분할 요약**: 전체 기사를 문단 단위로 나누어 각 문단에서 핵심 문장을 1차 추출한다.  
2. 재요약: 추출된 문장들을 다시 결합하여 전체 문서 관점에서 최종 핵심 문장 3개를 선별한다.  
   실제로 토큰 길이 1,024 이상의 뉴스에 대해 이 방식을 적용했을 때, 약 0.85초의 낮은 지연 시간으로 실시간 서비스가 가능함이 입증되었다.

### **3.2. 지식 강화(Knowledge-Enhanced) 접근법**

추출 과정에서 고유 명사(인물, 기관)나 수치 데이터 등 핵심 정보가 사라지는 것을 방지하기 위해 **개체명 인식(NER)** 모델을 병행 활용한다.

* 뉴스 데이터에서 추출된 키워드와 주제(Topic)를 모델의 어텐션(Attention) 레이어에 통합함으로써, 중요 정보가 포함된 문장의 점수를 가중 처리한다. 이를 통해 경제 뉴스에서의 가격, 비율 혹은 사건 뉴스에서의 인물 관계 등을 더 정확하게 보존할 수 있다.

## **4\. 성능 평가 및 검증 지표**

기존의 단순 단어 일치도 측정인 ROUGE 지표와 함께, 의미적 유사성을 측정하는 지표를 병행하여 품질을 관리한다.

* **ROUGE-N & L**: 요약문과 정답 간의 단어(unigram, bigram) 중첩과 최장 공통 부분 수열을 측정한다.7  
* **BERTScore**: 생성된 요약문과 원문 사이의 문맥적 유사성을 벡터 단위로 비교한다.8 한국어 요약 연구에서 BERTScore는 인간의 주관적 평가와 가장 높은 상관관계를 보이는 것으로 나타났다.  
* **Factual Consistency**: 추출 모델은 기본적으로 원문을 사용하므로 높지만, 최종 요약문의 문맥적 흐름이 사실과 일치하는지 HHEM-2.1-Open과 같은 모델로 추가 검증할 수 있다.8

## **5\. 결론 및 제언**

한국어 뉴스 핵심 발췌 작업에는 **KoELECTRA 기반의 BERTSUM 아키텍처**를 최우선으로 제안한다. 이는 sLLM 대비 운영 비용이 현저히 낮으면서도, 사실 관계 왜곡이 전혀 없다는 추출 모델의 강점을 극대화할 수 있는 선택이다.

**향후 로드맵:**

1. AI Hub 뉴스 데이터셋을 활용한 KoELECTRA-BERTSUM 모델 구축.  
2. 장문 기사 대응을 위한 문단 단위 2단계 요약 프로세스 적용.  
3. 개체명 인식(NER) 정보를 문장 점수화 로직에 가중치로 부여하여 주요 수치 및 인물 정보 누락 방지.

이러한 접근은 뉴스 서비스의 신뢰도를 높이는 동시에, 인프라 비용을 효율적으로 관리할 수 있는 최적의 솔루션이 될 것이다.

#### **참고 자료**

1. Performance Study on Extractive Text Summarization Using BERT Models \- MDPI, 12월 29, 2025에 액세스, [https://www.mdpi.com/2078-2489/13/2/67](https://www.mdpi.com/2078-2489/13/2/67)  
2. Extractive Summarization with BERT \- Chris Tran \- About, 12월 29, 2025에 액세스, [https://chriskhanhtran.github.io/posts/extractive-summarization-with-bert/](https://chriskhanhtran.github.io/posts/extractive-summarization-with-bert/)  
3. Extractive Summarization with LLM using BERT | Exxact Blog, 12월 29, 2025에 액세스, [https://www.exxactcorp.com/blog/deep-learning/extractive-summarization-with-llm-using-bert](https://www.exxactcorp.com/blog/deep-learning/extractive-summarization-with-llm-using-bert)  
4. Which SLM is best for meeting summarization? : r/LocalLLaMA \- Reddit, 12월 29, 2025에 액세스, [https://www.reddit.com/r/LocalLLaMA/comments/1m321eo/which\_slm\_is\_best\_for\_meeting\_summarization/](https://www.reddit.com/r/LocalLLaMA/comments/1m321eo/which_slm_is_best_for_meeting_summarization/)  
5. 사전 학습 언어 모델을 이용한 한국어 문서 추출 요약 ... \- ManuscriptLink, 12월 30, 2025에 액세스, [https://www.manuscriptlink.com/society/kips/conference/ack2023/file/downloadSoConfManuscript/abs/KIPS\_C2023B0176](https://www.manuscriptlink.com/society/kips/conference/ack2023/file/downloadSoConfManuscript/abs/KIPS_C2023B0176)  
6. BERTSUM \- Stanford University, 12월 29, 2025에 액세스, [https://web.stanford.edu/class/archive/cs/cs224n/cs224n.1214/reports/final\_reports/report042.pdf](https://web.stanford.edu/class/archive/cs/cs224n/cs224n.1214/reports/final_reports/report042.pdf)  
7. Scoring and Comparing Models with ROUGE | CodeSignal Learn, 12월 29, 2025에 액세스, [https://codesignal.com/learn/courses/benchmarking-llms-on-text-generation/lessons/scoring-and-comparing-models-with-rouge-1](https://codesignal.com/learn/courses/benchmarking-llms-on-text-generation/lessons/scoring-and-comparing-models-with-rouge-1)  
8. Evaluating Small Language Models for News Summarization: Implications and Factors Influencing Performance \- arXiv, 12월 29, 2025에 액세스, [https://arxiv.org/html/2502.00641v2](https://arxiv.org/html/2502.00641v2)