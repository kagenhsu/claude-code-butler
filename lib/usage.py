"""偵測 Claude Code 使用量與方案資訊"""
from __future__ import annotations

import json
import os
import glob
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path


# Claude 方案的已知限制
PLAN_LIMITS = {
    "free": {"name": "免費方案", "context": "200K", "rate": "基礎速率"},
    "pro": {"name": "Pro 方案（$20/月）", "context": "200K", "rate": "5 倍速率"},
    "max_5x": {"name": "Max 5x 方案（$100/月）", "context": "1M", "rate": "5 倍速率"},
    "max_20x": {"name": "Max 20x 方案（$200/月）", "context": "1M", "rate": "20 倍速率"},
}

MODEL_INFO = {
    "claude-opus-4-7": {"display": "Claude Opus 4.7", "tier": "旗艦", "context": "1M tokens"},
    "claude-sonnet-4-6": {"display": "Claude Sonnet 4.6", "tier": "進階", "context": "200K tokens"},
    "claude-haiku-4-5": {"display": "Claude Haiku 4.5", "tier": "快速", "context": "200K tokens"},
}


@dataclass
class SessionInfo:
    session_id: str = ""
    started_at: str = ""
    status: str = ""
    cwd: str = ""


@dataclass
class UsageInfo:
    model_id: str = ""
    model_display: str = ""
    model_tier: str = ""
    context_window: str = ""
    plan_name: str = ""
    plan_details: str = ""
    active_sessions: int = 0
    sessions_today: int = 0
    sessions_total: int = 0
    session_list: list[SessionInfo] = field(default_factory=list)
    history_entries_today: int = 0
    detection_notes: list[str] = field(default_factory=list)


def detect_usage() -> UsageInfo:
    info = UsageInfo()
    claude_dir = Path.home() / ".claude"

    # 模型資訊
    try:
        with open(claude_dir / "settings.json") as f:
            settings = json.load(f)
        info.model_id = settings.get("model", "")
    except Exception:
        pass

    if not info.model_id:
        info.model_id = "claude-opus-4-7"

    model_meta = MODEL_INFO.get(info.model_id, {})
    info.model_display = model_meta.get("display", info.model_id)
    info.model_tier = model_meta.get("tier", "未知")
    info.context_window = model_meta.get("context", "未知")

    # 方案推測
    if "opus" in info.model_id and "1M" in info.context_window:
        info.plan_name = PLAN_LIMITS["max_20x"]["name"]
        info.plan_details = "可使用 Opus 旗艦模型 + 1M 超長上下文"
        info.detection_notes.append("依據目前使用 Opus 4.7 (1M) 推測為 Max 方案")
    elif "opus" in info.model_id:
        info.plan_name = PLAN_LIMITS["max_5x"]["name"]
        info.plan_details = "可使用 Opus 旗艦模型"
    elif "sonnet" in info.model_id:
        info.plan_name = PLAN_LIMITS["pro"]["name"]
        info.plan_details = "可使用 Sonnet 進階模型"
    else:
        info.plan_name = "未知方案"
        info.plan_details = ""

    # Session 統計
    sessions_dir = claude_dir / "sessions"
    if sessions_dir.is_dir():
        today = datetime.now().date()
        for sf in sessions_dir.glob("*.json"):
            try:
                with open(sf) as f:
                    sess = json.load(f)
                si = SessionInfo(
                    session_id=sess.get("sessionId", "")[:8],
                    started_at=sess.get("procStart", ""),
                    status=sess.get("status", "unknown"),
                    cwd=sess.get("cwd", ""),
                )
                info.session_list.append(si)
                info.sessions_total += 1

                started_ms = sess.get("startedAt", 0)
                if started_ms:
                    started_date = datetime.fromtimestamp(started_ms / 1000).date()
                    if started_date == today:
                        info.sessions_today += 1

                if sess.get("status") in ("busy", "active"):
                    info.active_sessions += 1
            except Exception:
                continue

    # 歷史對話統計
    history_file = claude_dir / "history.jsonl"
    if history_file.is_file():
        try:
            today_str = datetime.now().strftime("%Y-%m-%d")
            with open(history_file) as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        ts = entry.get("timestamp", "")
                        if isinstance(ts, str) and ts.startswith(today_str):
                            info.history_entries_today += 1
                        elif isinstance(ts, (int, float)):
                            entry_date = datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d")
                            if entry_date == today_str:
                                info.history_entries_today += 1
                    except Exception:
                        continue
        except Exception:
            pass

    if not info.detection_notes:
        info.detection_notes.append("Claude Code 訂閱制不提供精確 token 用量 API，以上為本地推測")

    return info
