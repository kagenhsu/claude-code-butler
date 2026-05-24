"""Skill 名稱搜尋 — 「使用者只知道名稱」場景。

兩個來源:
1. 已知集合 repo（KNOWN_COLLECTIONS）— anthropics/skills 等可信來源,掃整顆樹後 fuzzy match
2. GitHub Repository Search API — 找 repo 名 / 描述含關鍵字 + 路徑含 SKILL.md 的 repo,按 star 排序

結果統一格式 SearchHit,UI 可一鍵把它丟進 GitHub fetch 流程安裝。

快取:
- KNOWN_COLLECTIONS 掃描結果存 ~/.claude/cache/skill_directory_<repo>.json,TTL 24h
  (避免每次搜尋都 hit GitHub Trees API)
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional

from .github_skill import (
    SkillCandidate,
    SkillCollection,
    fetch_skill_collection,
    hydrate_candidate,
)
from .paths import claude_dir


# 已知可信集合（將來想擴充再加）
KNOWN_COLLECTIONS: list[dict] = [
    {
        "id": "anthropics-skills",
        "label": "Anthropic 官方 Skills",
        "url": "https://github.com/anthropics/skills",
        "trusted": True,
    },
]


CACHE_TTL_SEC = 24 * 60 * 60  # 1 天


def _cache_dir() -> Path:
    p = claude_dir() / "cache"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _cache_file(coll_id: str) -> Path:
    return _cache_dir() / f"skill_directory_{coll_id}.json"


@dataclass
class SearchHit:
    """搜尋結果的一條：能直接灌進 GitHub fetch 流程安裝"""
    source: str               # "anthropics-skills" / "github-search"
    source_label: str         # 給 UI 顯示
    name: str                 # 顯示名 / 預設 skill 名
    description: str
    install_url: str          # 安裝時要餵給 github_fetch 的 URL
    stars: Optional[int] = None
    raw_url: Optional[str] = None  # 直接抓 SKILL.md 用（已知集合才有）
    score: float = 0.0


def _similarity(a: str, b: str) -> float:
    a, b = a.lower(), b.lower()
    if not a or not b:
        return 0.0
    if a in b or b in a:
        return 0.95
    return SequenceMatcher(None, a, b).ratio()


def _score(query: str, name: str, description: str) -> float:
    q = query.lower().strip()
    if not q:
        return 0.0
    name_l = (name or "").lower()
    desc_l = (description or "").lower()
    # 完全相同最高
    if q == name_l:
        return 1.0
    score = 0.0
    if q in name_l:
        score = max(score, 0.85 + 0.1 * (len(q) / max(len(name_l), 1)))
    if q in desc_l:
        score = max(score, 0.55)
    # 拆字（用 - _ 空白）
    tokens = [t for t in q.replace("_", "-").split("-") if t]
    if tokens:
        hits = sum(1 for t in tokens if t in name_l or t in desc_l)
        score = max(score, 0.5 * hits / len(tokens))
    # SequenceMatcher 兜底
    score = max(score, 0.6 * _similarity(q, name_l))
    return score


def _load_cache(coll_id: str) -> Optional[list[dict]]:
    cf = _cache_file(coll_id)
    if not cf.is_file():
        return None
    try:
        data = json.loads(cf.read_text(encoding="utf-8"))
        if time.time() - data.get("ts", 0) > CACHE_TTL_SEC:
            return None
        return data.get("items", [])
    except (OSError, json.JSONDecodeError):
        return None


def _save_cache(coll_id: str, items: list[dict]) -> None:
    cf = _cache_file(coll_id)
    try:
        cf.write_text(json.dumps({"ts": int(time.time()), "items": items},
                                 ensure_ascii=False, indent=2),
                      encoding="utf-8")
    except OSError:
        pass


def _scan_known(coll_def: dict, *, force_refresh: bool = False) -> list[dict]:
    """掃一個已知集合 repo,回傳 hydrate 過的 candidate dicts。"""
    if not force_refresh:
        cached = _load_cache(coll_def["id"])
        if cached is not None:
            return cached

    coll = fetch_skill_collection(coll_def["url"])
    if coll.fetch_error or not coll.candidates:
        return []

    items = []
    for cand in coll.candidates:
        hydrate_candidate(cand)
        items.append({
            "folder": cand.folder,
            "path": cand.path,
            "raw_url": cand.raw_url,
            "name": cand.name or cand.folder,
            "description": cand.description or "",
            "blob_url": (
                f"https://github.com/{coll.user}/{coll.repo}/"
                f"blob/{coll.branch}/{cand.path}"
            ),
        })
    _save_cache(coll_def["id"], items)
    return items


def _hits_from_known(query: str, *, limit: int, force_refresh: bool = False) -> list[SearchHit]:
    out: list[SearchHit] = []
    for coll in KNOWN_COLLECTIONS:
        items = _scan_known(coll, force_refresh=force_refresh)
        for it in items:
            sc = _score(query, it["name"], it["description"])
            if sc < 0.3:
                continue
            out.append(SearchHit(
                source=coll["id"],
                source_label=coll["label"],
                name=it["name"],
                description=it["description"],
                install_url=it["blob_url"],
                raw_url=it["raw_url"],
                score=sc,
            ))
    out.sort(key=lambda h: h.score, reverse=True)
    return out[:limit]


def _search_github_repos(query: str, *, limit: int = 10) -> list[SearchHit]:
    """用 GitHub Repository Search API 找含 SKILL 的 repo,按 star 排序。"""
    q = urllib.parse.quote(f"{query} SKILL in:name,description,readme")
    url = f"https://api.github.com/search/repositories?q={q}&sort=stars&order=desc&per_page={limit}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Claude-Code-Butler/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return []
    if not isinstance(data, dict):
        return []

    hits: list[SearchHit] = []
    for item in data.get("items", []):
        full = item.get("full_name") or ""
        desc = item.get("description") or ""
        stars = item.get("stargazers_count")
        # repo url；交給 github_fetch 自動偵測單一 / 集合
        hits.append(SearchHit(
            source="github-search",
            source_label="GitHub 搜尋",
            name=full,
            description=desc,
            install_url=item.get("html_url") or f"https://github.com/{full}",
            stars=stars,
            score=_score(query, full.split("/")[-1], desc),
        ))
    return hits


def search(query: str, *, limit: int = 20, include_github_search: bool = True,
           force_refresh: bool = False) -> list[SearchHit]:
    """主入口。優先回已知集合的命中(可信)、再 fallback 到 GitHub 搜尋。"""
    query = (query or "").strip()
    if not query:
        return []
    known = _hits_from_known(query, limit=limit, force_refresh=force_refresh)
    out = list(known)
    if include_github_search and len(out) < limit:
        gh = _search_github_repos(query, limit=limit - len(out))
        # 排除掉跟 known 重複 repo
        known_urls = {h.install_url for h in known}
        out.extend(h for h in gh if h.install_url not in known_urls)
    return out[:limit]


def list_all_known(*, force_refresh: bool = False) -> list[SearchHit]:
    """不帶查詢字 — 直接列出所有已知集合裡的 skill,供使用者瀏覽。"""
    out: list[SearchHit] = []
    for coll in KNOWN_COLLECTIONS:
        items = _scan_known(coll, force_refresh=force_refresh)
        for it in items:
            out.append(SearchHit(
                source=coll["id"],
                source_label=coll["label"],
                name=it["name"],
                description=it["description"],
                install_url=it["blob_url"],
                raw_url=it["raw_url"],
                score=0.0,
            ))
    out.sort(key=lambda h: h.name.lower())
    return out
