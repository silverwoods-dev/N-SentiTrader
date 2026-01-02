import polars as pl
from sklearn.linear_model import LinearRegression
from celer import Lasso, LassoCV
try:
    from src.learner.mlx_lasso import MLXLasso, MLXLassoCV
    MLX_AVAILABLE = True
except ImportError:
    MLX_AVAILABLE = False
from sklearn.preprocessing import StandardScaler, MaxAbsScaler
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
from src.db.connection import get_db_cursor
from src.nlp.tokenizer import Tokenizer
from datetime import datetime, timedelta
from scipy.sparse import hstack
import json
from src.utils.stock_info import get_stock_aliases

# Global cache to avoid redundant tokenization across different learner instances or iterations
TOKEN_CACHE = {}
GLOBAL_LEXICON_CACHE = set() # Discovered words to rescue

# Black Swan Critical Words (Hybird Lexicon Anchor)
CRITICAL_WORDS = {
    "배임", "횡령", "화재", "소송", "고발", "고소", "압수수색", "구속", "해킹", "전쟁",
    "부도", "파산", "상장폐지", "거래정지", "분식회계", "하한가", "유상증자"
}

class LassoLearner:
    # Phase 38 Enhancement: Extended parameters with dynamic decay
    # Research-backed: n-gram=3 for better context, lag=5 for 5-day news window, auto decay for optimal weights
    def __init__(self, alpha=0.00001, n_gram=3, lags=5, min_df=3, max_features=25000, 
                 use_fundamentals=True, use_sector_beta=False, use_cv_lasso=False, 
                 use_summary=False, use_tech_indicators=False,
                 decay_rate='auto', min_relevance=0,
                 engine='celer'):
        self.alpha = alpha
        self.n_gram = n_gram
        self.lags = lags
        self.min_df = min_df
        self.max_features = max_features
        self.use_fundamentals = use_fundamentals
        self.use_sector_beta = use_sector_beta
        self.use_cv_lasso = use_cv_lasso
        self.use_summary = use_summary
        self.use_tech_indicators = use_tech_indicators
        self.decay_rate = decay_rate  # Can be float or 'auto' for dynamic calculation
        self._dynamic_decay_weights = None  # Cache for dynamic decay
        self.min_relevance = min_relevance
        self.use_stability_selection = False # Default off, enable for production
        self.engine = engine
        self.tokenizer = Tokenizer()
        # Phase 37: Added max_df=0.85 to auto-filter high-frequency neutral words
        self.vectorizer = TfidfVectorizer(
            tokenizer=lambda x: x,
            lowercase=False,
            token_pattern=None,
            min_df=self.min_df,
            max_df=0.85,  # Remove terms appearing in >85% of docs (neutral words)
            max_features=self.max_features
        )
        
        # Select model based on engine
        if self.engine == 'mlx' and MLX_AVAILABLE:
            if self.use_cv_lasso:
                self.model = MLXLassoCV(cv=5, max_iter=1000, verbose=False)
            else:
                self.model = MLXLasso(alpha=self.alpha, max_iter=1000, verbose=False)
        else:
            # Default: Celer (CPU optimized)
            if self.engine == 'mlx' and not MLX_AVAILABLE:
                import logging
                logging.warning("MLX not available, falling back to Celer engine.")
            if self.use_cv_lasso:
                self.model = LassoCV(cv=5, max_iter=10000, n_jobs=-1)
            else:
                self.model = Lasso(alpha=self.alpha, max_iter=10000)
        self.keep_indices = None # Black Swan 필터링 결과 저장용

    def fetch_data(self, stock_code, start_date, end_date, prefetched_df_news=None, min_relevance=None):
        """
        특정 기간의 주가, 뉴스, 재무 데이터를 가져옵니다.
        prefetched_df_news: (Memory Opt) 미리 가져온 뉴스 DataFrame (Optional)
        min_relevance: 뉴스 필터링 기준 점수 (Optional, defaults to self.min_relevance)
        """
        target_relevance = min_relevance if min_relevance is not None else self.min_relevance
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
                # [Hybrid v2] summary_content 필드 추가 확인
                cur.execute("""
                    SELECT c.published_at::date as date, c.content, c.extracted_content, c.url_hash
                    FROM tb_news_content c
                    JOIN tb_news_mapping m ON c.url_hash = m.url_hash
                    WHERE m.stock_code = %s 
                    AND c.published_at::date BETWEEN %s AND %s
                    AND m.is_relevant = TRUE
                    AND m.relevance_score >= %s
                """, (stock_code, news_start, end_date, target_relevance))
                news = cur.fetchall()
                
                if self.use_summary and news:
                    from src.nlp.summarizer import NewsSummarizer
                    NewsSummarizer.bulk_ensure_summaries(news)
                df_news = None
            
        if not prices:
            print(f"No price data for {stock_code}")
            return None, None, None
            
        df_prices = pl.DataFrame(prices)
        if df_news is None:
            if news:
                df_news = pl.DataFrame(news)
                # [Hybrid v2] Content Selector
                if self.use_summary and "extracted_content" in df_news.columns:
                    df_news = df_news.with_columns(
                        pl.coalesce(pl.col("extracted_content"), pl.col("content")).alias("final_content")
                    )
                else:
                    df_news = df_news.with_columns(pl.col("content").alias("final_content"))
            else:
                df_news = pl.DataFrame({"date": [], "content": [], "final_content": []})
        else:
            # If prefetched, ensure final_content exists
            if "final_content" not in df_news.columns:
                if "extracted_content" in df_news.columns and self.use_summary:
                    df_news = df_news.with_columns(
                        pl.coalesce(pl.col("extracted_content"), pl.col("content")).alias("final_content")
                    )
                else:
                    df_news = df_news.with_columns(pl.col("content").alias("final_content"))
            
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
                # MEMORY_OPT: Keep cache size manageable
                if len(TOKEN_CACHE) > 20000:
                    keys_to_remove = list(TOKEN_CACHE.keys())[:5000]
                    for k in keys_to_remove:
                        del TOKEN_CACHE[k]
                TOKEN_CACHE[content] = tokens
                return tokens

            # Use final_content for tokenization (preferring summary if enabled)
            df_news = df_news.with_columns(
                pl.col("final_content").map_elements(get_cached_tokens, return_dtype=pl.List(pl.String)).alias("tokens"),
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
        
        # [Hybrid v2] Technical Indicators Integration
        if self.use_tech_indicators:
            from src.learner.tech_indicators import TechIndicatorProvider
            df = TechIndicatorProvider.calculate_indicators(df)
            print(f"    [Tech] Added indicators (RSI, MACD)")

        # [Hybrid v2] Content Selector (Raw vs Summarized)
        if self.use_summary and "extracted_content" in df_news.columns:
            # extracted_content가 있는 경우 이를 우선 사용
            df_news = df_news.with_columns(
                pl.coalesce(pl.col("extracted_content"), pl.col("content")).alias("final_content")
            )
        else:
            df_news = df_news.with_columns(pl.col("content").alias("final_content"))
        
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
        # Load Global Lexicon for rescue (Only once per session/instance if needed)
        global GLOBAL_LEXICON_CACHE
        if not GLOBAL_LEXICON_CACHE:
            try:
                with get_db_cursor() as cur:
                    cur.execute("SELECT word FROM tb_global_lexicon WHERE impact_score > 0.02") # 2% Threshold
                    rows = cur.fetchall()
                    GLOBAL_LEXICON_CACHE = {row['word'] for row in rows}
                    if GLOBAL_LEXICON_CACHE:
                        print(f"    [Global] Rescued Lexicon loaded: {len(GLOBAL_LEXICON_CACHE)} words found.")
            except Exception as e:
                print(f"    [Global] Warning: Could not load global lexicon: {e}")

        # 1. Text Features (TF-IDF)
        # 1. Text Features (TF-IDF)
        # MEMORY_OPT: Use Generator instead of List Materialization
        def token_generator():
            for i in range(1, self.lags + 1):
                col_name = f"news_lag{i}"
                if col_name in df.columns:
                    # Polars iter_rows is slow for single column, use to_series().to_list()?
                    # But to_list() materializes.
                    # df[col] is a Series.
                    # We can iterate over the Series directly?
                    # Or just iterating list is fine if list is already in memory via Polars?
                    # Issue: "news_lag{i}" contains LISTS of tokens.
                    # We just need to yield " ".join(tokens) or pass tokens directly if tokenizer=identity
                    
                    series = df[col_name]
                    # We can't avoid some materialization if Polars holds it, but we avoid *double* copy into 'all_token_lists'
                    for tokens_list in series:
                        # Polars List series yields python lists or None, but boolean check might be ambiguous if it's a Polars Series object?
                        # Actually iterating a pl.Series should yield python objects (list or None).
                        # But explicit check is safer:
                        if tokens_list is not None and len(tokens_list) > 0:
                            # Filter None and convert to str (safety)
                            yield [str(t) for t in tokens_list if t is not None]
                        else:
                            yield [] # Yield empty list for fit() inputs
                else:
                    pass # Skip missing lags for Vocab building
        
        # Check if we have any text data at all
        has_text = any(f"news_lag{i}" in df.columns for i in range(1, self.lags + 1))
        
        X_text = None
        feature_names = []
        
        if has_text:
            print(f"  Fitting vectorizer (Generator Mode)... (min_df={self.vectorizer.min_df}, min_rel={self.min_relevance})")
            
            # MEMORY_OPT: Do NOT override min_df=1. Trust the class default (3) or user input.
            # self.vectorizer.min_df = 1  <-- REMOVED
            
            # Count non-empty for logging (approximate)
            # We can't count without consuming generator. Just proceed.
            
            try:
                self.vectorizer.fit(token_generator())
            except ValueError:
                print("  No tokens found in generator (empty corpus?). Proceeding with Dense only.")
                has_text = False

            if has_text:
                feature_names = list(self.vectorizer.get_feature_names_out())
                
                # Transform needs to be done column by column anyway to form Lags
                X_list = []
                for i in range(1, self.lags + 1):
                    col_name = f"news_lag{i}"
                    if col_name in df.columns:
                        # Transform allows Iterable too, but we need to keep row alignment for hstack!
                        # So we must yield exactly one document per row, even if empty.
                        # df[col].to_list() is materialized list of lists.
                        # vectorizer.transform takes list of lists (since tokenizer=identity).
                        # This part still uses memory corresponding to the dataframe column size.
                        # But we saved the "Massive List" copy in fit().
                        
                        # Optimization: Transform directly from Series iterator?
                        # transform(df[col]) might work if Polars Series is iterable? Yes.
                        # But entries are Lists. Vectorizer expects keys.
                        # Since we used tokenizer=lambda x:x, it expects iterables of tokens.
                        
                        # Handle Nulls for Transform (Must yield empty list, not skip)
                        # We use a helper generator for transform to ensure safety
                        def transform_gen(series):
                            for tokens in series:
                                if tokens is None:
                                    yield []
                                else:
                                    yield [str(t) for t in tokens]
                                    
                        X_lag = self.vectorizer.transform(transform_gen(df[col_name]))
                    else:
                        X_lag = self.vectorizer.transform([[]] * len(df))
                    X_list.append(X_lag)
                
                X_text = hstack(X_list).tocsr()
            
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
        
        # 3. Dense Features (Technical Indicators)
        X_tech_scaled = None
        if self.use_tech_indicators:
            tech_cols = ["tech_rsi_14", "tech_macd_line", "tech_macd_sig", "tech_macd_hist"]
            X_tech = df.select(tech_cols).to_numpy()
            
            # Use separate scaler or integrate with dense? 
            # Separate is better for traceability.
            tech_scaler = StandardScaler()
            X_tech_scaled = tech_scaler.fit_transform(X_tech)
            scaler_params["tech"] = {
                "mean": tech_scaler.mean_.tolist(),
                "scale": tech_scaler.scale_.tolist(),
                "cols": tech_cols
            }

        # 4. Combine Features (with TF-IDF normalization for Lasso fairness)
        text_scaler_params = {}
        
        # Accumulate all feature parts
        features_to_stack = []
        if X_text is not None:
            text_scaler = MaxAbsScaler()
            X_text_scaled = text_scaler.fit_transform(X_text)
            text_scaler_params = {"max_abs": text_scaler.max_abs_.tolist()}
            features_to_stack.append(X_text_scaled)
            
        if X_dense_scaled is not None:
            features_to_stack.append(X_dense_scaled)
            
        if X_tech_scaled is not None:
            features_to_stack.append(X_tech_scaled)
            
        if features_to_stack:
            X = hstack(features_to_stack).tocsr()
        else:
            raise ValueError("No features available for training")
        
        # Store scaler params for prediction
        scaler_params["text"] = text_scaler_params
            
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
              
         if self.use_tech_indicators:
              tech_feature_names = [f"__T_{c}__" for c in ["rsi_14", "macd_line", "macd_sig", "macd_hist"]]
              feature_names_raw.extend(tech_feature_names)
        
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
            
            # Apply Ordered Lasso Decay (Lag Penalty) (TASK-042 + Dynamic Enhancement)
            # Each feature name is "Word_L{k}"
            # Logic: Scale X by 1/p where p = 1.0 + decay_rate * (lag - 1)
            # This increases the effective L1 penalty for older news:
            # L1_eff = alpha / (1/p) = alpha * p
            
            # Dynamic decay rate calculation
            if self.decay_rate == 'auto':
                # Calculate optimal decay from data (correlation-based)
                decay_weights = self._calculate_dynamic_decay(df, self.lags)
            else:
                # Use fixed decay rate
                decay_weights = None
            
            for idx in range(text_dim):
                fname = text_feature_names[idx]
                try:
                    # Extract lag number from suffix _L1, _L2...
                    lag_str = fname.rsplit('_L', 1)[1]
                    lag_val = int(lag_str)
                except:
                    lag_val = 1
                
                if decay_weights is not None:
                    # Dynamic decay from data
                    decay = decay_weights.get(lag_val, 1.0 / lag_val)
                else:
                    # Original fixed decay rate
                    # Penalty factor increases with lag (p=1.0 for L1, p=1.4 for L2 if decay=0.4)
                    penalty_factor = 1.0 + self.decay_rate * (lag_val - 1)
                    decay = 1.0 / penalty_factor
                
                # We multiply X by decay (compressing it), which requires a 
                # stronger weight (beta) to have the same effect on 'y', 
                # but Lasso sees small values as easier to zero out.
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
        # celer solvers are much faster with CSC format
        X_weighted = X_filtered.tocsc().multiply(weights_filtered).tocsc()
        
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
            # We already have stock_code, no need to fetch name just to get aliases
            # get_stock_aliases will now prioritize stock_code lookups in the JSON map.
            # However, for safety and fallback (if JSON not ready), we still fetch the name.
            with get_db_cursor() as cur:
                cur.execute("SELECT stock_name FROM tb_stock_master WHERE stock_code = %s", (stock_code,))
                row = cur.fetchone()
                if row:
                    raw_name = row['stock_name']
                    if raw_name:
                        stock_names = get_stock_aliases(raw_name, stock_code)
        
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
            
            # Check Critical Word or Global Lexicon (Strip _L suffix)
            is_critical = False
            is_global_rescue = False
            if feature_names:
                fname = feature_names[i]
                base_word = fname.rsplit('_L', 1)[0]
                if base_word in CRITICAL_WORDS:
                    is_critical = True
                if base_word in GLOBAL_LEXICON_CACHE:
                    is_global_rescue = True

            if count >= min_df:
                keep_indices.append(i)
            elif count > 0 and (vol > avg_vol * 2.0 or is_critical or is_global_rescue): # Black Swan/Global Rescue
                keep_indices.append(i)
                if is_critical or is_global_rescue:
                     # Critical/Global words get a weight boost to ensure visibility if they are rare
                     weights[i] = max(weights[i], avg_vol * 2.0)
        
        # 가중치 정규화 (평균 1.0)
        if np.mean(weights) > 0:
            weights = weights / np.mean(weights)
        else:
            weights = np.ones_like(weights)
            
        return weights, keep_indices

    def _calculate_dynamic_decay(self, df, max_lag: int) -> dict:
        """
        동적 감쇠율 계산: 각 lag별로 뉴스 영향력과 수익률의 상관관계를 분석
        
        Args:
            df: 학습 데이터 (date, excess_return, tokens 포함)
            max_lag: 최대 lag (일)
            
        Returns:
            dict: {lag: decay_weight} 형태의 동적 가중치 (lag=1이 1.0)
        """
        try:
            import polars as pl
            
            # 기본 fallback: 1/sqrt(lag) decay (실험적으로 효과적)
            decay_weights = {lag: 1.0 / np.sqrt(lag) for lag in range(1, max_lag + 1)}
            
            # 데이터가 충분하면 상관관계 기반 계산 시도
            if len(df) > max_lag * 2:
                returns = df["excess_return"].to_numpy()
                
                # 각 lag별로 뉴스 영향력 측정 (토큰 수 기반)
                correlations = {}
                for lag in range(1, max_lag + 1):
                    # 간단한 상관관계: lag일 전 데이터와 오늘 수익률
                    if len(returns) > lag:
                        lagged_returns = returns[:-lag]
                        future_returns = returns[lag:]
                        
                        # 자기상관 계수를 decay 지표로 활용
                        # 높은 자기상관 = 과거 정보가 여전히 유효
                        if len(lagged_returns) > 0 and np.std(lagged_returns) > 0:
                            corr = np.abs(np.corrcoef(lagged_returns, future_returns)[0, 1])
                            if not np.isnan(corr):
                                correlations[lag] = max(corr, 0.01)  # 최소값 보장
                
                # 상관관계 기반 가중치 계산
                if correlations:
                    max_corr = max(correlations.values())
                    decay_weights = {k: v / max_corr for k, v in correlations.items()}
                    
                    # 로깅
                    import logging
                    logging.info(f"[Dynamic Decay] Calculated from data: {decay_weights}")
            
            # 캐싱
            self._dynamic_decay_weights = decay_weights
            return decay_weights
            
        except Exception as e:
            import logging
            logging.warning(f"[Dynamic Decay] Fallback to 1/sqrt(lag): {e}")
            return {lag: 1.0 / np.sqrt(lag) for lag in range(1, max_lag + 1)}

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

    def run_training(self, stock_code, start_date, end_date, version=None, source='Main', is_active=True, prefetched_df_news=None, alpha=None, lags=None):
        if alpha is not None:
            self.alpha = float(alpha)
            if hasattr(self.model, 'alpha'):
                self.model.alpha = float(alpha)
        
        if lags is not None:
            self.lags = int(lags)

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

    def extract_and_save_neutral_words(self, stock_code, threshold=1e-6, min_occurrences=3):
        """
        학습 완료 후 가중치가 0에 가까운 단어(중립 단어)를 추출하여 저장합니다.
        다음 학습 시 tokenizer에서 필터링하여 메모리를 절약합니다.
        
        Args:
            stock_code: 종목 코드
            threshold: 중립으로 간주할 절대 가중치 임계값
            min_occurrences: AWO 스캔에서 여러 윈도우에 걸쳐 중립인 경우만 저장 (미래 확장용)
        
        Returns:
            list: 중립 단어 목록
        """
        import os
        
        if not hasattr(self, 'model') or self.model.coef_ is None:
            print(f"[NeutralWords] Model not trained yet for {stock_code}")
            return []
        
        try:
            feature_names = self.vectorizer.get_feature_names_out()
            coefs = self.model.coef_
            
            # 가중치가 임계값 이하인 단어 추출 (Lag 접미사 제거)
            neutral_words = set()
            for name, coef in zip(feature_names, coefs):
                if abs(coef) < threshold:
                    # Remove lag suffix (e.g., "상승_L1" -> "상승")
                    base_name = name.rsplit('_L', 1)[0]
                    # Skip fundamental features
                    if not base_name.startswith("__F_"):
                        neutral_words.add(base_name)
            
            # 저장 경로
            output_dir = os.getenv("LEARNED_STOPWORDS_DIR", "/app/data")
            if not os.path.exists(output_dir):
                # Local fallback
                output_dir = os.path.join(os.path.dirname(__file__), "../../data")
            
            output_path = os.path.join(output_dir, f"learned_stopwords_{stock_code}.txt")
            
            # 기존 파일과 병합 (누적)
            existing = set()
            if os.path.exists(output_path):
                with open(output_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            existing.add(line)
            
            # 새 단어 추가
            all_neutral = existing.union(neutral_words)
            
            # 저장
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"# Learned Neutral Words for {stock_code}\n")
                f.write(f"# Auto-generated by AWO training\n")
                f.write(f"# Total: {len(all_neutral)} words\n\n")
                for word in sorted(all_neutral):
                    f.write(f"{word}\n")
            
            print(f"[NeutralWords] Saved {len(neutral_words)} new neutral words to {output_path} (Total: {len(all_neutral)})")
            return list(neutral_words)
            
        except Exception as e:
            print(f"[NeutralWords] Error extracting neutral words: {e}")
            return []
