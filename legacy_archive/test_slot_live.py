import urllib.request
import json
import time

yaml_path = r'C:\Users\hesap\AppData\Local\Riot Games\Riot Client\Data\RiotGamesPrivateSettings.yaml'
with open(yaml_path, 'r', encoding='utf-8') as f:
    yaml_data = f.read()

print("Sending request_slot to Orchestrator...")
req = urllib.request.Request(
    "http://51.159.121.126:9000/api/request_slot",
    data=yaml_data.encode('utf-8'),
    headers={"Content-Type": "text/plain"}
)

with urllib.request.urlopen(req, timeout=10) as resp:
    res = json.loads(resp.read().decode('utf-8'))
    print("Slot provisioned response:", res)

slot_id = res.get("slot_id")
print(f"Monitoring slot {slot_id}...")

for i in range(40):
    time.sleep(2)
    poll_url = f"http://51.159.121.126:9000/api/poll_slot?slot_id={slot_id}"
    try:
        with urllib.request.urlopen(poll_url, timeout=5) as p_resp:
            p_data = json.loads(p_resp.read().decode('utf-8'))
            status = p_data.get("status")
            args_count = len(p_data.get("args", []))
            print(f"[{i*2}s] Status: {status} | Args count: {args_count}")
            if status == "game_ready":
                print(">>> SUCCESS! Slot reached GAME_READY! <<<")
                print("Args sample:", p_data.get("args")[:5])
                break
            elif "FAILED" in str(status):
                print(">>> FAILED! <<<", status)
                break
    except Exception as e:
        print(f"[{i*2}s] Poll error: {e}")
