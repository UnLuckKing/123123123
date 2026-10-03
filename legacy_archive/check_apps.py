import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'du -d 1 -h /Applications 2>/dev/null | sort -hr'
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())

ssh.close()
