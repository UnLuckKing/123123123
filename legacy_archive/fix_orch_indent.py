import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("51.159.121.126", username="m1", password="PNGGJHc5f7f1")

sftp = ssh.open_sftp()
with sftp.open("/Users/m1/vanta_orchestrator.py", "r") as f:
    lines = f.readlines()

new_lines = []
skip = False
for l in lines:
    if 'elif parsed.path == "/api/slots":' in l:
        skip = True
    if skip and 'elif parsed.path == "/api/health":' in l:
        skip = False
        new_lines.append("""        elif parsed.path == "/api/slots":
            res = {}
            with slots_lock:
                for sid, s in slots.items():
                    now = time.time()
                    lp = getattr(s, "last_poll", now)
                    res[sid] = {
                        "status": s.status,
                        "proxy_port": s.proxy_port,
                        "lcu_port": s.lcu_port,
                        "udp_proxy_port": s.udp_proxy_port,
                        "game_active": len(getattr(s, "game_args", [])) > 0,
                        "last_poll_seconds": int(now - lp)
                    }
            self._json(200, {"slots": res})\n""")
    if not skip:
        new_lines.append(l)

with sftp.open("/Users/m1/vanta_orchestrator.py", "w") as f:
    f.writelines(new_lines)
sftp.close()

stdin, stdout, stderr = ssh.exec_command("""
pkill -9 -f vanta_orchestrator.py
nohup /Applications/Xcode.app/Contents/Developer/Library/Frameworks/Python3.framework/Versions/3.9/Resources/Python.app/Contents/MacOS/Python /Users/m1/vanta_orchestrator.py > /Users/m1/vanta_orchestrator.log 2>&1 &
sleep 2
curl -s http://127.0.0.1:9000/api/slots
echo ""
curl -s http://127.0.0.1:9000/api/health
""")
print(stdout.read().decode("utf-8", "ignore"))
ssh.close()
