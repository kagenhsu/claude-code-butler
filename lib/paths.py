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


def config_file() -> Path:
    """AI Hub 自己的設定檔：~/ai-hub/config.json"""
    return Path(__file__).resolve().parent.parent / "config.json"
