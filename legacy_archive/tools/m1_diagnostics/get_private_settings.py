import paramiko

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1', timeout=5)

cmd = "head -n 50 /Users/m1/VantaSlots/slot1/Data/RiotGamesPrivateSettings.yaml"
_, out, _ = s.exec_command(cmd)
print("RiotGamesPrivateSettings.yaml:")
print(out.read().decode())
s.close()
