import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'lsof -p 32918 | grep -i TCP; lsof -p 32919 | grep -i TCP'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- TCP PORTS OPEN FOR LEAGUECLIENT ---")
print(stdout.read().decode())

ssh.close()
