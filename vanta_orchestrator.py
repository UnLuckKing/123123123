#!/usr/bin/env python3
# vanta_orchestrator.py - 25-Slot Zero-Collision Vanguard Mac Bypass Orchestrator (Apex v6.3)
# Multi-tenant headless broker for League of Legends on macOS M1 Apple Silicon
# Isolated APFS App Bundles (Slots 1-25), Non-Overlapping Dedicated Ports, Persistent Telemetry DB

import base64
import hashlib
import hmac
import json
import os
import re
import shlex
import signal
import socket
import sqlite3
import ssl
import struct
import subprocess
import sys
import threading
import time
import queue
import shutil
from pathlib import Path
import urllib.request
import urllib.error
import uuid
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from entitlement import EntitlementError, entitlement_verifier

# ── Global Configuration ───────────────────────────────────────────────────────
ORCH_PORT       = 9000
MAX_SLOTS       = int(os.environ.get("VANTA_MAX_SLOTS", "50"))
BASE_SLOTS_DIR  = "/Users/m1/VantaSlots"
BASE_APP_PATH   = "/Applications/League of Legends.app"
RC_APP_PATH     = "/Applications/Riot Client.app/Contents/MacOS/RiotClientServices"
TEMPLATE_CONFIG = "/Users/m1/Library/Application Support/RiotClientData_slot1/Config/RiotClientSettings.yaml"
DB_PATH         = "/Users/m1/vanta_auth.db"
TELEMETRY_LOG   = "/Users/m1/slots_telemetry.log"
DIRECT_UDP_ROUTE = True  # True = Direct 15-25ms UDP routing, False = Relayed 100ms M1 proxy
PUBLIC_HOST = os.environ.get("VANTA_PUBLIC_HOST", os.environ.get("M1_HOST", ""))
RELAY_BIND_HOST = os.environ.get("VANTA_RELAY_BIND", "127.0.0.1")
ENTITLEMENT_ISSUER = os.environ.get("VANTA_AUTH_ISSUER", "vanta-auth")
ENTITLEMENT_AUDIENCE = os.environ.get("VANTA_ENTITLEMENT_AUDIENCE", "vanta-orchestrator")
IDEMPOTENCY_SLOTS = {}
IDEMPOTENCY_LOCK = threading.RLock()

ALLOWED_ORIGINS = {
    origin.strip() for origin in os.environ.get("VANTA_ALLOWED_ORIGINS", "").split(",") if origin.strip()
}
MAX_REQUEST_BODY = int(os.environ.get("VANTA_MAX_REQUEST_BODY", str(2 * 1024 * 1024)))
MAX_DIAGNOSTICS_LIMIT = int(os.environ.get("VANTA_MAX_DIAGNOSTICS_LIMIT", "200"))
TELEMETRY_QUEUE_SIZE = int(os.environ.get("VANTA_TELEMETRY_QUEUE_SIZE", "4096"))
TELEMETRY_BATCH_SIZE = int(os.environ.get("VANTA_TELEMETRY_BATCH_SIZE", "64"))
TELEMETRY_RETENTION_DAYS = int(os.environ.get("VANTA_TELEMETRY_RETENTION_DAYS", "30"))
TELEMETRY_MAX_LOG_BYTES = int(os.environ.get("VANTA_TELEMETRY_MAX_LOG_BYTES", str(50 * 1024 * 1024)))
TELEMETRY_MAX_LOG_FILES = int(os.environ.get("VANTA_TELEMETRY_MAX_LOG_FILES", "4"))


_SENSITIVE_PATTERNS = [
    (re.compile(r"(?i)(license[_ -]?key\s*[:=]\s*)([^\s,;|]+)"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(hwid\s*[:=]\s*)([^\s,;|]+)"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(token\s*[:=]\s*)([^\s,;|]+)"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(password\s*[:=]\s*)([^\s,;|]+)"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(secret\s*[:=]\s*)([^\s,;|]+)"), r"\1[REDACTED]"),
    (re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"), "[REDACTED_JWT]"),
    (re.compile(r"X-Amz-Signature=[A-Za-z0-9%_-]+"), "X-Amz-Signature=[REDACTED]"),
]


def redact_text(value):
    if not isinstance(value, str):
        return value
    for pattern, replacement in _SENSITIVE_PATTERNS:
        value = pattern.sub(replacement, value)
    return value


def redact_value(value):
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            if str(key).lower() in {"license_key", "hwid", "token", "password", "secret", "yaml_data"}:
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = redact_value(item)
        return redacted
    if isinstance(value, (list, tuple)):
        return [redact_value(item) for item in value]
    return redact_text(value)


class TelemetryPipeline:
    """Bounded, priority-aware telemetry writer for SQLite and rotating logs."""

    _STOP = object()

    def __init__(self, db_path, log_path, queue_size=TELEMETRY_QUEUE_SIZE,
                 batch_size=TELEMETRY_BATCH_SIZE, max_log_bytes=TELEMETRY_MAX_LOG_BYTES,
                 max_log_files=TELEMETRY_MAX_LOG_FILES, retention_days=TELEMETRY_RETENTION_DAYS):
        self.db_path = db_path
        self.log_path = log_path
        self.queue = queue.Queue(maxsize=max(1, queue_size))
        self.batch_size = max(1, batch_size)
        self.max_log_bytes = max(1, max_log_bytes)
        self.max_log_files = max(1, max_log_files)
        self.retention_days = max(0, retention_days)
        self.dropped_debug = 0
        self.dropped_total = 0
        self._stats_lock = threading.Lock()
        self._closed = False
        self._done = threading.Event()
        self._idle = threading.Event()
        self._idle.set()
        self._thread = threading.Thread(target=self._writer_loop, name="vanta-telemetry-writer", daemon=True)
        self._thread.start()

    @staticmethod
    def _is_priority(severity):
        return str(severity).upper() in {"WARN", "ERROR", "CRITICAL", "SECURITY"}

    def _enqueue(self, item, priority):
        self._idle.clear()
        try:
            self.queue.put_nowait(item)
            return True
        except queue.Full:
            if not priority:
                with self._stats_lock:
                    self.dropped_debug += 1
                    self.dropped_total += 1
                return False

        # Preserve lifecycle/security events by evicting one lower-priority item.
        retained = []
        evicted = False
        while True:
            try:
                existing = self.queue.get_nowait()
            except queue.Empty:
                break
            if not evicted and not existing["priority"]:
                evicted = True
                with self._stats_lock:
                    self.dropped_debug += 1
                    self.dropped_total += 1
                continue
            retained.append(existing)
        for existing in retained:
            try:
                self.queue.put_nowait(existing)
            except queue.Full:
                with self._stats_lock:
                    self.dropped_total += 1
        try:
            self.queue.put_nowait(item)
            return True
        except queue.Full:
            with self._stats_lock:
                self.dropped_total += 1
            return False

    def record(self, severity, message, details="", client_ip="", slot_num=0,
               slot_id="", hwid="", extra=None):
        payload_extra = redact_value(dict(extra) if extra else {})
        item = {
            "timestamp": int(time.time()),
            "severity": redact_text(severity),
            "message": redact_text(message),
            "details": redact_text(details),
            "client_ip": "[REDACTED]" if client_ip else "",
            "hwid": "[REDACTED]" if hwid else "",
            "slot_num": slot_num,
            "slot_id": redact_text(slot_id),
            "extra": payload_extra,
            "priority": self._is_priority(severity),
            "persist_db": True,
        }
        return self._enqueue(item, item["priority"])

    def log_line(self, message, severity="INFO"):
        item = {
            "timestamp": int(time.time()),
            "severity": severity,
            "message": redact_text(message),
            "details": "",
            "client_ip": "",
            "hwid": "",
            "slot_num": 0,
            "slot_id": "",
            "extra": {},
            "priority": self._is_priority(severity),
            "persist_db": False,
        }
        return self._enqueue(item, item["priority"])

    def _configure_db(self, conn):
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=5000")
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "diagnostics" in tables:
            conn.execute("CREATE INDEX IF NOT EXISTS idx_diagnostics_source_id ON diagnostics(source, id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_diagnostics_timestamp ON diagnostics(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_diagnostics_severity_timestamp ON diagnostics(severity, timestamp)")
        if "audit_logs" in tables:
            conn.execute("""CREATE INDEX IF NOT EXISTS idx_audit_logs_slot_timestamp
                           ON audit_logs(slot_id, timestamp)""")
        if self.retention_days:
            cutoff = int(time.time()) - (self.retention_days * 86400)
            if "diagnostics" in tables:
                conn.execute("DELETE FROM diagnostics WHERE timestamp < ?", (cutoff,))
        conn.commit()

    def _rotate_log_if_needed(self, line_size):
        try:
            current_size = os.path.getsize(self.log_path)
        except OSError:
            current_size = 0
        if current_size == 0 or current_size + line_size <= self.max_log_bytes:
            return
        for index in range(self.max_log_files - 1, 0, -1):
            source = f"{self.log_path}.{index}"
            target = f"{self.log_path}.{index + 1}"
            if os.path.exists(source):
                if index + 1 >= self.max_log_files:
                    try:
                        os.remove(source)
                    except OSError:
                        pass
                else:
                    os.replace(source, target)
        if os.path.exists(self.log_path):
            os.replace(self.log_path, f"{self.log_path}.1")

    def _write_log(self, item):
        line = "[%s] [%s] %s" % (
            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(item["timestamp"])),
            item["severity"],
            item["message"],
        )
        if item["details"]:
            line += " | " + item["details"]
        line += "\n"
        encoded = line.encode("utf-8")
        self._rotate_log_if_needed(len(encoded))
        Path(self.log_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_path, "ab") as handle:
            handle.write(encoded)

    def _write_batch(self, conn, batch):
        db_rows = [item for item in batch if item["persist_db"]]
        if db_rows and conn is not None:
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if "diagnostics" in tables:
                conn.executemany(
                    """INSERT INTO diagnostics
                    (timestamp, severity, source, message, details, client_ip, hwid, extra, resolved)
                    VALUES (?, ?, 'ORCHESTRATOR', ?, ?, ?, ?, ?, 0)""",
                    [(
                        item["timestamp"], item["severity"], item["message"], item["details"],
                        item["client_ip"], item["hwid"], json.dumps({
                            **item["extra"], "slot_num": item["slot_num"], "slot_id": item["slot_id"]
                        }),
                    ) for item in db_rows],
                )
                conn.commit()
        for item in batch:
            self._write_log(item)

    def _writer_loop(self):
        conn = None
        try:
            if os.path.exists(self.db_path):
                conn = sqlite3.connect(self.db_path, timeout=5)
                self._configure_db(conn)
            while True:
                first = self.queue.get()
                if first is self._STOP:
                    break
                batch = [first]
                deadline = time.monotonic() + 0.25
                while len(batch) < self.batch_size and time.monotonic() < deadline:
                    try:
                        item = self.queue.get(timeout=max(0.001, deadline - time.monotonic()))
                    except queue.Empty:
                        break
                    if item is self._STOP:
                        self._write_batch(conn, batch)
                        self._done.set()
                        return
                    batch.append(item)
                self._write_batch(conn, batch)
                if self.queue.empty():
                    self._idle.set()
        except Exception:
            with self._stats_lock:
                self.dropped_total += self.queue.qsize()
        finally:
            if conn is not None:
                conn.close()
            self._idle.set()
            self._done.set()

    def flush(self, timeout=5):
        ready = self._idle.wait(timeout)
        if ready and not os.path.exists(self.log_path):
            Path(self.log_path).parent.mkdir(parents=True, exist_ok=True)
            Path(self.log_path).touch()
        return ready

    def close(self, timeout=5):
        if self._closed:
            return
        self._closed = True
        deadline = time.monotonic() + timeout
        while not self.queue.empty() and time.monotonic() < deadline:
            time.sleep(0.01)
        try:
            self.queue.put_nowait(self._STOP)
        except queue.Full:
            self.queue.get_nowait()
            self.queue.put_nowait(self._STOP)
        self._done.wait(max(0, deadline - time.monotonic()))


_telemetry_pipeline = None
_telemetry_pipeline_lock = threading.Lock()


def get_telemetry_pipeline():
    global _telemetry_pipeline
    with _telemetry_pipeline_lock:
        if _telemetry_pipeline is None:
            _telemetry_pipeline = TelemetryPipeline(DB_PATH, TELEMETRY_LOG)
        return _telemetry_pipeline


@dataclass(frozen=True)
class ProcessSnapshot:
    pid: int
    ppid: int
    executable: str
    command_line: str
    start_time: float
    rss_kb: int = 0


@dataclass(frozen=True)
class ProcessIdentity:
    pid: int
    executable: str
    start_time: float


class ProcessRegistry:
    """One immutable process snapshot shared by all slot workers."""

    def __init__(self, refresh_interval=0.5):
        self.refresh_interval = max(0.0, refresh_interval)
        self.provider = self._scan_processes
        self._lock = threading.Lock()
        self._snapshot = tuple()
        self._refreshed_at = 0.0

    @staticmethod
    def _scan_processes():
        try:
            output = subprocess.check_output(
                ["ps", "-axo", "pid=,ppid=,rss=,command="], timeout=5
            ).decode(errors="replace")
        except Exception:
            return []
        result = []
        for line in output.splitlines():
            parts = line.strip().split(None, 3)
            if len(parts) != 4:
                continue
            try:
                pid, ppid, rss_kb = int(parts[0]), int(parts[1]), int(parts[2])
            except ValueError:
                continue
            command_line = parts[3]
            result.append(ProcessSnapshot(pid, ppid, command_line.split(None, 1)[0], command_line, 0.0, rss_kb))
        return result

    def snapshot(self, force=False):
        now = time.monotonic()
        with self._lock:
            if not force and self._snapshot and now - self._refreshed_at < self.refresh_interval:
                return self._snapshot
            self._snapshot = tuple(self.provider())
            self._refreshed_at = now
            return self._snapshot

    def match(self, predicate):
        return next((process for process in self.snapshot() if predicate(process)), None)

    def identity_is_current(self, identity):
        current = next((process for process in self.snapshot() if process.pid == identity.pid), None)
        if current is None:
            return False
        if current.executable != identity.executable:
            return False
        return identity.start_time <= 0 or current.start_time == identity.start_time


process_registry = ProcessRegistry()


def wait_with_backoff(predicate, cancel_event, deadline, initial_delay=0.1, max_delay=2.0):
    delay = initial_delay
    while time.monotonic() < deadline:
        if cancel_event.is_set():
            return False
        if predicate():
            return True
        if cancel_event.wait(min(delay, max(0.0, deadline - time.monotonic()))):
            return False
        delay = min(max_delay, delay * 2)
    return False

def log(msg: str):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {redact_text(msg)}"
    print(line)
    sys.stdout.flush()
    get_telemetry_pipeline().log_line(msg)

def record_telemetry(severity: str, message: str, details: str = "", client_ip: str = "", slot_num: int = 0, slot_id: str = "", hwid: str = "", extra: dict = None):
    decorated = f"[{severity}][slot:{slot_num:02d}][{client_ip or 'local'}] {message} | {details}"
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {redact_text(decorated)}")
    sys.stdout.flush()
    return get_telemetry_pipeline().record(severity, message, details, client_ip, slot_num, slot_id, hwid, extra)

slots: dict = {}
slots_lock = threading.RLock()
active_slot_nums: set = set()
slot_reservations: dict = {}
concluded_engine_pids: set = set()

class SlotState:
    def __init__(self, slot_id: str, slot_num: int):
        self.slot_id        = slot_id
        self.slot_num       = slot_num
        self.slot_generation = uuid.uuid4().hex
        self.match_generation = 0
        self.cancel_event    = threading.Event()
        self.teardown_complete = threading.Event()
        self.lifecycle_state = "ALLOCATED"
        self._teardown_started = False
        self.data_dir       = os.path.join(BASE_SLOTS_DIR, f"slot{slot_num}")
        self.app_path       = f"/Applications/League of Legends_slot{slot_num}.app"
        # Non-overlapping port offsets for concurrent slots (Slots 1..100):
        # Slot 1 retains original legacy ports (8090, 8096, 8200) for backward compatibility.
        # Slots 2..100 use dedicated 1000-port spaced collision-free ranges:
        # proxy_port:     9102..9200
        # lcu_port:       9302..9400
        # udp_proxy_port: 9502..9600
        if slot_num == 1:
            self.proxy_port     = 8090
            self.lcu_port       = 8096
            self.udp_proxy_port = 8200
        else:
            self.proxy_port     = 9100 + slot_num
            self.lcu_port       = 9300 + slot_num
            self.udp_proxy_port = 9500 + slot_num
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
        self.license_id     = None
        self.session_id     = None
        self.device_thumbprint = None
        self.idempotency_key = None
        self.created_at     = time.time()
        self.last_poll      = time.time()
        self._proxy_srv     = None
        self._proxy_stop    = None
        self._lcu_srv       = None
        self._lcu_stop      = None
        self._udp_srv       = None
        self._udp_stop      = None

    def begin_match(self):
        self.match_generation += 1
        self.lifecycle_state = "MATCH_ACTIVE"
        return self.match_generation


def slot_is_current(slot: SlotState, generation: str) -> bool:
    with slots_lock:
        return (slots.get(slot.slot_id) is slot and
                slot.slot_generation == generation and
                slot.lifecycle_state not in ("STOPPING", "FREED") and
                not slot.cancel_event.is_set())


def snapshot_slot(slot: SlotState) -> dict:
    return {
        "status": slot.status,
        "args": list(slot.args),
        "game_args": list(slot.game_args),
        "proxy_port": slot.proxy_port,
        "lcu_port": slot.lcu_port,
        "udp_proxy_port": slot.udp_proxy_port,
        "rc_port": slot.rc_port,
        "slot_num": slot.slot_num,
        "slot_generation": slot.slot_generation,
        "match_generation": slot.match_generation,
        "lifecycle_state": slot.lifecycle_state,
        "direct_udp_route": DIRECT_UDP_ROUTE,
        "routing_mode": "direct" if DIRECT_UDP_ROUTE else "proxy",
        "slot_owner": slot.license_id,
    }


def runtime_metrics():
    pipeline = get_telemetry_pipeline()
    with pipeline._stats_lock:
        dropped_debug = pipeline.dropped_debug
        dropped_total = pipeline.dropped_total
    return {
        "thread_count": threading.active_count(),
        "slot_count": len(slots),
        "process_snapshot_age_seconds": round(max(0.0, time.monotonic() - process_registry._refreshed_at), 3) if process_registry._refreshed_at else None,
        "process_snapshot_count": len(process_registry._snapshot),
        "telemetry_queue_depth": pipeline.queue.qsize(),
        "telemetry_dropped_debug": dropped_debug,
        "telemetry_dropped_total": dropped_total,
    }

def alloc_slot_num(preferred=None) -> int:
    if preferred is not None:
        if preferred in active_slot_nums:
            raise RuntimeError("Slot number is still reserved")
        if preferred < 1 or preferred > MAX_SLOTS:
            raise RuntimeError("Invalid slot number")
        active_slot_nums.add(preferred)
        slot_reservations[preferred] = None
        return preferred
    for num in range(1, MAX_SLOTS + 1):
        if num not in active_slot_nums:
            active_slot_nums.add(num)
            slot_reservations[num] = None
            return num
    raise RuntimeError(f"No free slot numbers available (All {MAX_SLOTS} slots occupied)")

def free_slot_num(num: int):
    active_slot_nums.discard(num)
    slot_reservations.pop(num, None)

def get_slot_by_num(num: int):
    with slots_lock:
        for s in slots.values():
            if getattr(s, "slot_num", None) == num:
                return s
    return None


def complete_slot_teardown(slot: SlotState):
    with slots_lock:
        if slot.lifecycle_state == "FREED":
            return
        owner = slot_reservations.get(slot.slot_num)
        if owner not in (None, slot.slot_generation):
            slot.teardown_complete.set()
            return
        slot.lifecycle_state = "FREED"
        free_slot_num(slot.slot_num)
        slot.teardown_complete.set()


def request_slot_teardown(slot_id: str, generation: str, reason: str) -> bool:
    with slots_lock:
        slot = slots.get(slot_id)
        if not slot or slot.slot_generation != generation or slot._teardown_started:
            return False
        slot._teardown_started = True
        slot.lifecycle_state = "STOPPING"
        slot.cancel_event.set()
        slot_reservations[slot.slot_num] = slot.slot_generation
        slots.pop(slot_id, None)

    def teardown():
        try:
            record_telemetry("INFO", "SLOT_TEARDOWN", f"Closing slot {slot.slot_num} ({slot_id[:8]}): {reason}", slot.client_ip, slot.slot_num, slot_id)
            for stop_flag, server in ((slot._proxy_stop, slot._proxy_srv), (slot._lcu_stop, slot._lcu_srv), (slot._udp_stop, slot._udp_srv)):
                if stop_flag:
                    stop_flag[0] = False
                if server:
                    try: server.close()
                    except Exception: pass
            clean_slot_processes_isolated(slot)
            for lockfile in (os.path.join(slot.data_dir, "Config", "lockfile"), os.path.join(slot.app_path, "Contents", "LoL", "lockfile")):
                try:
                    if os.path.exists(lockfile): os.remove(lockfile)
                except Exception: pass
        finally:
            complete_slot_teardown(slot)
            record_telemetry("INFO", "SLOT_FREED", f"Slot {slot.slot_num} returned to free pool", slot.client_ip, slot.slot_num, slot_id)
    threading.Thread(target=teardown, daemon=True).start()
    return True


def conclude_match(slot_id: str, match_generation: int) -> bool:
    with slots_lock:
        slot = slots.get(slot_id)
        if not slot or slot.match_generation != match_generation:
            return False
        return True

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

class RelayHandle:
    def __init__(self, server, stop_flag, port, sockets, threads):
        self.server = server
        self.stop_flag = stop_flag
        self.port = port
        self.sockets = sockets
        self.threads = threads
        self.closed = False
        self._lock = threading.Lock()

    @property
    def active_connections(self):
        with self._lock:
            return len(self.sockets)

    def __iter__(self):
        # Compatibility with existing ``server, stop_flag = start_*_proxy`` callers.
        yield self.server
        yield self.stop_flag

    def register_socket(self, sock):
        with self._lock:
            if self.closed:
                return False
            self.sockets.add(sock)
            return True

    def unregister_socket(self, sock):
        with self._lock:
            self.sockets.discard(sock)

    def close(self, timeout=2):
        with self._lock:
            if self.closed:
                return
            self.closed = True
            self.stop_flag[0] = False
            sockets = list(self.sockets)
        try:
            self.server.close()
        except Exception:
            pass
        for sock in sockets:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                sock.close()
            except Exception:
                pass
        deadline = time.monotonic() + max(0, timeout)
        for thread in list(self.threads):
            if thread is threading.current_thread() or not thread.is_alive():
                continue
            thread.join(max(0, deadline - time.monotonic()))


def start_tcp_proxy(listen_port: int, target_port):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    srv.bind((RELAY_BIND_HOST, listen_port))
    srv.listen(128)
    actual_port = srv.getsockname()[1]
    log(f"[proxy] TCP/WS {RELAY_BIND_HOST}:{actual_port} -> dynamic target {target_port}")

    is_running = [True]
    sockets = {srv}
    threads = set()
    handle = RelayHandle(srv, is_running, actual_port, sockets, threads)

    # Optional secondary listener: dual-bind 8096 and 8150 for LCU compatibility
    sec_srv = None
    secondary_port = 8150 if listen_port == 8096 else (8096 if listen_port == 8150 else None)
    if secondary_port:
        try:
            s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s2.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s2.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            s2.bind((RELAY_BIND_HOST, secondary_port))
            s2.listen(128)
            handle.register_socket(s2)
            sec_srv = s2
            log(f"[proxy] Dual-bound secondary port {RELAY_BIND_HOST}:{secondary_port}")
        except Exception:
            sec_srv = None

    def get_target_port():
        if callable(target_port):
            try: return target_port()
            except Exception: return None
        return target_port

    def relay_raw(src, dst):
        handle.register_socket(src)
        handle.register_socket(dst)
        try:
            while is_running[0]:
                d = src.recv(65536)
                if not d: break
                dst.sendall(d)
        except Exception:
            pass
        finally:
            handle.unregister_socket(src)
            handle.unregister_socket(dst)
            try: src.close()
            except: pass
            try: dst.close()
            except: pass

    def relay_ws(client_sock, target_sock):
        handle.register_socket(client_sock)
        handle.register_socket(target_sock)
        stop = [False]

        def target_to_ws():
            try:
                while is_running[0] and not stop[0]:
                    data = target_sock.recv(32768)
                    if not data:
                        break
                    length = len(data)
                    if length < 126:
                        header = struct.pack("!BB", 0x82, length)
                    elif length <= 0xFFFF:
                        header = struct.pack("!BBH", 0x82, 126, length)
                    else:
                        header = struct.pack("!BBQ", 0x82, 127, length)
                    client_sock.sendall(header + data)
            except Exception:
                pass
            finally:
                stop[0] = True
                try: client_sock.close()
                except: pass
                try: target_sock.close()
                except: pass

        def ws_to_target():
            try:
                buf = bytearray()
                while is_running[0] and not stop[0]:
                    chunk = client_sock.recv(32768)
                    if not chunk:
                        break
                    buf.extend(chunk)

                    while len(buf) >= 2:
                        b1 = buf[0]
                        b2 = buf[1]
                        opcode = b1 & 0x0F
                        masked = (b2 & 0x80) != 0
                        payload_len = b2 & 0x7F

                        offset = 2
                        if payload_len == 126:
                            if len(buf) < 4: break
                            payload_len = struct.unpack("!H", buf[2:4])[0]
                            offset = 4
                        elif payload_len == 127:
                            if len(buf) < 10: break
                            payload_len = struct.unpack("!Q", buf[2:10])[0]
                            offset = 10

                        mask_key = None
                        if masked:
                            if len(buf) < offset + 4: break
                            mask_key = buf[offset:offset+4]
                            offset += 4

                        if len(buf) < offset + payload_len:
                            break

                        payload = buf[offset:offset+payload_len]
                        del buf[:offset+payload_len]

                        if opcode == 0x8:
                            stop[0] = True
                            return
                        elif opcode == 0x9:
                            pong = struct.pack("!BB", 0x8A, 0)
                            client_sock.sendall(pong)
                            continue
                        elif opcode in (0x1, 0x2):
                            if masked and mask_key:
                                unmasked = bytearray(len(payload))
                                for i in range(len(payload)):
                                    unmasked[i] = payload[i] ^ mask_key[i % 4]
                                target_sock.sendall(unmasked)
                            else:
                                target_sock.sendall(payload)
            except Exception:
                pass
            finally:
                stop[0] = True
                try: client_sock.close()
                except: pass
                try: target_sock.close()
                except: pass

        t1 = threading.Thread(target=target_to_ws, daemon=True)
        t2 = threading.Thread(target=ws_to_target, daemon=True)
        threads.update((t1, t2))
        t1.start()
        t2.start()

    def handle_client(c):
        try:
            if handle.closed:
                c.close()
                return
            c.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            c.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except Exception:
            pass

        peek = b""
        try:
            peek = c.recv(4, socket.MSG_PEEK)
        except Exception:
            pass

        if peek.startswith(b"GET ") or peek.startswith(b"POST"):
            try:
                req_data = b""
                while b"\r\n\r\n" not in req_data and len(req_data) < 8192:
                    chunk = c.recv(4096)
                    if not chunk:
                        break
                    req_data += chunk

                headers = {}
                lines = req_data.split(b"\r\n")
                for line in lines[1:]:
                    if b":" in line:
                        k, v = line.split(b":", 1)
                        headers[k.strip().lower().decode("utf-8", errors="ignore")] = v.strip().decode("utf-8", errors="ignore")

                ws_key = headers.get("sec-websocket-key")
                if ws_key and "upgrade" in headers.get("connection", "").lower() and headers.get("upgrade", "").lower() == "websocket":
                    first_line = lines[0].decode("utf-8", errors="ignore") if lines else ""
                    req_slot_num = None
                    if "slot=" in first_line:
                        try:
                            part = first_line.split("slot=")[1].split("&")[0].split(" ")[0]
                            req_slot_num = int(part)
                        except Exception:
                            pass

                    port = None
                    for _ in range(25):
                        if req_slot_num is not None:
                            s = get_slot_by_num(req_slot_num)
                            if s:
                                host_hdr = headers.get("host", "").lower()
                                if listen_port in (8096, 8150) or (8150 <= listen_port <= 8174) or (9300 <= listen_port <= 9500) or "tl" in host_hdr:
                                    port = s.app_port
                                else:
                                    port = s.rc_port
                        if not port:
                            port = get_target_port()
                        if port:
                            break
                        time.sleep(0.2)

                    if not port:
                        c.sendall(b"HTTP/1.1 503 Service Unavailable\r\n\r\nBackend Port Not Ready")
                        c.close()
                        return

                    try:
                        t = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        t.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                        t.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                        t.connect(("127.0.0.1", port))
                    except Exception:
                        c.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\nTarget Connect Failed")
                        c.close()
                        return

                    magic = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
                    accept = base64.b64encode(hashlib.sha1(ws_key.encode() + magic).digest()).decode()
                    resp = (
                        "HTTP/1.1 101 Switching Protocols\r\n"
                        "Upgrade: websocket\r\n"
                        "Connection: Upgrade\r\n"
                        f"Sec-WebSocket-Accept: {accept}\r\n\r\n"
                    )
                    c.sendall(resp.encode())
                    relay_ws(c, t)
                    return
                else:
                    c.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 17\r\n\r\nVANTA_RELAY_ALIVE")
                    c.close()
                    return
            except Exception:
                try: c.close()
                except: pass
                return

        port = get_target_port()
        if not port:
            try: c.close()
            except: pass
            return

        try:
            t = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            t.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            t.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            t.connect(("127.0.0.1", port))
        except Exception:
            try: c.close()
            except: pass
            return

        left = threading.Thread(target=relay_raw, args=(c, t), daemon=True)
        right = threading.Thread(target=relay_raw, args=(t, c), daemon=True)
        threads.update((left, right))
        left.start()
        right.start()

    def accept_loop(listener):
        while is_running[0]:
            try:
                c, _ = listener.accept()
            except (OSError, socket.error):
                break
            except Exception:
                break
            threading.Thread(target=handle_client, args=(c,), daemon=True).start()

    accept_thread = threading.Thread(target=accept_loop, args=(srv,), daemon=True)
    threads.add(accept_thread)
    accept_thread.start()

    if sec_srv:
        sec_thread = threading.Thread(target=accept_loop, args=(sec_srv,), daemon=True)
        threads.add(sec_thread)
        sec_thread.start()

    return handle

def start_udp_proxy(listen_port: int, target_ip: str, target_port: int):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((RELAY_BIND_HOST, listen_port))
    actual_port = sock.getsockname()[1]
    log(f"[udp_proxy] UDP {RELAY_BIND_HOST}:{actual_port} <-> {target_ip}:{target_port}")

    client_addr = [None]
    is_running = [True]
    threads = set()
    handle = RelayHandle(sock, is_running, actual_port, {sock}, threads)

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

    loop_thread = threading.Thread(target=loop, daemon=True)
    threads.add(loop_thread)
    loop_thread.start()
    return handle

def kill_pid_safe(pid: int, sig=None):
    if not pid: return
    if sig is None:
        sig = getattr(signal, "SIGKILL", signal.SIGTERM)
    try:
        os.kill(pid, sig)
    except ProcessLookupError:
        pass
    except Exception as err:
        log(f"[cleanup] Error killing PID {pid}: {err}")

def clean_slot_processes_isolated(slot: SlotState):
    # Riot session YAML is a credential, not slot state; remove it on teardown.
    private_yaml = os.path.join(slot.data_dir, "Data", "RiotGamesPrivateSettings.yaml")
    try:
        if os.path.exists(private_yaml): os.remove(private_yaml)
    except OSError:
        pass
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
    generation = slot.slot_generation
    record_telemetry("INFO", "GAME_MONITOR_STARTED", "3D engine monitor active", slot.client_ip, slot.slot_num, slot.slot_id)
    for _ in range(7200):
        with slots_lock:
            if not slot_is_current(slot, generation):
                break
        try:
            for process in process_registry.snapshot():
                line = f"{process.pid} {process.ppid} {process.command_line}"
                lower_line = process.command_line.lower()
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
                    if slot.lc_pid and ppid != slot.lc_pid and f"_slot{slot.slot_num}.app" not in process.command_line:
                        continue

                    with slots_lock:
                        if not slot_is_current(slot, generation):
                            return
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

                    udp_handle = start_udp_proxy(slot.udp_proxy_port, target_ip, target_port)
                    slot._udp_srv = udp_handle
                    slot._udp_stop = udp_handle.stop_flag

                    if not DIRECT_UDP_ROUTE:
                        if not PUBLIC_HOST:
                            log("[game_monitor] VANTA_PUBLIC_HOST / M1_HOST missing; cannot rewrite UDP relay target")
                            continue
                        game_args[0] = PUBLIC_HOST
                        game_args[1] = str(slot.udp_proxy_port)

                    with slots_lock:
                        if not slot_is_current(slot, generation):
                            return
                        slot.game_args = game_args
                        slot.engine_pid = pid
                        slot.begin_match()

                    mode_str = "DIRECT (15-25ms)" if DIRECT_UDP_ROUTE else f"UDP PROXY {slot.udp_proxy_port} (100ms)"
                    record_telemetry("INFO", "3D_GAME_ENGINE_CAPTURED", f"Target: {target_ip}:{target_port} -> Mode: {mode_str}", slot.client_ip, slot.slot_num, slot.slot_id, extra={"engine_pid": pid, "target_ip": target_ip, "target_port": target_port, "udp_proxy_port": slot.udp_proxy_port, "direct_udp": DIRECT_UDP_ROUTE})
                    try:
                        os.kill(pid, signal.SIGSTOP)
                        log(f"[game_monitor:slot{slot.slot_num}] Suspended (SIGSTOP) Mac 3D engine PID {pid} to keep parent LeagueClient in 'InProgress' phase")
                        try:
                            subprocess.run(["purge"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        except Exception:
                            pass
                    except Exception as err:
                        log(f"[game_monitor:slot{slot.slot_num}] Error suspending Mac game: {err}")

                    while True:
                        time.sleep(1.0)
                        with slots_lock:
                            if not slot_is_current(slot, generation):
                                return
                        if slot.engine_pid is None and len(slot.game_args) == 0:
                            concluded_engine_pids.add(pid)
                            if len(concluded_engine_pids) > 512:
                                concluded_engine_pids.pop()
                            record_telemetry("INFO", "MATCH_CONCLUDED_MONITOR_RESET", "3D Game Engine reset cleanly", slot.client_ip, slot.slot_num, slot.slot_id)
                            log(f"[game_monitor:slot{slot.slot_num}] Match concluded cleanly for PID {pid}. Ready for next match.")
                            break
                        try:
                            os.kill(pid, 0)
                        except OSError:
                            with slots_lock:
                                if slot.engine_pid == pid:
                                    slot.engine_pid = None
                                    slot.game_args = []
                            concluded_engine_pids.add(pid)
                            if len(concluded_engine_pids) > 512:
                                concluded_engine_pids.pop()
                            record_telemetry("INFO", "MATCH_CONCLUDED_MONITOR_RESET", "3D Game Engine terminated on Mac", slot.client_ip, slot.slot_num, slot.slot_id)
                            log(f"[game_monitor:slot{slot.slot_num}] 3D Game Engine PID {pid} exited on Mac. Ready for next match.")
                            break
        except Exception as e:
            log(f"[game_monitor:slot{slot.slot_num}] error: {e}")
        time.sleep(1.0)

def suppress_electron_ui_for_slot(slot: SlotState, generation: str):
    """
    Headless optimizer: Terminate high-memory Electron GUI front-end
    spawned by RiotClientServices. RCS remains 100% operational as a headless
    daemon providing full REST API, saving ~800MB RAM per slot.
    """
    for _ in range(40):
        time.sleep(1.0)
        with slots_lock:
            if not slot_is_current(slot, generation):
                return
        try:
            ps_out = subprocess.check_output(["ps", "-ef"], timeout=5).decode(errors="replace")
            for line in ps_out.splitlines():
                parts = line.split()
                if len(parts) > 1 and parts[1].isdigit():
                    pid = int(parts[1])
                    if pid != slot.rc_pid and f"slot{slot.slot_num}" in line and "Riot Client.app" in line:
                        try:
                            os.kill(pid, signal.SIGKILL)
                            record_telemetry("INFO", "HEADLESS_OPTIMIZATION", f"Suppressed heavy UI PID {pid} for slot {slot.slot_num} (~800MB RAM saved)", slot.client_ip, slot.slot_num, slot.slot_id)
                            return
                        except OSError:
                            pass
        except Exception:
            pass

def vm_worker(slot: SlotState, yaml_data: str):
    t_start = time.time()
    generation = slot.slot_generation
    try:
        if not slot_is_current(slot, generation):
            return
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
        os.chmod(private_yaml, 0o600)

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
        with slots_lock:
            if not slot_is_current(slot, generation):
                proc.kill()
                return
            slot.rc_proc = proc
            slot.rc_pid = proc.pid
        record_telemetry("INFO", "RC_SPAWNED", f"PID {proc.pid} spawned with user-data-root {slot.data_dir}", slot.client_ip, slot.slot_num, slot.slot_id, extra={"rc_pid": proc.pid})
        threading.Thread(target=suppress_electron_ui_for_slot, args=(slot, generation), daemon=True).start()

        rc_port, rc_token = None, None
        for _ in range(45):
            rc_port, rc_token = read_lockfile(lockfile_path)
            if rc_port and rc_token: break
            time.sleep(1)

        if not rc_port:
            _fail(slot, f"RC lockfile timeout in {slot.data_dir}")
            return

        with slots_lock:
            if not slot_is_current(slot, generation):
                return
            slot.rc_port  = rc_port
            slot.rc_token = rc_token
        proxy_handle = start_tcp_proxy(slot.proxy_port, lambda: slot.rc_port)
        slot._proxy_srv = proxy_handle
        slot._proxy_stop = proxy_handle.stop_flag
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

        if not session_ready:
            _fail(slot, "Riot session authentication timeout")
            return

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
            if not slot_is_current(slot, generation):
                return
            try:
                for process in process_registry.snapshot():
                    line = f"{process.pid} {process.command_line}"
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
                        with slots_lock:
                            if not slot_is_current(slot, generation):
                                return
                            if app_port:
                                slot.app_port = app_port
                                slot.lc_pid = pid
                                lcu_handle = start_tcp_proxy(slot.lcu_port, lambda: slot.app_port)
                                slot._lcu_srv = lcu_handle
                                slot._lcu_stop = lcu_handle.stop_flag
                            slot.status = "game_ready"
                            slot.lifecycle_state = "READY"
                            slot.args   = list(args)
                        
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
        if not slot_is_current(slot, slot.slot_generation):
            return
        slot.status = f"FAILED: {reason}"
    record_telemetry("ERROR", "SLOT_FAILED", reason, slot.client_ip, slot.slot_num, slot.slot_id)
    request_slot_teardown(slot.slot_id, slot.slot_generation, reason)

def _cleanup_slot_locked(sid: str):
    slot = slots.get(sid)
    if slot:
        request_slot_teardown(sid, slot.slot_generation, "cleanup")

def slot_reaper_loop():
    while True:
        time.sleep(5)
        now = time.time()
        to_clean = []
        telemetry_events = []
        with slots_lock:
            for sid, s in list(slots.items()):
                # 1. Active 3D Game Match: NEVER evict while match is active!
                if getattr(s, "engine_pid", None) is not None or getattr(s, "game_args", None):
                    continue

                # 2. Slot in game_ready state (user is in lobby or between matches)
                if s.status == "game_ready":
                    # Check if RiotClient process is still alive. If RiotClient is alive, slot is healthy.
                    rc_alive = False
                    if getattr(s, "rc_pid", None):
                        try:
                            os.kill(s.rc_pid, 0)
                            rc_alive = True
                        except (ProcessLookupError, OSError):
                            pass

                    # If RiotClient died completely, slot is orphaned
                    if not rc_alive and getattr(s, "rc_pid", None):
                        to_clean.append((sid, f"RiotClient process {s.rc_pid} terminated"))
                        continue

                    # Inactivity timeout for game_ready (900s / 15 minutes without polling)
                    if (now - getattr(s, "last_poll", now)) > 900.0:
                        to_clean.append((sid, "Client inactivity timeout (>900s)"))
                        continue
                    continue

                # 3. Slot in initial provisioning state (180s timeout)
                if s.status == "provisioning" and (now - getattr(s, "created_at", now)) > 180.0:
                    to_clean.append((sid, "Provisioning timeout (>180s)"))
                    continue

            for sid, reason in to_clean:
                stale_slot = slots.get(sid)
                snum = getattr(stale_slot, "slot_num", 0)
                telemetry_events.append((reason, getattr(stale_slot, "client_ip", ""), snum, sid))
                _cleanup_slot_locked(sid)
        for reason, client_ip, slot_num, sid in telemetry_events:
            record_telemetry("WARN", "REAPER_EVICTION", reason, client_ip, slot_num, sid)

# ── HTTP Server Request Handler ────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _entitlement(self, scope, slot=None, payload=None):
        try:
            claims = entitlement_verifier().verify(self.headers.get("Authorization", ""), scope)
        except EntitlementError:
            self._json(401, {"error": "invalid_entitlement"})
            return None
        if slot is not None:
            generation = self.headers.get("X-Vanta-Slot-Generation") or (payload or {}).get("slot_generation")
            if (slot.license_id != claims.get("sub") or slot.session_id != claims.get("sid") or
                    slot.device_thumbprint != claims.get("device_key_thumbprint") or
                    generation != slot.slot_generation):
                self._json(403, {"error": "slot_owner_mismatch"})
                return None
        return claims

    def _admin(self):
        expected = os.environ.get("VANTA_ORCHESTRATOR_ADMIN_TOKEN", "")
        supplied = self.headers.get("X-Vanta-Admin-Token", "")
        if not expected or not supplied or not hmac.compare_digest(expected, supplied):
            self._json(403 if expected else 503, {"error": "private_admin_required"})
            return False
        return True

    def do_POST(self):
        try:
            self._do_POST()
        except Exception as err:
            log(f"[http] POST {self.path} failed: {type(err).__name__}: {err}")
            try:
                self._json(500, {"error": "internal_server_error", "message": "request processing failed"})
            except Exception:
                self.close_connection = True

    def _do_POST(self):
        if self.path == "/api/request_slot":
            claims = self._entitlement("slot:create")
            if claims is None:
                return
            client_ip = self.client_address[0]
            # Optional diagnostic identity header; older clients do not send it.
            # Never require it for slot allocation and redact it in telemetry.
            hwid = self.headers.get("X-Vanta-HWID", "").strip()

            try:
                length = int(self.headers.get("Content-Length", 0))
            except (TypeError, ValueError):
                self._json(400, {"error": "invalid_content_length"})
                return
            if length < 0 or length > MAX_REQUEST_BODY:
                self._json(413, {"error": "request_too_large", "max_bytes": MAX_REQUEST_BODY})
                return
            yaml_data = self.rfile.read(length).decode()
            client_hash = hashlib.sha256(yaml_data.encode()).hexdigest()[:16]
            idem = self.headers.get("Idempotency-Key", "").strip()
            if not idem or len(idem) > 128:
                self._json(400, {"error": "idempotency_key_required"})
                return
            idem_key = (claims["sub"], claims["sid"], idem)
            with IDEMPOTENCY_LOCK:
                old = IDEMPOTENCY_SLOTS.get(idem_key)
                if old:
                    with slots_lock:
                        existing = slots.get(old)
                    if existing and existing.license_id == claims["sub"] and existing.session_id == claims["sid"]:
                        self._json(200, {"slot_id": old, "proxy_port": existing.proxy_port, "lcu_port": existing.lcu_port, "udp_proxy_port": existing.udp_proxy_port, "slot_generation": existing.slot_generation, "idempotent": True})
                        return

            reclaim_events = []
            with slots_lock:
                client_ip = self.client_address[0]
                # Auto-clear ONLY if the same account credentials / session reconnects
                for sid, s in list(slots.items()):
                    if getattr(s, "client_hash", None) == client_hash:
                        reclaim_events.append(("INFO", "RECONNECT_RECLAIM", f"Auto-clearing previous slot {s.slot_num} ({sid[:8]})", s.slot_num, sid))
                        _cleanup_slot_locked(sid)

                if len(slots) >= MAX_SLOTS:
                    oldest_id = min(slots.keys(), key=lambda sid: getattr(slots[sid], "last_poll", 0))
                    reclaim_events.append(("WARN", "POOL_FULL_EVICTION", f"Evicting oldest slot {oldest_id[:8]} to make room (Capacity: {MAX_SLOTS})", 0, oldest_id))
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
                slot.license_id = claims["sub"]
                slot.session_id = claims["sid"]
                slot.device_thumbprint = claims["device_key_thumbprint"]
                slot.idempotency_key = idem
                slot.last_poll    = time.time()
                slots[slot_id]    = slot

            for severity, event, details, event_slot_num, event_slot_id in reclaim_events:
                record_telemetry(severity, event, details, client_ip, event_slot_num, event_slot_id)
            record_telemetry("INFO", "SLOT_ALLOCATED", f"Slot {slot_num} assigned RCS: {slot.proxy_port}, LCU: {slot.lcu_port}, UDP: {slot.udp_proxy_port}", slot.client_ip, slot_num, slot_id, hwid=hwid, extra={"proxy_port": slot.proxy_port, "lcu_port": slot.lcu_port, "udp_proxy_port": slot.udp_proxy_port})
            threading.Thread(target=vm_worker, args=(slot, yaml_data), daemon=True).start()
            with IDEMPOTENCY_LOCK:
                IDEMPOTENCY_SLOTS[idem_key] = slot_id
            self._json(200, {
                "slot_id":        slot_id,
                "proxy_port":     slot.proxy_port,
                "lcu_port":       slot.lcu_port,
                "udp_proxy_port": slot.udp_proxy_port,
                "max_slots":      MAX_SLOTS,
                "active_count":   len(slots),
                "slot_generation": slot.slot_generation
            })
        elif self.path in ("/api/slots/reset", "/api/slots/clear_all"):
            if not self._admin(): return
            with slots_lock:
                slot_ids = list(slots.keys())
                for sid in slot_ids:
                    _cleanup_slot_locked(sid)
            record_telemetry("WARN", "EMERGENCY_RESET", f"Cleared {len(slot_ids)} owned slots", self.client_address[0])
            self._json(200, {"success": True, "cleared_slots": len(slot_ids), "max_slots": MAX_SLOTS})
        elif self.path == "/api/slots/kill":
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode() if length > 0 else "{}"
            try: payload = json.loads(raw)
            except Exception: payload = {}
            claims = self._entitlement("slot:stop")
            if claims is None:
                return
            sid = payload.get("slot_id")
            with slots_lock:
                slot = slots.get(sid)
                if slot and slot.license_id == claims.get("sub") and slot.session_id == claims.get("sid") and self._entitlement("slot:stop", slot, payload):
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
            claims = self._entitlement("match:conclude")
            if claims is None:
                return
            sid = payload.get("slot_id")
            requested_match_generation = payload.get("match_generation")
            with slots_lock:
                slot = slots.get(sid)
            if not slot:
                self._json(404, {"error": "slot_not_found"})
                return
            if slot.license_id != claims.get("sub") or slot.session_id != claims.get("sid") or self._entitlement("match:conclude", slot, payload) is None:
                return

            if requested_match_generation is not None:
                try:
                    requested_match_generation = int(requested_match_generation)
                except (TypeError, ValueError):
                    self._json(409, {"error": "invalid_match_generation"})
                    return
                if not conclude_match(sid, requested_match_generation):
                    self._json(409, {"error": "stale_match_generation"})
                    return

            record_telemetry("INFO", "MATCH_CONCLUDED", f"Match concluded on Windows for slot {slot.slot_num} ({sid[:8]}). Concluding Mac 3D engine PID {slot.engine_pid}", slot.client_ip, slot.slot_num, sid, extra={"engine_pid": slot.engine_pid, "match_generation": slot.match_generation})
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
                slot.lifecycle_state = "READY"
                if slot._udp_srv:
                    try: slot._udp_srv.close()
                    except: pass
                    slot._udp_srv = None
                    slot._udp_stop = None

            self._json(200, {"success": True, "message": "match_concluded_processed", "slot_num": slot.slot_num})
        elif self.path == "/api/config/routing":
            if not self._admin(): return
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

        if parsed.path == "/api/ping":
            self._json(200, {"status": "ok", "time": time.time()})
            return
        elif parsed.path == "/api/announcements":
            self._json(200, {"active": False, "message": ""})
            return

        if parsed.path == "/api/poll_slot":
            claims = self._entitlement("slot:poll")
            if claims is None:
                return
            slot_id = params.get("slot_id", [None])[0]
            with slots_lock:
                slot = slots.get(slot_id)
            if not slot:
                self._json(404, {"error": "not_found"})
                return
            if slot.license_id != claims.get("sub") or slot.session_id != claims.get("sid") or self._entitlement("slot:poll", slot) is None:
                return

            slot.last_poll = time.time()
            self._json(200, snapshot_slot(slot))
        elif parsed.path == "/api/config/routing":
            if not self._admin(): return
            self._json(200, {
                "direct_udp_route": DIRECT_UDP_ROUTE,
                "mode": "direct" if DIRECT_UDP_ROUTE else "proxy",
                "latency": "15-25ms" if DIRECT_UDP_ROUTE else "100ms",
                "description": "Direct 15-25ms UDP routing" if DIRECT_UDP_ROUTE else "Relayed 100ms M1 proxy routing"
            })
        elif parsed.path == "/api/slots":
            if not self._admin(): return
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
            if not self._admin(): return
            slot_filter = params.get("slot", [None])[0]
            try:
                limit_val = int(params.get("limit", [50])[0])
            except (TypeError, ValueError):
                self._json(400, {"error": "invalid_limit"})
                return
            limit_val = max(1, min(MAX_DIAGNOSTICS_LIMIT, limit_val))
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
                "free_slots":   MAX_SLOTS - len(slots),
                "metrics":      runtime_metrics(),
            })
        else:
            self.send_response(404); self.end_headers()

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        origin = self.headers.get("Origin", "")
        if origin and origin in ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

if __name__ == "__main__":
    if not os.environ.get("VANTA_ENTITLEMENT_PUBLIC_KEYS"):
        raise SystemExit("VANTA_ENTITLEMENT_PUBLIC_KEYS is required; refusing anonymous orchestrator mode")
    server = ThreadingHTTPServer((os.environ.get("VANTA_ORCH_BIND", "127.0.0.1"), ORCH_PORT), Handler)
    threading.Thread(target=slot_reaper_loop, daemon=True).start()
    log(f"[server] VANTA 25-Slot Zero-Collision Orchestrator V6.3 listening on 0.0.0.0:{ORCH_PORT}")
    server.serve_forever()
