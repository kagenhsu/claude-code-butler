"""備份與還原：把 Skills、設定、Prompt 庫打包成 zip。

備份內容：
- skills       → ~/.claude/skills/
- settings     → ~/.claude/settings.json
- aihub_config → <project>/config.json（內含加密的 API Key）
- sandbox_chats → ~/.claude/sandbox_chats/（對話沙盒儲存的對話 = Prompt 庫）

⚠️ 安全提醒：
- config.json 內的 API Key 是用本機綁定的主密鑰加密的（~/.claude/.aihub_secret）
- 主密鑰**不會**打包進備份檔，所以備份檔即使外流，API Key 仍是無法解開的密文
- 但這也代表：把備份還原到另一台機器後，原本加密的 API Key 會解不開，需要重設
"""
from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Callable

from .paths import (
    config_file,
    sandbox_chats_dir,
    settings_file,
    user_skills_dir,
)


BACKUP_ITEMS: dict[str, dict] = {
    "skills": {
        "label": "Skills（~/.claude/skills/）",
        "icon": "📂",
        "kind": "dir",
        "path": user_skills_dir,
    },
    "settings": {
        "label": "Claude Code 設定（~/.claude/settings.json）",
        "icon": "⚙️",
        "kind": "file",
        "path": settings_file,
    },
    "aihub_config": {
        "label": "AI Hub 設定（config.json，API Key 已加密）",
        "icon": "🧠",
        "kind": "file",
        "path": config_file,
    },
    "sandbox_chats": {
        "label": "Prompt 庫 ／ 對話沙盒紀錄",
        "icon": "💬",
        "kind": "dir",
        "path": sandbox_chats_dir,
    },
}


def _resolve_path(item_id: str) -> Path:
    spec = BACKUP_ITEMS[item_id]
    return spec["path"]()


def create_backup(selected: list[str]) -> bytes:
    """打包成 zip bytes。"""
    manifest = {
        "format": "aihub-backup",
        "version": 1,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "items": list(selected),
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "manifest.json",
            json.dumps(manifest, ensure_ascii=False, indent=2),
        )
        for item_id in selected:
            spec = BACKUP_ITEMS.get(item_id)
            if not spec:
                continue
            src = _resolve_path(item_id)
            if not src.exists():
                continue
            if spec["kind"] == "file":
                zf.write(src, arcname=f"{item_id}/{src.name}")
            else:
                for p in src.rglob("*"):
                    if p.is_file():
                        zf.write(p, arcname=f"{item_id}/{p.relative_to(src)}")
    return buf.getvalue()


def inspect_backup(zip_bytes: bytes) -> dict:
    """讀備份檔的 manifest + 各項目檔案數。失敗回 {error: ...}。"""
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            try:
                manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
            except KeyError:
                return {"error": "找不到 manifest.json — 不是有效的 AI Hub 備份檔"}
            counts: dict[str, int] = {}
            for name in zf.namelist():
                if name == "manifest.json" or name.endswith("/"):
                    continue
                top = name.split("/", 1)[0]
                counts[top] = counts.get(top, 0) + 1
            return {"manifest": manifest, "counts": counts}
    except zipfile.BadZipFile:
        return {"error": "檔案不是有效的 zip"}


def restore_backup(
    zip_bytes: bytes,
    *,
    selected: list[str] | None = None,
    overwrite: bool = False,
) -> dict:
    """從 zip 還原。

    Args:
        zip_bytes: 備份 zip 內容
        selected: 只還原這幾項；None = 還原 manifest 裡所有項目
        overwrite: 是否覆寫已存在的檔案

    Returns:
        {
          "restored_files": int,
          "skipped_files": int,
          "items_restored": [item_id, ...],
          "errors": [str, ...],
        }
    """
    result = {
        "restored_files": 0,
        "skipped_files": 0,
        "items_restored": [],
        "errors": [],
    }

    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile:
        result["errors"].append("檔案不是有效的 zip")
        return result

    with zf:
        try:
            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        except Exception:
            result["errors"].append("找不到 manifest.json — 不是有效的 AI Hub 備份檔")
            return result

        items_in_backup = list(manifest.get("items", []))
        items_to_restore = (
            [i for i in selected if i in items_in_backup]
            if selected is not None
            else items_in_backup
        )

        for item_id in items_to_restore:
            spec = BACKUP_ITEMS.get(item_id)
            if not spec:
                result["errors"].append(f"未知的備份項目：{item_id}（已跳過）")
                continue

            dest_base = _resolve_path(item_id)
            prefix = f"{item_id}/"
            found_any = False

            for name in zf.namelist():
                if not name.startswith(prefix) or name.endswith("/"):
                    continue
                rel = name[len(prefix):]
                if not rel:
                    continue
                found_any = True

                if spec["kind"] == "file":
                    target = dest_base
                else:
                    target = dest_base / rel

                if target.exists() and not overwrite:
                    result["skipped_files"] += 1
                    continue

                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(zf.read(name))
                result["restored_files"] += 1

            if found_any:
                result["items_restored"].append(item_id)

    return result
