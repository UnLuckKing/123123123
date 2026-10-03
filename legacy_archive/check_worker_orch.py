import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

stdin, stdout, stderr = ssh.exec_command('grep -E "worker|timeout|Timeout|spawned|fail" /Users/m1/orchestrator.log | tail -n 25')
print("--- ORCHESTRATOR WORKER LOGS ---")
print(stdout.read().decode())

ssh.close()
