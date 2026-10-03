import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = """
python3 -c '
with open("/Users/m1/orchestrator.log", "r", errors="replace") as f:
    lines = f.readlines()
for line in lines:
    if "slot2" in line or "slot 2" in line or "FAILED" in line:
        print(line.strip())
'
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print("SLOT 2 LOG ENTRIES:\n" + stdout.read().decode())
ssh.close()
