import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("51.159.121.126", username="m1", password="PNGGJHc5f7f1")

alter_script = """
import sqlite3
conn = sqlite3.connect('/Users/m1/vanta_auth.db')
c = conn.cursor()
try:
    c.execute('ALTER TABLE licenses ADD COLUMN last_ip TEXT')
    print('Added last_ip')
except Exception as e:
    print('last_ip:', e)
try:
    c.execute('ALTER TABLE licenses ADD COLUMN last_seen INTEGER')
    print('Added last_seen')
except Exception as e:
    print('last_seen:', e)
conn.commit()
conn.close()
"""

stdin, stdout, stderr = ssh.exec_command(f'python3 -c "{alter_script}"')
print("DB Migration output:", stdout.read().decode())
print("DB Migration stderr:", stderr.read().decode())
ssh.close()
