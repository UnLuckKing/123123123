import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')
stdin, stdout, stderr = ssh.exec_command('sysctl hw.memsize machdep.cpu.brand_string; df -h /')
print(stdout.read().decode())
stdin, stdout, stderr = ssh.exec_command('tail -n 35 /Users/m1/orchestrator.log')
print("--- ORCH LOG ---")
print(stdout.read().decode())
ssh.close()
