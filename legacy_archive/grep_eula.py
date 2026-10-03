import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

stdin, stdout, stderr = ssh.exec_command('grep -i -C 3 "eula" "/Users/m1/VantaSlots/slot1/Data/RiotGamesPrivateSettings.yaml"')
print("SLOT 1 EULA IN PRIVATE SETTINGS:\n" + stdout.read().decode())

stdin, stdout, stderr = ssh.exec_command('grep -i -C 3 "eula" "/Users/m1/VantaSlots/slot1/Config/RiotClientSettings.yaml"')
print("SLOT 1 EULA IN RC SETTINGS:\n" + stdout.read().decode())

ssh.close()
