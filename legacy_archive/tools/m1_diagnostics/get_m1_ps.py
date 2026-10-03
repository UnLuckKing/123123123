import paramiko

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1', timeout=5)

cmd = "ps -axo pid,ppid,command | grep -E 'Riot|League|vanta'"
_, out, _ = s.exec_command(cmd)
print("RUNNING PROCESSES:")
print(out.read().decode())
s.close()
