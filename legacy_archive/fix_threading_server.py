import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("51.159.121.126", username="m1", password="PNGGJHc5f7f1")

sftp = ssh.open_sftp()
with sftp.open("/Users/m1/vanta_orchestrator.py", "r") as f:
    code = f.read().decode("utf-8")

# 1. Use ThreadingHTTPServer
code = code.replace(
    "from http.server import BaseHTTPRequestHandler, HTTPServer",
    "from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer"
)
code = code.replace(
    'server = HTTPServer(("0.0.0.0", ORCH_PORT), Handler)',
    'server = ThreadingHTTPServer(("0.0.0.0", ORCH_PORT), Handler)'
)

# 2. Make slot reaper non-blocking and safe
safe_reaper = """
def _cleanup_slot_locked(sid: str):
    if sid not in slots: return
    s = slots.pop(sid, None)
    if not s: return
    def _close_sockets(slot_obj):
        if slot_obj._proxy_srv:
            try: slot_obj._proxy_srv.close()
            except: pass
        if slot_obj._lcu_srv:
            try: slot_obj._lcu_srv.close()
            except: pass
        if slot_obj._udp_srv:
            try: slot_obj._udp_srv.close()
            except: pass
        free_proxy_ports(slot_obj.proxy_port, slot_obj.lcu_port, slot_obj.udp_proxy_port)
    threading.Thread(target=_close_sockets, args=(s,), daemon=True).start()
    log(f"[slots] Freed slot {sid[:8]}")

def slot_reaper_loop():
    while True:
        time.sleep(10)
        now = time.time()
        stale = []
        with slots_lock:
            for sid, s in list(slots.items()):
                lp = getattr(s, "last_poll", now)
                # Keep active for at least 10 minutes if status is game_ready
                max_idle = 180 if s.status == "game_ready" else 90
                if (now - lp) > max_idle:
                    stale.append(sid)
            for sid in stale:
                log(f"[reaper] Slot {sid[:8]} timed out (idle > {max_idle}s), reaping...")
                _cleanup_slot_locked(sid)
"""

# Replace cleanup_helpers in code
idx = code.find("def _cleanup_slot_locked")
if idx != -1:
    end_idx = code.find("class Handler(BaseHTTPRequestHandler):")
    code = code[:idx] + safe_reaper.strip() + "\n\n" + code[end_idx:]

with sftp.open("/Users/m1/vanta_orchestrator.py", "w") as f:
    f.write(code)
sftp.close()

# Restart orchestrator
stdin, stdout, stderr = ssh.exec_command("""
pkill -9 -f vanta_orchestrator.py
nohup /Applications/Xcode.app/Contents/Developer/Library/Frameworks/Python3.framework/Versions/3.9/Resources/Python.app/Contents/MacOS/Python /Users/m1/vanta_orchestrator.py > /Users/m1/vanta_orchestrator.log 2>&1 &
sleep 2
curl -s http://127.0.0.1:9000/api/health
""")
print(stdout.read().decode("utf-8", "ignore"))
ssh.close()
