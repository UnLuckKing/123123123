import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

print("1. Testing RiotClientServices with --product-install-path for Slot 2...")
ssh.exec_command('pkill -9 -f RiotClientServices; pkill -9 -f LeagueClient')
time.sleep(2)

slot2_app = '/Applications/League of Legends_slot2.app'

cmd = f'''nohup /Applications/"Riot Client.app"/Contents/MacOS/RiotClientServices \
--allow-multiple-clients \
--user-data-root=/Users/m1/VantaSlots/slot2 \
--data-root=/Users/m1/VantaSlots/slot2/SharedMetadata \
--product-install-path="{slot2_app}" \
--product-install-root=/Applications \
> /tmp/rc_slot2_test.log 2>&1 &'''

stdin, stdout, stderr = ssh.exec_command(cmd)
time.sleep(4)

# Run launch script directly on Mac
mac_script = """
import urllib.request, ssl, base64, time, os, subprocess

lock_path = "/Users/m1/VantaSlots/slot2/Config/lockfile"
for _ in range(15):
    if os.path.exists(lock_path): break
    time.sleep(1)

with open(lock_path) as f:
    parts = f.read().strip().split(":")
port, token = int(parts[2]), parts[3]
print(f"RC online at port {port}")

auth_hdr = base64.b64encode(f"riot:{token}".encode()).decode()
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Wait for auth
for i in range(10):
    try:
        req = urllib.request.Request(f"https://127.0.0.1:{port}/rso-auth/v1/session", headers={"Authorization": f"Basic {auth_hdr}"})
        with urllib.request.urlopen(req, context=ctx, timeout=2) as r:
            if b"authenticated" in r.read():
                print("Authenticated!")
                break
    except: pass
    time.sleep(1)

# Trigger launch
launch_url = f"https://127.0.0.1:{port}/product-launcher/v1/products/league_of_legends/patchlines/live"
req = urllib.request.Request(launch_url, data=b"{}", headers={"Authorization": f"Basic {auth_hdr}", "Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req, context=ctx, timeout=5) as r:
        print("Launch status:", r.status, r.read().decode())
except Exception as e:
    print("Launch error:", e)

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
