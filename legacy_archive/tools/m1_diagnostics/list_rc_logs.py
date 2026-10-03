import paramiko

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1', timeout=5)

cmd = """python3 -c '
import glob, os
files = sorted(glob.glob("/Users/m1/Library/Logs/Riot Games/Riot Client/Riot Client Logs/*"), key=os.path.getmtime)
for f in files[-10:]:
    print(f, os.path.getmtime(f), os.path.getsize(f))
'"""

_, out, _ = s.exec_command(cmd)
print(out.read().decode())
s.close()
