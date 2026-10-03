import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')
cmd = """
python3 -c '
with open("/Applications/Riot Client.app/Contents/Frameworks/libRiotClientFoundation.dylib", "rb") as f:
    d = f.read()

import re
matches = [m.start() for m in re.finditer(b"Metadata", d)]
print("occurrences:", len(matches))
for m in matches:
    snippet = d[max(0, m - 40):min(len(d), m + 80)]
    if b"/" in snippet or b"Shared" in snippet or b"product" in snippet:
        print(" ", snippet)
'
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
ssh.close()
