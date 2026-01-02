# src/learner/awo_engine.py
import logging
import polars as pl
import numpy as np
from datetime import datetime, timedelta
from src.learner.validator import WalkForwardValidator
from src.db.connection import get_db_cursor
import json

logger = logging.getLogger(__name__)

class AWOEngine:
    def __init__(self, stock_code, use_sector_beta=False, model_type='tfidf'):
        self.stock_code = stock_code
        self.use_sector_beta = use_sector_beta
        self.model_type = model_type  # 'tfidf' or 'hybrid'
        self.validator = WalkForwardValidator(stock_code, use_sector_beta=use_sector_beta, model_type=model_type)

    def _save_checkpoint(self, v_job_id, window_months, alpha, hit_rate, mae):
        """각 윈도우/알파 조합 완료 후 체크포인트 저장 (Job 실패해도 복구 가능)"""
        try:
            with get_db_cursor() as cur:
                cur.execute("""
                    INSERT INTO tb_awo_checkpoints 
                    (v_job_id, stock_code, window_months, alpha, hit_rate, mae)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (v_job_id, window_months, alpha) 
                    DO UPDATE SET hit_rate = EXCLUDED.hit_rate, mae = EXCLUDED.mae, 
                                  created_at = CURRENT_TIMESTAMP
                """, (v_job_id, self.stock_code, window_months, alpha, hit_rate, mae))
            logger.info(f"  [Checkpoint] Saved: {window_months}m, alpha={alpha}")
        except Exception as e:
            logger.warning(f"  [Checkpoint] Failed to save: {e}")

    def run_exhaustive_scan(self, validation_months=1, v_job_id=None):
        """
        2차원 그리드 서치 (Window x Alpha) 및 안정성 평가 (Stability Score)
        """
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=validation_months * 30)
        
        # Grid Configuration
        # 3-12개월 범위로 세분화하여 최적 윈도우 탐색
        # 총 필요 데이터: window_months + validation_months (예: 12개월 윈도우 + 6개월 검증 = 18개월)
        windows = [3, 4, 5, 6, 7, 8, 9, 10, 11, 12]  # Months
        alphas = [1e-5, 5e-5, 1e-4, 5e-4]
        
        results = {} # Key: (window, alpha) -> metrics
        
        # 1. Verification Job 등록 (v_job_id가 없을 때만)
        if v_job_id is None:
            with get_db_cursor() as cur:
                cur.execute("""
                    INSERT INTO tb_verification_jobs (stock_code, v_type, params, status)
                    VALUES (%s, 'AWO_SCAN_2D', %s, 'running')
                    RETURNING v_job_id
                """, (self.stock_code, json.dumps({"windows": windows, "alphas": alphas, "val_months": validation_months})))
                v_job_id = cur.fetchone()['v_job_id']
        else:
            with get_db_cursor() as cur:
                cur.execute(
                    "UPDATE tb_verification_jobs SET status = 'running', started_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE v_job_id = %s",
                    (v_job_id,)
                )
        
        min_relevance = 0
        if v_job_id:
             with get_db_cursor() as cur:
                cur.execute("SELECT params FROM tb_verification_jobs WHERE v_job_id = %s", (v_job_id,))
                row = cur.fetchone()
                if row and row['params']:
                    params = row['params']
                    if isinstance(params, str):
                        params = json.loads(params)
                    min_relevance = params.get('min_relevance', 0)

        try:
            total_iterations = len(windows) * len(alphas)
            current_iter = 0
            
            for w in windows:
                # --- [MEMORY_OPT] Phase 9: Sequential Window Data Fetching ---
                # Instead of fetching everything for 12 months at once, 
                # we fetch only what's needed for the current window 'w'.
                train_days = w * 30
                lookback_start = (start_date - timedelta(days=train_days + self.validator.learner.lags + 2))
                
                logger.info(f"  [AWO 2D] Sequential Fetch: Window {w}m (Lookback: {lookback_start})")
                
                # Fetch with min_relevance
                # But fetch_data is inside validator.learner.fetch_data, called by run_training/run_validation?
                # Actually, AWOEngine calls fetch_data explicitly here?
                # No, AWOEngine fetches 'all_news_raw' manually here.
                # We need to update this manual fetch query too!
                
                with get_db_cursor() as cur:
                    cur.execute("""
                        SELECT c.published_at::date as date, c.content
                        FROM tb_news_content c
                        JOIN tb_news_mapping m ON c.url_hash = m.url_hash
                        WHERE m.stock_code = %s 
                        AND c.published_at::date BETWEEN %s AND %s
                        AND m.is_relevant = TRUE
                        AND m.relevance_score >= %s
                    """, (self.stock_code, lookback_start, end_date, min_relevance))
                    all_news_raw = cur.fetchall()
                    
                df_all_news = pl.DataFrame(all_news_raw) if all_news_raw else pl.DataFrame({"date": [], "content": []})
                del all_news_raw # Immediate cleanup
                
                if not df_all_news.is_empty():
                    from src.learner.lasso import TOKEN_CACHE as GLOBAL_TOKEN_CACHE
                    
                    # Clear global cache before new window to prevent across-window accumulation
                    # This is key for 12GB OrbStack stability
                    GLOBAL_TOKEN_CACHE.clear()
                    
                    def get_cached_tokens(content):
                        if content in GLOBAL_TOKEN_CACHE:
                            return GLOBAL_TOKEN_CACHE[content]
                        t = self.validator.learner.tokenizer.tokenize(content, n_gram=self.validator.learner.n_gram)
                        # Keep window-specific cache small
                        if len(GLOBAL_TOKEN_CACHE) < 10000:
                            GLOBAL_TOKEN_CACHE[content] = t
                        return t
                    
                    df_all_news = df_all_news.with_columns(
                        pl.col("content").map_elements(get_cached_tokens, return_dtype=pl.List(pl.String)).alias("tokens")
                    )
                # -------------------------------------------------------------

                for a in alphas:
                    current_iter += 1
                    key_str = f"{w}m_{a}_scan"

                    # --- [RESUME LOGIC] ---
                    # Check if this iteration was already completed (e.g., worker restart)
                    with get_db_cursor() as cur:
                        # First check if checkpoint exists (source of truth)
                        cur.execute("""
                            SELECT hit_rate, mae FROM tb_awo_checkpoints 
                            WHERE v_job_id = %s AND window_months = %s AND alpha = %s
                        """, (v_job_id, w, a))
                        checkpoint = cur.fetchone()
                        if checkpoint:
                            # Checkpoint exists - load it and skip
                            results[(w, a)] = {
                                "hit_rate": float(checkpoint['hit_rate']),
                                "mae": float(checkpoint['mae']),
                                "raw_results": []  # Not needed for stability calculation
                            }
                            logger.info(f"Skipping completed iteration: {key_str} ({current_iter}/{total_iterations}) [Loaded from checkpoint]")
                            continue
                        # No checkpoint - must run this iteration (even if partial results exist)
                    # ----------------------
                    
                    # Check Stop Signal
                    if self._is_stopped(v_job_id):
                        logger.info(f"AWO Scan stopped by user for {self.stock_code}")
                        return None
                    
                    logger.info(f"Scanning Config: Window={w}m, Alpha={a} ({current_iter}/{total_iterations})")
                    
                    # Progress Callback
                    last_progress_update = 0
                    def update_progress(inner_p):
                        nonlocal last_progress_update
                        total_progress = ((current_iter - 1) + inner_p) / total_iterations * 100
                        import time
                        now = time.time()
                        if now - last_progress_update > 2.0: # Update every 2 seconds
                            with get_db_cursor() as cur:
                                cur.execute(
                                    "UPDATE tb_verification_jobs SET progress = %s, updated_at = CURRENT_TIMESTAMP WHERE v_job_id = %s",
                                    (total_progress, v_job_id)
                                )
                            
                            # Prometheus Update
                            try:
                                from src.utils.metrics import BACKTEST_PROGRESS
                                BACKTEST_PROGRESS.labels(job_id=str(v_job_id), stock_code=self.stock_code).set(total_progress)
                            except:
                                pass
                                
                            last_progress_update = now

                    # Run Validation with [dry_run=False] for immediate persistence
                    res = self.validator.run_validation(
                        start_date.strftime('%Y-%m-%d'),
                        end_date.strftime('%Y-%m-%d'),
                        train_days=train_days,
                        dry_run=False, # Save to DB immediately
                        progress_callback=update_progress,
                        v_job_id=v_job_id,
                        prefetched_df_news=df_all_news,
                        alpha=a,
                        used_version_tag=key_str, # Custom tag for DB
                        retrain_frequency='weekly' # TASK-062: Weekly Main retraining for efficiency
                    )
                    
                    if res.get('status') == 'stopped':
                        return None
                        
                    results[(w, a)] = {
                        "hit_rate": res['hit_rate'],
                        "mae": res['mae'],
                        "raw_results": res['results']
                    }
                    
                    # Log result
                    with get_db_cursor() as cur:
                        key_str = f"{w}m_{a}"
                        logger.info(f"  Result {key_str}: Hit={res['hit_rate']:.2%}, MAE={res['mae']:.4f}")
                    
                    # Save checkpoint for partial recovery
                    self._save_checkpoint(v_job_id, w, a, res['hit_rate'], res['mae'])

                    # Small GC after each alpha
                    import gc; gc.collect()
                
                # Big GC & DataFrame cleanup after each window
                del df_all_news
                import gc
                gc.collect()

            # 2. Stability Score Calculation & Selection
            if not results:
                raise ValueError("No results generated.")

            best_config = None
            best_score = -np.inf
            scored_results = {}
            
            lambda_penalty = 1.0 # Standard deviation penalty weight
            
            from math import sqrt
            
            for (w, a), metric in results.items():
                # Find neighbors (Same Window, Adj Alpha OR Same Alpha, Adj Window)
                # For simplicity, we define neighbors as just the grid points around it.
                # But grid is sparse. Let's just use the config itself for now, 
                # or strictly nearest neighbors in the list.
                
                # Simple Neighbor approach:
                # Neighbors = Self + (Same W, Prev A) + (Same W, Next A) + (Prev W, Same A) + (Next W, Same A)
                neighbors = [metric['hit_rate']]
                
                w_idx = windows.index(w)
                a_idx = alphas.index(a)
                
                if w_idx > 0: neighbors.append(results[(windows[w_idx-1], a)]['hit_rate'])
                if w_idx < len(windows)-1: neighbors.append(results[(windows[w_idx+1], a)]['hit_rate'])
                if a_idx > 0: neighbors.append(results[(w, alphas[a_idx-1])]['hit_rate'])
                if a_idx < len(alphas)-1: neighbors.append(results[(w, alphas[a_idx+1])]['hit_rate'])
                
                # Stability Score Calculation (TASK-041 + Phase 2 Enhancement)
                # Goal: Find the \"Robust Plateau\", not the \"Spurious Peak\"
                # Phase 2: Composite score = Hit Rate (60%) + (1 - Normalized MAE) (40%)
                mean_hr = sum(neighbors) / len(neighbors)
                variance = sum([((x - mean_hr) ** 2) for x in neighbors]) / len(neighbors)
                std_hr = sqrt(variance)
                
                # Phase 2: Add MAE component to score
                # Normalize MAE: 0.1 is considered baseline (MAE of 0.1 = 50% score)
                mae = metric['mae']
                normalized_mae = min(mae / 0.1, 1.0)  # Cap at 1.0
                mae_score = 1.0 - normalized_mae  # Higher is better
                
                # Composite: 60% Hit Rate + 40% MAE Score
                composite_score = (0.6 * mean_hr) + (0.4 * mae_score)
                
                # We subtract StdDev to penalize configurations that have high variance with their neighbors
                stability_score = composite_score - (lambda_penalty * std_hr)
                
                scored_results[f"{w}m_{a}"] = {
                    "hit_rate": metric['hit_rate'],
                    "mae": metric['mae'],
                    "stability_score": stability_score,
                    "composite_score": composite_score,
                    "mean_hr": mean_hr,
                    "std_hr": std_hr,
                    "neighbor_count": len(neighbors)
                }
                
                if stability_score > best_score:
                    best_score = stability_score
                    best_config = (w, a)

            # --- [FIX] Persist Stability Scores to tb_awo_checkpoints ---
            with get_db_cursor() as cur:
                for (w, a), metric in results.items():
                    s_score = scored_results[f"{w}m_{a}"]['stability_score']
                    cur.execute("""
                        UPDATE tb_awo_checkpoints 
                        SET stability_score = %s 
                        WHERE v_job_id = %s AND window_months = %s AND alpha = %s
                    """, (s_score, v_job_id, w, a))
            # ------------------------------------------------------------
            best_metric = results[(best_w, best_a)]
            
            summary = {
                "best_window": best_w,
                "best_alpha": best_a,
                "best_stability_score": best_score,
                "hit_rate": best_metric['hit_rate'],
                "mae": best_metric['mae'],
                "all_scores": scored_results
            }
            
            # 3. Promotion
            promotion_result = None
            # Standard threshold: Hit Rate > 50% AND Stability Score > 0.45 (Example)
            if best_metric['hit_rate'] > 0.50:
                promotion_result = self.promote_best_model(best_w, best_a, metrics=summary)
            else:
                promotion_result = {"status": "rejected", "reason": "Low Hit Rate"}
                
            summary["promotion"] = promotion_result
            
            with get_db_cursor() as cur:
                cur.execute("""
                    UPDATE tb_verification_jobs 
                    SET status = 'completed', result_summary = %s, progress = 100, completed_at = CURRENT_TIMESTAMP
                    WHERE v_job_id = %s
                """, (json.dumps(summary, default=str), v_job_id))
                
            return summary

        except Exception as e:
            logger.error(f"AWO 2D Scan failed: {e}")
            with get_db_cursor() as cur:
                cur.execute(
                    "UPDATE tb_verification_jobs SET status = 'failed', error_message = %s WHERE v_job_id = %s",
                    (str(e), v_job_id)
                )
            raise e

    def promote_best_model(self, window_months, alpha, metrics=None):
        """최적 윈도우와 Alpha를 사용하여 최종 Production 모델을 학습하고 활성화함."""
        logger.info(f"Promoting best model for {self.stock_code} using {window_months}m window, Alpha={alpha}...")
        
        train_days = window_months * 30
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=train_days)
        
        version = f"prod_{window_months}m_a{alpha}_{end_date.strftime('%Y%m%d')}"
        
        try:
            # Set alpha & Enable Stability Selection for Production
            self.validator.learner.alpha = alpha
            self.validator.learner.use_stability_selection = True
            if hasattr(self.validator.learner.model, 'alpha'):
                 self.validator.learner.model.alpha = alpha

            # Get parent version
            parent_version = None
            with get_db_cursor() as cur:
                cur.execute("""
                    SELECT version FROM tb_sentiment_dict_meta 
                    WHERE stock_code = %s AND source = 'Main' AND is_active = TRUE
                    ORDER BY created_at DESC LIMIT 1
                """, (self.stock_code,))
                row = cur.fetchone()
                if row:
                    parent_version = row['version']

            self.validator.learner.run_training(
                self.stock_code,
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d'),
                version=version,
                source='Main'
            )
            
            with get_db_cursor() as cur:
                cur.execute("""
                    UPDATE tb_sentiment_dict_meta
                    SET parent_version = %s,
                        promotion_status = 'success',
                        promotion_metrics = %s
                    WHERE stock_code = %s AND version = %s AND source = 'Main'
                """, (parent_version, json.dumps(metrics) if metrics else None, self.stock_code, version))

                # Update daily_targets with optimal parameters (Golden Parameters)
                cur.execute("""
                    UPDATE daily_targets 
                    SET optimal_window_months = %s, 
                        optimal_alpha = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE stock_code = %s
                """, (window_months, alpha, self.stock_code))

            logger.info(f"Model Promotion Successful: {version} (Parent: {parent_version})")
            
            # Extract and save neutral words for future memory optimization
            try:
                neutral_words = self.validator.learner.extract_and_save_neutral_words(self.stock_code)
                logger.info(f"  [NeutralWords] Extracted {len(neutral_words)} neutral words for {self.stock_code}")
            except Exception as e:
                logger.warning(f"  [NeutralWords] Failed to extract neutral words: {e}")
            
            return {"status": "success", "version": version, "parent_version": parent_version, "timestamp": datetime.now().isoformat()}
        except Exception as e:
            logger.error(f"Model Promotion Failed: {e}")
            return {"status": "failed", "error": str(e), "timestamp": datetime.now().isoformat()}

    def save_scan_results(self, v_job_id, window_months, results):
        """윈도우별 검증 상세 결과를 tb_verification_results 에 기록"""
        with get_db_cursor() as cur:
            for r in results:
                cur.execute("""
                    INSERT INTO tb_verification_results 
                    (v_job_id, target_date, predicted_score, actual_alpha, is_correct, used_version)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (v_job_id, r['date'], r['sentiment_score'], r['actual_alpha'], r['is_correct'], f"{window_months}m_scan"))
    def _is_stopped(self, v_job_id):
        """작업이 중단 상태이거나 삭제되었는지 확인"""
        if v_job_id is None:
            return False
        with get_db_cursor() as cur:
            cur.execute("SELECT status FROM tb_verification_jobs WHERE v_job_id = %s", (v_job_id,))
            row = cur.fetchone()
            if not row:
                return True # Missing job is treated as stopped
            return row['status'] == 'stopped'
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    stock = sys.argv[1] if len(sys.argv) > 1 else "005930"
    engine = AWOEngine(stock)
    engine.run_exhaustive_scan(validation_months=1)
