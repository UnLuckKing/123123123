import paramiko

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1', timeout=5)

cmd = """python3 -c '
with open("/Users/m1/orchestrator.log") as f:
    lines = [l for l in f if any(k in l for k in ["game_monitor", "Suspended", "exited", "Freed", "3D Game", "Client requested kill", "reaper"])]
    print("".join(lines[-30:]))
'"""
_, out, _ = s.exec_command(cmd)
print("=== LOG FILTER RESULT ===")
print(out.read().decode())
s.close()
