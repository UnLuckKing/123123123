import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("51.159.121.126", username="m1", password="PNGGJHc5f7f1")

cmd = """python3 - << 'EOF'
import sqlite3, time
conn = sqlite3.connect('/Users/m1/vanta_auth.db')
c = conn.cursor()
c.execute("SELECT timestamp, severity, source, message, details FROM diagnostics WHERE client_ip = '159.146.64.81' ORDER BY id DESC LIMIT 20")
rows = c.fetchall()
for r in reversed(rows):
    t_str = time.strftime('%H:%M:%S', time.localtime(r[0]))
    print(f"{t_str} | {r[1]:<5} | {r[2]:<15} | {r[3]} | {r[4]}")
EOF
"""

stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode("utf-8", "ignore"))
ssh.close()
