import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

print("Creating APFS CoW clones for slots 1 to 5...")
for i in range(1, 6):
    app_path = f"/Applications/League of Legends_slot{i}.app"
    cmd = f'if [ ! -d "{app_path}" ]; then echo "Cloning slot{i}..."; cp -c -R "/Applications/League of Legends.app" "{app_path}"; fi'
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode().strip()
    if out: print(out)

stdin, stdout, stderr = ssh.exec_command('ls -d /Applications/League*')
print("Active Application bundles:")
print(stdout.read().decode())

ssh.close()
