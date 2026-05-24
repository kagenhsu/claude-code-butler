"""通用 Skill 來源解析器。

不管使用者從哪裡看到一段 SKILL.md 內容,都把它變成統一的 `FetchedSkill`:
- raw URL（任何網址）
- 直接貼 markdown 內容
- 上傳 .md 檔
"""
from __future__ import annotations

import re
import urllib.error
import urllib.request

from .github_skill import FetchedSkill, _parse_frontmatter, _slugify, check_safety


_UA = "Claude-Code-Butler/1.0"


def from_raw_url(url: str, *, timeout: int = 10) -> FetchedSkill:
    """從任意 URL 抓內容（不限 GitHub）。"""
    result = FetchedSkill(url=url)
    url = url.strip()
    if not re.match(r"^https?://", url, re.IGNORECASE):
        result.fetch_error = "URL 必須以 http:// 或 https:// 開頭"
        return result
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        result.fetch_error = f"HTTP {e.code}（{e.reason}）"
        return result
    except Exception as e:
        result.fetch_error = f"連線失敗：{e}"
        return result

    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        result.fetch_error = "回傳內容不是 UTF-8 文字（可能是二進位檔）"
        return result

    return _populate_from_content(result, content)


def from_paste(content: str, *, fallback_name: str = "") -> FetchedSkill:
    """直接貼上的 markdown 內容。"""
    result = FetchedSkill(url="(paste)")
    if not content.strip():
        result.fetch_error = "內容是空的"
        return result
    populated = _populate_from_content(result, content)
    if not populated.name and fallback_name:
        populated.name = _slugify(fallback_name)
    return populated


def from_file_bytes(data: bytes, filename: str = "") -> FetchedSkill:
    """從上傳檔案來的 bytes。"""
    result = FetchedSkill(url=f"(file:{filename})" if filename else "(file)")
    try:
        content = data.decode("utf-8")
    except UnicodeDecodeError:
        result.fetch_error = "檔案不是 UTF-8 文字（請上傳 .md 純文字檔）"
        return result
    populated = _populate_from_content(result, content)
    if not populated.name and filename:
        stem = filename.rsplit("/", 1)[-1]
        stem = re.sub(r"\.(md|markdown|txt)$", "", stem, flags=re.IGNORECASE)
        if stem.upper() == "SKILL":
            stem = filename.rsplit("/", 2)[-2] if "/" in filename else stem
        populated.name = _slugify(stem)
    return populated


def _populate_from_content(result: FetchedSkill, content: str) -> FetchedSkill:
    result.raw_content = content
    meta, body = _parse_frontmatter(content)
    result.name = meta.get("name", "")
    result.description = meta.get("description", "")
    result.body = body if body.strip() else content

    if not result.name:
        first_line = content.strip().split("\n", 1)[0]
        if first_line.startswith("# "):
            result.name = _slugify(first_line[2:].strip())

    result.safety = check_safety(content)
    return result
