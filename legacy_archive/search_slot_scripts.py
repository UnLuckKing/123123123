import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'grep -rnw "/Users/m1" -e "slot1" -e "sudo -u" 2>/dev/null | head -n 30; grep -rnw "/Users" --include="*.py" --include="*.sh" -e "asuser" -e "launchctl" 2>/dev/null | head -n 30'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- SEARCH SCRIPTS ---")
print(stdout.read().decode())
print(stderr.read().decode())

ssh.close()
