import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("51.159.121.126", username="m1", password="PNGGJHc5f7f1")

cmd = """python3 - << 'EOF'
import sqlite3
conn = sqlite3.connect('/Users/m1/vanta_auth.db')
c = conn.cursor()
c.execute("SELECT license_key, role, hwid, note, last_ip, datetime(last_seen, 'unixepoch') FROM licenses WHERE last_ip = '159.146.64.81'")
print("Active IP Licenses:", c.fetchall())
EOF
"""

stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode("utf-8", "ignore"))
ssh.close()
