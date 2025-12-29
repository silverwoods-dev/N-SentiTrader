import re
from src.db.connection import get_db_connection
from src.utils.stock_info import get_stock_aliases

class RelevanceScorer:
    def __init__(self):
        self.competitor_map = {}
        self._load_competitors()

    def _load_competitors(self):
        """
        Load all stock names to identify competitors/other entities.
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT stock_code, stock_name FROM tb_stock_master WHERE is_active = TRUE")
                    rows = cur.fetchall()
                    # Map name to code (or just keep set of names)
                    # Normalize names for matching
                    self.competitor_map = {row[1].replace(" ", ""): row[0] for row in rows}
                    self.competitor_map_raw = {row[1]: row[0] for row in rows}
                    self.code_to_name = {row[0]: row[1] for row in rows}
        except Exception as e:
            print(f"[!] Failed to load competitor map: {e}")

    def get_stock_name(self, stock_code):
        return self.code_to_name.get(stock_code)

    def calculate_score(self, content, title, target_stock_name, target_stock_code=None):
        """
        Calculate Target Focus Score (0-100).
        """
        if not content:
            return 0, False
        
        score = 0
        content_norm = content.replace(" ", "")
        title_norm = title.replace(" ", "") if title else ""
        target_norm = target_stock_name.replace(" ", "")
        
        # Get aliases for better recognition (e.g. SK, Hynix)
        aliases = get_stock_aliases(target_stock_name, target_stock_code)
        aliases_norm = {a.replace(" ", "") for a in aliases}
        aliases_norm.add(target_norm)
        
        # 1. Position Bias
        # Title (Check if ANY alias is in title)
        in_title = any(a in title_norm for a in aliases_norm)
        if in_title:
            score += 50
        
        # First Paragraph (Check if ANY alias is in first 200 chars)
        in_first_para = any(a in content_norm[:200] for a in aliases_norm)
        if in_first_para:
            score += 20
            
        # 2. Keyword Frequency
        # Use the most frequent alias as the representative count
        target_count = max([content_norm.count(a) for a in aliases_norm] + [0])
        
        if target_count > 0:
            score += min(target_count * 5, 20) # Max 20 points from frequency
        else:
            # If not in title AND not in content, it's very irrelevant
            if score == 0:
                return 0, False

        # 3. Competitor Ratio
        # Count other stocks
        competitor_counts = 0
        primary_competitor = None
        max_comp_count = 0
        
        for name, code in self.competitor_map.items():
            if name == target_norm:
                continue
            
            c_count = content_norm.count(name)
            if c_count > 0:
                competitor_counts += c_count
                if c_count > max_comp_count:
                    max_comp_count = c_count
                    primary_competitor = name

        # Penalize if a competitor is mentioned MORE than the target
        if max_comp_count > target_count:
            # Heavy penalty: It's likely about the competitor
            penalty = 30
            # If target is in title, we are more lenient
            if target_norm in title_norm:
                penalty = 10
            
            score -= penalty
            if score < 0: score = 0
            
        # 4. Threshold Check (Default 30)
        # If mentioned in Title (50) -> Pass
        # If mentioned in First Para (20) + 2 times (10) = 30 -> Pass
        # If mentioned only deeply (0) + 5 times (20) = 20 -> Fail (Low relevance)
        
        is_relevant = score >= 30
        
        return score, is_relevant
