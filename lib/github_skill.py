"""從 GitHub 匯入 Skill：抓取內容 + 安全性檢查"""
from __future__ import annotations

import re
import urllib.request
import urllib.error
import json
from dataclasses import dataclass, field

# 危險指令模式
DANGEROUS_PATTERNS: list[tuple[str, str]] = [
    (r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f", "偵測到 rm -rf，可能刪除大量檔案"),
    (r"\brm\s+-[a-zA-Z]*f[a-zA-Z]*r", "偵測到 rm -fr，可能刪除大量檔案"),
    (r"\bcurl\b.*\|\s*(ba)?sh", "偵測到 curl | sh，可能執行遠端惡意腳本"),
    (r"\bwget\b.*\|\s*(ba)?sh", "偵測到 wget | sh，可能執行遠端惡意腳本"),
    (r"\beval\s*\(", "偵測到 eval()，可能執行任意程式碼"),
    (r"\bexec\s*\(", "偵測到 exec()，可能執行任意程式碼"),
    (r"\b(sudo|chmod\s+777|chmod\s+\+s)", "偵測到權限提升操作"),
    (r"\bdd\s+if=", "偵測到 dd 指令，可能覆寫磁碟"),
    (r">(\/dev\/sd|\/dev\/disk|\/dev\/nvme)", "偵測到直接寫入磁碟裝置"),
    (r"\bmkfs\b", "偵測到格式化磁碟指令"),
    (r"\/etc\/passwd|\/etc\/shadow", "偵測到存取系統密碼檔"),
    (r"\b(ANTHROPIC|OPENAI|GEMINI|AWS|GOOGLE)_.*KEY\b", "偵測到 API Key 變數引用，請確認用途"),
    (r"\bos\.system\s*\(", "偵測到 os.system()，可能執行任意指令"),
    (r"\bsubprocess\.(run|call|Popen)\s*\(", "偵測到 subprocess，可能執行任意指令"),
    (r"--no-verify|--force", "偵測到略過安全檢查的旗標"),
    (r"\bgit\s+push\s+.*--force", "偵測到 git force push"),
]


@dataclass
class SafetyResult:
    is_safe: bool = True
    warnings: list[str] = field(default_factory=list)
    dangers: list[str] = field(default_factory=list)


@dataclass
class FetchedSkill:
    url: str = ""
    name: str = ""
    description: str = ""
    body: str = ""
    raw_content: str = ""
    fetch_error: str = ""
    safety: SafetyResult = field(default_factory=SafetyResult)


def _normalize_github_url(url: str) -> str | None:
    """把各種 GitHub URL 轉成 raw 內容 URL"""
    url = url.strip()

    # 已經是 raw URL
    if "raw.githubusercontent.com" in url:
        return url

    # github.com/user/repo/blob/branch/path → raw
    m = re.match(
        r"https?://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.*)",
        url,
    )
    if m:
        user, repo, branch, path = m.groups()
        return f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{path}"

    # github.com/user/repo/tree/branch/path → 假設是目錄，找 SKILL.md
    m = re.match(
        r"https?://github\.com/([^/]+)/([^/]+)/tree/([^/]+)/(.*)",
        url,
    )
    if m:
        user, repo, branch, path = m.groups()
        path = path.rstrip("/")
        return f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{path}/SKILL.md"

    # github.com/user/repo → 根目錄找 SKILL.md
    m = re.match(
        r"https?://github\.com/([^/]+)/([^/]+)/?$",
        url,
    )
    if m:
        user, repo = m.groups()
        return f"https://raw.githubusercontent.com/{user}/{repo}/main/SKILL.md"

    return None


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """解析 SKILL.md 的 frontmatter"""
    fm_re = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)
    m = fm_re.match(content)
    if not m:
        return {}, content
    meta_block, body = m.group(1), m.group(2)
    meta: dict = {}
    for line in meta_block.splitlines():
        kv = re.match(r"^([A-Za-z0-9_-]+)\s*:\s*(.*)$", line.strip())
        if not kv:
            continue
        key, val = kv.group(1), kv.group(2).strip().strip("'\"")
        meta[key] = val
    return meta, body


def check_safety(content: str) -> SafetyResult:
    """檢查 Skill 內容是否有危險指令"""
    result = SafetyResult()

    for pattern, message in DANGEROUS_PATTERNS:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            if "API Key" in message or "旗標" in message:
                result.warnings.append(f"⚠️ {message}")
            else:
                result.dangers.append(f"🚨 {message}")

    if result.dangers:
        result.is_safe = False

    return result


def fetch_skill_from_github(url: str) -> FetchedSkill:
    """從 GitHub URL 抓取 Skill 內容並做安全檢查"""
    result = FetchedSkill(url=url)

    raw_url = _normalize_github_url(url)
    if not raw_url:
        result.fetch_error = "無法辨識的 GitHub URL。請貼上 github.com 的連結。"
        return result

    try:
        req = urllib.request.Request(raw_url, headers={"User-Agent": "Claude-Code-Butler/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            result.fetch_error = f"找不到檔案（404）。請確認 URL 正確，且檔案名稱為 SKILL.md。\n嘗試的 URL：{raw_url}"
        else:
            result.fetch_error = f"GitHub 回應錯誤：HTTP {e.code}"
        return result
    except Exception as e:
        result.fetch_error = f"無法連線到 GitHub：{e}"
        return result

    result.raw_content = content

    # 解析 frontmatter
    meta, body = _parse_frontmatter(content)
    result.name = meta.get("name", "")
    result.description = meta.get("description", "")
    result.body = body if body.strip() else content

    # 如果沒有 frontmatter，嘗試從第一行 # 標題取名稱
    if not result.name:
        first_line = content.strip().split("\n")[0]
        if first_line.startswith("# "):
            result.name = re.sub(r"[^a-z0-9_-]", "-", first_line[2:].strip().lower())
            result.name = re.sub(r"-+", "-", result.name).strip("-")[:64]

    # 安全檢查
    result.safety = check_safety(content)

    return result
