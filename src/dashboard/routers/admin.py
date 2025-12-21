# src/dashboard/routers/admin.py
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from src.db.connection import get_db_cursor
from src.dashboard.data_helpers import (
    get_jobs_data, get_stock_stats_data, get_overall_stats, get_chart_data
)
from src.utils.stock_info import get_stock_name
from datetime import datetime
import json

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    from src.utils.mq import get_active_worker_count
    from src.dashboard.app import templates, START_TIME
    
    with get_db_cursor() as cur:
        jobs = get_jobs_data(cur)
        stock_stats = get_stock_stats_data(cur)
        stats = get_overall_stats(cur)
        chart_data = get_chart_data(cur)
    
    active_workers = get_active_worker_count()
    
    uptime_str = "0:00:00"
    delta = datetime.now() - START_TIME
    uptime_str = str(delta).split('.')[0]
        
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "jobs": jobs, 
        "targets": stock_stats,
        "stats": stats,
        "chart_data": chart_data,
        "active_workers": active_workers,
        "uptime": uptime_str
    })

@router.get("/jobs/list", response_class=HTMLResponse)
async def list_jobs(request: Request):
    from src.dashboard.app import templates
    with get_db_cursor() as cur:
        jobs = get_jobs_data(cur)
    return templates.TemplateResponse("partials/job_list.html", {"request": request, "jobs": jobs})

@router.get("/targets/list", response_class=HTMLResponse)
async def list_targets(request: Request):
    from src.dashboard.app import templates
    with get_db_cursor() as cur:
        targets = get_stock_stats_data(cur)
    return templates.TemplateResponse("partials/stock_list.html", {"request": request, "targets": targets})

@router.get("/errors/list", response_class=HTMLResponse)
async def list_errors(request: Request):
    from src.dashboard.app import templates
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT e.*, u.url 
            FROM tb_news_errors e
            JOIN tb_news_url u ON e.url_hash = u.url_hash
            ORDER BY e.occurred_at DESC 
            LIMIT 50
        """)
        errors = cur.fetchall()
    return templates.TemplateResponse("partials/error_list.html", {"request": request, "errors": errors})

@router.post("/jobs/stop/{job_id}")
async def stop_job(request: Request, job_id: int):
    from src.collector.news import JobManager
    from src.dashboard.app import templates
    manager = JobManager()
    manager.stop_job(job_id)
    
    if "HX-Request" in request.headers:
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM jobs WHERE job_id = %s", (job_id,))
            job = cur.fetchone()
        return templates.TemplateResponse("partials/job_list.html", {"request": request, "jobs": [job]})
    
    return RedirectResponse(url="/", status_code=303)

@router.post("/jobs/delete/{job_id}")
async def delete_job(request: Request, job_id: int):
    with get_db_cursor() as cur:
        cur.execute("DELETE FROM jobs WHERE job_id = %s", (job_id,))
    
    if "HX-Request" in request.headers:
        return HTMLResponse(content="")
        
    return RedirectResponse(url="/", status_code=303)

@router.delete("/jobs/finished")
async def delete_finished_jobs(request: Request):
    from src.dashboard.app import templates
    with get_db_cursor() as cur:
        cur.execute("DELETE FROM jobs WHERE status IN ('completed', 'failed')")
        jobs = get_jobs_data(cur)
    return templates.TemplateResponse("partials/job_list.html", {"request": request, "jobs": jobs})

@router.delete("/jobs/{job_id}")
async def delete_job_api(request: Request, job_id: int):
    with get_db_cursor() as cur:
        cur.execute("DELETE FROM jobs WHERE job_id = %s", (job_id,))
    return HTMLResponse(content="")

@router.delete("/errors/all")
async def clear_all_errors(request: Request):
    from src.dashboard.app import templates
    with get_db_cursor() as cur:
        cur.execute("DELETE FROM tb_news_errors")
    return templates.TemplateResponse("partials/error_list.html", {"request": request, "errors": []})

@router.post("/errors/retry/{url_hash}")
async def retry_error(request: Request, url_hash: str):
    from src.utils.mq import get_mq_channel, QUEUE_NAME
    
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT u.url, m.stock_code 
            FROM tb_news_url u
            LEFT JOIN tb_news_mapping m ON u.url_hash = m.url_hash
            WHERE u.url_hash = %s
        """, (url_hash,))
        data = cur.fetchone()
        
        if not data:
            return HTMLResponse(content="URL not found", status_code=404)
        cur.execute("UPDATE tb_news_url SET status = 'pending' WHERE url_hash = %s", (url_hash,))
        cur.execute("DELETE FROM tb_news_errors WHERE url_hash = %s", (url_hash,))
        
    connection, channel = get_mq_channel(QUEUE_NAME)
    try:
        message = {
            "url": data["url"],
            "url_hash": url_hash,
            "stock_code": data["stock_code"]
        }
        import pika
        channel.basic_publish(
            exchange='',
            routing_key=QUEUE_NAME,
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2)
        )
    finally:
        connection.close()
        
    return await list_errors(request)

@router.post("/targets/activate/{stock_code}")
async def activate_target(request: Request, stock_code: str):
    from src.dashboard.app import templates
    with get_db_cursor() as cur:
        cur.execute("""
            INSERT INTO daily_targets (stock_code, status, activation_requested_at, started_at) 
            VALUES (%s, 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (stock_code) DO UPDATE SET 
            status = 'active',
            activation_requested_at = EXCLUDED.activation_requested_at,
            started_at = EXCLUDED.started_at
        """, (stock_code,))
        
    if "HX-Request" in request.headers:
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT 
                    sm.stock_code, sm.stock_name, dt.status as target_status, dt.auto_activate_daily, dt.started_at,
                    MIN(COALESCE(nc.published_at::date, nu.published_at_hint)) as min_date,
                    MAX(COALESCE(nc.published_at::date, nu.published_at_hint)) as max_date,
                    COUNT(nu.url_hash) as url_count,
                    COUNT(nc.url_hash) as body_count
                FROM daily_targets dt
                INNER JOIN tb_stock_master sm ON dt.stock_code = sm.stock_code
                LEFT JOIN tb_news_mapping nm ON sm.stock_code = nm.stock_code
                LEFT JOIN tb_news_url nu ON nm.url_hash = nu.url_hash
                LEFT JOIN tb_news_content nc ON nu.url_hash = nc.url_hash
                WHERE sm.stock_code = %s
                GROUP BY sm.stock_code, sm.stock_name, dt.status, dt.auto_activate_daily, dt.started_at
            """, (stock_code,))
            target = cur.fetchone()
        return templates.TemplateResponse("partials/stock_list.html", {"request": request, "targets": [target]})
    return RedirectResponse(url="/", status_code=303)

@router.post("/targets/pause/{stock_code}")
async def pause_target(request: Request, stock_code: str):
    from src.dashboard.app import templates
    with get_db_cursor() as cur:
        cur.execute("UPDATE daily_targets SET status = 'paused' WHERE stock_code = %s", (stock_code,))
        
    if "HX-Request" in request.headers:
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT 
                    sm.stock_code, sm.stock_name, dt.status as target_status, dt.auto_activate_daily, dt.started_at,
                    MIN(COALESCE(nc.published_at::date, nu.published_at_hint)) as min_date,
                    MAX(COALESCE(nc.published_at::date, nu.published_at_hint)) as max_date,
                    COUNT(nu.url_hash) as url_count,
                    COUNT(nc.url_hash) as body_count
                FROM daily_targets dt
                INNER JOIN tb_stock_master sm ON dt.stock_code = sm.stock_code
                LEFT JOIN tb_news_mapping nm ON sm.stock_code = nm.stock_code
                LEFT JOIN tb_news_url nu ON nm.url_hash = nu.url_hash
                LEFT JOIN tb_news_content nc ON nu.url_hash = nc.url_hash
                WHERE sm.stock_code = %s
                GROUP BY sm.stock_code, sm.stock_name, dt.status, dt.auto_activate_daily, dt.started_at
            """, (stock_code,))
            target = cur.fetchone()
        return templates.TemplateResponse("partials/stock_list.html", {"request": request, "targets": [target]})
    return RedirectResponse(url="/", status_code=303)

@router.delete("/targets/{stock_code}")
async def delete_target(request: Request, stock_code: str):
    with get_db_cursor() as cur:
        cur.execute("DELETE FROM daily_targets WHERE stock_code = %s", (stock_code,))
    return HTMLResponse(content="")

@router.post("/targets/toggle_auto_activate/{stock_code}")
async def toggle_auto_activate(request: Request, stock_code: str):
    from src.dashboard.app import templates
    with get_db_cursor() as cur:
        cur.execute("UPDATE daily_targets SET auto_activate_daily = NOT auto_activate_daily WHERE stock_code = %s", (stock_code,))
        
    if "HX-Request" in request.headers:
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT 
                    sm.stock_code, sm.stock_name, dt.status as target_status, dt.auto_activate_daily, dt.started_at,
                    MIN(COALESCE(nc.published_at::date, nu.published_at_hint)) as min_date,
                    MAX(COALESCE(nc.published_at::date, nu.published_at_hint)) as max_date,
                    COUNT(nu.url_hash) as url_count,
                    COUNT(nc.url_hash) as body_count
                FROM daily_targets dt
                INNER JOIN tb_stock_master sm ON dt.stock_code = sm.stock_code
                LEFT JOIN tb_news_mapping nm ON sm.stock_code = nm.stock_code
                LEFT JOIN tb_news_url nu ON nm.url_hash = nu.url_hash
                LEFT JOIN tb_news_content nc ON nu.url_hash = nc.url_hash
                WHERE sm.stock_code = %s
                GROUP BY sm.stock_code, sm.stock_name, dt.status, dt.auto_activate_daily, dt.started_at
            """, (stock_code,))
            target = cur.fetchone()
        return templates.TemplateResponse("partials/stock_list.html", {"request": request, "targets": [target]})
    return RedirectResponse(url="/", status_code=303)

@router.post("/targets/add")
async def add_target(request: Request, stock_code: str = Form(...), backfill_days: int = Form(365), auto_activate: bool = Form(False)):
    from src.collector.news import JobManager
    from src.dashboard.app import templates
    manager = JobManager()
    
    with get_db_cursor() as cur:
        cur.execute("SELECT stock_name FROM tb_stock_master WHERE stock_code = %s", (stock_code,))
        if not cur.fetchone():
            stock_name = get_stock_name(stock_code)
            cur.execute(
                "INSERT INTO tb_stock_master (stock_code, stock_name, market_type) VALUES (%s, %s, 'KOSPI') ON CONFLICT DO NOTHING",
                (stock_code, stock_name)
            )
        cur.execute(
            """INSERT INTO daily_targets (stock_code, status, auto_activate_daily) 
               VALUES (%s, 'pending', %s) 
               ON CONFLICT (stock_code) DO UPDATE SET 
               status = 'pending', auto_activate_daily = EXCLUDED.auto_activate_daily""",
            (stock_code, auto_activate)
        )
    manager.create_backfill_job(stock_code, backfill_days)
    
    if "HX-Request" in request.headers:
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT 
                    sm.stock_code, sm.stock_name, dt.status as target_status, dt.auto_activate_daily, dt.started_at,
                    MIN(COALESCE(nc.published_at::date, nu.published_at_hint)) as min_date,
                    MAX(COALESCE(nc.published_at::date, nu.published_at_hint)) as max_date,
                    COUNT(nu.url_hash) as url_count,
                    COUNT(nc.url_hash) as body_count
                FROM daily_targets dt
                INNER JOIN tb_stock_master sm ON dt.stock_code = sm.stock_code
                LEFT JOIN tb_news_mapping nm ON sm.stock_code = nm.stock_code
                LEFT JOIN tb_news_url nu ON nm.url_hash = nu.url_hash
                LEFT JOIN tb_news_content nc ON nu.url_hash = nc.url_hash
                WHERE sm.stock_code = %s
                GROUP BY sm.stock_code, sm.stock_name, dt.status, dt.auto_activate_daily, dt.started_at
            """, (stock_code,))
            target = cur.fetchone()
        return templates.TemplateResponse("partials/stock_list.html", {"request": request, "targets": [target]})
    return RedirectResponse(url="/", status_code=303)

@router.get("/errors", response_class=HTMLResponse)
async def view_errors(request: Request):
    from src.dashboard.app import templates
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT e.*, u.url 
            FROM tb_news_errors e
            JOIN tb_news_url u ON e.url_hash = u.url_hash
            ORDER BY e.occurred_at DESC 
            LIMIT 50
        """)
        errors = cur.fetchall()
        cur.execute("SELECT count(*) as cnt FROM tb_news_errors")
        total_errors = cur.fetchone()['cnt']
        
    return templates.TemplateResponse("errors.html", {
        "request": request, 
        "errors": errors,
        "total_errors": total_errors
    })

@router.post("/jobs/backfill")
async def create_backfill(stock_code: str = Form(...), days: int = Form(...)):
    from src.collector.news import JobManager
    manager = JobManager()
    manager.create_backfill_job(stock_code, days)
    return RedirectResponse(url="/", status_code=303)

@router.get("/api/stats/distribution")
async def get_distribution_stats():
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT 
                m.stock_code,
                u.published_at_hint as pub_date,
                COUNT(*) as count
            FROM tb_news_url u
            JOIN tb_news_mapping m ON u.url_hash = m.url_hash
            WHERE u.published_at_hint >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY m.stock_code, u.published_at_hint
            ORDER BY u.published_at_hint ASC, m.stock_code ASC
        """)
        rows = cur.fetchall()
        dates = sorted(list(set(r['pub_date'].strftime('%Y-%m-%d') for r in rows if r['pub_date'])))
        stocks = sorted(list(set(r['stock_code'] for r in rows)))
        datasets = []
        for i, s in enumerate(stocks):
            data_map = {r['pub_date'].strftime('%Y-%m-%d'): r['count'] for r in rows if r['stock_code'] == s}
            color = f"hsla({(i * 137) % 360}, 70%, 50%, 0.6)"
            datasets.append({
                "label": s,
                "data": [data_map.get(d, 0) for d in dates],
                "backgroundColor": color
            })
        return {"labels": dates, "datasets": datasets}
