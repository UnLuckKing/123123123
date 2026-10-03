import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

stdin, stdout, stderr = ssh.exec_command('lsof -p 31834 | grep -i lock; lsof -p 31839 | grep -i lock')
print("--- LSOF LOCKFILES ---")
print(stdout.read().decode())

stdin, stdout, stderr = ssh.exec_command('cat /tmp/rcs_slot1.log; echo "--- SLOT2 LOG ---"; cat /tmp/rcs_slot2.log')
print("--- LOGS ---")
print(stdout.read().decode())

ssh.close()
