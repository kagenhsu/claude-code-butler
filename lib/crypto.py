"""輕量級加密：HMAC-SHA256 串流模式 + HMAC-SHA256 驗證。

只依賴 stdlib（hashlib / hmac / secrets / base64），不需要額外安裝 cryptography。

格式：base64( salt(16) || nonce(16) || ciphertext || tag(32) )

KDF 用 PBKDF2-HMAC-SHA256（迭代 20 萬次）派生兩把 32-byte 子密鑰：一把用於串流加密、
一把用於 HMAC 認證。雖然強度不如 Fernet / AES-GCM，但對「本地工具避免在 config.json
留下明文 API Key」這個威脅模型已經足夠。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

_PBKDF2_ITERS = 200_000
_DKLEN = 64


def _derive(password: bytes, salt: bytes) -> tuple[bytes, bytes]:
    full = hashlib.pbkdf2_hmac("sha256", password, salt, _PBKDF2_ITERS, dklen=_DKLEN)
    return full[:32], full[32:]


def _keystream(key: bytes, nonce: bytes, n: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < n:
        block = hmac.new(key, nonce + counter.to_bytes(8, "big"), hashlib.sha256).digest()
        out.extend(block)
        counter += 1
    return bytes(out[:n])


def encrypt(plaintext: str, password: bytes) -> str:
    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(16)
    enc_key, mac_key = _derive(password, salt)
    pt = plaintext.encode("utf-8")
    ks = _keystream(enc_key, nonce, len(pt))
    ct = bytes(a ^ b for a, b in zip(pt, ks))
    tag = hmac.new(mac_key, salt + nonce + ct, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(salt + nonce + ct + tag).decode("ascii")


def decrypt(token: str, password: bytes) -> str:
    blob = base64.urlsafe_b64decode(token.encode("ascii"))
    if len(blob) < 16 + 16 + 32:
        raise ValueError("ciphertext too short")
    salt = blob[:16]
    nonce = blob[16:32]
    ct = blob[32:-32]
    tag = blob[-32:]
    enc_key, mac_key = _derive(password, salt)
    expected = hmac.new(mac_key, salt + nonce + ct, hashlib.sha256).digest()
    if not hmac.compare_digest(expected, tag):
        raise ValueError("MAC verification failed")
    ks = _keystream(enc_key, nonce, len(ct))
    return bytes(a ^ b for a, b in zip(ct, ks)).decode("utf-8")
