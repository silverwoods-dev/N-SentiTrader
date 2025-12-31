# src/dashboard/routers/quant.py
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from src.db.connection import get_db_cursor
from src.dashboard.data_helpers import (
    get_validation_summary, get_validation_history, get_latest_version_dict,
    get_performance_chart_data, get_timeline_dict, get_news_pulse_data,
    get_vanguard_derelict, get_awo_landscape_data,
    get_equity_curve_data, get_feature_decay_analysis,
    get_equity_curve_data, get_feature_decay_analysis,
    get_available_model_versions, get_backtest_candidates,
    get_golden_parameters,
    get_weekly_performance_summary, get_weekly_outlook_data,
    get_expert_metrics, get_feature_importance_data,
    get_model_display_info
)
from datetime import datetime, timedelta
import json
from src.utils.mq import publish_verification_job

router = APIRouter(prefix="/analytics")

@router.get("/", response_class=HTMLResponse)
@router.get("/outlook", response_class=HTMLResponse)
async def analytics_outlook(request: Request, stock_code: str = "005930"):
    from src.dashboard.app import templates
    with get_db_cursor() as cur:
        # Get stock info
        cur.execute("SELECT stock_name FROM tb_stock_master WHERE stock_code = %s", (stock_code,))
        row = cur.fetchone()
        stock_name = row['stock_name'] if row else stock_code

        # Weekly Performance (Mon-Today)
        weekly_perf = get_weekly_performance_summary(cur, stock_code)
        
        # Weekly Outlook (Today-Fri)
        weekly_outlook = get_weekly_outlook_data(cur, stock_code)
        
        # Traditional history for chart
        perf_data = get_performance_chart_data(cur, stock_code, limit=30)
        
        # News Pulse for context
        pulse_data = get_news_pulse_data(cur, stock_code, days=7)
        
        # Dynamic Model Info
        model_info = get_model_display_info(cur, stock_code)

    return templates.TemplateResponse("weekly_outlook.html", {
        "request": request,
        "stock_code": stock_code,
        "stock_name": stock_name,
        "weekly_perf": weekly_perf,
        "weekly_outlook": weekly_outlook,
        "perf_data": perf_data,
        "pulse_data": pulse_data,
        "model_info": model_info
    })

@router.get("/search", response_class=HTMLResponse)
async def analytics_search(request: Request, q: str = ""):
    from src.dashboard.app import templates
    if not q or len(q) < 1:
        return HTMLResponse(content="")
    
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT stock_code, stock_name, market_type 
            FROM tb_stock_master 
            WHERE stock_code LIKE %s OR stock_name LIKE %s
            ORDER BY stock_name ASC
            LIMIT 10
        """, (f"%{q}%", f"%{q}%"))
        results = cur.fetchall()
                
    # Reuse the global search results partial but with a different redirect/link
    # Or create a specific one for analytics search
    html = "<div class='glass-card rounded-xl shadow-xl border border-gray-100 dark:border-gray-700 overflow-hidden'>"
    for r in results:
        html += f"""
        <a href="/analytics/outlook?stock_code={r['stock_code']}" class="block px-4 py-3 hover:bg-indigo-50 dark:hover:bg-indigo-900/40 transition-colors border-b border-gray-100 dark:border-gray-700 last:border-0">
            <div class="flex items-center justify-between">
                <span class="font-bold text-sm">{r['stock_name']}</span>
                <span class="text-[10px] text-gray-500 font-mono">{r['stock_code']}</span>
            </div>
        </a>
        """
    if not results:
        html += "<div class='px-4 py-8 text-center text-gray-400 text-sm italic'>No stocks found</div>"
    html += "</div>"
    return HTMLResponse(content=html)

@router.get("/validator", response_class=HTMLResponse)
async def analytics_home(request: Request, stock_code: str = "005930"):
    from src.dashboard.app import templates
    with get_db_cursor() as cur:
        # Get stock name
        cur.execute("SELECT stock_name FROM tb_stock_master WHERE stock_code = %s", (stock_code,))
        stock_row = cur.fetchone()
        stock_name = stock_row['stock_name'] if stock_row else stock_code

        summary = get_validation_summary(cur, stock_code)
        history = get_validation_history(cur, stock_code)
        
        main_pos = get_latest_version_dict(cur, stock_code, 'Main', limit=10, positive=True)
        main_neg = get_latest_version_dict(cur, stock_code, 'Main', limit=10, positive=False)
        buffer_pos = get_latest_version_dict(cur, stock_code, 'Buffer', limit=10, positive=True)
        buffer_neg = get_latest_version_dict(cur, stock_code, 'Buffer', limit=10, positive=False)
        
        perf_data = get_performance_chart_data(cur, stock_code, limit=60)
        latest_pred = get_validation_history(cur, stock_code, limit=1)
        latest_prediction = latest_pred[0] if latest_pred else None
        
        # Calculate latest_update for the partial template
        latest_update = None
        all_dict_items = main_pos + main_neg + buffer_pos + buffer_neg
        if all_dict_items:
            latest_update = max((item['updated_at'] for item in all_dict_items if item.get('updated_at')), default=None)
        
        chart_data = {
            "dates": [item["date"] for item in perf_data],
            "scores": [{"x": item["date"], "y": item["sentiment_score"]} for item in perf_data],
            "positive_scores": [{"x": item["date"], "y": item.get("positive_score", 0.0)} for item in perf_data],
            "negative_scores": [{"x": item["date"], "y": item.get("negative_score", 0.0)} for item in perf_data],
            "expected_alphas": [{"x": item["date"], "y": item.get("expected_alpha", 0.0)} for item in perf_data],
            "intensities": [{"x": item["date"], "y": item.get("intensity", 0.0)} for item in perf_data],
            "statuses": [{"x": item["date"], "y": item.get("status", "N/A")} for item in perf_data],
            "predictions": [
                {"x": item["date"], "y": 0.1 if item.get("expected_alpha", 0) > 0 else -0.1}
                for item in perf_data
            ],
            "alphas": [
                {"x": item["date"], "y": item["actual_alpha"]} 
                for item in perf_data 
                if item["actual_alpha"] is not None
            ],
            "pure_alphas": [
                {"x": item["date"], "y": item["pure_alpha"]}
                for item in perf_data
                if item.get("pure_alpha") is not None
            ],
            "sector_returns": [
                {"x": item["date"], "y": item.get("sector_return", 0.0)}
                for item in perf_data
            ],
            "is_trading_days": [item["is_trading_day"] for item in perf_data]
        }
        
    return templates.TemplateResponse("validator.html", {
        "request": request,
        "stock_code": stock_code,
        "stock_name": stock_name,
        "summary": summary,
        "history": history,
        "main_pos": main_pos,
        "main_neg": main_neg,
        "buffer_pos": buffer_pos,
        "buffer_neg": buffer_neg,
        "chart_data": chart_data,
        "latest_prediction": latest_prediction,
        "latest_update": latest_update
    })

@router.get("/current", response_class=HTMLResponse)
async def analytics_current(request: Request, stock_code: str = "005930"):
    from src.dashboard.app import templates
    with get_db_cursor() as cur:
        main_pos = get_latest_version_dict(cur, stock_code, 'Main', limit=10, positive=True)
        main_neg = get_latest_version_dict(cur, stock_code, 'Main', limit=10, positive=False)
        buffer_pos = get_latest_version_dict(cur, stock_code, 'Buffer', limit=10, positive=True)
        buffer_neg = get_latest_version_dict(cur, stock_code, 'Buffer', limit=10, positive=False)
        
        latest_update = None
        if main_pos or main_neg:
            all_items = main_pos + main_neg
            latest_update = max(item['updated_at'] for item in all_items) if all_items else None
    
    return templates.TemplateResponse("partials/validator_current.html", {
        "request": request,
        "stock_code": stock_code,
        "main_pos": main_pos,
        "main_neg": main_neg,
        "buffer_pos": buffer_pos,
        "buffer_neg": buffer_neg,
        "latest_update": latest_update
    })

@router.get("/timeline", response_class=HTMLResponse)
async def analytics_timeline(
    request: Request, 
    stock_code: str = "005930",
    range: str = "30d"
):
    from src.dashboard.app import templates
    range_days = {'7d': 7, '30d': 30, '90d': 90}.get(range, 30)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=range_days)
    
    with get_db_cursor() as cur:
        # Get heatmap data including top active words
        main_data = get_timeline_dict(cur, stock_code, 'Main', start_date, end_date, limit_words=20)
        
        # Get Vanguard / Derelict words
        updates = get_vanguard_derelict(cur, stock_code, 'Main', days=7)
        vanguard = [r for r in updates if r['type'] == 'vanguard']
        derelict = [r for r in updates if r['type'] == 'derelict']
        
        # Prepare heatmap structure
        top_words = sorted(list(set(item['word'] for item in main_data)))
        word_series = {}
        for item in main_data:
            word = item['word']
            if word not in word_series:
                word_series[word] = []
            word_series[word].append({
                'date': item['updated_at'].strftime('%Y-%m-%d'),
                'beta': item['beta']
            })
            
        # Get News Pulse data
        pulse_data = get_news_pulse_data(cur, stock_code, days=range_days)
    
    return templates.TemplateResponse("partials/validator_timeline.html", {
        "request": request,
        "stock_code": stock_code,
        "range": range,
        "main_data": main_data[::-1], # Latest first for table
        "word_series": word_series,
        "top_words": top_words,
        "vanguard": vanguard,
        "derelict": derelict,
        "pulse_data": pulse_data
    })

@router.get("/reports/{stock_code}/{date}")
async def get_report(stock_code: str, date: str):
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT p.*, sm.stock_name
            FROM tb_predictions p
            JOIN tb_stock_master sm ON p.stock_code = sm.stock_code
            WHERE p.stock_code = %s AND p.prediction_date = %s
        """, (stock_code, date))
        row = cur.fetchone()
        
    if not row:
        return {"error": "Report not found"}
        
    return {
        "stock_code": row['stock_code'],
        "stock_name": row['stock_name'],
        "score": float(row['sentiment_score']),
        "prediction": "UP" if row['prediction'] == 1 else "DOWN",
        "expected_alpha": float(row['expected_alpha']) if row['expected_alpha'] else 0.0,
        "top_keywords": row['top_keywords'] if isinstance(row['top_keywords'], dict) else json.loads(row['top_keywords'] or '{}')
    }

@router.get("/awo_landscape")
async def get_awo_landscape(stock_code: str = "005930"):
    with get_db_cursor() as cur:
        data = get_awo_landscape_data(cur, stock_code)
    return {"landscape": data}

# --- New Expert Features (Quant Hub) ---

@router.get("/versions/{stock_code}", response_class=HTMLResponse)
async def view_dictionary_versions(request: Request, stock_code: str):
    """단어사전 버전 이력 조회 (Lifecycle Management)"""
    from src.dashboard.app import templates
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT dm.*, sm.stock_name
            FROM tb_sentiment_dict_meta dm
            JOIN tb_stock_master sm ON dm.stock_code = sm.stock_code
            WHERE dm.stock_code = %s
            ORDER BY dm.created_at DESC
        """, (stock_code,))
        versions = cur.fetchall()
        
    if "HX-Request" in request.headers:
        # HTMX 요청 시 테이블 바디만 반환 (또는 전체 테이블)
        # 여기서는 편의상 전용 partial을 사용하거나, 동일 템플릿의 block만 반환 가능하나 
        # 명시적으로 따로 처리함. 
        return templates.TemplateResponse("quant/partials/version_rows.html", {
            "request": request,
            "stock_code": stock_code,
            "versions": versions
        })

    return templates.TemplateResponse("quant/versions.html", {
        "request": request,
        "stock_code": stock_code,
        "versions": versions
    })

@router.post("/versions/activate/{stock_code}/{version}/{source}")
async def activate_dict_version(request: Request, stock_code: str, version: str, source: str):
    """특정 버전의 단어사전을 서비스용(Active)으로 전환"""
    from src.learner.lasso import LassoLearner
    learner = LassoLearner()
    learner.activate_version(stock_code, version, source)
    
    # 업데이트된 목록 반환
    # 업데이트된 목록 반환
    return await view_dictionary_versions(request, stock_code)

@router.get("/expert", response_class=HTMLResponse)
async def analytics_expert(request: Request, stock_code: str = "005930", v_job_id: int = None):
    """전문가용 심층 분석 대시보드 (Static-First)"""
    from src.dashboard.app import templates
    
    with get_db_cursor() as cur:
        # 0. Auto-resolve v_job_id if not provided (Find latest completed AWO_SCAN)
        if not v_job_id:
            cur.execute("""
                SELECT v_job_id FROM tb_verification_jobs 
                WHERE stock_code = %s AND v_type = 'AWO_SCAN' AND status = 'completed'
                ORDER BY completed_at DESC LIMIT 1
            """, (stock_code,))
            row = cur.fetchone()
            if row:
                v_job_id = row['v_job_id']

        # 1. Stock Info
        cur.execute("SELECT stock_name FROM tb_stock_master WHERE stock_code = %s", (stock_code,))
        row = cur.fetchone()
        stock_name = row['stock_name'] if row else stock_code

        # 2. Calibration Data (AWO Stability)
        landscape = get_awo_landscape_data(cur, stock_code, v_job_id=v_job_id)
        
        # 3. Performance Data (Equity Curve)
        equity_curve = get_equity_curve_data(cur, stock_code, v_job_id=v_job_id)
        
        # 4. Forensics (Feature Decay)
        feature_decay = get_feature_decay_analysis(cur, stock_code)
        
        # 5. Latest Summary for Header
        summary = get_validation_summary(cur, stock_code)
        
        # 6. Available Versions for Selector
        versions = get_available_model_versions(cur, stock_code)
        
        # 7. Advanced Metrics
        expert_metrics = get_expert_metrics(cur, stock_code, v_job_id=v_job_id)
        
        # 8. Feature Importance
        feature_importance = get_feature_importance_data(cur, stock_code)

        # 9. AWO Checkpoints (New functionality)
        checkpoints = []
        if v_job_id:
            cur.execute("""
                SELECT * FROM tb_awo_checkpoints 
                WHERE v_job_id = %s 
                ORDER BY stability_score DESC
            """, (v_job_id,))
            checkpoints = cur.fetchall()

    return templates.TemplateResponse("quant/validator_expert.html", {
        "request": request,
        "stock_code": stock_code,
        "stock_name": stock_name,
        "landscape": landscape,
        "equity_curve": equity_curve,
        "feature_decay": feature_decay,
        "summary": summary,
        "v_job_id": v_job_id,
        "versions": versions,
        "expert_metrics": expert_metrics,
        "feature_importance": feature_importance,
        "checkpoints": checkpoints
    })

@router.get("/backtest/monitor", response_class=HTMLResponse)
async def monitor_backtests(request: Request):
    """WF 백테스팅 진행 상태 모니터링"""
    from src.dashboard.app import templates
    with get_db_cursor() as cur:
        # Fetch verification jobs (AWO, WF, DAILY_UPDATE)
        cur.execute("""
            SELECT vj.*, sm.stock_name
            FROM tb_verification_jobs vj
            JOIN tb_stock_master sm ON vj.stock_code = sm.stock_code
            ORDER BY vj.started_at DESC NULLS LAST, vj.v_job_id DESC
            LIMIT 30
        """)
        jobs = cur.fetchall()
        
        # Get Backtest Candidates (stocks with sufficient data)
        candidates = get_backtest_candidates(cur)
        
        # [NEW] Get Golden Parameters for Dashboard Header
        golden_params = get_golden_parameters(cur)
        
    return templates.TemplateResponse("quant/backtest_list.html", {
        "request": request,
        "jobs": jobs,
        "candidates": candidates,
        "golden_params": golden_params
    })

@router.get("/backtest/row/{v_job_id}", response_class=HTMLResponse)
async def get_backtest_row(request: Request, v_job_id: int):
    """특정 백테스팅 작업의 현재 상태(Row) 반환 (HTMX Polling용)"""
    from src.dashboard.app import templates
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT vj.*, sm.stock_name
            FROM tb_verification_jobs vj
            JOIN tb_stock_master sm ON vj.stock_code = sm.stock_code
            WHERE vj.v_job_id = %s
        """, (v_job_id,))
        job = cur.fetchone()
    if not job:
        return HTMLResponse(content="")
    return templates.TemplateResponse("quant/partials/backtest_row.html", {
        "request": request,
        "job": job
    })

@router.post("/backtest/create")
async def create_backtest_job(
    request: Request, 
    stock_code: str = Form(...), 
    val_months: int = Form(1),
    v_type: str = Form("AWO_SCAN_2D"),
    min_relevance: int = Form(0)
):
    """새로운 검증(AWO/Backtest) 또는 관리(DAILY_UPDATE) 작업 등록"""
    from src.utils.stock_info import get_stock_name
    
    # 1. 스톡 마스터 확인
    with get_db_cursor() as cur:
        cur.execute("SELECT stock_name FROM tb_stock_master WHERE stock_code = %s", (stock_code,))
        if not cur.fetchone():
            name = get_stock_name(stock_code)
            cur.execute("INSERT INTO tb_stock_master (stock_code, stock_name) VALUES (%s, %s)", (stock_code, name))

    # 2. Validation Limit Check (For AWO/WF types)
    if v_type in ("AWO_SCAN_2D", "AWO_SCAN", "WF_CHECK"):
        if val_months > 12: val_months = 12
        if val_months < 1: val_months = 1
    else:
        # For DAILY_UPDATE, months might not be relevant as it uses Golden Params
        val_months = 0

    # 3. Job 등록 (Pending)
    params = {"val_months": val_months, "min_relevance": min_relevance}
    if v_type == "DAILY_UPDATE":
        params["is_lightweight"] = True # Explicit flag for orchestrator/worker

    with get_db_cursor() as cur:
        cur.execute("""
            INSERT INTO tb_verification_jobs (stock_code, v_type, params, status)
            VALUES (%s, %s, %s, 'pending')
            RETURNING v_job_id
        """, (stock_code, v_type, json.dumps(params)))
        v_job_id = cur.fetchone()['v_job_id']
    
    # Update metrics
    from src.utils.metrics import BACKTEST_JOBS_TOTAL
    BACKTEST_JOBS_TOTAL.labels(stock_code=stock_code, type=v_type).inc()

    return RedirectResponse(url="/analytics/backtest/monitor", status_code=303)

@router.post("/backtest/run-daily")
async def run_daily_update_job(request: Request, stock_code: str = Form(...)):
    """특정 종목에 대해 즉시 경량 업데이트(DAILY_UPDATE)를 실행"""
    # Simply delegates to create_backtest_job with v_type=DAILY_UPDATE
    return await create_backtest_job(request, stock_code=stock_code, val_months=0, v_type="DAILY_UPDATE")

@router.post("/backtest/start/{v_job_id}")
async def start_backtest_job(request: Request, v_job_id: int):
    """등록된 작업을 시작"""
    from src.learner.awo_engine import AWOEngine
    
    with get_db_cursor() as cur:
        cur.execute("SELECT stock_code, params, v_type FROM tb_verification_jobs WHERE v_job_id = %s", (v_job_id,))
        job = cur.fetchone()
    
    if not job:
        return RedirectResponse(url="/analytics/backtest/monitor?error=not_found", status_code=303)
    
    stock_code = job['stock_code']
    params = job['params'] if isinstance(job['params'], dict) else json.loads(job['params'] or '{}')
    val_months = params.get('val_months', 1)
    v_type = job.get('v_type', 'AWO_SCAN')

    with get_db_cursor() as cur:
        # Check if any OTHER job is running for this stock
        cur.execute("SELECT v_job_id, v_type FROM tb_verification_jobs WHERE stock_code = %s AND status = 'running' AND v_job_id != %s", (stock_code, v_job_id))
        running_job = cur.fetchone()
        if running_job:
             msg = f"이미 해당 종목의 백테스트(#{running_job['v_job_id']}, {running_job['v_type']})가 실행 중입니다."
             if "HX-Request" in request.headers:
                 response = await get_backtest_row(request, v_job_id)
                 response.headers["HX-Trigger"] = json.dumps({"showToast": {"message": msg, "type": "error"}})
                 return response
             return HTMLResponse(content=f"<script>alert('{msg}');</script>")

        # Updated logic: We no longer update status to 'running' here.
        # The Verification Worker will set it to 'running' when it actualy starts processing.
        # This prevents 'Zombie Worker' alerts during MQ delivery lag.
        pass

    # Publish to Verification Worker
    publish_verification_job({
        "v_type": v_type,
        "stock_code": stock_code,
        "v_job_id": v_job_id,
        "val_months": val_months
    })

    if "HX-Request" in request.headers:
        import asyncio
        await asyncio.sleep(0.2) # Give a tiny bit of time for DB commit to propagate
        response = await get_backtest_row(request, v_job_id)
        response.headers["HX-Trigger"] = json.dumps({"showToast": {"message": f"Job #{v_job_id} started.", "type": "success"}})
        return response
    return RedirectResponse(url="/analytics/backtest/monitor", status_code=303)

@router.post("/backtest/stop/{v_job_id}")
async def stop_backtest_job(request: Request, v_job_id: int):
    """실행 중인 백테스트 작업 중단 (Status -> stopped)"""
    with get_db_cursor() as cur:
        cur.execute("UPDATE tb_verification_jobs SET status = 'stopped' WHERE v_job_id = %s", (v_job_id,))
    # Update row UI
    return await get_backtest_row(request, v_job_id)

@router.delete("/backtest/{v_job_id}")
async def delete_backtest_job(request: Request, v_job_id: int):
    """백테스트 작업 및 결과 삭제"""
    from src.utils.metrics import BACKTEST_PROGRESS
    with get_db_cursor() as cur:
        # Get labels before deletion to clean up Prometheus
        cur.execute("SELECT stock_code FROM tb_verification_jobs WHERE v_job_id = %s", (v_job_id,))
        row = cur.fetchone()
        if row:
            stock_code = row['stock_code']
            # Try removing metrics for both possible ID formats
            # Backtest IDs are usually str(v_job_id), Collection IDs are J{id}
            for label_id in [str(v_job_id), f"J{v_job_id}"]:
                try:
                    BACKTEST_PROGRESS.remove(label_id, stock_code)
                except:
                    pass
        
        # 1. Delete associated results first (FK cleanup if not cascading)
        cur.execute("DELETE FROM tb_verification_results WHERE v_job_id = %s", (v_job_id,))
        # 2. Delete checkpoints
        cur.execute("DELETE FROM tb_awo_checkpoints WHERE v_job_id = %s", (v_job_id,))
        # 3. Delete the job itself
        cur.execute("DELETE FROM tb_verification_jobs WHERE v_job_id = %s", (v_job_id,))
        
    return HTMLResponse(content="")

@router.get("/checkpoints/{v_job_id}")
async def get_awo_checkpoints(v_job_id: int):
    """AWO 스캔 중간 체크포인트 목록 반환 (부분 성공 복구용)"""
    from fastapi.responses import JSONResponse
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT id, stock_code, window_months, alpha, hit_rate, mae, status, created_at
            FROM tb_awo_checkpoints 
            WHERE v_job_id = %s 
            ORDER BY hit_rate DESC NULLS LAST
        """, (v_job_id,))
        checkpoints = cur.fetchall()
    
    return JSONResponse([dict(row) for row in checkpoints] if checkpoints else [])

@router.post("/checkpoints/promote/{checkpoint_id}")
async def promote_checkpoint(request: Request, checkpoint_id: int):
    """체크포인트의 윈도우/알파 설정으로 모델 프로모션"""
    from fastapi.responses import JSONResponse
    
    with get_db_cursor() as cur:
        # 1. Get checkpoint info
        cur.execute("""
            SELECT stock_code, window_months, alpha, hit_rate, mae 
            FROM tb_awo_checkpoints WHERE id = %s
        """, (checkpoint_id,))
        cp = cur.fetchone()
        
        if not cp:
            return JSONResponse({"error": "Checkpoint not found"}, status_code=404)
        
        stock_code = cp['stock_code']
        window_months = cp['window_months']
        alpha = float(cp['alpha'])
        
    # 2. Run promotion with backend engine
    try:
        from src.learner.awo_engine import AWOEngine
        engine = AWOEngine(stock_code)
        
        result = engine.promote_best_model(
            window_months=window_months, 
            alpha=alpha,
            metrics={
                "hit_rate": float(cp['hit_rate']) if cp['hit_rate'] else 0,
                "mae": float(cp['mae']) if cp['mae'] else 0,
                "source": "checkpoint_promotion"
            }
        )
        
        # 3. Update checkpoint status
        with get_db_cursor() as cur:
            cur.execute("""
                UPDATE tb_awo_checkpoints SET status = 'promoted' WHERE id = %s
            """, (checkpoint_id,))
        
        return JSONResponse({
            "success": True,
            "stock_code": stock_code,
            "window_months": window_months,
            "alpha": alpha,
            "promotion_result": result
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@router.get("/checkpoints/by_stock/{stock_code}")
async def get_checkpoints_by_stock(stock_code: str):
    """특정 종목의 모든 체크포인트 목록 (Job 실패해도 조회 가능)"""
    from fastapi.responses import JSONResponse
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT c.id, c.v_job_id, c.window_months, c.alpha, c.hit_rate, c.mae, c.status, c.created_at
            FROM tb_awo_checkpoints c
            WHERE c.stock_code = %s
            ORDER BY c.created_at DESC
            LIMIT 50
        """, (stock_code,))
        checkpoints = cur.fetchall()
    
    return JSONResponse([dict(row) for row in checkpoints] if checkpoints else [])


@router.post("/backtest/restart/{v_job_id}")
async def restart_backtest_job(request: Request, v_job_id: int):
    """실패하거나 중단된 백테스트 재시작"""
    with get_db_cursor() as cur:
        cur.execute("""
            UPDATE tb_verification_jobs 
            SET status = 'pending', progress = 0, started_at = NULL, completed_at = NULL, 
                worker_id = NULL, error_message = NULL, result_summary = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE v_job_id = %s
        """, (v_job_id,))
    
    # Re-trigger the start logic
    return await start_backtest_job(request, v_job_id)

@router.get("/backtest/report/{v_job_id}", response_class=HTMLResponse)
async def view_backtest_report(request: Request, v_job_id: int):
    """백테스팅 결과 상세 레포트"""
    from src.dashboard.app import templates
    with get_db_cursor() as cur:
        cur.execute("SELECT * FROM tb_verification_jobs WHERE v_job_id = %s", (v_job_id,))
        job = cur.fetchone()
        cur.execute("SELECT * FROM tb_verification_results WHERE v_job_id = %s ORDER BY target_date ASC", (v_job_id,))
        results = cur.fetchall()
        
    return templates.TemplateResponse("quant/report.html", {
        "request": request,
        "job": job,
        "results": results
    })

@router.get("/grounding/{stock_code}/{date}/{word}")
async def get_evidence_grounding(stock_code: str, date: str, word: str):
    """특정 날짜, 특정 단어가 포함된 실제 뉴스 헤드라인 리스트 반환"""
    # word가 word_L1 형식이라면 word만 추출
    base_word = word.rsplit('_L', 1)[0] if '_L' in word else word
    
    with get_db_cursor() as cur:
        # 해당 일자(date) 뉴스 중 base_word를 포함하는 본문/제목 조회
        cur.execute("""
            SELECT c.title, u.url, c.published_at
            FROM tb_news_content c
            JOIN tb_news_url u ON c.url_hash = u.url_hash
            JOIN tb_news_mapping m ON c.url_hash = m.url_hash
            WHERE m.stock_code = %s 
              AND c.published_at::date = %s
              AND (c.title ILIKE %s OR c.content ILIKE %s)
            ORDER BY c.published_at DESC
            LIMIT 10
        """, (stock_code, date, f"%{base_word}%", f"%{base_word}%"))
        news = cur.fetchall()
        
    return {
        "stock_code": stock_code,
        "date": date,
        "word": word,
        "news": [
            {
                "title": n['title'],
                "url": n['url'],
                "published_at": (
                    n['published_at'].strftime('%Y-%m-%d') 
                    if n['published_at'].hour == 0 and n['published_at'].minute == 0 
                    else n['published_at'].strftime('%Y-%m-%d %H:%M')
                ) if n['published_at'] else ""
            } for n in news
        ]
    }

@router.get("/word_detail/{stock_code}/{word}")
async def get_word_detail(stock_code: str, word: str):
    """단어의 백테스트 검증 데이터 및 히스토리 반환"""
    from src.dashboard.data_helpers import get_word_verification_data
    with get_db_cursor() as cur:
        data = get_word_verification_data(cur, stock_code, word)
    return data

@router.get("/top-signals", response_class=HTMLResponse)
async def get_top_signals(request: Request):
    from src.dashboard.app import templates
    with get_db_cursor() as cur:
        # Get latest predictions for all stocks that have predictions
        cur.execute("""
            SELECT DISTINCT ON (p.stock_code) 
                p.stock_code, m.stock_name, p.intensity, p.status, p.expected_alpha, p.sentiment_score,
                dt.optimal_window_months, dt.optimal_alpha
            FROM tb_predictions p
            JOIN tb_stock_master m ON p.stock_code = m.stock_code
            LEFT JOIN daily_targets dt ON p.stock_code = dt.stock_code
            WHERE p.status IS NOT NULL AND p.expected_alpha IS NOT NULL
            ORDER BY p.stock_code, p.created_at DESC
        """)
        latest = cur.fetchall()
        
        # Sort by status priority (Strong Buy/Sell first)
        priority = {
            'Strong Buy': 0,
            'Strong Sell': 1,
            'Cautious Buy': 2,
            'Cautious Sell': 3,
            'Mixed': 4,
            'Observation': 5
        }
        latest.sort(key=lambda x: priority.get(x['status'], 99))
        
        return templates.TemplateResponse("partials/top_signals_widget.html", {
            "request": request,
            "signals": latest[:5]
        })
@router.get("/api/news")
async def get_news_by_date(request: Request, stock_code: str, date: str):
    """
    Evidence-based news drill-down API.
    Shows past news that influenced the prediction for the selected date.
    """
    import math
    from src.predictor.scoring import Predictor
    from src.nlp.tokenizer import Tokenizer
    from src.utils.calendar import Calendar
    
    try:
        predictor = Predictor()
        tokenizer = Tokenizer()
        
        # 1. Parse target date (D-Day)
        try:
            target_date = datetime.strptime(date, '%Y-%m-%d').date()
        except:
            return {"error": "Invalid date format"}

        # 1.5 Check for persisted evidence in DB (Fast & Consistent)
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT evidence FROM tb_predictions 
                WHERE stock_code = %s AND prediction_date = %s
            """, (stock_code, target_date))
            row = cur.fetchone()
            
            if row and row['evidence']:
                evidence_json = row['evidence']
                evidence = evidence_json if isinstance(evidence_json, list) else json.loads(evidence_json)
                
                # Verify format
                if isinstance(evidence, list):
                    formatted_news = []
                    for e in evidence:
                        formatted_news.append({
                            "title": e.get('title', ''),
                            "summary": e.get('title', ''),
                            "url": e.get('url', ''),
                            "score": e.get('score', 0),
                            "lag": e.get('lag', 0),
                            "abs_score": e.get('abs_score', 0),
                            "published_at": e.get('published_at', '')
                        })
                    return {
                        "stock_code": stock_code,
                        "date": date,
                        "news": formatted_news
                    }

        # 2. Load active dictionaries (Fallback)
        main_dict = predictor.load_active_dict(stock_code, 'Main')
        buffer_dict = predictor.load_active_dict(stock_code, 'Buffer')
        score_map = main_dict.copy()
        for word, beta in buffer_dict.items():
            score_map[word] = score_map.get(word, 0.0) + beta

        # 3. Find Trading Windows for Lags 1-5
        trading_days = Calendar.get_trading_days(stock_code)
        idx = -1
        for i, d in enumerate(trading_days):
            if d == target_date:
                idx = i
                break
                
        # Fallback for future dates not yet in tb_daily_price
        if idx == -1:
            if trading_days:
                # Assume target_date is the "next" impact target
                idx = len(trading_days)  # virtual index
                # We need a virtual trading_days list including target_date
                full_trading_days = trading_days + [target_date]
            else:
                full_trading_days = [target_date]
                idx = 0
        else:
            full_trading_days = trading_days

        # Get optimal lag for this stock
        optimal_lag = 5  # Default fallback
        with get_db_cursor() as cur_lag:
            cur_lag.execute("SELECT optimal_lag FROM daily_targets WHERE stock_code = %s", (stock_code,))
            lag_row = cur_lag.fetchone()
            if lag_row and lag_row['optimal_lag']:
                optimal_lag = int(lag_row['optimal_lag'])

        from src.utils.report_helper import ReportHelper
        evidence = ReportHelper.get_evidence_news(stock_code, date, score_map)
        
        # Format for frontend
        formatted_news = []
        for e in evidence:
            formatted_news.append({
                "title": e['title'],
                "summary": e['title'], # Simplified for modal
                "url": e['url'],
                "score": e['score'],
                "lag": e['lag'],
                "abs_score": e['abs_score'],
                "published_at": e.get('published_at', '')
            })

        return {
            "stock_code": stock_code,
            "date": date,
            "news": formatted_news
        }
    except Exception as e:
        import logging
        logging.error(f"Error in get_news_by_date: {str(e)}")
        return {"error": str(e), "news": []}
