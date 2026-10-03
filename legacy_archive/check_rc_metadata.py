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
print("Metadata occurrences:", len(matches))
for m in matches[:10]:
    start = max(0, m - 40)
    end = min(len(d), m + 80)
    print(" ", d[start:end])
'
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
ssh.close()
