import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

# Check what happened in /tmp/slot2.log or launcher logs
cmd = 'ls -la /tmp/*.log'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("TMP LOGS:")
print(stdout.read().decode('utf-8', 'ignore'))

# Check the content of /tmp/rcs_slot1.log and /tmp/rcs_slot2.log or /tmp/slot2.log
cmd2 = 'tail -n 25 /tmp/slot2.log 2>/dev/null; tail -n 25 /tmp/rcs_slot2.log 2>/dev/null'
stdin, stdout, stderr = ssh.exec_command(cmd2)
print("CONTENT:")
print(stdout.read().decode('utf-8', 'ignore'))

ssh.close()
