import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

sftp = ssh.open_sftp()
with sftp.open('/Users/m1/vanta_orchestrator.py', 'r') as f:
    code = f.read().decode('utf-8')

# 1. Add self.client_ip = None to SlotState __init__
if "self.client_ip" not in code:
    code = code.replace("self.created_at     = time.time()", "self.client_ip     = None\n        self.created_at     = time.time()")
    print("Added self.client_ip to SlotState")

# 2. Update reaper max_idle to 60s
old_reaper = 'max_idle = 3600 if (s.status == "game_ready" or s.game_args) else 120'
new_reaper = 'max_idle = 60'
if old_reaper in code:
    code = code.replace(old_reaper, new_reaper)
    print("Updated reaper max_idle to 60s")
else:
    # Try any max_idle assignment in slot_reaper_loop
    import re
    code = re.sub(r'max_idle\s*=\s*.*', 'max_idle = 60', code)
    print("Regex updated reaper max_idle to 60s")

# 3. Update request_slot to auto-evict existing slots for the same client_ip
old_request = """                # If full, evict oldest slot
                if len(slots) >= MAX_SLOTS:"""

new_request = """                client_ip = self.client_address[0]
                # Auto-evict any previous slot for the same client IP
                for sid, s in list(slots.items()):
                    if getattr(s, "client_ip", "") == client_ip:
                        log(f"[slots] Auto-clearing previous slot {sid[:8]} for client {client_ip}")
                        _cleanup_slot_locked(sid)

                # If full, evict oldest slot
                if len(slots) >= MAX_SLOTS:"""

if old_request in code:
    code = code.replace(old_request, new_request)
    print("Added client IP auto-eviction to request_slot")

# Assign client_ip to new slot
old_assign = """                slot       = SlotState(slot_id, proxy_port, lcu_port, udp_proxy_port)
                slot.last_poll = time.time()"""

new_assign = """                slot       = SlotState(slot_id, proxy_port, lcu_port, udp_proxy_port)
                slot.client_ip = self.client_address[0]
                slot.last_poll = time.time()"""

if old_assign in code:
    code = code.replace(old_assign, new_assign)
    print("Assigned slot.client_ip in request_slot")

with sftp.open('/Users/m1/vanta_orchestrator.py', 'w') as f:
    f.write(code)

sftp.close()
print("Saved updated vanta_orchestrator.py to Mac M1")

# Restart orchestrator
ssh.exec_command('pkill -9 -f vanta_orchestrator.py; sleep 1; nohup python3 /Users/m1/vanta_orchestrator.py > /Users/m1/vanta_orchestrator.log 2>&1 &')
import time
time.sleep(2)
_, out, _ = ssh.exec_command('ps aux | grep vanta_orchestrator.py | grep -v grep')
print("Running status:", out.read().decode('utf-8'))
ssh.close()
