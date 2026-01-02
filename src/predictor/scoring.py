# src/predictor/scoring.py
from src.db.connection import get_db_cursor
import json
import logging
import math
from datetime import datetime, date, timedelta

logger = logging.getLogger(__name__)

# Black Swan Critical Words (Shared with Lasso)
CRITICAL_WORDS = {
    "배임", "횡령", "화재", "소송", "고발", "고소", "압수수색", "구속", "해킹", "전쟁",
    "부도", "파산", "상장폐지", "거래정지", "분식회계", "하한가", "유상증자"
}

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

    def predict_advanced(self, stock_code, news_by_lag, version=None, fundamentals=None, tech_indicators=None):
        """
        news_by_lag: {1: [tokens], 2: [tokens], ...}
        fundamentals: dict {'per': val, 'pbr': val, ...} (Optional)
        tech_indicators: dict {'tech_rsi_14': val, ...} (Optional)
        version: specific version or None (Active)
        """
        if version:
            main_dict = self.load_dict(version, stock_code, 'Main')
            buffer_dict = self.load_dict(version, stock_code, 'Buffer')
            # Fetch scaler params if available
            meta = self.load_meta_metrics(version, stock_code, 'Main')
            scaler_params = meta.get('scaler')
        else:
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
                 # Last resort Fallback
                 main_dict = self.load_active_dict(stock_code, 'Main')
                 buffer_dict = self.load_active_dict(stock_code, 'Buffer')
                 meta = {} # Ensure meta is defined even in fallback
                 scaler_params = None
            
        combined_dict = main_dict.copy()
        for word, beta in buffer_dict.items():
            combined_dict[word] = combined_dict.get(word, 0.0) + beta
            
        pos_score = 0.0
        neg_score = 0.0
        contributions = []
        
        
        # Threshold for filtering near-zero noise
        THRESHOLD = 1e-5
        
        for lag, items in news_by_lag.items():
            suffix = f"_L{lag}"
            # Check if items are tuples (token, weight) or just tokens
            for item in items:
                if isinstance(item, tuple):
                    token, time_weight = item
                else:
                    token, time_weight = item, 1.0
                    
                key = f"{token}{suffix}"
                base_weight = combined_dict.get(key, 0.0)
                
                # Apply Time Decay Weight (Hourly Decay from Weekend/Evening)
                weight = base_weight * time_weight
                
                if abs(weight) > THRESHOLD:  # Filter out near-zero weights
                    if weight > 0:
                        pos_score += weight
                    else:
                        neg_score += weight
                    contributions.append({"word": token, "weight": weight})
        
        # Add Dense (Fundamental: __F_) Contributions
        if fundamentals and scaler_params:
            cols = scaler_params.get('cols', [])
            means = scaler_params.get('mean', [])
            scales = scaler_params.get('scale', [])
            
            if cols and len(means) == len(cols):
                for i, col in enumerate(cols):
                    # Fundamental features usually have __F_ prefix in dict
                    key = f"__F_{col}__"
                    weight_coef = combined_dict.get(key, 0.0)
                    if weight_coef == 0: continue
                    
                    val = fundamentals.get(col, 0.0)
                    if col == 'log_market_cap' and 'log_market_cap' not in fundamentals and 'market_cap' in fundamentals:
                        val = math.log(fundamentals['market_cap']) if fundamentals['market_cap'] > 0 else 0
                    
                    scaled_val = (val - means[i]) / scales[i] if scales[i] != 0 else 0
                    contribution = scaled_val * weight_coef
                    
                    if contribution > 0: pos_score += contribution
                    else: neg_score += contribution
                    contributions.append({"word": key, "weight": contribution, "raw_val": val})

        # Add Tech Indicator (__T_) Contributions
        if tech_indicators and scaler_params and 'tech_cols' in scaler_params:
            t_cols = scaler_params.get('tech_cols', [])
            t_means = scaler_params.get('tech_mean', [])
            t_scales = scaler_params.get('tech_scale', [])
            
            if t_cols and len(t_means) == len(t_cols):
                for i, col in enumerate(t_cols):
                    # Tech features already have __T_ prefix in LassoLearner output
                    key = col if col.startswith("__T_") else f"__T_{col}"
                    weight_coef = combined_dict.get(key, 0.0)
                    if weight_coef == 0: continue
                    
                    # Search in tech_indicators (which might not have prefix)
                    raw_key = col.replace("__T_", "")
                    val = tech_indicators.get(raw_key, 0.0)
                    
                    scaled_val = (val - t_means[i]) / t_scales[i] if t_scales[i] != 0 else 0
                    contribution = scaled_val * weight_coef
                    
                    if contribution > 0: pos_score += contribution
                    else: neg_score += contribution
                    contributions.append({"word": key, "weight": contribution, "raw_val": val})
            
        # --- Multi-Factor Hybrid Scaling (Valuation Normalization) ---
        valuation_multiplier = 1.0
        pbr = fundamentals.get('pbr', 1.0) if fundamentals else 1.0
        
        # If PBR > 6.0, start penalizing aggressive Buy signals (Conservative stance)
        if pos_score > 0 and pbr > 6.0:
            # Overvaluation penalty: reduces pos_score by up to 30% for high PBR
            penalty = min(0.3, (pbr - 6.0) / 10.0)
            valuation_multiplier = 1.0 - penalty
            pos_score *= valuation_multiplier
            logger.info(f"Applying Valuation Penalty for {stock_code} (PBR: {pbr:.1f}, Multiplier: {valuation_multiplier:.2f})")

        net_score = pos_score + neg_score
        intensity = abs(pos_score) + abs(neg_score)
        
        # Volume-weighted Intensity (PRD Section 16.2)
        v_multiplier = 1.0
        volatility = 0.02 # Default daily volatility (2%)
        
        with get_db_cursor() as cur:
            # Fetch Volume Stats AND Volatility
            cur.execute("""
                WITH v_stats AS (
                    SELECT AVG(volume) as avg_vol, MAX(date) as last_date
                    FROM (
                        SELECT volume, date FROM tb_daily_price 
                        WHERE stock_code = %s 
                        ORDER BY date DESC LIMIT 5
                    ) t
                ),
                vol_stats AS (
                    SELECT STDDEV(return_rate) as vol, COUNT(*) as cnt
                    FROM (
                        SELECT return_rate FROM tb_daily_price
                        WHERE stock_code = %s
                        ORDER BY date DESC LIMIT 30
                    ) t2
                )
                SELECT 
                    p.volume as last_vol, 
                    (SELECT avg_vol FROM v_stats) as avg_vol,
                    (SELECT vol FROM vol_stats) as volatility,
                    (SELECT cnt FROM vol_stats) as vol_cnt
                FROM tb_daily_price p
                WHERE p.stock_code = %s AND p.date = (SELECT last_date FROM v_stats)
            """, (stock_code, stock_code, stock_code))
            row = cur.fetchone()
            
            if row:
                if row['avg_vol'] and row['avg_vol'] > 0:
                    v_ratio = float(row['last_vol']) / float(row['avg_vol'])
                    v_multiplier = math.log1p(v_ratio)
                    v_multiplier = max(0.5, min(2.0, v_multiplier))
                
                if row['volatility'] and row['vol_cnt'] >= 20:
                     volatility = float(row['volatility'])
                
        # Apply volume weighting
        original_intensity = intensity
        intensity = intensity * v_multiplier
        net_score = net_score * v_multiplier
        
        # 6-State Taxonomy Logic (Dynamic Thresholds)
        BASE_VOL = 0.02
        vol_scalar = max(0.5, min(3.0, volatility / BASE_VOL))
        
        ADJ_INTENSITY_THRESHOLD = 0.01 * vol_scalar
        ADJ_NET_THRESHOLD = 0.005 * vol_scalar
        
        # Check for Critical Words (Black Swan Override)
        has_critical_neg = any(c['word'] in CRITICAL_WORDS and c['weight'] < 0 for c in contributions)
        has_critical_pos = any(c['word'] in CRITICAL_WORDS and c['weight'] > 0 for c in contributions)
        
        if has_critical_neg:
            status = "Super Sell"
        elif has_critical_pos:
            status = "Super Buy"
        elif intensity < ADJ_INTENSITY_THRESHOLD:
            status = "Wait"
        elif intensity > (ADJ_INTENSITY_THRESHOLD * 2) and abs(net_score) < (ADJ_NET_THRESHOLD / 2):
            status = "Restricted"
        elif net_score > ADJ_NET_THRESHOLD:
            status = "Super Buy"
        elif net_score > 0:
            status = "Buy"
        elif net_score < -ADJ_NET_THRESHOLD:
            status = "Super Sell"
        else:
            status = "Sell"
            
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
            },
            "fundamentals": {
                "pbr": float(pbr) if pbr else None,
                "per": float(fundamentals.get('per', 0)) if fundamentals and fundamentals.get('per') else None,
                "roe": float(fundamentals.get('roe', 0)) if fundamentals and fundamentals.get('roe') else None,
                "valuation_multiplier": valuation_multiplier
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

    def run_daily_prediction(self, version=None):
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
                
            res = self.predict_advanced(stock_code, news_by_lag, version=version)
            
            # If everything is zero/observation, skip
            if res['status'] == "Observation":
                continue

            # Status is used as the directional signal (Strong Buy, Cautious Buy -> 1)
            # For DB, we might want to store the full status string, or a simplified numerical prediction.
            # Let's keep the full status for now as per the original schema.
            
            results.append(res)
            
            # Generate Evidence for Dashboard
            from src.utils.report_helper import ReportHelper
            # Use the dictionary from the prediction logic (approximate if version logic is complex, 
            # but usually it's the active one).
            # We can reload the active dict here to be safe and consistent with what the user sees.
            active_dict = self.load_active_dict(stock_code)
            evidence_list = ReportHelper.get_evidence_news(stock_code, date.today(), active_dict)
            
            # Save prediction AND evidence to DB
            with get_db_cursor() as cur_save:
                cur_save.execute(
                    """INSERT INTO tb_predictions 
                       (stock_code, prediction_date, sentiment_score, intensity, status, expected_alpha, confidence_score, top_keywords, evidence) 
                       VALUES (%s, CURRENT_DATE, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        stock_code, 
                        res['net_score'], 
                        res['intensity'], 
                        res['status'], 
                        res['expected_alpha'], 
                        res['confidence_score'],
                        json.dumps(res['top_keywords']),
                        json.dumps(evidence_list, default=str) # Handle datetime serialization
                    )
                )
        return results

    def fetch_news_by_lag(self, stock_code, lag_limit):
        from src.nlp.tokenizer import Tokenizer
        from src.utils.calendar import Calendar
        tokenizer = Tokenizer()
        news_by_lag = {}
        
        # 1. 대상 종목의 거래일 목록 가져오기
        trading_days = Calendar.get_trading_days(stock_code)
        if not trading_days:
            return {}

        # 2. '오늘' 기준의 타겟 거래일(Impact Date) 결정
        # 오늘이 주말이라면 타겟은 다음 월요일
        target_impact_day = Calendar.get_impact_date(stock_code, date.today())
        
        # 3. 타겟 거래일로부터 시차(Lag)에 해당하는 실제 거래일들 계산
        # j: 타겟 거래일의 인덱스
        idx = -1
        for i, d in enumerate(trading_days):
            if d == target_impact_day:
                idx = i
                break
        
        if idx == -1:
            # 타겟 거래일이 DB 가격 데이터보다 미래인 경우 (내일 모레 등)
            # 가장 최근 거래일을 '오늘'로 가정하고 진행
            idx = len(trading_days) - 1
            target_impact_day = trading_days[idx]

        with get_db_cursor() as cur:
            for lag in range(1, lag_limit + 1):
                # lag 1: target_impact_day에 해당하는 뉴스들 (주말 누적 포함)
                # lag 2: target_impact_day 이전 거래일에 해당하는 뉴스들
                
                if idx - (lag - 1) < 0:
                    break
                    
                actual_impact_date = trading_days[idx - (lag - 1)]
                
                # 해당 impact_date를 가진 뉴스들 찾기
                # (SQL에서 impact_date 계산 로직을 동일하게 적용하거나, 미리 저장된 필드가 없다면 날짜 범위를 추론)
                # 캘린더 로직에 따르면 actual_impact_date를 가진 뉴스는:
                # (이전 거래일 + 1일 장후) ~ (현재 거래일 장중) 까지임.
                
                prev_trading_day = trading_days[idx - lag] if idx - lag >= 0 else actual_impact_date - timedelta(days=7)
                
                # Impact Date Logic in SQL:
                # 16:00 (오늘) ~ 15:59 (다음거래일)
                # target_date 가 impact_date 라는 것은:
                # (target_date-1) 16:00 <= published_at < (target_date) 16:00 가 아님. (주말 때문)
                # 정확히는 (prev_trading_day) 16:00 <= published_at < (actual_impact_date) 16:00
                
                cur.execute("""
                    SELECT c.content, c.published_at
                    FROM tb_news_content c
                    JOIN tb_news_mapping m ON c.url_hash = m.url_hash
                    WHERE m.stock_code = %s 
                      AND c.published_at >= %s::timestamp + interval '7 hours'
                      AND c.published_at < %s::timestamp + interval '0 hours'
                """, (stock_code, prev_trading_day, actual_impact_date))
                
                rows = cur.fetchall()
                tokens = []
                
                # Market Open Time (Target Day 09:00:00)
                # impact_date is just a date object.
                market_open_dt = datetime.combine(actual_impact_date, datetime.min.time()) + timedelta(hours=9)
                
                for row in rows:
                    if row['content']:
                        # Calculate Hourly Decay with safe datetime handling
                        pub_at = row['published_at']
                        if pub_at:
                            # Safe datetime parsing and decay calculation
                            try:
                                if isinstance(pub_at, str):
                                    pub_at = datetime.fromisoformat(pub_at)
                                
                                # Check if this is date-only (legacy data at 00:00)
                                is_date_only = (pub_at.hour == 0 and pub_at.minute == 0 and pub_at.second == 0)
                                
                                if is_date_only:
                                    # For legacy data without time, use conservative 24h decay
                                    time_weight = math.exp(-0.02 * 24)  # ~0.62
                                else:
                                    # For precise datetime, calculate actual decay
                                    hours_diff = (market_open_dt - pub_at).total_seconds() / 3600.0
                                    hours_diff = max(0, hours_diff)
                                    time_weight = math.exp(-0.02 * hours_diff)
                            except Exception as e:
                                # Fallback to neutral weight on any error
                                time_weight = 1.0
                        else:
                            time_weight = 1.0
                            
                        item_tokens = tokenizer.tokenize(row['content'])
                        
                        # Store as (token, weight) tuples
                        for t in item_tokens:
                            tokens.append((t, time_weight))
                
                if tokens:
                    news_by_lag[lag] = tokens
                    
        return news_by_lag
