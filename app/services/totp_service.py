import hmac
import hashlib
import struct
import time
import base64
import secrets
import urllib.parse
from typing import Optional


def generate_totp_secret(length: int = 20) -> str:
    """Generates a cryptographically random Base32 secret string (RFC 4648)."""
    random_bytes = secrets.token_bytes(length)
    return base64.b32encode(random_bytes).decode("utf-8").rstrip("=")


def get_totp_code(secret: str, intervals_no: Optional[int] = None) -> str:
    """Computes a 6-digit TOTP code for the specified time interval (RFC 6238)."""
    if intervals_no is None:
        intervals_no = int(time.time()) // 30
    
    # Pad Base32 string to multiple of 8 characters
    clean_secret = secret.replace(" ", "").upper()
    padding = (8 - len(clean_secret) % 8) % 8
    key = base64.b32decode((clean_secret + "=" * padding), casefold=True)
    
    msg = struct.pack(">Q", intervals_no)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    
    offset = digest[19] & 15
    code = (struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF) % 1000000
    return f"{code:06d}"


def verify_totp(secret: str, code: str, valid_window: int = 1) -> bool:
    """Verifies a 6-digit TOTP code allowing +/- valid_window (default 30 seconds drift)."""
    if not secret or not code:
        return False
    code = str(code).strip().replace(" ", "")
    if len(code) != 6 or not code.isdigit():
        return False
    
    current_interval = int(time.time()) // 30
    for offset in range(-valid_window, valid_window + 1):
        if get_totp_code(secret, current_interval + offset) == code:
            return True
    return False


def get_totp_uri(secret: str, username: str, issuer: str = "Scented Bubbles") -> str:
    """Generates an otpauth:// URI for authenticator applications."""
    encoded_issuer = urllib.parse.quote(issuer)
    encoded_user = urllib.parse.quote(f"{issuer}:{username}")
    clean_secret = secret.replace(" ", "").upper()
    return f"otpauth://totp/{encoded_user}?secret={clean_secret}&issuer={encoded_issuer}&algorithm=SHA1&digits=6&period=30"
