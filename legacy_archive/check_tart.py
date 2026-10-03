import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'ls -la /Applications/tart.app; ls -la /Applications/tart.app/Contents/MacOS/; /Applications/tart.app/Contents/MacOS/tart --version 2>&1'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- TART ---")
print(stdout.read().decode())
print(stderr.read().decode())

# Check tart list
cmd_list = '/Applications/tart.app/Contents/MacOS/tart list 2>&1'
stdin, stdout, stderr = ssh.exec_command(cmd_list)
print("--- TART LIST ---")
print(stdout.read().decode())

ssh.close()
