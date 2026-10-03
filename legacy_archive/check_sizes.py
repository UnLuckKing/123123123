import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'sudo du -d 1 -h /System/Volumes/Data/ | sort -hr; echo "--- USERS ---"; sudo du -d 1 -h /Users/ | sort -hr'
# user is m1, password PNGGJHc5f7f1
stdin, stdout, stderr = ssh.exec_command('echo PNGGJHc5f7f1 | sudo -S du -d 1 -h /System/Volumes/Data 2>/dev/null | sort -hr; echo "--- USERS ---"; echo PNGGJHc5f7f1 | sudo -S du -d 1 -h /Users 2>/dev/null | sort -hr')
print(stdout.read().decode())

ssh.close()
