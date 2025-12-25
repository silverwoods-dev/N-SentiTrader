# src/dashboard/routers/admin.py
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from src.utils.docker_control import restart_all_workers, get_container_logs, restart_container
from src.db.connection import get_db_cursor
from src.dashboard.data_helpers import (
    get_jobs_data, get_stock_stats_data, get_overall_stats, get_chart_data,
    get_collection_metrics, get_active_workers_list, get_system_health, get_system_events
)

from src.utils.stock_info import get_stock_name
from datetime import datetime, timedelta
import json
# ... imports ...


router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    from src.utils.mq import get_active_worker_count, get_queue_depths
    from src.dashboard.app import templates, START_TIME
    
    with get_db_cursor() as cur:
        jobs = get_jobs_data(cur)
        stock_stats = get_stock_stats_data(cur)
        overall_stats = get_overall_stats(cur)
        collection_metrics = get_collection_metrics(cur)
        chart_data = get_chart_data(cur)
        worker_list = get_active_workers_list(cur)
        system_health = get_system_health(cur)
        system_events = get_system_events(cur, limit=20)
    
    active_workers = get_active_worker_count()
    queue_depths = get_queue_depths()
    # queue_depths is now {q_name: {'total': X, 'ready': Y, 'unacked': Z}}
    total_queue = sum(info['total'] for info in queue_depths.values())
    
    uptime_str = "0:00:00"
    delta = datetime.now() - START_TIME
    uptime_str = str(delta).split('.')[0]
        
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "jobs": jobs, 
        "targets": stock_stats,
        "stats": overall_stats,
        "collection_metrics": collection_metrics,
        "chart_data": chart_data,
        "active_workers": active_workers, # This relies on RabbitMQ which is fine
        "worker_details": worker_list,    # New detailed list from DB
        "total_queue": total_queue,
        "uptime": uptime_str,
        "system_health": system_health,
        "system_events": system_events
    })

@router.post("/system/restart_workers")
async def restart_workers():
    results = restart_all_workers()
    success_count = sum(1 for v in results.values() if v)
    
    # Log action
    try:
        from src.dashboard.data_helpers import log_system_event
        with get_db_cursor() as cur:
            msg = f"User manually triggered worker restart. Success: {success_count}/{len(results)}"
            log_system_event(cur, "ACTION", "INFO", "admin", msg, results)
    except Exception as e:
        print(f"Failed to log action: {e}")

    if success_count > 0:
        return JSONResponse({"status": "success", "msg": f"Restarted {success_count} workers", "details": results})
    else:
        return JSONResponse({"status": "error", "msg": "Failed to restart workers", "details": results}, status_code=500)

@router.get("/jobs/list", response_class=HTMLResponse)
async def list_jobs(request: Request):
    from src.dashboard.app import templates
    with get_db_cursor() as cur:
        jobs = get_jobs_data(cur)
    return templates.TemplateResponse("partials/job_list.html", {"request": request, "jobs": jobs})

@router.get("/targets/list", response_class=HTMLResponse)
async def list_targets(request: Request, q: str = None, status_filter: str = None):
    from src.dashboard.app import templates
    with get_db_cursor() as cur:
        targets = get_stock_stats_data(cur, q=q, status_filter=status_filter)
    return templates.TemplateResponse("partials/stock_list.html", {"request": request, "targets": targets})

@router.post("/targets/bulk")
async def bulk_targets(request: Request):
    from pydantic import BaseModel
    from typing import List
    
    class BulkAction(BaseModel):
        action: str
        stock_codes: List[str]
        
    data = await request.json()
    action = data.get("action")
    stock_codes = data.get("stock_codes", [])
    
    if not stock_codes:
        return {"status": "ok", "count": 0}
        
    with get_db_cursor() as cur:
        if action == "activate":
            cur.execute("""
                UPDATE daily_targets 
                SET status = 'active', started_at = CURRENT_TIMESTAMP 
                WHERE stock_code = ANY(%s)
            """, (stock_codes,))
        elif action == "pause":
            cur.execute("UPDATE daily_targets SET status = 'paused' WHERE stock_code = ANY(%s)", (stock_codes,))
        elif action == "delete":
            cur.execute("DELETE FROM daily_targets WHERE stock_code = ANY(%s)", (stock_codes,))
            
    return {"status": "ok", "count": len(stock_codes)}

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

@router.post("/jobs/run_daily")
async def run_daily(request: Request):
    from src.collector.news import JobManager
    from src.dashboard.app import templates
    manager = JobManager()
    manager.start_daily_jobs()
    
    with get_db_cursor() as cur:
        jobs = get_jobs_data(cur)
    
    response = templates.TemplateResponse("partials/job_list.html", {"request": request, "jobs": jobs})
    response.headers["HX-Trigger"] = json.dumps({"showToast": {"message": "Daily collection pipeline triggered manually.", "type": "success"}})
    return response

@router.post("/jobs/restart/{job_id}")
async def restart_job(request: Request, job_id: int):
    from src.utils.mq import publish_job, publish_daily_job
    from src.dashboard.app import templates
    
    with get_db_cursor() as cur:
        cur.execute("SELECT * FROM jobs WHERE job_id = %s", (job_id,))
        job = cur.fetchone()
        
        if not job:
            return HTMLResponse(content="Job not found", status_code=404)
        
        # Reset job state
        cur.execute("""
            UPDATE jobs 
            SET status = 'pending', progress = 0, message = 'Restarted by user', 
                started_at = NULL, completed_at = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE job_id = %s
        """, (job_id,))
        
        # Re-publish to MQ
        params = job['params']
        if isinstance(params, str):
            params = json.loads(params)
        
        params['job_id'] = job_id
        
        if job['job_type'] == 'daily':
            publish_daily_job(params)
        else:
            if 'tasks' in params:
                for key, task in params['tasks'].items():
                    publish_data = {
                        **params,
                        "job_id": job_id,
                        "task_key": key,
                        "direction": task["direction"],
                        "days": task["days"],
                        "offset": task["offset"]
                    }
                    publish_job(publish_data)
            else:
                publish_job(params)
            
    if "HX-Request" in request.headers:
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM jobs WHERE job_id = %s", (job_id,))
            updated_job = cur.fetchone()
        return templates.TemplateResponse("partials/job_list.html", {"request": request, "jobs": [updated_job]})
        
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
            targets = get_stock_stats_data(cur, stock_code)
        return templates.TemplateResponse("partials/stock_list.html", {"request": request, "targets": targets})
    return RedirectResponse(url="/", status_code=303)

@router.post("/targets/pause/{stock_code}")
async def pause_target(request: Request, stock_code: str):
    from src.dashboard.app import templates
    with get_db_cursor() as cur:
        cur.execute("UPDATE daily_targets SET status = 'paused' WHERE stock_code = %s", (stock_code,))
        
    if "HX-Request" in request.headers:
        with get_db_cursor() as cur:
            targets = get_stock_stats_data(cur, stock_code)
        return templates.TemplateResponse("partials/stock_list.html", {"request": request, "targets": targets})
    return RedirectResponse(url="/", status_code=303)

@router.post("/targets/backfill/{stock_code}")
async def trigger_backfill(request: Request, stock_code: str):
    from src.collector.news import JobManager
    from src.dashboard.app import templates
    
    manager = JobManager()
    manager.create_backfill_job(stock_code, 365)
        
    if "HX-Request" in request.headers:
        with get_db_cursor() as cur:
            jobs = get_jobs_data(cur)
        return templates.TemplateResponse("partials/job_list.html", {"request": request, "jobs": jobs})
    
    return RedirectResponse(url="/", status_code=303)
        
    if "HX-Request" in request.headers:
        with get_db_cursor() as cur:
            jobs = get_jobs_data(cur)
        return templates.TemplateResponse("partials/job_list.html", {"request": request, "jobs": jobs})
        
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
            targets = get_stock_stats_data(cur, stock_code)
        return templates.TemplateResponse("partials/stock_list.html", {"request": request, "targets": targets})
    return RedirectResponse(url="/", status_code=303)

@router.post("/targets/add")
async def add_target(request: Request):
    from src.dashboard.app import templates
    form = await request.form()
    stock_code = form.get("stock_code")
    backfill_days = int(form.get("backfill_days", 365))
    auto_activate = form.get("auto_activate") == "true"
    
    backfill_until = datetime.now() - timedelta(days=backfill_days)
    
    backfill_until = datetime.now() - timedelta(days=backfill_days)
    name = "Unknown"
    
    # 1. Update stock master if name invalid/unknown (Outside main target transaction)
    try:
        name = get_stock_name(stock_code)
        with get_db_cursor() as cur:
            cur.execute("""
                INSERT INTO tb_stock_master (stock_code, stock_name, market_type)
                VALUES (%s, %s, 'KOSPI')
                ON CONFLICT (stock_code) DO NOTHING
            """, (stock_code, name))
    except Exception:
        pass

    # 2. Insert target and daily job placeholder
    with get_db_cursor() as cur:
        cur.execute("""
            INSERT INTO daily_targets (stock_code, status, auto_activate_daily, backfill_until)
            VALUES (%s, 'active', %s, %s)
            ON CONFLICT (stock_code) DO UPDATE SET
                status = 'active',
                auto_activate_daily = EXCLUDED.auto_activate_daily,
                backfill_until = EXCLUDED.backfill_until,
                activation_requested_at = CURRENT_TIMESTAMP
        """, (stock_code, auto_activate, backfill_until))
        
        daily_params = {
            "stock_code": stock_code,
            "stock_name": name,
            "job_type": "daily"
        }
        
        cur.execute("""
            INSERT INTO jobs (job_type, params, status, message, created_at)
            VALUES ('daily', %s, 'stopped', 'Registered via Add Target. Click Restart to run manually.', CURRENT_TIMESTAMP)
        """, (json.dumps(daily_params),))
        
    # 3. Create and Trigger initial backfill job using Manager (OUTSIDE transaction)
    try:
        from src.collector.news import JobManager
        manager = JobManager()
        manager.create_backfill_job(stock_code, backfill_days)
    except Exception as e:
        print(f"Error creating backfill job: {e}")

    # 4. Fetch updated list
    with get_db_cursor() as cur:
        targets = get_stock_stats_data(cur, stock_code)
        
    response = templates.TemplateResponse("partials/stock_list.html", {"request": request, "targets": targets})
    # Add success trigger for toast
    response.headers["HX-Trigger"] = json.dumps({"showToast": {"message": f"Deploying collection job for {stock_code}.", "type": "success"}})
    return response

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

@router.get("/targets/search", response_class=HTMLResponse)
async def search_stocks(request: Request, q: str = "", stock_code: str = ""):
    from src.dashboard.app import templates
    search_q = q or stock_code
    if not search_q or len(search_q) < 2:
        return HTMLResponse(content="")
    
    with get_db_cursor() as cur:
        # Search in DB first
        cur.execute("""
            SELECT stock_code, stock_name, market_type 
            FROM tb_stock_master 
            WHERE stock_code LIKE %s OR stock_name LIKE %s
            LIMIT 5
        """, (f"%{search_q}%", f"%{search_q}%"))
        results = cur.fetchall()
        
        # If no results and looks like a code (6 digits), try fetching from Naver
        if not results and search_q.isdigit() and len(search_q) == 6:
            try:
                name = get_stock_name(search_q)
                if name and name != "Unknown":
                    results = [{"stock_code": search_q, "stock_name": name, "market_type": "KOSPI"}]
            except:
                pass
                
    return templates.TemplateResponse("partials/stock_search_results.html", {
        "request": request,
        "results": results
    })

@router.get("/global-search", response_class=HTMLResponse)
async def global_search(request: Request, q: str = ""):
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
                
    return templates.TemplateResponse("partials/global_search_results.html", {
        "request": request,
        "results": results
    })

@router.post("/system/restart/{container_id}", response_class=JSONResponse)
async def restart_single_container(container_id: str):
    success = restart_container(container_id)
    if success:
        # Log action
        try:
            from src.dashboard.data_helpers import log_system_event
            with get_db_cursor() as cur:
                log_system_event(cur, "ACTION", "INFO", "admin", f"User manually restarted container: {container_id}", {"success": True})
        except: pass
        return JSONResponse({"status": "success", "msg": f"Container {container_id} restarted"})
    else:
        return JSONResponse({"status": "error", "msg": "Failed to restart container"}, status_code=500)
@router.get("/system/logs", response_class=HTMLResponse)
async def view_ops_logs(request: Request):
    from src.dashboard.app import templates
    return templates.TemplateResponse("ops_logs.html", {"request": request})

@router.get("/system/containers", response_class=JSONResponse)
async def list_containers():
    # Hardcoded for now as per plan, could be dynamic via Docker API
    workers = [
        {"id": "n_senti_verification_worker", "name": "Verification Worker"},
        {"id": "n_senti_address_worker_1", "name": "Address Worker 1"},
        {"id": "n_senti_address_worker_2", "name": "Address Worker 2"},
        {"id": "n_senti_daily_address_worker", "name": "Daily Address Worker"},
        {"id": "n_senti_body_worker_1", "name": "Body Worker 1"},
        {"id": "n_senti_body_worker_2", "name": "Body Worker 2"},
    ]
    return {"containers": workers}

@router.get("/system/logs/{container_id}", response_class=HTMLResponse)
async def get_logs_html(request: Request, container_id: str, tail: int = 200):
    logs = get_container_logs(container_id, tail=tail)
    # Simple ANSI to HTML (Basic colors)
    # In a real app, use a lib like 'ansi2html', but for a custom revamp we can do basic regex or just wrap in <pre>
    return HTMLResponse(content=f"<pre class='terminal-content'>{logs}</pre>")
