import paramiko

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1', timeout=5)

cmd = """python3 -c '
with open("/Users/m1/Library/Logs/Riot Games/Riot Client/Riot Client Logs/2026-09-29T23-48-01_39881_Riot Client.log") as f:
    lines = f.readlines()
    print("Total lines:", len(lines))
    print("First 20 lines:")
    print("".join(lines[:20]))
    print("Last 20 lines:")
    print("".join(lines[-20:]))
'"""

_, out, _ = s.exec_command(cmd)
print(out.read().decode())
s.close()
