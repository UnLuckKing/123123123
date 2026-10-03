import paramiko

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1', timeout=5)

cmd = "ls -la /Applications/'Riot Client.app'/Contents/MacOS/"
_, out, _ = s.exec_command(cmd)
print("RiotClient.app/Contents/MacOS/:")
print(out.read().decode())

cmd2 = "ls -la /Applications/'League of Legends.app'/Contents/LoL/"
_, out2, _ = s.exec_command(cmd2)
print("League of Legends.app/Contents/LoL/:")
print(out2.read().decode())

s.close()
