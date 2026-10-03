import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

stdin, stdout, stderr = ssh.exec_command('ps -axo pid,command | grep -E "LeagueClientUx|LeagueofLegends" | grep -v grep')
print("--- UX AND GAME PROCESSES ---")
print(stdout.read().decode())

ssh.close()
