"""Claude Code Hooks 設定的讀寫層。

Hooks 存在 settings.json：
- 全域：~/.claude/settings.json
- 專案：<project>/.claude/settings.json（或 .claude/settings.local.json）

結構：
{
  "hooks": {
    "PreToolUse":      [{"matcher": "Bash", "hooks": [{"type": "command", "command": "..."}]}],
    "PostToolUse":     [...],
    "UserPromptSubmit":[...],
    "Stop":            [...],
    "SubagentStop":    [...],
    "Notification":    [...],
    "SessionStart":    [...],
    "PreCompact":      [...]
  }
}

讀寫時只動 "hooks" 這個 key，其他欄位（env / permissions / model / theme）原樣保留。
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import uuid
from pathlib import Path
from typing import Optional

from .paths import claude_dir


# 所有 Claude Code 支援的事件名稱
EVENTS: list[str] = [
    "PreToolUse",
    "PostToolUse",
    "UserPromptSubmit",
    "Stop",
    "SubagentStop",
    "Notification",
    "SessionStart",
    "PreCompact",
]


EVENT_DESC: dict[str, str] = {
    "PreToolUse": "Claude 即將呼叫某個工具前。可用 exit code 2 阻止這次呼叫（搭配 matcher 過濾工具名）",
    "PostToolUse": "工具呼叫結束後。常用來自動 format、跑 lint、記錄稽核",
    "UserPromptSubmit": "使用者送出 prompt 時。stdout 會被注入到 Claude 看到的內容（可加額外 context）",
    "Stop": "Assistant 結束一個回合時。常用於桌面通知、寫日誌",
    "SubagentStop": "子 agent 結束時。可用來統計每個子任務花了多少時間",
    "Notification": "Claude Code 對外推送通知時（例如等待輸入）",
    "SessionStart": "新 session 啟動時。可印歡迎訊息、跑 git status、檢查環境",
    "PreCompact": "Context 被自動壓縮之前。可用來備份對話",
}


# 哪些事件吃 matcher（工具名稱）
MATCHER_EVENTS = {"PreToolUse", "PostToolUse"}


def global_settings_file() -> Path:
    return claude_dir() / "settings.json"


def project_settings_file(project_dir: str) -> Path:
    return Path(os.path.expanduser(project_dir)) / ".claude" / "settings.json"


def _load(p: Path) -> dict:
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save(p: Path, data: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_hooks(settings_path: Path) -> dict:
    """回傳 {event_name: [matcher_group, ...]}（沒設定的事件不會出現）"""
    cfg = _load(settings_path)
    return cfg.get("hooks", {}) or {}


def save_hooks(settings_path: Path, hooks: dict) -> None:
    cfg = _load(settings_path)
    if hooks:
        cfg["hooks"] = hooks
    else:
        cfg.pop("hooks", None)
    _save(settings_path, cfg)


def list_flat_entries(settings_path: Path) -> list[dict]:
    """把 hooks 攤平成 [{event, matcher, command, group_idx, hook_idx}, ...]
    方便 UI 一條條列出來。"""
    hooks = load_hooks(settings_path)
    flat = []
    for event in EVENTS:
        groups = hooks.get(event, []) or []
        for gi, group in enumerate(groups):
            matcher = group.get("matcher", "") if isinstance(group, dict) else ""
            for hi, h in enumerate(group.get("hooks", []) if isinstance(group, dict) else []):
                if not isinstance(h, dict):
                    continue
                flat.append({
                    "event": event,
                    "matcher": matcher,
                    "type": h.get("type", "command"),
                    "command": h.get("command", ""),
                    "timeout": h.get("timeout"),
                    "group_idx": gi,
                    "hook_idx": hi,
                    "uid": f"{event}-{gi}-{hi}-{uuid.uuid4().hex[:6]}",
                })
    return flat


def add_hook(settings_path: Path, *, event: str, matcher: str, command: str,
             timeout: Optional[int] = None) -> None:
    if event not in EVENTS:
        raise ValueError(f"unknown event: {event}")
    hooks = load_hooks(settings_path)
    groups = hooks.setdefault(event, [])
    # 找有沒有現成的 matcher group 可以塞進去
    target = None
    for g in groups:
        if isinstance(g, dict) and g.get("matcher", "") == matcher:
            target = g
            break
    if target is None:
        target = {"matcher": matcher, "hooks": []}
        groups.append(target)
    h = {"type": "command", "command": command}
    if timeout is not None and timeout > 0:
        h["timeout"] = int(timeout)
    target["hooks"].append(h)
    save_hooks(settings_path, hooks)


def update_hook(settings_path: Path, *, event: str, group_idx: int, hook_idx: int,
                matcher: str, command: str, timeout: Optional[int] = None) -> None:
    hooks = load_hooks(settings_path)
    groups = hooks.get(event, [])
    if not (0 <= group_idx < len(groups)):
        raise ValueError("group_idx out of range")
    grp = groups[group_idx]
    if not (0 <= hook_idx < len(grp.get("hooks", []))):
        raise ValueError("hook_idx out of range")
    # 如果 matcher 變了，移到正確 group
    if matcher != grp.get("matcher", ""):
        h = grp["hooks"].pop(hook_idx)
        if not grp["hooks"]:
            groups.pop(group_idx)
        target = None
        for g in groups:
            if isinstance(g, dict) and g.get("matcher", "") == matcher:
                target = g
                break
        if target is None:
            target = {"matcher": matcher, "hooks": []}
            groups.append(target)
        h["command"] = command
        if timeout is not None and timeout > 0:
            h["timeout"] = int(timeout)
        else:
            h.pop("timeout", None)
        target["hooks"].append(h)
    else:
        grp["hooks"][hook_idx]["command"] = command
        if timeout is not None and timeout > 0:
            grp["hooks"][hook_idx]["timeout"] = int(timeout)
        else:
            grp["hooks"][hook_idx].pop("timeout", None)
    save_hooks(settings_path, hooks)


def delete_hook(settings_path: Path, *, event: str, group_idx: int, hook_idx: int) -> None:
    hooks = load_hooks(settings_path)
    groups = hooks.get(event, [])
    if not (0 <= group_idx < len(groups)):
        return
    grp = groups[group_idx]
    if 0 <= hook_idx < len(grp.get("hooks", [])):
        grp["hooks"].pop(hook_idx)
    if not grp.get("hooks"):
        groups.pop(group_idx)
    if not groups:
        hooks.pop(event, None)
    save_hooks(settings_path, hooks)


def validate_command(command: str) -> tuple[bool, str]:
    """簡易 syntax check — 用 bash -n 看有沒有語法錯。回 (ok, msg)。"""
    if not command.strip():
        return False, "指令是空的"
    try:
        r = subprocess.run(
            ["bash", "-n", "-c", command],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except FileNotFoundError:
        return False, "找不到 bash"
    except subprocess.TimeoutExpired:
        return False, "syntax check 超時"
    if r.returncode == 0:
        return True, "✓ bash syntax OK"
    return False, (r.stderr.strip() or "syntax error")[:300]


def dry_run(command: str, *, cwd: Optional[str] = None, timeout: int = 8) -> dict:
    """真的把指令跑一次（不傳 hook stdin），看 exit code 與輸出。給「測試 hook」按鈕用。
    回 {"rc", "stdout", "stderr", "duration_ms"}。"""
    import time
    t0 = time.time()
    try:
        r = subprocess.run(
            ["bash", "-c", command],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.path.expanduser(cwd) if cwd else None,
        )
        ms = int((time.time() - t0) * 1000)
        return {
            "rc": r.returncode,
            "stdout": r.stdout[-2000:],
            "stderr": r.stderr[-2000:],
            "duration_ms": ms,
        }
    except subprocess.TimeoutExpired:
        return {"rc": -1, "stdout": "", "stderr": f"超時（>{timeout}s）", "duration_ms": timeout * 1000}
    except Exception as e:
        return {"rc": -2, "stdout": "", "stderr": f"執行例外：{e!r}", "duration_ms": 0}


# ── 範本 ──────────────────────────────────────────────────
TEMPLATES: list[dict] = [
    {
        "id": "notify-on-stop",
        "name": "🔔 任務完成時跳 macOS 通知",
        "desc": "每次 assistant 結束一回合，桌面右上角彈個通知（適合長任務）",
        "event": "Stop",
        "matcher": "",
        "command": (
            "osascript -e 'display notification \"Claude 完成回合\" "
            "with title \"Claude Code\" sound name \"Glass\"'"
        ),
    },
    {
        "id": "log-bash",
        "name": "📜 稽核：記錄每一條 Bash 指令",
        "desc": "PreToolUse + matcher=Bash，把要跑的指令寫進 ~/.claude/bash_audit.log",
        "event": "PreToolUse",
        "matcher": "Bash",
        "command": (
            "jq -r '\"[\\(now|todateiso8601)] \\(.cwd // \"?\") $ \\(.tool_input.command)\"' "
            ">> ~/.claude/bash_audit.log"
        ),
    },
    {
        "id": "block-rm-rf",
        "name": "🛡️ 攔截危險的 rm -rf",
        "desc": "PreToolUse + matcher=Bash，發現 `rm -rf` 直接擋掉並回報原因",
        "event": "PreToolUse",
        "matcher": "Bash",
        "command": (
            "cmd=$(jq -r .tool_input.command); "
            "if echo \"$cmd\" | grep -Eq 'rm[[:space:]]+(-[rRf]+[[:space:]]+)*-?[rR]?[fF]?[[:space:]]*/'; "
            "then echo '攔截：偵測到看起來會刪根目錄附近的 rm 指令' >&2; exit 2; fi"
        ),
    },
    {
        "id": "auto-format-py",
        "name": "🎨 寫完 Python 檔自動跑 ruff format",
        "desc": "PostToolUse + matcher=Write|Edit，如果改的是 .py 就跑 `ruff format`（需要先 `pip install ruff`）",
        "event": "PostToolUse",
        "matcher": "Write|Edit|MultiEdit",
        "command": (
            "f=$(jq -r .tool_input.file_path); "
            "if [ -n \"$f\" ] && [ \"${f##*.}\" = py ] && command -v ruff >/dev/null; "
            "then ruff format \"$f\" >/dev/null 2>&1 || true; fi"
        ),
    },
    {
        "id": "session-git-status",
        "name": "🌿 Session 啟動印 git status",
        "desc": "SessionStart — 進入專案時自動印一次 git status，讓你知道從哪裡接手",
        "event": "SessionStart",
        "matcher": "",
        "command": (
            "if [ -n \"$CLAUDE_PROJECT_DIR\" ] && [ -d \"$CLAUDE_PROJECT_DIR/.git\" ]; "
            "then echo '=== git status ==='; git -C \"$CLAUDE_PROJECT_DIR\" status -sb; fi"
        ),
    },
    {
        "id": "block-env-edit",
        "name": "🔐 禁止改 .env 與密鑰檔",
        "desc": "PreToolUse + matcher=Write|Edit，發現要改的是 .env / *.pem / *.key 就擋掉",
        "event": "PreToolUse",
        "matcher": "Write|Edit|MultiEdit",
        "command": (
            "f=$(jq -r .tool_input.file_path); "
            "case \"$f\" in *.env|*/.env|*.env.*|*.pem|*.key|*/secrets/*) "
            "echo \"攔截：禁止直接修改密鑰類檔案：$f\" >&2; exit 2;; esac"
        ),
    },
]


def template_by_id(tid: str) -> Optional[dict]:
    for t in TEMPLATES:
        if t["id"] == tid:
            return t
    return None


def find_candidate_projects() -> list[Path]:
    """找一些常見位置裡『有 .git 的資料夾』，給專案下拉選單當候選。"""
    home = Path.home()
    roots = [
        home / "ai-hub",
        home / "work",
        home / "code",
        home / "projects",
        home / "Documents" / "projects",
        home / "Documents" / "code",
        home / "Desktop",
    ]
    found: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        try:
            for child in sorted(root.iterdir()):
                if child.is_dir() and (child / ".git").exists():
                    found.append(child)
                if len(found) >= 40:
                    return found
        except OSError:
            continue
    return found
