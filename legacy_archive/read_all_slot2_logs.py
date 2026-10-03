import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'find /Users/slot2 -name "*.log" | xargs tail -n 15'
stdin, stdout, stderr = ssh.exec_command(f'echo PNGGJHc5f7f1 | sudo -S {cmd}')
print("--- ALL LOGS FOR SLOT2 ---")
print(stdout.read().decode())

ssh.close()
