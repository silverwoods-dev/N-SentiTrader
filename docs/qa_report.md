# Multi-Target Integration Test Report (Task-028)

**Date:** 2025-12-19
**Target:** SK Hynix (000660)
**Tester:** N-SentiTrader Agent

## 1. Objective
Verify the end-to-end functionality of N-SentiTrader for a secondary stock target (SK Hynix) to ensure system scalability and multi-target capabilities.

## 2. Test Scope
1.  **Backfill Process:** Triggering and execution of historical data collection.
2.  **Data Pipeline:** Normalization, Tokenization, and Dictionary Construction (Buffer).
3.  **Prediction:** Sentiment scoring and directional prediction generation.
4.  **Display:** Dashboard API availability.

## 3. Execution Results

### 3.1 Data Collection (Backfill)
-   **Job ID:** 48
-   **Status:** Completed
-   **Data Points:** ~141 articles (Limited by recent "Rapid Mode" backfill test, but sufficient for pipeline verification).
-   **Validation:**
    -   `tb_news_url`: URLs collected via `address_worker` (Naver News).
    -   `tb_news_content`: Body text collected via `body_worker`.

### 3.2 Dictionary Construction (Daily Buffer)
-   **Process:** `AnalysisManager.run_daily_update()`
-   **Result:** Success
-   **Metrics:**
    -   Training Data: Dec 12 - Dec 19 (Last 7 days)
    -   Features: 250,000+ extracted -> 5,249 filtered.
    -   Saved to `tb_sentiment_dict` (Source: Buffer, Version: daily_buffer).

### 3.3 Prediction
-   **Process:** `Predictor.predict_advanced()`
-   **Method:** Buffer-only prediction (due to insufficient long-term data for Main Dictionary).
-   **Result:**
    -   **Date:** 2025-12-19
    -   **Score:** -0.0718 (Negative Sentiment)
    -   **Prediction:** DOWN (0)
    -   **Top Keywords:** "SK" (Negative weight observed)

### 3.4 API / Dashboard
-   **Endpoint:** `GET /api/reports/000660/2025-12-19`
-   **Response:**
    ```json
    {
      "stock_code": "000660",
      "stock_name": "SK하이닉스",
      "date": "2025-12-19",
      "score": -0.07180804100108262,
      "prediction": "DOWN",
      "top_keywords": {
        "negative": [{"word": "SK", "weight": -0.0042...}],
        "positive": []
      }
    }
    ```
-   **Conclusion:** The system correctly serves prediction results for the new target.

## 4. Observations & Recommendations
-   **Timezone Handling:** There is a discrepancy between stored UTC timestamps and "Current Date" querying logic in `Predictor`. It is recommended to standardize on KST or explicitly handle timezone conversions in the SQL queries for daily prediction.
-   **Data Consistency:** Ensure `collect_stock_history` is run for all new targets to enable Main Dictionary training (which requires price data).
-   **Resource Scaling:** Workers successfully scaled to handle the new job without varying configuration.

## 5. Conclusion
The N-SentiTrader system successfully handled the addition of a new stock target. The core pipeline from collection to prediction is functional for multiple targets.
