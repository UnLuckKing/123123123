import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

stdin, stdout, stderr = ssh.exec_command('tail -n 60 /Users/m1/orchestrator.log')
print("ORCHESTRATOR LOG:\n" + stdout.read().decode())

stdin, stdout, stderr = ssh.exec_command('ps -axo pid,user,command | grep -E "Riot|League" | grep -v grep')
print("PROCESSES:\n" + stdout.read().decode())

ssh.close()
