import urllib.request
import json
import time

yaml_path = r'C:\Users\hesap\AppData\Local\Riot Games\Riot Client\Data\RiotGamesPrivateSettings.yaml'
with open(yaml_path, 'r', encoding='utf-8') as f:
    base_yaml = f.read()

# Generate a slightly modified session for slot 2 so client_hash is unique
# e.g., append a comment line
yaml_slot2 = base_yaml + "\n# mock_slot_2_test: 12345\n"

print("Requesting Slot 2 while Slot 1 is STILL RUNNING...")
req = urllib.request.Request(
    "http://51.159.121.126:9000/api/request_slot",
    data=yaml_slot2.encode('utf-8'),
    headers={"Content-Type": "text/plain"}
)

try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        res2 = json.loads(resp.read().decode('utf-8'))
        print("Slot 2 provisioned response:", res2)
except Exception as e:
    print("Error requesting slot 2:", e)
    exit(1)

sid2 = res2.get("slot_id")

print(f"Monitoring Slot 2 ({sid2}) while checking Slot 1 concurrently...")
for i in range(35):
    time.sleep(2)
    try:
        # Check overall slots
        with urllib.request.urlopen("http://51.159.121.126:9000/api/slots", timeout=5) as resp:
            all_slots = json.loads(resp.read().decode('utf-8'))
        
        # Poll slot 2 to keep it alive
        with urllib.request.urlopen(f"http://51.159.121.126:9000/api/poll_slot?slot_id={sid2}", timeout=5) as resp:
            s2_data = json.loads(resp.read().decode('utf-8'))
            s2_status = s2_data.get("status")

        print(f"[{i*2}s] Active count: {all_slots.get('active_count')} | Slot 2 status: {s2_status}")
        
        if s2_status == "game_ready":
            print(">>> DUAL CONCURRENCY CONFIRMED! SLOT 2 REACHED GAME_READY! <<<")
            print("Current active slots in orchestrator:", all_slots.get("slots"))
            break
        elif "FAILED" in str(s2_status):
            print(">>> SLOT 2 FAILED! <<<", s2_status)
            break
    except Exception as e:
        print(f"[{i*2}s] Error during poll: {e}")
