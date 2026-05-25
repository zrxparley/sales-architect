"""
Configuration management for Sales Architect CLI.
Handles ~/.sa-config read/write and API credential detection.
"""

import json
import os
from pathlib import Path

CONFIG_FILE = Path.home() / ".sa-config"
DEFAULTS = {
    "api": {
        "base_url": "https://api.anthropic.com",
        "api_key": "",
        "model": "claude-sonnet-4-6",
    },
    "architect": {
        "name": "",
        "title": "售前架构师",
        "company": "",
    },
    "defaults": {
        "industry": "",
        "output_dir": str(Path.home() / "sales-architect-outputs"),
    },
}


def load_config() -> dict:
    """Load config with 5-level priority detection."""
    config = _deep_copy(DEFAULTS)

    # Priority 4: Claude Code settings
    claude_settings = Path.home() / ".claude" / "settings.json"
    if claude_settings.exists():
        try:
            data = json.loads(claude_settings.read_text())
            env = data.get("env", {})
            if env.get("ANTHROPIC_BASE_URL"):
                config["api"]["base_url"] = env["ANTHROPIC_BASE_URL"]
            if env.get("ANTHROPIC_AUTH_TOKEN"):
                config["api"]["api_key"] = env["ANTHROPIC_AUTH_TOKEN"]
        except (json.JSONDecodeError, OSError):
            pass

    # Priority 3: ANTHROPIC env vars
    if os.environ.get("ANTHROPIC_BASE_URL"):
        config["api"]["base_url"] = os.environ["ANTHROPIC_BASE_URL"]
    if os.environ.get("ANTHROPIC_API_KEY"):
        config["api"]["api_key"] = os.environ["ANTHROPIC_API_KEY"]

    # Priority 2: SA_ env vars
    if os.environ.get("SA_API_BASE"):
        config["api"]["base_url"] = os.environ["SA_API_BASE"]
    if os.environ.get("SA_API_KEY"):
        config["api"]["api_key"] = os.environ["SA_API_KEY"]
    if os.environ.get("SA_MODEL"):
        config["api"]["model"] = os.environ["SA_MODEL"]

    # Priority 1: ~/.sa-config (highest)
    if CONFIG_FILE.exists():
        try:
            user_config = json.loads(CONFIG_FILE.read_text())
            _deep_merge(config, user_config)
        except (json.JSONDecodeError, OSError):
            pass

    return config


def save_config(config: dict) -> None:
    """Save config to ~/.sa-config."""
    CONFIG_FILE.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n")


def show_config(config: dict) -> str:
    """Format config for display, hiding API key."""
    lines = []
    api = config.get("api", {})
    key = api.get("api_key", "")
    masked = key[:8] + "..." + key[-4:] if len(key) > 12 else "(未配置)" if not key else "***"

    lines.append(f"  Base URL: {api.get('base_url', '(未配置)')}")
    lines.append(f"  API Key:  {masked}")
    lines.append(f"  模型:     {api.get('model', '(未配置)')}")

    arch = config.get("architect", {})
    if arch.get("name"):
        lines.append(f"  姓名:     {arch['name']}")
    if arch.get("company"):
        lines.append(f"  公司:     {arch['company']}")

    return "\n".join(lines)


def _deep_copy(d: dict) -> dict:
    return json.loads(json.dumps(d))


def _deep_merge(base: dict, override: dict) -> None:
    """Merge override into base in-place."""
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
