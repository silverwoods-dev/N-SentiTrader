import logging
import re
from typing import List
import numpy as np
from src.learner.finbert_embedder import FinBERTEmbedder

logger = logging.getLogger(__name__)

class NewsSummarizer:
    """
    Existing FinBERTEmbedder를 활용한 한국어 뉴스 추출 요약기
    """
    
    def __init__(self, model_path: str = "snunlp/KR-FinBert", use_mlx: bool = True):
        self.embedder = FinBERTEmbedder(model_path=model_path, use_mlx=use_mlx)

    def split_sentences(self, text: str) -> List[str]:
        """한국어 문장 분리 (정교화)"""
        if not text: return []
        # 뉴스 기사 특유의 (서울=연합뉴스) OOO 기자, [사진] 등 노이즈 제거 시도
        text = re.sub(r'\([가-힣]+=연합뉴스\)|\[[가-힣\s]+\]', '', text)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if len(s.strip()) > 5]

    def split_paragraphs(self, text: str) -> List[str]:
        """
        본문 문자열만 있는 경우 문단을 나누는 로직
        1. 더블 개행(\n\n) 우선
        2. 긴 문장들의 묶음 (보통 3~4문장) 단위로 강제 분할 시도
        """
        if not text: return []
        # 더블 개행이 있다면 문단이 구분된 것으로 간주
        if "\n\n" in text:
            return [p.strip() for p in text.split("\n\n") if len(p.strip()) > 20]
        
        # 개행이 없는 장문의 경우, 마침표 3~4개 단위로 그룹핑하여 의사(Pseudo) 문단 생성
        sentences = self.split_sentences(text)
        if len(sentences) <= 4:
            return [text]
            
        paragraphs = []
        for i in range(0, len(sentences), 3):
            paragraphs.append(" ".join(sentences[i:i+3]))
        return paragraphs

    def summarize(self, text: str, top_k: int = 3) -> str:
        """
        BERT 임베딩 기반 추출 요약 (2단계 접근)
        1. 문단별 핵심 문장 추출 (Local Importance)
        2. 전체 문서 맥락에서의 중요도 산출 (Global Importance)
        """
        if not text or len(text) < 150:
            return text
            
        paragraphs = self.split_paragraphs(text)
        all_sentences = []
        
        # 1단계: 문단 분석
        for p in paragraphs:
            sents = self.split_sentences(p)
            all_sentences.extend(sents)
            
        if len(all_sentences) <= top_k:
            return text
            
        try:
            import time
            start_t = time.time()
            
            # 2단계: Global Importance
            embeddings = self.embedder.encode(all_sentences)
            doc_center = np.mean(embeddings, axis=0)
            
            # Cosine Similarity with doc center
            norm_emb = embeddings / (np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-9)
            norm_center = doc_center / (np.linalg.norm(doc_center) + 1e-9)
            similarities = np.dot(norm_emb, norm_center)
            
            # 상위 K개 선정 (원문 순서 유지)
            top_indices = np.argsort(similarities)[-top_k:]
            sorted_indices = sorted(top_indices.tolist())
            
            duration = (time.time() - start_t) * 1000
            logger.debug(f"Summarized in {duration:.1f}ms (CPU/GPU={self.embedder.use_mlx})")
            
            summary_sentences = [all_sentences[i] for i in sorted_indices]
            return " ".join(summary_sentences)
            
        except Exception as e:
            logger.error(f"Summarization error: {e}")
            return " ".join(all_sentences[:top_k])
    _singleton_instance = None
    
    @classmethod
    def bulk_ensure_summaries(cls, news_rows: List[dict]):
        """
        extracted_content 가 없는 뉴스들에 대해 일괄 요약을 수행하고 news_rows 와 DB를 업데이트함.
        """
        missing = [r for r in news_rows if not r.get('extracted_content') and r.get('content') and r.get('url_hash')]
        if not missing:
            return
            
        logger.info(f"[*] Bulk extraction for {len(missing)} news items...")
        
        if cls._singleton_instance is None:
            # CPU context for safety in workers/docker
            cls._singleton_instance = NewsSummarizer(use_mlx=False)
        
        summarizer = cls._singleton_instance
        
        from src.db.connection import get_db_cursor
        with get_db_cursor() as cur:
            for r in missing:
                try:
                    summary = summarizer.summarize(r['content'])
                    r['extracted_content'] = summary
                    cur.execute(
                        "UPDATE tb_news_content SET extracted_content = %s WHERE url_hash = %s",
                        (summary, r['url_hash'])
                    )
                except Exception as e:
                    logger.error(f"Bulk summarization failed for {r.get('url_hash', 'unknown')}: {e}")

if __name__ == "__main__":
    s = NewsSummarizer(use_mlx=False)
    test = "삼성전자가 갤럭시 S25를 공개했습니다. 이번 모델은 AI 성능이 대폭 강화되었습니다. 주가는 보합세를 유지하고 있습니다. 소비자들은 디자인에 만족하고 있습니다."
    print(s.summarize(test, top_k=2))
