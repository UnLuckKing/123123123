#!/usr/bin/env python3
# vanta_orchestrator.py - Multi-Slot Isolated Native RC REST API Orchestrator (V5.5 Apex Hybrid Engine)
# Mac M1 - Isolated Data Dirs, Dynamic Port Allocation, Zero-Collision Concurrency, UDP Relay & Instant X-Cleanup

import base64
import json
import os
import re
import shlex
import signal
import socket
import ssl
import subprocess
import sys
import threading
import time
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

# Configuration
ORCH_PORT       = 9000
MAX_SLOTS       = 5
BASE_USER_DIR   = "/Users/m1/Library/Application Support"
TEMPLATE_CONFIG = os.path.join(BASE_USER_DIR, "RiotClientData_slot1", "Config", "RiotClientSettings.yaml")

def log(msg: str):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")
    sys.stdout.flush()

slots: dict = {}
slots_lock = threading.Lock()
active_slot_nums: set = set()

class SlotState:
    def __init__(self, slot_id: str, slot_num: int):
        self.slot_id        = slot_id
        self.slot_num       = slot_num
        self.data_dir       = os.path.join(BASE_USER_DIR, f"RiotClientData_slot{slot_num}")
        self.proxy_port     = 8090 + (slot_num - 1)
        self.lcu_port       = 8100 + (slot_num - 1)
        self.udp_proxy_port = 8200 + (slot_num - 1)
        self.status         = "provisioning"
        self.args: list     = []
        self.game_args: list= []
        self.rc_port        = None
        self.rc_token       = None
        self.app_port       = None
        self.rc_proc        = None
        self.rc_pid         = None
        self.lc_pid         = None
        self.engine_pid     = None
        self.client_ip      = None
        self.created_at     = time.time()
        self.last_poll      = time.time()
        self._proxy_srv     = None
        self._lcu_srv       = None
        self._udp_srv       = None

def alloc_slot_num() -> int:
    for num in range(1, MAX_SLOTS + 1):
        if num not in active_slot_nums:
            active_slot_nums.add(num)
            return num
    raise RuntimeError("No free slot numbers available")

def free_slot_num(num: int):
    active_slot_nums.discard(num)

def read_lockfile(path: str):
    try:
        if os.path.exists(path):
            with open(path) as f:
                parts = f.read().strip().split(":")
            if len(parts) >= 4:
                return int(parts[2]), parts[3]
    except Exception:
        pass
    return None, None

def start_tcp_proxy(listen_port: int, target_port: int) -> socket.socket:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", listen_port))
    srv.listen(64)
    log(f"[proxy] TCP 0.0.0.0:{listen_port} -> 127.0.0.1:{target_port}")

    def relay(src, dst):
        try:
            while True:
                d = src.recv(65536)
                if not d: break
                dst.sendall(d)
        except Exception: pass
        finally:
            try: src.close()
            except: pass
            try: dst.close()
            except: pass

    def accept_loop():
        while True:
            try:
                client, _ = srv.accept()
            except Exception: break
            remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                remote.connect(("127.0.0.1", target_port))
            except Exception:
                client.close()
                continue
            threading.Thread(target=relay, args=(client, remote), daemon=True).start()
            threading.Thread(target=relay, args=(remote, client), daemon=True).start()

    threading.Thread(target=accept_loop, daemon=True).start()
    return srv

def start_udp_proxy(listen_port: int, target_ip: str, target_port: int) -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", listen_port))
    client_addr = None
    target_addr = (target_ip, target_port)
    log(f"[proxy] UDP 0.0.0.0:{listen_port} -> {target_ip}:{target_port}")

    def loop():
        nonlocal client_addr
        pkt_in = 0
        pkt_out = 0
        while True:
            try:
                data, addr = sock.recvfrom(65536)
                if addr[0] == target_ip:
                    if client_addr:
                        sock.sendto(data, client_addr)
                        pkt_out += 1
                        if pkt_out % 100 == 1:
                            log(f"[udp_proxy:{listen_port}] Server -> Client ({len(data)}B, total {pkt_out})")
                else:
                    client_addr = addr
                    sock.sendto(data, target_addr)
                    pkt_in += 1
                    if pkt_in % 100 == 1:
                        log(f"[udp_proxy:{listen_port}] Client -> Server ({len(data)}B from {addr}, total {pkt_in})")
            except Exception as e:
                log(f"[udp_proxy:{listen_port}] error: {e}")
                break

    threading.Thread(target=loop, daemon=True).start()
    return sock

def kill_pid_safe(pid: int, sig=signal.SIGKILL):
    if not pid: return
    try:
        os.kill(pid, sig)
    except ProcessLookupError:
        pass
    except Exception as err:
        log(f"[cleanup] Error killing PID {pid}: {err}")

def clean_slot_processes_isolated(slot: SlotState):
    """Terminates processes strictly belonging to this slot only. Zero cross-slot interference."""
    if slot.engine_pid:
        kill_pid_safe(slot.engine_pid)
        slot.engine_pid = None

    if slot.lc_pid:
        kill_pid_safe(slot.lc_pid)
        slot.lc_pid = None

    if slot.rc_proc:
        try: slot.rc_proc.kill()
        except: pass
        slot.rc_proc = None

    if slot.rc_pid:
        kill_pid_safe(slot.rc_pid)
        slot.rc_pid = None

    # Sweep for any auxiliary or child processes tied to this slot's data directory or ports
    patterns = []
    if slot.data_dir:
        patterns.append(f"--user-data-root={slot.data_dir}")
    if slot.rc_port:
        patterns.append(f"--riotclient-app-port={slot.rc_port}")
        patterns.append(f"-RiotClientPort={slot.rc_port}")
    if slot.app_port:
        patterns.append(f"--app-port={slot.app_port}")

    if patterns:
        try:
            ps_out = subprocess.check_output(["ps", "-axo", "pid,args"], timeout=5).decode(errors="replace")
            for line in ps_out.splitlines():
                if any(p in line for p in patterns) and "grep" not in line and "vanta_orchestrator" not in line:
                    parts = line.strip().split()
                    if parts and parts[0].isdigit():
                        p = int(parts[0])
                        kill_pid_safe(p)
        except Exception:
            pass

def capture_game_engine_loop(slot: SlotState):
    log(f"[game_monitor] Started 3D engine monitor for slot {slot.slot_num} ({slot.slot_id[:8]})")
    for _ in range(3600):
        with slots_lock:
            if slot.slot_id not in slots:
                break
        try:
            ps_out = subprocess.check_output(["ps", "-axo", "pid,ppid,command"], timeout=5).decode(errors="replace")
            for line in ps_out.splitlines():
                lower_line = line.lower()
                if "leagueoflegends" in lower_line and ("-gameid=" in lower_line or "-product=lol" in lower_line or "192.207." in lower_line or "104.160." in lower_line):
                    parts = line.strip().split()
                    if len(parts) < 3:
                        continue
                    try:
                        pid = int(parts[0])
                        ppid = int(parts[1])
                    except ValueError:
                        continue

                    with slots_lock:
                        other_claimed = any(s.engine_pid == pid for sid, s in slots.items() if sid != slot.slot_id)
                        if other_claimed or slot.engine_pid == pid:
                            continue

                    arg_start = None
                    for idx, token in enumerate(parts[2:], 2):
                        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", token):
                            arg_start = idx
                            break

                    if arg_start is None:
                        continue

                    game_args = parts[arg_start:]
                    target_ip = game_args[0]
                    target_port = int(game_args[1])

                    slot._udp_srv = start_udp_proxy(slot.udp_proxy_port, target_ip, target_port)

                    game_args[0] = "51.159.121.126"
                    game_args[1] = str(slot.udp_proxy_port)

                    with slots_lock:
                        slot.game_args = game_args
                        slot.engine_pid = pid

                    log(f"[game_monitor:slot{slot.slot_num}] Captured 3D Game Engine (PID {pid}, PPID {ppid}): Redirecting {target_ip}:{target_port} -> 51.159.121.126:{slot.udp_proxy_port}")
                    try:
                        os.kill(pid, signal.SIGSTOP)
                        log(f"[game_monitor:slot{slot.slot_num}] Suspended (SIGSTOP) Mac 3D engine PID {pid} to keep parent LeagueClient in 'InProgress' phase")
                    except Exception as err:
                        log(f"[game_monitor:slot{slot.slot_num}] Error suspending Mac game: {err}")

                    while True:
                        time.sleep(2.0)
                        with slots_lock:
                            if slot.slot_id not in slots:
                                return
                        try:
                            os.kill(pid, 0)
                        except OSError:
                            log(f"[game_monitor:slot{slot.slot_num}] 3D Game engine PID {pid} exited. Resetting monitor for next match.")
                            with slots_lock:
                                slot.game_args = None
                                slot.engine_pid = None
                                if slot._udp_srv:
                                    try: slot._udp_srv.close()
                                    except: pass
                                    slot._udp_srv = None
                            break
        except Exception as e:
            log(f"[game_monitor:slot{slot.slot_num}] error: {e}")
        time.sleep(1.0)


def vm_worker(slot: SlotState, yaml_data: str):
    try:
        log(f"[worker:slot{slot.slot_num}] Initializing isolated slot environment...")

        clean_slot_processes_isolated(slot)

        cfg_dir = os.path.join(slot.data_dir, "Config")
        data_dir = os.path.join(slot.data_dir, "Data")
        shared_dir = os.path.join(slot.data_dir, "SharedMetadata")
        os.makedirs(cfg_dir, exist_ok=True)
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(os.path.join(shared_dir, "league_of_legends.live"), exist_ok=True)

        app_path = f"/Applications/League of Legends_slot{slot.slot_num}.app"
        subprocess.run(f"rm -rf '{app_path}'", shell=True)
        subprocess.run(f"cp -c -R '/Applications/League of Legends.app' '{app_path}'", shell=True)
        
        meta_yaml = f"""auto_patching_enabled_by_player: false
dependencies: {{}}
patching_policy: "manual"
patchline_patching_ask_policy: "ask"
product_dependency: "teamfighttactics.live"
product_install_full_path: "{app_path}"
product_install_root: "/Applications"
settings:
    create_shortcut: false
    create_uninstall_key: false
    locale: "en_GB"
should_repair: false
"""
        with open(os.path.join(shared_dir, "league_of_legends.live", "league_of_legends.live.product_settings.yaml"), "w") as f:
            f.write(meta_yaml)

        lockfile_path = os.path.join(cfg_dir, "lockfile")
        if os.path.exists(lockfile_path):
            try: os.remove(lockfile_path)
            except: pass

        settings_yaml = os.path.join(cfg_dir, "RiotClientSettings.yaml")
        if os.path.exists(TEMPLATE_CONFIG) and not os.path.exists(settings_yaml):
            try:
                import shutil
                shutil.copyfile(TEMPLATE_CONFIG, settings_yaml)
            except: pass

        private_yaml = os.path.join(data_dir, "RiotGamesPrivateSettings.yaml")
        with open(private_yaml, "w") as f:
            f.write(yaml_data)

        cmd = [
            "/Applications/Riot Client.app/Contents/MacOS/RiotClientServices",
            "--allow-multiple-clients",
            f"--user-data-root={slot.data_dir}",
            f"--data-root={shared_dir}"
        ]
        
        env = os.environ.copy()
        env["VANTA_SLOT_NUM"] = str(slot.slot_num)
        proc = subprocess.Popen(cmd, env=env)
        slot.rc_proc = proc
        slot.rc_pid = proc.pid
        log(f"[worker:slot{slot.slot_num}] RiotClientServices spawned (PID {proc.pid}) with root {slot.data_dir}")

        rc_port, rc_token = None, None
        for _ in range(45):
            rc_port, rc_token = read_lockfile(lockfile_path)
            if rc_port and rc_token: break
            time.sleep(1)

        if not rc_port:
            _fail(slot, f"RC lockfile timeout in {slot.data_dir}")
            return

        slot.rc_port  = rc_port
        slot.rc_token = rc_token
        log(f"[worker:slot{slot.slot_num}] RC online at port {rc_port}")

        srv = start_tcp_proxy(slot.proxy_port, rc_port)
        slot._proxy_srv = srv

        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        auth_hdr = base64.b64encode(f"riot:{rc_token}".encode()).decode()

        session_ready = False
        for i in range(25):
            try:
                session_req = urllib.request.Request(
                    f"https://127.0.0.1:{rc_port}/rso-auth/v1/session",
                    headers={"Authorization": f"Basic {auth_hdr}"}
                )
                with urllib.request.urlopen(session_req, context=ctx, timeout=3) as resp:
                    data = json.loads(resp.read().decode())
                    if data.get("type") == "authenticated":
                        session_ready = True
                        break
            except: pass
            time.sleep(1)

        launch_url = f"https://127.0.0.1:{rc_port}/product-launcher/v1/products/league_of_legends/patchlines/live"
        req = urllib.request.Request(
            launch_url, data=b"{}",
            headers={"Authorization": f"Basic {auth_hdr}", "Content-Type": "application/json"}
        )

        launch_ok = False
        for attempt in range(20):
            try:
                with urllib.request.urlopen(req, context=ctx, timeout=5) as resp:
                    launch_ok = True
                    break
            except: time.sleep(2)

        if not launch_ok:
            _fail(slot, "Failed to trigger game launch via RC API")
            return

        for _ in range(60):
            try:
                ps = subprocess.check_output(["ps", "-axo", "pid,args"], timeout=5).decode(errors="replace")
                for line in ps.splitlines():
                    if ("grep" not in line
                            and ("LeagueClientUx" in line or "LeagueClient" in line)
                            and "--app-port=" in line
                            and (f"--riotclient-app-port={slot.rc_port}" in line or f"_slot{slot.slot_num}.app" in line or f"RiotClientData_slot{slot.slot_num}" in line)):
                        raw_parts = line.strip().split()
                        pid = int(raw_parts[0])
                        import shlex
                        args = shlex.split(line)[1:]
                        if args and ("LeagueClient" in args[0] or "LeagueClientUx" in args[0]):
                            args = args[1:]
                        app_port = None
                        for a in args:
                            if a.startswith("--app-port="):
                                try: app_port = int(a.split("=")[1])
                                except: pass
                                break
                        if app_port:
                            slot.app_port = app_port
                            slot.lc_pid = pid
                            slot._lcu_srv = start_tcp_proxy(slot.lcu_port, app_port)
                        with slots_lock:
                            slot.status = "game_ready"
                            slot.args   = args
                        threading.Thread(target=capture_game_engine_loop, args=(slot,), daemon=True).start()
                        return
            except: pass
            time.sleep(1.5)

        _fail(slot, "Timeout waiting for LeagueClient")
    except Exception as e:
        _fail(slot, f"exception: {e}")

def _fail(slot: SlotState, reason: str):
    with slots_lock:
        slot.status = reason
    log(f"[slot {slot.slot_num} ({slot.slot_id[:8]})] FAILED: {reason}")
    _cleanup_slot_locked(slot.slot_id)

def _cleanup_slot_locked(sid: str):
    if sid not in slots: return
    s = slots.pop(sid, None)
    if not s: return

    def _async_teardown(slot_obj: SlotState):
        if slot_obj._proxy_srv:
            try: slot_obj._proxy_srv.close()
            except: pass
        if slot_obj._lcu_srv:
            try: slot_obj._lcu_srv.close()
            except: pass
        if slot_obj._udp_srv:
            try: slot_obj._udp_srv.close()
            except: pass

        clean_slot_processes_isolated(slot_obj)

        lockfile = os.path.join(slot_obj.data_dir, "Config", "lockfile")
        if os.path.exists(lockfile):
            try: os.remove(lockfile)
            except: pass

        free_slot_num(slot_obj.slot_num)
        log(f"[slots] Freed slot {slot_obj.slot_num} ({sid[:8]}) and closed all isolated processes.")

    threading.Thread(target=_async_teardown, args=(s,), daemon=True).start()

def slot_reaper_loop():
    while True:
        time.sleep(5)
        now = time.time()
        stale = []
        with slots_lock:
            for sid, s in list(slots.items()):
                lp = getattr(s, "last_poll", now)
                # If client window was closed (clicking X) or client died, polling stops.
                # Reap after 45s of silence regardless of game phase.
                if (now - lp) > 45:
                    stale.append(sid)
            for sid in stale:
                stale_slot = slots.get(sid)
                snum = getattr(stale_slot, "slot_num", "?")
                log(f"[reaper] Slot {snum} ({sid[:8]}) timed out (idle > 45s, client closed), reaping...")
                _cleanup_slot_locked(sid)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        log(f"{self.address_string()} - {fmt % args}")

    def do_POST(self):
        if self.path == "/api/request_slot":
            length = int(self.headers.get("Content-Length", 0))
            yaml_data = self.rfile.read(length).decode()

            with slots_lock:
                client_ip = self.client_address[0]
                # Auto-evict any previous slot for the same client IP
                for sid, s in list(slots.items()):
                    if client_ip != "127.0.0.1" and getattr(s, "client_ip", "") == client_ip:
                        log(f"[slots] Auto-clearing previous slot {s.slot_num} ({sid[:8]}) for client {client_ip}")
                        _cleanup_slot_locked(sid)

                # If full, evict oldest idle slot
                if len(slots) >= MAX_SLOTS:
                    oldest_id = min(slots.keys(), key=lambda sid: getattr(slots[sid], "last_poll", 0))
                    log(f"[slots] Evicting stale slot {oldest_id[:8]} to make room")
                    _cleanup_slot_locked(oldest_id)

                try:
                    slot_num = alloc_slot_num()
                except Exception as e:
                    self._json(503, {"error": "no_available_slots"})
                    return

                slot_id        = str(uuid.uuid4())
                slot           = SlotState(slot_id, slot_num)
                slot.client_ip = self.client_address[0]
                slot.last_poll = time.time()
                slots[slot_id] = slot

            log(f"[http] request_slot -> slot_num={slot_num} slot_id={slot_id[:8]} proxy_port={slot.proxy_port} lcu_port={slot.lcu_port} udp_proxy_port={slot.udp_proxy_port}")
            threading.Thread(target=vm_worker, args=(slot, yaml_data), daemon=True).start()
            self._json(200, {
                "slot_id":        slot_id,
                "proxy_port":     slot.proxy_port,
                "lcu_port":       slot.lcu_port,
                "udp_proxy_port": slot.udp_proxy_port
            })
        elif self.path in ("/api/slots/reset", "/api/slots/clear_all"):
            with slots_lock:
                slot_ids = list(slots.keys())
                for sid in slot_ids:
                    _cleanup_slot_locked(sid)
            subprocess.run("pkill -9 -f 'LeagueClient' || true", shell=True)
            subprocess.run("pkill -9 -f 'LeagueofLegends' || true", shell=True)
            subprocess.run("pkill -9 -f 'RiotClientServices' || true", shell=True)
            subprocess.run("pkill -9 -f 'Riot Client' || true", shell=True)
            log(f"[admin] Full reset: cleared {len(slot_ids)} slots and killed all background Riot processes")
            self._json(200, {"success": True, "cleared_slots": len(slot_ids)})
        elif self.path == "/api/slots/kill":
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode() if length > 0 else "{}"
            try: payload = json.loads(raw)
            except Exception: payload = {}
            sid = payload.get("slot_id")
            with slots_lock:
                if sid in slots:
                    slot_num = slots[sid].slot_num
                    _cleanup_slot_locked(sid)
                    log(f"[admin] Client requested kill: freed slot {slot_num} ({sid[:8]})")
                    self._json(200, {"success": True, "killed": sid})
                else:
                    self._json(404, {"error": "not_found"})
        else:
            self.send_response(404); self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path == "/api/poll_slot":
            slot_id = params.get("slot_id", [None])[0]
            with slots_lock:
                slot = slots.get(slot_id)
            if not slot:
                self._json(404, {"error": "not_found"})
                return

            slot.last_poll = time.time()
            self._json(200, {
                "status":     slot.status,
                "args":       slot.args,
                "game_args":  slot.game_args,
                "proxy_port": slot.proxy_port,
                "lcu_port":   slot.lcu_port,
                "rc_port":    slot.rc_port,
            })
        elif parsed.path == "/api/slots":
            res = {}
            with slots_lock:
                for sid, s in slots.items():
                    now = time.time()
                    lp = getattr(s, "last_poll", now)
                    res[sid] = {
                        "slot_num":          s.slot_num,
                        "status":            s.status,
                        "proxy_port":        s.proxy_port,
                        "lcu_port":          s.lcu_port,
                        "udp_proxy_port":    s.udp_proxy_port,
                        "game_active":       len(getattr(s, "game_args", [])) > 0,
                        "last_poll_seconds": int(now - lp),
                        "client_ip":         getattr(s, "client_ip", "unknown")
                    }
            self._json(200, {"slots": res, "active_count": len(res)})
        elif parsed.path == "/api/health":
            self._json(200, {"ok": True, "active_slots": len(slots)})
        else:
            self.send_response(404); self.end_headers()

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", ORCH_PORT), Handler)
    threading.Thread(target=slot_reaper_loop, daemon=True).start()
    log(f"[server] VANTA multi-slot orchestrator V5.5 listening on 0.0.0.0:{ORCH_PORT}")
    server.serve_forever()
