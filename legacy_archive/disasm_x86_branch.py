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
    if "1004f2e2" in line:
        capture = True
    if capture:
        lines.append(line.strip())
        if "1004f2e55" in line:
            break
p.kill()
for l in lines: print(l)
'
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
ssh.close()
