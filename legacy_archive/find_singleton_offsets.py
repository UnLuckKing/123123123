import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = """
python3 -c '
with open("/Applications/League of Legends.app/Contents/LoL/LeagueClient.app/Contents/MacOS/LeagueClient", "rb") as f:
    d = f.read()

import re

# Find offsets of strings
s1 = b"Did not acquire process singleton"
s2 = b"Client already running, exiting."
s3 = b"Acquired process singleton"

for target in [s1, s2, s3]:
    idx = d.find(target)
    print(f"String \"{target.decode()}\" found at offset 0x{idx:x}")
'
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
ssh.close()
