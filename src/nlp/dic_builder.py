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
        self.data_dir = os.environ.get("NS_DATA_PATH", "data")
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
        
        # 후보 생성을 위한 공통 접미사 (MeCab이 못 쪼개는 경우 대비)
        common_suffixes = [
            "홀딩스", "생명", "화재", "SDI", "디스플레이", "전기", "중공업", "바이오", 
            "전자", "바이오로직스", "에너지솔루션", "금융지주", "텔레콤", "이노베이션",
            "건설", "증권", "은행", "자동차", "제약", "메디칼", "테크"
        ]

        # 1차 패스: 모든 가능한 토큰 후보들의 출현 빈도 수집
        for s in stocks:
            code = s['stock_code']
            name = s['stock_name']
            
            candidates = set()
            # A. MeCab 토큰
            tokens = self.tokenizer.tokenize(name, n_gram=1)
            candidates.update(tokens)
            # B. 공통 접미사 제거 시도
            for sx in common_suffixes:
                if name.endswith(sx) and len(name) > len(sx):
                    candidates.add(name.replace(sx, "").strip())
                    candidates.add(sx)
            # C. 공백 분리
            if " " in name:
                candidates.update(name.split())
            # D. 원본
            candidates.add(name)

            for t in candidates:
                if len(t) < 2: continue
                if t not in token_to_stocks:
                    token_to_stocks[t] = set()
                token_to_stocks[t].add(code)

        # 2차 패스: 빈도 기반 필터링 및 최종 별칭 할당
        stock_aliases = {}
        for s in stocks:
            code = s['stock_code']
            name = s['stock_name']
            
            candidates = set()
            tokens = self.tokenizer.tokenize(name, n_gram=1)
            candidates.update(tokens)
            for sx in common_suffixes:
                if name.endswith(sx) and len(name) > len(sx):
                    candidates.add(name.replace(sx, "").strip())
            if " " in name:
                candidates.update(name.split())
            candidates.add(name)
            
            final_aliases = set()
            for t in candidates:
                if len(t) < 2: continue
                
                # 이 토큰을 사용하는 종목의 수
                owner_count = len(token_to_stocks.get(t, []))
                
                # 임계값: 전체 종목의 일정 비율 이상 혹은 절대 수치 이상이면 Connector로 간주하여 제외
                # (예: 5개 이상의 종목에서 공통으로 쓰이면 별칭에서 제외하여 '전자' 등을 걸러냄)
                # 단, '삼성', 'SK' 등 그룹명은 필터링에서 빼고 싶거나 별도 관리가 필요할 수 있음
                # 우선 5개 이상이면 제외하는 보수적 접근
                if owner_count < 5:
                    final_aliases.add(t)
                    # 영어 변형
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
