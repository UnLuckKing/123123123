#!/usr/bin/env python3
"""
vanta_orchestrator.py — Native RC REST API Orchestrator (V5 Hybrid Engine)
Mac M1 - Direct API Launch, Dual TCP Tunneling (RC + LCU) & 3D Game Param Capturing
"""

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
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

# ── Configuration ─────────────────────────────────────────────────────────────
ORCH_PORT   = 9000
MAX_SLOTS   = 5
BASE_DATA   = os.path.expanduser("~/Library/Application Support")
STD_RC_DIR  = os.path.join(BASE_DATA, "Riot Games", "Riot Client")
STD_LOCKFILE= os.path.join(STD_RC_DIR, "Config", "lockfile")
STD_YAML    = os.path.join(STD_RC_DIR, "Data", "RiotGamesPrivateSettings.yaml")

def log(msg: str):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")
    sys.stdout.flush()

# ── State Store ───────────────────────────────────────────────────────────────
slots: dict = {}
slots_lock  = threading.Lock()
proxy_ports: set = set()

class SlotState:
    def __init__(self, slot_id: str, proxy_port: int, lcu_port: int):
        self.slot_id     = slot_id
        self.proxy_port  = proxy_port
        self.lcu_port    = lcu_port
        self.status      = "provisioning"
        self.args: list  = []
        self.game_args: list = []
        self.rc_port     = None
        self.rc_token    = None
        self.app_port    = None
        self.rc_pids: set = set()
        self.created_at  = time.time()
        self.last_poll   = time.time()
        self._proxy_srv  = None
        self._lcu_srv    = None

def alloc_proxy_ports():
    base_rc  = 8090
    base_lcu = 8100
    for i in range(MAX_SLOTS):
        rc_p  = base_rc + i
        lcu_p = base_lcu + i
        if rc_p not in proxy_ports and lcu_p not in proxy_ports:
            proxy_ports.add(rc_p)
            proxy_ports.add(lcu_p)
            return rc_p, lcu_p
    raise RuntimeError("no free proxy ports")

def free_proxy_ports(rc_p: int, lcu_p: int):
    proxy_ports.discard(rc_p)
    proxy_ports.discard(lcu_p)

# ── Helpers ───────────────────────────────────────────────────────────────────
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
    log(f"[proxy] 0.0.0.0:{listen_port} -> 127.0.0.1:{target_port}")

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

def capture_game_engine_loop(slot: SlotState):
    """Monitors for the 3D Game Engine (LeagueofLegends.app) match launch on Mac."""
    log(f"[game_monitor] Started 3D engine monitor for slot {slot.slot_id[:8]}")
    for _ in range(3600): # Monitor up to 1 hour
        with slots_lock:
            if slot.slot_id not in slots:
                break
        try:
            ps_out = subprocess.check_output(["ps", "-u", "m1", "-ww", "-o", "pid,command"], timeout=5).decode(errors="replace")
            for line in ps_out.splitlines():
                lower_line = line.lower()
                if "leagueoflegends" in lower_line and ("-gameid=" in lower_line or "-product=lol" in lower_line or "192.207." in lower_line or "104.160." in lower_line):
                    parts = line.strip().split()
                    pid = int(parts[0])
                    
                    # Find index where the actual game arguments start (first IP or arg starting with digit or minus)
                    arg_start = 1
                    for idx, token in enumerate(parts[1:], 1):
                        # The first token is the IP e.g. 192.207.0.5 or 104.160.x.x
                        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", token):
                            arg_start = idx
                            break
                    
                    game_args = parts[arg_start:]
                    with slots_lock:
                        slot.game_args = game_args
                    log(f"[game_monitor] Captured 3D Game Engine (PID {pid}): {len(game_args)} args -> {game_args[:4]}")
                    return
        except Exception as e:
            log(f"[game_monitor] error: {e}")
        time.sleep(1.0)

# ── Worker ────────────────────────────────────────────────────────────────────
def vm_worker(slot: SlotState, yaml_data: str):
    try:
        # 1. Clean previous zombie instances
        subprocess.run(["pkill", "-9", "-f", "League"], capture_output=True)
        subprocess.run(["pkill", "-9", "-f", "Riot Client"], capture_output=True)
        subprocess.run(["pkill", "-9", "-f", "RiotClientServices"], capture_output=True)
        time.sleep(1)

        if os.path.exists(STD_LOCKFILE):
            try: os.remove(STD_LOCKFILE)
            except: pass

        # 2. Write YAML
        os.makedirs(os.path.dirname(STD_YAML), exist_ok=True)
        with open(STD_YAML, "w") as f:
            f.write(yaml_data)
        log(f"[worker] YAML written ({len(yaml_data)} bytes)")

        # 3. Launch Riot Client app
        subprocess.Popen(["open", "-a", "Riot Client"])
        log("[worker] Riot Client launched")

        # 4. Wait for RC Lockfile
        rc_port, rc_token = None, None
        for _ in range(60):
            rc_port, rc_token = read_lockfile(STD_LOCKFILE)
            if rc_port and rc_token:
                break
            time.sleep(1)

        if not rc_port:
            _fail(slot, "RC lockfile timeout")
            return

        slot.rc_port  = rc_port
        slot.rc_token = rc_token
        log(f"[worker] RC online at port {rc_port}")

        # 5. Start TCP proxy for RC
        srv = start_tcp_proxy(slot.proxy_port, rc_port)
        slot._proxy_srv = srv

        # 6. Wait until Riot Client session is fully authenticated
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
                        log(f"[worker] RC authenticated after {i+1}s")
                        break
            except Exception:
                pass
            time.sleep(1)

        # 7. Launch League via RC REST API
        launch_url = f"https://127.0.0.1:{rc_port}/product-launcher/v1/products/league_of_legends/patchlines/live"
        req = urllib.request.Request(
            launch_url,
            data=b"{}",
            headers={
                "Authorization": f"Basic {auth_hdr}",
                "Content-Type": "application/json"
            }
        )

        launch_ok = False
        for attempt in range(5):
            try:
                with urllib.request.urlopen(req, context=ctx, timeout=5) as resp:
                    log(f"[worker] API launch triggered (attempt {attempt+1}), HTTP {resp.status}")
                    launch_ok = True
                    break
            except Exception as e:
                log(f"[worker] API launch attempt {attempt+1} error: {e}")
                time.sleep(2)

        if not launch_ok:
            _fail(slot, "failed to trigger game launch via RC API")
            return

        # 8. Capture LeagueClient args & start LCU proxy
        for _ in range(60):
            try:
                ps = subprocess.check_output(["ps", "-eo", "args"], timeout=5).decode(errors="replace")
                for line in ps.splitlines():
                    if ("remoting-auth-token=" in line
                            and ("LeagueClientUx" in line or "LeagueClient" in line)
                            and "grep" not in line
                            and "Riot Client" not in line
                            and "--app-port=" in line):
                        
                        args = shlex.split(line)
                        if args and ("LeagueClient" in args[0] or "LeagueClientUx" in args[0]):
                            args = args[1:]
                        
                        app_port = None
                        for a in args:
                            if a.startswith("--app-port="):
                                try:
                                    app_port = int(a.split("=")[1])
                                except Exception: pass
                                break

                        if app_port:
                            slot.app_port = app_port
                            slot._lcu_srv = start_tcp_proxy(slot.lcu_port, app_port)
                            log(f"[worker] LCU proxy started: 0.0.0.0:{slot.lcu_port} -> 127.0.0.1:{app_port}")

                        with slots_lock:
                            slot.status = "game_ready"
                            slot.args   = args
                        log(f"[worker] game_ready captured ({len(args)} args)")

                        # Start background monitor for 3D Game Engine params
                        threading.Thread(target=capture_game_engine_loop, args=(slot,), daemon=True).start()
                        return
            except Exception:
                pass
            time.sleep(1.5)

        _fail(slot, "timeout waiting for LeagueClient")

    except Exception as e:
        _fail(slot, f"exception: {e}")
        import traceback; traceback.print_exc()

def _fail(slot: SlotState, reason: str):
    with slots_lock:
        slot.status = reason
    log(f"[slot {slot.slot_id[:8]}] FAILED: {reason}")
    if slot._proxy_srv:
        try: slot._proxy_srv.close()
        except: pass
    if slot._lcu_srv:
        try: slot._lcu_srv.close()
        except: pass
    free_proxy_ports(slot.proxy_port, slot.lcu_port)

# ── HTTP Server ───────────────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        log(f"{self.address_string()} - {fmt % args}")

    def do_POST(self):
        if self.path == "/api/request_slot":
            length = int(self.headers.get("Content-Length", 0))
            yaml_data = self.rfile.read(length).decode()

            with slots_lock:
                if len(slots) >= MAX_SLOTS:
                    self._json(503, {"error": "slot_pool_full"})
                    return
                slot_id    = str(uuid.uuid4())
                proxy_port, lcu_port = alloc_proxy_ports()
                slot       = SlotState(slot_id, proxy_port, lcu_port)
                slots[slot_id] = slot

            log(f"[http] request_slot -> slot_id={slot_id[:8]} proxy_port={proxy_port} lcu_port={lcu_port}")
            threading.Thread(target=vm_worker, args=(slot, yaml_data), daemon=True).start()
            self._json(200, {
                "slot_id": slot_id,
                "proxy_port": proxy_port,
                "lcu_port": lcu_port
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
                "status":     slot.status,
                "args":       slot.args,
                "game_args":  slot.game_args,
                "proxy_port": slot.proxy_port,
                "lcu_port":   slot.lcu_port,
                "rc_port":    slot.rc_port,
            })
        elif parsed.path == "/api/health":
            self._json(200, {"ok": True})
        else:
            self.send_response(404); self.end_headers()

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", ORCH_PORT), Handler)
    log(f"[server] vanta_orchestrator V5 listening on 0.0.0.0:{ORCH_PORT}")
    server.serve_forever()
