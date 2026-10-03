import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'ls -lt "/Applications/League of Legends_slot1.app/Contents/LoL/Logs/LeagueClient Logs" | head -n 10'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- LATEST SLOT1 LOGS ---")
print(stdout.read().decode())

cmd = 'ls -lt "/Applications/League of Legends_slot2.app/Contents/LoL/Logs/LeagueClient Logs" | head -n 10'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- LATEST SLOT2 LOGS ---")
print(stdout.read().decode())

ssh.close()
