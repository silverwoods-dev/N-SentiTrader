from src.dashboard.app import app

expected = [
    "/analytics/backtest/monitor",
    "/analytics/backtest/row/{v_job_id}",
    "/analytics/backtest/create",
    "/analytics/backtest/start/{v_job_id}",
    "/analytics/backtest/stop/{v_job_id}",
    "/analytics/backtest/{v_job_id}",
    "/analytics/backtest/report/{v_job_id}",
]

routes = [r.path for r in app.routes]

print("Registered routes (sample):")
for p in routes:
    if p.startswith("/analytics/backtest"):
        print("  ", p)

missing = [p for p in expected if p not in routes]
if missing:
    print("\nMissing expected routes:")
    for m in missing:
        print("  ", m)
    raise SystemExit(2)
else:
    print('\nAll expected backtest routes are registered.')
