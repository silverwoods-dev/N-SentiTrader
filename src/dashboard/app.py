# src/dashboard/app.py
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from datetime import datetime
from src.utils.metrics import start_metrics_server
from src.dashboard.routers import admin, quant
from src.dashboard.filters import format_kst

app = FastAPI(title="N-SentiTrader Dashboard")

# Global START_TIME for uptime calculation
START_TIME = datetime.now()

@app.on_event("startup")
async def startup_event():
    start_metrics_server()

templates = Jinja2Templates(directory="src/dashboard/templates")

# Register Filters
templates.env.filters["kst"] = format_kst

# Register Globals
from datetime import timedelta
templates.env.globals.update(timedelta=timedelta)

# Include Routers
app.include_router(admin.router)
app.include_router(quant.router)

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8081))
    uvicorn.run(app, host="0.0.0.0", port=port)
