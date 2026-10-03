import re
import paramiko

with open("vanta_orchestrator_remote.py", "r", encoding="utf-8") as f:
    code = f.read()

# Check if /api/slots/reset already in code
if "/api/slots/reset" not in code:
    target = '            self._json(200, {\n                "slot_id": slot_id,\n                "proxy_port": proxy_port,\n                "lcu_port": lcu_port,\n                "udp_proxy_port": udp_proxy_port\n            })'
    replacement = '''            self._json(200, {
                "slot_id": slot_id,
                "proxy_port": proxy_port,
                "lcu_port": lcu_port,
                "udp_proxy_port": udp_proxy_port
            })
        elif self.path == "/api/slots/reset":
            with slots_lock:
                slot_ids = list(slots.keys())
                for sid in slot_ids:
                    _cleanup_slot_locked(sid)
            import subprocess
            subprocess.run("pkill -9 -f 'LeagueClient' || true", shell=True)
            subprocess.run("pkill -9 -f 'LeagueofLegends' || true", shell=True)
            subprocess.run("pkill -9 -f 'RiotClientServices' || true", shell=True)
            log(f"[admin] Reset all {len(slot_ids)} slots and killed background Riot processes")
            self._json(200, {"success": True, "cleared_slots": len(slot_ids)})
        elif self.path == "/api/slots/kill":
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode() if length > 0 else "{}"
            try:
                payload = json.loads(raw)
            except Exception:
                payload = {}
            sid = payload.get("slot_id")
            with slots_lock:
                if sid in slots:
                    _cleanup_slot_locked(sid)
                    log(f"[admin] Manually killed slot {sid[:8]}")
                    self._json(200, {"success": True, "killed": sid})
                else:
                    self._json(404, {"error": "not_found"})'''
    if target in code:
        code = code.replace(target, replacement, 1)
        print("Patched do_POST in vanta_orchestrator.py successfully")
    else:
        print("Target string not found in orchestrator!")

with open("vanta_orchestrator_updated.py", "w", encoding="utf-8") as f:
    f.write(code)

# Upload and restart on Mac
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("51.159.121.126", username="m1", password="PNGGJHc5f7f1")
sftp = ssh.open_sftp()
with sftp.open("/Users/m1/vanta_orchestrator.py", "w") as f:
    f.write(code)
sftp.close()
print("Uploaded vanta_orchestrator.py to Mac")

stdin, stdout, stderr = ssh.exec_command("pkill -9 -f vanta_orchestrator.py || true; nohup python3 /Users/m1/vanta_orchestrator.py > /Users/m1/vanta_orchestrator.log 2>&1 &")
stdout.channel.recv_exit_status()

# Verify orchestrator is up
stdin, stdout, stderr = ssh.exec_command("sleep 1; ps aux | grep vanta_orchestrator; curl -s http://127.0.0.1:9000/api/health")
print("Orchestrator health check:", stdout.read().decode())
ssh.close()
