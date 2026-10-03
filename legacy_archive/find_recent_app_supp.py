import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'find "/Users/m1/Library/Application Support/League of Legends" -mmin -2 -type f'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- NEW FILES IN GLOBAL LEAGUE SUPPORT ---")
print(stdout.read().decode())

cmd = 'find "/Users/m1/Library/Application Support/Riot Games" -mmin -2 -type f'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- NEW FILES IN GLOBAL RIOT GAMES SUPPORT ---")
print(stdout.read().decode())

ssh.close()
