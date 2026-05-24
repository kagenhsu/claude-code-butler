"""任務執行器 — 把任務丟去 claude CLI，輸出寫進 log 並更新狀態。

兩種使用方式：
- run_inline(task) — 同步跑、阻塞直到完成（給 scheduler 用）
- spawn(task)      — 背景 subprocess 跑、立刻回傳 PID（給 UI「立即執行」按鈕用）

每次執行的 log 都單獨存一份：
    ~/.claude/aihub_tasks/<task_id>/<timestamp>.log
另外維護一個 `last.log` symlink/檔案，方便 UI 抓最新一份。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from . import task_store


def _claude_bin() -> Optional[str]:
    return shutil.which("claude")


def _log_path(task_id: str, ts: str) -> Path:
    return task_store.task_log_dir(task_id) / f"{ts}.log"


def _update_last_log(task_id: str, log_file: Path) -> None:
    last = task_store.task_log_dir(task_id) / "last.log"
    try:
        if last.exists() or last.is_symlink():
            last.unlink()
        last.symlink_to(log_file.name)
    except OSError:
        try:
            last.write_bytes(log_file.read_bytes())
        except OSError:
            pass


def _resolve_cwd(task: dict) -> str:
    cwd = task.get("cwd", "").strip()
    if cwd:
        p = Path(os.path.expanduser(cwd))
        if p.is_dir():
            return str(p)
    return str(Path.home())


def run_inline(task: dict, *, timeout_sec: int = 1800) -> dict:
    """同步跑一個任務。回傳 {"status", "duration_sec", "log_path"}。"""
    claude = _claude_bin()
    started_at = datetime.now().isoformat(timespec="seconds")
    ts_for_file = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_file = _log_path(task["id"], ts_for_file)

    if not claude:
        log_file.write_text(
            "❌ 找不到 `claude` 指令 — 請先安裝 Claude Code CLI（"
            "https://docs.anthropic.com/en/docs/claude-code）\n",
            encoding="utf-8",
        )
        ended_at = datetime.now().isoformat(timespec="seconds")
        task_store.record_run(
            task["id"], status="fail", started_at=started_at, ended_at=ended_at,
            duration_sec=0, log_path=str(log_file),
        )
        _update_last_log(task["id"], log_file)
        return {"status": "fail", "duration_sec": 0, "log_path": str(log_file)}

    task_store.mark_running(task["id"])

    cwd = _resolve_cwd(task)
    prompt = task.get("prompt", "")
    header = (
        f"=== 任務: {task.get('name')} ===\n"
        f"開始時間: {started_at}\n"
        f"工作目錄: {cwd}\n"
        f"指令: claude -p <prompt>\n"
        f"--- prompt ---\n{prompt}\n"
        f"--- 輸出 ---\n"
    )
    log_file.write_text(header, encoding="utf-8")

    t0 = time.time()
    status = "success"
    try:
        with open(log_file, "ab") as fh:
            proc = subprocess.Popen(
                [claude, "-p", prompt],
                cwd=cwd,
                stdout=fh,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                env=os.environ.copy(),
            )
            try:
                rc = proc.wait(timeout=timeout_sec)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                status = "fail"
                fh.write(f"\n\n⏱️ 超時（>{timeout_sec}s）已強制終止\n".encode("utf-8"))
                rc = -1
        if rc != 0 and status == "success":
            status = "fail"
            with open(log_file, "ab") as fh:
                fh.write(f"\n\n❌ 結束碼 {rc}（非 0）\n".encode("utf-8"))
    except Exception as e:
        status = "fail"
        with open(log_file, "ab") as fh:
            fh.write(f"\n\n❌ 執行例外：{e!r}\n".encode("utf-8"))

    duration = int(time.time() - t0)
    ended_at = datetime.now().isoformat(timespec="seconds")
    with open(log_file, "ab") as fh:
        fh.write(f"\n=== 結束 {ended_at}（狀態 {status}，{duration}s）===\n".encode("utf-8"))

    _update_last_log(task["id"], log_file)
    task_store.record_run(
        task["id"], status=status, started_at=started_at, ended_at=ended_at,
        duration_sec=duration, log_path=str(log_file),
    )
    return {"status": status, "duration_sec": duration, "log_path": str(log_file)}


def spawn(task: dict) -> dict:
    """背景跑一個任務，立刻回傳。內部用 python -m lib.task_runner_cli 包一層 run_inline。"""
    claude_dir = task_store.tasks_dir().parent  # ~/.claude
    pid_file = claude_dir / "bots" / f"task_{task['id']}.pid"
    pid_file.parent.mkdir(parents=True, exist_ok=True)

    if pid_file.is_file():
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, 0)
            return {"ok": False, "pid": pid, "msg": f"這個任務還在跑（PID {pid}）"}
        except (ValueError, ProcessLookupError, OSError):
            pid_file.unlink(missing_ok=True)

    cmd = [sys.executable, "-m", "lib.task_runner_cli", task["id"]]
    log_file = task_store.task_log_dir(task["id"]) / "spawn.out"
    with open(log_file, "ab") as fh:
        proc = subprocess.Popen(
            cmd,
            stdout=fh,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            cwd=str(Path(__file__).resolve().parent.parent),
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
    pid_file.write_text(str(proc.pid))
    return {"ok": True, "pid": proc.pid, "msg": f"已背景啟動（PID {proc.pid}）"}


def is_running(task_id: str) -> bool:
    pid_file = task_store.tasks_dir().parent / "bots" / f"task_{task_id}.pid"
    if not pid_file.is_file():
        return False
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)
        return True
    except (ValueError, ProcessLookupError, OSError):
        pid_file.unlink(missing_ok=True)
        return False


def read_log(log_path: str, tail_lines: int = 200) -> str:
    p = Path(log_path)
    if not p.is_file():
        return ""
    try:
        with open(p, "rb") as f:
            try:
                f.seek(-200_000, 2)
            except OSError:
                f.seek(0)
            data = f.read().decode("utf-8", errors="replace")
    except OSError as e:
        return f"(讀 log 失敗：{e})"
    lines = data.splitlines()
    return "\n".join(lines[-tail_lines:])


def last_log_path(task_id: str) -> Optional[str]:
    last = task_store.task_log_dir(task_id) / "last.log"
    if last.exists():
        if last.is_symlink():
            return str(last.resolve())
        return str(last)
    candidates = sorted(task_store.task_log_dir(task_id).glob("*.log"))
    return str(candidates[-1]) if candidates else None
