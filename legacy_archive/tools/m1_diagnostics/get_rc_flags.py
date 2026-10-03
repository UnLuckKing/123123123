import paramiko

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1', timeout=5)

cmd = "/Applications/'Riot Client.app'/Contents/MacOS/RiotClientServices --help"
_, out, _ = s.exec_command(cmd)
print("HELP OUTPUT:")
print(out.read().decode())

cmd2 = "strings /Applications/'Riot Client.app'/Contents/MacOS/RiotClientServices | grep -E '\-\-[a-z0-9\-]{5,}' | head -n 40"
_, out2, _ = s.exec_command(cmd2)
print("CLI FLAGS:")
print(out2.read().decode())

s.close()
