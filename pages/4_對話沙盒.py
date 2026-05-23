"""💬 對話沙盒 — 多模型並排對話、比較回答"""
from __future__ import annotations

import json
import os
import time
import urllib.request
import urllib.error
import shutil
import subprocess
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

- 比較不同模型的回答品質和速度
- 測試 Prompt 在各家模型的效果
- 選擇最適合你任務的模型

### 使用方式

1. 左側選擇要比較的模型（最多 3 個）
2. 可設定角色指令（System Prompt）讓 AI 扮演特定角色
3. 可調整回應長度與創意程度
4. 在下方輸入框打字送出
5. 支援多輪對話，AI 會記住之前的對話內容

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
AVAILABLE_MODELS: list[dict] = []

anthropic_key = _get_key("anthropic", "ANTHROPIC_API_KEY")
if anthropic_key:
    AVAILABLE_MODELS.extend([
        {"id": "claude-sonnet-4-6", "name": "Claude Sonnet 4.6", "provider": "anthropic", "emoji": "🟣"},
        {"id": "claude-haiku-4-5-20251001", "name": "Claude Haiku 4.5", "provider": "anthropic", "emoji": "🟣"},
    ])

openai_key = _get_key("openai", "OPENAI_API_KEY")
if openai_key:
    AVAILABLE_MODELS.extend([
        {"id": "gpt-4o", "name": "GPT-4o", "provider": "openai", "emoji": "🟢"},
        {"id": "gpt-4o-mini", "name": "GPT-4o mini", "provider": "openai", "emoji": "🟢"},
    ])

gemini_key = _get_key("gemini", "GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY", "")
if gemini_key:
    AVAILABLE_MODELS.extend([
        {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "provider": "gemini", "emoji": "🔵"},
    ])

minimax_key = _get_key("minimax", "MINIMAX_API_KEY")
if minimax_key:
    AVAILABLE_MODELS.extend([
        {"id": "MiniMax-Text-01", "name": "MiniMax-Text-01", "provider": "minimax", "emoji": "🟡"},
    ])

deepseek_key = _get_key("deepseek", "DEEPSEEK_API_KEY")
if deepseek_key:
    AVAILABLE_MODELS.extend([
        {"id": "deepseek-chat", "name": "DeepSeek V3", "provider": "deepseek", "emoji": "🔷"},
    ])

xai_key = _get_key("xai", "XAI_API_KEY")
if xai_key:
    AVAILABLE_MODELS.extend([
        {"id": "grok-3-mini", "name": "Grok 3 mini", "provider": "xai", "emoji": "⚫"},
    ])

mistral_key = _get_key("mistral", "MISTRAL_API_KEY")
if mistral_key:
    AVAILABLE_MODELS.extend([
        {"id": "mistral-small-latest", "name": "Mistral Small", "provider": "mistral", "emoji": "🟠"},
    ])

if shutil.which("ollama"):
    try:
        r = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            for line in r.stdout.strip().split("\n")[1:]:
                parts = line.split()
                if parts:
                    AVAILABLE_MODELS.append({
                        "id": f"ollama:{parts[0]}",
                        "name": f"{parts[0]}（Ollama）",
                        "provider": "ollama",
                        "emoji": "🦙",
                    })
    except Exception:
        pass

if shutil.which("lms"):
    try:
        r = subprocess.run(["lms", "ps"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            lines = r.stdout.strip().split("\n")
            if len(lines) > 1:
                for line in lines[1:]:
                    parts = line.strip().split()
                    if parts:
                        model_name = parts[0]
                        AVAILABLE_MODELS.append({
                            "id": f"lmstudio:{model_name}",
                            "name": f"{model_name}（LM Studio）",
                            "provider": "lmstudio",
                            "emoji": "🎬",
                        })
        if not any(m["provider"] == "lmstudio" for m in AVAILABLE_MODELS):
            r2 = subprocess.run(["lms", "status"], capture_output=True, text=True, timeout=5)
            if r2.returncode == 0 and "ON" in r2.stdout:
                AVAILABLE_MODELS.append({
                    "id": "lmstudio:default",
                    "name": "LM Studio（本地）",
                    "provider": "lmstudio",
                    "emoji": "🎬",
                })
    except Exception:
        pass


# ── Prompt 範本 ──────────────────────────────────────────
PROMPT_TEMPLATES = [
    {"name": "翻譯比較", "prompt": "請將以下內容翻譯成英文，保持原意並使用自然的表達方式：\n\n"},
    {"name": "程式碼解釋", "prompt": "請用繁體中文解釋以下程式碼的功能，並指出可能的改進方向：\n\n```\n\n```"},
    {"name": "文章摘要", "prompt": "請用繁體中文將以下文章摘要成 3-5 個重點：\n\n"},
    {"name": "創意發想", "prompt": "請針對以下主題提供 5 個創意點子，每個點子附上簡短說明：\n\n主題："},
    {"name": "Bug 分析", "prompt": "請分析以下錯誤訊息，找出可能的原因並提供解決方案：\n\n"},
    {"name": "SQL 生成", "prompt": "請根據以下需求生成 SQL 查詢語句，並解釋每個部分的作用：\n\n需求："},
]


# ── API 呼叫函式 ──────────────────────────────────────────
def _call_anthropic(model: str, messages: list, system: str, max_tokens: int, temperature: float) -> str:
    body: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
        "temperature": temperature,
    }
    if system:
        body["system"] = system
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(body).encode(),
        headers={
            "x-api-key": anthropic_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    return data["content"][0]["text"]

def _call_openai_compatible(url: str, key: str, model: str, messages: list, system: str, max_tokens: int, temperature: float) -> str:
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.extend(messages)
    req = urllib.request.Request(
        url,
        data=json.dumps({
            "model": model,
            "messages": msgs,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }).encode(),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"]

def _call_gemini(model: str, messages: list, system: str, max_tokens: int, temperature: float) -> str:
    contents = []
    for m in messages:
        role = "user" if m["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})
    body: dict = {
        "contents": contents,
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature},
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    return data["candidates"][0]["content"]["parts"][0]["text"]

def call_model(model_info: dict, messages: list, system: str, max_tokens: int, temperature: float) -> str:
    provider = model_info["provider"]
    model_id = model_info["id"]
    try:
        if provider == "anthropic":
            return _call_anthropic(model_id, messages, system, max_tokens, temperature)
        elif provider == "openai":
            return _call_openai_compatible("https://api.openai.com/v1/chat/completions", openai_key, model_id, messages, system, max_tokens, temperature)
        elif provider == "gemini":
            return _call_gemini(model_id, messages, system, max_tokens, temperature)
        elif provider == "minimax":
            return _call_openai_compatible("https://api.minimax.chat/v1/text/chatcompletion_v2", minimax_key, model_id, messages, system, max_tokens, temperature)
        elif provider == "deepseek":
            return _call_openai_compatible("https://api.deepseek.com/chat/completions", deepseek_key, model_id, messages, system, max_tokens, temperature)
        elif provider == "xai":
            return _call_openai_compatible("https://api.x.ai/v1/chat/completions", xai_key, model_id, messages, system, max_tokens, temperature)
        elif provider == "mistral":
            return _call_openai_compatible("https://api.mistral.ai/v1/chat/completions", mistral_key, model_id, messages, system, max_tokens, temperature)
        elif provider == "ollama":
            actual_model = model_id.replace("ollama:", "")
            return _call_openai_compatible("http://localhost:11434/v1/chat/completions", "ollama", actual_model, messages, system, max_tokens, temperature)
        elif provider == "lmstudio":
            actual_model = model_id.replace("lmstudio:", "")
            return _call_openai_compatible("http://localhost:1234/v1/chat/completions", "lm-studio", actual_model, messages, system, max_tokens, temperature)
        else:
            return f"❌ 不支援的模型提供者：{provider}"
    except urllib.error.HTTPError as e:
        body_text = ""
        try:
            body_text = e.read().decode()[:200]
        except Exception:
            pass
        return f"❌ API 錯誤（HTTP {e.code}）：{body_text}"
    except Exception as e:
        return f"❌ 呼叫失敗：{e}"


# ── Session State ──────────────────────────────────────────
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "conversations" not in st.session_state:
    st.session_state.conversations = {}

# ── 側邊欄 ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 💬 對話沙盒設定")

    if not AVAILABLE_MODELS:
        st.warning("⚠️ 沒有可用的模型。請先到「雲端模型」設定 API Key，或啟動本地模型。")
        st.stop()

    model_names = [f"{m['emoji']} {m['name']}" for m in AVAILABLE_MODELS]

    selected_indices = st.multiselect(
        "選擇模型（最多 3 個）",
        range(len(AVAILABLE_MODELS)),
        default=[0] if AVAILABLE_MODELS else [],
        format_func=lambda i: model_names[i],
        max_selections=3,
    )
    selected_models = [AVAILABLE_MODELS[i] for i in selected_indices]

    st.divider()

    # 角色指令
    st.markdown("**🎭 角色指令（System Prompt）**")
    role_presets = {
        "無（預設）": "",
        "繁體中文助手": "你是一個繁體中文助手，所有回答都使用繁體中文。回答要簡潔、清楚、實用。",
        "程式碼專家": "你是一個資深軟體工程師，擅長多種程式語言。回答程式相關問題時，提供可執行的程式碼範例，並解釋關鍵邏輯。使用繁體中文回答。",
        "翻譯專家": "你是一個專業翻譯，精通中文、英文、日文。翻譯時保持原文語意，使用自然流暢的目標語言表達。",
        "文案寫手": "你是一個創意文案寫手，擅長撰寫吸引人的行銷文案、社群貼文、產品描述。使用繁體中文。",
        "自訂...": "__custom__",
    }
    selected_role = st.selectbox("快速選擇", list(role_presets.keys()), key="role-preset")
    if role_presets[selected_role] == "__custom__":
        system_prompt = st.text_area("自訂角色指令", height=100, key="custom-system", placeholder="你是一個...")
    else:
        system_prompt = role_presets[selected_role]
        if system_prompt:
            st.caption(f"_{system_prompt[:50]}..._" if len(system_prompt) > 50 else f"_{system_prompt}_")

    st.divider()

    # 參數設定
    st.markdown("**⚙️ 參數**")
    max_tokens = st.slider("最大回應長度（tokens）", 128, 4096, 1024, 128, help="數字越大，回答越長")
    temperature = st.slider("創意程度", 0.0, 1.5, 0.7, 0.1, help="0 = 精確嚴謹　1.5 = 天馬行空")

    st.divider()

    # Prompt 範本
    st.markdown("**📋 Prompt 範本**")
    for tpl in PROMPT_TEMPLATES:
        if st.button(f"📝 {tpl['name']}", key=f"tpl-{tpl['name']}", use_container_width=True):
            st.session_state["prefill_prompt"] = tpl["prompt"]
            st.rerun()

    st.divider()

    # 操作
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🗑️ 清除對話", use_container_width=True):
            st.session_state.chat_history = []
            st.session_state.conversations = {}
            st.rerun()
    with col_b:
        if st.button("📥 匯出對話", use_container_width=True):
            st.session_state["show_export"] = True

    st.caption(f"可用模型：{len(AVAILABLE_MODELS)} 個")

# ── 匯出對話 ──────────────────────────────────────────────
if st.session_state.get("show_export") and st.session_state.chat_history:
    export_lines = []
    for entry in st.session_state.chat_history:
        export_lines.append(f"## 使用者\n\n{entry['prompt']}\n")
        for resp in entry["responses"]:
            export_lines.append(f"### {resp['emoji']} {resp['name']}（{resp['time']:.1f}s）\n\n{resp['content']}\n")
        export_lines.append("---\n")
    export_md = "\n".join(export_lines)

    with st.container(border=True):
        st.markdown("**📥 匯出對話**")
        tab_md, tab_json = st.tabs(["Markdown", "JSON"])
        with tab_md:
            st.code(export_md, language="markdown")
            st.download_button("💾 下載 .md", export_md, file_name=f"對話沙盒_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md", mime="text/markdown")
        with tab_json:
            export_json = json.dumps(st.session_state.chat_history, ensure_ascii=False, indent=2)
            st.code(export_json, language="json")
            st.download_button("💾 下載 .json", export_json, file_name=f"對話沙盒_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", mime="application/json")

        if st.button("關閉匯出"):
            st.session_state["show_export"] = False
            st.rerun()
    st.divider()

# ── 主區域 ──────────────────────────────────────────────
if not selected_models:
    st.info("👈 請在左側選擇至少一個模型")
    st.stop()

# 顯示目前選擇的模型標籤
model_tags = "　".join([f"{m['emoji']} **{m['name']}**" for m in selected_models])
st.caption(f"目前模型：{model_tags}")

# ── 對話紀錄顯示 ──────────────────────────────────────────
for entry in st.session_state.chat_history:
    with st.chat_message("user"):
        st.markdown(entry["prompt"])

    if len(entry["responses"]) == 1:
        resp = entry["responses"][0]
        with st.chat_message("assistant"):
            st.caption(f"{resp['emoji']} **{resp['name']}**　⏱️ {resp['time']:.1f}s")
            st.markdown(resp["content"])
    else:
        cols = st.columns(len(entry["responses"]))
        for i, resp in enumerate(entry["responses"]):
            with cols[i]:
                with st.container(border=True):
                    st.caption(f"{resp['emoji']} **{resp['name']}**　⏱️ {resp['time']:.1f}s")
                    st.markdown(resp["content"])

# ── 輸入區 ──────────────────────────────────────────────
prefill = st.session_state.pop("prefill_prompt", None)
if prefill:
    st.info(f"📋 已套用範本，請在下方輸入框繼續編輯後送出")
    prompt = st.chat_input(f"輸入訊息，送給 {len(selected_models)} 個模型...", key="chat-input")
    if not prompt:
        prompt = None
        with st.container(border=True):
            edited = st.text_area("📝 編輯 Prompt 範本", value=prefill, height=150, key="edit-tpl")
            if st.button("📤 送出此 Prompt", type="primary"):
                prompt = edited
else:
    prompt = st.chat_input(f"輸入訊息，送給 {len(selected_models)} 個模型...")

if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)

    # 建構多輪對話訊息
    messages: list[dict] = []
    for entry in st.session_state.chat_history:
        messages.append({"role": "user", "content": entry["prompt"]})
        if entry["responses"]:
            messages.append({"role": "assistant", "content": entry["responses"][0]["content"]})
    messages.append({"role": "user", "content": prompt})

    # 並排呼叫所有模型
    if len(selected_models) == 1:
        model = selected_models[0]
        with st.chat_message("assistant"):
            with st.spinner(f"{model['emoji']} {model['name']} 思考中..."):
                t0 = time.time()
                result = call_model(model, messages, system_prompt, max_tokens, temperature)
                elapsed = time.time() - t0
            st.caption(f"{model['emoji']} **{model['name']}**　⏱️ {elapsed:.1f}s")
            st.markdown(result)
            responses = [{
                "name": model["name"],
                "emoji": model["emoji"],
                "content": result,
                "time": elapsed,
            }]
    else:
        cols = st.columns(len(selected_models))
        responses = []
        for i, model in enumerate(selected_models):
            with cols[i]:
                with st.container(border=True):
                    st.caption(f"{model['emoji']} **{model['name']}**")
                    with st.spinner("思考中..."):
                        t0 = time.time()
                        result = call_model(model, messages, system_prompt, max_tokens, temperature)
                        elapsed = time.time() - t0
                    st.caption(f"⏱️ {elapsed:.1f}s")
                    st.markdown(result)
                    responses.append({
                        "name": model["name"],
                        "emoji": model["emoji"],
                        "content": result,
                        "time": elapsed,
                    })

    st.session_state.chat_history.append({
        "prompt": prompt,
        "timestamp": datetime.now().isoformat(),
        "responses": responses,
    })
