# src/learner/lasso.py
import polars as pl
from sklearn.linear_model import Lasso
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
        특정 기간의 주가 및 뉴스 데이터를 가져옵니다.
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
            
            # Fetch news (lags를 고려하여 시작일을 앞당김)
            news_start = (datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=self.lags + 2)).strftime('%Y-%m-%d')
            cur.execute("""
                SELECT c.published_at::date as date, c.content
                FROM tb_news_content c
                JOIN tb_news_mapping m ON c.url_hash = m.url_hash
                WHERE m.stock_code = %s AND c.published_at::date BETWEEN %s AND %s
            """, (stock_code, news_start, end_date))
            news = cur.fetchall()
            
        if not prices or not news:
            return None, None
            
        return pl.DataFrame(prices), pl.DataFrame(news)

    def prepare_features(self, df_prices, df_news):
        # 날짜별 뉴스 병합 및 미리 토큰화
        print(f"    Tokenizing {len(df_news)} news items...")
        
        # 각 뉴스별로 토큰화
        df_news = df_news.with_columns(
            pl.col("content").map_elements(
                lambda x: self.tokenizer.tokenize(x, n_gram=self.n_gram),
                return_dtype=pl.List(pl.String)
            ).alias("tokens")
        )
        
        # 날짜별로 토큰 리스트 합치기
        df_news_daily = df_news.group_by("date").agg(
            pl.col("tokens").flatten()
        )
        
        # 시차(Lag) 피처 생성
        df = df_prices.clone()
        for i in range(1, self.lags + 1):
            # p.date - i일의 뉴스를 가져옴
            df_lag = df_news_daily.select([
                (pl.col("date") + timedelta(days=i)).alias("date"),
                pl.col("tokens").alias(f"news_lag{i}")
            ])
            df = df.join(df_lag, on="date", how="left")
        
        # null 값은 빈 리스트로 채움
        for i in range(1, self.lags + 1):
            df = df.with_columns(
                pl.col(f"news_lag{i}").fill_null([])
            )
            
        # 뉴스가 하나도 없는 날은 제외
        df = df.filter(pl.any_horizontal(pl.col("^news_lag.*$").list.len() > 0))
        return df

    def train(self, df, stock_code=None):
        # 모든 시차의 토큰 리스트를 합쳐서 전체 어휘(Vocabulary) 학습
        all_token_lists = []
        for i in range(1, self.lags + 1):
            for lst in df[f"news_lag{i}"].to_list():
                if lst and len(lst) > 0:
                    clean_lst = [str(t) for t in lst if t is not None]
                    if clean_lst:
                        all_token_lists.append(clean_lst)
        
        if not all_token_lists:
            print("  No tokens found for training.")
            return {}
            
        # Black Swan 구제를 위해 일단 모든 단어를 포함 (min_df=1)
        print(f"  Fitting vectorizer on {len(all_token_lists)} non-empty token lists...")
        original_min_df = self.vectorizer.min_df
        self.vectorizer.min_df = 1 
        self.vectorizer.fit(all_token_lists)
        
        feature_names = self.vectorizer.get_feature_names_out()
        
        # 각 시차별로 DTM 생성
        X_list = []
        for i in range(1, self.lags + 1):
            X_lag = self.vectorizer.transform(df[f"news_lag{i}"].to_list())
            X_list.append(X_lag)
            
        X = hstack(X_list)
        y = df["excess_return"].cast(pl.Float64).to_numpy()
        
        # Volatility-weighted IDF 및 Black Swan 필터링
        weights, keep_indices = self.calculate_volatility_weights_with_filter(df, X, original_min_df)
        self.keep_indices = keep_indices # 예측 시 사용을 위해 저장
        
        # 선택된 피처만 유지
        X_filtered = X[:, keep_indices]
        weights_filtered = weights[keep_indices]
        
        # 가중치 적용
        X_weighted = X_filtered.multiply(weights_filtered)
        
        print(f"    [Train] Original Features: {X.shape[1]}, Filtered (Black Swan Rescued): {X_weighted.shape[1]}")
        self.model.fit(X_weighted, y)
        
        # 결과 저장용 사전 생성
        feature_names_raw = []
        for lag in range(1, self.lags + 1):
            feature_names_raw.extend([f"{name}_L{lag}" for name in feature_names])
        
        feature_names_filtered = [feature_names_raw[i] for i in keep_indices]
        
        sentiment_dict = {}
        stock_names = []
        if stock_code:
            with get_db_cursor() as cur:
                cur.execute("SELECT stock_name FROM tb_stock_master WHERE stock_code = %s", (stock_code,))
                row = cur.fetchone()
                if row:
                    name = row['stock_name']
                    stock_names = [name, name.replace("전자", "")]

        for name, coef in zip(feature_names_filtered, self.model.coef_):
            if coef != 0:
                base_name = name.rsplit('_L', 1)[0]
                if base_name in stock_names:
                    continue
                sentiment_dict[name] = float(coef)
                
        return sentiment_dict

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
        """
        X_list = []
        for i in range(1, self.lags + 1):
            X_lag = self.vectorizer.transform(df[f"news_lag{i}"].to_list())
            X_list.append(X_lag)
        
        X = hstack(X_list)
        
        # 학습 시 사용된 필터링 적용
        if self.keep_indices is not None:
            X = X[:, self.keep_indices]
            
        return self.model.predict(X)

    def run_training(self, stock_code, start_date, end_date, version=None, source='Main', is_active=True):
        df_prices, df_news = self.fetch_data(stock_code, start_date, end_date)
        if df_prices is None or len(df_prices) < 3:
            print(f"Insufficient data for {stock_code} in range {start_date}~{end_date}")
            return None
            
        df = self.prepare_features(df_prices, df_news)
        sentiment_dict = self.train(df, stock_code=stock_code)
        
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
            'metrics': {'word_count': len(sentiment_dict)},
            'is_active': is_active
        }
        
        if is_active:
            self.deactivate_all_versions(stock_code, source)

        self.save_dict(sentiment_dict, version, stock_code, source=source, meta=meta)
        print(f"Training completed for {stock_code}. {len(sentiment_dict)} words saved (version: {version}, active: {is_active}).")
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
            df_prices, df_news = self.fetch_data(stock_code, start_date, end_date)
            if df_prices is None or len(df_prices) < 10:
                continue
                
            df = self.prepare_features(df_prices, df_news)
            if len(df) < 5:
                continue
                
            # 간단한 시계열 교차 검증 (마지막 20%를 테스트로 사용)
            split_idx = int(len(df) * 0.8)
            df_train = df.head(split_idx)
            df_test = df.tail(len(df) - split_idx)
            
            try:
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
