import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = """
python3 -c '
import subprocess

cmd = ["otool", "-tvV", "-arch", "arm64", "/Applications/League of Legends.app/Contents/LoL/LeagueClient.app/Contents/MacOS/LeagueClient"]
p = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)

capture = False
count = 0
for line in p.stdout:
    if "1004d3fd" in line or "1004d3fc" in line:
        capture = True
    if capture:
        print(line, end="")
        count += 1
        if count > 50:
            break
p.kill()
'
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
ssh.close()
