import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = """
python3 -c '
import subprocess
cmd = ["otool", "-tvV", "-arch", "arm64", "/Applications/League of Legends.app/Contents/LoL/LeagueClient.app/Contents/MacOS/LeagueClient"]
p = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)

lines = []
capture = False
for line in p.stdout:
    if "1004d9930" in line or "1004d9934" in line:
        capture = True
    if capture:
        lines.append(line.strip())
        if len(lines) > 40:
            break
p.kill()
for l in lines:
    print(l)
'
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
ssh.close()
