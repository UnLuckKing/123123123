import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'find "/Applications/League of Legends_slot1.app" "/Applications/League of Legends_slot2.app" -name "lockfile"'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- APP LOCKFILES ---")
print(stdout.read().decode())

cmd = 'find "/Users/m1/Library/Application Support/RiotClientData_slot1" "/Users/m1/Library/Application Support/RiotClientData_slot2" -name "lockfile"'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- RIOT CLIENT DATA LOCKFILES ---")
print(stdout.read().decode())

ssh.close()
