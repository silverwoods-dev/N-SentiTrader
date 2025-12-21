"""
tests/test_validator_timeline.py

TASK-032: Validator 대시보드 Timeline View 백엔드 로직 테스트
"""

import pytest
from datetime import datetime, timedelta
from src.db.connection import get_db_cursor
from src.dashboard.app import get_latest_version_dict, get_timeline_dict


class TestLatestVersionDict:
    """최신 버전 감성 사전 조회 함수 테스트"""
    
    def test_get_latest_version_dict_removes_duplicates(self):
        """
        같은 단어가 여러 버전으로 존재할 때, 최신 버전만 반환하는지 검증
        """
        stock_code = '005930'
        source = 'Main'
        word = 'TEST_PUMP'
        
        with get_db_cursor() as cur:
            # 1. 테스트 데이터 삽입 (기존 데이터와 충돌 방지 위해 독특한 단어 사용)
            # 여러 버전을 시간차를 두고 삽입
            now = datetime.now()
            cur.execute("""
                INSERT INTO tb_sentiment_dict (stock_code, word, beta, version, source, updated_at)
                VALUES (%s, %s, 0.05, 'v1', %s, %s),
                       (%s, %s, 0.06, 'v2', %s, %s + interval '1 hour')
            """, (stock_code, word, source, now, stock_code, word, source, now))
            
            try:
                # 2. 최신 버전 조회 실행 (Positive)
                result = get_latest_version_dict(cur, stock_code, source, limit=10, positive=True)
                
                # 3. 검증
                pump_entries = [r for r in result if r['word'] == word]
                assert len(pump_entries) == 1, "중복 제거 실패: 같은 단어가 여러 번 반환됨"
                assert pump_entries[0]['version'] == 'v2', "최신 버전이 아님"
                assert pump_entries[0]['beta'] == 0.06
            finally:
                # 4. 테스트 데이터 삭제
                cur.execute("DELETE FROM tb_sentiment_dict WHERE word = %s", (word,))

    def test_get_latest_version_dict_sorting(self):
        """
        긍정/부정 단어 정렬 순서 검증
        """
        stock_code = '005930'
        with get_db_cursor() as cur:
            # 긍정: DESC (큰 값부터)
            pos_result = get_latest_version_dict(cur, stock_code, 'Main', limit=5, positive=True)
            if len(pos_result) >= 2:
                assert pos_result[0]['beta'] >= pos_result[1]['beta']
                
            # 부정: ASC (작은(더 음수인) 값부터)
            neg_result = get_latest_version_dict(cur, stock_code, 'Main', limit=5, positive=False)
            if len(neg_result) >= 2:
                assert neg_result[0]['beta'] <= neg_result[1]['beta']


class TestTimelineDict:
    """시계열 감성 사전 조회 함수 테스트"""
    
    def test_get_timeline_dict_filters_and_includes_all(self):
        """
        날짜 범위 필터링 및 모든 버전 포함 여부 검증
        """
        stock_code = '005930'
        word = 'TEST_TIMELINE'
        
        with get_db_cursor() as cur:
            now = datetime.now()
            # 30일 전과 오늘 데이터 삽입
            cur.execute("""
                INSERT INTO tb_sentiment_dict (stock_code, word, beta, version, source, updated_at)
                VALUES (%s, %s, 0.1, 'v1', 'Main', %s - interval '31 days'),
                       (%s, %s, 0.2, 'v2', 'Main', %s - interval '10 days'),
                       (%s, %s, 0.3, 'v3', 'Main', %s)
            """, (stock_code, word, now, stock_code, word, now, stock_code, word, now))
            
            try:
                # 최근 15일 범위로 조회
                start = now - timedelta(days=15)
                end = now + timedelta(days=1)
                result = get_timeline_dict(cur, stock_code, 'Main', start, end)
                
                words_in_range = [r for r in result if r['word'] == word]
                # v2, v3가 포함되어야 함 (v1은 제외)
                assert len(words_in_range) == 2
                versions = [r['version'] for r in words_in_range]
                assert 'v2' in versions
                assert 'v3' in versions
                assert 'v1' not in versions
            finally:
                cur.execute("DELETE FROM tb_sentiment_dict WHERE word = %s", (word,))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
