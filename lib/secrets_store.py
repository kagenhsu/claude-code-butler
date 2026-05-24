"""加密 API Key 儲存層。

設計重點：
- 主密鑰：自動產生 32 bytes 隨機 bytes，存在 ~/.claude/.aihub_secret（權限 0600）
- 儲存：API Key 加密後寫入 config.json 的 `encrypted_api_keys` 欄位
- 向下相容：仍能讀取舊版的 `api_keys` / `providers[*].api_key` 明文格式
- 寫入時：明文殘留會被清空（避免兩種格式並存）
- 跨機器：主密鑰是「本機綁定」的——把 config.json 移到別台機器後 Key 需要重設
"""
from __future__ import annotations

import json
import os
import secrets as _secrets
import stat
from pathlib import Path

from . import crypto
from .paths import claude_dir, config_file, crypto_key_file


PROVIDER_ENV_VARS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GOOGLE_API_KEY",
    "minimax": "MINIMAX_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "xai": "XAI_API_KEY",
    "mistral": "MISTRAL_API_KEY",
}


def _get_master_key() -> bytes:
    kf = crypto_key_file()
    if kf.is_file():
        try:
            data = kf.read_bytes()
            if len(data) >= 32:
                return data
        except Exception:
            pass
    claude_dir().mkdir(parents=True, exist_ok=True)
    key = _secrets.token_bytes(32)
    kf.write_bytes(key)
    try:
        os.chmod(kf, stat.S_IRUSR | stat.S_IWUSR)  # 0600
    except Exception:
        pass
    return key


def load_config() -> dict:
    cf = config_file()
    if not cf.is_file():
        return {}
    try:
        return json.loads(cf.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_config(cfg: dict) -> None:
    config_file().write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def get_api_key(provider_id: str, *, include_env: bool = True) -> str:
    """讀取 API Key（自動解密、向下相容明文、可 fallback 到環境變數）"""
    cfg = load_config()

    enc = cfg.get("encrypted_api_keys", {}).get(provider_id)
    if enc:
        try:
            return crypto.decrypt(enc, _get_master_key())
        except Exception:
            pass

    p = cfg.get("providers", {}).get(provider_id, {})
    if p.get("api_key"):
        return p["api_key"]

    legacy = cfg.get("api_keys", {}).get(provider_id, "")
    if legacy:
        return legacy

    if include_env:
        ev = PROVIDER_ENV_VARS.get(provider_id)
        if ev:
            v = os.environ.get(ev, "")
            if v:
                return v
            if provider_id == "gemini":
                return os.environ.get("GEMINI_API_KEY", "")

    return ""


def set_api_key(provider_id: str, key: str) -> None:
    """加密儲存 API Key，並清掉舊版明文殘留。"""
    cfg = load_config()

    enc_keys = cfg.setdefault("encrypted_api_keys", {})
    enc_keys[provider_id] = crypto.encrypt(key, _get_master_key())

    if "api_keys" in cfg:
        cfg["api_keys"].pop(provider_id, None)

    providers = cfg.setdefault("providers", {})
    pdata = providers.setdefault(provider_id, {})
    pdata.pop("api_key", None)
    if pdata.get("mode") != "subscription":
        pdata["mode"] = "api_key"

    save_config(cfg)


def delete_api_key(provider_id: str) -> None:
    cfg = load_config()
    cfg.get("encrypted_api_keys", {}).pop(provider_id, None)
    cfg.get("api_keys", {}).pop(provider_id, None)
    p = cfg.get("providers", {}).get(provider_id)
    if p:
        p.pop("api_key", None)
        if p.get("mode") == "api_key" and not p.get("api_key"):
            cfg["providers"].pop(provider_id, None)
    save_config(cfg)


def list_stored_providers() -> list[str]:
    cfg = load_config()
    ids: set[str] = set()
    ids.update(cfg.get("encrypted_api_keys", {}).keys())
    ids.update(cfg.get("api_keys", {}).keys())
    for pid, pdata in cfg.get("providers", {}).items():
        if pdata.get("api_key"):
            ids.add(pid)
    return sorted(ids)


def is_encrypted(provider_id: str) -> bool:
    return provider_id in load_config().get("encrypted_api_keys", {})


def has_plaintext_leftovers() -> list[str]:
    """回傳仍以明文儲存的 provider 列表（給遷移按鈕用）"""
    cfg = load_config()
    leftovers: set[str] = set()
    leftovers.update(pid for pid, v in cfg.get("api_keys", {}).items() if v)
    for pid, pdata in cfg.get("providers", {}).items():
        if pdata.get("api_key"):
            leftovers.add(pid)
    return sorted(leftovers)


def migrate_plaintext_keys() -> int:
    """把所有明文 Key 改成加密儲存。回傳遷移數量。"""
    cfg = load_config()
    plaintext: dict[str, str] = {}

    for pid, k in cfg.get("api_keys", {}).items():
        if k:
            plaintext[pid] = k
    for pid, pdata in cfg.get("providers", {}).items():
        if pdata.get("api_key"):
            plaintext.setdefault(pid, pdata["api_key"])

    if not plaintext:
        return 0

    enc_keys = cfg.setdefault("encrypted_api_keys", {})
    master = _get_master_key()
    migrated = 0
    for pid, k in plaintext.items():
        if pid not in enc_keys:
            enc_keys[pid] = crypto.encrypt(k, master)
            migrated += 1

    if "api_keys" in cfg:
        cfg["api_keys"] = {pid: "" for pid in cfg["api_keys"]}
        cfg["api_keys"] = {}
    for pid in list(cfg.get("providers", {}).keys()):
        cfg["providers"][pid].pop("api_key", None)

    save_config(cfg)
    return migrated


def mask_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 8:
        return "****"
    return key[:4] + "…" + key[-4:]
