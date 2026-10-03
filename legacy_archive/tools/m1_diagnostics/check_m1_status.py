import paramiko

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1', timeout=5)

_, out, _ = s.exec_command("sqlite3 /Users/m1/vanta_auth.db 'SELECT timestamp, event_type, license_key, client_ip, details FROM audit_logs ORDER BY id DESC LIMIT 10;'")
print("=== AUDIT LOGS ===")
print(out.read().decode())

_, out2, _ = s.exec_command("sqlite3 /Users/m1/vanta_auth.db 'SELECT timestamp, severity, source, message, details FROM diagnostics ORDER BY id DESC LIMIT 10;'")
print("=== DIAGNOSTICS ===")
print(out2.read().decode())

_, out3, _ = s.exec_command("ps aux | grep -i [l]eague")
print("=== RUNNING PROCESSES ON M1 ===")
print(out3.read().decode())

_, out4, _ = s.exec_command("tail -n 30 /Users/m1/vanta_orchestrator.log 2>/dev/null || tail -n 30 /tmp/orchestrator.log 2>/dev/null || echo 'no log file'")
print("=== ORCHESTRATOR LOG ===")
print(out4.read().decode())

s.close()
