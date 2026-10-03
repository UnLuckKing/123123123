import paramiko

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1', timeout=5)

cmd = """python3 -c '
import glob, os
logs = glob.glob("/Users/m1/Library/Logs/**/Riot*/**/*", recursive=True)
for l in sorted(logs, key=os.path.getmtime)[-10:]:
    if os.path.isfile(l):
        print(l, os.path.getmtime(l), os.path.getsize(l))
'"""

_, out, _ = s.exec_command(cmd)
print(out.read().decode())
s.close()
