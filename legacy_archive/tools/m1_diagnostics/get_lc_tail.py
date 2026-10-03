import paramiko

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1', timeout=5)

cmd = """python3 -c '
import glob
files = sorted(glob.glob("/Applications/League of Legends_slot1.app/Contents/LoL/Logs/LeagueClient Logs/*_LeagueClient.log"))
if files:
    with open(files[-1]) as f:
        lines = f.readlines()
        print("Latest log:", files[-1])
        print("".join(lines[-80:]))
'"""

_, out, _ = s.exec_command(cmd)
print(out.read().decode())
s.close()
