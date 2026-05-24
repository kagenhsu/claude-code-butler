"""共用頁首導覽列 — 飛電インテリジェンス HUD 風格"""
from __future__ import annotations

import streamlit as st

PAGES = [
    {"icon": "🧠", "label": "儀表板", "url": "/"},
    {"icon": "📂", "label": "技能", "url": "/技能管理"},
    {"icon": "💬", "label": "對話", "url": "/對話沙盒"},
    {"icon": "🤖", "label": "雲端", "url": "/雲端模型"},
    {"icon": "💻", "label": "本地", "url": "/本地模型"},
    {"icon": "⚙️", "label": "設定", "url": "/設定"},
    {"icon": "📱", "label": "通訊", "url": "/通訊軟體"},
    {"icon": "🤖", "label": "任務", "url": "/自動化任務"},
    {"icon": "🪝", "label": "Hooks", "url": "/Hooks"},
]


def render_nav():
    links = " ".join(
        f'<a href="{p["url"]}" target="_self" class="hi-nav-link">'
        f'{p["icon"]} {p["label"]}</a>'
        for p in PAGES
    )

    st.markdown(
        f"""
        <style>
        .hi-nav {{
            position: fixed;
            top: 0; left: 0; right: 0;
            z-index: 99999;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.7rem 2rem;
            background: linear-gradient(135deg, #0B1120 0%, #0F1729 100%);
            border-bottom: 1px solid rgba(0, 210, 255, 0.25);
            box-shadow: 0 2px 16px rgba(0, 210, 255, 0.08);
        }}
        .hi-nav .hi-nav-title {{
            font-weight: 800;
            font-size: 1.4rem;
            letter-spacing: 1.5px;
            white-space: nowrap;
            color: #00D2FF;
            text-shadow: 0 0 12px rgba(0, 210, 255, 0.4);
        }}
        .hi-nav .hi-nav-links {{
            display: flex;
            gap: 0.2rem;
            flex-wrap: wrap;
            justify-content: flex-end;
        }}
        .hi-nav .hi-nav-link {{
            padding: 0.4rem 0.8rem;
            border-radius: 4px;
            text-decoration: none;
            color: rgba(180, 225, 255, 0.75);
            font-size: 1rem;
            font-weight: 600;
            white-space: nowrap;
            transition: all 0.2s;
            border: 1px solid transparent;
        }}
        .hi-nav .hi-nav-link:hover {{
            color: #00D2FF;
            background: rgba(0, 210, 255, 0.08);
            border-color: rgba(0, 210, 255, 0.3);
            text-shadow: 0 0 6px rgba(0, 210, 255, 0.3);
        }}
        .stMainBlockContainer,
        .block-container {{
            padding-top: 5rem !important;
        }}
        </style>
        <div class="hi-nav">
            <div class="hi-nav-title">⚡ CLAUDE CODE 管家</div>
            <div class="hi-nav-links">{links}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
