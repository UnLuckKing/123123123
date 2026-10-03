import paramiko
import time
import subprocess

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

print("Starting test_concurrent_both.py and capturing LC launch...")
# Run in background on Mac
ssh.exec_command('python3 /Users/m1/test_concurrent_both.py > /tmp/test_both.log 2>&1 &')

# Monitor ps output every 0.5s for 20 seconds
for i in range(30):
    time.sleep(0.5)
    stdin, stdout, stderr = ssh.exec_command('ps -axo pid,command | grep -E "LeagueClient|LeagueClientUx" | grep -v grep')
    out = stdout.read().decode().strip()
    if out:
        print(f"[{i*0.5}s] FOUND PROCESSES:")
        for line in out.splitlines():
            print("  ", line[:180])

ssh.close()
