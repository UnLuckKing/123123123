import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

print("--- test_slot2_e2e.py ---")
stdin, stdout, stderr = ssh.exec_command('cat /Users/m1/test_slot2_e2e.py')
print(stdout.read().decode())

print("--- setup_slots.py ---")
stdin, stdout, stderr = ssh.exec_command('cat /Users/m1/setup_slots.py')
print(stdout.read().decode())

ssh.close()
