"""Skills CRUD：讀寫 ~/.claude/skills/<name>/SKILL.md"""
from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from .paths import user_skills_dir

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)


@dataclass
class Skill:
    folder: str
    name: str
    description: str
    body: str
    broken: bool = False


def validate_name(name: str) -> bool:
    return bool(NAME_RE.match(name or ""))


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    m = FRONTMATTER_RE.match(content)
    if not m:
        return {}, content
    meta_block, body = m.group(1), m.group(2)
    meta: dict = {}
    for line in meta_block.splitlines():
        line = line.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        kv = re.match(r"^([A-Za-z0-9_-]+)\s*:\s*(.*)$", line)
        if not kv:
            continue
        key, val = kv.group(1), kv.group(2).strip()
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]
        meta[key] = val
    return meta, body


def _build_markdown(meta: dict, body: str) -> str:
    lines = ["---"]
    for k, v in meta.items():
        v = str(v)
        if re.search(r"[:#\n\"']", v):
            v_esc = v.replace("'", "''")
            lines.append(f"{k}: '{v_esc}'")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append("")
    return "\n".join(lines) + "\n" + body.lstrip("\n")


def list_skills() -> list[Skill]:
    root = user_skills_dir()
    skills: list[Skill] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        if not validate_name(entry.name):
            continue
        skill_file = entry / "SKILL.md"
        if not skill_file.is_file():
            skills.append(Skill(folder=entry.name, name=entry.name, description="(SKILL.md 不存在)", body="", broken=True))
            continue
        meta, body = _parse_frontmatter(skill_file.read_text(encoding="utf-8"))
        skills.append(Skill(
            folder=entry.name,
            name=meta.get("name", entry.name),
            description=meta.get("description", ""),
            body=body,
        ))
    return skills


def load_skill(folder: str) -> Skill:
    if not validate_name(folder):
        raise ValueError(f"非法 skill 名稱：{folder}")
    skill_file = user_skills_dir() / folder / "SKILL.md"
    if not skill_file.is_file():
        raise FileNotFoundError(f"Skill 不存在：{folder}")
    meta, body = _parse_frontmatter(skill_file.read_text(encoding="utf-8"))
    return Skill(
        folder=folder,
        name=meta.get("name", folder),
        description=meta.get("description", ""),
        body=body,
    )


def save_skill(name: str, description: str, body: str, old_folder: str | None = None) -> None:
    if not validate_name(name):
        raise ValueError("Skill 名稱只能用小寫英數字、底線、連字號（開頭須英數字），最多 64 字")

    root = user_skills_dir()

    # 改名情境：先把舊資料夾刪掉
    if old_folder and old_folder != name:
        if not validate_name(old_folder):
            raise ValueError("舊 skill 名稱非法")
        old_dir = root / old_folder
        if old_dir.is_dir():
            shutil.rmtree(old_dir)

    skill_dir = root / name
    skill_dir.mkdir(parents=True, exist_ok=True)

    meta = {"name": name, "description": description}
    content = _build_markdown(meta, body)
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")


def delete_skill(folder: str) -> None:
    if not validate_name(folder):
        raise ValueError(f"非法 skill 名稱：{folder}")
    skill_dir = user_skills_dir() / folder
    if skill_dir.is_dir():
        shutil.rmtree(skill_dir)
