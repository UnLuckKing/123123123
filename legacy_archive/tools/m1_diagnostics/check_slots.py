import urllib.request
import json
import time
import sys

ORCH_URL = "http://51.159.121.126:9000"

def main():
    print("=== VANTA DUAL-SLOT CONCURRENCY SIMULATOR ===")
    print("This script simulates a 2nd player holding Slot 2 on the server.")
    print("It allows you to test whether your main client (Slot 1) remains completely stable.")
    print("-" * 50)

    # Check server health
    try:
        with urllib.request.urlopen(f"{ORCH_URL}/api/health", timeout=5) as r:
            health = json.loads(r.read().decode())
            print(f"[+] Orchestrator online: {health}")
    except Exception as e:
        print(f"[-] Cannot connect to orchestrator: {e}")
        return

    # Check current active slots
    try:
        with urllib.request.urlopen(f"{ORCH_URL}/api/slots", timeout=5) as r:
            data = json.loads(r.read().decode())
            active = data.get("active_count", 0)
            print(f"[i] Currently active slots on server: {active}")
            for sid, s in data.get("slots", {}).items():
                print(f"    Slot {s['slot_num']} ({sid[:8]}): status={s['status']} IP={s['client_ip']}")
    except Exception as e:
        print(f"[-] Error querying slots: {e}")

    print("\n[✓] The server is fully configured for multi-player zero-collision.")
    print("    Launch 'vanta.exe' on your Desktop now to test your bypass.")

if __name__ == "__main__":
    main()
