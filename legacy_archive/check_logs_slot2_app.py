import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'find "/Applications/League of Legends_slot2.app/Contents/LoL/Logs/LeagueClient Logs" -type f | xargs tail -n 25'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- LOGS IN SLOT2 ---")
print(stdout.read().decode())

ssh.close()
