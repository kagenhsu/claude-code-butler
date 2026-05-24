"""跨平台路徑處理（Mac / Windows / Linux 共用）"""
from pathlib import Path


def home_dir() -> Path:
    return Path.home()


def claude_dir() -> Path:
    return home_dir() / ".claude"


def user_skills_dir() -> Path:
    """使用者層 skills：~/.claude/skills/"""
    p = claude_dir() / "skills"
    p.mkdir(parents=True, exist_ok=True)
    return p


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def config_file() -> Path:
    """AI Hub 自己的設定檔：~/ai-hub/config.json"""
    return project_root() / "config.json"


def settings_file() -> Path:
    """Claude Code 全域設定：~/.claude/settings.json"""
    return claude_dir() / "settings.json"


def sandbox_chats_dir() -> Path:
    """對話沙盒儲存的歷史對話：~/.claude/sandbox_chats/"""
    return claude_dir() / "sandbox_chats"


def crypto_key_file() -> Path:
    """加密 API Key 用的本機主密鑰（每台機器獨立）"""
    return claude_dir() / ".aihub_secret"


def streamlit_config_file() -> Path:
    """Streamlit 主題與行為設定：<project>/.streamlit/config.toml"""
    return project_root() / ".streamlit" / "config.toml"


def backups_dir() -> Path:
    """本機備份歷史（保留最近一次匯出記錄）：~/.claude/aihub_backups/"""
    p = claude_dir() / "aihub_backups"
    p.mkdir(parents=True, exist_ok=True)
    return p
