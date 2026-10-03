import paramiko

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1', timeout=5)

cmd = """python3 -c '
with open("/Users/m1/orchestrator.log") as f:
    lines = [l for l in f if "23:52" in l or "23:51" in l or "23:53" in l]
    print("".join(lines))
'"""

_, out, _ = s.exec_command(cmd)
print("ORCHESTRATOR:")
print(out.read().decode())

cmd2 = """python3 -c '
import os
for p in ["/Users/m1/vanta_hub.log", "/Users/m1/hub.log"]:
    if os.path.exists(p):
        print(f"=== {p} ===")
        with open(p) as f:
            lines = [l for l in f if "23:52" in l or "kill" in l or "slots" in l]
            print("".join(lines[-20:]))
'"""
_, out2, _ = s.exec_command(cmd2)
print("HUB:")
print(out2.read().decode())

s.close()
