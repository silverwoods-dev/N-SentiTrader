
import logging
from datetime import datetime
import json
from src.db.connection import get_db_cursor
from src.utils.mq import get_queue_depths, JOB_QUEUE_NAME, VERIFICATION_QUEUE_NAME, VERIFICATION_DAILY_QUEUE_NAME, DAILY_JOB_QUEUE_NAME

logger = logging.getLogger(__name__)

class SystemWatchdog:
    """
    Monitors the health of the system by cross-referencing state 
    between the Database (Application) and RabbitMQ (Infrastructure).
    """

    def check_health(self):
        """
        Performs a full health check.
        Returns a dict with overall status and details.
        """
        health_status = {
            "status": "healthy", # healthy, warning, critical
            "issues": [],
            "details": {},
            "timestamp": datetime.now().isoformat()
        }

        try:
            # 1. Get Infrastructure State (RabbitMQ)
            mq_state = get_queue_depths()
            health_status["details"]["mq"] = mq_state
            
            # 2. Get Application State (Database)
            db_state = self._get_db_job_counts()
            
            # Convert datetimes to strings for JSON serialization in details
            serializable_db_state = {
                "running_verification_data": [
                    {**j, "started_at": j["started_at"].isoformat() if j.get("started_at") else None}
                    for j in db_state.get("running_verification_data", [])
                ],
                "running_collection_data": [
                    {**j, "started_at": j["started_at"].isoformat() if j.get("started_at") else None}
                    for j in db_state.get("running_collection_data", [])
                ]
            }
            health_status["details"]["db"] = serializable_db_state

            # 3. Cross-Validate: Zombie Worker Check
            grace_seconds = 30
            now = datetime.now()

            # Check Verification Workers (Granular by queue)
            v_running_data = db_state.get("running_verification_data", [])
            v_zombie_ids = []
            for job in v_running_data:
                v_type = job.get("v_type")
                # Map job type to its specific target queue
                target_q = VERIFICATION_DAILY_QUEUE_NAME if v_type == "DAILY_UPDATE" else VERIFICATION_QUEUE_NAME
                consumers = mq_state.get(target_q, {}).get("consumers", 0)
                
                started_at = job.get('started_at')
                is_expired = not started_at or (now - started_at).total_seconds() > grace_seconds
                
                if is_expired and consumers == 0:
                    v_zombie_ids.append(f"V{job['v_job_id']} ({v_type}) on {target_q}")

            if v_zombie_ids:
                health_status["status"] = "critical"
                health_status["issues"].append(f"Zombie Verification: Jobs {', '.join(v_zombie_ids)} have 0 consumers.")
            
            # Check Collection Workers (Granular by queue)
            c_running_data = db_state.get("running_collection_data", []) 
            c_zombie_ids = []
            for job in c_running_data:
                j_type = job.get("job_type")
                # Map collection job type to queue
                if j_type == 'daily':
                    target_q = DAILY_JOB_QUEUE_NAME
                elif j_type == 'backfill':
                    target_q = JOB_QUEUE_NAME
                elif j_type == 'content':
                    target_q = QUEUE_NAME
                else:
                    target_q = JOB_QUEUE_NAME
                
                consumers = mq_state.get(target_q, {}).get("consumers", 0)
                
                started_at = job.get('started_at')
                is_expired = not started_at or (now - started_at).total_seconds() > grace_seconds

                if is_expired and consumers == 0:
                    c_zombie_ids.append(f"J{job['job_id']} ({j_type}) on {target_q}")

            if c_zombie_ids:
                health_status["status"] = "critical"
                health_status["issues"].append(f"Zombie Collection: Jobs {', '.join(c_zombie_ids)} have 0 consumers.")

            # 4. Check Queue Backlogs (Warning)
            for q_name, metrics in mq_state.items():
                if metrics.get("ready", 0) > 2000: # Increased threshold for scaled workers
                   health_status["status"] = "warning" if health_status["status"] == "healthy" else health_status["status"]
                   health_status["issues"].append(f"High Queue Backlog: {q_name} has {metrics['ready']} messages pending.")

        except Exception as e:
            logger.error(f"Health Check Failed: {e}")
            health_status["status"] = "unknown"
            health_status["issues"].append(f"Health Check Error: {str(e)}")

        return health_status

    def _get_db_job_counts(self):
        """Fetch counts and detail of running jobs from DB"""
        stats = {}
        with get_db_cursor() as cur:
            # Verification Jobs
            cur.execute("SELECT v_job_id, v_type, started_at FROM tb_verification_jobs WHERE status = 'running'")
            stats["running_verification_data"] = cur.fetchall()
            
            # Collection Jobs (General)
            cur.execute("SELECT job_id, job_type, started_at FROM jobs WHERE status = 'running'")
            stats["running_collection_data"] = cur.fetchall()
            
        return stats

def _log_system_event(cur, event_type, severity, component, message, metadata=None):
    """Internal helper to log events"""
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
    cur.execute("""
        INSERT INTO tb_system_events (event_type, severity, component, message, metadata)
        VALUES (%s, %s, %s, %s, %s)
    """, (event_type, severity, component, message, json.dumps(metadata) if metadata else None))

def persist_health_status(status_data):
    """
    Saves health status and logs transitions.
    """
    try:
        with get_db_cursor() as cur:
            # 1. Fetch Previous Status
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tb_system_health (
                    check_type VARCHAR(50) PRIMARY KEY,
                    status VARCHAR(20),
                    details JSONB,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cur.execute("SELECT status FROM tb_system_health WHERE check_type = 'watchdog'")
            row = cur.fetchone()
            prev_status = row['status'] if row else 'unknown'
            new_status = status_data["status"]
            
            # 2. Check Transition
            if prev_status != new_status:
                event_type = "INFO"
                severity = "INFO"
                msg = f"System status changed from {prev_status} to {new_status}"
                
                if new_status == "critical":
                    event_type = "DETECTION"
                    severity = "CRITICAL"
                    msg = status_data["issues"][0] if status_data["issues"] else "Critical Issue Detected"
                elif new_status == "healthy" and prev_status in ["critical", "warning"]:
                    event_type = "RESOLUTION"
                    severity = "SUCCESS"
                    msg = "System returned to healthy state"
                elif new_status == "warning":
                    event_type = "DETECTION"
                    severity = "WARNING"
                    msg = status_data["issues"][0] if status_data["issues"] else "Warning Detected"

                _log_system_event(cur, event_type, severity, "watchdog", msg, status_data)
                logger.info(f"Logged System Event: {msg}")

            # 3. Upsert status
            cur.execute("""
                INSERT INTO tb_system_health (check_type, status, details, updated_at)
                VALUES ('watchdog', %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (check_type) 
                DO UPDATE SET status = EXCLUDED.status, details = EXCLUDED.details, updated_at = CURRENT_TIMESTAMP
            """, (new_status, json.dumps(status_data)))
            
    except Exception as e:
        logger.error(f"Failed to persist health status: {e}")
