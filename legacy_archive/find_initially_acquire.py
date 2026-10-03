import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = """
python3 -c '
with open("/Applications/League of Legends.app/Contents/LoL/LeagueClient.app/Contents/MacOS/LeagueClient", "rb") as f:
    d = f.read()

# Look for "Did not initially acquire process singleton"
idx = d.find(b"not initially acquire process singleton")
print("not initially acquire found at 0x%x" % idx)

# String in ARM64 slice
arm_off = idx - 0x257c000
va = 0x100000000 + arm_off
print(f"ARM64 VA: 0x{va:x}")

import subprocess
cmd = ["otool", "-tvV", "-arch", "arm64", "/Applications/League of Legends.app/Contents/LoL/LeagueClient.app/Contents/MacOS/LeagueClient"]
p = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)

for line in p.stdout:
    if "not initially acquire" in line or ("0x%x" % va) in line:
        print("MATCH:", line.strip())
        for _ in range(25):
            print(" ", next(p.stdout).strip())
        break
p.kill()
'
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
ssh.close()
