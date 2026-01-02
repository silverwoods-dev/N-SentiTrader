# src/dashboard/app.py
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from datetime import datetime
from src.utils.metrics import start_metrics_server
from src.dashboard.routers import admin, quant
from src.dashboard.filters import format_kst
import json

def from_json(value):
    if isinstance(value, str):
        return json.loads(value)
    return value

app = FastAPI(title="N-SentiTrader Dashboard")

# Global START_TIME for uptime calculation
START_TIME = datetime.now()

@app.on_event("startup")
async def startup_event():
    start_metrics_server()
    # Start background task for updating backtest metrics
    import asyncio
    asyncio.create_task(update_backtest_metrics_loop())

async def update_backtest_metrics_loop():
    """Background task to update aggregate backtest metrics every 10 seconds"""
    import asyncio
    from src.db.connection import get_db_cursor
    from src.utils.metrics import (
        BACKTEST_JOBS_RUNNING,
        BACKTEST_JOBS_BY_STATUS
    )
    
    while True:
        try:
            with get_db_cursor() as cur:
                # Count jobs by status
                cur.execute("""
                    SELECT status, COUNT(*) as count
                    FROM tb_verification_jobs
                    GROUP BY status
                """)
                status_counts = {row['status']: row['count'] for row in cur.fetchall()}
                
                # Update gauges for aggregate view
                for status in ['pending', 'running', 'completed', 'failed', 'stopped']:
                    count = status_counts.get(status, 0)
                    BACKTEST_JOBS_BY_STATUS.labels(status=status).set(count)
                
                BACKTEST_JOBS_RUNNING.set(status_counts.get('running', 0))
                
        except Exception as e:
            print(f"Error updating aggregate backtest metrics: {e}")
        
        await asyncio.sleep(10)

templates = Jinja2Templates(directory="src/dashboard/templates")

# Register Filters
templates.env.filters["kst"] = format_kst
templates.env.filters["from_json"] = from_json

# Register Globals
from datetime import timedelta
templates.env.globals.update(timedelta=timedelta, min=min, max=max)

# Include Routers
app.include_router(admin.router)
app.include_router(quant.router)

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8081))
    uvicorn.run(app, host="0.0.0.0", port=port)
