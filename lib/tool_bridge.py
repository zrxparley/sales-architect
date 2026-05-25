"""
Enhanced mode: detect and route to coding tools (Claude Code, WorkBuddy).
"""

import subprocess
import shutil


def has_claude() -> bool:
    """Check if Claude Code CLI is available."""
    return shutil.which("claude") is not None


def has_workbuddy() -> bool:
    """Check if WorkBuddy CLI is available."""
    return shutil.which("workbuddy") is not None or shutil.which("wb") is not None


def detect_tools() -> dict:
    """Detect available coding tools."""
    return {
        "claude": has_claude(),
        "workbuddy": has_workbuddy(),
    }


def run_claude(prompt_file: str, working_dir: str = None) -> int:
    """Execute prompt via Claude Code CLI. Returns exit code."""
    try:
        with open(prompt_file, "r") as f:
            prompt_text = f.read()
        cmd = ["claude", "-p", prompt_text]
    except OSError:
        cmd = ["claude", "--file", prompt_file]

    result = subprocess.run(cmd, cwd=working_dir)
    return result.returncode


def run_workbuddy(prompt_file: str, working_dir: str = None) -> int:
    """Execute prompt via WorkBuddy CLI. Returns exit code."""
    wb = shutil.which("workbuddy") or shutil.which("wb")
    if not wb:
        return 1
    cmd = [wb, "--file", prompt_file]
    result = subprocess.run(cmd, cwd=working_dir)
    return result.returncode


def suggest_install() -> str:
    """Return installation instructions for coding tools."""
    return """
╔══════════════════════════════════════════════════╗
║  检测到需要增强模式执行此任务                      ║
╚══════════════════════════════════════════════════╝

  当前未检测到 coding 工具。安装后可解锁:
    - 方案设计 (多步骤工作流)
    - 行业简报 (网页搜索)
    - 原型开发 (代码执行)

  安装 Claude Code:
    npm install -g @anthropic-ai/claude-code

  安装后重试:
    sa solution --tool claude

  或使用内置模式 (--output-only 只生成 prompt):
    sa solution --output-only
"""
