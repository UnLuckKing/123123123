import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'grep -E "worker:slot" /Users/m1/orchestrator.log | tail -n 25'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("WORKER LOGS:")
print(stdout.read().decode('utf-8', 'ignore'))

ssh.close()
