"""LINE Bot worker — 用 stdlib http.server 接 webhook，HMAC-SHA256 驗章，呼 LLM、reply。

獨立腳本：被 lib/bot_runner 以 subprocess 啟動。

啟動參數（環境變數）：
- BOT_CHANNEL_SECRET ：Channel Secret（用來驗證 webhook 簽章，必填）
- BOT_CHANNEL_TOKEN  ：Channel Access Token（用來呼 reply API，必填）
- BOT_MODEL          ：模型 ID（預設 claude-haiku-4-5-20251001）
- BOT_SYSTEM         ：system prompt
- BOT_PORT           ：監聽 port（預設 8765）
- BOT_ALLOWED_USERS  ：以逗號分隔的 userId 白名單（空 = 不限）

需要對外可達——配 Cloudflare Tunnel：
    cloudflared tunnel --url http://localhost:8765
然後把 webhook URL 設成 https://<random>.trycloudflare.com/webhook
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sys
import time
import traceback
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import llm  # noqa: E402


REPLY_URL = "https://api.line.me/v2/bot/message/reply"


def _log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def _verify_signature(secret: str, body: bytes, signature: str) -> bool:
    if not signature:
        return False
    mac = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    expected = base64.b64encode(mac).decode("utf-8")
    return hmac.compare_digest(expected, signature)


def _reply(token: str, reply_token: str, text: str) -> None:
    body = json.dumps(
        {"replyToken": reply_token, "messages": [{"type": "text", "text": text[:4900]}]}
    ).encode("utf-8")
    req = urllib.request.Request(
        REPLY_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()
    except urllib.error.HTTPError as e:
        _log(f"reply 失敗（HTTP {e.code}）：{e.read().decode('utf-8', 'ignore')[:200]}")


def make_handler(secret: str, token: str, model: str, system: str, allowed: set[str]):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            _log(f"http: {fmt % args}")

        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"AI Hub LINE bot is alive\n")

        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length) if length else b""
            sig = self.headers.get("X-Line-Signature", "")

            if not _verify_signature(secret, body, sig):
                _log(f"⛔ 簽章驗證失敗 path={self.path}")
                self.send_response(401)
                self.end_headers()
                self.wfile.write(b"bad signature")
                return

            # 先回 200 給 LINE，免得 webhook 超時被標記失敗
            self.send_response(200)
            self.end_headers()

            try:
                payload = json.loads(body.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                _log("⚠️ payload 不是 JSON")
                return

            for event in payload.get("events", []):
                try:
                    self._handle_event(event)
                except Exception as e:
                    _log(f"事件處理例外：{e}\n{traceback.format_exc()}")

        def _handle_event(self, event: dict):
            if event.get("type") != "message":
                return
            msg = event.get("message", {})
            if msg.get("type") != "text":
                return
            text = (msg.get("text") or "").strip()
            if not text:
                return
            source = event.get("source", {})
            user_id = source.get("userId", "")
            reply_token = event.get("replyToken")

            if allowed and user_id not in allowed:
                _log(f"⛔ 拒絕（不在白名單）userId={user_id}")
                if reply_token:
                    _reply(token, reply_token, "⛔ 你的 LINE userId 不在白名單，無法使用本 bot。")
                return

            _log(f"💬 {user_id[:8]}…：{text[:80]}")
            try:
                reply = llm.call_text(model, text, system=system, max_tokens=1024)
            except Exception as e:
                reply = f"❌ 模型呼叫例外：{e}"
            if not reply:
                reply = "（模型沒回任何內容）"
            if reply_token:
                _reply(token, reply_token, reply)

    return Handler


def main() -> int:
    secret = os.environ.get("BOT_CHANNEL_SECRET", "").strip()
    token = os.environ.get("BOT_CHANNEL_TOKEN", "").strip()
    if not secret or not token:
        _log("❌ BOT_CHANNEL_SECRET 或 BOT_CHANNEL_TOKEN 未設定，退出")
        return 1

    model = os.environ.get("BOT_MODEL", "claude-haiku-4-5-20251001").strip()
    system = os.environ.get("BOT_SYSTEM", "").strip()
    port = int(os.environ.get("BOT_PORT", "8765"))
    allowed_raw = os.environ.get("BOT_ALLOWED_USERS", "").strip()
    allowed = {s.strip() for s in allowed_raw.split(",") if s.strip()} if allowed_raw else set()

    handler = make_handler(secret, token, model, system, allowed)
    server = HTTPServer(("127.0.0.1", port), handler)

    _log(f"✅ 啟動 LINE Bot webhook 監聽 127.0.0.1:{port}（模型 {model}）")
    if allowed:
        _log(f"🔒 白名單模式：{sorted(allowed)}")
    else:
        _log("⚠️  未設白名單，任何能透過 tunnel 連到 webhook 的 LINE 使用者都會被回覆")
    _log("👉 別忘了開 Cloudflare Tunnel：cloudflared tunnel --url http://localhost:%d" % port)

    server.serve_forever()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        _log("👋 收到 KeyboardInterrupt，退出")
