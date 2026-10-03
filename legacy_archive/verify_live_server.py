import urllib.request
import json

base = "http://51.159.121.126:8088"

print("--- Admin Resellers Query ---")
res = urllib.request.urlopen(base + "/api/admin/resellers")
data = json.loads(res.read().decode())
resellers = data.get("resellers", [])
print(f"Total resellers registered: {len(resellers)}")
for r in resellers:
    print(f"  ID: {r['id']} | Key: {r['reseller_key']} | Name: {r['name']} | Credits: {r['credits']} | Status: {r['status']}")

if resellers:
    test_key = resellers[0]["reseller_key"]
    print(f"\n--- Reseller Portal Login Test (Key: {test_key}) ---")
    res2 = urllib.request.urlopen(f"{base}/api/reseller/info?key={test_key}")
    data2 = json.loads(res2.read().decode())
    r_info = data2.get("reseller", {})
    print(f"  Auth Success: {data2.get('success')}")
    print(f"  Partner Name: {r_info.get('name')}")
    print(f"  Current Balance: {r_info.get('credits')} Credits")
    print(f"  Issued Keys Count: {len(r_info.get('keys', []))}")
    print(f"  Direct Portal Link: {base}/reseller?key={test_key}")
