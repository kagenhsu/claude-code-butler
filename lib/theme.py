"""主題切換：寫入 <project>/.streamlit/config.toml 的 [theme] base。

- "light" → base = "light"
- "dark" → base = "dark"
- "system" → 不寫 base，由 Streamlit 預設（會跟瀏覽器/系統偏好）

⚠️ Streamlit 啟動時才會讀 config.toml，切換後需要重新整理頁面才會生效。
"""
from __future__ import annotations

from pathlib import Path

from .paths import streamlit_config_file


THEMES: dict[str, dict] = {
    "light": {"label": "淺色", "icon": "☀️", "base": "light"},
    "dark": {"label": "深色", "icon": "🌙", "base": "dark"},
    "system": {"label": "跟系統", "icon": "🖥️", "base": None},
}


def _split_sections(text: str) -> list[tuple[str, list[str]]]:
    """把 TOML 切成 [(section_name, lines), ...]，section_name 為空字串代表頂層。"""
    sections: list[tuple[str, list[str]]] = [("", [])]
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            sections.append((stripped[1:-1].strip(), []))
        else:
            sections[-1][1].append(line)
    return sections


def get_theme() -> str:
    cp = streamlit_config_file()
    if not cp.is_file():
        return "system"
    try:
        text = cp.read_text(encoding="utf-8")
    except Exception:
        return "system"
    for name, lines in _split_sections(text):
        if name != "theme":
            continue
        for line in lines:
            s = line.strip()
            if s.startswith("base") and "=" in s:
                val = s.split("=", 1)[1].strip().strip('"').strip("'")
                if val in ("light", "dark"):
                    return val
    return "system"


def set_theme(theme: str) -> None:
    if theme not in THEMES:
        raise ValueError(f"unknown theme: {theme}")

    cp = streamlit_config_file()
    cp.parent.mkdir(parents=True, exist_ok=True)

    existing = cp.read_text(encoding="utf-8") if cp.is_file() else ""
    sections = _split_sections(existing) if existing else [("", [])]

    # 保留所有非 [theme] section
    kept: list[tuple[str, list[str]]] = [(n, l) for n, l in sections if n != "theme"]

    if theme != "system":
        base = THEMES[theme]["base"]
        kept.append(("theme", [f'base = "{base}"']))

    out: list[str] = []
    for name, lines in kept:
        if name:
            if out and out[-1].strip():
                out.append("")
            out.append(f"[{name}]")
        out.extend(line.rstrip() for line in lines)
    # 去掉尾巴多餘空行
    text = "\n".join(out).rstrip() + "\n"
    cp.write_text(text, encoding="utf-8")
