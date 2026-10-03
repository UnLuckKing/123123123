import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

print("Killing anything on port 9000...")
ssh.exec_command("lsof -ti :9000 | xargs kill -9")
time.sleep(1)

print("Killing python processes...")
ssh.exec_command("pkill -9 -f 'vanta_orchestrator.py'")
time.sleep(1)

print("Starting orchestrator...")
ssh.exec_command("nohup python3 /Users/m1/vanta_orchestrator.py > /Users/m1/orch.log 2>&1 &")

time.sleep(2)
print("Logs:")
stdin, stdout, stderr = ssh.exec_command('tail -n 20 /Users/m1/orch.log')
print(stdout.read().decode())
ssh.close()
