import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("51.159.121.126", username="m1", password="PNGGJHc5f7f1")

cmd = "python3 -c \"with open('/Users/m1/vanta_hub.py') as f: lines = f.readlines(); print(len(lines)); [print(i, l.strip()) for i, l in enumerate(lines) if 'total_slots' in l]\""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode("utf-8", "ignore"))
ssh.close()
