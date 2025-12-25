import polars as pl
from sklearn.linear_model import Lasso, LassoCV, LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
from src.db.connection import get_db_cursor
from src.nlp.tokenizer import Tokenizer
from datetime import datetime, timedelta
from scipy.sparse import hstack
import json

# Global cache to avoid redundant tokenization across different learner instances or iterations
TOKEN_CACHE = {}

# Black Swan Critical Words (Hybird Lexicon Anchor)
CRITICAL_WORDS = {
    "배임", "횡령", "화재", "소송", "고발", "고소", "압수수색", "구속", "해킹", "전쟁",
    "부도", "파산", "상장폐지", "거래정지", "분식회계", "하한가", "유상증자"
}

class LassoLearner:
    def __init__(self, alpha=0.00001, n_gram=3, lags=5, min_df=3, max_features=50000, use_fundamentals=True, use_sector_beta=False, use_cv_lasso=False):
        self.alpha = alpha
        self.n_gram = n_gram
        self.lags = lags
        self.min_df = min_df
        self.max_features = max_features
        self.use_fundamentals = use_fundamentals
        self.use_sector_beta = use_sector_beta
        self.use_fundamentals = use_fundamentals
        self.use_sector_beta = use_sector_beta
        self.use_cv_lasso = use_cv_lasso
        self.use_stability_selection = False # Default off, enable for production
        self.tokenizer = Tokenizer()
        # 리스트 입력을 직접 받기 위해 tokenizer를 identity 함수로 설정
        self.vectorizer = TfidfVectorizer(
            tokenizer=lambda x: x,
            lowercase=False,
            token_pattern=None,
            min_df=self.min_df,
            max_features=self.max_features
        )
        if self.use_cv_lasso:
            # Try a range of autos
            self.model = LassoCV(cv=5, max_iter=10000, n_jobs=-1, random_state=42)
        else:
            self.model = Lasso(alpha=self.alpha, max_iter=10000)
        self.keep_indices = None # Black Swan 필터링 결과 저장용

    def fetch_data(self, stock_code, start_date, end_date, prefetched_df_news=None):
        """
        특정 기간의 주가, 뉴스, 재무 데이터를 가져옵니다.
        prefetched_df_news: (Memory Opt) 미리 가져온 뉴스 DataFrame (Optional)
        """
        with get_db_cursor() as cur:
            # Fetch prices
            if self.use_sector_beta:
                # Use Pure Alpha (Stock Return - Sector Return)
                sql = """
                    SELECT date, stock_code, (return_rate - COALESCE(sector_return, 0)) as excess_return 
                    FROM tb_daily_price 
                    WHERE stock_code = %s AND date BETWEEN %s AND %s
                    ORDER BY date ASC
                """
            else:
                # Use Market Alpha (Traditional Excess Return)
                sql = """
                    SELECT date, stock_code, excess_return 
                    FROM tb_daily_price 
                    WHERE stock_code = %s AND date BETWEEN %s AND %s
                    ORDER BY date ASC
                """
            cur.execute(sql, (stock_code, start_date, end_date))
            prices = cur.fetchall()
            
            fundamentals = []
            if self.use_fundamentals:
                # Fetch fundamentals (TASK-038)
                cur.execute("""
                    SELECT base_date as date, per, pbr, roe, market_cap
                    FROM tb_stock_fundamentals
                    WHERE stock_code = %s AND base_date BETWEEN %s AND %s
                    ORDER BY base_date ASC
                """, (stock_code, start_date, end_date))
                fundamentals = cur.fetchall()

            # Fetch news (lags를 고려하여 시작일을 앞당김)
            news_start_dt = datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=self.lags + 2)
            news_start = news_start_dt.strftime('%Y-%m-%d')
            news_end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            if prefetched_df_news is not None and not prefetched_df_news.is_empty():
                # Filter from prefetched dataframe
                # Ensure dates are comparable
                df_news = prefetched_df_news.filter(
                    (pl.col("date") >= news_start_dt.date()) & 
                    (pl.col("date") <= news_end_dt.date())
                )
                news = None # Signal that we have df_news
            else:
                cur.execute("""
                    SELECT c.published_at::date as date, c.content
                    FROM tb_news_content c
                    JOIN tb_news_mapping m ON c.url_hash = m.url_hash
                    WHERE m.stock_code = %s AND c.published_at::date BETWEEN %s AND %s
                """, (stock_code, news_start, end_date))
                news = cur.fetchall()
                df_news = None
            
        if not prices:
            print(f"No price data for {stock_code}")
            return None, None, None
            
        df_prices = pl.DataFrame(prices)
        if df_news is None:
            df_news = pl.DataFrame(news) if news else pl.DataFrame({"date": [], "content": []})
            
        df_fund = pl.DataFrame(fundamentals) if fundamentals else pl.DataFrame({"date": [], "per": [], "pbr": [], "roe": [], "market_cap": []})
        
        return df_prices, df_news, df_fund



    def prepare_features(self, df_prices, df_news, df_fund):
        from src.utils.calendar import Calendar
        stock_code = df_prices["stock_code"][0] if not df_prices.is_empty() else None
        
        # 1. 뉴스 토큰화 및 Impact Date 맵핑
        if not df_news.is_empty() and stock_code:
            print(f"    Tokenizing and mapping impact dates for {len(df_news)} news items...")
            
            # published_at_hint 혹은 content의 날짜 정보를 바탕으로 impact_date 계산
            # Calendar.get_impact_date(stock_code, date) 사용
            global TOKEN_CACHE
            
            def get_cached_tokens(content):
                if content in TOKEN_CACHE:
                    return TOKEN_CACHE[content]
                tokens = self.tokenizer.tokenize(content, n_gram=self.n_gram)
                # Keep cache size manageable - LRU-ish: clear 25% if full
                if len(TOKEN_CACHE) > 50000:
                    keys_to_remove = list(TOKEN_CACHE.keys())[:10000]
                    for k in keys_to_remove:
                        del TOKEN_CACHE[k]
                TOKEN_CACHE[content] = tokens
                return tokens

            df_news = df_news.with_columns(
                pl.col("content").map_elements(
                    get_cached_tokens,
                    return_dtype=pl.List(pl.String)
                ).alias("tokens"),
                pl.col("date").map_elements(
                    lambda d: Calendar.get_impact_date(stock_code, d),
                    return_dtype=pl.Date
                ).alias("impact_date")
            )
            # impact_date 기준으로 뉴스 취합 (주말 뉴스는 월요일로 모임)
            df_news_daily = df_news.group_by("impact_date").agg(pl.col("tokens").flatten())
            df_news_daily = df_news_daily.rename({"impact_date": "date"})
        else:
            df_news_daily = pl.DataFrame({"date": [], "tokens": []})
        
        # 2. 기본 데이터 병합 (Prices + Fundamentals)
        df = df_prices.clone()
        
        if self.use_fundamentals:
            if not df_fund.is_empty():
                df = df.join(df_fund, on="date", how="left")
                df = df.with_columns([
                    pl.col("per").fill_null(strategy="forward").fill_null(0.0),
                    pl.col("pbr").fill_null(strategy="forward").fill_null(0.0),
                    pl.col("roe").fill_null(strategy="forward").fill_null(0.0),
                    pl.col("market_cap").fill_null(strategy="forward").fill_null(0.0)
                ])
                df = df.with_columns(
                    pl.col("market_cap").clip(lower_bound=1.0).log().alias("log_market_cap")
                )
            else:
                df = df.with_columns([
                    pl.lit(0.0).alias("per"),
                    pl.lit(0.0).alias("pbr"),
                    pl.lit(0.0).alias("roe"),
                    pl.lit(0.0).alias("log_market_cap")
                ])
        
        # 3. 거래일 기준 시차(Lag) 피처 생성
        # 캘린더 날짜가 아닌 '거래일 순서'대로 JOIN
        trading_days = Calendar.get_trading_days(stock_code)
        
        for i in range(1, self.lags + 1):
            # i번째 전 거래일의 뉴스를 현재 거래일로 가져옴
            # df_news_daily는 이미 impact_date(거래일) 기준으로 정리됨
            
            # 매핑 로직:
            # current_date가 trading_days의 j번째 인덱스라면,
            # lag1 뉴스는 j번 인덱스에 매핑된 뉴스 (당일 뉴스) -> 이건 보통 리드타임 때문에 불가능함.
            # 보통 lag1은 '가장 최근에 사용 가능한 뉴스'를 의미함.
            
            # 여기서 정의:
            # Lag 1: T일의 주가 등락을 예측하기 위해 사용하는 'T일의 Impact Date를 가진 뉴스'
            # (즉, T일 장전 혹은 T-1 장후 뉴스)
            
            df_lag = df_news_daily.select([
                pl.col("date"),
                pl.col("tokens").alias(f"news_lag{i}")
            ])
            
            # Trading Day Lag Join
            # i=1이면 현재 날짜의 뉴스 (Impact Date가 오늘인 뉴스)
            # i=2이면 이전 거래일의 뉴스
            if i == 1:
                df = df.join(df_lag, on="date", how="left")
            else:
                # 이전 거래일 매핑을 위해 trading_days 인덱스 활용
                # polars의 shift 기능 활용 가능
                df_temp = df_news_daily.clone()
                # Trading days 리스트 상에서 i-1 만큼 뒤로 밀어야 함
                # (예: 20일에 19일 뉴스를 붙이고 싶다면, 19일 뉴스의 date를 20일로 바꿔야 함)
                
                # Trading Day List를 DataFrame으로 만들어 시차 생성
                df_td = pl.DataFrame({"td": trading_days})
                df_td = df_td.with_columns(
                    pl.col("td").shift(-(i-1)).alias("target_date")
                )
                
                df_lag_shifted = df_lag.join(df_td, left_on="date", right_on="td", how="inner")
                df_lag_shifted = df_lag_shifted.select([
                    pl.col("target_date").alias("date"),
                    pl.col(f"news_lag{i}")
                ])
                df = df.join(df_lag_shifted, on="date", how="left")

        # null 값은 빈 리스트로 채움
        for i in range(1, self.lags + 1):
            df = df.with_columns(pl.col(f"news_lag{i}").fill_null([]))
            
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
                    X_lag = self.vectorizer.transform([[]] * len(df))
                X_list.append(X_lag)
            
            X_text = hstack(X_list).tocsr()
        else:
            print("  No tokens found, proceeding with Dense features only.")
            
        # 2. Dense Features (Fundamentals)
        X_dense_scaled = None
        scaler_params = {}
        
        if self.use_fundamentals:
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
        if X_text is not None and X_dense_scaled is not None:
            X = hstack([X_text, X_dense_scaled]).tocsr()
        elif X_text is not None:
            X = X_text
        elif X_dense_scaled is not None:
            X = X_dense_scaled
        else:
            raise ValueError("No features available for training (Text or Fundamentals required)")
            
        y = df["excess_return"].cast(pl.Float64).to_numpy()
        
        # Volatility-weighted IDF 및 Black Swan 필터링 (Text Only?)
        # Dense features should usually be KEPT.
        # But `calculate_volatility_weights_with_filter` assumes X columns map to `feature_names_raw`.
        # We need to adjust indices.
        
        # Volatility-weighted IDF 및 Black Swan 필터링
        
        # Feature Names construction
        feature_names_raw = []
        if X_text is not None:
             for lag in range(1, self.lags + 1):
                feature_names_raw.extend([f"{name}_L{lag}" for name in feature_names])
                
        # Append Dense feature names with prefix '__F_'
        if self.use_fundamentals:
             dense_feature_names = [f"__F_{c}__" for c in ["per", "pbr", "roe", "log_market_cap"]]
             feature_names_raw.extend(dense_feature_names)
        
        # Volatility Filter
        weights = np.ones(X.shape[1])
        keep_indices = list(range(X.shape[1])) # Default keep all
        
        if X_text is not None:
            text_dim = X_text.shape[1]
            # Extract Text part for Volatility Calc
            X_text_part = X[:, :text_dim]
            
            # Pass feature_names to filter (Needs stripping _L suffixes)
            # feature_names_raw has structure "word_L1", "word_L2", etc.
            # We need the base word.
            text_feature_names = feature_names_raw[:text_dim]
            
            w_text, keep_idx_text = self.calculate_volatility_weights_with_filter(
                df, X_text_part, 
                self.vectorizer.min_df if hasattr(self.vectorizer, 'min_df') else 1,
                feature_names=text_feature_names
            )
            
            # Apply Ordered Lasso Decay (Lag Penalty)
            # Each feature name is "Word_L{k}"
            # Weight *= (0.75 ** (k-1)) -> Penalize old lags (make weight smaller -> beta larger? NO.)
            # Wait, scaling X by w (w<1) INCREASES penalty.
            # We want to penalize Lag 5 more. So Lag 5 X should be smaller.
            # w = gamma ** (lag-1) where gamma = 0.75
            # Lag 1: 1.0, Lag 5: 0.31
            # w_text contains Volatility Weights. We MULTIPLY decay.
            
            gamma = 0.75
            for idx in range(text_dim):
                fname = text_feature_names[idx]
                # Parse lag from name "word_L1"
                try:
                    lag_str = fname.rsplit('_L', 1)[1]
                    lag_val = int(lag_str)
                except:
                    lag_val = 1
                
                decay = gamma ** (lag_val - 1)
                w_text[idx] *= decay

            # dense indices
            dense_indices = []
            if self.use_fundamentals:
                dense_indices = list(range(text_dim, X.shape[1]))
            
            # Combine
            weights[:text_dim] = w_text
            
            # Keep indices: keep_idx_text + dense_indices
            keep_indices = keep_idx_text + dense_indices
            
        self.keep_indices = keep_indices
        self.scaler_params = scaler_params # Store for predict
        
        # 선택된 피처만 유지
        X_filtered = X[:, keep_indices]
        weights_filtered = weights[keep_indices]
        
        # 가중치 적용 (Sparse compatible multiply)
        X_weighted = X_filtered.tocsr().multiply(weights_filtered)
        
        print(f"    [Train] Original Features: {X.shape[1]}, Filtered: {X_weighted.shape[1]} (Use Fund: {self.use_fundamentals})")
        print(f"    [Train] Original Features: {X.shape[1]}, Filtered: {X_weighted.shape[1]} (Use Fund: {self.use_fundamentals})")
        
        # --- Stability Selection (Bootstrap) ---
        if self.use_stability_selection and X_weighted.shape[1] > 0:
            print("    [Stability] Running Bootstrap Selection (n=5)...")
            n_bootstraps = 5
            sample_fraction = 0.7
            threshold = 0.6
            
            n_samples = X_weighted.shape[0]
            n_feats = X_weighted.shape[1]
            stability_counts = np.zeros(n_feats)
            
            # Check for critical words indices to force keep
            force_keep_mask = np.zeros(n_feats, dtype=bool)
            # feature_names_filtered is available only after we decide strictly? 
            # We must map current X_weighted cols to names.
            # feature_names_raw indices were mapped by keep_indices.
            # So naming aligns with X_weighted columns.
            
            current_names = [feature_names_raw[i] for i in keep_indices]
            for idx, name in enumerate(current_names):
                base = name.rsplit('_L', 1)[0]
                if base in CRITICAL_WORDS:
                    force_keep_mask[idx] = True
            
            for b in range(n_bootstraps):
                # Resample
                indices = np.random.choice(n_samples, int(n_samples * sample_fraction), replace=False)
                X_sub = X_weighted[indices]
                y_sub = y[indices]
                
                # Fit
                if self.use_cv_lasso:
                    # CV is too slow inside bootstrap, use simple Lasso
                    sub_model = Lasso(alpha=self.alpha, max_iter=2000)
                else:
                    sub_model = Lasso(alpha=self.alpha, max_iter=2000)
                    
                sub_model.fit(X_sub, y_sub)
                stability_counts += (sub_model.coef_ != 0).astype(int)
                
            selection_probs = stability_counts / n_bootstraps
            stable_mask = (selection_probs >= threshold) | force_keep_mask
            
            # Refit on stable features only (Relaxed Lasso)
            # We only keep columns where stable_mask is True
            stable_indices_local = np.where(stable_mask)[0]
            
            if len(stable_indices_local) == 0:
                print("    [Stability] Warning: No features survived stability selection. Reverting to all.")
                self.model.fit(X_weighted, y)
            else:
                X_stable = X_weighted[:, stable_indices_local]
                print(f"    [Stability] {len(stable_indices_local)}/{n_feats} features selected.")
                self.model.fit(X_stable, y)
                
                # Expand coefs back to X_weighted size (filling zeros)
                full_coefs = np.zeros(n_feats)
                full_coefs[stable_indices_local] = self.model.coef_
                self.model.coef_ = full_coefs
                # Hack: intercept might be different, but for dictionary we care about coefs.
                
        else:
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
        
        for idx, (name, coef) in enumerate(zip(feature_names_filtered, self.model.coef_)):
            if coef != 0:
                # Filter out stock name related keywords (Text only)
                if not name.startswith("__F_"):
                    base_name = name.rsplit('_L', 1)[0]
                    if base_name in stock_names:
                        continue
                
                # Recover Real Beta: Beta_Real = Beta_Model * Weight
                # X_w = X * W
                # y = X_w * B_m = X * (W * B_m)
                real_beta = coef * weights_filtered[idx]
                sentiment_dict[name] = float(real_beta)
                
        # Return Dict AND Scaler Params
        return sentiment_dict, scaler_params

    def calculate_volatility_weights_with_filter(self, df, X, min_df, feature_names=None):
        """
        변동성 가중치를 계산하고, 희소 단어 중 'Black Swan' (고변동성) 단어만 살려냅니다.
        feature_names: 리스트, 각 컬럼의 피처 이름 (ex: "word_L1")
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
        # 3. CRITICAL_WORDS에 포함된 단어 (Hybrid Lexicon Anchor)
        avg_vol = np.mean(weights[weights > 0]) if np.any(weights > 0) else 0
        
        keep_indices = []
        for i in range(len(weights)):
            count = word_count[i]
            vol = weights[i]
            
            # Check Critical Word (Strip _L suffix)
            is_critical = False
            if feature_names:
                fname = feature_names[i]
                base_word = fname.rsplit('_L', 1)[0]
                if base_word in CRITICAL_WORDS:
                    is_critical = True

            if count >= min_df:
                keep_indices.append(i)
            elif count > 0 and (vol > avg_vol * 2.0 or is_critical): # Black Swan 구제
                keep_indices.append(i)
                if is_critical:
                     # Critical words get a weight boost to ensure visibility if they are rare
                     weights[i] = max(weights[i], avg_vol * 2.0)
        
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
                    (stock_code, version, source, lookback_months, train_start_date, train_end_date, metrics, is_active, use_sector_beta)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (stock_code, version, source) DO UPDATE SET
                    metrics = EXCLUDED.metrics,
                    is_active = EXCLUDED.is_active,
                    use_sector_beta = EXCLUDED.use_sector_beta
                """, (
                    stock_code, version, source, 
                    meta.get('lookback_months'),
                    meta.get('train_start_date'),
                    meta.get('train_end_date'),
                    json.dumps(meta.get('metrics', {})),
                    meta.get('is_active', False),
                    meta.get('use_sector_beta', False)
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
        
        X_text = hstack(X_list).tocsr()
        
        # 2. Dense Features
        if self.use_fundamentals and hasattr(self, 'scaler_params') and self.scaler_params:
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
            X = X.tocsr()
            X = X[:, self.keep_indices]
            
        return self.model.predict(X)

    def run_training(self, stock_code, start_date, end_date, version=None, source='Main', is_active=True, prefetched_df_news=None):
        df_prices, df_news, df_fund = self.fetch_data(stock_code, start_date, end_date, prefetched_df_news=prefetched_df_news)
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
            'is_active': is_active,
            'use_sector_beta': self.use_sector_beta
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
