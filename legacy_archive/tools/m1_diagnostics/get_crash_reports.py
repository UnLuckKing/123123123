import paramiko

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1', timeout=5)

cmd = """python3 -c '
import glob, os
crashes = glob.glob("/Users/m1/Library/Logs/DiagnosticReports/*") + glob.glob("/Library/Logs/DiagnosticReports/*")
for c in crashes:
    if "Riot" in c or "League" in c:
        print(c, os.path.getmtime(c))
'"""

_, out, _ = s.exec_command(cmd)
print("CRASH REPORTS:")
print(out.read().decode())
s.close()
