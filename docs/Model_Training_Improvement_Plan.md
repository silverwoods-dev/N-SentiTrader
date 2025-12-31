# 학습 모델 개선 작업 계획 보고서 (Model Training Improvement Work Plan)

## 1. 개요 및 배경
본 보고서는 Apple Silicon M1 환경에서 대규모 뉴스 데이터(10만 건 이상)를 활용한 Lasso 회귀 학습 시 발생하는 병목 현상을 해결하고, 학습 성능을 비약적으로 향상시키기 위한 구체적인 실행 계획을 제안합니다. 현재 Scikit-learn 기반의 학습 방식은 M1의 하드웨어 잠재력을 충분히 활용하지 못하고 있으며, 특히 다차원 종속 변수(수익률, 재무 지표 등) 처리 시 기하급수적으로 증가하는 연산 시간을 단축하는 것이 핵심 목표입니다.

## 2. 현황 분석 및 병목 지점
*   **알고리즘적 한계**: Scikit-learn의 Lasso는 '좌표 하강법(Coordinate Descent)'을 사용하며, 이는 본질적으로 순차적(Sequential)인 특성을 가집니다. CPU 10코어를 모두 점유하더라도 이는 개별 모델의 학습 가속이 아닌, 교차 검증(Cross-validation) 폴드의 병렬 처리에 한정됩니다.
*   **고차원 희소 데이터 처리**: n-gram(Bigram 등) 적용 시 독립 변수의 개수가 수백만 개에 달하며, Scikit-learn의 표준 솔버는 이러한 초대형 희소 행렬(Sparse Matrix) 최적화에 한계가 있습니다.
*   **하드웨어 활용 미흡**: M1의 GPU(MPS) 및 NPU(Neural Engine)가 Lasso와 같은 전통적인 1차 통계 모델 학습에 직접적으로 기여하지 못하고 있습니다.

## 3. 기술적 검증 및 해결 방안 (Research-based)
웹 리서치와 공식 레퍼런스를 통해 검증된 최적화 방안은 다음과 같습니다.

### A. Celer 라이브러리 도입 (Pragmatic Path)
*   **원리**: Gap Safe Screening Rules 및 Working Set 기법을 적용하여, 실제로 유의미한 변수(Active Set)에 연산을 집중합니다.
*   **성능**: Scikit-learn 대비 **10배~100배** 빠른 속도를 제공하며, `MultiTaskLasso` 및 희소 행렬(CSR/CSC)을 완벽하게 지원합니다.
*   **일관성**: 수학적으로 동일한 목적 함수를 최적화하므로, 기존 구축된 '단어 감성 사전'의 품질과 일관성을 보장합니다.

### B. Apple MLX 프레임워크 활용 (High-Performance Path)
*   **원리**: Apple Silicon의 Unified Memory 가속을 극대화하며, GPU를 통한 병렬 연산(Gradient Descent 계열)을 수행합니다.
*   **장점**: CPU-GPU 간 데이터 복사 오버헤드가 없으며, 매우 큰 행렬 연산에서 압도적인 효율을 보입니다. 단, 희소 행렬을 직접 최적화하려면 커스텀 커널 구현이 필요할 수 있습니다.

## 4. 단계별 실행 계획 (Action Plan)

### [Phase 1] 즉각적 성능 가속 (1-2주)
*   **`celer` 패키지 설치 및 통합**: 기존 `src/learner/lasso.py`의 `Lasso`, `LassoCV`를 `celer` 계열로 교체합니다.
*   **하드웨어 프로파일링**: M1 Pro/Max 환경에서 `n_jobs` 설정을 최적화하여 메모리 대역폭 점유율을 조정합니다.
*   **수렴 조건(`tol`) 미세 조정**: 성능 저하 없는 범위 내에서 `tol` 값을 `1e-4`~`1e-3` 사이로 최적화하여 학습 시간을 추가 단축합니다.

### [Phase 2] 모델 확장 및 다차원 학습 (3-4주)
*   **`MultiTaskLasso` 활성화**: 주가 수익률뿐만 아니라 PER/PBR 변화액 등 재무 지표를 동시에 종속 변수로 두어, 감성 사전의 입체적 품질을 높입니다.
*   **Feature Selection 고도화**: `celer`의 Working Set 정보를 활용하여 불필요한 n-gram 단어를 조기에 제거하는 전처리 파이프라인을 강화합니다.

### [Phase 3] 하드웨어 특화 최적화 (향후 과제)
*   **MLX 기반 가속기 개발**: 초거대 데이터셋 대응을 위해 MLX를 활용한 전용 Lasso Solver 프로토타입을 구축합니다.
*   **NPU/GPU 하이브리드 전략**: 데이터 로딩은 Unified Memory로, 단순 연산은 GPU로 분산 처리하는 구조를 설계합니다.

## 5. 기대 효과
*   **학습 시간 단축**: 현재 수 시간 소요되는 10만 건 뉴스 학습을 **10분 내외**로 단축 (생산성 1,000% 향상).
*   **모델 정교화**: 빨라진 학습 속도를 바탕으로 더 넓은 범위의 하이퍼파라미터 탐색(Grid Search)이 가능해져 예측 성능(IC/IR) 향상.
*   **리소스 효율성**: CPU 발열 및 전력 소모 감소, 학습 중 시스템 응답성 확보.

---
**작성일**: 2025년 12월 31일
**보고자**: Antigravity (Advanced AI Coding Agent)
