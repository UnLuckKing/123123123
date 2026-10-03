import paramiko

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1', timeout=5)

cmd = "python3 -c 'import sqlite3; conn = sqlite3.connect(\"/Users/m1/vanta_auth.db\"); print(conn.execute(\"SELECT name FROM sqlite_master WHERE type=\\\"table\\\"\").fetchall()); conn.close()'"
_, out, _ = s.exec_command(cmd)
print("TABLES:")
print(out.read().decode())
s.close()
