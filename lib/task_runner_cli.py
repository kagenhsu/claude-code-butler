"""背景執行任務的入口：python -m lib.task_runner_cli <task_id>

跟 `task_runner.run_inline` 唯一差別是它會在結束時刪掉 PID 檔，
這樣 UI 上的「執行中」狀態就會自動消失。
"""
from __future__ import annotations

import sys
from pathlib import Path

from . import task_runner, task_store


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: python -m lib.task_runner_cli <task_id>", file=sys.stderr)
        return 2
    task_id = argv[1]
    task = task_store.get_task(task_id)
    if not task:
        print(f"❌ 找不到任務 id={task_id}", file=sys.stderr)
        return 2

    try:
        task_runner.run_inline(task)
    finally:
        pid_file = task_store.tasks_dir().parent / "bots" / f"task_{task_id}.pid"
        try:
            pid_file.unlink(missing_ok=True)
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
