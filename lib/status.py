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

    # 讀取管家設定檔
    config_keys = {}
    config_providers = {}
    try:
        from .paths import config_file
        cf = config_file()
        if cf.is_file():
            full_cfg = json.load(open(cf, encoding="utf-8"))
            config_keys = full_cfg.get("api_keys", {})
            config_providers = full_cfg.get("providers", {})
    except Exception:
        pass

    def _provider_configured(pid: str, env_var: str) -> bool:
        p = config_providers.get(pid, {})
        return bool(
            p.get("mode")
            or config_keys.get(pid)
            or os.environ.get(env_var)
        )

    # 雲端模型偵測
    cloud = []

    providers_list = [
        ("anthropic", "Claude", "ANTHROPIC_API_KEY"),
        ("openai", "OpenAI", "OPENAI_API_KEY"),
        ("gemini", "Gemini", "GOOGLE_API_KEY"),
        ("minimax", "MiniMax", "MINIMAX_API_KEY"),
        ("deepseek", "DeepSeek", "DEEPSEEK_API_KEY"),
        ("xai", "xAI (Grok)", "XAI_API_KEY"),
        ("mistral", "Mistral", "MISTRAL_API_KEY"),
    ]

    for pid, name, env_var in providers_list:
        configured = _provider_configured(pid, env_var)
        if pid == "anthropic":
            configured = configured or s.claude_code_installed
        if pid == "gemini":
            configured = configured or bool(os.environ.get("GEMINI_API_KEY"))
        cloud.append(CloudModel(
            name=name,
            status="已連接" if configured else "未設定",
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
