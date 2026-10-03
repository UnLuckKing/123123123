import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

stdin, stdout, stderr = ssh.exec_command('ps -axo pid,command | grep -E "LeagueClient|RiotClient" | grep -v grep')
print("--- RUNNING RIOT / LEAGUE PROCESSES ---")
print(stdout.read().decode())

ssh.close()
