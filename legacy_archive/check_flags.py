import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')
stdin, stdout, stderr = ssh.exec_command('strings "/Applications/Riot Client.app/Contents/MacOS/RiotClientServices" | grep "^--[a-z]"')
lines = stdout.read().decode().splitlines()
flags = set([l.split("=")[0] for l in lines if l.startswith("--")])
print("\n".join(sorted(list(flags))))
ssh.close()
