import logging
from src.nlp.summarizer import NewsSummarizer

def test_summary():
    logging.basicConfig(level=logging.INFO)
    summarizer = NewsSummarizer()
    
    text = """
    현대자동차가 4분기 사상 최대 실적을 달성했습니다. 북미 시장에서의 SUV 판매 호조와 원화 약세 효과가 맞물린 결과입니다.
    영업이익은 전년 동기 대비 30% 증가한 3조원을 기록했습니다. 이는 시장 예상치를 크게 웃도는 수준입니다.
    배당 성향도 상향 조정하여 주주 환원을 강화하기로 했습니다. 주가는 발표 직후 5%대 강세를 보이고 있습니다.
    글로벌 경기 침체 우려에도 불구하고 고부가가치 차량 중심의 판매 전략이 주효했다는 분석입니다.
    """
    
    print("\n[Original Text]")
    print(text.strip())
    
    summary = summarizer.summarize(text, top_k=2)
    print("\n[Summary (top_k=2)]")
    print(summary)

if __name__ == "__main__":
    test_summary()
