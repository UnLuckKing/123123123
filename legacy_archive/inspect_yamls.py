import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'head -n 25 "/Users/m1/Library/Application Support/RiotClientData/Data/RiotGamesPrivateSettings.yaml"'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("M1 Golden YAML:")
print(stdout.read().decode('utf-8', 'ignore'))

ssh.close()
