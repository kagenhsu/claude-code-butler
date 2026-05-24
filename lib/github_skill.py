"""從 GitHub 匯入 Skill：抓取內容 + 安全性檢查 + 集合 repo 探索。

支援兩種模式：
- 單一 SKILL.md（blob URL 或 raw URL 或 root SKILL.md）→ FetchedSkill
- 集合 repo（root / tree URL 或 .git clone URL，根目錄沒 SKILL.md
  但有多個子資料夾各帶 SKILL.md）→ SkillCollection
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Optional, Union


# ── 危險指令模式 ─────────────────────────────────────────
DANGEROUS_PATTERNS: list[tuple[str, str]] = [
    (r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f", "偵測到 rm -rf，可能刪除大量檔案"),
    (r"\brm\s+-[a-zA-Z]*f[a-zA-Z]*r", "偵測到 rm -fr，可能刪除大量檔案"),
    (r"\bcurl\b.*\|\s*(ba)?sh", "偵測到 curl | sh,可能執行遠端惡意腳本"),
    (r"\bwget\b.*\|\s*(ba)?sh", "偵測到 wget | sh,可能執行遠端惡意腳本"),
    (r"\beval\s*\(", "偵測到 eval(),可能執行任意程式碼"),
    (r"\bexec\s*\(", "偵測到 exec(),可能執行任意程式碼"),
    (r"\b(sudo|chmod\s+777|chmod\s+\+s)", "偵測到權限提升操作"),
    (r"\bdd\s+if=", "偵測到 dd 指令,可能覆寫磁碟"),
    (r">(\/dev\/sd|\/dev\/disk|\/dev\/nvme)", "偵測到直接寫入磁碟裝置"),
    (r"\bmkfs\b", "偵測到格式化磁碟指令"),
    (r"\/etc\/passwd|\/etc\/shadow", "偵測到存取系統密碼檔"),
    (r"\b(ANTHROPIC|OPENAI|GEMINI|AWS|GOOGLE)_.*KEY\b", "偵測到 API Key 變數引用,請確認用途"),
    (r"\bos\.system\s*\(", "偵測到 os.system(),可能執行任意指令"),
    (r"\bsubprocess\.(run|call|Popen)\s*\(", "偵測到 subprocess,可能執行任意指令"),
    (r"--no-verify|--force", "偵測到略過安全檢查的旗標"),
    (r"\bgit\s+push\s+.*--force", "偵測到 git force push"),
]


# ── Dataclasses ──────────────────────────────────────────
@dataclass
class SafetyResult:
    is_safe: bool = True
    warnings: list[str] = field(default_factory=list)
    dangers: list[str] = field(default_factory=list)


@dataclass
class FetchedSkill:
    """單一 SKILL.md 的抓取結果"""
    url: str = ""
    name: str = ""
    description: str = ""
    body: str = ""
    raw_content: str = ""
    fetch_error: str = ""
    safety: SafetyResult = field(default_factory=SafetyResult)


@dataclass
class SkillCandidate:
    """集合 repo 裡的一個候選 skill（尚未抓內容,只有路徑與名稱）"""
    folder: str            # 例如 "pdf"
    path: str              # 例如 "pdf/SKILL.md"
    raw_url: str           # 該 SKILL.md 的 raw URL
    # 以下欄位在「展開預覽」時才會填入
    fetched: bool = False
    name: str = ""
    description: str = ""
    body: str = ""
    raw_content: str = ""
    safety: SafetyResult = field(default_factory=SafetyResult)
    fetch_error: str = ""


@dataclass
class SkillCollection:
    """從 repo（或 repo 子目錄）發現的多個 skill"""
    url: str = ""
    user: str = ""
    repo: str = ""
    branch: str = ""
    subpath: str = ""           # 起始子路徑（""=repo 根）
    candidates: list[SkillCandidate] = field(default_factory=list)
    fetch_error: str = ""


FetchResult = Union[FetchedSkill, SkillCollection]


# ── URL 解析 ─────────────────────────────────────────────
_HTTP_RE = re.compile(r"^https?://", re.IGNORECASE)


def _strip_git_suffix(s: str) -> str:
    return s[:-4] if s.endswith(".git") else s


def _extract_repo_info(url: str) -> Optional[dict]:
    """把任意 GitHub URL 拆成 {user, repo, kind, branch, path}。
    kind ∈ {'blob', 'tree', 'root', 'raw', 'git'}
    branch / path 對 'root' / 'git' 可為 None / ''。
    """
    url = url.strip()
    if not _HTTP_RE.match(url):
        # 容忍 `git@github.com:user/repo.git` 形式
        m = re.match(r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?/?$", url)
        if m:
            return {"user": m.group(1), "repo": m.group(2), "kind": "git",
                    "branch": None, "path": ""}
        return None

    # raw.githubusercontent.com/<user>/<repo>/<branch>/<path>
    m = re.match(r"https?://raw\.githubusercontent\.com/([^/]+)/([^/]+)/([^/]+)/(.+)$", url)
    if m:
        return {"user": m.group(1), "repo": _strip_git_suffix(m.group(2)),
                "kind": "raw", "branch": m.group(3), "path": m.group(4)}

    # github.com/<user>/<repo>/blob/<branch>/<path>
    m = re.match(r"https?://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.+)$", url)
    if m:
        return {"user": m.group(1), "repo": _strip_git_suffix(m.group(2)),
                "kind": "blob", "branch": m.group(3), "path": m.group(4)}

    # github.com/<user>/<repo>/tree/<branch>[/<path>]
    m = re.match(r"https?://github\.com/([^/]+)/([^/]+)/tree/([^/]+)(?:/(.*))?$", url)
    if m:
        return {"user": m.group(1), "repo": _strip_git_suffix(m.group(2)),
                "kind": "tree", "branch": m.group(3),
                "path": (m.group(4) or "").rstrip("/")}

    # github.com/<user>/<repo>(.git)?
    m = re.match(r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", url)
    if m:
        return {"user": m.group(1), "repo": m.group(2),
                "kind": "git" if url.endswith(".git") else "root",
                "branch": None, "path": ""}

    return None


def _normalize_github_url(url: str) -> Optional[str]:
    """舊版單一檔案路徑邏輯（給 blob / raw / 單檔 root 用）。"""
    info = _extract_repo_info(url)
    if not info:
        return None
    user, repo = info["user"], info["repo"]
    if info["kind"] == "raw":
        return f"https://raw.githubusercontent.com/{user}/{repo}/{info['branch']}/{info['path']}"
    if info["kind"] == "blob":
        return f"https://raw.githubusercontent.com/{user}/{repo}/{info['branch']}/{info['path']}"
    if info["kind"] == "tree":
        # tree URL：假設指向某個 skill 子資料夾
        p = info["path"].rstrip("/")
        return f"https://raw.githubusercontent.com/{user}/{repo}/{info['branch']}/{p}/SKILL.md"
    if info["kind"] in ("root", "git"):
        return f"https://raw.githubusercontent.com/{user}/{repo}/main/SKILL.md"
    return None


# ── HTTP helpers ─────────────────────────────────────────
_UA = "Claude-Code-Butler/1.0"


def _http_get(url: str, *, timeout: int = 10) -> tuple[Optional[bytes], Optional[str]]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read(), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except Exception as e:
        return None, f"{e}"


def _http_get_json(url: str, *, timeout: int = 10) -> tuple[Optional[dict], Optional[str]]:
    data, err = _http_get(url, timeout=timeout)
    if err:
        return None, err
    try:
        return json.loads(data.decode("utf-8")), None
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return None, f"JSON parse 失敗：{e}"


def _default_branch(user: str, repo: str) -> Optional[str]:
    data, err = _http_get_json(f"https://api.github.com/repos/{user}/{repo}")
    if err or not isinstance(data, dict):
        return None
    return data.get("default_branch")


def _list_tree(user: str, repo: str, branch: str) -> tuple[list[dict], Optional[str]]:
    url = f"https://api.github.com/repos/{user}/{repo}/git/trees/{urllib.parse.quote(branch)}?recursive=1"
    data, err = _http_get_json(url, timeout=15)
    if err:
        return [], err
    if not isinstance(data, dict):
        return [], "GitHub API 回傳非預期格式"
    if data.get("truncated"):
        # truncated 仍可用 tree, 只是不完整 — 給 UI 提示
        return data.get("tree", []) or [], "（warning: GitHub 回傳被 truncated, 大型 repo 可能漏掉部分）"
    return data.get("tree", []) or [], None


# ── 解析 SKILL.md ────────────────────────────────────────
def _parse_frontmatter(content: str) -> tuple[dict, str]:
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
    result = SafetyResult()
    for pattern, message in DANGEROUS_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            if "API Key" in message or "旗標" in message:
                result.warnings.append(f"⚠️ {message}")
            else:
                result.dangers.append(f"🚨 {message}")
    if result.dangers:
        result.is_safe = False
    return result


def _slugify(s: str) -> str:
    s = re.sub(r"[^a-z0-9_-]+", "-", s.lower())
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:64]


# ── 公開 API ────────────────────────────────────────────
def fetch_skill_from_github(url: str) -> FetchedSkill:
    """抓單一 SKILL.md。給原本流程用。"""
    result = FetchedSkill(url=url)

    raw_url = _normalize_github_url(url)
    if not raw_url:
        result.fetch_error = "無法辨識的 GitHub URL。請貼上 github.com 的連結。"
        return result

    data, err = _http_get(raw_url)
    if err:
        result.fetch_error = f"抓取失敗：{err}\n嘗試的 URL：{raw_url}"
        return result

    try:
        content = data.decode("utf-8")
    except UnicodeDecodeError:
        result.fetch_error = "回傳內容不是 UTF-8 文字"
        return result

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


def fetch_skill_collection(url: str) -> SkillCollection:
    """掃整個 repo（或 tree 子路徑）裡所有 SKILL.md，只回路徑清單；
    各候選的內容與安全檢查在 UI 展開時才呼 hydrate_candidate。"""
    info = _extract_repo_info(url)
    if not info:
        return SkillCollection(url=url, fetch_error="無法辨識的 GitHub URL")

    user, repo = info["user"], info["repo"]
    branch = info.get("branch")
    subpath = (info.get("path") or "").rstrip("/")

    if not branch:
        branch = _default_branch(user, repo) or "main"

    tree, warn = _list_tree(user, repo, branch)
    if not tree:
        # 試 master 作為後備
        if branch != "master":
            tree2, _ = _list_tree(user, repo, "master")
            if tree2:
                branch = "master"
                tree = tree2
                warn = None
    if not tree:
        return SkillCollection(
            url=url, user=user, repo=repo, branch=branch, subpath=subpath,
            fetch_error=warn or f"找不到 repo {user}/{repo} 的檔案樹（分支：{branch}）",
        )

    # 找出所有 (subpath/...)/SKILL.md — 任意深度都接受，folder 用該 SKILL.md
    # 的『直屬資料夾名』（path 倒數第二段）
    prefix = f"{subpath}/" if subpath else ""
    candidates: list[SkillCandidate] = []
    seen_folders: dict[str, int] = {}  # 處理同名衝突
    for ent in tree:
        if ent.get("type") != "blob":
            continue
        path = ent.get("path", "")
        if not (path.endswith("/SKILL.md") or path == "SKILL.md"):
            continue
        if prefix and not path.startswith(prefix):
            continue
        parts = path.split("/")
        if len(parts) < 2:
            # 根目錄的 SKILL.md：folder = repo 名
            folder = repo
        else:
            folder = parts[-2]
        # 同名 → 加數字後綴
        if folder in seen_folders:
            seen_folders[folder] += 1
            folder = f"{folder}-{seen_folders[folder]}"
        else:
            seen_folders[folder] = 1
        raw_url = (
            f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/"
            f"{urllib.parse.quote(path)}"
        )
        candidates.append(SkillCandidate(folder=folder, path=path, raw_url=raw_url))

    candidates.sort(key=lambda c: c.folder.lower())
    return SkillCollection(
        url=url, user=user, repo=repo, branch=branch, subpath=subpath,
        candidates=candidates, fetch_error=warn or "",
    )


def hydrate_candidate(c: SkillCandidate) -> SkillCandidate:
    """補抓單一候選的內容 + 安全檢查。冪等：已抓過直接回傳。"""
    if c.fetched:
        return c
    data, err = _http_get(c.raw_url)
    if err:
        c.fetch_error = f"抓取失敗：{err}"
        c.fetched = True
        return c
    try:
        content = data.decode("utf-8")
    except UnicodeDecodeError:
        c.fetch_error = "回傳內容不是 UTF-8 文字"
        c.fetched = True
        return c
    c.raw_content = content
    meta, body = _parse_frontmatter(content)
    c.name = meta.get("name", c.folder)
    c.description = meta.get("description", "")
    c.body = body if body.strip() else content
    c.safety = check_safety(content)
    c.fetched = True
    return c


def fetch(url: str) -> FetchResult:
    """聰明分派：
    - blob / raw / .../SKILL.md → 單一 (FetchedSkill)
    - tree / root / .git        → 集合 (SkillCollection)
    若 root 沒有 SKILL.md 但有子資料夾的 SKILL.md，也回 collection。
    """
    info = _extract_repo_info(url)
    if not info:
        f = FetchedSkill(url=url)
        f.fetch_error = "無法辨識的 GitHub URL"
        return f

    kind = info["kind"]
    if kind in ("blob", "raw"):
        return fetch_skill_from_github(url)

    if kind == "tree":
        # 試把 tree path 當成某個 skill 資料夾抓 SKILL.md
        single = fetch_skill_from_github(url)
        if not single.fetch_error and single.raw_content:
            return single
        # 抓不到 → 當集合 repo 列下面所有 SKILL.md
        return fetch_skill_collection(url)

    # root / git → 先試集合，集合空時退回單一（root SKILL.md）
    coll = fetch_skill_collection(url)
    if coll.candidates:
        return coll
    single = fetch_skill_from_github(url)
    if not single.fetch_error:
        return single
    # 都失敗 → 回 collection（含 fetch_error）
    if not coll.fetch_error:
        coll.fetch_error = "這個 repo 找不到任何 SKILL.md"
    return coll
