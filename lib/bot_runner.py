"""通訊軟體 Bot 的 subprocess 管理層。

- start(name, cmd, env)：背景啟動子進程，PID 與 log 存 ~/.claude/bots/
- stop(name)：用 PID 殺掉子進程（先 SIGTERM、必要時 SIGKILL）
- status(name)：回傳 {"running": bool, "pid": int|None, "log_path": str}
- tail_log(name, n)：抓最後 n 行 log（給 UI 顯示）

設計重點：
- 完全脫離 Streamlit 程序——Streamlit 重啟不影響 bot
- PID 檔自動清理 stale entries（如果 PID 不存在了）
- 不裝 launchd / systemd，使用者自己負責「我什麼時候要跑」
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from .paths import claude_dir


def bots_dir() -> Path:
    p = claude_dir() / "bots"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _pid_file(name: str) -> Path:
    return bots_dir() / f"{name}.pid"


def log_file(name: str) -> Path:
    return bots_dir() / f"{name}.log"


def _is_pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _read_pid(name: str) -> int | None:
    pf = _pid_file(name)
    if not pf.is_file():
        return None
    try:
        pid = int(pf.read_text().strip())
    except (ValueError, OSError):
        return None
    if not _is_pid_alive(pid):
        pf.unlink(missing_ok=True)
        return None
    return pid


def status(name: str) -> dict:
    pid = _read_pid(name)
    return {
        "running": pid is not None,
        "pid": pid,
        "log_path": str(log_file(name)),
    }


def start(name: str, cmd: list[str], env: dict[str, str] | None = None) -> dict:
    """背景啟動 bot。回傳 {"ok": bool, "pid": int|None, "msg": str}。"""
    cur = _read_pid(name)
    if cur is not None:
        return {"ok": False, "pid": cur, "msg": f"已經在執行中（PID {cur}）"}

    log = log_file(name)
    log.touch(exist_ok=True)

    full_env = os.environ.copy()
    if env:
        full_env.update(env)

    log_fh = open(log, "ab", buffering=0)
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            env=full_env,
            start_new_session=True,
            cwd=str(Path(__file__).resolve().parent.parent),
        )
    except FileNotFoundError as e:
        log_fh.close()
        return {"ok": False, "pid": None, "msg": f"啟動失敗：{e}"}

    time.sleep(0.4)
    if proc.poll() is not None:
        return {
            "ok": False,
            "pid": None,
            "msg": f"啟動後立即結束（exit code {proc.returncode}）— 看 log 找原因",
        }

    _pid_file(name).write_text(str(proc.pid))
    return {"ok": True, "pid": proc.pid, "msg": f"已啟動（PID {proc.pid}）"}


def stop(name: str) -> dict:
    pid = _read_pid(name)
    if pid is None:
        return {"ok": True, "msg": "本來就沒在跑"}

    try:
        os.killpg(os.getpgid(pid), signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        _pid_file(name).unlink(missing_ok=True)
        return {"ok": True, "msg": "進程已不存在，PID 檔清掉了"}

    for _ in range(20):
        time.sleep(0.1)
        if not _is_pid_alive(pid):
            break

    if _is_pid_alive(pid):
        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass

    _pid_file(name).unlink(missing_ok=True)
    return {"ok": True, "msg": f"已停止（原 PID {pid}）"}


def tail_log(name: str, n: int = 40) -> str:
    lf = log_file(name)
    if not lf.is_file():
        return ""
    try:
        with open(lf, "rb") as f:
            try:
                f.seek(-65536, 2)
            except OSError:
                f.seek(0)
            data = f.read().decode("utf-8", errors="replace")
    except OSError as e:
        return f"(無法讀取 log：{e})"
    lines = data.splitlines()
    return "\n".join(lines[-n:])


def clear_log(name: str) -> None:
    log_file(name).write_text("")


def python_executable() -> str:
    return sys.executable
