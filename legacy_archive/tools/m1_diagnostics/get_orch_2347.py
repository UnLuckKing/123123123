import paramiko

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1', timeout=5)

cmd = """python3 -c '
with open("/Users/m1/orchestrator.log") as f:
    lines = [l for l in f if "23:45" in l or "23:46" in l or "23:47" in l or "23:48" in l or "23:49" in l or "23:50" in l]
    print("".join(lines[-40:]))
'"""

_, out, _ = s.exec_command(cmd)
print(out.read().decode())
s.close()
