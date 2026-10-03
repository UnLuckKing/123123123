import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')
cmd = """
python3 -c '
with open("/Applications/Riot Client.app/Contents/Frameworks/libRiotClientFoundation.dylib", "rb") as f:
    d = f.read()

import re
matches = [m.start() for m in re.finditer(b"product_install_full_path", d)]
for m in matches:
    print(d[max(0, m-120):min(len(d), m+120)])
'
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
ssh.close()
