import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'python3 -c "import sqlite3; conn = sqlite3.connect(\'/Users/m1/vanta_auth.db\'); c = conn.cursor(); c.execute(\'SELECT id, license_key, role, reseller_id, hwid, status, note FROM licenses\'); print(c.fetchall())"'

stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:", stdout.read().decode())
print("STDERR:", stderr.read().decode())
ssh.close()
