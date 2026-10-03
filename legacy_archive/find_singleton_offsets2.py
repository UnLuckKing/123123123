import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = """
python3 -c '
with open("/Applications/League of Legends.app/Contents/LoL/LeagueClient.app/Contents/MacOS/LeagueClient", "rb") as f:
    d = f.read()

print("File size:", len(d))
targets = [b"Did not acquire process singleton", b"Client already running", b"Acquired process singleton"]
for t in targets:
    pos = 0
    while True:
        idx = d.find(t, pos)
        if idx == -1: break
        print(f"Found {t} at 0x{idx:x}")
        pos = idx + 1
'
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
print("STDERR:", stderr.read().decode())
ssh.close()
