#!/usr/bin/env python3
# vanta_orchestrator.py - 25-Slot Zero-Collision Vanguard Mac Bypass Orchestrator (Apex v6.3)
# Multi-tenant headless broker for League of Legends on macOS M1 Apple Silicon
# Isolated APFS App Bundles (Slots 1-25), Non-Overlapping Dedicated Ports, Persistent Telemetry DB

import base64
import hashlib
import json
import os
import re
import shlex
import signal
import socket
import sqlite3
import ssl
import subprocess
import sys
import threading
import time
import urllib.request
import urllib.error
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

# ── Global Configuration ───────────────────────────────────────────────────────
ORCH_PORT       = 9000
MAX_SLOTS       = 25
BASE_SLOTS_DIR  = "/Users/m1/VantaSlots"
BASE_APP_PATH   = "/Applications/League of Legends.app"
RC_APP_PATH     = "/Applications/Riot Client.app/Contents/MacOS/RiotClientServices"
TEMPLATE_CONFIG = "/Users/m1/Library/Application Support/RiotClientData_slot1/Config/RiotClientSettings.yaml"
DB_PATH         = "/Users/m1/vanta_auth.db"
TELEMETRY_LOG   = "/Users/m1/slots_telemetry.log"
DIRECT_UDP_ROUTE = True  # True = Direct 15-25ms UDP routing, False = Relayed 100ms M1 proxy

def log(msg: str):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    sys.stdout.flush()
    try:
        with open(TELEMETRY_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def record_telemetry(severity: str, message: str, details: str = "", client_ip: str = "", slot_num: int = 0, slot_id: str = "", hwid: str = "", extra: dict = None):
    log(f"[{severity}][slot:{slot_num:02d}][{client_ip or 'local'}] {message} | {details}")
    
    def _db_async():
        try:
            if os.path.exists(DB_PATH):
                payload_extra = dict(extra) if extra else {}
                payload_extra["slot_num"] = slot_num
                payload_extra["slot_id"] = slot_id
                
                conn = sqlite3.connect(DB_PATH, timeout=5)
                c = conn.cursor()
                c.execute("""
                    INSERT INTO diagnostics (timestamp, severity, source, message, details, client_ip, hwid, extra, resolved)
                    VALUES (?, ?, 'ORCHESTRATOR', ?, ?, ?, ?, ?, 0)
                """, (int(time.time()), severity, message, details, client_ip, hwid, json.dumps(payload_extra)))
                conn.commit()
                conn.close()
        except Exception:
            pass

    threading.Thread(target=_db_async, daemon=True).start()

slots: dict = {}
slots_lock = threading.Lock()
active_slot_nums: set = set()
concluded_engine_pids: set = set()

class SlotState:
    def __init__(self, slot_id: str, slot_num: int):
        self.slot_id        = slot_id
        self.slot_num       = slot_num
        self.data_dir       = os.path.join(BASE_SLOTS_DIR, f"slot{slot_num}")
        self.app_path       = f"/Applications/League of Legends_slot{slot_num}.app"
        # Non-overlapping port offsets for 25 concurrent slots:
        # proxy_port:     8090..8114 (Slots 1..25)
        # lcu_port:       8150..8174 (Slots 1..25)
        # udp_proxy_port: 8200..8224 (Slots 1..25)
        self.proxy_port     = 8090 + (slot_num - 1)
        self.lcu_port       = 8150 + (slot_num - 1)
        self.udp_proxy_port = 8200 + (slot_num - 1)
        self.status         = "provisioning"
        self.args           = []
        self.game_args      = []
        self.rc_port        = None
        self.rc_token       = None
        self.app_port       = None
        self.rc_proc        = None
        self.rc_pid         = None
        self.lc_pid         = None
        self.engine_pid     = None
        self.client_ip      = None
        self.client_hash    = None
        self.created_at     = time.time()
        self.last_poll      = time.time()
        self._proxy_srv     = None
        self._proxy_stop    = None
        self._lcu_srv       = None
        self._lcu_stop      = None
        self._udp_srv       = None
        self._udp_stop      = None

def alloc_slot_num() -> int:
    for num in range(1, MAX_SLOTS + 1):
        if num not in active_slot_nums:
            active_slot_nums.add(num)
            return num
    raise RuntimeError("No free slot numbers available (All 25 slots occupied)")

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

def start_tcp_proxy(listen_port: int, target_port):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    srv.bind(("0.0.0.0", listen_port))
    srv.listen(128)
    log(f"[proxy] TCP 0.0.0.0:{listen_port} -> dynamic target {target_port}")

    is_running = [True]

    def get_target_port():
        if callable(target_port):
            try: return target_port()
            except Exception: return None
        return target_port

    def relay(src, dst):
        try:
            while is_running[0]:
                d = src.recv(65536)
                if not d: break
                dst.sendall(d)
        except Exception:
            pass
        finally:
            try: src.close()
            except: pass
            try: dst.close()
            except: pass

    def accept_loop():
        while is_running[0]:
            try:
                c, _ = srv.accept()
            except (OSError, socket.error):
                # Clean exit on socket close
                break
            except Exception:
                break

            port = get_target_port()
            if not port:
                try: c.close()
                except: pass
                continue

            try:
                c.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                c.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            except Exception:
                pass

            try:
                t = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                t.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                t.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                t.connect(("127.0.0.1", port))
            except Exception:
                try: c.close()
                except: pass
                continue

            threading.Thread(target=relay, args=(c, t), daemon=True).start()
            threading.Thread(target=relay, args=(t, c), daemon=True).start()

    threading.Thread(target=accept_loop, daemon=True).start()
    return srv, is_running

def start_udp_proxy(listen_port: int, target_ip: str, target_port: int):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", listen_port))
    log(f"[udp_proxy] UDP 0.0.0.0:{listen_port} <-> {target_ip}:{target_port}")

    client_addr = [None]
    is_running = [True]

    def loop():
        while is_running[0]:
            try:
                data, addr = sock.recvfrom(65535)
                if addr != (target_ip, target_port):
                    client_addr[0] = addr
                    sock.sendto(data, (target_ip, target_port))
                else:
                    if client_addr[0]:
                        sock.sendto(data, client_addr[0])
            except (OSError, socket.error):
                break
            except Exception:
                break

    threading.Thread(target=loop, daemon=True).start()
    return sock, is_running

def kill_pid_safe(pid: int, sig=signal.SIGKILL):
    if not pid: return
    try:
        os.kill(pid, sig)
    except ProcessLookupError:
        pass
    except Exception as err:
        log(f"[cleanup] Error killing PID {pid}: {err}")

def clean_slot_processes_isolated(slot: SlotState):
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

    patterns = [
        f"--user-data-root={slot.data_dir}",
        f"_slot{slot.slot_num}.app",
        f"slot{slot.slot_num}"
    ]
    if slot.rc_port:
        patterns.append(f"--riotclient-app-port={slot.rc_port}")
        patterns.append(f"-RiotClientPort={slot.rc_port}")
    if slot.app_port:
        patterns.append(f"--app-port={slot.app_port}")

    try:
        ps_out = subprocess.check_output(["ps", "-axo", "pid,args"], timeout=5).decode(errors="replace")
        for line in ps_out.splitlines():
            if any(p in line for p in patterns) and "grep" not in line and "vanta_orchestrator" not in line:
                parts = line.strip().split()
                if parts and parts[0].isdigit():
                    kill_pid_safe(int(parts[0]))
    except Exception:
        pass

    # Clean isolated lockfile in the cloned application bundle
    app_lock = os.path.join(slot.app_path, "Contents", "LoL", "lockfile")
    if os.path.exists(app_lock):
        try: os.remove(app_lock)
        except: pass

def capture_game_engine_loop(slot: SlotState):
    record_telemetry("INFO", "GAME_MONITOR_STARTED", "3D engine monitor active", slot.client_ip, slot.slot_num, slot.slot_id)
    for _ in range(7200):
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

                    # If slot has recorded lc_pid, ensure this game engine was spawned by this slot's LeagueClient
                    if slot.lc_pid and ppid != slot.lc_pid and f"_slot{slot.slot_num}.app" not in line:
                        continue

                    with slots_lock:
                        other_claimed = any(s.engine_pid == pid for sid, s in slots.items() if sid != slot.slot_id)
                        if pid in concluded_engine_pids or other_claimed or slot.engine_pid == pid:
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

                    slot._udp_srv, slot._udp_stop = start_udp_proxy(slot.udp_proxy_port, target_ip, target_port)

                    if not DIRECT_UDP_ROUTE:
                        game_args[0] = "51.159.121.126"
                        game_args[1] = str(slot.udp_proxy_port)

                    with slots_lock:
                        slot.game_args = game_args
                        slot.engine_pid = pid

                    mode_str = "DIRECT (15-25ms)" if DIRECT_UDP_ROUTE else f"UDP PROXY {slot.udp_proxy_port} (100ms)"
                    record_telemetry("INFO", "3D_GAME_ENGINE_CAPTURED", f"Target: {target_ip}:{target_port} -> Mode: {mode_str}", slot.client_ip, slot.slot_num, slot.slot_id, extra={"engine_pid": pid, "target_ip": target_ip, "target_port": target_port, "udp_proxy_port": slot.udp_proxy_port, "direct_udp": DIRECT_UDP_ROUTE})
                    try:
                        os.kill(pid, signal.SIGSTOP)
                        log(f"[game_monitor:slot{slot.slot_num}] Suspended (SIGSTOP) Mac 3D engine PID {pid} to keep parent LeagueClient in 'InProgress' phase")
                    except Exception as err:
                        log(f"[game_monitor:slot{slot.slot_num}] Error suspending Mac game: {err}")

                    while True:
                        time.sleep(1.0)
                        with slots_lock:
                            if slot.slot_id not in slots:
                                return
                            if slot.engine_pid is None and len(slot.game_args) == 0:
                                concluded_engine_pids.add(pid)
                                record_telemetry("INFO", "MATCH_CONCLUDED_MONITOR_RESET", "3D Game Engine reset cleanly", slot.client_ip, slot.slot_num, slot.slot_id)
                                break
                        try:
                            os.kill(pid, 0)
                        except OSError:
                            pass
        except Exception as e:
            log(f"[game_monitor:slot{slot.slot_num}] error: {e}")
        time.sleep(1.0)

def vm_worker(slot: SlotState, yaml_data: str):
    t_start = time.time()
    try:
        record_telemetry("INFO", "SLOT_PROVISION_START", "Initializing isolated slot environment", slot.client_ip, slot.slot_num, slot.slot_id)
        clean_slot_processes_isolated(slot)

        # Ensure the slot's dedicated APFS CoW cloned application bundle exists
        if not os.path.exists(slot.app_path):
            record_telemetry("INFO", "APFS_CLONING", f"Creating instant APFS clone: {slot.app_path}", slot.client_ip, slot.slot_num, slot.slot_id)
            subprocess.run(f"cp -c -R '{BASE_APP_PATH}' '{slot.app_path}'", shell=True)

        # Remove any lingering lockfile inside the slot's app bundle
        slot_app_lock = os.path.join(slot.app_path, "Contents", "LoL", "lockfile")
        if os.path.exists(slot_app_lock):
            try: os.remove(slot_app_lock)
            except: pass

        cfg_dir = os.path.join(slot.data_dir, "Config")
        data_dir = os.path.join(slot.data_dir, "Data")
        shared_dir = os.path.join(slot.data_dir, "SharedMetadata")
        os.makedirs(cfg_dir, exist_ok=True)
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(os.path.join(shared_dir, "league_of_legends.live"), exist_ok=True)

        meta_yaml = f"""auto_patching_enabled_by_player: false
dependencies: {{}}
patching_policy: "manual"
patchline_patching_ask_policy: "ask"
product_dependency: "teamfighttactics.live"
product_install_full_path: "{slot.app_path}"
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
            RC_APP_PATH,
            "--allow-multiple-clients",
            f"--user-data-root={slot.data_dir}",
            f"--data-root={shared_dir}",
            f"--product-install-path={slot.app_path}",
            "--product-install-root=/Applications",
            "--product-install-patchline=live"
        ]

        env = os.environ.copy()
        env["VANTA_SLOT_NUM"] = str(slot.slot_num)
        proc = subprocess.Popen(cmd, env=env)
        slot.rc_proc = proc
        slot.rc_pid = proc.pid
        record_telemetry("INFO", "RC_SPAWNED", f"PID {proc.pid} spawned with user-data-root {slot.data_dir}", slot.client_ip, slot.slot_num, slot.slot_id, extra={"rc_pid": proc.pid})

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
        srv, stop_flag = start_tcp_proxy(slot.proxy_port, lambda: slot.rc_port)
        slot._proxy_srv = srv
        slot._proxy_stop = stop_flag
        record_telemetry("INFO", "RC_ONLINE", f"RCS listening on port {rc_port}, proxy on {slot.proxy_port}", slot.client_ip, slot.slot_num, slot.slot_id, extra={"rc_port": rc_port, "proxy_port": slot.proxy_port})

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        auth_hdr = base64.b64encode(f"riot:{rc_token}".encode()).decode()

        # Wait for authentication
        session_ready = False
        for i in range(30):
            try:
                session_req = urllib.request.Request(
                    f"https://127.0.0.1:{rc_port}/rso-auth/v1/session",
                    headers={"Authorization": f"Basic {auth_hdr}"}
                )
                with urllib.request.urlopen(session_req, context=ctx, timeout=3) as resp:
                    data = json.loads(resp.read().decode())
                    if data.get("type") == "authenticated":
                        session_ready = True
                        record_telemetry("INFO", "RC_AUTHENTICATED", f"Authenticated after {i+1}s", slot.client_ip, slot.slot_num, slot.slot_id)
                        break
            except Exception:
                pass
            time.sleep(1)

        # Proactively accept EULA for this account & product to prevent HTTP 464
        for eula_path in ["/eula/v1/agreement/acceptance", "/eula/v1/product-context"]:
            try:
                e_req = urllib.request.Request(
                    f"https://127.0.0.1:{rc_port}{eula_path}",
                    data=b"{}",
                    headers={"Authorization": f"Basic {auth_hdr}", "Content-Type": "application/json"},
                    method="PUT"
                )
                with urllib.request.urlopen(e_req, context=ctx, timeout=3) as resp:
                    record_telemetry("INFO", "EULA_ACCEPTED", f"{eula_path} HTTP {resp.status}", slot.client_ip, slot.slot_num, slot.slot_id)
            except Exception:
                pass

        # Trigger game launch via RC REST API
        launch_url = f"https://127.0.0.1:{rc_port}/product-launcher/v1/products/league_of_legends/patchlines/live"
        req = urllib.request.Request(
            launch_url, data=b"{}",
            headers={"Authorization": f"Basic {auth_hdr}", "Content-Type": "application/json"}
        )

        launch_ok = False
        for attempt in range(25):
            try:
                with urllib.request.urlopen(req, context=ctx, timeout=5) as resp:
                    launch_ok = True
                    record_telemetry("INFO", "GAME_LAUNCH_TRIGGERED", f"RC API HTTP {resp.status}", slot.client_ip, slot.slot_num, slot.slot_id)
                    break
            except urllib.error.HTTPError as he:
                log(f"[worker:slot{slot.slot_num}] RC API HTTP {he.code}: {he.reason}")
                if he.code == 464:
                    try:
                        eula_put = urllib.request.Request(
                            f"https://127.0.0.1:{rc_port}/eula/v1/agreement/acceptance",
                            data=b"{}",
                            headers={"Authorization": f"Basic {auth_hdr}", "Content-Type": "application/json"},
                            method="PUT"
                        )
                        with urllib.request.urlopen(eula_put, context=ctx, timeout=3) as eresp:
                            log(f"[worker:slot{slot.slot_num}] EULA PUT acceptance succeeded (HTTP {eresp.status})")
                    except Exception as err:
                        log(f"[worker:slot{slot.slot_num}] EULA PUT acceptance error: {err}")
                time.sleep(2)
            except Exception as e:
                log(f"[worker:slot{slot.slot_num}] RC launch attempt {attempt+1} exception: {e}")
                time.sleep(2)

        if not launch_ok:
            _fail(slot, "Failed to trigger game launch via RC API")
            return

        # Poll for LeagueClientUx arguments
        for _ in range(90):
            try:
                ps = subprocess.check_output(["ps", "-axo", "pid,args"], timeout=5).decode(errors="replace")
                for line in ps.splitlines():
                    if ("grep" not in line
                            and ("LeagueClientUx" in line or "LeagueClient" in line)
                            and "--app-port=" in line
                            and (f"--riotclient-app-port={slot.rc_port}" in line or f"_slot{slot.slot_num}.app" in line or f"slot{slot.slot_num}" in line)):
                        raw_parts = line.strip().split()
                        pid = int(raw_parts[0])
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
                            slot._lcu_srv, slot._lcu_stop = start_tcp_proxy(slot.lcu_port, lambda: slot.app_port)
                        with slots_lock:
                            slot.status = "game_ready"
                            slot.args   = args
                        
                        elapsed = time.time() - t_start
                        record_telemetry("INFO", "SLOT_READY", f"LCU online (PID {pid}, AppPort {app_port}) in {elapsed:.1f}s", slot.client_ip, slot.slot_num, slot.slot_id, extra={"lc_pid": pid, "app_port": app_port, "elapsed_s": round(elapsed, 2), "proxy_port": slot.proxy_port, "lcu_port": slot.lcu_port})
                        threading.Thread(target=capture_game_engine_loop, args=(slot,), daemon=True).start()
                        return
            except Exception:
                pass
            time.sleep(1.5)

        _fail(slot, "Timeout waiting for LeagueClient")
    except Exception as e:
        _fail(slot, f"exception: {e}")

def _fail(slot: SlotState, reason: str):
    with slots_lock:
        slot.status = f"FAILED: {reason}"
    record_telemetry("ERROR", "SLOT_FAILED", reason, slot.client_ip, slot.slot_num, slot.slot_id)
    _cleanup_slot_locked(slot.slot_id)

def _cleanup_slot_locked(sid: str):
    if sid not in slots: return
    s = slots.pop(sid, None)
    if not s: return

    def _async_teardown(slot_obj: SlotState):
        record_telemetry("INFO", "SLOT_TEARDOWN", f"Closing slot {slot_obj.slot_num} ({sid[:8]})", slot_obj.client_ip, slot_obj.slot_num, sid)
        if slot_obj._proxy_stop:
            slot_obj._proxy_stop[0] = False
        if slot_obj._proxy_srv:
            try: slot_obj._proxy_srv.close()
            except: pass

        if slot_obj._lcu_stop:
            slot_obj._lcu_stop[0] = False
        if slot_obj._lcu_srv:
            try: slot_obj._lcu_srv.close()
            except: pass

        if slot_obj._udp_stop:
            slot_obj._udp_stop[0] = False
        if slot_obj._udp_srv:
            try: slot_obj._udp_srv.close()
            except: pass

        clean_slot_processes_isolated(slot_obj)

        lockfile = os.path.join(slot_obj.data_dir, "Config", "lockfile")
        if os.path.exists(lockfile):
            try: os.remove(lockfile)
            except: pass

        app_lock = os.path.join(slot_obj.app_path, "Contents", "LoL", "lockfile")
        if os.path.exists(app_lock):
            try: os.remove(app_lock)
            except: pass

        free_slot_num(slot_obj.slot_num)
        record_telemetry("INFO", "SLOT_FREED", f"Slot {slot_obj.slot_num} returned to free pool (Active: {len(slots)}/{MAX_SLOTS})", slot_obj.client_ip, slot_obj.slot_num, sid)

    threading.Thread(target=_async_teardown, args=(s,), daemon=True).start()

def slot_reaper_loop():
    while True:
        time.sleep(5)
        now = time.time()
        to_clean = []
        with slots_lock:
            for sid, s in list(slots.items()):
                # 1. Active 3D Game Match: NEVER evict while match is active!
                if getattr(s, "engine_pid", None) is not None or getattr(s, "game_args", None):
                    continue

                # 2. Slot in game_ready state (user is in lobby or between matches)
                if s.status == "game_ready":
                    if getattr(s, "lc_pid", None):
                        try:
                            os.kill(s.lc_pid, 0)
                        except (ProcessLookupError, OSError):
                            to_clean.append((sid, f"LeagueClient process {s.lc_pid} terminated"))
                            continue
                    # Inactivity timeout for game_ready (600s / 10 minutes without polling)
                    if (now - getattr(s, "last_poll", now)) > 600.0:
                        to_clean.append((sid, "Client inactivity timeout (>600s)"))
                        continue
                    continue

                # 3. Slot in initial provisioning state (180s timeout)
                if s.status == "provisioning" and (now - getattr(s, "created_at", now)) > 180.0:
                    to_clean.append((sid, "Provisioning timeout (>180s)"))
                    continue

            for sid, reason in to_clean:
                stale_slot = slots.get(sid)
                snum = getattr(stale_slot, "slot_num", 0)
                record_telemetry("WARN", "REAPER_EVICTION", reason, getattr(stale_slot, "client_ip", ""), snum, sid)
                _cleanup_slot_locked(sid)

def verify_license_db(key: str, hwid: str, client_ip: str) -> tuple[bool, str]:
    """Verify license key and HWID directly against vanta_auth.db"""
    if not key:
        return False, "Missing license key"
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM licenses WHERE license_key = ?", (key,))
        row = c.fetchone()
        if not row:
            conn.close()
            return False, "Invalid license key"
        if row["status"] != "active":
            conn.close()
            return False, f"License is {row['status']}"
        now = int(time.time())
        if row["expires_at"] < now:
            c.execute("UPDATE licenses SET status = 'expired' WHERE id = ?", (row["id"],))
            conn.commit()
            conn.close()
            return False, "License has expired"
        bound_hwid = row["hwid"]
        if bound_hwid and hwid and bound_hwid != hwid:
            conn.close()
            return False, "HWID mismatch"
        if not bound_hwid and hwid:
            c.execute("UPDATE licenses SET hwid = ?, last_ip = ?, last_seen = ? WHERE id = ?", (hwid, client_ip, now, row["id"]))
            conn.commit()
        else:
            c.execute("UPDATE licenses SET last_ip = ?, last_seen = ? WHERE id = ?", (client_ip, now, row["id"]))
            conn.commit()
        conn.close()
        return True, "Authorized"
    except Exception as e:
        return False, f"Auth DB error: {e}"

# ── HTTP Server Request Handler ────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_POST(self):
        if self.path == "/api/request_slot":
            client_ip = self.client_address[0]
            # 1. Enforce Server-Side License & HWID Security
            license_key = self.headers.get("X-Vanta-License", "").strip()
            hwid = self.headers.get("X-Vanta-HWID", "").strip()

            valid, auth_err = verify_license_db(license_key, hwid, client_ip)
            if not valid:
                record_telemetry("WARN", "SLOT_REQUEST_DENIED", f"Unauthorized slot attempt: {auth_err}", client_ip, hwid=hwid, extra={"key": license_key[:8] if license_key else "NONE"})
                self._json(401, {"error": "unauthorized", "message": auth_err})
                return

            length = int(self.headers.get("Content-Length", 0))
            yaml_data = self.rfile.read(length).decode()
            client_hash = hashlib.sha256(yaml_data.encode()).hexdigest()[:16]

            with slots_lock:
                client_ip = self.client_address[0]
                # Auto-clear ONLY if the same account credentials / session reconnects
                for sid, s in list(slots.items()):
                    if getattr(s, "client_hash", None) == client_hash:
                        record_telemetry("INFO", "RECONNECT_RECLAIM", f"Auto-clearing previous slot {s.slot_num} ({sid[:8]}) for reconnecting account", client_ip, s.slot_num, sid)
                        _cleanup_slot_locked(sid)

                if len(slots) >= MAX_SLOTS:
                    oldest_id = min(slots.keys(), key=lambda sid: getattr(slots[sid], "last_poll", 0))
                    record_telemetry("WARN", "POOL_FULL_EVICTION", f"Evicting oldest slot {oldest_id[:8]} to make room (Capacity: {MAX_SLOTS})", client_ip)
                    _cleanup_slot_locked(oldest_id)

                try:
                    slot_num = alloc_slot_num()
                except Exception as e:
                    self._json(503, {"error": "no_available_slots", "max_slots": MAX_SLOTS, "active_count": len(slots)})
                    return

                slot_id           = str(uuid.uuid4())
                slot              = SlotState(slot_id, slot_num)
                slot.client_ip    = self.client_address[0]
                slot.client_hash  = client_hash
                slot.license_key  = license_key
                slot.hwid         = hwid
                slot.last_poll    = time.time()
                slots[slot_id]    = slot

            record_telemetry("INFO", "SLOT_ALLOCATED", f"Slot {slot_num} assigned to key {license_key[:8]}... RCS: {slot.proxy_port}, LCU: {slot.lcu_port}, UDP: {slot.udp_proxy_port}", slot.client_ip, slot_num, slot_id, hwid=hwid, extra={"proxy_port": slot.proxy_port, "lcu_port": slot.lcu_port, "udp_proxy_port": slot.udp_proxy_port})
            threading.Thread(target=vm_worker, args=(slot, yaml_data), daemon=True).start()
            self._json(200, {
                "slot_id":        slot_id,
                "proxy_port":     slot.proxy_port,
                "lcu_port":       slot.lcu_port,
                "udp_proxy_port": slot.udp_proxy_port,
                "max_slots":      MAX_SLOTS,
                "active_count":   len(slots)
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
            record_telemetry("WARN", "EMERGENCY_RESET", f"Cleared {len(slot_ids)} slots and killed all background Riot processes", self.client_address[0])
            self._json(200, {"success": True, "cleared_slots": len(slot_ids), "max_slots": MAX_SLOTS})
        elif self.path == "/api/slots/kill":
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode() if length > 0 else "{}"
            try: payload = json.loads(raw)
            except Exception: payload = {}
            sid = payload.get("slot_id")
            with slots_lock:
                if sid in slots:
                    snum = slots[sid].slot_num
                    _cleanup_slot_locked(sid)
                    record_telemetry("INFO", "MANUAL_KILL", f"Client requested kill: freed slot {snum} ({sid[:8]})", self.client_address[0], snum, sid)
                    self._json(200, {"success": True, "killed": sid, "slot_num": snum})
                else:
                    self._json(404, {"error": "not_found"})
        elif self.path == "/api/match_concluded":
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode() if length > 0 else "{}"
            try: payload = json.loads(raw)
            except Exception: payload = {}
            sid = payload.get("slot_id")
            with slots_lock:
                slot = slots.get(sid)
            if not slot:
                self._json(404, {"error": "slot_not_found"})
                return

            record_telemetry("INFO", "MATCH_CONCLUDED", f"Match concluded on Windows for slot {slot.slot_num} ({sid[:8]}). Concluding Mac 3D engine PID {slot.engine_pid}", slot.client_ip, slot.slot_num, sid, extra={"engine_pid": slot.engine_pid})
            if slot.engine_pid:
                concluded_engine_pids.add(slot.engine_pid)
                try:
                    os.kill(slot.engine_pid, signal.SIGCONT)
                    time.sleep(0.1)
                    os.kill(slot.engine_pid, signal.SIGKILL)
                except Exception as err:
                    log(f"[match_concluded:slot{slot.slot_num}] Notice on 3D engine termination: {err}")

            with slots_lock:
                slot.game_args = []
                slot.engine_pid = None
                if slot._udp_stop:
                    slot._udp_stop[0] = False
                if slot._udp_srv:
                    try: slot._udp_srv.close()
                    except: pass
                    slot._udp_srv = None

            self._json(200, {"success": True, "message": "match_concluded_processed", "slot_num": slot.slot_num})
        elif self.path == "/api/config/routing":
            global DIRECT_UDP_ROUTE
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode() if length > 0 else "{}"
            try: payload = json.loads(raw)
            except Exception: payload = {}
            mode = payload.get("mode", "").lower()
            if mode == "direct":
                DIRECT_UDP_ROUTE = True
            elif mode == "proxy":
                DIRECT_UDP_ROUTE = False
            elif "direct" in payload:
                DIRECT_UDP_ROUTE = bool(payload["direct"])
            record_telemetry("INFO", "ROUTING_CONFIG_UPDATED", f"UDP routing mode set to: {'DIRECT (15-25ms)' if DIRECT_UDP_ROUTE else 'PROXY (100ms)'}", self.client_address[0])
            self._json(200, {
                "success": True,
                "direct_udp_route": DIRECT_UDP_ROUTE,
                "mode": "direct" if DIRECT_UDP_ROUTE else "proxy",
                "latency": "15-25ms" if DIRECT_UDP_ROUTE else "100ms"
            })
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
                "status":         slot.status,
                "args":           slot.args,
                "game_args":      slot.game_args,
                "proxy_port":     slot.proxy_port,
                "lcu_port":       slot.lcu_port,
                "udp_proxy_port": slot.udp_proxy_port,
                "rc_port":        slot.rc_port,
                "slot_num":       slot.slot_num,
                "direct_udp_route": DIRECT_UDP_ROUTE,
                "routing_mode":   "direct" if DIRECT_UDP_ROUTE else "proxy"
            })
        elif parsed.path == "/api/config/routing":
            self._json(200, {
                "direct_udp_route": DIRECT_UDP_ROUTE,
                "mode": "direct" if DIRECT_UDP_ROUTE else "proxy",
                "latency": "15-25ms" if DIRECT_UDP_ROUTE else "100ms",
                "description": "Direct 15-25ms UDP routing" if DIRECT_UDP_ROUTE else "Relayed 100ms M1 proxy routing"
            })
        elif parsed.path == "/api/client/update_check":
            client_ver = params.get("version", ["5.0.0"])[0].strip()
            version_file = "/Users/m1/releases/version.json"
            latest_info = {
                "version": "6.5.0",
                "mandatory": True,
                "changelog": "VANTA Apex v6.5: Direct Ultra-Low Latency UDP Routing (15-25ms) + 25 Isolated Slots + Autonomous In-Place Self-Updater",
                "download_url": "http://51.159.121.126:9000/api/client/download_latest",
                "file_size": 0,
                "sha256": ""
            }
            if os.path.exists(version_file):
                try:
                    with open(version_file, "r") as vf:
                        latest_info.update(json.load(vf))
                except Exception:
                    pass
            bin_path = "/Users/m1/releases/vanta.exe"
            if os.path.exists(bin_path):
                latest_info["file_size"] = os.path.getsize(bin_path)

            is_diff = (client_ver != latest_info["version"])
            self._json(200, {
                "success": True,
                "update_available": is_diff,
                "current_version": client_ver,
                "latest_version": latest_info["version"],
                "mandatory": latest_info.get("mandatory", True),
                "download_url": latest_info["download_url"],
                "file_size": latest_info.get("file_size", 0),
                "sha256": latest_info.get("sha256", ""),
                "changelog": latest_info.get("changelog", "")
            })
        elif parsed.path == "/api/client/download_latest":
            bin_path = "/Users/m1/releases/vanta.exe"
            if not os.path.exists(bin_path):
                self._json(404, {"success": False, "error": "Latest binary release not found"})
                return

            file_size = os.path.getsize(bin_path)
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", 'attachment; filename="vanta.exe"')
            self.send_header("Content-Length", str(file_size))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            with open(bin_path, "rb") as f:
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    try:
                        self.wfile.write(chunk)
                    except Exception:
                        break
            return
        elif parsed.path == "/api/slots":
            res = {}
            with slots_lock:
                now = time.time()
                for sid, s in slots.items():
                    lp = getattr(s, "last_poll", now)
                    res[sid] = {
                        "slot_num":          s.slot_num,
                        "status":            s.status,
                        "proxy_port":        s.proxy_port,
                        "lcu_port":          s.lcu_port,
                        "udp_proxy_port":    s.udp_proxy_port,
                        "game_active":       len(getattr(s, "game_args", [])) > 0,
                        "last_poll_seconds": int(now - lp),
                        "client_ip":         getattr(s, "client_ip", "unknown"),
                        "uptime_seconds":    int(now - getattr(s, "created_at", now)),
                        "rc_pid":            getattr(s, "rc_pid", None),
                        "lc_pid":            getattr(s, "lc_pid", None),
                        "engine_pid":        getattr(s, "engine_pid", None)
                    }
            self._json(200, {
                "slots":        res,
                "active_count": len(res),
                "max_slots":    MAX_SLOTS,
                "free_slots":   MAX_SLOTS - len(res)
            })
        elif parsed.path == "/api/diagnostics/recent":
            slot_filter = params.get("slot", [None])[0]
            limit_val = int(params.get("limit", [50])[0])
            events = []
            try:
                if os.path.exists(DB_PATH):
                    conn = sqlite3.connect(DB_PATH, timeout=3)
                    c = conn.cursor()
                    if slot_filter:
                        c.execute("""
                            SELECT id, timestamp, severity, source, message, details, client_ip, hwid, extra 
                            FROM diagnostics 
                            WHERE source = 'ORCHESTRATOR' AND extra LIKE ? 
                            ORDER BY id DESC LIMIT ?
                        """, (f'%"slot_num": {int(slot_filter)}%', limit_val))
                    else:
                        c.execute("""
                            SELECT id, timestamp, severity, source, message, details, client_ip, hwid, extra 
                            FROM diagnostics 
                            WHERE source = 'ORCHESTRATOR' 
                            ORDER BY id DESC LIMIT ?
                        """, (limit_val,))
                    for row in c.fetchall():
                        events.append({
                            "id":        row[0],
                            "timestamp": row[1],
                            "time_str":  time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(row[1])),
                            "severity":  row[2],
                            "source":    row[3],
                            "message":   row[4],
                            "details":   row[5],
                            "client_ip": row[6],
                            "hwid":      row[7],
                            "extra":     json.loads(row[8]) if row[8] else {}
                        })
                    conn.close()
            except Exception as err:
                events = [{"error": str(err)}]
            self._json(200, {"success": True, "count": len(events), "diagnostics": events})
        elif parsed.path == "/api/health":
            self._json(200, {
                "ok":           True,
                "active_slots": len(slots),
                "max_slots":    MAX_SLOTS,
                "free_slots":   MAX_SLOTS - len(slots)
            })
        else:
            self.send_response(404); self.end_headers()

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", ORCH_PORT), Handler)
    threading.Thread(target=slot_reaper_loop, daemon=True).start()
    log(f"[server] VANTA 25-Slot Zero-Collision Orchestrator V6.3 listening on 0.0.0.0:{ORCH_PORT}")
    server.serve_forever()
