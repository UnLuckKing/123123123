import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = """
python3 -c '
import os, time

now = time.time()
found = []
for root, dirs, files in os.walk("/Applications"):
    if "Logs" in root:
        for f in files:
            if f.endswith(".log") or f.endswith(".txt"):
                p = os.path.join(root, f)
                try:
                    mtime = os.path.getmtime(p)
                    # within last 30 minutes
                    if now - mtime < 1800:
                        found.append((mtime, p))
                except: pass

for root, dirs, files in os.walk("/Users/m1"):
    if "Logs" in root or "VantaSlots" in root:
        for f in files:
            if f.endswith(".log") or f.endswith(".txt"):
                p = os.path.join(root, f)
                try:
                    mtime = os.path.getmtime(p)
                    if now - mtime < 1800:
                        found.append((mtime, p))
                except: pass

found.sort(reverse=True)
print(f"Total recent logs found: {len(found)}")
for mtime, p in found[:25]:
    print(f"{time.strftime(\"%H:%M:%S\", time.localtime(mtime))} : {p}")
'
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
ssh.close()
