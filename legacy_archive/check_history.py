import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'tail -n 60 ~/.zsh_history | tr -cd "\\11\\12\\15\\40-\\176"'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- ZSH HISTORY ---")
print(stdout.read().decode())

ssh.close()
