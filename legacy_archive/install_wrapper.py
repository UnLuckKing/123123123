import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')
sftp = ssh.open_sftp()

print("Uploading updated LeagueClient_wrapper.sh...")
sftp.put('LeagueClient_wrapper.sh', '/Users/m1/LeagueClient_wrapper.sh')
sftp.close()

print("Deploying wrapper to LeagueClient app...")
cmd = "cd '/Applications/League of Legends.app/Contents/LoL/LeagueClient.app/Contents/MacOS' && cp /Users/m1/LeagueClient_wrapper.sh LeagueClient && chmod +x LeagueClient"
ssh.exec_command(cmd)
ssh.close()
print("Done")
