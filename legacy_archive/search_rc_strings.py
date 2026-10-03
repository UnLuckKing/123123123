import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = """
python3 -c '
with open("/Applications/Riot Client.app/Contents/MacOS/RiotClientServices", "rb") as f:
    data = f.read()

import re
matches = [m.start() for m in re.finditer(b"product-integration", data)]
print("Found product-integration references:", len(matches))
for m in matches[:10]:
    start = max(0, m - 50)
    end = min(len(data), m + 150)
    print(data[start:end])
'
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
ssh.close()
