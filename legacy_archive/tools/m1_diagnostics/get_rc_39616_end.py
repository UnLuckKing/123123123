import paramiko

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1', timeout=5)

cmd = """python3 -c '
with open("/Users/m1/Library/Logs/Riot Games/Riot Client/Riot Client Logs/2026-09-29T23-45-01_39616_Riot Client.log") as f:
    lines = f.readlines()
    print("".join(lines[-60:]))
'"""

_, out, _ = s.exec_command(cmd)
print(out.read().decode())
s.close()
