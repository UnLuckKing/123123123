import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = """
python3 -c '
with open("/Users/m1/Library/Logs/Riot Games/Riot Client/Riot Client Logs/2026-09-29T23-38-06_38858_Riot Client.log") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "productSessionEnd" in line:
        start = max(0, i - 30)
        end = min(len(lines), i + 10)
        print("".join(lines[start:end]))
'
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
ssh.close()
