import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

stdin, stdout, stderr = ssh.exec_command('echo PNGGJHc5f7f1 | sudo -S chmod -R 777 "/Applications/League of Legends.app" "/Applications/Riot Client.app"')
print(stdout.read().decode())
print(stderr.read().decode())

stdin, stdout, stderr = ssh.exec_command('echo PNGGJHc5f7f1 | sudo -S ls -la /Users/slot1 /Users/slot2')
print(stdout.read().decode())

ssh.close()
