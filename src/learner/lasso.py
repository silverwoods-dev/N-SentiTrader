import polars as pl
from sklearn.linear_model import Lasso
from sklearn.preprocessing import StandardScaler
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
from src.db.connection import get_db_cursor
from src.nlp.tokenizer import Tokenizer
from datetime import datetime, timedelta
from scipy.sparse import hstack
import json

class LassoLearner:
    def __init__(self, alpha=0.0001, n_gram=3, lags=5, min_df=3, max_features=50000):
        self.alpha = alpha
        self.n_gram = n_gram
        self.lags = lags
        self.min_df = min_df
        self.max_features = max_features
        self.tokenizer = Tokenizer()
        # 리스트 입력을 직접 받기 위해 tokenizer를 identity 함수로 설정
        self.vectorizer = TfidfVectorizer(
            tokenizer=lambda x: x,
            lowercase=False,
            token_pattern=None,
            min_df=self.min_df,
            max_features=self.max_features
        )
        self.model = Lasso(alpha=self.alpha, max_iter=10000)
        self.keep_indices = None # Black Swan 필터링 결과 저장용

    def fetch_data(self, stock_code, start_date, end_date):
        """
        특정 기간의 주가, 뉴스, 재무 데이터를 가져옵니다.
        """
        with get_db_cursor() as cur:
            # Fetch prices
            cur.execute("""
                SELECT date, excess_return 
                FROM tb_daily_price 
                WHERE stock_code = %s AND date BETWEEN %s AND %s
                ORDER BY date ASC
            """, (stock_code, start_date, end_date))
            prices = cur.fetchall()
            
            # Fetch fundamentals (TASK-038)
            cur.execute("""
                SELECT base_date as date, per, pbr, roe, market_cap
                FROM tb_stock_fundamentals
                WHERE stock_code = %s AND base_date BETWEEN %s AND %s
                ORDER BY base_date ASC
            """, (stock_code, start_date, end_date))
            fundamentals = cur.fetchall()

            # Fetch news (lags를 고려하여 시작일을 앞당김)
            news_start = (datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=self.lags + 2)).strftime('%Y-%m-%d')
            cur.execute("""
                SELECT c.published_at::date as date, c.content
                FROM tb_news_content c
                JOIN tb_news_mapping m ON c.url_hash = m.url_hash
                WHERE m.stock_code = %s AND c.published_at::date BETWEEN %s AND %s
            """, (stock_code, news_start, end_date))
            news = cur.fetchall()
            
        if not prices:
            print(f"No price data for {stock_code}")
            return None, None, None
            
        df_prices = pl.DataFrame(prices)
        df_news = pl.DataFrame(news) if news else pl.DataFrame({"date": [], "content": []})
        df_fund = pl.DataFrame(fundamentals) if fundamentals else pl.DataFrame({"date": [], "per": [], "pbr": [], "roe": [], "market_cap": []})
        
        return df_prices, df_news, df_fund

    def prepare_features(self, df_prices, df_news, df_fund):
        # 1. 뉴스 토큰화
        if not df_news.is_empty():
            print(f"    Tokenizing {len(df_news)} news items...")
            df_news = df_news.with_columns(
                pl.col("content").map_elements(
                    lambda x: self.tokenizer.tokenize(x, n_gram=self.n_gram),
                    return_dtype=pl.List(pl.String)
                ).alias("tokens")
            )
            df_news_daily = df_news.group_by("date").agg(pl.col("tokens").flatten())
        else:
            df_news_daily = pl.DataFrame({"date": [], "tokens": []})
        
        # 2. 기본 데이터 병합 (Prices + Fundamentals)
        # Fundamentals JOIN (Left Join on Prices)
        df = df_prices.clone()
        
        # 날짜 타입 통일 (Date vs Datetime)
        # pl.DataFrame from cursor usually infers Date.
        # Check types if needed.
        
        if not df_fund.is_empty():
            df = df.join(df_fund, on="date", how="left")
            # Fill missing fundamentals with Forward Fill (then specific val)
            df = df.with_columns([
                pl.col("per").fill_null(strategy="forward").fill_null(0.0),
                pl.col("pbr").fill_null(strategy="forward").fill_null(0.0),
                pl.col("roe").fill_null(strategy="forward").fill_null(0.0),
                pl.col("market_cap").fill_null(strategy="forward").fill_null(0.0)
            ])
            # Log transform Market Cap
            df = df.with_columns(
                pl.col("market_cap").max(1).log().alias("log_market_cap")
            )
        else:
            # Add dummy columns if no fundamentals
            df = df.with_columns([
                pl.lit(0.0).alias("per"),
                pl.lit(0.0).alias("pbr"),
                pl.lit(0.0).alias("roe"),
                pl.lit(0.0).alias("log_market_cap")
            ])
        
        # 3. 시차(Lag) 피처 생성 (뉴스)
        for i in range(1, self.lags + 1):
            offset_date = pl.col("date") - timedelta(days=i) 
            # Note: Logic was `(pl.col("date") + timedelta(days=i)).alias("date")` in previous code to align news date to target date.
            # To simulate "Price at T" using "News at T-i", we join Price(T) with News(T-i).
            # The previous code did: `df_lag = df_news.select([ (date + i) as date, tokens ])`.
            # This shifts News forward by i days.
            # So News(T-i) becomes News(T).
            
            df_lag = df_news_daily.select([
                (pl.col("date") + timedelta(days=i)).alias("date"),
                pl.col("tokens").alias(f"news_lag{i}")
            ])
            df = df.join(df_lag, on="date", how="left")
        
        # null 값은 빈 리스트로 채움
        for i in range(1, self.lags + 1):
            df = df.with_columns(pl.col(f"news_lag{i}").fill_null([]))
            
        # 뉴스가 하나도 없는 날은 제외? -> 재무 팩터가 있으면 아닐 수도 있음.
        # But LassoLearner relies heavily on text. Keep filter for now to avoid empty rows?
        # Actually Hybrid model can predict without news if fundamentals exist.
        # But our task says "Lasso Model Extension".
        # Let's keep rows even if no news, treating tokens as empty list.
        # BUT previous code filtered it: `df.filter(pl.any_horizontal(...))`.
        # If I remove this filter, training set increases.
        # Let's REMOVE the filter to allow Fundamental-only prediction on no-news days.
        
        return df

    def train(self, df, stock_code=None):
        # 1. Text Features (TF-IDF)
        all_token_lists = []
        for i in range(1, self.lags + 1):
            if f"news_lag{i}" in df.columns:
                for lst in df[f"news_lag{i}"].to_list():
                    if lst and len(lst) > 0:
                        clean_lst = [str(t) for t in lst if t is not None]
                        if clean_lst:
                            all_token_lists.append(clean_lst)
        
        # 기본적으로 텍스트가 없으면 학습이 어렵지만, 재무 팩터만으로도 학습 가능하도록 수정
        X_text = None
        feature_names = []
        
        if all_token_lists:
            # Black Swan 구제를 위해 일단 모든 단어를 포함 (min_df=1)
            print(f"  Fitting vectorizer on {len(all_token_lists)} non-empty token lists...")
            original_min_df = self.vectorizer.min_df
            self.vectorizer.min_df = 1 
            self.vectorizer.fit(all_token_lists)
            
            feature_names = list(self.vectorizer.get_feature_names_out())
            
            X_list = []
            for i in range(1, self.lags + 1):
                if f"news_lag{i}" in df.columns:
                    X_lag = self.vectorizer.transform(df[f"news_lag{i}"].to_list())
                else:
                    # 빈 행렬? Or should ensure columns exist
                    X_lag = self.vectorizer.transform([[]] * len(df))
                X_list.append(X_lag)
            
            X_text = hstack(X_list)
        else:
            print("  No tokens found, proceeding with Dense features only.")
            
        # 2. Dense Features (Fundamentals)
        dense_cols = ["per", "pbr", "roe", "log_market_cap"]
        X_dense = df.select(dense_cols).to_numpy()
        
        # Scale Dense Features
        scaler = StandardScaler()
        X_dense_scaled = scaler.fit_transform(X_dense)
        scaler_params = {
            "mean": scaler.mean_.tolist(),
            "scale": scaler.scale_.tolist(),
            "cols": dense_cols
        }
        
        # 3. Combine Features
        if X_text is not None:
            # Sparse + Dense stacking
            # hstack handle sparse matrix efficiently
            X = hstack([X_text, X_dense_scaled])
        else:
            X = X_dense_scaled
            
        y = df["excess_return"].cast(pl.Float64).to_numpy()
        
        # Volatility-weighted IDF 및 Black Swan 필터링 (Text Only?)
        # Dense features should usually be KEPT.
        # But `calculate_volatility_weights_with_filter` assumes X columns map to `feature_names_raw`.
        # We need to adjust indices.
        
        # Feature Names construction
        feature_names_raw = []
        if X_text is not None:
             for lag in range(1, self.lags + 1):
                feature_names_raw.extend([f"{name}_L{lag}" for name in feature_names])
                
        # Append Dense feature names with prefix '__F_'
        dense_feature_names = [f"__F_{c}__" for c in dense_cols]
        feature_names_raw.extend(dense_feature_names)
        
        # Volatility Filter (Apply to Text indices only?)
        # Or apply to everything.
        # Dense features might be filtered if they don't correlate?
        # Let's trust Lasso for Dense feature selection, but keep them in "Candidate" set.
        
        # Current logic `calculate_volatility_weights_with_filter` expects X to be sparse usually?
        # It handles `X > 0`. `X_dense_scaled` can be negative.
        # Volatility Weighting logic is designed for Bag-Of-Words (Positive Occurrence).
        # For Dense features, this logic might be wrong.
        # Strategy: Apply Volatility Weights ONLY to Text part. Dense part gets weight 1.0.
        
        weights = np.ones(X.shape[1])
        keep_indices = list(range(X.shape[1])) # Default keep all
        
        if X_text is not None:
            text_dim = X_text.shape[1]
            # Extract Text part for Volatility Calc
            # X is csr_matrix or coo_matrix. slicing `X[:, :text_dim]`.
            X_text_part = X[:, :text_dim]
            
            w_text, keep_idx_text = self.calculate_volatility_weights_with_filter(df, X_text_part, self.vectorizer.min_df if hasattr(self.vectorizer, 'min_df') else 1)
            
            # dense indices
            dense_indices = list(range(text_dim, X.shape[1]))
            
            # Combine
            # Weights: Text weights + [1.0] * dense_dim
            weights[:text_dim] = w_text
            
            # Keep indices: keep_idx_text + dense_indices
            keep_indices = keep_idx_text + dense_indices
            
        self.keep_indices = keep_indices
        self.scaler_params = scaler_params # Store for predict
        
        # 선택된 피처만 유지
        X_filtered = X[:, keep_indices]
        weights_filtered = weights[keep_indices]
        
        # 가중치 적용 (Sparse compatible multiply)
        X_weighted = X_filtered.multiply(weights_filtered)
        
        print(f"    [Train] Original Features: {X.shape[1]}, Filtered: {X_weighted.shape[1]} (Text+Dense)")
        self.model.fit(X_weighted, y)
        
        # 결과 저장용 사전 생성
        feature_names_filtered = [feature_names_raw[i] for i in keep_indices]
        
        sentiment_dict = {}
        stock_names = []
        if stock_code:
            with get_db_cursor() as cur:
                cur.execute("SELECT stock_name FROM tb_stock_master WHERE stock_code = %s", (stock_code,))
                row = cur.fetchone()
                if row:
                    name = row['stock_name']
                    if name:
                        stock_names = [name, name.replace("전자", "").strip()]
        
        for name, coef in zip(feature_names_filtered, self.model.coef_):
            if coef != 0:
                # Filter out stock name related keywords (Text only)
                if not name.startswith("__F_"):
                    base_name = name.rsplit('_L', 1)[0]
                    if base_name in stock_names:
                        continue
                sentiment_dict[name] = float(coef)
                
        # Return Dict AND Scaler Params
        return sentiment_dict, scaler_params

    def calculate_volatility_weights_with_filter(self, df, X, min_df):
        """
        변동성 가중치를 계산하고, 희소 단어 중 'Black Swan' (고변동성) 단어만 살려냅니다.
        """
        y_abs = np.abs(df["excess_return"].cast(pl.Float64).to_numpy())
        word_presence = (X > 0).astype(float)
        
        vol_sum = word_presence.T.dot(y_abs)
        word_count = np.array(word_presence.sum(axis=0)).flatten()
        
        # 변동성 가중치 = 해당 단어가 나타난 날들의 평균 절대 수익률
        weights = np.divide(vol_sum, word_count, out=np.zeros_like(vol_sum), where=word_count!=0)
        
        # 필터링 조건:
        # 1. 빈도가 min_df 이상인 단어
        # 2. 빈도가 낮더라도 변동성 가중치가 상위 10%이거나 평균의 2배 이상인 단어 (Black Swan)
        avg_vol = np.mean(weights[weights > 0]) if np.any(weights > 0) else 0
        
        keep_indices = []
        for i in range(len(weights)):
            count = word_count[i]
            vol = weights[i]
            
            if count >= min_df:
                keep_indices.append(i)
            elif count > 0 and vol > avg_vol * 2.0: # Black Swan 구제
                keep_indices.append(i)
        
        # 가중치 정규화 (평균 1.0)
        if np.mean(weights) > 0:
            weights = weights / np.mean(weights)
        else:
            weights = np.ones_like(weights)
            
        return weights, keep_indices

    def save_dict(self, sentiment_dict, version, stock_code, source='Main', meta=None):
        from psycopg2.extras import execute_values
        with get_db_cursor() as cur:
            # 기존 버전/종목 삭제
            cur.execute(
                "DELETE FROM tb_sentiment_dict WHERE version = %s AND source = %s AND stock_code = %s", 
                (version, source, stock_code)
            )
            
            if sentiment_dict:
                values = [(word, beta, version, source, stock_code) for word, beta in sentiment_dict.items()]
                execute_values(cur, """
                    INSERT INTO tb_sentiment_dict (word, beta, version, source, stock_code) 
                    VALUES %s
                """, values)
            
            # 메타데이터 저장
            if meta:
                cur.execute("""
                    INSERT INTO tb_sentiment_dict_meta 
                    (stock_code, version, source, lookback_months, train_start_date, train_end_date, metrics, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (stock_code, version, source) DO UPDATE SET
                    metrics = EXCLUDED.metrics,
                    is_active = EXCLUDED.is_active
                """, (
                    stock_code, version, source, 
                    meta.get('lookback_months'),
                    meta.get('train_start_date'),
                    meta.get('train_end_date'),
                    json.dumps(meta.get('metrics', {})),
                    meta.get('is_active', False)
                ))

    def predict(self, df):
        """
        학습된 모델을 사용하여 수익률을 예측합니다.
        DF는 prepare_features를 거친 상태여야 함 (Dense 포함)
        """
        # 1. Text Features
        X_list = []
        for i in range(1, self.lags + 1):
             if f"news_lag{i}" in df.columns:
                X_lag = self.vectorizer.transform(df[f"news_lag{i}"].to_list())
             else:
                X_lag = self.vectorizer.transform([[]] * len(df))
             X_list.append(X_lag)
        
        X_text = hstack(X_list)
        
        # 2. Dense Features
        if hasattr(self, 'scaler_params'):
            dense_cols = self.scaler_params['cols']
            mean = np.array(self.scaler_params['mean'])
            scale = np.array(self.scaler_params['scale'])
            
            # Extract raw values
            X_dense = df.select(dense_cols).to_numpy()
            # Scale manually using stored params (to ensure consistency vs recreating Scaler)
            X_dense_scaled = (X_dense - mean) / scale
            
            X = hstack([X_text, X_dense_scaled])
        else:
            # Fallback (Should not happen if trained)
            X = X_text
        
        # 학습 시 사용된 필터링 적용
        if self.keep_indices is not None:
             # Ensure indices are within bounds
             # If prediction set has mismatching features (e.g. vectorizer vocab diff), this fails.
             # But vectorizer is same self instance.
             # New words are ignored by transform.
            X = X[:, self.keep_indices]
            
        return self.model.predict(X)

    def run_training(self, stock_code, start_date, end_date, version=None, source='Main', is_active=True):
        df_prices, df_news, df_fund = self.fetch_data(stock_code, start_date, end_date)
        if df_prices is None or len(df_prices) < 3:
            print(f"Insufficient data for {stock_code} in range {start_date}~{end_date}")
            return None
            
        df = self.prepare_features(df_prices, df_news, df_fund)
        sentiment_dict, scaler_params = self.train(df, stock_code=stock_code)
        
        if version is None:
            version = datetime.now().strftime("%Y%m%d_%H%M")
            
        # 메타데이터 구성 (AWO 등을 위해 개월수 계산)
        s_dt = datetime.strptime(start_date, '%Y-%m-%d')
        e_dt = datetime.strptime(end_date, '%Y-%m-%d')
        lookback_months = (e_dt.year - s_dt.year) * 12 + (e_dt.month - s_dt.month)
        
        meta = {
            'lookback_months': lookback_months,
            'train_start_date': start_date,
            'train_end_date': end_date,
            'metrics': {
                'word_count': len(sentiment_dict),
                'scaler': scaler_params # Save scaler params for Inference
            },
            'is_active': is_active
        }
        
        if is_active:
            self.deactivate_all_versions(stock_code, source)

        self.save_dict(sentiment_dict, version, stock_code, source=source, meta=meta)
        print(f"Training completed for {stock_code}. {len(sentiment_dict)} words + factors saved (version: {version}, active: {is_active}).")
        return sentiment_dict

    def deactivate_all_versions(self, stock_code, source):
        with get_db_cursor() as cur:
            cur.execute(
                "UPDATE tb_sentiment_dict_meta SET is_active = FALSE WHERE stock_code = %s AND source = %s",
                (stock_code, source)
            )

    def activate_version(self, stock_code, version, source):
        self.deactivate_all_versions(stock_code, source)
        with get_db_cursor() as cur:
            cur.execute(
                "UPDATE tb_sentiment_dict_meta SET is_active = TRUE WHERE stock_code = %s AND version = %s AND source = %s",
                (stock_code, version, source)
            )

    def find_optimal_lag(self, stock_code, start_date, end_date, max_lag=5):
        """
        1부터 max_lag까지 시차를 변경하며 검증 성능이 가장 좋은 시차를 찾습니다.
        """
        best_lag = 1
        best_score = -np.inf
        
        print(f"Finding optimal lag for {stock_code} (max: {max_lag})...")
        
        # 원본 lags 저장
        original_lags = self.lags
        
        for lag in range(1, max_lag + 1):
            self.lags = lag
            df_prices, df_news, df_fund = self.fetch_data(stock_code, start_date, end_date)
            if df_prices is None or len(df_prices) < 10:
                continue
                
            df = self.prepare_features(df_prices, df_news, df_fund)
            if len(df) < 5:
                continue
                
            # 간단한 시계열 교차 검증 (마지막 20%를 테스트로 사용)
            split_idx = int(len(df) * 0.8)
            df_train = df.head(split_idx)
            df_test = df.tail(len(df) - split_idx)
            
            try:
                # Train returns tuple now, but we just need side-effects (self.model, self.scaler_params)
                self.train(df_train, stock_code=stock_code)
                y_true = df_test["excess_return"].cast(pl.Float64).to_numpy()
                y_pred = self.predict(df_test)
                
                # 방향성 정확도(Directional Accuracy) 기준
                y_true_dir = (y_true > 0).astype(int)
                y_pred_dir = (y_pred > 0).astype(int)
                score = np.mean(y_true_dir == y_pred_dir)
                
                print(f"  Lag {lag}: Directional Accuracy = {score:.4f}")
                
                if score > best_score:
                    best_score = score
                    best_lag = lag
            except Exception as e:
                print(f"  Error testing lag {lag}: {e}")
                
        self.lags = original_lags
        print(f"Optimal lag for {stock_code} is {best_lag} (Acc: {best_score:.4f})")
        
        # DB에 영구 저장
        with get_db_cursor() as cur:
            cur.execute(
                "UPDATE daily_targets SET optimal_lag = %s WHERE stock_code = %s",
                (best_lag, stock_code)
            )
            
        return best_lag
