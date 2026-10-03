#!/usr/bin/env python3
# vanta_orchestrator.py - Native RC REST API Orchestrator (V5 Hybrid Engine)
# Mac M1 - Direct API Launch, Dual TCP Tunneling (RC + LCU), UDP Relay (Zero-Ban) & 3D Game Param Capturing

import base64
import json
import os
import re
import shlex
import socket
import ssl
import subprocess
import sys
import threading
import time
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

# Configuration
ORCH_PORT   = 9000
MAX_SLOTS   = 5
BASE_DATA   = os.path.expanduser("~/Library/Application Support")
STD_RC_DIR  = os.path.join(BASE_DATA, "Riot Games", "Riot Client")
STD_LOCKFILE= os.path.join(STD_RC_DIR, "Config", "lockfile")
STD_YAML    = os.path.join(STD_RC_DIR, "Data", "RiotGamesPrivateSettings.yaml")

def log(msg: str):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")
    sys.stdout.flush()

slots: dict = {}
slots_lock  = threading.Lock()
proxy_ports: set = set()

class SlotState:
    def __init__(self, slot_id: str, proxy_port: int, lcu_port: int, udp_proxy_port: int):
        self.slot_id        = slot_id
        self.proxy_port     = proxy_port
        self.lcu_port       = lcu_port
        self.udp_proxy_port = udp_proxy_port
        self.status         = "provisioning"
        self.args: list     = []
        self.game_args: list= []
        self.rc_port        = None
        self.rc_token       = None
        self.app_port       = None
        self.rc_pids: set   = set()
        self.created_at     = time.time()
        self.last_poll      = time.time()
        self._proxy_srv     = None
        self._lcu_srv       = None
        self._udp_srv       = None

def alloc_proxy_ports():
    base_rc  = 8090
    base_lcu = 8100
    base_udp = 8200
    for i in range(MAX_SLOTS):
        rc_p  = base_rc + i
        lcu_p = base_lcu + i
        udp_p = base_udp + i
        if rc_p not in proxy_ports and lcu_p not in proxy_ports and udp_p not in proxy_ports:
            proxy_ports.add(rc_p)
            proxy_ports.add(lcu_p)
            proxy_ports.add(udp_p)
            return rc_p, lcu_p, udp_p
    raise RuntimeError("no free proxy ports")

def free_proxy_ports(rc_p: int, lcu_p: int, udp_p: int):
    proxy_ports.discard(rc_p)
    proxy_ports.discard(lcu_p)
    proxy_ports.discard(udp_p)

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
                # If packet comes from Riot server (by IP, regardless of dynamic port)
                if addr[0] == target_ip:
                    if client_addr:
                        sock.sendto(data, client_addr)
                        pkt_out += 1
                        if pkt_out % 100 == 1:
                            log(f"[udp_proxy] Server -> Client ({len(data)}B, total {pkt_out})")
                else:
                    # Packet comes from Windows client
                    client_addr = addr
                    sock.sendto(data, target_addr)
                    pkt_in += 1
                    if pkt_in % 100 == 1:
                        log(f"[udp_proxy] Client -> Server ({len(data)}B from {addr}, total {pkt_in})")
            except Exception as e:
                log(f"[udp_proxy] error: {e}")
                break

    threading.Thread(target=loop, daemon=True).start()
    return sock

def capture_game_engine_loop(slot: SlotState):
    log(f"[game_monitor] Started 3D engine monitor for slot {slot.slot_id[:8]}")
    for _ in range(3600):
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
                    
                    arg_start = 1
                    for idx, token in enumerate(parts[1:], 1):
                        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", token):
                            arg_start = idx
                            break
                    
                    game_args = parts[arg_start:]
                    
                    target_ip = game_args[0]
                    target_port = int(game_args[1])
                    
                    slot._udp_srv = start_udp_proxy(slot.udp_proxy_port, target_ip, target_port)
                    
                    game_args[0] = "51.159.121.126"
                    game_args[1] = str(slot.udp_proxy_port)
                    
                    with slots_lock:
                        slot.game_args = game_args
                    log(f"[game_monitor] Captured 3D Game Engine (PID {pid}): Redirecting {target_ip}:{target_port} via relay on port {slot.udp_proxy_port}")
                    try:
                        os.kill(pid, 9)
                        subprocess.run(["pkill", "-9", "-f", "LeagueofLegends"], capture_output=True)
                        log(f"[game_monitor] Terminated Mac 3D engine PID {pid} so local Windows client has exclusive session")
                    except Exception as err:
                        log(f"[game_monitor] Error terminating Mac game: {err}")
                    return
        except Exception as e:
            log(f"[game_monitor] error: {e}")
        time.sleep(1.0)

def vm_worker(slot: SlotState, yaml_data: str):
    try:
        subprocess.run(["pkill", "-9", "-f", "League"], capture_output=True)
        subprocess.run(["pkill", "-9", "-f", "Riot Client"], capture_output=True)
        subprocess.run(["pkill", "-9", "-f", "RiotClientServices"], capture_output=True)
        time.sleep(1)

        if os.path.exists(STD_LOCKFILE):
            try: os.remove(STD_LOCKFILE)
            except: pass

        os.makedirs(os.path.dirname(STD_YAML), exist_ok=True)
        with open(STD_YAML, "w") as f:
            f.write(yaml_data)
        log(f"[worker] YAML written ({len(yaml_data)} bytes)")

        subprocess.Popen(["open", "-a", "Riot Client"])
        log("[worker] Riot Client launched")

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

        srv = start_tcp_proxy(slot.proxy_port, rc_port)
        slot._proxy_srv = srv

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

                        threading.Thread(target=capture_game_engine_loop, args=(slot,), daemon=True).start()
                        return
            except Exception:
                pass
            time.sleep(1.5)

        _fail(slot, "timeout waiting for LeagueClient")

    except Exception as e:
        _fail(slot, f"exception: {e}")

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
    if slot._udp_srv:
        try: slot._udp_srv.close()
        except: pass
    free_proxy_ports(slot.proxy_port, slot.lcu_port, slot.udp_proxy_port)


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

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        log(f"{self.address_string()} - {fmt % args}")

    def do_POST(self):
        if self.path == "/api/request_slot":
            length = int(self.headers.get("Content-Length", 0))
            yaml_data = self.rfile.read(length).decode()

            with slots_lock:
                # If full, evict oldest slot
                if len(slots) >= MAX_SLOTS:
                    oldest_id = min(slots.keys(), key=lambda sid: getattr(slots[sid], "last_poll", 0))
                    log(f"[slots] Evicting stale slot {oldest_id[:8]} to make room")
                    _cleanup_slot_locked(oldest_id)

                slot_id    = str(uuid.uuid4())
                proxy_port, lcu_port, udp_proxy_port = alloc_proxy_ports()
                slot       = SlotState(slot_id, proxy_port, lcu_port, udp_proxy_port)
                slot.last_poll = time.time()
                slots[slot_id] = slot

            log(f"[http] request_slot -> slot_id={slot_id[:8]} proxy_port={proxy_port} lcu_port={lcu_port} udp_proxy_port={udp_proxy_port}")
            threading.Thread(target=vm_worker, args=(slot, yaml_data), daemon=True).start()
            self._json(200, {
                "slot_id": slot_id,
                "proxy_port": proxy_port,
                "lcu_port": lcu_port,
                "udp_proxy_port": udp_proxy_port
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
        elif parsed.path == "/api/slots":
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
            self._json(200, {"slots": res})
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

if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", ORCH_PORT), Handler)
    threading.Thread(target=slot_reaper_loop, daemon=True).start()
    log(f"[server] VANTA orchestrator V5 listening on 0.0.0.0:{ORCH_PORT}")
    server.serve_forever()
