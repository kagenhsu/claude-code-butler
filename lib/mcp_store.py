"""Claude Code MCP server 設定的讀寫層。

兩個範圍：
- 全域：~/.claude.json 裡的 `mcpServers` 物件（**只動這個 key**,其他欄位原樣保留）
- 專案：<project>/.mcp.json（整個檔案就是 `{mcpServers: {...}}`,可 commit 到 repo）

每個 server 設定有兩種型別：
- stdio:  {"command": "...", "args": [...], "env": {...}}
- remote: {"url": "https://...", "type": "sse"|"http"}

讀寫時務必保留未知欄位（向前相容）。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional


def global_settings_file() -> Path:
    return Path.home() / ".claude.json"


def project_settings_file(project_dir: str) -> Path:
    return Path(os.path.expanduser(project_dir)) / ".mcp.json"


def _load(p: Path) -> dict:
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save(p: Path, data: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    # 全域檔很大,寫之前先 backup（時間戳 5 份輪替）
    if p == global_settings_file() and p.is_file():
        try:
            backup = p.with_suffix(f".json.bak.{int(time.time())}")
            shutil.copy2(p, backup)
            # 只留最新 5 份
            backups = sorted(p.parent.glob(f"{p.name}.bak.*"), reverse=True)
            for old in backups[5:]:
                old.unlink(missing_ok=True)
        except OSError:
            pass
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def is_global(settings_path: Path) -> bool:
    return settings_path.resolve() == global_settings_file().resolve()


def load_servers(settings_path: Path) -> dict:
    """回傳 {name: server_config} dict。"""
    cfg = _load(settings_path)
    if is_global(settings_path):
        return cfg.get("mcpServers") or {}
    # 專案的 .mcp.json 本身就是 {mcpServers: {...}}
    return cfg.get("mcpServers") or {}


def save_servers(settings_path: Path, servers: dict) -> None:
    """寫回。對全域只動 mcpServers,其他欄位原樣保留。"""
    cfg = _load(settings_path)
    if servers:
        cfg["mcpServers"] = servers
    elif "mcpServers" in cfg:
        cfg.pop("mcpServers")
    if not is_global(settings_path) and not cfg:
        # 專案檔留空 dict 比較好（讓 .mcp.json 仍存在但 mcpServers={}）
        cfg = {"mcpServers": {}}
    _save(settings_path, cfg)


def add_server(settings_path: Path, name: str, config: dict, *,
               overwrite: bool = False) -> None:
    name = name.strip()
    if not name:
        raise ValueError("server 名稱不能空白")
    servers = load_servers(settings_path)
    if name in servers and not overwrite:
        raise ValueError(f"已存在同名 server：{name}")
    servers[name] = _sanitize_config(config)
    save_servers(settings_path, servers)


def update_server(settings_path: Path, name: str, config: dict) -> None:
    servers = load_servers(settings_path)
    if name not in servers:
        raise ValueError(f"找不到 server：{name}")
    servers[name] = _sanitize_config(config)
    save_servers(settings_path, servers)


def rename_server(settings_path: Path, old: str, new: str) -> None:
    new = new.strip()
    if not new:
        raise ValueError("新名稱不能空白")
    servers = load_servers(settings_path)
    if old not in servers:
        raise ValueError(f"找不到 server：{old}")
    if new != old and new in servers:
        raise ValueError(f"目標名稱已存在：{new}")
    servers[new] = servers.pop(old)
    save_servers(settings_path, servers)


def delete_server(settings_path: Path, name: str) -> bool:
    servers = load_servers(settings_path)
    if name not in servers:
        return False
    servers.pop(name)
    save_servers(settings_path, servers)
    return True


def _sanitize_config(config: dict) -> dict:
    """清掉空值,確保最小有效結構。"""
    out: dict = {}
    if "command" in config and config["command"]:
        out["command"] = str(config["command"]).strip()
        args = config.get("args") or []
        if isinstance(args, list):
            out["args"] = [str(a) for a in args if str(a).strip()]
        env = config.get("env") or {}
        if isinstance(env, dict) and env:
            out["env"] = {k: str(v) for k, v in env.items() if k}
    elif "url" in config and config["url"]:
        out["url"] = str(config["url"]).strip()
        t = config.get("type") or config.get("transport") or "sse"
        if t in ("sse", "http"):
            out["type"] = t
    else:
        raise ValueError("server 設定必須包含 command 或 url")
    return out


def server_kind(config: dict) -> str:
    if config.get("command"):
        return "stdio"
    if config.get("url"):
        return "remote"
    return "unknown"


def describe_server(config: dict) -> str:
    if config.get("command"):
        args = " ".join(config.get("args") or [])
        return f"{config['command']} {args}".strip()
    if config.get("url"):
        return f"{config.get('type', 'sse')} → {config['url']}"
    return "(未知設定)"


# ── 連線測試 ─────────────────────────────────────────────
def check_command_exists(command: str) -> tuple[bool, str]:
    """檢查指令是否存在（不實際跑 server）。"""
    if not command.strip():
        return False, "command 是空的"
    bin_ = command.split()[0]
    path = shutil.which(bin_)
    if not path:
        return False, f"找不到指令：`{bin_}`（請確認已安裝、且在 PATH 中）"
    return True, path


def try_spawn_server(config: dict, *, timeout: int = 6) -> dict:
    """實際 spawn 一次 stdio server,送 MCP initialize JSON-RPC,看回應。
    僅適用 stdio 類。回傳 {"ok", "msg", "details"}。"""
    kind = server_kind(config)
    if kind == "remote":
        # remote 簡單做：HEAD 看 status
        import urllib.error
        import urllib.request
        url = config.get("url", "")
        try:
            req = urllib.request.Request(url, method="GET")
            req.add_header("User-Agent", "Claude-Code-Butler/1.0")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return {"ok": True, "msg": f"HTTP {resp.status} — endpoint 可連線", "details": ""}
        except urllib.error.HTTPError as e:
            ok = e.code in (200, 401, 403, 405)  # endpoint 存在,只是需要 auth
            return {"ok": ok, "msg": f"HTTP {e.code} {'(需要 auth)' if ok else ''}", "details": ""}
        except Exception as e:
            return {"ok": False, "msg": f"連線失敗：{e}", "details": ""}

    if kind != "stdio":
        return {"ok": False, "msg": "未知的 server 型別", "details": ""}

    exists, msg = check_command_exists(config["command"])
    if not exists:
        return {"ok": False, "msg": msg, "details": ""}

    init_payload = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "ai-hub", "version": "0.1.0"},
        },
    }) + "\n"

    env = os.environ.copy()
    env.update(config.get("env") or {})
    try:
        proc = subprocess.Popen(
            [config["command"], *(config.get("args") or [])],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
        )
    except Exception as e:
        return {"ok": False, "msg": f"啟動失敗：{e}", "details": ""}

    try:
        proc.stdin.write(init_payload)
        proc.stdin.flush()
        try:
            out, err = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, err = proc.communicate()
            # 沒回應 → 失敗
            return {
                "ok": False,
                "msg": f"連 server 超時（>{timeout}s),沒收到 initialize 回應",
                "details": (err or "")[:600],
            }
    except Exception as e:
        try:
            proc.kill()
        except Exception:
            pass
        return {"ok": False, "msg": f"溝通例外：{e}", "details": ""}

    # 解析 stdout 第一行 JSON
    for line in (out or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            if data.get("id") == 1 and "result" in data:
                info = data["result"].get("serverInfo", {})
                proto = data["result"].get("protocolVersion", "?")
                return {
                    "ok": True,
                    "msg": f"✅ 通了！server: {info.get('name', '?')} {info.get('version', '')} · proto {proto}",
                    "details": json.dumps(data, ensure_ascii=False, indent=2)[:1500],
                }
            if "error" in data:
                return {
                    "ok": False,
                    "msg": f"server 回 error：{data['error'].get('message', '?')}",
                    "details": json.dumps(data, ensure_ascii=False, indent=2)[:1500],
                }
        except json.JSONDecodeError:
            continue

    return {
        "ok": False,
        "msg": "server 啟動了但沒回符合 MCP 規格的 JSON",
        "details": ((out or "") + "\n--- stderr ---\n" + (err or ""))[:1500],
    }
