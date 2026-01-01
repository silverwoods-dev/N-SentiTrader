from datetime import datetime, timedelta
import json
import numpy as np
from src.utils import calendar_helper

def get_jobs_data(cur, limit=20):
    cur.execute("SELECT *, message FROM jobs ORDER BY created_at DESC LIMIT %s", (limit,))
    rows = cur.fetchall()
    
    results = []
    for row in rows:
        r = dict(row)
        params = r.get('params')
        if isinstance(params, str):
            try:
                params = json.loads(params)
            except:
                params = {}
        elif not isinstance(params, dict):
            params = {}
            
        range_str = "-"
        
        if r['job_type'] == 'backfill':
            try:
                days = int(params.get('days', 0))
                offset = int(params.get('offset', 0))
                
                end_date = datetime.now() - timedelta(days=offset)
                start_date = end_date - timedelta(days=max(1, days)-1)
                
                if days <= 1:
                     range_str = end_date.strftime('%Y-%m-%d')
                else:
                     range_str = f"{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}"
            except:
                range_str = "Unknown Range"
                 
        elif r['job_type'] == 'daily':
             # Daily jobs typically run for "today" relative to execution
             # Rough approximation using created_at if params doesn't specify
             range_str = r['created_at'].strftime('%Y-%m-%d')
             
        r['date_range'] = range_str
        results.append(r)
        
    return results

def get_stock_stats_data(cur, stock_code=None, q=None, status_filter=None, limit=50):
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
    
    # Optimized: Use pre-calculated or simpler stats if possible.
    # For now, let's at least avoid the massive join for every row if we can.
    
    # Improved Sparkline: Use a more efficient way to get last 14 days counts
    full_query = f"""
        WITH recent_counts AS (
            SELECT 
                nm.stock_code,
                nu.published_at_hint as pdate,
                COUNT(*) as cnt
            FROM tb_news_mapping nm
            JOIN tb_news_url nu ON nm.url_hash = nu.url_hash
            WHERE nu.published_at_hint >= CURRENT_DATE - INTERVAL '14 days'
            GROUP BY nm.stock_code, nu.published_at_hint
        ),
        sparklines AS (
            SELECT 
                stock_code,
                json_agg(json_build_object('date', pdate, 'count', cnt) ORDER BY pdate) as data
            FROM recent_counts
            GROUP BY stock_code
        ),
        total_counts AS (
            SELECT 
                nm.stock_code, 
                COUNT(*) as total,
                MIN(nu.published_at_hint) as min_date,
                MAX(nu.published_at_hint) as max_date
            FROM tb_news_mapping nm
            JOIN tb_news_url nu ON nm.url_hash = nu.url_hash
            GROUP BY nm.stock_code
        ),
        daily_presence AS (
            SELECT DISTINCT nm.stock_code, nu.published_at_hint
            FROM tb_news_mapping nm
            JOIN tb_news_url nu ON nm.url_hash = nu.url_hash
        ),
        gaps AS (
            SELECT 
                tc.stock_code,
                COUNT(*) as missing_days
            FROM total_counts tc
            CROSS JOIN LATERAL generate_series(tc.min_date, tc.max_date, '1 day'::interval) gs(d)
            LEFT JOIN daily_presence dp ON tc.stock_code = dp.stock_code AND gs.d::date = dp.published_at_hint
            WHERE dp.published_at_hint IS NULL
            GROUP BY tc.stock_code
        )
        SELECT 
            sm.stock_code, 
            sm.stock_name,
            dt.status as target_status,
            dt.auto_activate_daily,
            dt.started_at,
            tc.min_date, 
            tc.max_date,
            COALESCE(tc.total, 0) as url_count,
            0 as body_count,
            COALESCE(sl.data, '[]'::json) as sparkline_data,
            COALESCE(g.missing_days, 0) as missing_days,
            dt.optimal_window_months,
            dt.optimal_alpha
        FROM daily_targets dt
        INNER JOIN tb_stock_master sm ON dt.stock_code = sm.stock_code
        LEFT JOIN sparklines sl ON sm.stock_code = sl.stock_code
        LEFT JOIN total_counts tc ON sm.stock_code = tc.stock_code
        LEFT JOIN gaps g ON sm.stock_code = g.stock_code
        {where_clause}
        ORDER BY sm.stock_name
        LIMIT %s
    """
    params.append(limit)
    
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
        SELECT DISTINCT ON (p.prediction_date::date)
            p.prediction_date::date as pred_date,
            p.sentiment_score,
            p.intensity,
            p.status,
            p.expected_alpha,
            p.actual_alpha,
            dp.sector_return,
            (dp.return_rate - COALESCE(dp.sector_return, 0)) as pure_alpha,
            CASE WHEN p.actual_alpha IS NOT NULL THEN true ELSE false END as is_trading_day,
            p.created_at,
            'production' as source
        FROM tb_predictions p
        LEFT JOIN tb_daily_price dp ON p.stock_code = dp.stock_code AND p.prediction_date = dp.date
        WHERE p.stock_code = %s
        ORDER BY p.prediction_date::date DESC, p.created_at DESC
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
            "pure_alpha": float(r.get("pure_alpha")) if r.get("pure_alpha") is not None else None,
            "sector_return": float(r.get("sector_return")) if r.get("sector_return") is not None else 0.0,
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

def get_active_workers_list(cur):
    """Fetch list of currently active workers and their tasks"""
    # 1. Verification Jobs
    cur.execute("""
        SELECT worker_id, 'Verification' as type, stock_code, status, updated_at
        FROM tb_verification_jobs 
        WHERE status = 'running' AND worker_id IS NOT NULL
    """)
    v_rows = cur.fetchall()
    
    # 2. Collection Jobs (jobs table needs worker_id too ideally, assuming it has it or we focus on verification for now)
    # Check if jobs table has worker_id
    try:
        cur.execute("""
            SELECT worker_id, job_type as type, 'N/A' as stock_code, status, updated_at 
            FROM jobs 
            WHERE status = 'running' AND worker_id IS NOT NULL
        """)
        j_rows = cur.fetchall()
    except Exception:
        j_rows = []
        
    workers = []
    seen_workers = set()
    
    all_rows = v_rows + j_rows
    for r in all_rows:
        w_id = r['worker_id']
        workers.append({
            "worker_id": w_id,
            "type": r['type'],
            "task": r['stock_code'] if r['type'] == 'Verification' else r['type'],
            "last_heartbeat": r['updated_at']
        })
        
    return workers

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

def get_awo_landscape_data(cur, stock_code, v_job_id=None):
    if v_job_id:
        cur.execute("""
            SELECT result_summary 
            FROM tb_verification_jobs 
            WHERE v_job_id = %s
        """, (v_job_id,))
    else:
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
        
    # Check if 2D result (has 'all_scores') or legacy 1D
    all_scores = summary.get('all_scores')
    
    landscape = []
    
    if all_scores:
        # 2D Format: key="6m_0.0001", value={hit_rate, stability_score...}
        best_stability = summary.get('best_stability_score', -999)
        best_config = (summary.get('best_window'), summary.get('best_alpha'))
        
        for key, res in all_scores.items():
            try:
                # Parse Key "6m_0.0001" -> 6, 0.0001
                parts = key.split('_')
                window = int(parts[0].replace('m', ''))
                alpha = float(parts[1])
                
                landscape.append({
                    "window": window,
                    "alpha": alpha,
                    "hit_rate": res.get('hit_rate', 0),
                    "mae": res.get('mae', 0),
                    "stability_score": res.get('stability_score', 0),
                    "is_best": (window == best_config[0] and alpha == best_config[1])
                })
            except:
                continue
                
        # Sort for Heatmap rendering (X: Window, Y: Alpha)
        landscape.sort(key=lambda x: (x['window'], x['alpha']))
        
    else:
        # Legacy 1D Fallback
        best_window = summary.get('best_window_months')
        scan_results = summary.get('scan_results', {})
        for m in range(1, 12):
            res = scan_results.get(str(m)) or scan_results.get(m)
            if res:
                landscape.append({
                    "window": int(m),
                    "alpha": 0.0, # Dummy for 1D
                    "hit_rate": res.get('hit_rate', 0),
                    "mae": res.get('mae', 0),
                    "stability_score": res.get('hit_rate', 0), # Use HitRate as proxy
                    "is_best": int(m) == best_window
                })
            
    return landscape

def get_equity_curve_data(cur, stock_code, v_job_id=None):
    """Calculate cumulative returns for Strategy vs Benchmark"""
    
    if v_job_id:
        # Backtest Mode: Read from tb_verification_results
        cur.execute("""
            SELECT 
                vr.target_date as prediction_date, 
                vr.predicted_score as strategy_signal,
                dp.return_rate,
                COALESCE(dp.sector_return, 0) as sector_return
            FROM tb_verification_results vr
            JOIN tb_daily_price dp ON dp.stock_code = %s AND vr.target_date = dp.date
            WHERE vr.v_job_id = %s
            ORDER BY vr.target_date ASC
        """, (stock_code, v_job_id))
    else:
        # Production Mode: Read from tb_predictions
        cur.execute("""
            SELECT 
                p.prediction_date, 
                p.expected_alpha as strategy_signal,
                dp.return_rate,
                COALESCE(dp.sector_return, 0) as sector_return
            FROM tb_predictions p
            JOIN tb_daily_price dp ON p.stock_code = dp.stock_code AND p.prediction_date = dp.date
            WHERE p.stock_code = %s
            ORDER BY p.prediction_date ASC
        """, (stock_code,))
    
    rows = cur.fetchall()
    
    dates = []
    cum_bench = [100.0] # Start at 100
    cum_strat = [100.0]
    
    curr_bench = 100.0
    curr_strat = 100.0
    
    for r in rows:
        ret = float(r['return_rate'])
        
        # Benchmark: Simple Buy & Hold
        curr_bench = curr_bench * (1 + ret)
        
        # Strategy: Directional Exposure
        # If signal > 0: Long, < 0: Short/Cash? 
        # For simple comparison, assume Long/Cash (if < 0, return 0) or Long/Short.
        # Let's assume Long/Short for full alpha demonstration or Long/Cash for conservative.
        # Given "Cautious Sell", let's assume Cash (0 return) for negatives to be safe.
        # Or if "Strong Sell", Short?
        # Let's use simple logic: Signal Sign * Return (Long/Short)
        sig = float(r['strategy_signal'] or 0)
        
        if sig > 0:
            strat_ret = ret
        elif sig < 0:
            strat_ret = -ret # Short
        else:
            strat_ret = 0 # Cash
            
        # Friction/Slippage could be added here (-0.002)
        curr_strat = curr_strat * (1 + strat_ret)
        
        dates.append(r['prediction_date'].strftime('%Y-%m-%d'))
        cum_bench.append(round(curr_bench, 2))
        cum_strat.append(round(curr_strat, 2))
        
    return {
        "dates": dates,
        "benchmark": cum_bench[1:], # Align with dates
        "strategy": cum_strat[1:]
    }

def get_feature_decay_analysis(cur, stock_code):
    """Analyze Feature Coefficients (L1 vs L5) for stability check"""
    # Get latest dictionary
    cur.execute("""
        SELECT word, beta 
        FROM tb_sentiment_dict 
        WHERE stock_code = %s 
          AND version = (SELECT version FROM tb_sentiment_dict_meta WHERE stock_code=%s AND is_active=TRUE ORDER BY created_at DESC LIMIT 1)
        ORDER BY ABS(beta) DESC
        LIMIT 100
    """, (stock_code, stock_code))
    
    rows = cur.fetchall()
    
    # Group by base word (e.g., '매출_L1', '매출_L5' -> '매출')
    grouped = {}
    for r in rows:
        word = r['word']
        beta = float(r['beta'])
        
        if '_L' in word:
            base, lag_str = word.rsplit('_L', 1)
            try:
                lag = int(lag_str)
            except:
                lag = 1
        else:
            base = word
            lag = 1
            
        if base not in grouped:
            grouped[base] = []
        grouped[base].append({'lag': lag, 'beta': beta})
        
    analysis = []
    for base, lags in grouped.items():
        if len(lags) > 1: # Only interesting if multiple lags exist
            lags.sort(key=lambda x: x['lag'])
            analysis.append({
                "word": base,
                "lags": [l['lag'] for l in lags],
                "betas": [l['beta'] for l in lags],
                "decay_check": abs(lags[0]['beta']) > abs(lags[-1]['beta']) if lags[-1]['lag'] > lags[0]['lag'] else True
            })
            
    # Sort by primary beta magnitude
    analysis.sort(key=lambda x: abs(x['betas'][0]), reverse=True)
    return analysis[:20]

def get_available_model_versions(cur, stock_code):
    """Fetch completed AWO jobs for version selection"""
    cur.execute("""
        SELECT v_job_id, completed_at, params, result_summary
        FROM tb_verification_jobs
        WHERE stock_code = %s AND status = 'completed' AND completed_at IS NOT NULL
        ORDER BY completed_at DESC
        LIMIT 20
    """, (stock_code,))
    rows = cur.fetchall()
    
    versions = []
    for r in rows:
        summary = r['result_summary']
        if isinstance(summary, str):
            try:
                summary = json.loads(summary)
            except:
                summary = {}
        
        if summary is None:
            summary = {}
            
        # Extract metadata for display
        hit_rate = summary.get('final_hit_rate') or summary.get('hit_rate')
        
        # If 2D scan, key might be deeper
        if hit_rate is None and summary.get('all_scores'):
             # Try to find best score (just a proxy for display)
             best_score_data = summary.get('best_stability_score')
             # Note: best_stability_score might be a number OR a dict? 
             # In my dummy data I didn't verify structure deeply, but usually it's a number.
             # Let's trust 'hit_rate' is more standard.
             hit_rate = 0.0 # Default if unknown
             
        if hit_rate is None:
            hit_rate = 0.0
             
        # Extract Range from Params or Summary
        train_days = "?"
        if r['params']:
            p = r['params'] if isinstance(r['params'], dict) else json.loads(r['params'])
            train_days = p.get('train_months', '?')
            
        versions.append({
            "v_job_id": r['v_job_id'],
            "label": f"Backtest #{r['v_job_id']} - {r['completed_at'].strftime('%Y-%m-%d %H:%M')}",
            "meta": f"Hit Rate: {float(hit_rate)*100:.1f}% | Win: {train_days}m" 
        })
        
    return versions

def get_backtest_candidates(cur):
    """Fetch stocks that are ready for backtesting (sufficient data)"""
    # Criteria:
    # 1. In daily_targets (Active interest)
    # 2. Has news data in recent 6 months > 50 items (Arbitrary threshold)
    # 3. Has price data (Implicitly checked by daily_targets usually, but we check presence)
    
    cur.execute("""
        WITH news_counts AS (
            SELECT 
                nm.stock_code, 
                COUNT(*) as news_cnt
            FROM tb_news_mapping nm
            JOIN tb_news_url nu ON nm.url_hash = nu.url_hash
            WHERE nu.published_at_hint >= CURRENT_DATE - INTERVAL '6 months'
            GROUP BY nm.stock_code
        )
        SELECT 
            dt.stock_code,
            sm.stock_name,
            COALESCE(nc.news_cnt, 0) as news_count,
            dt.status
        FROM daily_targets dt
        JOIN tb_stock_master sm ON dt.stock_code = sm.stock_code
        LEFT JOIN news_counts nc ON dt.stock_code = nc.stock_code
        WHERE COALESCE(nc.news_cnt, 0) > 10
        ORDER BY nc.news_cnt DESC
    """)
    rows = cur.fetchall()
    
    return [
        {
            "stock_code": r['stock_code'],
            "stock_name": r['stock_name'],
            "news_count": r['news_count'],
            "status": r['status']
        }
        for r in rows
    ]

def get_golden_parameters(cur):
    """
    Fetch the currently active optimal parameters (Golden Parameters) for all stocks.
    """
    cur.execute("""
        SELECT dt.stock_code, sm.stock_name, 
               dt.optimal_lag as lag, 
               dt.optimal_window_months as window, 
               dt.optimal_alpha as alpha,
               dt.updated_at
        FROM daily_targets dt
        JOIN tb_stock_master sm ON dt.stock_code = sm.stock_code
        WHERE dt.optimal_window_months IS NOT NULL
        ORDER BY dt.updated_at DESC
    """)
    return cur.fetchall()

def get_weekly_performance_summary(cur, stock_code):
    """Aggregates performance from Monday of the current week to now."""
    now = datetime.now()
    # Monday of this week
    monday = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    
    cur.execute("""
        SELECT 
            COUNT(*) as total_days,
            SUM(CASE WHEN actual_alpha IS NOT NULL THEN 1 ELSE 0 END) as verified_days,
            SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct_days,
            AVG(ABS(actual_alpha)) as avg_alpha,
            json_agg(json_build_object(
                'date', prediction_date,
                'score', sentiment_score,
                'is_correct', is_correct,
                'alpha', actual_alpha
            ) ORDER BY prediction_date ASC) as daily_details
        FROM tb_predictions
        WHERE stock_code = %s AND prediction_date >= %s
    """, (stock_code, monday))
    
    row = cur.fetchone()
    if not row or row['total_days'] == 0:
        return {
            "total_days": 0,
            "hit_rate": 0,
            "avg_alpha": 0,
            "details": []
        }
        
    hit_rate = (row['correct_days'] / row['verified_days']) * 100 if row['verified_days'] and row['verified_days'] > 0 else 0
    
    return {
        "total_days": row['total_days'],
        "verified_days": row['verified_days'] or 0,
        "correct_days": row['correct_days'] or 0,
        "hit_rate": round(hit_rate, 1),
        "avg_alpha": round(float(row['avg_alpha'] or 0), 4),
        "details": row['daily_details']
    }

def get_weekly_outlook_data(cur, stock_code):
    """Fetches expectations for the remainder of the week and recent sentiment pulse."""
    # Calculate monday first since it's used in the query
    now = datetime.now()
    monday = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    
    # This involves latest predictions that don't have actuals yet (outlook)
    cur.execute("""
        SELECT 
            prediction_date, 
            sentiment_score, 
            intensity, 
            expected_alpha, 
            status,
            top_keywords,
            is_correct
        FROM tb_predictions
        WHERE stock_code = %s AND prediction_date >= %s
        ORDER BY prediction_date ASC
        LIMIT 15
    """, (stock_code, monday.strftime('%Y-%m-%d')))
    outlook_rows = cur.fetchall()
    
    # Also get top moving keywords for the week
    
    cur.execute("""
        SELECT word, beta
        FROM tb_sentiment_dict
        WHERE stock_code = %s AND updated_at >= %s
        ORDER BY ABS(beta) DESC
        LIMIT 20
    """, (stock_code, monday))
    top_words = cur.fetchall()

    # Get latest fundamentals for Pulse
    cur.execute("""
        SELECT per, pbr, roe, market_cap, sector
        FROM tb_stock_fundamentals
        WHERE stock_code = %s
        ORDER BY base_date DESC
        LIMIT 1
    """, (stock_code,))
    fund = cur.fetchone()
    
    fund_data = {
        "per": float(fund['per']) if fund and fund['per'] else None,
        "pbr": float(fund['pbr']) if fund and fund['pbr'] else None,
        "roe": float(fund['roe']) if fund and fund['roe'] else None,
        "market_cap": float(fund['market_cap']) if fund and fund['market_cap'] else None,
        "sector": fund['sector'] if fund else "N/A"
    }
    
    # Generate Consumer-friendly Valuation Label (Bilingual)
    pbr = fund_data['pbr']
    roe = fund_data['roe']
    if pbr is not None:
        if pbr < 1.0 and (roe is None or roe > 5):
            val_label = "Good Value 저평가"
            val_color = "emerald"
        elif pbr > 8.0:
            val_label = "High Premium 고평가"
            val_color = "rose"
        elif pbr > 4.0:
            val_label = "Premium Price 프리미엄 가격"
            val_color = "amber"
        else:
            val_label = "Fair Value 적정가격"
            val_color = "indigo"
    else:
        val_label = "No Data 데이터 없음"
        val_color = "gray"
    
    fund_data["valuation_label"] = val_label
    fund_data["valuation_color"] = val_color

    # --- Phase 7: Calendar-driven logic ---
    now = datetime.now()
    # Get current week's Monday
    monday = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Generate 10 trading days (2 weeks of Mon-Fri)
    # We want Mon-Fri of THIS week and NEXT week, regardless of trading status
    target_dates = []
    for week_off in [0, 7]:
        for day_off in range(5): # Mon-Fri
            target_dates.append((monday + timedelta(days=week_off + day_off)).strftime('%Y-%m-%d'))
    
    # Map existing predictions to these dates
    prediction_map = {r['prediction_date'].strftime('%Y-%m-%d'): r for r in outlook_rows}
    
    final_outlook = []
    for d_str in target_dates:
        is_open = calendar_helper.is_trading_day(d_str)
        existing = prediction_map.get(d_str)
        
        if not is_open:
            item = {
                "date": d_str,
                "score": 0,
                "alpha": 0,
                "status": "HOLIDAY",
                "primary_driver": "휴장"
            }
        elif existing:
            tk = existing.get('top_keywords')
            if isinstance(tk, str):
                try:
                    tk_dict = json.loads(tk or '{}')
                except:
                    tk_dict = {}
            else:
                tk_dict = tk or {}
            
            # V3 Logic: extract from granular positive/negative lists based on status
            positive_list = tk_dict.get('positive', [])
            negative_list = tk_dict.get('negative', [])
            
            # Default fallback
            primary_driver = "시장 감성"
            primary_driver_kr = "시장 감성"
            
            # Determine alignment based on status
            target_list = []
            if 'Buy' in existing['status']:
                target_list = positive_list
            elif 'Sell' in existing['status']:
                target_list = negative_list
            else:
                # Neutral: pick mostly updated one or largest impact? 
                # Pick largest absolute score from combined
                all_words = (positive_list if isinstance(positive_list, list) else []) + \
                            (negative_list if isinstance(negative_list, list) else [])
                # manually sort if needed, but usually they are pre-sorted.
                # Just pick top of positive if exists, else negative
                target_list = positive_list or negative_list

            if target_list and isinstance(target_list, list):
                # Iterate to find first valid driver
                for top_item in target_list:
                    if not isinstance(top_item, dict): continue
                    
                    raw_word = top_item.get('word', '')
                    # Clean it
                    clean = raw_word.split('_L')[0].replace('_', ' ').replace(';', ' ').strip()
                    
                    # Garbage Filter
                    if clean.isdigit(): continue
                    if len(clean) == 1 and clean.isalnum(): continue
                    
                    if clean:
                        primary_driver = clean
                        break
            
            # Fallback for legacy data (simple keys)
            if primary_driver == "시장 감성":
                driver_keys = [k for k in tk_dict.keys() if k not in ('version', 'news_count', 'decay_based', 'positive', 'negative')]
                if driver_keys:
                    primary_driver = driver_keys[0]
                
            item = {
                "date": d_str,
                "score": float(existing['sentiment_score'] or 0),
                "alpha": float(existing['expected_alpha'] or 0),
                "status": existing['status'],
                "primary_driver": primary_driver,
                "is_correct": existing.get('is_correct')
            }
        else:
            item = {
                "date": d_str,
                "score": 0,
                "alpha": 0,
                "status": "PENDING",
                "primary_driver": "분석 중..."
            }
        final_outlook.append(item)

    # Process Pulse Words (Phase 21: Aggregated Daily Data)
    # Instead of using `top_words` from dictionary, use `outlook_rows` -> `top_keywords`
    
    agg_map = {}
    
    # Iterate through all fetched prediction rows (covering displayed range)
    for row in outlook_rows:
        tk_json = row.get('top_keywords')
        if not tk_json:
            continue
            
        try:
            tk_dict = tk_json if isinstance(tk_json, dict) else json.loads(tk_json)
        except:
            continue
            
        # Extract both lists
        pos_list = tk_dict.get('positive', [])
        neg_list = tk_dict.get('negative', [])
        
        # Helper to process list
        def process_list(word_list, is_positive):
            if not isinstance(word_list, list): return
            for item in word_list:
                if not isinstance(item, dict): continue
                raw_word = item.get('word', '')
                score = float(item.get('score', 0))
                
                # Clean
                clean = raw_word.split('_L')[0].replace('_', ' ').replace(';', ' ').strip()
                
                # Garbage Filter: Skip digits or very short non-korean alphanumeric
                # Simple check: if it acts like a number
                if clean.isdigit(): continue
                if len(clean) == 1 and clean.isalnum(): continue # Skip single chars like 'A', '1'
                if not clean: continue
                
                if clean not in agg_map:
                    agg_map[clean] = {'word': clean, 'total_score': 0.0, 'count': 0, 'max_score': 0.0}
                
                agg_map[clean]['total_score'] += score
                agg_map[clean]['count'] += 1
                if abs(score) > abs(agg_map[clean]['max_score']):
                    agg_map[clean]['max_score'] = score

        process_list(pos_list, True)
        process_list(neg_list, False)

    # Calculate Weekly Narrative
    valid_scores = [item['score'] for item in final_outlook if item['status'] not in ('HOLIDAY', 'PENDING')]
    avg_sentiment = sum(valid_scores) / len(valid_scores) if valid_scores else 0
    
    # Get top driver from ACTUAL usage (agg_map) not Dictionary
    top_driver = "Market"
    top_driver_kr = "시장"
    
    # Sort agg_map by absolute total score to find the most influential word of the week
    sorted_drivers = sorted(agg_map.values(), key=lambda x: abs(x['total_score']), reverse=True)
    
    if sorted_drivers:
        top_driver_obj = sorted_drivers[0]
        top_driver = top_driver_obj['word']
        top_driver_kr = top_driver 
        
    narrative = {
        "en": "",
        "kr": ""
    }
    
    if avg_sentiment > 0.3:
        narrative["en"] = f"Investors are showing strong optimism around <span class='text-indigo-600 font-bold'>{top_driver}</span>, driving a positive trend."
        narrative["kr"] = f"<span class='text-indigo-600 font-bold'>{top_driver_kr}</span>에 대한 투자자들의 기대감이 높아지며 긍정적인 추세를 보이고 있습니다."
        narrative["sentiment"] = "positive"
    elif avg_sentiment < -0.3:
        narrative["en"] = f"Market sentiment faces headwinds, primarily driven by concerns regarding <span class='text-indigo-600 font-bold'>{top_driver}</span>."
        narrative["kr"] = f"<span class='text-indigo-600 font-bold'>{top_driver_kr}</span> 관련 우려가 확산되며 시장 감성이 위축되고 있습니다."
        narrative["sentiment"] = "negative"
    else:
        narrative["en"] = f"The market is showing mixed signals regarding <span class='text-indigo-600 font-bold'>{top_driver}</span>, suggesting a cautious approach."
        narrative["kr"] = f"<span class='text-indigo-600 font-bold'>{top_driver_kr}</span>에 대해 엇갈린 신호가 감지되며, 신중한 접근이 요구됩니다."
        narrative["sentiment"] = "neutral"
    # Sort final_outlook ascending by date (Chronological)
    final_outlook.sort(key=lambda x: x['date'])

    # If agg_map is empty (e.g. no daily data yet), fallback to top_words?
    # User specifically wants daily data. If empty, show empty. 
    # But for now, let's keep top_words as fallback if agg_map is empty?
    # No, user knows data is sparsely populated (0s).
    
    if not agg_map and top_words:
        # Fallback to old logic if daily agg is empty (e.g. legacy data)
        for item in top_words:
            raw_word = item['word']
            beta = float(item['beta'])
            clean_word = raw_word.split('_L')[0].replace('_', ' ').replace(';', ' ').strip()
            if clean_word not in agg_map:
                agg_map[clean_word] = {'word': clean_word, 'total_score': 0.0, 'count': 0, 'max_score': 0.0}
            agg_map[clean_word]['total_score'] += beta
            agg_map[clean_word]['count'] += 1
            if abs(beta) > abs(agg_map[clean_word]['max_score']):
                agg_map[clean_word]['max_score'] = beta

    # 2. Split & Sort
    positive_drivers = []
    negative_drivers = []
    
    for word, data in agg_map.items():
        # Use total_score sign for classification
        if data['total_score'] > 0:
            # Rename total_score to beta for frontend compatibility if needed? 
            # Frontend uses {{ item.count }} and just {{ item.word }}. 
            # Beta check is used in older code but new code loops .positive/.negative directly.
            positive_drivers.append(data)
        elif data['total_score'] < 0:
            negative_drivers.append(data)
            
    # Sort by absolute influence (Magnitude of Total Score or Max Score?)
    # "Influential words" -> Total Score sum is good for cumulative impact.
    positive_drivers.sort(key=lambda x: abs(x['total_score']), reverse=True)
    negative_drivers.sort(key=lambda x: abs(x['total_score']), reverse=True)

    return {
        "outlook": final_outlook,
        "pulse_words": {
            "all": [], # Deprecated or add top_words if needed
            "positive": positive_drivers[:5], # Top 5 Aggregate
            "negative": negative_drivers[:5]  # Top 5 Aggregate
        },
        "fundamentals": fund_data,
        "narrative": narrative
    }

def get_model_display_info(cur, stock_code):
    """
    Fetch active model metadata for display in the dashboard header.
    Returns dict with name, duration, status, period, score_label.
    """
    # 1. Find Active Main Version
    cur.execute("""
        SELECT version, created_at 
        FROM tb_sentiment_dict_meta 
        WHERE stock_code = %s AND source = 'Main' AND is_active = TRUE
        ORDER BY created_at DESC LIMIT 1
    """, (stock_code,))
    row = cur.fetchone()
    
    # Fallback to latest verification result or prediction if no meta is active
    if not row:
         cur.execute("""
            SELECT version FROM tb_predictions 
            WHERE stock_code = %s 
            ORDER BY prediction_date DESC LIMIT 1
         """, (stock_code,))
         pred_row = cur.fetchone()
         version = json.loads(pred_row['version']) if pred_row and pred_row['version'].startswith('{') else pred_row['version'] if pred_row else "Unknown"
         # Handle "phase22_1y_samsung_hybrid" format
         if isinstance(version, str) and "_hybrid" in version:
             version = version
    else:
        version = row['version']

    # 2. Parse Version String
    # e.g. phase22_1y_samsung_hybrid, phase22_3m, etc.
    if not isinstance(version, str):
        version = "Unknown"
        
    display = {
        "name": "AI",
        "tag": "2M", # Default to 2M if not found, closer to current truth
        "status_en": "Active Model",
        "status_kr": "최적화 모델 가동 중",
        "period_en": "Rolling Window",
        "period_kr": "최근 데이터",
        "verification_en": "Verified",
        "verification_kr": "검증 완료"
    }

    # 3. Fetch Params from daily_targets for accuracy
    cur.execute("SELECT optimal_window_months, optimal_alpha FROM daily_targets WHERE stock_code = %s", (stock_code,))
    t_row = cur.fetchone()
    
    window = 2
    if t_row and t_row['optimal_window_months']:
        window = t_row['optimal_window_months']
        display["tag"] = f"{window}M"
        
        # Calculate dynamic period string based on window
        end_date = datetime.now()
        start_date = end_date - timedelta(days=window*30)
        display["period_en"] = f"{start_date.strftime('%b %y')} - {end_date.strftime('%b %y')}"
        display["period_kr"] = f"{start_date.strftime('%y.%m')} ~ {end_date.strftime('%y.%m')}"
        
        if t_row['optimal_alpha']:
             display["name"] = f"Lasso (α={t_row['optimal_alpha']})"
             display["alpha"] = float(t_row['optimal_alpha']) # Add raw alpha for template
    else:
        # If not in daily_targets, try to parse from version string fallback
        if "3m" in version.lower(): window = 3
        if "1y" in version.lower(): window = 12
        if "6m" in version.lower(): window = 6
        display["tag"] = f"{window}M"

    if "1y" in version:
        display["tag"] = "1Y" # Override if version explicitly says 1Y (legacy compat)
        
    if "hybrid" in version or "Buffer" in version:
        display["status_en"] = "Hybrid Model (Main + Buffer)"
        display["status_kr"] = "하이브리드 모델 (Main + Buffer) 가동 중"
        display["name"] = "Hybrid"
        
    return display

def get_system_health(cur):
    """Fetch the latest system health status from the watchdog table"""
    # Simply check if table exists first to avoid error on fresh start
    cur.execute("SELECT to_regclass('tb_system_health')")
    result = cur.fetchone()
    if not result or not result['to_regclass']:
        return None
        
    cur.execute("""
        SELECT status, details, updated_at 
        FROM tb_system_health 
        WHERE check_type = 'watchdog'
    """)
    row = cur.fetchone()
    
    if row:
        details = row['details']
        if isinstance(details, str):
            details = json.loads(details)
            
        return {
            "status": row['status'],
            "details": details,
            "updated_at": row['updated_at']
        }
    return None

def log_system_event(cur, event_type, severity, component, message, metadata=None):
    """
    Logs a system event to tb_system_events.
    """
    # Create table if not exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tb_system_events (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            event_type VARCHAR(20) NOT NULL,
            severity VARCHAR(20) NOT NULL,
            component VARCHAR(50) NOT NULL,
            message TEXT NOT NULL,
            metadata JSONB
        )
    """)
    # Create index if not exists (simple check or ignore error)
    # Skipped index check for brevity, Postgres handles it usually or we can do IF NOT EXISTS in newer PG.
    
    cur.execute("""
        INSERT INTO tb_system_events (event_type, severity, component, message, metadata)
        VALUES (%s, %s, %s, %s, %s)
    """, (event_type, severity, component, message, json.dumps(metadata) if metadata else None))

def get_system_events(cur, limit=50):
    """Fetches recent system events."""
    cur.execute("SELECT * FROM tb_system_events ORDER BY timestamp DESC LIMIT %s", (limit,))
    return cur.fetchall()

def get_expert_metrics(cur, stock_code, v_job_id=None):
    """
    Calculates advanced ML and financial risk metrics.
    If v_job_id is provided, use verification results. Otherwise use Live predictions.
    """
    if v_job_id:
        cur.execute("""
            SELECT 
                vr.predicted_score as p_alpha, 
                vr.actual_alpha as a_alpha,
                dp.sector_return
            FROM tb_verification_results vr
            LEFT JOIN tb_daily_price dp ON dp.stock_code = %s AND vr.target_date = dp.date
            WHERE vr.v_job_id = %s AND vr.actual_alpha IS NOT NULL
            ORDER BY vr.target_date ASC
        """, (stock_code, v_job_id))
    else:
        # Live Data (last 90 days for stability)
        cur.execute("""
            SELECT 
                p.expected_alpha as p_alpha, 
                p.actual_alpha as a_alpha,
                dp.sector_return
            FROM tb_predictions p
            LEFT JOIN tb_daily_price dp ON p.stock_code = dp.stock_code AND p.prediction_date = dp.date
            WHERE p.stock_code = %s AND p.actual_alpha IS NOT NULL
              AND p.prediction_date >= CURRENT_DATE - INTERVAL '90 days'
            ORDER BY p.prediction_date ASC
        """, (stock_code,))
    
    rows = cur.fetchall()
    if not rows:
        return {
            "rmse": 0, "mae": 0, "sharpe": 0, "mdd": 0, 
            "ic": 0, "ir": 0, "profit_factor": 0,
            "sortino": 0, "volatility": 0, "beta": 1,
            "mdd_duration": 0,
            "residual_data": [], "residual_hist": {"counts": [], "bins": []}
        }

    p_alphas = np.array([float(r['p_alpha'] or 0) for r in rows])
    a_alphas = np.array([float(r['a_alpha'] or 0) for r in rows])
    s_returns = np.array([float(r['sector_return'] or 0) for r in rows])
    
    # 1. Statistical Metrics
    rmse = np.sqrt(np.mean((p_alphas - a_alphas)**2))
    mae = np.mean(np.abs(p_alphas - a_alphas))
    
    # Information Coefficient (Signal Skill)
    if len(p_alphas) > 1 and np.std(p_alphas) > 0 and np.std(a_alphas) > 0:
        ic = np.corrcoef(p_alphas, a_alphas)[0, 1]
    else:
        ic = 0.0

    # 2. Financial Risk Metrics (Daily Returns)
    daily_returns = a_alphas
    avg_return = np.mean(daily_returns)
    std_return = np.std(daily_returns)
    
    # Sharpe Ratio
    sharpe = (avg_return / std_return * np.sqrt(252)) if std_return > 0 else 0
    
    # Sortino Ratio (Downside Risk)
    downside_returns = daily_returns[daily_returns < 0]
    downside_std = np.std(downside_returns) if len(downside_returns) > 0 else 0
    sortino = (avg_return / downside_std * np.sqrt(252)) if downside_std > 0 else 0

    # Volatility (Annualized)
    volatility = std_return * np.sqrt(252)

    # Beta (Sensitivity to Market/Sector)
    if len(s_returns) > 1 and np.var(s_returns) > 0:
        beta = np.cov(daily_returns, s_returns)[0, 1] / np.var(s_returns)
    else:
        beta = 1.0
    
    # Information Ratio (Consistency)
    ir = (avg_return / std_return) if std_return > 0 else 0

    # Profit Factor
    profits = daily_returns[daily_returns > 0]
    losses = daily_returns[daily_returns < 0]
    profit_factor = (np.sum(profits) / abs(np.sum(losses))) if len(losses) > 0 and np.sum(losses) != 0 else (1.0 if len(profits) > 0 else 0.0)

    # MDD & Duration
    cum_returns = np.cumprod(1 + daily_returns)
    peak = np.maximum.accumulate(cum_returns)
    drawdown = (cum_returns - peak) / peak
    mdd = np.min(drawdown) if len(drawdown) > 0 else 0
    
    # MDD Duration (Max days under peak)
    mdd_duration = 0
    if len(drawdown) > 0:
        curr_dur = 0
        for d in drawdown:
            if d < 0:
                curr_dur += 1
            else:
                mdd_duration = max(mdd_duration, curr_dur)
                curr_dur = 0
        mdd_duration = max(mdd_duration, curr_dur)
    
    # 3. Residual Data
    residuals = p_alphas - a_alphas
    residual_data = [{"x": float(p), "y": float(a)} for p, a in zip(p_alphas, a_alphas)]
    
    hist, bin_edges = np.histogram(residuals, bins=10)
    residual_hist = {
        "counts": hist.tolist(),
        "bins": [round((bin_edges[i] + bin_edges[i+1])/2, 4) for i in range(len(hist))]
    }
    
    return {
        "rmse": round(rmse, 4),
        "mae": round(mae, 4),
        "ic": round(ic, 4),
        "ir": round(ir, 2),
        "sharpe": round(sharpe, 2),
        "sortino": round(sortino, 2),
        "volatility": round(volatility * 100, 1), # In percent
        "beta": round(beta, 2),
        "profit_factor": round(profit_factor, 2),
        "mdd": round(mdd * 100, 2),
        "mdd_duration": mdd_duration,
        "residual_data": residual_data,
        "residual_hist": residual_hist
    }

def get_feature_importance_data(cur, stock_code):
    """
    Returns the top influential features (keywords/factors) for the active model.
    """
    cur.execute("""
        SELECT word, beta 
        FROM tb_sentiment_dict 
        WHERE stock_code = %s 
          AND version = (SELECT version FROM tb_sentiment_dict_meta WHERE stock_code=%s AND is_active=TRUE ORDER BY created_at DESC LIMIT 1)
        ORDER BY ABS(beta) DESC
        LIMIT 20
    """, (stock_code, stock_code))
    
    rows = cur.fetchall()
    return [{"word": r['word'], "beta": float(r['beta'])} for r in rows]

def get_historical_signals(cur, stock_code, limit=20, offset=0):
    """
    Fetches historical predictions older than the current week for infinite scroll.
    Grouped by week in the frontend, so we just return the flat list here.
    """
    # Calculate start of current week (Monday) to exclude current/future signals
    now = datetime.now()
    monday = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    

    cur.execute("""
        SELECT DISTINCT ON (prediction_date)
            prediction_date, 
            sentiment_score, 
            expected_alpha, 
            status,
            actual_alpha,
            is_correct,
            top_keywords
        FROM tb_predictions
        WHERE stock_code = %s 
          AND prediction_date < %s
          AND EXTRACT(DOW FROM prediction_date) NOT IN (0, 6)
        ORDER BY prediction_date DESC, ABS(expected_alpha) DESC
        LIMIT %s OFFSET %s
    """, (stock_code, monday.strftime('%Y-%m-%d'), limit, offset))
    
    rows = cur.fetchall()
    results = []
    
    for r in rows:
        # Parse keywords for "Reasoning"
        tk = r['top_keywords']
        if isinstance(tk, str):
            try:
                tk = json.loads(tk)
            except:
                tk = {}
        
        # Extract primary driver (Top 1 keyword)
        driver = ""
        if isinstance(tk, dict):
            words = []
            if 'positive' in tk: words.extend(tk['positive'])
            if 'negative' in tk: words.extend(tk['negative'])
            if words:
                try:
                    words.sort(key=lambda x: abs(float(x.get('score') or x.get('beta') or 0)), reverse=True)
                except Exception:
                    pass
                if words:
                    driver = words[0].get('word', '').split('_L')[0].replace('_', ' ')
        
        # Determine Prediction Type from Status or Score
        p_type = "Hold"
        status = r['status'] or ""
        alpha = float(r['expected_alpha'] or 0)
        
        # Unify terminology for history
        if status in ['WAIT', 'Neutral', 'PENDING']:
            if calendar_helper.is_trading_day(r['prediction_date'].strftime('%Y-%m-%d')):
                status = 'NEUTRAL'
            else:
                status = 'HOLIDAY'
        
        if "Buy" in status:
            p_type = "Buy"
        elif "Sell" in status:
            p_type = "Sell"
        elif alpha > 0.005: 
            p_type = "Buy"
        elif alpha < -0.005:
            p_type = "Sell"

        results.append({
            "date": r['prediction_date'].strftime('%Y-%m-%d'),
            "day_en": r['prediction_date'].strftime('%a'),
            "prediction_type": p_type,

            "status": status, # Updated to use unified terminology
            "keywords": driver,
            "actual_return": float(r['actual_alpha']) * 100 if r['actual_alpha'] is not None else None,
            "is_correct": r['is_correct'],
            "score": float(r['sentiment_score']) if r['sentiment_score'] else 0
        })
        
    return results
def get_thematic_timeline(cur, stock_code, limit=60):
    """
    Fetches the top keyword driver for each day to build a thematic timeline.
    """
    cur.execute("""
        SELECT prediction_date, top_keywords, sentiment_score, expected_alpha
        FROM tb_predictions
        WHERE stock_code = %s AND top_keywords IS NOT NULL
        ORDER BY prediction_date DESC
        LIMIT %s
    """, (stock_code, limit))
    
    rows = cur.fetchall()
    timeline = []
    for r in rows:
        keywords = r['top_keywords']
        if isinstance(keywords, str):
            keywords = json.loads(keywords)
        
        # Extract version/model source
        version = keywords.get('version', '') if isinstance(keywords, dict) else ''
        if 'hybrid' in version.lower():
            model_tag = 'H'  # Hybrid
        elif version:
            model_tag = 'L'  # Lasso with version
        else:
            model_tag = 'L'  # Legacy Lasso
        
        # Get the word with highest absolute beta
        top_word = "N/A"
        top_val = 0
        if keywords:
            # Handle new format: {positive: [{word, weight}, ...], negative: [...]}
            if 'positive' in keywords or 'negative' in keywords:
                all_words = []
                for item in keywords.get('positive', []):
                    if isinstance(item, dict) and 'word' in item:
                        # Skip internal feature markers
                        if not item['word'].startswith('__F_'):
                            weight = item.get('weight', item.get('score', 0))
                            all_words.append((item['word'], float(weight)))
                for item in keywords.get('negative', []):
                    if isinstance(item, dict) and 'word' in item:
                        if not item['word'].startswith('__F_'):
                            weight = item.get('weight', item.get('score', 0))
                            all_words.append((item['word'], float(weight)))
                
                if all_words:
                    # Sort by absolute value, get top
                    sorted_words = sorted(all_words, key=lambda x: abs(x[1]), reverse=True)
                    top_word = sorted_words[0][0]
                    top_val = sorted_words[0][1]
            else:
                # Old format: {word: weight}
                filtered_k = []
                for k, v in keywords.items():
                    try:
                        filtered_k.append((k, float(v)))
                    except (ValueError, TypeError):
                        continue
                
                if filtered_k:
                    sorted_k = sorted(filtered_k, key=lambda x: abs(x[1]), reverse=True)
                    top_word = sorted_k[0][0]
                    top_val = sorted_k[0][1]
        
        timeline.append({
            "date": r['prediction_date'].strftime('%Y-%m-%d'),
            "weekday_name": r['prediction_date'].strftime('%a'),
            "week_label": f"{r['prediction_date'].isocalendar()[0]}-W{r['prediction_date'].isocalendar()[1]}",
            "word": top_word,
            "weight": round(top_val, 4),
            "score": round(float(r['sentiment_score']), 2),
            "model": model_tag  # 'L' for Lasso, 'H' for Hybrid
        })
    
    return sorted(timeline, key=lambda x: x['date'])

def get_fundamental_history(cur, stock_code, limit=60):
    """Fetches historical fundamental data for charting (Recent data first)."""
    cur.execute("""
        SELECT base_date as date, per, pbr, roe
        FROM (
            SELECT base_date, per, pbr, roe
            FROM tb_stock_fundamentals
            WHERE stock_code = %s
            ORDER BY base_date DESC
            LIMIT %s
        ) as sub
        ORDER BY base_date ASC
    """, (stock_code, limit))
    rows = cur.fetchall()
    
    history = []
    for r in rows:
        history.append({
            "date": r['date'].strftime('%Y-%m-%d') if hasattr(r['date'], 'strftime') else str(r['date']),
            "per": float(r['per']) if r['per'] else 0,
            "pbr": float(r['pbr']) if r['pbr'] else 0,
            "roe": float(r['roe']) if r['roe'] else 0
        })
    return history
