"""Telegram Bot worker — 長輪詢 getUpdates，把訊息丟給 LLM 回覆。

獨立腳本：被 lib/bot_runner 以 subprocess 啟動，不依賴 Streamlit。

啟動參數（環境變數）：
- BOT_TOKEN  ：Telegram Bot Token（必填）
- BOT_MODEL  ：要呼叫的模型 ID（預設 claude-haiku-4-5-20251001）
- BOT_SYSTEM ：system prompt（預設空）
- BOT_ALLOWED_CHATS：以逗號分隔的 chat_id 白名單（空 = 不限）

執行：python -m bots.telegram_worker
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import llm  # noqa: E402


API = "https://api.telegram.org/bot{token}/{method}"


def _log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def _call(token: str, method: str, **params) -> dict:
    url = API.format(token=token, method=method)
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=60) as resp:
        return json.loads(resp.read())


def _send_message(token: str, chat_id: int, text: str) -> None:
    url = API.format(token=token, method="sendMessage")
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode("utf-8")
    req = urllib.request.Request(url, data=data)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp.read()
    except urllib.error.HTTPError as e:
        _log(f"sendMessage 失敗（HTTP {e.code}）：{e.read().decode('utf-8', 'ignore')[:200]}")


def main() -> int:
    token = os.environ.get("BOT_TOKEN", "").strip()
    if not token:
        _log("❌ BOT_TOKEN 未設定，退出")
        return 1

    model = os.environ.get("BOT_MODEL", "claude-haiku-4-5-20251001").strip()
    system = os.environ.get("BOT_SYSTEM", "").strip()
    allowed_raw = os.environ.get("BOT_ALLOWED_CHATS", "").strip()
    allowed: set[int] = set()
    if allowed_raw:
        for s in allowed_raw.split(","):
            s = s.strip()
            if s:
                try:
                    allowed.add(int(s))
                except ValueError:
                    pass

    try:
        me = _call(token, "getMe")
    except Exception as e:
        _log(f"❌ getMe 失敗，Token 應該是錯的：{e}")
        return 1
    if not me.get("ok"):
        _log(f"❌ getMe 回傳 ok=false：{me}")
        return 1
    _log(f"✅ 啟動 Telegram Bot：@{me['result'].get('username')}（模型 {model}）")
    if allowed:
        _log(f"🔒 白名單模式：{sorted(allowed)}")
    else:
        _log("⚠️  未設白名單，任何人傳訊都會被回覆")

    offset = 0
    while True:
        try:
            res = _call(token, "getUpdates", offset=offset, timeout=30)
        except urllib.error.URLError as e:
            _log(f"網路錯誤（會重試）：{e}")
            time.sleep(3)
            continue
        except Exception as e:
            _log(f"getUpdates 例外：{e}\n{traceback.format_exc()}")
            time.sleep(3)
            continue

        if not res.get("ok"):
            _log(f"getUpdates 回傳 ok=false：{res}")
            time.sleep(3)
            continue

        for upd in res.get("result", []):
            offset = max(offset, upd["update_id"] + 1)
            msg = upd.get("message") or upd.get("edited_message")
            if not msg:
                continue
            chat = msg.get("chat", {})
            chat_id = chat.get("id")
            text = (msg.get("text") or "").strip()
            if not text:
                continue
            if allowed and chat_id not in allowed:
                _log(f"⛔ 拒絕（不在白名單）chat_id={chat_id}")
                _send_message(token, chat_id, "⛔ 你的 chat_id 不在白名單，無法使用本 bot。")
                continue

            sender = chat.get("username") or chat.get("first_name") or str(chat_id)
            _log(f"💬 {sender}（{chat_id}）：{text[:80]}")

            try:
                reply = llm.call_text(model, text, system=system, max_tokens=1024)
            except Exception as e:
                reply = f"❌ 模型呼叫例外：{e}"
            if not reply:
                reply = "（模型沒回任何內容）"
            _send_message(token, chat_id, reply[:4000])


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        _log("👋 收到 KeyboardInterrupt，退出")
