import urllib.request
import json
import time
import os
import paramiko

# 1. Read local YAML (Account 1 - Kralim)
local_appdata = os.environ.get("LOCALAPPDATA", "")
yaml1_path = os.path.join(local_appdata, "Riot Games", "Riot Client", "Data", "RiotGamesPrivateSettings.yaml")
with open(yaml1_path, "r", encoding="utf-8") as f:
    yaml1_data = f.read()

# 2. Fetch Account 2 YAML from M1 server
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

print("Fetching Account 2 YAML from M1...")
stdin, stdout, stderr = ssh.exec_command('cat "/Users/m1/Library/Application Support/RiotClientData/Data/RiotGamesPrivateSettings.yaml"')
yaml2_data = stdout.read().decode('utf-8', 'ignore')

# Reset slots on orchestrator
print("Resetting any existing slots on orchestrator...")
req_reset = urllib.request.Request("http://51.159.121.126:9000/api/slots/reset", data=b"{}")
try:
    with urllib.request.urlopen(req_reset, timeout=5) as r:
        print("Reset response:", r.read().decode())
except Exception as e:
    print("Reset notice:", e)

time.sleep(2)

print("\n--- SIMULATION STEP 1: Launching Slot 1 (Kralim) ---")
req1 = urllib.request.Request("http://51.159.121.126:9000/api/request_slot", data=yaml1_data.encode("utf-8"), headers={"Content-Type": "text/plain"})
with urllib.request.urlopen(req1, timeout=10) as r1:
    res1 = json.loads(r1.read().decode())
    sid1 = res1["slot_id"]
    print(f"Slot 1 acquired: ID={sid1[:8]} Ports: proxy={res1['proxy_port']}, lcu={res1['lcu_port']}, udp={res1['udp_proxy_port']}")

time.sleep(2)

print("\n--- SIMULATION STEP 2: Launching Slot 2 (Second Player / Friend) ---")
req2 = urllib.request.Request("http://51.159.121.126:9000/api/request_slot", data=yaml2_data.encode("utf-8"), headers={"Content-Type": "text/plain"})
with urllib.request.urlopen(req2, timeout=10) as r2:
    res2 = json.loads(r2.read().decode())
    sid2 = res2["slot_id"]
    print(f"Slot 2 acquired: ID={sid2[:8]} Ports: proxy={res2['proxy_port']}, lcu={res2['lcu_port']}, udp={res2['udp_proxy_port']}")

print("\n--- SIMULATION STEP 3: Concurrently Polling Both Slots ---")
start_time = time.time()
both_ready = False

for attempt in range(45):
    time.sleep(2)
    elapsed = int(time.time() - start_time)
    
    # Poll Slot 1
    try:
        with urllib.request.urlopen(f"http://51.159.121.126:9000/api/poll_slot?slot_id={sid1}", timeout=5) as p1:
            st1 = json.loads(p1.read().decode())
    except Exception as e:
        st1 = {"status": f"error: {e}"}
        
    # Poll Slot 2
    try:
        with urllib.request.urlopen(f"http://51.159.121.126:9000/api/poll_slot?slot_id={sid2}", timeout=5) as p2:
            st2 = json.loads(p2.read().decode())
    except Exception as e:
        st2 = {"status": f"error: {e}"}

    status1 = st1.get("status")
    status2 = st2.get("status")
    args1 = len(st1.get("args") or [])
    args2 = len(st2.get("args") or [])

    print(f"[{elapsed:2d}s] Slot 1: {status1:<12} (args={args1:2d}) | Slot 2: {status2:<12} (args={args2:2d})")

    if status1 == "game_ready" and status2 == "game_ready":
        both_ready = True
        print("\n========================================================")
        print(">>> SUCCESS: BOTH SLOTS ARE RUNNING CONCURRENTLY! <<<")
        print("========================================================")
        break

    if "FAILED" in str(status1) or "FAILED" in str(status2):
        print(f"\n[!] Failure detected: st1={status1}, st2={status2}")
        break

print("\n--- SIMULATION STEP 4: Live M1 System Process Inspection ---")
stdin, stdout, stderr = ssh.exec_command('ps -axo pid,command | grep -E "LeagueClient|slot" | grep -v grep')
print(stdout.read().decode())

print("\n--- SIMULATION STEP 5: Verifying Active Slots on Orchestrator API ---")
try:
    with urllib.request.urlopen("http://51.159.121.126:9000/api/slots", timeout=5) as s_api:
        api_slots = json.loads(s_api.read().decode())
        print(json.dumps(api_slots, indent=2))
except Exception as e:
    print("API slot inspect error:", e)

# Clean up simulation
print("\nCleaning up test slots...")
try:
    urllib.request.urlopen(urllib.request.Request("http://51.159.121.126:9000/api/slots/reset", data=b"{}"))
    print("Cleanup complete.")
except Exception as e:
    print("Cleanup notice:", e)

ssh.close()
