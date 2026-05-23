"""💬 對話沙盒 — 多模型並排對話、比較回答"""
from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

import streamlit as st

from lib.paths import config_file

st.set_page_config(page_title="對話沙盒 | Claude Code 管家", page_icon="💬", layout="wide")

_css = (Path(__file__).parent.parent / "assets" / "style.css").read_text()
st.markdown(f"<style>{_css}</style>", unsafe_allow_html=True)

st.title("💬 對話沙盒")
st.caption("同一句話餵給不同 AI 模型，並排比較回答")

# ── 說明 ──────────────────────────────────────────────────
with st.expander("❓ 對話沙盒怎麼用？", expanded=False):
    st.markdown("""
### 用途

輸入一句話，同時送給多個 AI 模型，**並排比較**它們的回答。適合：

- 比較不同模型的回答品質
- 測試 Prompt 在各家模型的效果
- 選擇最適合你任務的模型

### 使用方式

1. 左側選擇要比較的模型（最多 3 個）
2. 在下方輸入框打字
3. 點「送出」，等待所有模型回應
4. 回答會並排顯示，方便比較

### 需要什麼？

- 已在「雲端模型」頁面設定好 API Key
- 或有本地模型（Ollama / LM Studio）正在運行
""")

# ── 載入設定 ──────────────────────────────────────────────
def _load_config() -> dict:
    cf = config_file()
    if cf.is_file():
        try:
            return json.loads(cf.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

cfg = _load_config()
api_keys = cfg.get("api_keys", {})
providers_cfg = cfg.get("providers", {})

def _get_key(provider_id: str, env_var: str) -> str:
    p = providers_cfg.get(provider_id, {})
    return p.get("api_key", "") or api_keys.get(provider_id, "") or os.environ.get(env_var, "")

# ── 可用模型列表 ──────────────────────────────────────────
import shutil
import subprocess

AVAILABLE_MODELS: list[dict] = []

# Anthropic
anthropic_key = _get_key("anthropic", "ANTHROPIC_API_KEY")
if anthropic_key:
    AVAILABLE_MODELS.extend([
        {"id": "claude-sonnet-4-6", "name": "Claude Sonnet 4.6", "provider": "anthropic", "emoji": "🟣"},
        {"id": "claude-haiku-4-5-20251001", "name": "Claude Haiku 4.5", "provider": "anthropic", "emoji": "🟣"},
    ])

# OpenAI
openai_key = _get_key("openai", "OPENAI_API_KEY")
if openai_key:
    AVAILABLE_MODELS.extend([
        {"id": "gpt-4o", "name": "GPT-4o", "provider": "openai", "emoji": "🟢"},
        {"id": "gpt-4o-mini", "name": "GPT-4o mini", "provider": "openai", "emoji": "🟢"},
    ])

# Gemini
gemini_key = _get_key("gemini", "GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY", "")
if gemini_key:
    AVAILABLE_MODELS.extend([
        {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "provider": "gemini", "emoji": "🔵"},
    ])

# MiniMax
minimax_key = _get_key("minimax", "MINIMAX_API_KEY")
if minimax_key:
    AVAILABLE_MODELS.extend([
        {"id": "MiniMax-Text-01", "name": "MiniMax-Text-01", "provider": "minimax", "emoji": "🟡"},
    ])

# DeepSeek
deepseek_key = _get_key("deepseek", "DEEPSEEK_API_KEY")
if deepseek_key:
    AVAILABLE_MODELS.extend([
        {"id": "deepseek-chat", "name": "DeepSeek V3", "provider": "deepseek", "emoji": "🔷"},
    ])

# xAI
xai_key = _get_key("xai", "XAI_API_KEY")
if xai_key:
    AVAILABLE_MODELS.extend([
        {"id": "grok-3-mini", "name": "Grok 3 mini", "provider": "xai", "emoji": "⚫"},
    ])

# Mistral
mistral_key = _get_key("mistral", "MISTRAL_API_KEY")
if mistral_key:
    AVAILABLE_MODELS.extend([
        {"id": "mistral-small-latest", "name": "Mistral Small", "provider": "mistral", "emoji": "🟠"},
    ])

# Ollama 本地模型
if shutil.which("ollama"):
    try:
        r = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            for line in r.stdout.strip().split("\n")[1:]:
                parts = line.split()
                if parts:
                    AVAILABLE_MODELS.append({
                        "id": f"ollama:{parts[0]}",
                        "name": f"{parts[0]}（本地）",
                        "provider": "ollama",
                        "emoji": "🦙",
                    })
    except Exception:
        pass

# LM Studio
if shutil.which("lms"):
    try:
        r = subprocess.run(["lms", "status"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and "ON" in r.stdout:
            AVAILABLE_MODELS.append({
                "id": "lmstudio:default",
                "name": "LM Studio（本地）",
                "provider": "lmstudio",
                "emoji": "🎬",
            })
    except Exception:
        pass


# ── API 呼叫函式 ──────────────────────────────────────────
def _call_anthropic(model: str, prompt: str) -> str:
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps({
            "model": model,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        }).encode(),
        headers={
            "x-api-key": anthropic_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    return data["content"][0]["text"]

def _call_openai_compatible(url: str, key: str, model: str, prompt: str) -> str:
    req = urllib.request.Request(
        url,
        data=json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1024,
        }).encode(),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"]

def _call_gemini(model: str, prompt: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
    req = urllib.request.Request(
        url,
        data=json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": 1024},
        }).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    return data["candidates"][0]["content"]["parts"][0]["text"]

def _call_minimax(model: str, prompt: str) -> str:
    return _call_openai_compatible(
        "https://api.minimax.chat/v1/text/chatcompletion_v2",
        minimax_key, model, prompt,
    )

def call_model(model_info: dict, prompt: str) -> str:
    provider = model_info["provider"]
    model_id = model_info["id"]
    try:
        if provider == "anthropic":
            return _call_anthropic(model_id, prompt)
        elif provider == "openai":
            return _call_openai_compatible("https://api.openai.com/v1/chat/completions", openai_key, model_id, prompt)
        elif provider == "gemini":
            return _call_gemini(model_id, prompt)
        elif provider == "minimax":
            return _call_minimax(model_id, prompt)
        elif provider == "deepseek":
            return _call_openai_compatible("https://api.deepseek.com/chat/completions", deepseek_key, model_id, prompt)
        elif provider == "xai":
            return _call_openai_compatible("https://api.x.ai/v1/chat/completions", xai_key, model_id, prompt)
        elif provider == "mistral":
            return _call_openai_compatible("https://api.mistral.ai/v1/chat/completions", mistral_key, model_id, prompt)
        elif provider == "ollama":
            actual_model = model_id.replace("ollama:", "")
            return _call_openai_compatible("http://localhost:11434/v1/chat/completions", "ollama", actual_model, prompt)
        elif provider == "lmstudio":
            return _call_openai_compatible("http://localhost:1234/v1/chat/completions", "lm-studio", "default", prompt)
        else:
            return f"❌ 不支援的模型提供者：{provider}"
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode()[:200]
        except Exception:
            pass
        return f"❌ API 錯誤（HTTP {e.code}）：{body}"
    except Exception as e:
        return f"❌ 呼叫失敗：{e}"


# ── Session State ──────────────────────────────────────────
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ── 側邊欄：模型選擇 ──────────────────────────────────────
with st.sidebar:
    st.markdown("### 💬 對話沙盒設定")

    if not AVAILABLE_MODELS:
        st.warning("⚠️ 沒有可用的模型。請先到「雲端模型」設定 API Key，或啟動本地模型。")
        st.stop()

    model_names = [f"{m['emoji']} {m['name']}" for m in AVAILABLE_MODELS]

    selected_indices = st.multiselect(
        "選擇要比較的模型（最多 3 個）",
        range(len(AVAILABLE_MODELS)),
        default=[0] if AVAILABLE_MODELS else [],
        format_func=lambda i: model_names[i],
        max_selections=3,
    )

    selected_models = [AVAILABLE_MODELS[i] for i in selected_indices]

    st.divider()

    if st.button("🗑️ 清除對話紀錄", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()

    st.divider()
    st.caption(f"可用模型：{len(AVAILABLE_MODELS)} 個")

# ── 對話紀錄顯示 ──────────────────────────────────────────
if not selected_models:
    st.info("👈 請在左側選擇至少一個模型")
    st.stop()

for entry in st.session_state.chat_history:
    # 使用者訊息
    with st.chat_message("user"):
        st.markdown(entry["prompt"])

    # 模型回應並排
    cols = st.columns(len(entry["responses"]))
    for i, resp in enumerate(entry["responses"]):
        with cols[i]:
            with st.container(border=True):
                st.caption(f"{resp['emoji']} **{resp['name']}**　⏱️ {resp['time']:.1f}s")
                st.markdown(resp["content"])

# ── 輸入區 ──────────────────────────────────────────────
prompt = st.chat_input(f"輸入訊息，同時送給 {len(selected_models)} 個模型...")

if prompt:
    # 顯示使用者訊息
    with st.chat_message("user"):
        st.markdown(prompt)

    # 並排呼叫所有模型
    cols = st.columns(len(selected_models))
    responses = []

    for i, model in enumerate(selected_models):
        with cols[i]:
            with st.container(border=True):
                st.caption(f"{model['emoji']} **{model['name']}**")
                with st.spinner("思考中..."):
                    import time
                    t0 = time.time()
                    result = call_model(model, prompt)
                    elapsed = time.time() - t0

                st.caption(f"⏱️ {elapsed:.1f}s")
                st.markdown(result)
                responses.append({
                    "name": model["name"],
                    "emoji": model["emoji"],
                    "content": result,
                    "time": elapsed,
                })

    # 存入歷史
    st.session_state.chat_history.append({
        "prompt": prompt,
        "timestamp": datetime.now().isoformat(),
        "responses": responses,
    })
