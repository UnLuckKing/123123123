import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

print("Purging local snapshots...")
stdin, stdout, stderr = ssh.exec_command('echo PNGGJHc5f7f1 | sudo -S tmutil thinlocalsnapshots / 100000000000 4')
print(stdout.read().decode())
print(stderr.read().decode())

stdin, stdout, stderr = ssh.exec_command('df -h /System/Volumes/Data')
print(stdout.read().decode())

ssh.close()
