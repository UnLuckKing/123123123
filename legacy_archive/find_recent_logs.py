import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'find "/Users/m1/Library/Logs" -type f -mtime -2 2>/dev/null'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("RECENT LOGS IN /Users/m1/Library/Logs:")
print(stdout.read().decode('utf-8', 'ignore'))

cmd2 = 'find "/Users/m1/VantaSlots" -type f -name "*.log" 2>/dev/null'
stdin, stdout, stderr = ssh.exec_command(cmd2)
print("RECENT LOGS IN VantaSlots:")
print(stdout.read().decode('utf-8', 'ignore'))

ssh.close()
