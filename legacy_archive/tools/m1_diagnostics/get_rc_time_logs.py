import paramiko

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1', timeout=5)

cmd = """python3 -c '
import glob, os
logs = glob.glob("/Users/m1/Library/Logs/Riot Games/Riot Client/Riot Client Logs/*.log")
for l in sorted(logs):
    print(l)
    with open(l) as f:
        content = f.read()
        if "23:51" in content or "23:50" in content or "23:45" in content:
            print("--- MATCH FOUND IN", l, "---")
            lines = [line for line in content.splitlines() if any(k in line for k in ["23:50", "23:51", "23:52", "disconnect", "close", "session", "quit", "exit", "token"])]
            print("\\n".join(lines[-30:]))
'"""

_, out, _ = s.exec_command(cmd)
print(out.read().decode())
s.close()
