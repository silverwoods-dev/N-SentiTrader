
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from src.db.connection import get_db_cursor
from src.utils.monitor import _log_system_event

def verify_events():
    print("Running Event Logging verification...")
    try:
        with get_db_cursor() as cur:
            # 1. Log a test event
            print("Logging test event...")
            _log_system_event(cur, "INFO", "SUCCESS", "verification_script", "Verifying event logging system", {"test": True})
            
            # 2. Read back
            print("Reading events...")
            cur.execute("SELECT * FROM tb_system_events ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            
            if row:
                print(f"✅ Event Logged: [{row['severity']}] {row['message']} (Type: {row['event_type']})")
            else:
                print("❌ No events found!")

    except Exception as e:
        print(f"❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_events()
