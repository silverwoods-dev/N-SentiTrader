# src/dashboard/data_helpers.py
from datetime import datetime, timedelta
import json

def get_jobs_data(cur, limit=20):
    cur.execute("SELECT * FROM jobs ORDER BY started_at DESC LIMIT %s", (limit,))
    return cur.fetchall()

def get_stock_stats_data(cur, stock_code=None, q=None, status_filter=None):
    params = []
    where_clauses = []
    
    if stock_code:
        where_clauses.append("sm.stock_code = %s")
        params.append(stock_code)
    
    if q:
        where_clauses.append("(sm.stock_code LIKE %s OR sm.stock_name LIKE %s)")
        params.append(f"%{q}%")
        params.append(f"%{q}%")
        
    if status_filter:
        where_clauses.append("dt.status = %s")
        params.append(status_filter)
        
    where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    
    # Common CTE
    cte_query = """
        WITH daily_counts AS (
            SELECT 
                m.stock_code,
                u.published_at_hint as pdate,
                count(*) as cnt
            FROM tb_news_url u
            JOIN tb_news_mapping m ON u.url_hash = m.url_hash
            WHERE u.published_at_hint >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY m.stock_code, u.published_at_hint
        )
    """
    
    main_query = """
        SELECT 
            sm.stock_code, 
            sm.stock_name,
            dt.status as target_status,
            dt.auto_activate_daily,
            dt.started_at,
            MIN(COALESCE(nc.published_at::date, nu.published_at_hint)) as min_date,
            MAX(COALESCE(nc.published_at::date, nu.published_at_hint)) as max_date,
            COUNT(nu.url_hash) as url_count,
            COUNT(nc.url_hash) as body_count,
            (
                SELECT COALESCE(json_agg(json_build_object('date', dc.pdate, 'count', dc.cnt) ORDER BY dc.pdate), '[]'::json)
                FROM daily_counts dc
                WHERE dc.stock_code = sm.stock_code
            ) as sparkline_data
        FROM daily_targets dt
        INNER JOIN tb_stock_master sm ON dt.stock_code = sm.stock_code
        LEFT JOIN tb_news_mapping nm ON sm.stock_code = nm.stock_code
        LEFT JOIN tb_news_url nu ON nm.url_hash = nu.url_hash
        LEFT JOIN tb_news_content nc ON nu.url_hash = nc.url_hash
    """
    
    group_by = "GROUP BY sm.stock_code, sm.stock_name, dt.status, dt.auto_activate_daily, dt.started_at ORDER BY sm.stock_name"
    full_query = f"{cte_query} {main_query} {where_clause} {group_by}"
    
    cur.execute(full_query, tuple(params))
    return cur.fetchall()

def get_overall_stats(cur):
    cur.execute("SELECT status, count(*) as cnt FROM tb_news_url GROUP BY status")
    rows = cur.fetchall()
    return {row['status']: row['cnt'] for row in rows}

def get_chart_data(cur):
    cur.execute("""
        SELECT published_at_hint as date, COUNT(*) as cnt
        FROM tb_news_url
        WHERE published_at_hint >= CURRENT_DATE - INTERVAL '30 days'
        GROUP BY published_at_hint
        ORDER BY published_at_hint ASC
    """)
    rows = cur.fetchall()
    return {
        "labels": [r['date'].strftime('%m-%d') for r in rows if r['date']],
        "counts": [r['cnt'] for r in rows if r['date']]
    }

def get_validation_summary(cur, stock_code):
    cur.execute("""
        SELECT 
            COUNT(*) as total_days,
            SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct_days,
            AVG(ABS(actual_alpha)) as avg_alpha_magnitude,
            MIN(prediction_date) as start_date,
            MAX(prediction_date) as end_date
        FROM tb_predictions
        WHERE stock_code = %s AND actual_alpha IS NOT NULL
    """, (stock_code,))
    row = cur.fetchone()
    if row:
        return {
            "total_days": row["total_days"],
            "correct_days": row["correct_days"],
            "avg_alpha_magnitude": float(row["avg_alpha_magnitude"] or 0),
            "start_date": row["start_date"],
            "end_date": row["end_date"]
        }
    return None

def get_validation_history(cur, stock_code, limit=30):
    cur.execute("""
        SELECT * FROM tb_predictions
        WHERE stock_code = %s
        ORDER BY prediction_date DESC
        LIMIT %s
    """, (stock_code, limit))
    rows = cur.fetchall()
    for r in rows:
        if r['sentiment_score'] is not None: r['sentiment_score'] = float(r['sentiment_score'])
        if r['actual_alpha'] is not None: r['actual_alpha'] = float(r['actual_alpha'])
        if r.get('intensity') is not None: r['intensity'] = float(r['intensity'])
        if r.get('expected_alpha') is not None: r['expected_alpha'] = float(r['expected_alpha'])
        if r.get('confidence_score') is not None: r['confidence_score'] = float(r['confidence_score'])
    return rows

def get_performance_chart_data(cur, stock_code, limit=60):
    # 1. Fetch Production Predictions
    cur.execute("""
        SELECT DISTINCT ON (prediction_date::date)
            prediction_date::date as pred_date,
            sentiment_score,
            intensity,
            status,
            expected_alpha,
            actual_alpha,
            CASE WHEN actual_alpha IS NOT NULL THEN true ELSE false END as is_trading_day,
            created_at,
            'production' as source
        FROM tb_predictions
        WHERE stock_code = %s
        ORDER BY prediction_date::date DESC, created_at DESC
        LIMIT %s
    """, (stock_code, limit))
    prod_rows = cur.fetchall()
    
    # 2. Fetch Latest Verification Results (Optional, to fill gaps)
    # Only if prod_rows is small or specifically requested
    cur.execute("""
        SELECT v_job_id FROM tb_verification_jobs
        WHERE stock_code = %s AND status IN ('completed', 'running')
        ORDER BY started_at DESC LIMIT 1
    """, (stock_code,))
    job = cur.fetchone()
    
    ver_rows = []
    if job:
        cur.execute("""
            SELECT 
                target_date as pred_date,
                predicted_score as sentiment_score,
                ABS(predicted_score) * 1.2 as intensity, -- Approx
                'Backtest' as status,
                predicted_score as expected_alpha,
                actual_alpha,
                CASE WHEN actual_alpha IS NOT NULL THEN true ELSE false END as is_trading_day,
                CURRENT_TIMESTAMP as created_at,
                'verification' as source
            FROM tb_verification_results
            WHERE v_job_id = %s
            ORDER BY target_date DESC
            LIMIT %s
        """, (job['v_job_id'], limit))
        ver_rows = cur.fetchall()

    # Merge and deduplicate (Production wins)
    merged = {r['pred_date']: r for r in ver_rows}
    for r in prod_rows:
        merged[r['pred_date']] = r # Production overwrites verification for same date
        
    sorted_dates = sorted(merged.keys())[-limit:]
    
    result = []
    for d in sorted_dates:
        r = merged[d]
        
        # Calculate positive and negative scores
        # sentiment_score = pos + neg (net score)
        # intensity = |pos| + |neg|
        # Solve: pos + neg = sentiment_score, |pos| + |neg| = intensity
        
        sentiment_score = float(r["sentiment_score"]) if r["sentiment_score"] is not None else 0.0
        intensity = float(r.get("intensity")) if r.get("intensity") is not None else abs(sentiment_score) * 1.5
        
        # Approximate positive and negative scores
        # If sentiment_score > 0: pos is larger
        # If sentiment_score < 0: neg is larger (more negative)
        if sentiment_score >= 0:
            positive_score = (intensity + sentiment_score) / 2
            negative_score = (sentiment_score - intensity) / 2
        else:
            positive_score = (intensity + sentiment_score) / 2
            negative_score = (sentiment_score - intensity) / 2
        
        result.append({
            "date": d.isoformat(),
            "sentiment_score": sentiment_score,
            "positive_score": positive_score,
            "negative_score": negative_score,
            "intensity": intensity,
            "status": r.get("status") or ("N/A" if r['source'] == 'production' else "Verification"),
            "expected_alpha": float(r["expected_alpha"]) if r.get("expected_alpha") is not None else 0.0,
            "actual_alpha": float(r["actual_alpha"]) if r["actual_alpha"] is not None else None,
            "is_trading_day": r["is_trading_day"],
            "source": r["source"]
        })
    return result

def get_word_verification_data(cur, stock_code, word):
    """단어의 계수 안정성 및 백테스트 기반 정답률(Hit-Rate) 산출"""
    # 1. 계수 변동성 (베타 히스토리)
    cur.execute("""
        SELECT version, beta, updated_at
        FROM tb_sentiment_dict
        WHERE stock_code = %s AND word = %s
        ORDER BY updated_at ASC
    """, (stock_code, word))
    history = cur.fetchall()
    
    # 2. 백테스트 기반 정답률 (Hit-Rate)
    # 정규화된 단어 추출
    base_word = word.rsplit('_L', 1)[0] if '_L' in word else word
    lag = 1
    if '_L' in word:
        try:
            lag = int(word.rsplit('_L', 1)[1])
        except:
            lag = 1
            
    # 해당 단어가 등장한 빈도와 그에 따른 수익률 방향 일치 여부 확인
    cur.execute(f"""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN (p.excess_return > 0) THEN 1 ELSE 0 END) as pos_days,
            SUM(CASE WHEN (p.excess_return < 0) THEN 1 ELSE 0 END) as neg_days
        FROM tb_news_content c
        JOIN tb_news_mapping m ON c.url_hash = m.url_hash
        JOIN tb_daily_price p ON m.stock_code = p.stock_code 
            AND p.date = (c.published_at::date + (INTERVAL '1 day' * %s))::date
        WHERE m.stock_code = %s 
          AND (c.title ILIKE %s OR c.content ILIKE %s)
    """, (lag, stock_code, f"%{base_word}%", f"%{base_word}%"))
    
    stats = cur.fetchone()
    
    # 베타 방향과의 정합성 계산
    current_beta = float(history[-1]['beta']) if history else 0.0
    hit_count = 0
    if current_beta > 0:
        hit_count = stats['pos_days'] or 0
    elif current_beta < 0:
        hit_count = stats['neg_days'] or 0
        
    total = stats['total'] or 0
    hit_rate = (hit_count / total) if total > 0 else 0
    
    return {
        "word": word,
        "base_word": base_word,
        "current_beta": current_beta,
        "history": [
            {"version": h['version'], "beta": float(h['beta']), "date": h['updated_at'].strftime('%Y-%m-%d')} 
            for h in history
        ],
        "stats": {
            "total_occurrences": total,
            "hit_days": hit_count,
            "hit_rate": hit_rate,
            "pos_days": stats['pos_days'] or 0,
            "neg_days": stats['neg_days'] or 0
        }
    }

def get_senti_dict_pos_neg(cur, stock_code, source='Main', limit=10):
    cur.execute("""
        SELECT word, beta, version
        FROM tb_sentiment_dict
        WHERE stock_code = %s AND source = %s AND beta > 0
        ORDER BY beta DESC
        LIMIT %s
    """, (stock_code, source, limit))
    pos_rows = cur.fetchall()
    positive = [(r["word"], float(r["beta"]), r["version"]) for r in pos_rows]
    
    cur.execute("""
        SELECT word, beta, version
        FROM tb_sentiment_dict
        WHERE stock_code = %s AND source = %s AND beta < 0
        ORDER BY beta ASC
        LIMIT %s
    """, (stock_code, source, limit))
    neg_rows = cur.fetchall()
    negative = [(r["word"], float(r["beta"]), r["version"]) for r in neg_rows]
    return positive, negative

def get_latest_version_dict(cur, stock_code, source='Main', limit=10, positive=True):
    beta_condition = "d.beta > 0" if positive else "d.beta < 0"
    order_direction = "DESC" if positive else "ASC"
    cur.execute(f"""
        WITH latest_versions AS (
            SELECT word, MAX(updated_at) as max_date
            FROM tb_sentiment_dict
            WHERE stock_code = %s AND source = %s
            GROUP BY word
        )
        SELECT d.word, d.beta, d.version, d.updated_at
        FROM tb_sentiment_dict d
        INNER JOIN latest_versions lv 
            ON d.word = lv.word AND d.updated_at = lv.max_date
        WHERE d.stock_code = %s AND d.source = %s AND {beta_condition}
        ORDER BY d.beta {order_direction}
        LIMIT %s
    """, (stock_code, source, stock_code, source, limit))
    rows = cur.fetchall()
    return [
        {
            'word': r['word'],
            'beta': float(r['beta']),
            'version': r['version'],
            'updated_at': r['updated_at']
        }
        for r in rows
    ]

def get_timeline_dict(cur, stock_code, source='Main', start_date=None, end_date=None, limit_words=30):
    if start_date is None:
        start_date = datetime.now() - timedelta(days=30)
    if end_date is None:
        end_date = datetime.now()
        
    # Get top active words in this period by average magnitude
    cur.execute("""
        WITH active_words AS (
            SELECT word, AVG(ABS(beta)) as avg_beta
            FROM tb_sentiment_dict
            WHERE stock_code = %s AND source = %s
                AND updated_at BETWEEN %s AND %s
            GROUP BY word
            ORDER BY avg_beta DESC
            LIMIT %s
        )
        SELECT d.word, d.beta, d.version, d.updated_at
        FROM tb_sentiment_dict d
        JOIN active_words aw ON d.word = aw.word
        WHERE d.stock_code = %s AND d.source = %s
            AND d.updated_at BETWEEN %s AND %s
            AND d.updated_at IS NOT NULL
        ORDER BY d.updated_at ASC, d.word ASC
    """, (stock_code, source, start_date, end_date, limit_words, stock_code, source, start_date, end_date))
    rows = cur.fetchall()
    return [
        {
            'word': r['word'],
            'beta': float(r['beta']) if r['beta'] is not None else 0.0,
            'version': r['version'],
            'updated_at': r['updated_at']
        }
        for r in rows if r['updated_at']
    ]


def get_vanguard_derelict(cur, stock_code, source='Main', days=7):
    """Recently entered (Vanguard) or exited (Derelict) words"""
    cutoff = datetime.now() - timedelta(days=days)
    
    # Vanguard: Present in most recent version but NOT in version from [days] ago
    cur.execute("""
        WITH latest_v AS (
            SELECT version FROM tb_sentiment_dict 
            WHERE stock_code = %s AND source = %s ORDER BY updated_at DESC LIMIT 1
        ),
        old_v AS (
            SELECT version FROM tb_sentiment_dict 
            WHERE stock_code = %s AND source = %s AND updated_at < %s ORDER BY updated_at DESC LIMIT 1
        )
        SELECT word, beta, updated_at, 'vanguard' as type
        FROM tb_sentiment_dict 
        WHERE stock_code = %s AND source = %s 
          AND version IN (SELECT version FROM latest_v)
          AND word NOT IN (SELECT word FROM tb_sentiment_dict WHERE stock_code = %s AND source = %s AND version IN (SELECT version FROM old_v))
        UNION ALL
        SELECT word, beta, updated_at, 'derelict' as type
        FROM tb_sentiment_dict 
        WHERE stock_code = %s AND source = %s 
          AND version IN (SELECT version FROM old_v)
          AND word NOT IN (SELECT word FROM tb_sentiment_dict WHERE stock_code = %s AND source = %s AND version IN (SELECT version FROM latest_v))
    """, (stock_code, source, stock_code, source, cutoff, stock_code, source, stock_code, source, stock_code, source, stock_code, source))
    
    rows = cur.fetchall()
    return [
        {
            'word': r['word'],
            'beta': float(r['beta']),
            'updated_at': r['updated_at'],
            'type': r['type']
        }
        for r in rows
    ]

def get_collection_metrics(cur):
    """Fetch collection success rate and error count for the last 24h"""
    cutoff = datetime.now() - timedelta(hours=24)
    
    cur.execute("""
        SELECT status, count(*) as cnt 
        FROM tb_news_url 
        WHERE created_at >= %s
        GROUP BY status
    """, (cutoff,))
    success_rows = cur.fetchall()
    stats = {row['status']: row['cnt'] for row in success_rows}
    
    cur.execute("""
        SELECT count(*) as cnt 
        FROM tb_news_errors 
        WHERE occurred_at >= %s
    """, (cutoff,))
    error_count = cur.fetchone()['cnt']
    
    total = sum(stats.values())
    success_rate = (stats.get('completed', 0) / total * 100) if total > 0 else 100.0
    
    return {
        "success_rate": round(success_rate, 1),
        "total_24h": total,
        "errors_24h": error_count,
        "completed_24h": stats.get('completed', 0)
    }

def get_news_pulse_data(cur, stock_code, days=30):
    cutoff = datetime.now().date() - timedelta(days=days)
    cur.execute("""
        WITH daily_news AS (
            SELECT 
                COALESCE(nc.published_at::date, nu.published_at_hint) as pdate,
                nc.title,
                nc.url_hash
            FROM tb_news_mapping nm
            LEFT JOIN tb_news_url nu ON nm.url_hash = nu.url_hash
            LEFT JOIN tb_news_content nc ON nm.url_hash = nc.url_hash
            WHERE nm.stock_code = %s 
              AND COALESCE(nc.published_at::date, nu.published_at_hint) >= %s
        ),
        ranked_news AS (
            SELECT 
                pdate,
                title,
                ROW_NUMBER() OVER(PARTITION BY pdate ORDER BY LENGTH(title) DESC) as rnk
            FROM daily_news
            WHERE title IS NOT NULL
        )
        SELECT 
            pdate,
            COUNT(*) as count,
            (
                SELECT json_agg(title) 
                FROM (SELECT title FROM ranked_news rn WHERE rn.pdate = dn.pdate AND rn.rnk <= 3) t
            ) as top_headlines
        FROM daily_news dn
        GROUP BY pdate
        ORDER BY pdate ASC
    """, (stock_code, cutoff))
    
    rows = cur.fetchall()
    return [
        {
            "date": r['pdate'].isoformat(),
            "count": r['count'],
            "headlines": r['top_headlines'] or []
        }
        for r in rows if r['pdate']
    ]

def get_awo_landscape_data(cur, stock_code):
    cur.execute("""
        SELECT result_summary 
        FROM tb_verification_jobs 
        WHERE stock_code = %s AND v_type = 'AWO_SCAN' AND status = 'completed'
        ORDER BY completed_at DESC 
        LIMIT 1
    """, (stock_code,))
    row = cur.fetchone()
    if not row or not row['result_summary']:
        return None
        
    summary = row['result_summary']
    if isinstance(summary, str):
        summary = json.loads(summary)
        
    best_window = summary.get('best_window_months')
    scan_results = summary.get('scan_results', {})
    
    landscape = []
    for m in range(1, 12):
        res = scan_results.get(str(m)) or scan_results.get(m)
        if res:
            landscape.append({
                "window": int(m),
                "hit_rate": res.get('hit_rate', 0),
                "mae": res.get('mae', 0),
                "is_best": int(m) == best_window
            })
            
    return landscape
