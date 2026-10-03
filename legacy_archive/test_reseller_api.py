import urllib.request
import json

base = "http://51.159.121.126:8088"
reseller_key = "VANTA-RSL-3D4908C39DE6"

print("--- 1. Testing /api/reseller/info ---")
try:
    req = urllib.request.urlopen(f"{base}/api/reseller/info?key={reseller_key}")
    res = json.loads(req.read().decode())
    print("Info result:", res)
except Exception as e:
    print("Info failed:", e)

print("\n--- 2. Testing /api/reseller/generate ---")
try:
    data = json.dumps({
        "reseller_key": reseller_key,
        "days": 30,
        "role": "user",
        "note": "API test single mint"
    }).encode("utf-8")
    req = urllib.request.Request(f"{base}/api/reseller/generate", data=data, headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req)
    res = json.loads(resp.read().decode())
    print("Generate result:", res)
    minted_key = res.get("license_key")
except Exception as e:
    print("Generate failed:", e)
    minted_key = None

print("\n--- 3. Testing /api/v1/reseller/mint_key (Bearer token) ---")
try:
    data = json.dumps({
        "days": 30,
        "role": "user",
        "note": "Bearer test mint"
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/api/v1/reseller/mint_key",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {reseller_key}"
        }
    )
    resp = urllib.request.urlopen(req)
    res = json.loads(resp.read().decode())
    print("Bearer mint result:", res)
except Exception as e:
    print("Bearer mint failed:", e)

print("\n--- 4. Testing /api/reseller/reset_hwid ---")
if minted_key:
    try:
        data = json.dumps({
            "reseller_key": reseller_key,
            "license_key": minted_key
        }).encode("utf-8")
        req = urllib.request.Request(f"{base}/api/reseller/reset_hwid", data=data, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req)
        res = json.loads(resp.read().decode())
        print("Reset HWID result:", res)
    except Exception as e:
        print("Reset HWID failed:", e)

print("\n--- 5. Testing /api/reseller/bulk_generate ---")
try:
    data = json.dumps({
        "reseller_key": reseller_key,
        "count": 2,
        "days": 7,
        "role": "user",
        "note": "Bulk test"
    }).encode("utf-8")
    req = urllib.request.Request(f"{base}/api/reseller/bulk_generate", data=data, headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req)
    res = json.loads(resp.read().decode())
    print("Bulk generate result:", res)
except Exception as e:
    print("Bulk generate failed:", e)
