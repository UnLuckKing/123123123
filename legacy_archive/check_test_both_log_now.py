import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'grep -E "CONCURRENCY|FAILURE|game_ready" /tmp/test_both.log 2>/dev/null; tail -n 20 /tmp/test_both.log 2>/dev/null'
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())

ssh.close()
