import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'find /private/tmp -mmin -2 -type f'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- NEW FILES IN /TMP ---")
print(stdout.read().decode())

cmd = 'find /private/var/folders -mmin -2 -name "*lockfile*"'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- LOCKFILES IN VAR FOLDERS ---")
print(stdout.read().decode())

ssh.close()
