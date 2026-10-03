import base64
import hashlib
import json
import os
import time
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEY_FILE = "/Users/m1/vanta_ed25519_root.key"
DEFAULT_PRIV_B64 = "ESbsBLA+NpGJQ42C6QN7kxM0xjfOCnGEfwrMYk4U9dg="
DEFAULT_PUB_B64 = "UAvCUdWyYOZZLOP95Kq53o94w6dyFv0i3FL3qcSuoCU="

AES_KEY = hashlib.sha256(b"VANTA_APEX_KERNEL_TRANSPORT_SECRET_2026_SOVEREIGN_KEY_!#").digest()

def get_keys():
    priv_b64 = DEFAULT_PRIV_B64
    if os.path.exists(KEY_FILE):
        try:
            with open(KEY_FILE, "r") as f:
                c = f.read().strip()
                if c:
                    priv_b64 = c
        except Exception:
            pass
    priv_raw = base64.b64decode(priv_b64)
    priv_key = ed25519.Ed25519PrivateKey.from_private_bytes(priv_raw)
    pub_key = priv_key.public_key()
    return priv_key, pub_key

_priv_key, _pub_key = get_keys()
_aesgcm = AESGCM(AES_KEY)

def encrypt_envelope(plaintext: bytes) -> str:
    """Encrypts raw bytes using AES-256-GCM with a 12-byte random nonce, returns Base64."""
    nonce = os.urandom(12)
    ciphertext = _aesgcm.encrypt(nonce, plaintext, None)
    return base64.b64encode(nonce + ciphertext).decode("ascii")

def decrypt_envelope(b64_packet: str) -> bytes:
    """Decrypts a Base64 AES-256-GCM packet, returning raw plaintext bytes."""
    raw = base64.b64decode(b64_packet)
    if len(raw) < 28: # 12 nonce + 16 auth tag
        raise ValueError("Ciphertext packet too short")
    nonce = raw[:12]
    ciphertext = raw[12:]
    return _aesgcm.decrypt(nonce, ciphertext, None)

def sign_ticket(ticket_dict: dict) -> tuple:
    """Creates a canonical JSON ticket and signs it with the Ed25519 private key."""
    canonical_json = json.dumps(ticket_dict, sort_keys=True, separators=(',', ':')).encode("utf-8")
    sig = _priv_key.sign(canonical_json)
    b64_ticket = base64.b64encode(canonical_json).decode("ascii")
    b64_sig = base64.b64encode(sig).decode("ascii")
    return b64_ticket, b64_sig

def verify_ticket(b64_ticket: str, b64_sig: str) -> tuple:
    """Verifies ticket authenticity against server public key. Returns (valid: bool, data: dict)."""
    try:
        ticket_bytes = base64.b64decode(b64_ticket)
        sig_bytes = base64.b64decode(b64_sig)
        _pub_key.verify(sig_bytes, ticket_bytes)
        ticket = json.loads(ticket_bytes.decode("utf-8"))
        if ticket.get("expires_at", 0) < time.time():
            return False, {"error": "Ticket expired"}
        return True, ticket
    except Exception as e:
        return False, {"error": str(e)}

if __name__ == "__main__":
    t = {
        "license_key": "VANTA-TEST-ROOT",
        "hwid": "HWID-WIN-999",
        "role": "vip",
        "expires_at": int(time.time()) + 86400,
        "nonce": "test_nonce_12345",
        "issued_at": int(time.time())
    }
    b_ticket, b_sig = sign_ticket(t)
    print("Ticket Base64:", b_ticket)
    print("Sig Base64:", b_sig)
    ok, res = verify_ticket(b_ticket, b_sig)
    print("Verify Result:", ok, res)

    enc = encrypt_envelope(b'{"test": "hello sovereign vanta"}')
    print("Encrypted:", enc)
    dec = decrypt_envelope(enc)
    print("Decrypted:", dec.decode())
