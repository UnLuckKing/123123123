import sys
import base64
import json
import os

def main():
    if len(sys.argv) < 2:
        return
    arg = sys.argv[1]
    if not arg.startswith("--riotgamesapi-settings="):
        print(arg)
        return
        
    b64 = arg.split("=", 1)[1]
    try:
        js = json.loads(base64.b64decode(b64).decode())
    except Exception:
        print(arg)
        return
    
    slot_num = os.environ.get("VANTA_SLOT_NUM", "0")
    if slot_num != "0":
        base_dir = f"/Users/m1/VantaSlots/slot{slot_num}"
        os.makedirs(f"{base_dir}/League", exist_ok=True)
        
        # Isolate product-integration lockfile & heartbeat
        if "product-integration" in js:
            js["product-integration"]["lockfile"] = f"{base_dir}/league.lockfile"
            js["product-integration"]["heartbeat"] = f"{base_dir}/heartbeat.json"
            
        # Isolate persistence path
        if "riotgamesapi" in js:
            js["riotgamesapi"]["persistence-path"] = f"{base_dir}/League"
            
    new_b64 = base64.b64encode(json.dumps(js).encode()).decode()
    print(f"--riotgamesapi-settings={new_b64}")

if __name__ == "__main__":
    main()
