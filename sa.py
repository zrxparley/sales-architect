#!/usr/bin/env python3
"""
售前架构师工具箱 (Sales Architect CLI)
Main entry point — routes subcommands, handles interactive I/O.
"""

import os
import sys
import json
import signal
import tempfile
from pathlib import Path

# Ensure lib is importable
sys.path.insert(0, str(Path(__file__).parent))

from lib.config import load_config, save_config, show_config, CONFIG_FILE
from lib.prompt import load_command, load_workflow, render_prompt, list_commands, list_workflows
from lib.llm import call_llm_streaming
from lib.output import (
    print_header, print_success, print_warning, print_error, print_info,
    display_streaming, format_terminal, format_plain, save_output,
    BOLD, GREEN, YELLOW, BLUE, RED, DIM, RESET,
)
from lib.tool_bridge import detect_tools, run_claude, run_workbuddy, suggest_install
from lib.history import log_history, show_history, clear_history
from lib.cache import get_cache, is_cache_enabled

# ─── Globals ───
SA_HOME = Path(__file__).parent
_partial_output = ""


def handle_interrupt(sig, frame):
    """Save partial output on Ctrl+C."""
    if _partial_output:
        config = load_config()
        out_dir = config.get("defaults", {}).get("output_dir", str(Path.home() / "sales-architect-outputs"))
        path = Path(out_dir) / "interrupted-output.md"
        path.write_text(_partial_output, encoding="utf-8")
        print(f"\n\n  {YELLOW}⚠ 已中断。部分内容已保存到: {path}{RESET}")
    sys.exit(130)


signal.signal(signal.SIGINT, handle_interrupt)


# ═══════════════════════════════════════════════════
# Subcommand handlers
# ═══════════════════════════════════════════════════

def cmd_help():
    """Show help."""
    print_header("售前架构师工具箱 · 命令帮助")

    print(f"  {BOLD}售前命令:{RESET}")
    commands_info = [
        ("lead-score", "线索评估 — 8维100分量化商机质量"),
        ("news", "AI行业早报 — 今日核心动态"),
        ("briefing", "行业深度简报 — 客户背景研究"),
        ("strategy", "战略分析 — KPMG框架诊断客户痛点"),
        ("simulate", "战局推演 — 多路径风险收益模拟"),
        ("solution", "方案设计 — 8步标准化方案文档"),
        ("decide", "商业决策 — 双引擎结构化分析"),
        ("build", "原型开发 — POC/全栈开发"),
        ("learn", "能力学习 — 生成技能树"),
    ]
    for cmd, desc in commands_info:
        print(f"    {BLUE}sa {cmd:<14}{RESET} {desc}")

    print(f"\n  {BOLD}组合工作流:{RESET}")
    workflows_info = [
        ("cycle", "完整售前周期 (线索→简报→战略→方案→推演)"),
        ("rfp", "快速RFP响应"),
        ("compete", "竞标对抗分析"),
    ]
    for cmd, desc in workflows_info:
        print(f"    {BLUE}sa {cmd:<14}{RESET} {desc}")

    print(f"\n  {BOLD}辅助命令:{RESET}")
    aux_info = [
        ("config", "配置 API / 个人信息"),
        ("status", "查看 skill 安装状态"),
        ("update", "更新所有 skill"),
        ("history", "查看历史记录"),
        ("cache", "管理 LLM 缓存"),
        ("docs", "打开输出目录"),
        ("help", "显示帮助"),
    ]
    for cmd, desc in aux_info:
        print(f"    {BLUE}sa {cmd:<14}{RESET} {desc}")

    print(f"\n  {BOLD}输出控制:{RESET}")
    print(f"    {DIM}sa <命令> --plain          纯文本输出 (可粘贴微信){RESET}")
    print(f"    {DIM}sa <命令> --tool claude    强制使用 Claude Code{RESET}")
    print(f"    {DIM}sa <命令> --output-only    只生成 prompt 文件{RESET}")
    print()


def cmd_welcome():
    """Show welcome message and first-use guidance."""
    config = load_config()
    has_key = bool(config.get("api", {}).get("api_key"))

    print(f"\n  {BOLD}🎉 欢迎使用售前架构师工具箱{RESET}\n")

    if not has_key:
        print(f"  {YELLOW}你还没有配置 API，需要 30 秒完成初始化:{RESET}")
        print(f"  运行: {BLUE}sa config{RESET}\n")
    else:
        print(f"  {GREEN}✓ API 已配置{RESET}")
        print(f"  {GREEN}✓ 准备就绪{RESET}\n")

    print(f"  {BOLD}试试这些命令:{RESET}")
    print(f"    {BLUE}sa lead-score{RESET}     评估一个商机值不值得跟进")
    print(f"    {BLUE}sa news{RESET}           看看今天 AI 行业发生了什么")
    print(f"    {BLUE}sa help{RESET}           查看所有命令")
    print()


def cmd_config(args, flags=None):
    """Configure API and personal info."""
    config = load_config()
    flags = flags or {}

    if "--show" in args or flags.get("show"):
        print(f"\n  {BOLD}当前配置:{RESET}\n")
        print(show_config(config))
        print()
        return

    print_header("配置售前架构师工具箱")

    try:
        import questionary

        # API config
        print(f"  {BOLD}API 连接配置:{RESET}\n")
        base_url = questionary.text(
            "API 端点 Base URL:",
            default=config["api"]["base_url"],
        ).ask()

        api_key = questionary.password(
            "API Key:",
        ).ask()
        if not api_key:
            api_key = config["api"]["api_key"]

        model = questionary.select(
            "模型:",
            choices=[
                "claude-sonnet-4-6",
                "claude-opus-4-7",
                "claude-haiku-4-5",
                "deepseek-v4-pro",
            ],
            default=config["api"]["model"],
        ).ask()

        config["api"]["base_url"] = base_url
        config["api"]["api_key"] = api_key
        config["api"]["model"] = model

        # Personal info
        print(f"\n  {BOLD}个人信息 (可选):{RESET}\n")
        name = questionary.text("姓名:", default=config["architect"]["name"]).ask()
        company = questionary.text("公司:", default=config["architect"]["company"]).ask()

        config["architect"]["name"] = name
        config["architect"]["company"] = company

    except ImportError:
        # Fallback to plain input
        print("  (questionary 未安装，使用基础输入)\n")

        base_url = input(f"  API 端点 [{config['api']['base_url']}]: ").strip()
        if base_url:
            config["api"]["base_url"] = base_url

        api_key = input("  API Key: ").strip()
        if api_key:
            config["api"]["api_key"] = api_key

        model = input(f"  模型 [{config['api']['model']}]: ").strip()
        if model:
            config["api"]["model"] = model

        name = input(f"  姓名 [{config['architect']['name']}]: ").strip()
        if name:
            config["architect"]["name"] = name

        company = input(f"  公司 [{config['architect']['company']}]: ").strip()
        if company:
            config["architect"]["company"] = company

    save_config(config)
    print(f"\n  {GREEN}✓ 配置已保存到 {CONFIG_FILE}{RESET}\n")


def cmd_status():
    """Check skill installation status."""
    print_header("Skill 安装状态")

    skills_dir = Path.home() / ".workbuddy" / "skills"
    skills = [
        ("lead-scoring", "线索打分"),
        ("ai-daily-news", "AI早报"),
        ("kpmg-strategy-framework", "KPMG战略框架"),
        ("tian-dao-tui-yan-skill", "天道推演"),
        ("solution-architect-expert", "方案设计"),
        ("business-decision-tool", "商业决策"),
        ("fullstack-design-studio", "全栈开发"),
        ("system-awakening", "技能树学习"),
    ]

    installed = 0
    for name, desc in skills:
        path = skills_dir / name
        if path.exists():
            print(f"  {GREEN}✓{RESET} {name:<32} {desc}")
            installed += 1
        else:
            print(f"  {RED}✗{RESET} {name:<32} {desc} (未安装)")

    print(f"\n  {BOLD}{installed}/8 skill 已安装{RESET}")
    if installed < 8:
        print(f"  运行 {BLUE}bash ~/.workbuddy/skills/sales-architect/install.sh{RESET} 安装缺失 skill\n")
    else:
        print()

    # Check coding tools
    tools = detect_tools()
    print(f"  {BOLD}Coding 工具:{RESET}")
    if tools["claude"]:
        print(f"  {GREEN}✓{RESET} Claude Code")
    else:
        print(f"  {DIM}✗{RESET} Claude Code (未安装)")
    if tools["workbuddy"]:
        print(f"  {GREEN}✓{RESET} WorkBuddy")
    else:
        print(f"  {DIM}✗{RESET} WorkBuddy (未安装)")
    print()


def cmd_docs():
    """Open output directory."""
    config = load_config()
    out_dir = config.get("defaults", {}).get("output_dir", str(Path.home() / "sales-architect-outputs"))
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    import subprocess
    if sys.platform == "darwin":
        subprocess.run(["open", out_dir], capture_output=True)
        print(f"  {GREEN}✓{RESET} 已打开: {out_dir}")
    else:
        print(f"  输出目录: {out_dir}")


def cmd_history(args, flags):
    """Show command execution history."""
    if "--clear" in args or flags.get("clear"):
        clear_history()
        print(f"\n  {GREEN}✓{RESET} 历史记录已清空\n")
        return

    show_history()


def cmd_cache(args, flags):
    """Manage LLM response cache."""
    if "--clear" in args or flags.get("clear"):
        cache = get_cache()
        count = cache.clear()
        print(f"\n  {GREEN}✓{RESET} 已清空 {count} 个缓存文件\n")
        return

    if "--info" in args or flags.get("info") or not args:
        cache = get_cache()
        stats = cache.get_stats()

        print_header("LLM 缓存统计")
        print(f"  缓存目录: {stats['cache_dir']}")
        print(f"  缓存条目: {stats['total_entries']}")
        print(f"  实际文件: {stats['actual_files']}")
        print(f"  总大小: {stats['total_size_mb']} MB ({stats['total_size_bytes']} bytes)")

        if stats['oldest_entry']:
            print(f"  最早缓存: {stats['oldest_entry']}")

        if stats['most_accessed']:
            most = stats['most_accessed']
            print(f"  最常访问: 访问 {most['access_count']} 次")
            print(f"            创建于 {most['created']}")
            print(f"            最后访问 {most['last_access']}")

        print()
        return

    print(f"\n  {YELLOW}!{RESET} 未知缓存命令: {args}")
    print(f"  使用 {BLUE}sa cache --info{RESET} 查看统计")
    print(f"  使用 {BLUE}sa cache --clear{RESET} 清空缓存\n")


def cmd_update():
    """Update all skill repos."""
    print_header("更新 Skill")

    skills_dir = Path.home() / ".workbuddy" / "skills"
    import subprocess

    repos = [
        "tian-dao-tui-yan-skill",
        "system-awakening",
        "kpmg-strategy-framework",
        "ai-daily-news",
        "business-decision-tool",
        "lead-scoring",
        "fullstack-design-studio",
        "solution-architect-expert",
    ]

    for repo in repos:
        repo_dir = skills_dir / repo
        if repo_dir.exists() and (repo_dir / ".git").exists():
            result = subprocess.run(
                ["git", "-C", str(repo_dir), "pull", "--ff-only"],
                capture_output=True, text=True,
            )
            if result.returncode == 0:
                if "Already up to date" in result.stdout:
                    print(f"  {GREEN}✓{RESET} {repo} (已是最新)")
                else:
                    print(f"  {GREEN}✓{RESET} {repo} (已更新)")
            else:
                print(f"  {RED}✗{RESET} {repo} ({result.stderr.strip()[:50]})")
        elif repo_dir.exists():
            print(f"  {YELLOW}!{RESET} {repo} (非 git 仓库，跳过)")
        else:
            print(f"  {DIM}✗{RESET} {repo} (未安装)")

    print()


def cmd_skill(subcommand, args, flags, existing_context=None):
    """Run a skill command (lead-score, news, strategy, etc.).

    Args:
        subcommand: Command name
        args: Positional arguments
        flags: Parsed flags
        existing_context: Context from previous workflow steps (for context passing)

    Returns:
        dict: Updated context (for workflow chaining)
    """
    global _partial_output

    config = load_config()

    # Check API key
    if not config.get("api", {}).get("api_key"):
        print(f"\n  {RED}✗ API Key 未配置{RESET}")
        print(f"  运行 {BLUE}sa config{RESET} 配置 API\n")
        return existing_context or {}

    # Load command definition
    cmd_def = load_command(subcommand)
    if not cmd_def:
        print(f"\n  {RED}✗ 未知命令: {subcommand}{RESET}")
        print(f"  运行 {BLUE}sa help{RESET} 查看可用命令\n")
        return existing_context or {}

    # Determine execution mode
    mode = cmd_def["mode"]
    tool_override = flags.get("tool")
    output_only = flags.get("output-only", False)
    plain = flags.get("plain", False)

    if tool_override:
        mode = "enhanced"
    elif output_only:
        mode = "output-only"

    # Interactive context collection — pass existing_context for workflow chaining
    context = collect_context(cmd_def, args, existing_context)

    # Render prompt
    prompt = render_prompt(cmd_def, context, config)

    if output_only or mode == "output-only":
        prompt_file = Path(tempfile.gettempdir()) / f"sa-{subcommand}-{context.get('customer_name', 'task')}.md"
        prompt_file.write_text(
            f"# System\n\n{prompt['system']}\n\n# User\n\n{prompt['user']}",
            encoding="utf-8",
        )
        print(f"\n  {GREEN}✓{RESET} Prompt 已生成: {prompt_file}")
        print(f"  复制到任意 AI 工具执行即可\n")
        log_history(subcommand, context, str(prompt_file))
        return context

    if mode == "enhanced":
        prompt_file = Path(tempfile.gettempdir()) / f"sa-{subcommand}-{context.get('customer_name', 'task')}.md"
        prompt_file.write_text(
            f"# System\n\n{prompt['system']}\n\n# User\n\n{prompt['user']}",
            encoding="utf-8",
        )

        tools = detect_tools()
        if tool_override == "claude" or tools.get("claude"):
            print(f"\n  {BLUE}ℹ 使用 Claude Code 执行...{RESET}\n")
            run_claude(str(prompt_file))
        elif tool_override == "workbuddy" or tools.get("workbuddy"):
            print(f"\n  {BLUE}ℹ 使用 WorkBuddy 执行...{RESET}\n")
            run_workbuddy(str(prompt_file))
        else:
            print(suggest_install())
            print(f"  Prompt 已保存: {prompt_file}")
        log_history(subcommand, context, str(prompt_file))
        return context

    # Built-in mode: call LLM API directly
    api = config["api"]
    out_dir = config.get("defaults", {}).get("output_dir", str(Path.home() / "sales-architect-outputs"))

    # Check cache first (only if cache is enabled and not in plain mode)
    cache_hit = False
    if is_cache_enabled() and not plain:
        cache = get_cache()
        messages = [
            {"role": "system", "content": prompt["system"]},
            {"role": "user", "content": prompt["user"]}
        ]
        cached_response = cache.get(messages, api["model"], 0.7)

        if cached_response:
            result = cached_response.get("text", "")
            cache_hit = True
            if not plain:
                print(f"\n  {GREEN}⚡ 缓存命中{RESET} (跳过 API 调用)\n")
                print(f"  {'─' * 50}")

    # If no cache hit, call API
    if not cache_hit:
        if not plain:
            print(f"\n  {DIM}⏳ 正在分析中...{RESET}\n")
            print(f"  {'─' * 50}")

        def on_chunk(text):
            global _partial_output
            _partial_output += text
            if plain:
                sys.stdout.write(format_plain(text))
            else:
                display_streaming(text)

        result = call_llm_streaming(
            base_url=api["base_url"],
            api_key=api["api_key"],
            model=api["model"],
            system=prompt["system"],
            user=prompt["user"],
            on_chunk=on_chunk,
        )

        # Save to cache if successful
        if is_cache_enabled() and not result.startswith("❌"):
            cache = get_cache()
            messages = [
                {"role": "system", "content": prompt["system"]},
                {"role": "user", "content": prompt["user"]}
            ]
            cache.set(messages, api["model"], 0.7, {"text": result})

    if not plain:
        print(f"\n  {'─' * 50}")

    if result.startswith("❌"):
        print(f"\n  {result}\n")
        return context

    # Save output
    filepath = save_output(result, subcommand, context, out_dir)

    # Log to history
    log_history(subcommand, context, filepath)

    if not plain:
        print(f"\n  {GREEN}✓{RESET} 已保存到: {filepath}\n")

    return context


def cmd_workflow(name, args, flags):
    """Run a workflow (cycle, rfp, compete).

    Context is passed between steps: step 1's context is injected into step 2,
    so users only answer NEW questions in later steps.
    """
    wf = load_workflow(name)
    if not wf:
        print(f"\n  {RED}✗ 未知工作流: {name}{RESET}\n")
        return

    print_header(f"工作流: {wf['name']}")
    print(f"  {DIM}{wf['description']}{RESET}\n")

    steps = wf.get("steps", [])
    if not steps:
        print(f"  {YELLOW}工作流定义不完整{RESET}\n")
        return

    # Handle RFP file reading
    rfp_content = None
    if name == "rfp" and args:
        rfp_path = Path(args[0])
        if rfp_path.exists():
            rfp_content = read_rfp_file(rfp_path)
            print(f"  {GREEN}✓{RESET} 已读取 RFP 文件: {rfp_path.name} ({len(rfp_content)} 字符)")
            args = []  # Clear args since we've consumed the file path
        else:
            print(f"  {RED}✗{RESET} 文件不存在: {args[0]}\n")
            return

    print(f"  {BOLD}将依次执行 {len(steps)} 个步骤:{RESET}")
    for i, step in enumerate(steps, 1):
        step = step.strip()
        print(f"    {BLUE}{i}.{RESET} {step}")
    print()

    # Shared context across workflow steps
    shared_context = {}
    if rfp_content:
        shared_context["rfp_content"] = rfp_content
        shared_context["core_need"] = f"基于以下 RFP 文档的核心需求:\n\n{rfp_content[:500]}"

    for i, step in enumerate(steps, 1):
        step = step.strip()
        print(f"\n  {BOLD}━━━ 步骤 {i}/{len(steps)}: {step} ━━━{RESET}")
        # Pass shared_context so later steps reuse earlier answers
        returned_context = cmd_skill(step, args, flags, existing_context=shared_context)
        # Merge returned context into shared context for next step
        if returned_context:
            shared_context.update(returned_context)


# ═══════════════════════════════════════════════════
# Interactive context collection
# ═══════════════════════════════════════════════════

def collect_context(cmd_def: dict, args: list, existing_context: dict = None) -> dict:
    """Collect context via interactive questions.

    Args:
        cmd_def: Command definition with questions
        args: Positional arguments
        existing_context: Context from previous workflow steps (keys that exist are skipped)

    Returns:
        dict: Complete context for this command
    """
    context = {}
    questions = cmd_def.get("questions", [])

    # Pre-fill from existing context (workflow chaining)
    if existing_context:
        for q in questions:
            if q["key"] in existing_context and existing_context[q["key"]]:
                context[q["key"]] = existing_context[q["key"]]

    # Map positional args to remaining questions
    remaining_questions = [q for q in questions if q["key"] not in context]
    for i, arg in enumerate(args):
        if i < len(remaining_questions):
            context[remaining_questions[i]["key"]] = arg

    # Ask only questions not already answered
    try:
        import questionary
        has_q = True
    except ImportError:
        has_q = False

    for q in questions:
        if q["key"] in context:
            continue

        if has_q:
            if q["type"] == "select":
                import re
                choices_match = re.search(r"\[([^\]]+)\]", q["text"])
                if choices_match:
                    choices = [c.strip() for c in choices_match.group(1).split("/")]
                    clean_text = re.sub(r"\s*\[[^\]]+\]", "", q["text"])
                    answer = questionary.select(clean_text + ":", choices=choices).ask()
                else:
                    answer = questionary.text(q["text"] + ":").ask()
            elif q["type"] == "multiline":
                answer = questionary.text(q["text"] + ":", multiline=True).ask()
            else:
                answer = questionary.text(q["text"] + ":").ask()
        else:
            answer = input(f"  ? {q['text']}: ").strip()

        context[q["key"]] = answer or ""

    return context


def read_rfp_file(filepath: Path) -> str:
    """Read RFP file content. Supports .md, .txt, .docx, .pdf."""
    suffix = filepath.suffix.lower()

    if suffix in (".md", ".txt", ".text"):
        return filepath.read_text(encoding="utf-8")

    if suffix == ".docx":
        try:
            import subprocess
            result = subprocess.run(
                ["python3", "-c", f"""
import zipfile, xml.etree.ElementTree as ET
doc = zipfile.ZipFile("{filepath}")
xml_content = doc.read("word/document.xml")
tree = ET.fromstring(xml_content)
ns = {{"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}}
texts = [t.text for t in tree.iter("{{http://schemas.openxmlformats.org/wordprocessingml/2006/main}}t") if t.text]
print("\\n".join(texts))
"""],
                capture_output=True, text=True, timeout=10,
            )
            return result.stdout.strip() if result.returncode == 0 else f"[无法读取 .docx 文件: {filepath.name}]"
        except Exception:
            return f"[无法读取 .docx 文件: {filepath.name}]"

    if suffix == ".pdf":
        try:
            import subprocess
            result = subprocess.run(
                ["python3", "-c", f"""
import subprocess
r = subprocess.run(["pdftotext", "{filepath}", "-"], capture_output=True, text=True)
print(r.stdout)
"""],
                capture_output=True, text=True, timeout=10,
            )
            return result.stdout.strip() if result.returncode == 0 else f"[无法读取 .pdf 文件: {filepath.name}，请安装 pdftotext]"
        except Exception:
            return f"[无法读取 .pdf 文件: {filepath.name}]"

    # Fallback: try reading as text
    try:
        return filepath.read_text(encoding="utf-8")
    except Exception:
        return f"[无法读取文件: {filepath.name}]"


# ═══════════════════════════════════════════════════
# Main router
# ═══════════════════════════════════════════════════

COMMANDS = {
    "lead-score", "news", "briefing", "strategy", "simulate",
    "solution", "decide", "build", "learn",
}

WORKFLOWS = {
    "cycle", "rfp", "compete",
}

AUX = {
    "help", "config", "status", "update", "docs", "history", "cache",
}


def main():
    argv = sys.argv[1:]

    # Parse flags
    flags = {}
    positional = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--plain":
            flags["plain"] = True
        elif arg == "--tool":
            i += 1
            flags["tool"] = argv[i] if i < len(argv) else "claude"
        elif arg.startswith("--tool="):
            flags["tool"] = arg.split("=", 1)[1]
        elif arg == "--output-only":
            flags["output-only"] = True
        elif arg.startswith("--"):
            flags[arg.lstrip("-")] = True
        else:
            positional.append(arg)
        i += 1

    subcommand = positional[0] if positional else None
    sub_args = positional[1:] if len(positional) > 1 else []

    if subcommand is None:
        cmd_welcome()
    elif subcommand in AUX:
        if subcommand == "help":
            cmd_help()
        elif subcommand == "config":
            cmd_config(sub_args, flags)
        elif subcommand == "status":
            cmd_status()
        elif subcommand == "update":
            cmd_update()
        elif subcommand == "docs":
            cmd_docs()
        elif subcommand == "history":
            cmd_history(sub_args, flags)
        elif subcommand == "cache":
            cmd_cache(sub_args, flags)
    elif subcommand in COMMANDS:
        cmd_skill(subcommand, sub_args, flags)
    elif subcommand in WORKFLOWS:
        cmd_workflow(subcommand, sub_args, flags)
    else:
        print(f"\n  {RED}✗ 未知命令: {subcommand}{RESET}")
        print(f"  运行 {BLUE}sa help{RESET} 查看可用命令\n")


if __name__ == "__main__":
    main()
