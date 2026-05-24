"""每日排程任務的常駐 worker。

啟動方式跟 telegram / line bot 一樣，由 lib/bot_runner 拉起。

設計：
- 每 30 秒掃一次 task_store，把所有 enabled 且 schedule.mode 有效的 daily 任務拿出來算「下次該跑時間」
- 如果上次執行時間 < 該跑時間 ≤ 現在，就跑它
- 同時只跑一個任務（避免一堆 claude CLI 同時開），跑完才檢查下一個
- 不依賴 Streamlit，但會更新 ~/.claude/aihub_tasks.json
"""
from __future__ import annotations

import sys
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import task_runner, task_store  # noqa: E402


CHECK_INTERVAL_SEC = 30


def _log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def _parse_hhmm(s: str) -> Optional[tuple[int, int]]:
    try:
        h, m = s.split(":")
        return int(h), int(m)
    except (ValueError, AttributeError):
        return None


def _next_due(task: dict, now: datetime) -> Optional[datetime]:
    """根據 schedule 算出『最近一次該跑的時間點』（不未來）。
    回傳 None 代表這個 task 還沒到該跑的時刻。"""
    sched = task.get("schedule") or {}
    mode = sched.get("mode")
    last_run = task.get("last_run_at") or ""

    if mode == "interval":
        minutes = int(sched.get("minutes", 0) or 0)
        if minutes <= 0:
            return None
        try:
            last = datetime.fromisoformat(last_run) if last_run else None
        except ValueError:
            last = None
        threshold = now - timedelta(minutes=minutes)
        if last is None or last <= threshold:
            return now
        return None

    if mode == "daily":
        hm = _parse_hhmm(sched.get("time", ""))
        if not hm:
            return None
        h, m = hm
        due_today = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if due_today > now:
            return None
        try:
            last = datetime.fromisoformat(last_run) if last_run else None
        except ValueError:
            last = None
        if last is None or last < due_today:
            return due_today
        return None

    if mode == "weekly":
        hm = _parse_hhmm(sched.get("time", ""))
        if not hm:
            return None
        weekday = int(sched.get("weekday", 0)) % 7  # 0=Mon
        h, m = hm
        # 找「最近一次（不未來）的那個 weekday HH:MM」
        target = now.replace(hour=h, minute=m, second=0, microsecond=0)
        delta_days = (target.weekday() - weekday) % 7
        # 如果是今天但 HH:MM 還沒到，往前推 7 天
        candidate = target - timedelta(days=delta_days)
        if candidate > now:
            candidate -= timedelta(days=7)
        try:
            last = datetime.fromisoformat(last_run) if last_run else None
        except ValueError:
            last = None
        if last is None or last < candidate:
            return candidate
        return None

    return None


def tick(now: Optional[datetime] = None) -> int:
    """掃描所有 daily 任務並跑該跑的。回傳本次執行了幾個任務。"""
    now = now or datetime.now()
    ran = 0
    for task in task_store.list_tasks(kind="daily"):
        if not task.get("enabled"):
            continue
        due = _next_due(task, now)
        if due is None:
            continue
        _log(f"▶️ 觸發任務「{task['name']}」（{task_store.describe_schedule(task['schedule'])}）")
        try:
            result = task_runner.run_inline(task)
            _log(f"   → {result['status']}（{result['duration_sec']}s）log: {result['log_path']}")
            ran += 1
        except Exception as e:
            _log(f"   ❌ 例外：{e}\n{traceback.format_exc()}")
    return ran


def main() -> int:
    _log(f"✅ scheduler 啟動 — 每 {CHECK_INTERVAL_SEC}s 檢查一次")
    while True:
        try:
            tick()
        except Exception as e:
            _log(f"tick 例外：{e}\n{traceback.format_exc()}")
        time.sleep(CHECK_INTERVAL_SEC)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        _log("👋 收到 KeyboardInterrupt，退出")
