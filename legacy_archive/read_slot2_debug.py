import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'grep -E "worker:slot2|slot 2" /Users/m1/*.log 2>/dev/null | tail -n 40'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("LOGS:")
print(stdout.read().decode('utf-8', 'ignore'))

ssh.close()
