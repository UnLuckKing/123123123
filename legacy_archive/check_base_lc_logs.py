import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')
stdin, stdout, stderr = ssh.exec_command('ls -lat "/Applications/League of Legends.app/Contents/LoL/Logs/LeagueClient Logs" | head -n 20')
print(stdout.read().decode())
ssh.close()
