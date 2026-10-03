import paramiko

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1', timeout=5)

cmd = "strings /Applications/'Riot Client.app'/Contents/MacOS/RiotClientServices | grep -iE 'close.*game|exit.*game|minimize.*game|game_launch|keep_open|close_on_game' | head -n 40"
_, out, _ = s.exec_command(cmd)
print("STRINGS RESULT:")
print(out.read().decode())
s.close()
