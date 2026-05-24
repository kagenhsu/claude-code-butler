"""共用 LLM 分派器：給對話沙盒、bot worker 都能呼叫。

設計重點：
- 純文字進、純文字出（簡單版，不處理圖片附件）
- 自動從 secrets_store 讀取 API Key
- 自動 fallback：請求模型沒設 Key 時，按優先順序試 anthropic → openai → gemini → claude_code CLI
- 錯誤訊息一律以 "❌ ..." 開頭，方便上游辨識

主要 entry point：`call_text(model_id, prompt, system="", max_tokens=2048)`
"""
from __future__ import annotations

import json
import shutil
import subprocess
import urllib.error
import urllib.request
from typing import Optional

from . import secrets_store


# 模型 → provider 映射
MODEL_PROVIDER: dict[str, str] = {
    # Anthropic
    "claude-opus-4-7": "anthropic",
    "claude-sonnet-4-6": "anthropic",
    "claude-haiku-4-5-20251001": "anthropic",
    # OpenAI
    "gpt-4o": "openai",
    "gpt-4o-mini": "openai",
    # Gemini
    "gemini-2.5-flash": "gemini",
    "gemini-2.5-pro": "gemini",
    # Claude Code CLI
    "claude-code": "claude-code",
}


MODEL_DISPLAY: dict[str, str] = {
    "claude-opus-4-7": "🟣 Claude Opus 4.7",
    "claude-sonnet-4-6": "🟣 Claude Sonnet 4.6",
    "claude-haiku-4-5-20251001": "🟣 Claude Haiku 4.5",
    "gpt-4o": "🟢 GPT-4o",
    "gpt-4o-mini": "🟢 GPT-4o mini",
    "gemini-2.5-flash": "🔵 Gemini 2.5 Flash",
    "gemini-2.5-pro": "🔵 Gemini 2.5 Pro",
    "claude-code": "🧠 Claude Code（訂閱）",
}


def display_name(model_id: str) -> str:
    return MODEL_DISPLAY.get(model_id, model_id)


def available_models() -> list[str]:
    """根據已設定的 API Key 與本機環境，列出可用模型 ID。"""
    out: list[str] = []
    if shutil.which("claude"):
        out.append("claude-code")
    if secrets_store.get_api_key("anthropic"):
        out.extend(["claude-opus-4-7", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"])
    if secrets_store.get_api_key("openai"):
        out.extend(["gpt-4o", "gpt-4o-mini"])
    if secrets_store.get_api_key("gemini"):
        out.extend(["gemini-2.5-flash", "gemini-2.5-pro"])
    return out


def _call_claude_code(prompt: str, system: str) -> str:
    full = f"[角色指令] {system}\n\n{prompt}" if system else prompt
    r = subprocess.run(["claude", "-p", full], capture_output=True, text=True, timeout=120)
    if r.returncode == 0:
        return r.stdout.strip()
    return f"❌ Claude Code 執行失敗：{r.stderr.strip()[:200]}"


def _call_anthropic(model: str, prompt: str, system: str, max_tokens: int) -> str:
    key = secrets_store.get_api_key("anthropic")
    if not key:
        return "❌ 沒有 Anthropic API Key，請到「🤖 雲端模型」設定"
    body: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        body["system"] = system
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    return data["content"][0]["text"]


def _call_openai_compatible(url: str, key: str, model: str, prompt: str, system: str, max_tokens: int) -> str:
    msgs: list[dict] = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    req = urllib.request.Request(
        url,
        data=json.dumps({"model": model, "messages": msgs, "max_tokens": max_tokens}).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"]


def _call_openai(model: str, prompt: str, system: str, max_tokens: int) -> str:
    key = secrets_store.get_api_key("openai")
    if not key:
        return "❌ 沒有 OpenAI API Key，請到「🤖 雲端模型」設定"
    return _call_openai_compatible(
        "https://api.openai.com/v1/chat/completions", key, model, prompt, system, max_tokens
    )


def _call_gemini(model: str, prompt: str, system: str, max_tokens: int) -> str:
    key = secrets_store.get_api_key("gemini")
    if not key:
        return "❌ 沒有 Google Gemini API Key，請到「🤖 雲端模型」設定"
    body: dict = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": max_tokens},
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    return data["candidates"][0]["content"]["parts"][0]["text"]


def call_text(
    model_id: str,
    prompt: str,
    *,
    system: str = "",
    max_tokens: int = 2048,
) -> str:
    """跑指定模型，回傳純文字。失敗會回 "❌ ..." 字串而不拋例外。"""
    provider = MODEL_PROVIDER.get(model_id)
    if not provider:
        return f"❌ 不認得的模型：{model_id}"
    try:
        if provider == "claude-code":
            return _call_claude_code(prompt, system)
        if provider == "anthropic":
            return _call_anthropic(model_id, prompt, system, max_tokens)
        if provider == "openai":
            return _call_openai(model_id, prompt, system, max_tokens)
        if provider == "gemini":
            return _call_gemini(model_id, prompt, system, max_tokens)
        return f"❌ 不支援的 provider：{provider}"
    except urllib.error.HTTPError as e:
        body_text = ""
        try:
            body_text = e.read().decode("utf-8", errors="ignore")[:200]
        except Exception:
            pass
        return f"❌ API 錯誤（HTTP {e.code}）：{body_text}"
    except Exception as e:
        return f"❌ 呼叫失敗：{e!r}"
