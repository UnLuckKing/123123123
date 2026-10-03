import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

print("--- ORCH LOG ---")
stdin, stdout, stderr = ssh.exec_command('tail -n 150 /Users/m1/orch.log')
print(stdout.read().decode())

print("--- PS OUT ---")
stdin, stdout, stderr = ssh.exec_command('ps -axo pid,args | grep -i League')
print(stdout.read().decode())

ssh.close()
