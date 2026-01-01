# MLX 기반 Lasso 학습 엔진 구축 요구분석 및 리서치 보고서

## 1. 개요
현재 `celer`를 통해 CPU 기반 Coordinate Descent로 Lasso 학습 속도를 혁신적으로 개선했으나, Apple Silicon(M-series)의 GPU 성능을 극한으로 활용하기 위해 `MLX` 기반의 새로운 엔진을 구축하고자 합니다.

## 2. MLX 프레임워크 분석
- **Unified Memory:** CPU와 GPU가 동일한 메모리 풀을 공유하여 데이터 전송 오버헤드가 거의 없음.
- **Array API:** NumPy/PyTorch와 유사한 직관적인 API 제공.
- **Lazy Computation:** 계산 그래프를 효율적으로 최적화하여 실행.
- **Sparse Matrix 지원 현황:** 현재 MLX는 Dense Tensor 연산에 최적화되어 있으며, 고수준의 Sparse Lasso API는 부재함.

## 3. 알고리즘 설계: ISTA/FISTA
Lasso의 L1 규제항은 미분이 불가능하므로, 경사하강법(GD) 대신 **ISTA (Iterative Soft Thresholding Algorithm)** 또는 가속화된 버전인 **FISTA**를 사용합니다.

### 핵심 수식 (ISTA)
1. **Gradient Step:** $w_{t+1/2} = w_t - \eta \nabla f(w_t)$ (Smooth part: MSE Loss)
2. **Proximal Step (Soft Thresholding):** $w_{t+1} = S_{\eta \lambda}(w_{t+1/2})$
   where $S_a(x) = \text{sign}(x) \max(|x| - a, 0)$

## 4. 데이터 규모 및 메모리 적합성 검토
- **데이터 형상:** 약 120~150일 (Rows) x 40,000~50,000 피처 (Columns).
- **메모리 계산:** $150 \times 50,000 \times 4 \text{ bytes (float32)} \approx 30 \text{ MB}$.
- **결론:** MLX의 Dense Matrix 연산으로도 충분히 핸들링 가능한 크기이며, GPU 병렬 연산을 통한 비약적인 속도 향상이 기대됨.

## 5. 구현 계획 (3FS)
- **PRD:** `MLX 엔진` 섹션 추가.
- **TASK:** MLX 환경 구축 및 FISTA 알고리즘 구현 태스크 정의.
- **Implementation:** `src/learner/mlx_lasso.py` 신규 구축 및 `awo_engine.py` 연동.

---
**작성일:** 2025-12-31  
**담당:** Antigravity (AI Assistant)
