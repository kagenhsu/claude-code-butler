"""自動化任務的儲存層。

兩種任務：
- daily   ：排程任務（時間到自動跑）
- project ：綁某個專案資料夾的任務（手動觸發，不自動）

任務存在 ~/.claude/aihub_tasks.json：
{
  "tasks": [
    {
      "id": "...",                  # uuid4
      "name": "顯示名稱",
      "kind": "daily" | "project",
      "prompt": "餵給 claude -p 的內容",
      "cwd": "/path/to/project",     # project 必填、daily 可空 → 用 home
      "enabled": true,
      "schedule": {                   # 只有 daily 用
          "mode": "daily" | "weekly" | "interval",
          "time": "09:00",            # daily / weekly
          "weekday": 0,               # weekly: 0=週一 .. 6=週日
          "minutes": 30,              # interval
      },
      "created_at": "2026-05-24T...",
      "last_run_at": "...",
      "last_status": "success" | "fail" | "running" | "",
      "last_duration_sec": 12,
    }
  ],
  "history": [                        # 最近 N 筆執行紀錄
    {"task_id": "...", "name": "...", "started_at": "...", "ended_at": "...", "status": "...", "log_path": "..."}
  ]
}
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .paths import claude_dir


HISTORY_LIMIT = 200


def store_file() -> Path:
    return claude_dir() / "aihub_tasks.json"


def tasks_dir() -> Path:
    """每個任務的 log 目錄：~/.claude/aihub_tasks/<task_id>/"""
    p = claude_dir() / "aihub_tasks"
    p.mkdir(parents=True, exist_ok=True)
    return p


def task_log_dir(task_id: str) -> Path:
    p = tasks_dir() / task_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def _load() -> dict:
    f = store_file()
    if not f.is_file():
        return {"tasks": [], "history": []}
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"tasks": [], "history": []}
    data.setdefault("tasks", [])
    data.setdefault("history", [])
    return data


def _save(data: dict) -> None:
    claude_dir().mkdir(parents=True, exist_ok=True)
    store_file().write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def list_tasks(kind: Optional[str] = None) -> list[dict]:
    tasks = _load()["tasks"]
    if kind:
        return [t for t in tasks if t.get("kind") == kind]
    return tasks


def get_task(task_id: str) -> Optional[dict]:
    for t in _load()["tasks"]:
        if t.get("id") == task_id:
            return t
    return None


def create_task(*, name: str, kind: str, prompt: str, cwd: str = "",
                schedule: Optional[dict] = None, enabled: bool = True) -> dict:
    if kind not in {"daily", "project"}:
        raise ValueError(f"unknown kind: {kind}")
    data = _load()
    task = {
        "id": uuid.uuid4().hex[:12],
        "name": name.strip() or "(未命名任務)",
        "kind": kind,
        "prompt": prompt,
        "cwd": cwd,
        "enabled": enabled,
        "schedule": schedule or {},
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "last_run_at": "",
        "last_status": "",
        "last_duration_sec": 0,
    }
    data["tasks"].append(task)
    _save(data)
    return task


def update_task(task_id: str, **fields: Any) -> Optional[dict]:
    data = _load()
    for t in data["tasks"]:
        if t.get("id") == task_id:
            t.update({k: v for k, v in fields.items() if k != "id"})
            _save(data)
            return t
    return None


def delete_task(task_id: str) -> bool:
    data = _load()
    before = len(data["tasks"])
    data["tasks"] = [t for t in data["tasks"] if t.get("id") != task_id]
    if len(data["tasks"]) == before:
        return False
    data["history"] = [h for h in data["history"] if h.get("task_id") != task_id]
    _save(data)
    return True


def set_enabled(task_id: str, enabled: bool) -> Optional[dict]:
    return update_task(task_id, enabled=enabled)


def record_run(task_id: str, *, status: str, started_at: str, ended_at: str,
               duration_sec: int, log_path: str) -> None:
    data = _load()
    task_name = ""
    for t in data["tasks"]:
        if t.get("id") == task_id:
            task_name = t.get("name", "")
            t["last_run_at"] = ended_at
            t["last_status"] = status
            t["last_duration_sec"] = duration_sec
            break
    entry = {
        "task_id": task_id,
        "name": task_name,
        "started_at": started_at,
        "ended_at": ended_at,
        "status": status,
        "duration_sec": duration_sec,
        "log_path": log_path,
    }
    data["history"].insert(0, entry)
    data["history"] = data["history"][:HISTORY_LIMIT]
    _save(data)


def mark_running(task_id: str) -> None:
    update_task(task_id, last_status="running")


def list_history(*, task_id: Optional[str] = None, limit: int = 50) -> list[dict]:
    hist = _load()["history"]
    if task_id:
        hist = [h for h in hist if h.get("task_id") == task_id]
    return hist[:limit]


def clear_history() -> None:
    data = _load()
    data["history"] = []
    _save(data)


def describe_schedule(schedule: dict) -> str:
    """把 schedule dict 轉成人讀字串。"""
    if not schedule:
        return "（無排程）"
    mode = schedule.get("mode", "")
    if mode == "daily":
        return f"每天 {schedule.get('time', '00:00')}"
    if mode == "weekly":
        names = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
        wd = schedule.get("weekday", 0)
        return f"{names[wd % 7]} {schedule.get('time', '00:00')}"
    if mode == "interval":
        return f"每 {schedule.get('minutes', 0)} 分鐘"
    return f"（未知模式 {mode}）"
