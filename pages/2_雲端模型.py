"""🤖 雲端模型 — API Key 管理 + 連線測試"""
from __future__ import annotations

import json
import os
from pathlib import Path

import streamlit as st

from lib.paths import config_file

st.set_page_config(page_title="雲端模型 | Claude Code 管家", page_icon="🤖", layout="wide")

_css = (Path(__file__).parent.parent / "assets" / "style.css").read_text()
st.markdown(f"<style>{_css}</style>", unsafe_allow_html=True)

st.title("🤖 雲端模型")
st.caption("管理 Claude / OpenAI / Gemini 的 API Key，一鍵測試連線")

# ── 設定檔讀寫 ──────────────────────────────────────────────
CONFIG_PATH = config_file()

def _load_config() -> dict:
    if CONFIG_PATH.is_file():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

def _save_config(cfg: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

def _get_keys(cfg: dict) -> dict:
    return cfg.get("api_keys", {})

def _set_key(cfg: dict, provider: str, key: str) -> dict:
    if "api_keys" not in cfg:
        cfg["api_keys"] = {}
    cfg["api_keys"][provider] = key
    return cfg

def _mask_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 8:
        return "****"
    return key[:4] + "…" + key[-4:]

# ── 連線測試 ──────────────────────────────────────────────
def _test_anthropic(key: str) -> tuple[bool, str]:
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps({
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 1,
                "messages": [{"role": "user", "content": "hi"}],
            }).encode(),
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return True, "連線成功"
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return False, "API Key 無效（401 未授權）"
        elif e.code == 429:
            return True, "連線成功（速率限制中，但 Key 有效）"
        else:
            return False, f"HTTP 錯誤 {e.code}"
    except Exception as e:
        return False, f"連線失敗：{e}"

def _test_openai(key: str) -> tuple[bool, str]:
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {key}"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return True, "連線成功"
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return False, "API Key 無效（401 未授權）"
        elif e.code == 429:
            return True, "連線成功（速率限制中，但 Key 有效）"
        else:
            return False, f"HTTP 錯誤 {e.code}"
    except Exception as e:
        return False, f"連線失敗：{e}"

def _test_minimax(key: str) -> tuple[bool, str]:
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://api.minimax.chat/v1/text/chatcompletion_v2",
            data=json.dumps({
                "model": "MiniMax-Text-01",
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 1,
            }).encode(),
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return True, "連線成功"
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return False, "API Key 無效（401 未授權）"
        elif e.code == 429:
            return True, "連線成功（速率限制中，但 Key 有效）"
        else:
            return False, f"HTTP 錯誤 {e.code}"
    except Exception as e:
        return False, f"連線失敗：{e}"

def _test_deepseek(key: str) -> tuple[bool, str]:
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://api.deepseek.com/models",
            headers={"Authorization": f"Bearer {key}"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return True, "連線成功"
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return False, "API Key 無效（401 未授權）"
        else:
            return False, f"HTTP 錯誤 {e.code}"
    except Exception as e:
        return False, f"連線失敗：{e}"

def _test_xai(key: str) -> tuple[bool, str]:
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://api.x.ai/v1/models",
            headers={"Authorization": f"Bearer {key}"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return True, "連線成功"
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return False, "API Key 無效（401 未授權）"
        else:
            return False, f"HTTP 錯誤 {e.code}"
    except Exception as e:
        return False, f"連線失敗：{e}"

def _test_mistral(key: str) -> tuple[bool, str]:
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://api.mistral.ai/v1/models",
            headers={"Authorization": f"Bearer {key}"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return True, "連線成功"
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return False, "API Key 無效（401 未授權）"
        else:
            return False, f"HTTP 錯誤 {e.code}"
    except Exception as e:
        return False, f"連線失敗：{e}"

def _test_gemini(key: str) -> tuple[bool, str]:
    try:
        import urllib.request
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return True, "連線成功"
    except urllib.error.HTTPError as e:
        if e.code == 400 or e.code == 403:
            return False, "API Key 無效或權限不足"
        else:
            return False, f"HTTP 錯誤 {e.code}"
    except Exception as e:
        return False, f"連線失敗：{e}"

# ── 頁面說明 ──────────────────────────────────────────────
with st.expander("❓ API Key 是什麼？怎麼取得？", expanded=False):
    st.markdown("""
### API Key 是什麼？

API Key 是你跟 AI 公司申請的「通行證」，讓程式可以代你呼叫他們的 AI 模型。

### 怎麼取得？

| 廠商 | 申請網址 | 說明 |
|------|----------|------|
| **Anthropic (Claude)** | [console.anthropic.com](https://console.anthropic.com/settings/keys) | 註冊後到 Settings → API Keys 建立 |
| **OpenAI** | [platform.openai.com](https://platform.openai.com/api-keys) | 註冊後到 API Keys 頁面建立 |
| **Google (Gemini)** | [aistudio.google.com](https://aistudio.google.com/apikey) | 到 AI Studio 取得 API Key |
| **MiniMax** | [platform.minimaxi.com](https://platform.minimaxi.com/user-center/basic-information/interface-key) | 註冊後到介面金鑰頁面建立 |
| **DeepSeek** | [platform.deepseek.com](https://platform.deepseek.com/api_keys) | 註冊後到 API Keys 頁面建立 |
| **xAI (Grok)** | [console.x.ai](https://console.x.ai/) | 註冊後建立 API Key |
| **Mistral** | [console.mistral.ai](https://console.mistral.ai/api-keys) | 註冊後到 API Keys 頁面建立 |

### 注意事項

- API Key 是**機密資料**，不要分享給別人
- Key 儲存在本機的 `config.json`，不會上傳到任何地方
- 如果你用的是 Claude Code **訂閱制**（非 API），不需要設定 Anthropic API Key
""")

# ── 載入設定 ──────────────────────────────────────────────
cfg = _load_config()
keys = _get_keys(cfg)

# ── 模型卡片 ──────────────────────────────────────────────
PROVIDERS = [
    {
        "id": "anthropic",
        "name": "Anthropic (Claude)",
        "emoji": "🟣",
        "env_var": "ANTHROPIC_API_KEY",
        "key_prefix": "sk-ant-",
        "test_fn": _test_anthropic,
        "models": [
            ("Claude Opus 4.7", "claude-opus-4-7", "旗艦模型，最強推理能力"),
            ("Claude Sonnet 4.6", "claude-sonnet-4-6", "進階模型，速度與能力兼顧"),
            ("Claude Haiku 4.5", "claude-haiku-4-5", "快速模型，適合大量呼叫"),
        ],
    },
    {
        "id": "openai",
        "name": "OpenAI",
        "emoji": "🟢",
        "env_var": "OPENAI_API_KEY",
        "key_prefix": "sk-",
        "test_fn": _test_openai,
        "models": [
            ("GPT-4o", "gpt-4o", "多模態旗艦模型"),
            ("GPT-4o mini", "gpt-4o-mini", "輕量快速模型"),
            ("o3", "o3", "深度推理模型"),
        ],
    },
    {
        "id": "gemini",
        "name": "Google (Gemini)",
        "emoji": "🔵",
        "env_var": "GOOGLE_API_KEY",
        "key_prefix": "AI",
        "test_fn": _test_gemini,
        "models": [
            ("Gemini 2.5 Pro", "gemini-2.5-pro", "旗艦模型，超長上下文"),
            ("Gemini 2.5 Flash", "gemini-2.5-flash", "快速模型"),
        ],
    },
    {
        "id": "minimax",
        "name": "MiniMax (海螺AI)",
        "emoji": "🟡",
        "env_var": "MINIMAX_API_KEY",
        "key_prefix": "eyJ",
        "test_fn": _test_minimax,
        "models": [
            ("MiniMax-Text-01", "MiniMax-Text-01", "旗艦文字模型，4M 超長上下文"),
            ("MiniMax-M1", "MiniMax-M1", "深度推理模型"),
        ],
    },
    {
        "id": "deepseek",
        "name": "DeepSeek (深度求索)",
        "emoji": "🔷",
        "env_var": "DEEPSEEK_API_KEY",
        "key_prefix": "sk-",
        "test_fn": _test_deepseek,
        "models": [
            ("DeepSeek-R1", "deepseek-r1", "深度推理模型"),
            ("DeepSeek-V3", "deepseek-chat", "通用對話模型"),
        ],
    },
    {
        "id": "xai",
        "name": "xAI (Grok)",
        "emoji": "⚫",
        "env_var": "XAI_API_KEY",
        "key_prefix": "xai-",
        "test_fn": _test_xai,
        "models": [
            ("Grok 3", "grok-3", "旗艦推理模型"),
            ("Grok 3 mini", "grok-3-mini", "快速推理模型"),
        ],
    },
    {
        "id": "mistral",
        "name": "Mistral AI",
        "emoji": "🟠",
        "env_var": "MISTRAL_API_KEY",
        "key_prefix": "",
        "test_fn": _test_mistral,
        "models": [
            ("Mistral Large", "mistral-large-latest", "旗艦模型"),
            ("Mistral Small", "mistral-small-latest", "快速模型"),
            ("Codestral", "codestral-latest", "程式碼專用模型"),
        ],
    },
]

for provider in PROVIDERS:
    pid = provider["id"]
    saved_key = keys.get(pid, "")
    env_key = os.environ.get(provider["env_var"], "")
    active_key = saved_key or env_key
    has_key = bool(active_key)
    key_source = ""
    if saved_key:
        key_source = "（來自管家設定）"
    elif env_key:
        key_source = "（來自環境變數）"

    with st.container(border=True):
        # 標題列
        header_col, status_col = st.columns([4, 1])
        with header_col:
            status_icon = "✅" if has_key else "⬜"
            st.markdown(f"### {provider['emoji']} {provider['name']} {status_icon}")
        with status_col:
            if has_key:
                st.success("已設定", icon="✅")
            else:
                st.warning("未設定", icon="⬜")

        # 目前狀態
        if has_key:
            st.caption(f"目前 Key：`{_mask_key(active_key)}` {key_source}")
        else:
            st.caption(f"尚未設定 API Key。環境變數 `{provider['env_var']}` 也未偵測到。")

        # 可用模型
        model_text = " · ".join([f"`{m[0]}`" for m in provider["models"]])
        st.caption(f"可用模型：{model_text}")

        # 操作區
        action_col1, action_col2, action_col3 = st.columns([3, 1, 1])

        with action_col1:
            new_key = st.text_input(
                f"輸入 {provider['name']} API Key",
                type="password",
                placeholder=f"{provider['key_prefix']}...",
                key=f"input-{pid}",
                label_visibility="collapsed",
            )

        with action_col2:
            if st.button("💾 儲存", key=f"save-{pid}", use_container_width=True):
                if not new_key.strip():
                    st.error("❌ 請輸入 API Key")
                else:
                    cfg = _set_key(cfg, pid, new_key.strip())
                    _save_config(cfg)
                    st.success("✅ 已儲存")
                    st.rerun()

        with action_col3:
            test_key = new_key.strip() or active_key
            if st.button(
                "🧪 測試連線",
                key=f"test-{pid}",
                use_container_width=True,
                disabled=not test_key,
            ):
                with st.spinner("測試中..."):
                    ok, msg = provider["test_fn"](test_key)
                if ok:
                    st.success(f"✅ {msg}")
                else:
                    st.error(f"❌ {msg}")

        # 刪除 Key
        if saved_key:
            if st.button("🗑️ 移除已儲存的 Key", key=f"del-{pid}"):
                cfg["api_keys"].pop(pid, None)
                _save_config(cfg)
                st.success("已移除")
                st.rerun()

st.divider()

# ── 模型詳細比較 ──────────────────────────────────────────
with st.expander("📋 模型比較表", expanded=False):
    st.markdown("""
| 模型 | 廠商 | 擅長 | 上下文 | 價格等級 |
|------|------|------|--------|----------|
| Claude Opus 4.7 | Anthropic | 複雜推理、程式碼 | 1M | 💰💰💰 |
| Claude Sonnet 4.6 | Anthropic | 通用、速度與能力兼顧 | 200K | 💰💰 |
| Claude Haiku 4.5 | Anthropic | 快速回應、大量處理 | 200K | 💰 |
| GPT-4o | OpenAI | 多模態、通用 | 128K | 💰💰 |
| GPT-4o mini | OpenAI | 輕量快速 | 128K | 💰 |
| o3 | OpenAI | 深度推理 | 200K | 💰💰💰 |
| Gemini 2.5 Pro | Google | 超長上下文、多模態 | 1M | 💰💰 |
| Gemini 2.5 Flash | Google | 快速回應 | 1M | 💰 |
| MiniMax-Text-01 | MiniMax | 超長上下文（4M） | 4M | 💰💰 |
| MiniMax-M1 | MiniMax | 深度推理 | 1M | 💰💰 |
| DeepSeek-R1 | DeepSeek | 深度推理、開源 | 128K | 💰 |
| DeepSeek-V3 | DeepSeek | 通用對話、高性價比 | 128K | 💰 |
| Grok 3 | xAI | 旗艦推理 | 128K | 💰💰💰 |
| Grok 3 mini | xAI | 快速推理 | 128K | 💰 |
| Mistral Large | Mistral | 歐洲旗艦模型 | 128K | 💰💰 |
| Codestral | Mistral | 程式碼專用 | 256K | 💰💰 |
""")

# ── 安全提示 ──────────────────────────────────────────────
st.caption("🔒 API Key 儲存在本機 `config.json`，不會上傳到任何伺服器。建議將 `config.json` 加入 `.gitignore`。")
