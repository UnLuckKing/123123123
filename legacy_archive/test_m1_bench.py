import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'time cp -c -R "/Applications/League of Legends.app" "/Applications/League of Legends_slot1.app"'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:", stdout.read().decode('utf-8', 'ignore'))
print("STDERR:", stderr.read().decode('utf-8', 'ignore'))

stdin, stdout, stderr = ssh.exec_command('ls -ld /Applications/League*')
print("LS:\n", stdout.read().decode('utf-8', 'ignore'))

ssh.close()
