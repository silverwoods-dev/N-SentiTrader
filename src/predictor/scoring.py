# src/predictor/scoring.py
from src.db.connection import get_db_cursor
import json
import logging
import math

logger = logging.getLogger(__name__)

class Predictor:
    def load_dict(self, version, stock_code, source='Main'):
        with get_db_cursor() as cur:
            cur.execute(
                """SELECT word, beta FROM tb_sentiment_dict 
                   WHERE version = %s AND source = %s AND stock_code = %s""",
                (version, source, stock_code)
            )
            rows = cur.fetchall()
        return {row['word']: float(row['beta']) for row in rows}

    def load_meta_metrics(self, version, stock_code, source='Main'):
        """Load metadata metrics (including scaler params)"""
        with get_db_cursor() as cur:
            cur.execute(
                "SELECT metrics FROM tb_sentiment_dict_meta WHERE version = %s AND source = %s AND stock_code = %s",
                (version, source, stock_code)
            )
            row = cur.fetchone()
            if row and row['metrics']:
                return row['metrics'] if isinstance(row['metrics'], dict) else json.loads(row['metrics'])
        return {}

    def load_active_dict(self, stock_code, source='Main'):
        """Metadata에서 현재 'Active' 상태인 버전을 찾아 로드합니다."""
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT version FROM tb_sentiment_dict_meta
                WHERE stock_code = %s AND source = %s AND is_active = TRUE
                ORDER BY created_at DESC LIMIT 1
            """, (stock_code, source))
            row = cur.fetchone()
            
            if row:
                return self.load_dict(row['version'], stock_code, source)
            
            # Active 버전이 없는 경우 가장 최신 버전을 시도 (Fallback)
            cur.execute("""
                SELECT version FROM tb_sentiment_dict
                WHERE stock_code = %s AND source = %s
                ORDER BY updated_at DESC LIMIT 1
            """, (stock_code, source))
            row = row or cur.fetchone()
            if row:
                return self.load_dict(row['version'], stock_code, source)
        return {}

    def calculate_score(self, tokens, sentiment_dict, lag=None):
        score = 0.0
        suffix = f"_L{lag}" if lag else ""
        for token in tokens:
            score += sentiment_dict.get(f"{token}{suffix}", 0.0)
        return score

    def predict_advanced(self, stock_code, news_by_lag, version=None, fundamentals=None):
        """
        news_by_lag: {1: [tokens], 2: [tokens], ...}
        fundamentals: dict {'per': val, 'pbr': val, ...} (Optional)
        version: specific version or None (Active)
        """
        if version:
            main_dict = self.load_dict(version, stock_code, 'Main')
            buffer_dict = self.load_dict(version, stock_code, 'Buffer')
            # Fetch scaler params if available
            meta = self.load_meta_metrics(version, stock_code, 'Main')
            scaler_params = meta.get('scaler')
        else:
            # Active version logic needs to be robust. 
            # For simplicity, we assume if version check passes, we get dict.
            # But we also need 'meta' for Active version.
            # load_active_dict handles dict loading. We need a helper to get Active Version ID first if we want meta.
            # Re-implementing logic to get version first.
            
            with get_db_cursor() as cur: 
                 # Find active version
                cur.execute("""
                    SELECT version FROM tb_sentiment_dict_meta
                    WHERE stock_code = %s AND source = 'Main' AND is_active = TRUE
                    ORDER BY created_at DESC LIMIT 1
                """, (stock_code,))
                row = cur.fetchone()
                current_version = row['version'] if row else None
            
            if current_version:
                 main_dict = self.load_dict(current_version, stock_code, 'Main')
                 buffer_dict = self.load_dict(current_version, stock_code, 'Buffer')
                 meta = self.load_meta_metrics(current_version, stock_code, 'Main')
                 scaler_params = meta.get('scaler')
            else:
                 # Fallback (Legacy behavior)
                 main_dict = self.load_active_dict(stock_code, 'Main')
                 buffer_dict = self.load_active_dict(stock_code, 'Buffer')
                 scaler_params = None
            
        combined_dict = main_dict.copy()
        for word, beta in buffer_dict.items():
            combined_dict[word] = combined_dict.get(word, 0.0) + beta
            
        pos_score = 0.0
        neg_score = 0.0
        contributions = []
        
        # Threshold for filtering near-zero noise
        THRESHOLD = 1e-5
        
        for lag, tokens in news_by_lag.items():
            suffix = f"_L{lag}"
            for token in tokens:
                key = f"{token}{suffix}"
                weight = combined_dict.get(key, 0.0)
                if abs(weight) > THRESHOLD:  # Filter out near-zero weights
                    if weight > 0:
                        pos_score += weight
                    else:
                        neg_score += weight
                    contributions.append({"word": token, "weight": weight})
        
        # Add Dense (Fundamental) Contributions
        if fundamentals and scaler_params:
            import math
            import numpy as np
            
            cols = scaler_params.get('cols', [])
            means = scaler_params.get('mean', [])
            scales = scaler_params.get('scale', [])
            
            if cols and len(means) == len(cols):
                for i, col in enumerate(cols):
                    # Value extraction
                    val = fundamentals.get(col, 0.0)
                    
                    # Log transform if needed (Hardcoded logic matching LassoLearner)
                    if col == 'log_market_cap':
                         # If input is 'market_cap' (raw), transform it.
                         # If input is 'log_market_cap', use it.
                         if 'log_market_cap' not in fundamentals and 'market_cap' in fundamentals:
                             val = math.log(fundamentals['market_cap']) if fundamentals['market_cap'] > 0 else 0
                         
                    # Scale
                    scaled_val = (val - means[i]) / scales[i] if scales[i] != 0 else 0
                    
                    # Weight
                    # Key used in LassoLearner: "__F_{col}__"
                    key = f"__F_{col}__"
                    weight_coef = combined_dict.get(key, 0.0)
                    
                    if weight_coef != 0:
                        contribution = scaled_val * weight_coef
                        if contribution > 0:
                            pos_score += contribution
                        else:
                            neg_score += contribution
                        
                        contributions.append({"word": key, "weight": contribution, "raw_val": val})
            
        net_score = pos_score + neg_score
        intensity = abs(pos_score) + abs(neg_score)
        
        # Volume-weighted Intensity (PRD Section 16.2)
        v_multiplier = 1.0
        with get_db_cursor() as cur:
            # 5-day Avg Volume vs Latest Volume (Today's volume might be estimated or fetched if available)
            # For simplicity, we fetch the most recent volume available in DB
            cur.execute("""
                WITH stats AS (
                    SELECT AVG(volume) as avg_vol, MAX(date) as last_date
                    FROM (
                        SELECT volume, date FROM tb_daily_price 
                        WHERE stock_code = %s 
                        ORDER BY date DESC LIMIT 5
                    ) t
                )
                SELECT 
                    volume as last_vol, 
                    (SELECT avg_vol FROM stats) as avg_vol
                FROM tb_daily_price 
                WHERE stock_code = %s AND date = (SELECT last_date FROM stats)
            """, (stock_code, stock_code))
            vol_row = cur.fetchone()
            
            if vol_row and vol_row['avg_vol'] and vol_row['avg_vol'] > 0:
                v_ratio = float(vol_row['last_vol']) / float(vol_row['avg_vol'])
                v_multiplier = math.log1p(v_ratio) # log(1 + v_ratio)
                v_multiplier = max(0.5, min(2.0, v_multiplier)) # Bound the multiplier
                
        # Apply volume weighting
        original_intensity = intensity
        intensity = intensity * v_multiplier
        net_score = net_score * v_multiplier
        
        # 6-State Taxonomy Logic
        # Thresholds can be tuned. For now, using naive values.
        INTENSITY_THRESHOLD = 0.01
        NET_THRESHOLD = 0.005
        
        if intensity < INTENSITY_THRESHOLD:
            status = "Observation"
        elif intensity > (INTENSITY_THRESHOLD * 2) and abs(net_score) < (NET_THRESHOLD / 2):
            status = "Mixed"
        elif net_score > NET_THRESHOLD:
            status = "Strong Buy"
        elif net_score > 0:
            status = "Cautious Buy"
        elif net_score < -NET_THRESHOLD:
            status = "Strong Sell"
        else:
            status = "Cautious Sell"
            
        # 기여도 정렬 (절대값 기준 상위 키워드 추출)
        pos_contribs = sorted([c for c in contributions if c['weight'] > 0], key=lambda x: x['weight'], reverse=True)[:3]
        neg_contribs = sorted([c for c in contributions if c['weight'] < 0], key=lambda x: x['weight'])[:3]
        
        # Outlier Clipping (+/- 15%)
        original_alpha = net_score
        clipped_alpha = max(-0.15, min(0.15, net_score))
        
        if original_alpha != clipped_alpha:
            logger.warning(f"Outlier detected for {stock_code}: {original_alpha:.4f} clipped to {clipped_alpha:.4f}")
        
        # Calculate Confidence Score
        confidence_score = self.calculate_confidence(news_by_lag, meta)
        
        # Soft Warning & Confidence Penalty for extreme alpha (> 5%)
        if abs(net_score) > 0.05:
            # Reduce confidence by 30% for extreme predictions to reflect higher uncertainty
            confidence_score = confidence_score * 0.7
            logger.info(f"Extreme alpha ({net_score:.4f}) detected for {stock_code}. Reducing confidence score.")
        
        return {
            "stock_code": stock_code,
            "expected_alpha": clipped_alpha,
            "net_score": net_score,
            "intensity": intensity,
            "status": status,
            "confidence_score": confidence_score,
            "top_keywords": {
                "positive": pos_contribs,
                "negative": neg_contribs
            }
        }

    def calculate_confidence(self, news_by_lag, meta):
        """뉴스 수집량과 모델 성능(MAE)을 기반으로 신뢰도 지수 산출"""
        # 1. Volume Factor (신호의 충분성)
        # Lag 1(최신) 뉴스 토큰 수를 기반으로 추정 (약 50개 토큰이 1건의 뉴스라 가정)
        latest_tokens = news_by_lag.get(1, [])
        v_count = len(latest_tokens) / 50.0
        v_factor = min(1.0, v_count / 3.0) # 일일 3건 이상 뉴스 시 만점
        
        # 2. Accuracy Factor (모델의 검증 성능)
        val_metrics = meta.get('lasso_metrics', {}).get('val', {})
        mae = val_metrics.get('mae', 0.05) # MAE 5%를 기본값으로 타겟팅
        # MAE가 0.1(10%) 이상이면 신뢰도 급감
        m_factor = max(0.0, 1.0 - (mae * 10))
        
        confidence = (v_factor * 0.4 + m_factor * 0.6) * 100
        return round(min(100, max(0, confidence)), 1)

    def run_daily_prediction(self):
        """모든 활성 종목에 대해 '배포된(Active)' 사전을 사용하여 예측을 수행합니다."""
        # Fetch optimal lag for each active target
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT dt.stock_code, dt.optimal_lag, sm.stock_name
                FROM daily_targets dt
                JOIN tb_stock_master sm ON dt.stock_code = sm.stock_code
                WHERE dt.status = 'active'
            """)
            targets = cur.fetchall()
            
        results = []
        for target in targets:
            stock_code = target['stock_code']
            lag_limit = target['optimal_lag']
            
            # Fetch news for this stock within lag_limit
            # (실제로는 날짜별로 그룹화된 토큰이 필요함)
            news_by_lag = self.fetch_news_by_lag(stock_code, lag_limit)
            
            if not news_by_lag:
                continue
                
            res = self.predict_advanced(stock_code, news_by_lag, version=None)
            
            # If everything is zero/observation, skip
            if res['status'] == "Observation":
                continue

            # Status is used as the directional signal (Strong Buy, Cautious Buy -> 1)
            # For DB, we might want to store the full status string, or a simplified numerical prediction.
            # Let's keep the full status for now as per the original schema.
            
            results.append(res)
            
            # Save prediction to DB
            with get_db_cursor() as cur_save:
                cur_save.execute(
                    """INSERT INTO tb_predictions 
                       (stock_code, prediction_date, sentiment_score, intensity, status, expected_alpha, confidence_score, top_keywords) 
                       VALUES (%s, CURRENT_DATE, %s, %s, %s, %s, %s, %s)""",
                    (
                        stock_code, 
                        res['net_score'], 
                        res['intensity'], 
                        res['status'], 
                        res['expected_alpha'], 
                        res['confidence_score'],
                        json.dumps(res['top_keywords'])
                    )
                )
        return results

    def fetch_news_by_lag(self, stock_code, lag_limit):
        from src.nlp.tokenizer import Tokenizer
        tokenizer = Tokenizer()
        news_by_lag = {}
        
        with get_db_cursor() as cur:
            for i in range(1, lag_limit + 1):
                # Lag 1 is Today (predicting for Tomorrow)
                target_date = "CURRENT_DATE" if i == 1 else f"CURRENT_DATE - INTERVAL '{i-1} days'"
                cur.execute(f"""
                    SELECT c.content
                    FROM tb_news_content c
                    JOIN tb_news_mapping m ON c.url_hash = m.url_hash
                    WHERE m.stock_code = %s AND c.published_at::date = {target_date}
                """, (stock_code,))
                rows = cur.fetchall()
                
                tokens = []
                for row in rows:
                    tokens.extend(tokenizer.tokenize(row['content']))
                
                if tokens:
                    news_by_lag[i] = tokens
                    
        return news_by_lag
