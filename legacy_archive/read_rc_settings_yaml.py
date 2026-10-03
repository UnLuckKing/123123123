import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')
stdin, stdout, stderr = ssh.exec_command('cat "/Users/m1/Library/Application Support/RiotClientData_slot1/Config/RiotClientSettings.yaml" 2>/dev/null; cat "/Users/m1/VantaSlots/slot1/Config/RiotClientSettings.yaml" 2>/dev/null')
print(stdout.read().decode())
ssh.close()
