import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'ls -la /Users/m1/VantaSlots/*/Data/RiotGamesPrivateSettings.yaml; ls -la /Users/m1/Library/Application\\ Support/RiotClientData*/Data/RiotGamesPrivateSettings.yaml'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("YAML FILES ON M1:")
print(stdout.read().decode('utf-8', 'ignore'))

ssh.close()
