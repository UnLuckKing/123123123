import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'cat /Users/m1/modify_settings.py'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- modify_settings.py ---")
print(stdout.read().decode())

cmd = 'find "/Applications/League of Legends_slot2.app" -name "LeagueClient*"'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- LC FILES IN SLOT2 ---")
print(stdout.read().decode())

ssh.close()
