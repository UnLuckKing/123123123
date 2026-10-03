import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = """
python3 -c '
with open("/Applications/League of Legends.app/Contents/LoL/LeagueClient.app/Contents/MacOS/LeagueClient", "rb") as f:
    d = f.read()

import re
keywords = [b"exit(9)", b"exit 9", b"ExitCode", b"status -1", b"already running", b"_flock", b"mutex", b"singleton"]
for kw in keywords:
    matches = [m.start() for m in re.finditer(kw, d, re.IGNORECASE)]
    print(f"Keyword {kw}: {len(matches)} matches")
    for m in matches[:3]:
        print("  ", d[max(0, m-30):min(len(d), m+50)])
'
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
ssh.close()
