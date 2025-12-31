import mecab_ko as MeCab
import os

class Tokenizer:
    def __init__(self, dic_path=None, user_dic_path=None, stopwords_path=None):
        if not dic_path:
            # 기본 경로 (Docker 환경 고려)
            dic_path = os.getenv("MECAB_DIC_PATH", "/usr/lib/x86_64-linux-gnu/mecab/dic/mecab-ko-dic")
        
        if not user_dic_path:
            user_dic_path = os.getenv("MECAB_USER_DIC_PATH")
        
        # Stopwords 로딩
        self.stopwords = self._load_stopwords(stopwords_path)
            
        if user_dic_path and os.path.exists(user_dic_path):
            self.tagger = MeCab.Tagger(f"-d {dic_path} -u {user_dic_path}")
        else:
            # 로컬 환경에서 dic_path가 없을 경우 기본 Tagger 사용
            try:
                self.tagger = MeCab.Tagger(f"-d {dic_path}")
            except Exception:
                self.tagger = MeCab.Tagger()
    
    def _load_stopwords(self, stopwords_path=None, stock_code=None):
        """불용어 목록 로드 (정적 + 동적 학습된 불용어)"""
        if not stopwords_path:
            # 기본 경로 (Docker: /app/data, Local: data/)
            stopwords_path = os.getenv("STOPWORDS_PATH", "/app/data/stopwords.txt")
            if not os.path.exists(stopwords_path):
                stopwords_path = os.path.join(os.path.dirname(__file__), "../../data/stopwords.txt")
        
        stopwords = set()
        
        # 1. 정적 불용어 로드
        if os.path.exists(stopwords_path):
            try:
                with open(stopwords_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            stopwords.add(line)
            except Exception as e:
                print(f"Warning: Could not load stopwords from {stopwords_path}: {e}")
        
        # 2. 동적 학습된 불용어 로드 (종목별)
        if stock_code:
            learned_path = os.path.join(os.path.dirname(stopwords_path), f"learned_stopwords_{stock_code}.txt")
            if os.path.exists(learned_path):
                try:
                    with open(learned_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                stopwords.add(line)
                    print(f"[Tokenizer] Loaded learned stopwords for {stock_code}")
                except Exception as e:
                    print(f"Warning: Could not load learned stopwords from {learned_path}: {e}")
        
        return stopwords
    
    def load_learned_stopwords(self, stock_code):
        """종목별 학습된 불용어를 동적으로 로드하여 기존 stopwords에 추가"""
        learned_path = os.getenv("LEARNED_STOPWORDS_DIR", "/app/data")
        if not os.path.exists(learned_path):
            learned_path = os.path.join(os.path.dirname(__file__), "../../data")
        
        learned_file = os.path.join(learned_path, f"learned_stopwords_{stock_code}.txt")
        if os.path.exists(learned_file):
            try:
                with open(learned_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            self.stopwords.add(line)
                print(f"[Tokenizer] Added {stock_code} learned stopwords (Total: {len(self.stopwords)})")
            except Exception as e:
                print(f"Warning: Could not load learned stopwords: {e}")

    def tokenize(self, text, n_gram=1):
        """
        텍스트를 토큰화하고 N-gram을 생성합니다.
        n_gram: 1이면 1-gram, 2이면 1~2-gram, 3이면 1~3-gram 반환
        
        필터링:
        1. POS 필터 (명사, 외래어, 숫자만)
        2. 불용어 필터 (stopwords.txt)
        3. 길이 필터 (1자 이하 제외)
        """
        if not text:
            return []
            
        node = self.tagger.parseToNode(text)
        base_tokens = []
        while node:
            pos = node.feature.split(',')[0]
            # 명사(NNG, NNP), 외국어(SL), 숫자(SN) 추출
            if pos in ['NNG', 'NNP', 'SL', 'SN']:
                token = node.surface
                if token and len(token) > 1:  # 1자 이하 제외
                    if token not in self.stopwords:  # 불용어 필터링
                        base_tokens.append(str(token))
            node = node.next
        
        if n_gram <= 1:
            return base_tokens
        
        result_tokens = list(base_tokens)
        for n in range(2, n_gram + 1):
            for i in range(len(base_tokens) - n + 1):
                ngram_token = ";".join(base_tokens[i:i+n]) # 공백 대신 세미콜론 등으로 구분 (Lasso 학습 시 편리)
                result_tokens.append(ngram_token)
        
        return result_tokens

if __name__ == "__main__":
    tokenizer = Tokenizer()
    print(f"Loaded {len(tokenizer.stopwords)} stopwords")
    test_text = "삼성전자가 반도체 실적 발표 이후 주가가 급등했습니다. 오늘 시장은 상승했다."
    print(f"1-gram: {tokenizer.tokenize(test_text, n_gram=1)}")
    print(f"2-gram: {tokenizer.tokenize(test_text, n_gram=2)}")

