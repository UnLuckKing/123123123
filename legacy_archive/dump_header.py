import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')
stdin, stdout, stderr = ssh.exec_command('file "/Applications/League of Legends.app/Contents/LoL/LeagueClient.app/Contents/MacOS/LeagueClient"')
print("FILE INFO:", stdout.read().decode())

stdin, stdout, stderr = ssh.exec_command('otool -f "/Applications/League of Legends.app/Contents/LoL/LeagueClient.app/Contents/MacOS/LeagueClient"')
print("FAT INFO:\n", stdout.read().decode())
ssh.close()
