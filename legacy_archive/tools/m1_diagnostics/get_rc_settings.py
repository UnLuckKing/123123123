import paramiko

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1', timeout=5)

cmd = "cat '/Users/m1/Library/Application Support/RiotClientData_slot1/Config/RiotClientSettings.yaml'"
_, out, _ = s.exec_command(cmd)
print("RiotClientSettings.yaml:")
print(out.read().decode())
s.close()
