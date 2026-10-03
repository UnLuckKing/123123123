import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')
stdin, stdout, stderr = ssh.exec_command('find "/Users/m1/Library/Application Support/Riot Games" -name "*.yaml" | xargs grep -i "/Applications/League"')
print(stdout.read().decode())
ssh.close()
