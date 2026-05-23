"""偵測系統上 Claude Code、雲端模型、本地模型的狀態"""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field


@dataclass
class CloudModel:
    name: str
    status: str  # "已連接" | "未設定"


@dataclass
class SystemStatus:
    claude_code_installed: bool = False
    claude_code_version: str = ""
    claude_model: str = ""
    cloud_models: list[CloudModel] = field(default_factory=list)
    local_model_count: int = 0
    local_models: list[str] = field(default_factory=list)
    skill_count: int = 0


def _run(cmd: list[str], timeout: int = 5) -> str | None:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def detect_status() -> SystemStatus:
    s = SystemStatus()

    # Claude Code CLI
    if shutil.which("claude"):
        s.claude_code_installed = True
        ver = _run(["claude", "--version"])
        if ver:
            s.claude_code_version = ver.split("\n")[0].strip()

    # 目前使用的模型 — 從 Claude Code settings 讀取
    settings_path = os.path.expanduser("~/.claude/settings.json")
    try:
        import json
        with open(settings_path) as f:
            settings = json.load(f)
        s.claude_model = settings.get("model", "")
    except Exception:
        pass

    if not s.claude_model and s.claude_code_installed:
        s.claude_model = "claude-opus-4-7"

    # 讀取管家設定檔的 API Key
    config_keys = {}
    try:
        from .paths import config_file
        cf = config_file()
        if cf.is_file():
            config_keys = json.load(open(cf, encoding="utf-8")).get("api_keys", {})
    except Exception:
        pass

    # 雲端模型偵測
    cloud = []

    has_anthropic = bool(
        os.environ.get("ANTHROPIC_API_KEY")
        or config_keys.get("anthropic")
        or s.claude_code_installed
    )
    cloud.append(CloudModel(
        name="Claude (Anthropic)",
        status="已連接" if has_anthropic else "未設定",
    ))

    has_openai = bool(
        os.environ.get("OPENAI_API_KEY")
        or config_keys.get("openai")
    )
    cloud.append(CloudModel(
        name="OpenAI",
        status="已連接" if has_openai else "未設定",
    ))

    has_gemini = bool(
        os.environ.get("GOOGLE_API_KEY")
        or os.environ.get("GEMINI_API_KEY")
        or config_keys.get("gemini")
    )
    cloud.append(CloudModel(
        name="Google Gemini",
        status="已連接" if has_gemini else "未設定",
    ))

    has_minimax = bool(
        os.environ.get("MINIMAX_API_KEY")
        or config_keys.get("minimax")
    )
    cloud.append(CloudModel(
        name="MiniMax",
        status="已連接" if has_minimax else "未設定",
    ))

    has_deepseek = bool(
        os.environ.get("DEEPSEEK_API_KEY")
        or config_keys.get("deepseek")
    )
    cloud.append(CloudModel(
        name="DeepSeek",
        status="已連接" if has_deepseek else "未設定",
    ))

    has_xai = bool(
        os.environ.get("XAI_API_KEY")
        or config_keys.get("xai")
    )
    cloud.append(CloudModel(
        name="xAI (Grok)",
        status="已連接" if has_xai else "未設定",
    ))

    has_mistral = bool(
        os.environ.get("MISTRAL_API_KEY")
        or config_keys.get("mistral")
    )
    cloud.append(CloudModel(
        name="Mistral",
        status="已連接" if has_mistral else "未設定",
    ))

    s.cloud_models = cloud

    # 本地模型偵測 (Ollama)
    if shutil.which("ollama"):
        result = _run(["ollama", "list"])
        if result:
            lines = [l for l in result.split("\n")[1:] if l.strip()]
            s.local_models = [l.split()[0] for l in lines if l.split()]
            s.local_model_count = len(s.local_models)

    return s
