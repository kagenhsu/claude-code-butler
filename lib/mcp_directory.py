"""MCP server 目錄 — 新手友善卡片 + 進階搜尋 + 資安資訊。

每個 server entry 都帶：
- 新手卡：what_it_does / good_for / category(general/dev) / difficulty
- 資安卡：risk_level / permissions / security_notes
- 依賴：needs_prereq（["node"], ["uv"], ["docker"]…）
- 安裝參數：params（含 hint 給新手看）
"""
from __future__ import annotations

import json
import re
import shutil
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Optional


# ╔═════════════════════════════════════════════════════════╗
# ║ 前置依賴：給 UI 偵測「使用者裝了 node / uv / docker 嗎」║
# ╚═════════════════════════════════════════════════════════╝
PREREQ_INFO: dict[str, dict] = {
    "node": {
        "label": "Node.js (npx)",
        "check_bin": "npx",
        "install_hint": "brew install node  # 或從 nodejs.org 下載安裝",
        "why_needed": "幾乎所有 `@modelcontextprotocol/server-*` 都是 npm 套件,用 npx 啟動。",
    },
    "uv": {
        "label": "uv (uvx)",
        "check_bin": "uvx",
        "install_hint": "brew install uv  # 或 curl -LsSf https://astral.sh/uv/install.sh | sh",
        "why_needed": "Python 寫的 MCP server 用 uvx 啟動,Anthropic 官方推薦。",
    },
    "docker": {
        "label": "Docker",
        "check_bin": "docker",
        "install_hint": "從 docker.com 下載 Docker Desktop",
        "why_needed": "某些 server 包成 docker image。較少見。",
    },
}


def prereq_status(needs: list[str]) -> list[dict]:
    """回傳 [{key, label, installed, install_hint, why_needed}, ...]。"""
    out = []
    for key in needs:
        info = PREREQ_INFO.get(key, {})
        bin_ = info.get("check_bin", key)
        path = shutil.which(bin_)
        out.append({
            "key": key,
            "label": info.get("label", key),
            "installed": bool(path),
            "path": path or "",
            "install_hint": info.get("install_hint", ""),
            "why_needed": info.get("why_needed", ""),
        })
    return out


# ╔═════════════════════════════════════════════════════════╗
# ║ 風險等級語意                                            ║
# ╚═════════════════════════════════════════════════════════╝
RISK_META: dict[str, dict] = {
    "low": {"emoji": "🟢", "label": "低風險", "color": "green"},
    "medium": {"emoji": "🟡", "label": "中度風險", "color": "orange"},
    "high": {"emoji": "🔴", "label": "高風險", "color": "red"},
}


# ╔═════════════════════════════════════════════════════════╗
# ║ 內建熱門 server 清單(新手卡片用)                       ║
# ╚═════════════════════════════════════════════════════════╝
# category: "general"(一般使用) | "dev"(開發者)
# risk_level: "low"/"medium"/"high"
# permissions: 一句話總結這台 server 會給 Claude 什麼權限
# security_notes: bullet list,具體的資安提醒
# needs_prereq: ["node"] / ["uv"] / ["docker"]
BUILTIN_SERVERS: list[dict] = [
    # ── 一般使用 ─────────────────────────────────────────
    {
        "id": "filesystem",
        "name": "filesystem",
        "label": "📁 讀寫檔案",
        "newbie_title": "讓 Claude 整理你的檔案",
        "what_it_does": "讓 Claude 讀、寫、改你指定資料夾裡的檔案。",
        "good_for": "整理 Downloads / 文件、批次改檔名、用自然語言搜尋檔案內容",
        "category": "general",
        "difficulty": "easy",
        "risk_level": "medium",
        "permissions": "對你指定的單一資料夾(含所有子資料夾)有完整讀寫權",
        "security_notes": [
            "Claude 只能動你選的那個資料夾，動不到其他位置",
            "建議『不要』指向 ~ 或 /，會給太多權限",
            "對重要資料夾(原始碼 / 文件)請先 git commit 或備份",
        ],
        "needs_prereq": ["node"],
        "official": True,
        "tags": ["file", "filesystem", "本機", "讀寫", "整理"],
        "command": "npx",
        "args_template": ["-y", "@modelcontextprotocol/server-filesystem"],
        "params": [{
            "key": "path", "label": "允許存取的資料夾(絕對路徑)",
            "placeholder": "/Users/xujiayuan/Downloads",
            "required": True, "kind": "text", "target": "arg",
            "hint": "從『下載』或『文件』開始最安全。要多個資料夾的話再來編輯加。",
        }],
    },
    {
        "id": "brave-search",
        "name": "brave-search",
        "label": "🦁 上網搜尋",
        "newbie_title": "讓 Claude 能上網查資料",
        "what_it_does": "Claude 能用 Brave 搜尋引擎查網路。",
        "good_for": "查最新資訊、確認事實、找文件、看新聞",
        "category": "general",
        "difficulty": "easy",
        "risk_level": "low",
        "permissions": "把你的搜尋字串送到 Brave 伺服器；不會碰你本機檔案",
        "security_notes": [
            "搜尋關鍵字會送給 Brave API",
            "API Key 用 env 變數存(明文寫進 ~/.claude.json),這檔案權限本來就只有你能讀",
        ],
        "needs_prereq": ["node"],
        "official": True,
        "tags": ["search", "搜尋", "web", "brave", "上網"],
        "command": "npx",
        "args_template": ["-y", "@modelcontextprotocol/server-brave-search"],
        "params": [{
            "key": "BRAVE_API_KEY", "label": "Brave Search API Key",
            "placeholder": "BSA_...", "required": True, "kind": "password", "target": "env",
            "hint": "免費申請:https://brave.com/search/api/(每月 2000 次免費)",
        }],
    },
    {
        "id": "memory",
        "name": "memory",
        "label": "🧠 跨對話記憶",
        "newbie_title": "讓 Claude 記住你以前告訴它的事",
        "what_it_does": "Claude 能把對話事實(你的名字、偏好、專案脈絡)存進本機知識圖,下次自動讀回。",
        "good_for": "不用每次重新介紹自己 / 專案；跨 session 累積上下文",
        "category": "general",
        "difficulty": "easy",
        "risk_level": "low",
        "permissions": "在 ~/.claude/memory 寫一個 JSON 檔；不會上傳",
        "security_notes": [
            "資料完全在本機,不上傳任何伺服器",
            "別跟它說密碼或機密;一旦寫進記憶,以後 Claude 都看得到",
        ],
        "needs_prereq": ["node"],
        "official": True,
        "tags": ["記憶", "memory", "graph", "knowledge"],
        "command": "npx",
        "args_template": ["-y", "@modelcontextprotocol/server-memory"],
        "params": [],
    },
    {
        "id": "fetch",
        "name": "fetch",
        "label": "🌐 抓網頁",
        "newbie_title": "讓 Claude 讀指定網址的內容",
        "what_it_does": "你給 Claude 一個 URL,它能去抓網頁正文回來分析。",
        "good_for": "丟一篇文章請它整理摘要、把網頁內容轉成 markdown",
        "category": "general",
        "difficulty": "easy",
        "risk_level": "low",
        "permissions": "向你指定的網址發 HTTP request;不會碰本機檔案",
        "security_notes": [
            "Claude 只會抓你叫它抓的網址,不會主動瀏覽",
            "私人網站(內網)如果在本機網路內,理論上也抓得到 — 要小心提示",
        ],
        "needs_prereq": ["node"],
        "official": True,
        "tags": ["http", "web", "fetch", "下載", "網頁"],
        "command": "npx",
        "args_template": ["-y", "@modelcontextprotocol/server-fetch"],
        "params": [],
    },
    {
        "id": "time",
        "name": "time",
        "label": "🕐 時間/時區",
        "newbie_title": "讓 Claude 知道現在時間",
        "what_it_does": "Claude 預設不知道現在幾點。裝這個它就會。",
        "good_for": "做排程提醒、計算時差、產生有時間戳的內容",
        "category": "general",
        "difficulty": "easy",
        "risk_level": "low",
        "permissions": "讀系統時間;沒別的",
        "security_notes": ["無風險"],
        "needs_prereq": ["uv"],
        "official": True,
        "tags": ["time", "時間", "時區", "timezone"],
        "command": "uvx",
        "args_template": ["mcp-server-time"],
        "params": [],
    },

    # ── 開發者 ───────────────────────────────────────────
    {
        "id": "github",
        "name": "github",
        "label": "🐙 GitHub",
        "newbie_title": "讓 Claude 操作你的 GitHub",
        "what_it_does": "Claude 能看 issue / 開 PR / 查 commit / 留言 / 改 repo。",
        "good_for": "自動回覆 issue、整理 PR 描述、查專案歷史",
        "category": "dev",
        "difficulty": "medium",
        "risk_level": "high",
        "permissions": "PAT 給多少權限,Claude 就有多少。預設能讀寫你所有 repo!",
        "security_notes": [
            "⚠️ 強烈建議用 fine-grained PAT,只勾你要操作的 repo + 必要 scope",
            "別給 admin / delete_repo 權限",
            "Token 會明文存進 ~/.claude.json — 該檔權限是 600 只有你能讀",
            "可隨時到 GitHub Settings → Developer settings → Tokens 撤銷",
        ],
        "needs_prereq": ["node"],
        "official": True,
        "tags": ["github", "git", "issue", "pr", "開發"],
        "command": "npx",
        "args_template": ["-y", "@modelcontextprotocol/server-github"],
        "params": [{
            "key": "GITHUB_PERSONAL_ACCESS_TOKEN",
            "label": "GitHub Personal Access Token (建議 fine-grained)",
            "placeholder": "ghp_... 或 github_pat_...",
            "required": True, "kind": "password", "target": "env",
            "hint": "申請:https://github.com/settings/personal-access-tokens/new(選 Fine-grained、勾你要的 repo)",
        }],
    },
    {
        "id": "git",
        "name": "git",
        "label": "🌿 本機 Git",
        "newbie_title": "讓 Claude 跑 git 指令",
        "what_it_does": "Claude 能對指定 repo 跑 git status / log / diff / blame 等指令。",
        "good_for": "查專案歷史、整理 changelog、找 commit 來源",
        "category": "dev",
        "difficulty": "easy",
        "risk_level": "medium",
        "permissions": "讀寫你指定的 git repo(含 commit、checkout 等動作)",
        "security_notes": [
            "預設只讀;不會 push 到 remote(除非你叫它)",
            "建議搭配 hook 攔截 git push --force",
        ],
        "needs_prereq": ["uv"],
        "official": True,
        "tags": ["git", "版本控制", "vcs", "開發"],
        "command": "uvx",
        "args_template": ["mcp-server-git", "--repository"],
        "params": [{
            "key": "repo", "label": "Git 倉庫絕對路徑",
            "placeholder": "/Users/xujiayuan/ai-hub",
            "required": True, "kind": "text", "target": "arg",
            "hint": "指向某個 .git 所在的資料夾。",
        }],
    },
    {
        "id": "sqlite",
        "name": "sqlite",
        "label": "🗄️ SQLite",
        "newbie_title": "讓 Claude 查 SQLite 資料庫",
        "what_it_does": "Claude 能對你指定的 .db 檔跑 SQL 查詢。",
        "good_for": "做報表、找異常資料、了解 schema",
        "category": "dev",
        "difficulty": "easy",
        "risk_level": "medium",
        "permissions": "對指定 SQLite 檔有完整讀寫權(包含 DROP TABLE)",
        "security_notes": [
            "⚠️ 不是唯讀!Claude 也能跑 DELETE / DROP",
            "重要 db 請先複製一份再給 Claude 用",
        ],
        "needs_prereq": ["uv"],
        "official": True,
        "tags": ["sqlite", "sql", "資料庫", "db", "開發"],
        "command": "uvx",
        "args_template": ["mcp-server-sqlite", "--db-path"],
        "params": [{
            "key": "db", "label": "SQLite 檔案絕對路徑",
            "placeholder": "/Users/xujiayuan/data.db",
            "required": True, "kind": "text", "target": "arg",
            "hint": "建議:先 cp 原檔成 .db.copy 給 Claude,避免動到原本資料。",
        }],
    },
    {
        "id": "postgres",
        "name": "postgres",
        "label": "🐘 Postgres (唯讀)",
        "newbie_title": "讓 Claude 查 Postgres(唯讀)",
        "what_it_does": "Claude 對 Postgres 跑唯讀 SQL(這個 server 本身有保護,不能寫)。",
        "good_for": "分析 production 資料庫、查 schema、跑 ad-hoc 查詢",
        "category": "dev",
        "difficulty": "medium",
        "risk_level": "medium",
        "permissions": "用你給的連線字串連 DB,只能 SELECT(server 已限制)",
        "security_notes": [
            "連線字串含密碼,會明文存進 ~/.claude.json",
            "強烈建議建一個唯讀帳號專供此用,不要用 superuser",
            "如果是 production,加 IP whitelist 或走 SSH tunnel",
        ],
        "needs_prereq": ["node"],
        "official": True,
        "tags": ["postgres", "sql", "資料庫", "db", "開發"],
        "command": "npx",
        "args_template": ["-y", "@modelcontextprotocol/server-postgres"],
        "params": [{
            "key": "conn", "label": "Postgres 連線字串",
            "placeholder": "postgresql://readonly_user:pass@host:5432/dbname",
            "required": True, "kind": "password", "target": "arg",
            "hint": "建議建專用的 readonly user。",
        }],
    },
    {
        "id": "puppeteer",
        "name": "puppeteer",
        "label": "🎭 瀏覽器自動化",
        "newbie_title": "讓 Claude 操作無頭瀏覽器",
        "what_it_does": "Claude 能開無頭 Chrome、點按、截圖、抓動態網頁。",
        "good_for": "測試前端、抓需登入的網站、自動化重複操作",
        "category": "dev",
        "difficulty": "medium",
        "risk_level": "medium",
        "permissions": "啟動本機瀏覽器,能連任何網址、執行 JavaScript",
        "security_notes": [
            "瀏覽器會啟動真實 session — 別讓它去敏感網站",
            "第一次啟動會下載 Chromium,約 200MB",
        ],
        "needs_prereq": ["node"],
        "official": True,
        "tags": ["browser", "瀏覽器", "puppeteer", "scraping", "截圖", "開發"],
        "command": "npx",
        "args_template": ["-y", "@modelcontextprotocol/server-puppeteer"],
        "params": [],
    },
    {
        "id": "sequentialthinking",
        "name": "sequentialthinking",
        "label": "💭 分步思考",
        "newbie_title": "給 Claude 一個『分步推論』的工具",
        "what_it_does": "Claude 在難題時可以用這個工具一步步展開思路。",
        "good_for": "解複雜邏輯題、規劃多步流程、推理任務",
        "category": "dev",
        "difficulty": "easy",
        "risk_level": "low",
        "permissions": "純運算,不存取外部資料",
        "security_notes": ["無風險"],
        "needs_prereq": ["node"],
        "official": True,
        "tags": ["thinking", "推論", "step", "開發"],
        "command": "npx",
        "args_template": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
        "params": [],
    },
    {
        "id": "slack",
        "name": "slack",
        "label": "💬 Slack",
        "newbie_title": "讓 Claude 讀寫 Slack 訊息",
        "what_it_does": "Claude 能看頻道訊息、發訊息、查 thread。",
        "good_for": "整理頻道討論、自動回 mention、跨頻道找關鍵字",
        "category": "dev",
        "difficulty": "hard",
        "risk_level": "high",
        "permissions": "看到 bot 被加入的所有頻道訊息;可發訊息冒充 bot",
        "security_notes": [
            "Bot 加入的頻道訊息都看得到 — 別把 bot 加進機密頻道",
            "Token 外洩等於 Slack 帳號被入侵",
            "建議走 workspace admin 流程申請,別用個人 token",
        ],
        "needs_prereq": ["node"],
        "official": True,
        "tags": ["slack", "通訊", "訊息", "開發"],
        "command": "npx",
        "args_template": ["-y", "@modelcontextprotocol/server-slack"],
        "params": [
            {"key": "SLACK_BOT_TOKEN", "label": "Slack Bot Token", "placeholder": "xoxb-...",
             "required": True, "kind": "password", "target": "env",
             "hint": "從 https://api.slack.com/apps → OAuth & Permissions 拿"},
            {"key": "SLACK_TEAM_ID", "label": "Slack Team ID", "placeholder": "T01...",
             "required": True, "kind": "text", "target": "env",
             "hint": "Workspace URL 開始的那串 T 開頭 ID"},
        ],
    },
]


# ── 場景分組(給新手 UI 用)─────────────────────────────
def by_category(cat: str) -> list[dict]:
    return [s for s in BUILTIN_SERVERS if s.get("category") == cat]


# ╔═════════════════════════════════════════════════════════╗
# ║ 搜尋                                                    ║
# ╚═════════════════════════════════════════════════════════╝
@dataclass
class SearchHit:
    source: str
    name: str
    description: str
    score: float = 0.0
    builtin_entry: Optional[dict] = None
    install_command: Optional[str] = None
    homepage: str = ""
    downloads_weekly: Optional[int] = None
    stars: Optional[int] = None
    repo_url: Optional[str] = None


def _similarity(a: str, b: str) -> float:
    a, b = a.lower(), b.lower()
    if not a or not b:
        return 0.0
    if a in b or b in a:
        return 0.95
    return SequenceMatcher(None, a, b).ratio()


def _score(query: str, entry: dict) -> float:
    q = query.lower().strip()
    if not q:
        return 0.0
    name = entry.get("name", "").lower()
    label = entry.get("label", "").lower()
    title = entry.get("newbie_title", "").lower()
    desc = entry.get("what_it_does", "").lower() + " " + entry.get("good_for", "").lower()
    tags = " ".join(entry.get("tags", [])).lower()
    if q == name:
        return 1.0
    if q in name:
        return 0.92
    if q in label or q in title:
        return 0.85
    if q in tags:
        return 0.78
    if q in desc:
        return 0.6
    return 0.6 * _similarity(q, name)


def search_builtin(query: str, *, limit: int = 30, min_score: float = 0.3) -> list[SearchHit]:
    out: list[SearchHit] = []
    if not query.strip():
        for e in BUILTIN_SERVERS:
            out.append(SearchHit(source="builtin", name=e["name"],
                                 description=e.get("what_it_does", e.get("desc", "")),
                                 score=0.0, builtin_entry=e))
        return out
    for e in BUILTIN_SERVERS:
        s = _score(query, e)
        if s >= min_score:
            out.append(SearchHit(source="builtin", name=e["name"],
                                 description=e.get("what_it_does", ""),
                                 score=s, builtin_entry=e))
    out.sort(key=lambda h: h.score, reverse=True)
    return out[:limit]


def _npm_weekly_downloads(pkg: str) -> Optional[int]:
    safe = urllib.parse.quote(pkg, safe="@/")
    url = f"https://api.npmjs.org/downloads/point/last-week/{safe}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Claude-Code-Butler/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
        d = data.get("downloads")
        return int(d) if isinstance(d, (int, float)) else None
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError, ValueError):
        return None


def search_npm(query: str, *, limit: int = 8, with_downloads: bool = True) -> list[SearchHit]:
    q = urllib.parse.quote(f"{query} mcp-server")
    url = f"https://registry.npmjs.org/-/v1/search?text={q}&size={limit}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Claude-Code-Butler/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError):
        return []
    hits = []
    for obj in data.get("objects", []):
        pkg = obj.get("package", {})
        name = pkg.get("name", "")
        if "mcp" not in name.lower() and "modelcontext" not in name.lower():
            continue
        hits.append(SearchHit(source="npm", name=name,
                              description=pkg.get("description", ""),
                              score=_similarity(query, name),
                              install_command=f"npx -y {name}",
                              homepage=pkg.get("links", {}).get("npm", "")))
    if with_downloads:
        for h in hits:
            h.downloads_weekly = _npm_weekly_downloads(h.name)
        hits.sort(key=lambda h: ((h.downloads_weekly or -1), h.score), reverse=True)
    else:
        hits.sort(key=lambda h: h.score, reverse=True)
    return hits


def search(query: str, *, include_npm: bool = True, limit: int = 30) -> list[SearchHit]:
    out = search_builtin(query, limit=limit)
    if include_npm and query.strip() and len(out) < limit:
        seen = {h.name for h in out}
        for n in search_npm(query, limit=limit - len(out)):
            if n.name not in seen:
                out.append(n)
    return out


def materialize_builtin(entry: dict, param_values: dict[str, str]) -> dict:
    args = list(entry.get("args_template", []))
    env: dict = {}
    for p in entry.get("params", []):
        v = (param_values.get(p["key"]) or "").strip()
        if not v and p.get("required"):
            raise ValueError(f"必填欄位未填:{p['label']}")
        if not v:
            continue
        if p.get("target") == "env":
            env[p["key"]] = v
        else:
            args.append(v)
    cfg = {"command": entry["command"], "args": args}
    if env:
        cfg["env"] = env
    return cfg


# ╔═════════════════════════════════════════════════════════╗
# ║ 從 GitHub repo URL 抓 README、挖出 MCP 設定             ║
# ╚═════════════════════════════════════════════════════════╝
@dataclass
class GithubMcpHint:
    user: str = ""
    repo: str = ""
    branch: str = ""
    readme_url: str = ""
    has_mcp_keyword: bool = False
    json_configs: list[dict] = field(default_factory=list)
    raw_json_blocks: list[str] = field(default_factory=list)
    install_commands: list[str] = field(default_factory=list)
    stars: Optional[int] = None
    notes: list[str] = field(default_factory=list)
    fetch_error: str = ""


_GITHUB_URL_RE = re.compile(
    r"https?://github\.com/([^/\s]+)/([^/\s]+?)(?:\.git)?(?:/.*)?$",
    re.IGNORECASE,
)


def _parse_github_url(url: str) -> Optional[tuple[str, str]]:
    m = _GITHUB_URL_RE.match(url.strip())
    if not m:
        return None
    return m.group(1), m.group(2)


def _github_api_json(url: str, *, timeout: int = 10) -> Optional[dict]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Claude-Code-Butler/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError):
        return None


def _fetch_text(url: str, *, timeout: int = 10) -> Optional[str]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Claude-Code-Butler/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        return None


def _default_branch(user: str, repo: str) -> tuple[str, Optional[int]]:
    info = _github_api_json(f"https://api.github.com/repos/{user}/{repo}")
    if info:
        return info.get("default_branch") or "main", info.get("stargazers_count")
    return "main", None


def _extract_json_configs(readme: str) -> tuple[list[dict], list[str]]:
    raw_blocks: list[str] = []
    parsed: list[dict] = []
    block_re = re.compile(r"```(?:jsonc?|JSON)?\s*\n(.*?)```", re.DOTALL)
    for m in block_re.finditer(readme):
        body = m.group(1).strip()
        if "mcpServers" not in body and '"command"' not in body and '"url"' not in body:
            continue
        cleaned = re.sub(r"//[^\n]*", "", body)
        cleaned = re.sub(r",(\s*[}\]])", r"\1", cleaned)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            raw_blocks.append(body); continue
        raw_blocks.append(body)
        if isinstance(data, dict) and isinstance(data.get("mcpServers"), dict):
            for name, conf in data["mcpServers"].items():
                if isinstance(conf, dict):
                    parsed.append({"_suggested_name": name, **conf})
        elif isinstance(data, dict) and ("command" in data or "url" in data):
            parsed.append(data)
        elif isinstance(data, dict):
            for name, conf in data.items():
                if isinstance(conf, dict) and ("command" in conf or "url" in conf):
                    parsed.append({"_suggested_name": name, **conf})
    return parsed, raw_blocks


def _extract_install_commands(readme: str) -> list[str]:
    cmds: set[str] = set()
    block_re = re.compile(r"```(?:sh|bash|shell|zsh)?\s*\n(.*?)```", re.DOTALL)
    cmd_re = re.compile(
        r"^\s*(?:npx|uvx|uv run|pip install|docker run|pipx run|deno run)\s+[^\n]+",
        re.MULTILINE,
    )
    for m in block_re.finditer(readme):
        for cm in cmd_re.finditer(m.group(1)):
            line = cm.group(0).strip()
            if "mcp" in line.lower() or "modelcontext" in line.lower():
                cmds.add(line)
    return sorted(cmds)


def from_github_repo(url: str) -> GithubMcpHint:
    parsed = _parse_github_url(url)
    if not parsed:
        return GithubMcpHint(fetch_error="無法辨識的 GitHub URL")
    user, repo = parsed
    branch, stars = _default_branch(user, repo)
    hint = GithubMcpHint(user=user, repo=repo, branch=branch, stars=stars)

    readme_text: Optional[str] = None
    for name in ["README.md", "README.MD", "readme.md", "Readme.md"]:
        url_try = f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{name}"
        text = _fetch_text(url_try)
        if text:
            hint.readme_url = url_try
            readme_text = text
            break
    if not readme_text:
        hint.fetch_error = "找不到 README.md"
        return hint

    hint.has_mcp_keyword = bool(
        re.search(r"\bMCP\b|Model\s+Context\s+Protocol|mcpServers", readme_text, re.IGNORECASE)
    )
    if not hint.has_mcp_keyword:
        hint.notes.append("⚠️ README 沒提到 MCP / Model Context Protocol — 不確定是不是 MCP server")

    configs, raw_blocks = _extract_json_configs(readme_text)
    hint.json_configs = configs
    hint.raw_json_blocks = raw_blocks[:3]
    hint.install_commands = _extract_install_commands(readme_text)

    if not configs and hint.install_commands:
        for cmd in hint.install_commands:
            parts = cmd.split()
            if len(parts) < 2:
                continue
            command, args = parts[0], parts[1:]
            name_hint = repo.lower()
            for a in args:
                if a.startswith("@"):
                    last = a.split("/")[-1]
                    name_hint = re.sub(r"^(server-|mcp-server-|mcp-)", "", last).lower() or name_hint
                elif a.startswith("mcp-server-"):
                    name_hint = a[len("mcp-server-"):]
                elif "/" not in a and a not in ("-y", "--yes"):
                    name_hint = a
            hint.json_configs.append({
                "_suggested_name": name_hint,
                "command": command,
                "args": args,
            })

    if not hint.json_configs:
        hint.notes.append(
            "README 裡沒找到可解析的 mcpServers JSON 或安裝指令;"
            "若你看到 README 有 JSON 範例,可複製貼到「📥 進階 → 貼 JSON」。"
        )
    return hint


# ╔═════════════════════════════════════════════════════════╗
# ║ 官方目錄(modelcontextprotocol/servers)— 給進階搜尋  ║
# ╚═════════════════════════════════════════════════════════╝
OFFICIAL_DIRECTORY_REPO = {
    "user": "modelcontextprotocol",
    "repo": "servers",
    "branch": "main",
    "subdir": "src",
}


def fetch_official_servers(*, force_refresh: bool = False) -> list[dict]:
    import time
    from pathlib import Path
    from .paths import claude_dir
    cache = claude_dir() / "cache" / "mcp_official_directory.json"
    cache.parent.mkdir(parents=True, exist_ok=True)
    if not force_refresh and cache.is_file():
        try:
            data = json.loads(cache.read_text(encoding="utf-8"))
            if time.time() - data.get("ts", 0) < 24 * 60 * 60:
                return data.get("items", [])
        except (OSError, json.JSONDecodeError):
            pass

    info = OFFICIAL_DIRECTORY_REPO
    url = (f"https://api.github.com/repos/{info['user']}/{info['repo']}/"
           f"git/trees/{info['branch']}?recursive=1")
    tree = _github_api_json(url, timeout=15)
    if not tree:
        return []
    items = []
    seen = set()
    prefix = f"{info['subdir']}/"
    for ent in tree.get("tree", []):
        if ent.get("type") != "tree":
            continue
        path = ent.get("path", "")
        if not path.startswith(prefix):
            continue
        rel = path[len(prefix):]
        if "/" in rel or not rel or rel in seen:
            continue
        seen.add(rel)
        items.append({
            "name": rel,
            "github_url": (f"https://github.com/{info['user']}/{info['repo']}/"
                           f"tree/{info['branch']}/{path}"),
        })
    items.sort(key=lambda x: x["name"])
    try:
        cache.write_text(
            json.dumps({"ts": int(time.time()), "items": items}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass
    return items
