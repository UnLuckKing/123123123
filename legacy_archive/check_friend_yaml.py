import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'head -n 20 "/Users/m1/VantaSlots/slot2/Data/RiotGamesPrivateSettings.yaml"'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("SLOT 2 (FRIEND) YAML:")
print(stdout.read().decode('utf-8', 'ignore'))

ssh.close()
