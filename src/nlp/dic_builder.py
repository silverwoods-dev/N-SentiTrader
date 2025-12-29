import os
import re
import json
import subprocess
from collections import Counter
from src.db.connection import get_db_cursor
from src.nlp.tokenizer import Tokenizer

class DicBuilder:
    def __init__(self):
        self.tokenizer = Tokenizer()
        self.data_dir = os.environ.get("NS_DATA_PATH", "/app/data")
        self.user_dic_csv = os.path.join(self.data_dir, "user_dic.csv")
        self.alias_json = os.path.join(self.data_dir, "stock_aliases.json")

    def sync_all(self):
        """
        1. DB의 모든 종목명을 MeCab 사용자 사전에 동기화
        2. 전체 종목명 빈도 분석을 통한 별칭 맵 생성
        """
        with get_db_cursor() as cur:
            cur.execute("SELECT stock_code, stock_name FROM tb_stock_master")
            stocks = cur.fetchall()

        if not stocks:
            print("No stocks found in DB.")
            return

        self._update_mecab_user_dic(stocks)
        self._build_frequency_aliases(stocks)

    def _update_mecab_user_dic(self, stocks):
        """
        user_dic.csv 업데이트 및 컴파일 지시
        """
        # 기존 단어 로드 (중복 방지 및 기존 일반 단어 보존)
        existing_lines = []
        if os.path.exists(self.user_dic_csv):
            with open(self.user_dic_csv, 'r', encoding='utf-8') as f:
                existing_lines = f.readlines()
        
        # 기본 단어셋 (이미 구현되어 있던 경제 용어 등)
        # 종목명만 업데이트하기 위해 필터링하거나 새로 구성
        # 여기서는 종목명 전용 CSV를 따로 관리하거나 합침
        stock_entries = []
        for s in stocks:
            name = s['stock_name']
            # MeCab User Dic format: 단어,,,,품사,형태소,종성여부,읽기,타입,첫번째품사,마지막품사,표현
            # NNP(고유명사)로 등록
            stock_entries.append(f"{name},,,,NNP,*,T,{name},*,*,*,*\n")
            
            # 쪼개진 이름들도 명사로 등록 (예: 하이닉스)
            tokens = self.tokenizer.tokenize(name, n_gram=1)
            for t in tokens:
                if len(t) >= 2:
                    stock_entries.append(f"{t},,,,NNP,*,T,{t},*,*,*,*\n")

        # 합치기 및 중복 제거
        all_lines = list(set(existing_lines + stock_entries))
        all_lines.sort()

        os.makedirs(os.path.dirname(self.user_dic_csv), exist_ok=True)
        with open(self.user_dic_csv, 'w', encoding='utf-8') as f:
            f.writelines(all_lines)
        
        print(f"Updated MeCab user dictionary CSV: {self.user_dic_csv}")
        # Note: 실제 컴파일(.dic 생성)은 Docker 환경 내에서 mecab-dict-index 호출 필요
        # 런타임에 불가능할 경우 컨테이너 재시작 시점에 수행되도록 가이드

    def _build_frequency_aliases(self, stocks):
        """
        전체 종목명 토큰 빈도 분석 -> 고유 식별어 추출
        """
        token_to_stocks = {}
        all_tokens = []

        for s in stocks:
            code = s['stock_code']
            name = s['stock_name']
            
            # MeCab으로 쪼개기
            tokens = self.tokenizer.tokenize(name, n_gram=1)
            # 원본 추가
            tokens.append(name)
            if " " in name:
                tokens.extend(name.split())
            
            unique_tokens = set(t for t in tokens if len(t) >= 2)
            for t in unique_tokens:
                if t not in token_to_stocks:
                    token_to_stocks[t] = set()
                token_to_stocks[t].add(code)
                all_tokens.append(t)

        # 빈도 계산 (여러 종목에 걸쳐 나타나는 단어 찾기)
        # 예: '전자' -> {삼성전자, LG전자, ...} -> 빈도 높음 -> Connector
        # 예: '삼성' -> {삼성전자, 삼성카드, ...} -> 빈도 높음? (그룹사인 경우 예외 처리 고민)
        # 기본 전략: 3개 이상의 '다른' 종목에서 발견되면 Connector로 간주하여 별칭에서 제외
        
        stock_aliases = {}
        for s in stocks:
            code = s['stock_code']
            name = s['stock_name']
            
            # 후보 토큰들
            tokens = self.tokenizer.tokenize(name, n_gram=1)
            tokens.append(name)
            if " " in name:
                tokens.extend(name.split())
            
            final_aliases = set()
            for t in set(tokens):
                if len(t) < 2: continue
                
                # 이 토큰을 가진 종목 수
                owner_count = len(token_to_stocks.get(t, []))
                
                # 임계값 (예: 4개 이상의 종목에서 공통으로 쓰이면 별칭에서 탈락)
                if owner_count < 4:
                    final_aliases.add(t)
                    # 영어면 대소문자 변형 추가
                    if re.search(r'[a-zA-Z]', t):
                        eng = "".join(re.findall(r'[a-zA-Z]', t))
                        if len(eng) >= 2:
                            final_aliases.add(eng.lower())
                            final_aliases.add(eng.upper())
                            final_aliases.add(eng.capitalize())
            
            stock_aliases[code] = list(final_aliases)

        # JSON 저장
        with open(self.alias_json, 'w', encoding='utf-8') as f:
            json.dump(stock_aliases, f, ensure_ascii=False, indent=2)
            
        print(f"Built stock aliases map: {self.alias_json}")

if __name__ == "__main__":
    builder = DicBuilder()
    builder.sync_all()
