import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'grep -i "vanta_orchestrator" /Users/m1/.*history 2>/dev/null; head -n 30 /Users/m1/vanta_orchestrator.py.bak* 2>/dev/null; ls -la /Users/m1/*.py'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- SEARCH PY ---")
print(stdout.read().decode())

ssh.close()
