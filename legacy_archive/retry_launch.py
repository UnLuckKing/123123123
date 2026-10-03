import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

mac_script = """
import urllib.request, ssl, base64, time, os, subprocess

lock_path = "/Users/m1/VantaSlots/slot2/Config/lockfile"
with open(lock_path) as f:
    parts = f.read().strip().split(":")
port, token = int(parts[2]), parts[3]

auth_hdr = base64.b64encode(f"riot:{token}".encode()).decode()
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Wait for auth
for i in range(10):
    try:
        req = urllib.request.Request(f"https://127.0.0.1:{port}/rso-auth/v1/session", headers={"Authorization": f"Basic {auth_hdr}"})
        with urllib.request.urlopen(req, context=ctx, timeout=2) as r:
            body = r.read().decode()
            if "authenticated" in body:
                print(f"Authenticated at {i}s")
                break
    except: pass
    time.sleep(1)

# Retry launch 3 times
launch_url = f"https://127.0.0.1:{port}/product-launcher/v1/products/league_of_legends/patchlines/live"
req = urllib.request.Request(launch_url, data=b"{}", headers={"Authorization": f"Basic {auth_hdr}", "Content-Type": "application/json"})

for attempt in range(1, 6):
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=5) as r:
            print(f"Launch attempt {attempt} SUCCESS:", r.status, r.read().decode())
            break
    except urllib.error.HTTPError as e:
        print(f"Launch attempt {attempt} HTTP {e.code}: {e.read().decode()}")
        time.sleep(2)
    except Exception as e:
        print(f"Launch attempt {attempt} Error: {e}")
        time.sleep(2)

time.sleep(3)
ps = subprocess.check_output(["ps", "-axo", "pid,command"]).decode(errors="replace")
for l in ps.splitlines():
    if "LeagueClient" in l and "grep" not in l:
        print("FOUND LC:", l)
"""

sftp = ssh.open_sftp()
with sftp.open("/tmp/do_launch.py", "w") as f:
    f.write(mac_script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command("python3 /tmp/do_launch.py")
print("MAC OUTPUT:\n" + stdout.read().decode())
err = stderr.read().decode()
if err: print("MAC ERR:\n" + err)

ssh.close()
