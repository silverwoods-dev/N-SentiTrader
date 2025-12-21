
import os
import time
import subprocess
from pathlib import Path

TRIGGER_FILE = "src/.trigger_warp_rotation"
COOLDOWN_FILE = "src/.warp_last_rotation"
COOLDOWN_SECONDS = 300  # Max rotation once every 5 mins

def rotate_warp():
    print(f"[*] Rotating WARP IP due to trigger...")
    try:
        # Check last rotation
        if os.path.exists(COOLDOWN_FILE):
             last_rot = os.path.getmtime(COOLDOWN_FILE)
             if time.time() - last_rot < COOLDOWN_SECONDS:
                 print(f"[-] Rotation skipped (Cooldown active).")
                 return

        # Execute rotation
        subprocess.run(["warp-cli", "disconnect"], check=False)
        time.sleep(5)
        subprocess.run(["warp-cli", "connect"], check=False)
        print(f"[+] WARP IP Rotation command sent.")
        
        # Update timestamp
        with open(COOLDOWN_FILE, 'w') as f:
            f.write(str(time.time()))
            
    except Exception as e:
        print(f"[!] Error rotating WARP: {e}")

def main():
    print("[*] WARP Rotator Service Started. Monitoring for triggers...")
    while True:
        if os.path.exists(TRIGGER_FILE):
            print(f"[!] Trigger detected in {TRIGGER_FILE}")
            rotate_warp()
            try:
                os.remove(TRIGGER_FILE)
            except:
                pass
        time.sleep(5)

if __name__ == "__main__":
    main()
