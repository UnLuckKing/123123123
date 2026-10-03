import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'find "/Applications/League of Legends_slot1.app/Contents/LoL/Logs/LeagueClient Logs" -type f -name "*LeagueClient.log" | xargs tail -n 30'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- LEAGUECLIENT LOG SLOT1 ---")
print(stdout.read().decode())

cmd2 = 'find "/Applications/League of Legends_slot2.app/Contents/LoL/Logs/LeagueClient Logs" -type f -name "*LeagueClient.log" | xargs tail -n 30'
stdin, stdout, stderr = ssh.exec_command(cmd2)
print("--- LEAGUECLIENT LOG SLOT2 ---")
print(stdout.read().decode())

ssh.close()
