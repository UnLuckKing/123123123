import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("51.159.121.126", username="m1", password="PNGGJHc5f7f1")

sftp = ssh.open_sftp()
with sftp.open("/Users/m1/vanta_orchestrator.py", "r") as f:
    content = f.read().decode("utf-8")

# Replace slot management logic with auto-reaper and eviction
old_block = """            with slots_lock:
                if len(slots) >= MAX_SLOTS:
                    self._json(503, {"error": "slot_pool_full"})
                    return
                slot_id    = str(uuid.uuid4())
                proxy_port, lcu_port, udp_proxy_port = alloc_proxy_ports()
                slot       = SlotState(slot_id, proxy_port, lcu_port, udp_proxy_port)
                slots[slot_id] = slot"""

new_block = """            with slots_lock:
                # If full, evict oldest slot
                if len(slots) >= MAX_SLOTS:
                    oldest_id = min(slots.keys(), key=lambda sid: getattr(slots[sid], "last_poll", 0))
                    log(f"[slots] Evicting stale slot {oldest_id[:8]} to make room")
                    _cleanup_slot_locked(oldest_id)

                slot_id    = str(uuid.uuid4())
                proxy_port, lcu_port, udp_proxy_port = alloc_proxy_ports()
                slot       = SlotState(slot_id, proxy_port, lcu_port, udp_proxy_port)
                slot.last_poll = time.time()
                slots[slot_id] = slot"""

cleanup_helpers = """
def _cleanup_slot_locked(sid: str):
    if sid not in slots: return
    s = slots.pop(sid, None)
    if not s: return
    if s._proxy_srv:
        try: s._proxy_srv.close()
        except: pass
    if s._lcu_srv:
        try: s._lcu_srv.close()
        except: pass
    if s._udp_srv:
        try: s._udp_srv.close()
        except: pass
    free_proxy_ports(s.proxy_port, s.lcu_port, s.udp_proxy_port)
    log(f"[slots] Cleaned up & freed slot {sid[:8]}")

def slot_reaper_loop():
    while True:
        time.sleep(10)
        now = time.time()
        with slots_lock:
            stale = []
            for sid, s in slots.items():
                lp = getattr(s, "last_poll", now)
                # If slot has not been polled for > 60s, reap it
                if (now - lp) > 60:
                    stale.append(sid)
            for sid in stale:
                log(f"[reaper] Slot {sid[:8]} timed out (idle > 60s), reaping...")
                _cleanup_slot_locked(sid)
"""

content = content.replace("class Handler(BaseHTTPRequestHandler):", cleanup_helpers + "\nclass Handler(BaseHTTPRequestHandler):")
content = content.replace(old_block, new_block)

# Start reaper in __main__
main_old = '    log(f"[server] VANTA orchestrator V5 listening on 0.0.0.0:{ORCH_PORT}")'
main_new = '    threading.Thread(target=slot_reaper_loop, daemon=True).start()\n    log(f"[server] VANTA orchestrator V5 listening on 0.0.0.0:{ORCH_PORT}")'
content = content.replace(main_old, main_new)

with sftp.open("/Users/m1/vanta_orchestrator.py", "w") as f:
    f.write(content)
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
print("PATCHED & RESTARTED SUCCESSFULLY")
