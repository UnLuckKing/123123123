import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = """
python3 -c '
with open("/Applications/Riot Client.app/Contents/Frameworks/libRiotClientFoundation.dylib", "rb") as f:
    data = f.read()

import re
matches = [m.start() for m in re.finditer(b"terminated with exit code", data)]
for m in matches:
    start = max(0, m - 100)
    end = min(len(data), m + 150)
    print("Match at", m, ":", data[start:end])
'
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
ssh.close()
