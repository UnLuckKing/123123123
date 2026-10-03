import paramiko

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1', timeout=5)

cmd = """python3 -c '
import glob
files = sorted(glob.glob("/Users/m1/Library/Logs/Riot Games/Riot Client/Riot Client Logs/*.log"))
for f in files:
    with open(f) as fp:
        lines = fp.readlines()
        for i, l in enumerate(lines):
            if any(k in l for k in ["restart", "Restart", "Exit", "CRASH", "Signal", "Terminating"]):
                if "23:47" in l or "23:48" in l:
                    print(f"{f}:{i}: {l.strip()}")
'"""

_, out, _ = s.exec_command(cmd)
print(out.read().decode())
s.close()
