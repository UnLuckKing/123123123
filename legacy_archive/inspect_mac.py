import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')
_, out, _ = ssh.exec_command('ps aux | grep -i riot')
print(out.read().decode('utf-8', 'ignore'))
ssh.close()
