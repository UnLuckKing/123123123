import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')
stdin, stdout, stderr = ssh.exec_command('grep -E "worker|error|fail|Timeout|spawned" /Users/m1/orchestrator.log | tail -n 30')
print(stdout.read().decode())
ssh.close()
