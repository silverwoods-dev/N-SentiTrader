import mecab_ko as MeCab
import os

class Tokenizer:
    def __init__(self, dic_path=None, user_dic_path=None):
        if not dic_path:
            # 기본 경로 (Docker 환경 고려)
            dic_path = os.getenv("MECAB_DIC_PATH", "/usr/lib/x86_64-linux-gnu/mecab/dic/mecab-ko-dic")
        
        if not user_dic_path:
            user_dic_path = os.getenv("MECAB_USER_DIC_PATH")
            
        if user_dic_path and os.path.exists(user_dic_path):
            self.tagger = MeCab.Tagger(f"-d {dic_path} -u {user_dic_path}")
        else:
            # 로컬 환경에서 dic_path가 없을 경우 기본 Tagger 사용
            try:
                self.tagger = MeCab.Tagger(f"-d {dic_path}")
            except Exception:
                self.tagger = MeCab.Tagger()

    def tokenize(self, text, n_gram=1):
        """
        텍스트를 토큰화하고 N-gram을 생성합니다.
        n_gram: 1이면 1-gram, 2이면 1~2-gram, 3이면 1~3-gram 반환
        """
        if not text:
            return []
            
        node = self.tagger.parseToNode(text)
        base_tokens = []
        while node:
            pos = node.feature.split(',')[0]
            # 명사(NNG, NNP), 외국어(SL) 추출
            if pos in ['NNG', 'NNP', 'SL']:
                if node.surface and len(node.surface) > 1: # None 체크 및 한 글자 제외
                    base_tokens.append(str(node.surface))
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
    test_text = "삼성전자가 반도체 실적 발표 이후 주가가 급등했습니다."
    print(f"1-gram: {tokenizer.tokenize(test_text, n_gram=1)}")
    print(f"2-gram: {tokenizer.tokenize(test_text, n_gram=2)}")
    print(f"3-gram: {tokenizer.tokenize(test_text, n_gram=3)}")
