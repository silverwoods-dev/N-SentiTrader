
import logging
from datetime import datetime
import json
from src.db.connection import get_db_cursor
from src.utils.mq import get_queue_depths, JOB_QUEUE_NAME, VERIFICATION_QUEUE_NAME, DAILY_JOB_QUEUE_NAME

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
            health_status["details"]["db"] = db_state

            # 3. Cross-Validate: Zombie Worker Check
            # Check Verification Workers (One replica expected)
            v_running_data = db_state.get("running_verification_data", [])
            v_consumers = mq_state.get(VERIFICATION_QUEUE_NAME, {}).get("consumers", 0)
            
            # Grace Period: 30 seconds to allow for MQ delivery and worker pickup
            grace_seconds = 30
            now = datetime.now()
            
            v_real_zombies = []
            for job in v_running_data:
                # If started_at is missing, assume it's old/stuck
                started_at = job.get('started_at')
                if not started_at:
                    v_real_zombies.append(job)
                    continue
                
                # Check if outside grace period
                if (now - started_at).total_seconds() > grace_seconds:
                    v_real_zombies.append(job)

            if len(v_real_zombies) > 0 and v_consumers == 0:
                health_status["status"] = "critical"
                health_status["issues"].append(f"Zombie Verification Worker: {len(v_real_zombies)} jobs running but 0 consumers on '{VERIFICATION_QUEUE_NAME}'.")
            
            # Check Address/Collection Workers (Address & Daily)
            c_running_data = db_state.get("running_collection_data", []) 
            # We check both address_jobs and daily_address_jobs consumers
            addr_consumers = mq_state.get(JOB_QUEUE_NAME, {}).get("consumers", 0)
            daily_consumers = mq_state.get(DAILY_JOB_QUEUE_NAME, {}).get("consumers", 0)
            total_c_consumers = addr_consumers + daily_consumers
            
            c_real_zombies = []
            for job in c_running_data:
                started_at = job.get('started_at')
                if not started_at:
                    c_real_zombies.append(job)
                    continue
                
                if (now - started_at).total_seconds() > grace_seconds:
                    c_real_zombies.append(job)

            if len(c_real_zombies) > 0 and total_c_consumers == 0:
                health_status["status"] = "critical"
                health_status["issues"].append(f"Zombie Collection Worker: {len(c_real_zombies)} jobs running but 0 consumers on '{JOB_QUEUE_NAME}'/'{DAILY_JOB_QUEUE_NAME}'.")

            # 4. Check Queue Backlogs (Warning)
            for q_name, metrics in mq_state.items():
                if metrics.get("ready", 0) > 1000:
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
            cur.execute("SELECT v_job_id, started_at FROM tb_verification_jobs WHERE status = 'running'")
            stats["running_verification_data"] = cur.fetchall()
            
            # Collection Jobs (General)
            cur.execute("SELECT job_id, started_at FROM jobs WHERE status = 'running'")
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
