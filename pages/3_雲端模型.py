"""🤖 雲端模型 — 訂閱制 / API Key 管理 + 連線測試"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import streamlit as st

from lib.paths import config_file

st.set_page_config(page_title="雲端模型 | Claude Code 管家", page_icon="🤖", layout="wide")

_css = (Path(__file__).parent.parent / "assets" / "style.css").read_text()
st.markdown(f"<style>{_css}</style>", unsafe_allow_html=True)

st.title("🤖 雲端模型")
st.caption("設定你使用的 AI 模型 — 支援訂閱制與 API Key 兩種方式")

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

def _mask_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 8:
        return "****"
    return key[:4] + "…" + key[-4:]

# ── 連線測試函式 ──────────────────────────────────────────
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
    except Exception as e:
        code = getattr(e, "code", None)
        if code == 401:
            return False, "API Key 無效（401 未授權）"
        if code == 429:
            return True, "連線成功（速率限制中，但 Key 有效）"
        return False, f"連線失敗：{e}"

def _test_openai(key: str) -> tuple[bool, str]:
    try:
        import urllib.request
        req = urllib.request.Request("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {key}"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return True, "連線成功"
    except Exception as e:
        code = getattr(e, "code", None)
        if code == 401: return False, "API Key 無效（401 未授權）"
        if code == 429: return True, "連線成功（速率限制中，但 Key 有效）"
        return False, f"連線失敗：{e}"

def _test_gemini(key: str) -> tuple[bool, str]:
    try:
        import urllib.request
        req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models?key={key}")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return True, "連線成功"
    except Exception as e:
        code = getattr(e, "code", None)
        if code in (400, 403): return False, "API Key 無效或權限不足"
        return False, f"連線失敗：{e}"

def _test_minimax(key: str) -> tuple[bool, str]:
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://api.minimax.chat/v1/text/chatcompletion_v2",
            data=json.dumps({"model": "MiniMax-Text-01", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1}).encode(),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return True, "連線成功"
    except Exception as e:
        code = getattr(e, "code", None)
        if code == 401: return False, "API Key 無效（401 未授權）"
        if code == 429: return True, "連線成功（速率限制中，但 Key 有效）"
        return False, f"連線失敗：{e}"

def _test_deepseek(key: str) -> tuple[bool, str]:
    try:
        import urllib.request
        req = urllib.request.Request("https://api.deepseek.com/models", headers={"Authorization": f"Bearer {key}"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return True, "連線成功"
    except Exception as e:
        code = getattr(e, "code", None)
        if code == 401: return False, "API Key 無效（401 未授權）"
        return False, f"連線失敗：{e}"

def _test_xai(key: str) -> tuple[bool, str]:
    try:
        import urllib.request
        req = urllib.request.Request("https://api.x.ai/v1/models", headers={"Authorization": f"Bearer {key}"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return True, "連線成功"
    except Exception as e:
        code = getattr(e, "code", None)
        if code == 401: return False, "API Key 無效（401 未授權）"
        return False, f"連線失敗：{e}"

def _test_mistral(key: str) -> tuple[bool, str]:
    try:
        import urllib.request
        req = urllib.request.Request("https://api.mistral.ai/v1/models", headers={"Authorization": f"Bearer {key}"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return True, "連線成功"
    except Exception as e:
        code = getattr(e, "code", None)
        if code == 401: return False, "API Key 無效（401 未授權）"
        return False, f"連線失敗：{e}"

# ── 頁面說明 ──────────────────────────────────────────────
with st.expander("❓ 訂閱制 vs API Key 有什麼差別？", expanded=False):
    st.markdown("""
### 兩種使用方式

| | 訂閱制（月費） | API Key（按量計費） |
|---|---|---|
| **付費方式** | 每月固定金額 | 用多少付多少 |
| **適合誰** | 個人日常使用 | 開發者、大量自動化 |
| **額度** | 每月有使用上限，動態調整 | 依餘額無上限 |
| **設定方式** | 登入帳號即可 | 需要取得 API Key |

### 怎麼選？

- **我只是想用 Claude Code** → 選訂閱制，直接登入就好
- **我要用程式呼叫 AI API** → 選 API Key
- **我想同時用好幾家 AI** → 各家分別設定

### 各家 API Key 申請網址

| 廠商 | 申請網址 |
|------|----------|
| Anthropic (Claude) | [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys) |
| OpenAI | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| Google (Gemini) | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| MiniMax | [platform.minimaxi.com](https://platform.minimaxi.com/user-center/basic-information/interface-key) |
| DeepSeek | [platform.deepseek.com/api_keys](https://platform.deepseek.com/api_keys) |
| xAI (Grok) | [console.x.ai](https://console.x.ai/) |
| Mistral | [console.mistral.ai/api-keys](https://console.mistral.ai/api-keys) |
""")

# ── 載入設定 ──────────────────────────────────────────────
cfg = _load_config()
providers_cfg = cfg.get("providers", {})

# ── 廠商定義 ──────────────────────────────────────────────
PROVIDERS = [
    {
        "id": "anthropic",
        "name": "Anthropic (Claude)",
        "emoji": "🟣",
        "env_var": "ANTHROPIC_API_KEY",
        "key_prefix": "sk-ant-",
        "test_fn": _test_anthropic,
        "has_subscription": True,
        "links": {
            "官網": "https://www.anthropic.com",
            "訂閱方案": "https://claude.ai/upgrade",
            "API Key 申請": "https://console.anthropic.com/settings/keys",
            "API 定價": "https://www.anthropic.com/pricing",
            "API 文件": "https://docs.anthropic.com",
        },
        "subscription_plans": [
            {"id": "free",    "name": "Free（免費）",       "desc": "Sonnet 模型，基礎速率", "price": "免費"},
            {"id": "pro",     "name": "Pro（$20/月）",      "desc": "Sonnet + 有限 Opus，5 倍速率", "price": "$20/月"},
            {"id": "max_5x",  "name": "Max 5x（$100/月）",  "desc": "Opus + Sonnet，1M 上下文，5 倍速率", "price": "$100/月"},
            {"id": "max_20x", "name": "Max 20x（$200/月）", "desc": "Opus + Sonnet，1M 上下文，20 倍速率", "price": "$200/月"},
        ],
        "models": [
            ("Claude Opus 4.7", "旗艦模型，最強推理能力"),
            ("Claude Sonnet 4.6", "進階模型，速度與能力兼顧"),
            ("Claude Haiku 4.5", "快速模型，適合大量呼叫"),
        ],
    },
    {
        "id": "openai",
        "name": "OpenAI",
        "emoji": "🟢",
        "env_var": "OPENAI_API_KEY",
        "key_prefix": "sk-",
        "test_fn": _test_openai,
        "has_subscription": True,
        "links": {
            "官網": "https://openai.com",
            "訂閱方案": "https://chatgpt.com/#pricing",
            "API Key 申請": "https://platform.openai.com/api-keys",
            "API 定價": "https://openai.com/api/pricing",
            "API 文件": "https://platform.openai.com/docs",
        },
        "subscription_plans": [
            {"id": "free",    "name": "Free（免費）",       "desc": "GPT-4o mini，有限額度", "price": "免費"},
            {"id": "plus",    "name": "Plus（$20/月）",     "desc": "GPT-4o + o3-mini", "price": "$20/月"},
            {"id": "pro",     "name": "Pro（$200/月）",     "desc": "所有模型無限制 + o3 pro", "price": "$200/月"},
        ],
        "models": [
            ("GPT-4o", "多模態旗艦模型"),
            ("GPT-4o mini", "輕量快速模型"),
            ("o3", "深度推理模型"),
        ],
    },
    {
        "id": "gemini",
        "name": "Google (Gemini)",
        "emoji": "🔵",
        "env_var": "GOOGLE_API_KEY",
        "key_prefix": "AI",
        "test_fn": _test_gemini,
        "has_subscription": True,
        "links": {
            "官網": "https://gemini.google.com",
            "訂閱方案": "https://one.google.com/about/ai-premium",
            "API Key 申請": "https://aistudio.google.com/apikey",
            "API 定價": "https://ai.google.dev/pricing",
            "API 文件": "https://ai.google.dev/docs",
        },
        "subscription_plans": [
            {"id": "free",    "name": "Free（免費）",             "desc": "Gemini Flash，有限額度", "price": "免費"},
            {"id": "advanced","name": "Google One AI Premium（$20/月）", "desc": "Gemini 2.5 Pro 完整存取", "price": "$20/月"},
        ],
        "models": [
            ("Gemini 2.5 Pro", "旗艦模型，超長上下文"),
            ("Gemini 2.5 Flash", "快速模型"),
        ],
    },
    {
        "id": "minimax",
        "name": "MiniMax (海螺AI)",
        "emoji": "🟡",
        "env_var": "MINIMAX_API_KEY",
        "key_prefix": "eyJ",
        "test_fn": _test_minimax,
        "has_subscription": True,
        "links": {
            "官網（國際）": "https://hailuoai.com",
            "官網（中國）": "https://www.minimaxi.com",
            "訂閱方案": "https://hailuoai.com/pricing",
            "API Key 申請": "https://platform.minimaxi.com/user-center/basic-information/interface-key",
            "API 定價": "https://platform.minimaxi.com/document/Price",
            "API 文件": "https://platform.minimaxi.com/document/Guides",
        },
        "subscription_plans": [
            {"id": "free",    "name": "Free（免費）",         "desc": "基礎額度，每日有限制", "price": "免費"},
            {"id": "pro",     "name": "Hailuo Pro（$9.99/月）","desc": "進階存取 + 更高額度", "price": "$9.99/月"},
            {"id": "unlimited","name": "Hailuo Unlimited（$29.99/月）","desc": "無限制使用 + 優先回應", "price": "$29.99/月"},
            {"id": "cn_vip",  "name": "海螺 VIP（¥99/月）",   "desc": "中國版 VIP 完整存取", "price": "¥99/月"},
        ],
        "models": [
            ("MiniMax-Text-01", "旗艦文字模型，4M 超長上下文"),
            ("MiniMax-M1", "深度推理模型"),
        ],
    },
    {
        "id": "deepseek",
        "name": "DeepSeek (深度求索)",
        "emoji": "🔷",
        "env_var": "DEEPSEEK_API_KEY",
        "key_prefix": "sk-",
        "test_fn": _test_deepseek,
        "has_subscription": True,
        "links": {
            "官網": "https://www.deepseek.com",
            "對話介面": "https://chat.deepseek.com",
            "API Key 申請": "https://platform.deepseek.com/api_keys",
            "API 定價": "https://platform.deepseek.com/api-docs/pricing",
            "API 文件": "https://platform.deepseek.com/api-docs",
        },
        "subscription_plans": [
            {"id": "free",  "name": "Free（免費）",         "desc": "DeepSeek 網頁版免費使用", "price": "免費"},
            {"id": "pro",   "name": "DeepSeek Pro（¥9.9/月）","desc": "更高額度 + 優先回應", "price": "¥9.9/月"},
        ],
        "models": [
            ("DeepSeek-R1", "深度推理模型，開源"),
            ("DeepSeek-V3-0324", "通用對話模型，高性價比"),
        ],
    },
    {
        "id": "xai",
        "name": "xAI (Grok)",
        "emoji": "⚫",
        "env_var": "XAI_API_KEY",
        "key_prefix": "xai-",
        "test_fn": _test_xai,
        "has_subscription": True,
        "links": {
            "官網": "https://x.ai",
            "對話介面": "https://grok.com",
            "訂閱方案": "https://grok.com/pricing",
            "API Key 申請": "https://console.x.ai",
            "API 定價": "https://docs.x.ai/docs/pricing",
            "API 文件": "https://docs.x.ai",
        },
        "subscription_plans": [
            {"id": "free",      "name": "Free（免費）",         "desc": "Grok 基礎存取", "price": "免費"},
            {"id": "premium",   "name": "Premium（$8/月）",    "desc": "Grok 進階存取", "price": "$8/月"},
            {"id": "supergrok", "name": "SuperGrok（$30/月）",  "desc": "Grok 3 完整存取", "price": "$30/月"},
        ],
        "models": [
            ("Grok 3", "旗艦推理模型"),
            ("Grok 3 mini", "快速推理模型"),
        ],
    },
    {
        "id": "mistral",
        "name": "Mistral AI",
        "emoji": "🟠",
        "env_var": "MISTRAL_API_KEY",
        "key_prefix": "",
        "test_fn": _test_mistral,
        "has_subscription": True,
        "links": {
            "官網": "https://mistral.ai",
            "對話介面": "https://chat.mistral.ai",
            "訂閱方案": "https://mistral.ai/pricing",
            "API Key 申請": "https://console.mistral.ai/api-keys",
            "API 定價": "https://docs.mistral.ai/capabilities/pricing",
            "API 文件": "https://docs.mistral.ai",
        },
        "subscription_plans": [
            {"id": "free", "name": "Free（免費）", "desc": "基礎模型存取", "price": "免費"},
            {"id": "pro",  "name": "Le Chat Pro（$10/月）", "desc": "所有模型完整存取", "price": "$10/月"},
        ],
        "models": [
            ("Mistral Large", "旗艦模型"),
            ("Mistral Small", "快速模型"),
            ("Codestral", "程式碼專用模型"),
        ],
    },
]

# ── 渲染每家廠商 ──────────────────────────────────────────
for provider in PROVIDERS:
    pid = provider["id"]
    p_cfg = providers_cfg.get(pid, {})
    saved_mode = p_cfg.get("mode", "")  # "subscription" | "api_key" | ""
    saved_key = p_cfg.get("api_key", "")
    saved_plan = p_cfg.get("plan", "")
    env_key = os.environ.get(provider["env_var"], "")

    # 判斷是否已設定
    is_configured = bool(saved_mode)
    # 特殊：Anthropic 有 Claude Code CLI 就算已連接
    has_cli = pid == "anthropic" and shutil.which("claude")

    with st.container(border=True):
        # ── 標題列 ──
        h1, h2 = st.columns([4, 1])
        with h1:
            if is_configured or has_cli:
                if saved_mode == "subscription" or (has_cli and not saved_mode):
                    plan_label = p_cfg.get("plan_name", "") or saved_plan or ("已透過 Claude Code 登入" if has_cli else "已設定")
                    st.markdown(f"### {provider['emoji']} {provider['name']} ✅")
                    st.caption(f"🔄 訂閱制 — {plan_label}")
                else:
                    st.markdown(f"### {provider['emoji']} {provider['name']} ✅")
                    display_key = saved_key or env_key
                    source = "管家設定" if saved_key else "環境變數"
                    st.caption(f"🔑 API Key — `{_mask_key(display_key)}`（{source}）")
            else:
                if env_key:
                    st.markdown(f"### {provider['emoji']} {provider['name']} ✅")
                    st.caption(f"🔑 API Key — `{_mask_key(env_key)}`（環境變數自動偵測）")
                else:
                    st.markdown(f"### {provider['emoji']} {provider['name']} ⬜")
                    st.caption("尚未設定")
        with h2:
            if is_configured or has_cli or env_key:
                st.success("已設定", icon="✅")
            else:
                st.info("未設定", icon="⬜")

        # 可用模型
        model_text = " · ".join([f"`{m[0]}`" for m in provider["models"]])
        st.caption(f"可用模型：{model_text}")

        # 快速連結
        links = provider.get("links", {})
        if links:
            link_parts = [f"[{label}]({url})" for label, url in links.items()]
            st.caption("🔗 " + " ｜ ".join(link_parts))

        # ── 設定區域 ──
        mode_options = []
        if provider.get("has_subscription"):
            mode_options.append("🔄 訂閱制（月費）")
        mode_options.append("🔑 API Key（按量計費）")

        default_idx = 0
        if saved_mode == "api_key" and len(mode_options) > 1:
            default_idx = 1
        elif saved_mode == "subscription":
            default_idx = 0

        selected_mode = st.radio(
            "使用方式",
            mode_options,
            index=default_idx,
            key=f"mode-{pid}",
            horizontal=True,
            label_visibility="collapsed",
        )

        is_sub = "訂閱" in selected_mode

        if is_sub and provider.get("has_subscription"):
            # ── 訂閱制設定 ──
            plans = provider["subscription_plans"]
            plan_names = [f"{p['name']} — {p['desc']}" for p in plans]

            current_idx = 0
            if saved_plan:
                for i, p in enumerate(plans):
                    if p["id"] == saved_plan:
                        current_idx = i
                        break

            selected_plan_str = st.selectbox(
                "選擇你的方案",
                plan_names,
                index=current_idx,
                key=f"plan-{pid}",
            )
            selected_plan_idx = plan_names.index(selected_plan_str)
            selected_plan = plans[selected_plan_idx]

            s1, s2, _ = st.columns([1, 1, 3])
            with s1:
                if st.button("💾 儲存方案", key=f"save-sub-{pid}", type="primary", use_container_width=True):
                    if "providers" not in cfg:
                        cfg["providers"] = {}
                    cfg["providers"][pid] = {
                        "mode": "subscription",
                        "plan": selected_plan["id"],
                        "plan_name": selected_plan["name"],
                    }
                    _save_config(cfg)
                    st.success(f"✅ 已設定為 {selected_plan['name']}")
                    st.rerun()
            with s2:
                if saved_mode == "subscription":
                    if st.button("🗑️ 清除設定", key=f"del-sub-{pid}", use_container_width=True):
                        cfg.get("providers", {}).pop(pid, None)
                        _save_config(cfg)
                        st.success("已清除")
                        st.rerun()

        else:
            # ── API Key 設定 ──
            k1, k2, k3 = st.columns([3, 1, 1])

            with k1:
                new_key = st.text_input(
                    f"輸入 {provider['name']} API Key",
                    type="password",
                    placeholder=f"{provider['key_prefix']}...",
                    key=f"input-{pid}",
                    label_visibility="collapsed",
                )
            with k2:
                if st.button("💾 儲存", key=f"save-key-{pid}", type="primary", use_container_width=True):
                    if not new_key.strip():
                        st.error("❌ 請輸入 API Key")
                    else:
                        if "providers" not in cfg:
                            cfg["providers"] = {}
                        cfg["providers"][pid] = {
                            "mode": "api_key",
                            "api_key": new_key.strip(),
                        }
                        # 同時存到舊格式以維持相容
                        if "api_keys" not in cfg:
                            cfg["api_keys"] = {}
                        cfg["api_keys"][pid] = new_key.strip()
                        _save_config(cfg)
                        st.success("✅ 已儲存")
                        st.rerun()
            with k3:
                test_key = new_key.strip() or saved_key or env_key
                if st.button("🧪 測試", key=f"test-{pid}", use_container_width=True, disabled=not test_key):
                    with st.spinner("測試中..."):
                        ok, msg = provider["test_fn"](test_key)
                    if ok:
                        st.success(f"✅ {msg}")
                    else:
                        st.error(f"❌ {msg}")

            if saved_key:
                if st.button("🗑️ 移除已儲存的 Key", key=f"del-key-{pid}"):
                    cfg.get("providers", {}).pop(pid, None)
                    cfg.get("api_keys", {}).pop(pid, None)
                    _save_config(cfg)
                    st.success("已移除")
                    st.rerun()

st.divider()

# ── 模型詳細比較 ──────────────────────────────────────────
with st.expander("📋 全模型比較表", expanded=False):
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
| DeepSeek-V3-0324 | DeepSeek | 通用對話、高性價比 | 128K | 💰 |
| Grok 3 | xAI | 旗艦推理 | 128K | 💰💰💰 |
| Grok 3 mini | xAI | 快速推理 | 128K | 💰 |
| Mistral Large | Mistral | 歐洲旗艦模型 | 128K | 💰💰 |
| Codestral | Mistral | 程式碼專用 | 256K | 💰💰 |
""")

st.caption("🔒 所有設定儲存在本機 `config.json`，不會上傳到任何伺服器。")
