# tests/test_advanced_logic.py
import unittest
from src.learner.lasso import LassoLearner
from src.predictor.scoring import Predictor
from src.db.connection import get_db_cursor
from datetime import datetime, timedelta

class TestAdvancedLogic(unittest.TestCase):
    def setUp(self):
        self.stock_code = "005930" # 삼성전자
        self.learner = LassoLearner(alpha=0.0001, n_gram=3, lags=5, min_df=1)
        self.predictor = Predictor()

    def test_db_schema(self):
        """tb_sentiment_dict에 stock_code 컬럼이 있는지 확인"""
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'tb_sentiment_dict' AND column_name = 'stock_code'
            """)
            self.assertIsNotNone(cur.fetchone())

    def test_entity_masking(self):
        """학습 결과에서 종목명 단독 토큰이 제외되는지 확인"""
        # 임의의 데이터 생성 (삼성전자 단어가 포함된 뉴스)
        import polars as pl
        df_prices = pl.DataFrame({
            "date": [datetime.now().date()],
            "excess_return": [0.01]
        })
        df_news = pl.DataFrame({
            "date": [datetime.now().date() - timedelta(days=1)],
            "content": ["삼성전자 실적 발표 삼성전자;실적 호조"]
        })
        
        df = self.learner.prepare_features(df_prices, df_news)
        sentiment_dict = self.learner.train(df, stock_code=self.stock_code)
        
        # '삼성전자_L1'은 제외되어야 함
        self.assertNotIn("삼성전자_L1", sentiment_dict)
        # '삼성전자;실적_L1'은 유지되어야 함 (N-gram)
        # Note: min_df=1 이므로 데이터가 적어도 포함될 수 있음
        # 하지만 실제 학습에서는 다른 단어들이 선택될 수 있으므로 
        # train 로직 내부에서 stop_indices가 제대로 작동하는지 확인하는 것이 더 정확함
        
    def test_stock_specific_dict_save_load(self):
        """종목별로 사전이 저장되고 로드되는지 확인"""
        version = "test_v1"
        test_dict = {"test_word_L1": 0.5}
        self.learner.save_dict(test_dict, version, self.stock_code)
        
        # 로드 확인
        loaded_dict = self.predictor.load_dict(version, self.stock_code)
        self.assertIn("test_word_L1", loaded_dict)
        self.assertEqual(loaded_dict["test_word_L1"], 0.5)
        
        # 다른 종목 코드로 로드 시 비어있어야 함
        other_dict = self.predictor.load_dict(version, "000660")
        self.assertEqual(len(other_dict), 0)

if __name__ == "__main__":
    unittest.main()
