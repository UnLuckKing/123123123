import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = """
python3 -c '
import subprocess
cmd = ["otool", "-tvV", "-arch", "x86_64", "/Applications/League of Legends.app/Contents/LoL/LeagueClient.app/Contents/MacOS/LeagueClient"]
p = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)

capture = False
lines = []
for line in p.stdout:
    if "Did not acquire process singleton" in line:
        capture = True
        lines.append(line.strip())
        for _ in range(15):
            lines.append(next(p.stdout).strip())
        break
p.kill()
for l in lines: print(l)
'
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
ssh.close()
