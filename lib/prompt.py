"""
Prompt template loading and context injection.
"""

import re
from pathlib import Path

SA_HOME = Path(__file__).parent.parent
COMMANDS_DIR = SA_HOME / "commands"
WORKFLOWS_DIR = SA_HOME / "workflows"
TEMPLATES_DIR = SA_HOME / "templates"


def load_command(name: str) -> dict:
    """Load a command definition from commands/<name>.md.

    Returns dict with keys: name, description, mode, questions, system_prompt, user_template
    """
    path = COMMANDS_DIR / f"{name}.md"
    if not path.exists():
        return None

    content = path.read_text(encoding="utf-8")

    # Parse YAML frontmatter
    meta = {}
    body = content
    fm_match = re.match(r"^---\n(.*?)\n---\n(.*)$", content, re.DOTALL)
    if fm_match:
        for line in fm_match.group(1).split("\n"):
            if ":" in line:
                key, val = line.split(":", 1)
                meta[key.strip()] = val.strip().strip('"').strip("'")
        body = fm_match.group(2).strip()

    # Parse questions section
    questions = []
    q_match = re.search(r"## Questions\n(.*?)(?=\n## |\Z)", body, re.DOTALL)
    if q_match:
        for line in q_match.group(1).strip().split("\n"):
            line = line.strip()
            if line.startswith("- "):
                qm = re.match(r"- (\w+):\s*(.+?)(?:\s*\[(\w+)\])?$", line)
                if qm:
                    questions.append({
                        "key": qm.group(1),
                        "text": qm.group(2).strip(),
                        "type": qm.group(3) or "text",
                    })

    # Parse system prompt
    system = ""
    sys_match = re.search(r"## System\n(.*?)(?=\n## |\Z)", body, re.DOTALL)
    if sys_match:
        system = sys_match.group(1).strip()

    # Parse user template
    user_tmpl = ""
    usr_match = re.search(r"## User Template\n(.*?)(?=\n## |\Z)", body, re.DOTALL)
    if usr_match:
        user_tmpl = usr_match.group(1).strip()

    return {
        "name": meta.get("name", name),
        "description": meta.get("description", ""),
        "mode": meta.get("mode", "builtin"),
        "skill_ref": meta.get("skill_ref", ""),
        "questions": questions,
        "system_prompt": system,
        "user_template": user_tmpl,
    }


def load_workflow(name: str) -> dict:
    """Load a workflow definition from workflows/<name>.md."""
    path = WORKFLOWS_DIR / f"{name}.md"
    if not path.exists():
        return None

    content = path.read_text(encoding="utf-8")
    meta = {}
    fm_match = re.match(r"^---\n(.*?)\n---\n(.*)$", content, re.DOTALL)
    if fm_match:
        for line in fm_match.group(1).split("\n"):
            if ":" in line:
                key, val = line.split(":", 1)
                meta[key.strip()] = val.strip().strip('"').strip("'")

    return {
        "name": meta.get("name", name),
        "description": meta.get("description", ""),
        "steps": meta.get("steps", "").split(","),
        "content": content,
    }


def render_prompt(cmd_def: dict, context: dict, config: dict) -> dict:
    """Render System and User prompts with context and config.

    Returns: {"system": str, "user": str}
    """
    system = cmd_def["system_prompt"]
    user_tmpl = cmd_def["user_template"]

    # Inject config context
    arch = config.get("architect", {})
    config_block = ""
    if arch.get("name"):
        config_block += f"售前架构师: {arch['name']}\n"
    if arch.get("company"):
        config_block += f"所属公司: {arch['company']}\n"
    if arch.get("title"):
        config_block += f"职位: {arch['title']}\n"

    if config_block:
        system = f"## 当前用户信息\n{config_block}\n---\n\n{system}"

    # Replace placeholders in user template: {{key}}
    user = user_tmpl
    for key, val in context.items():
        user = user.replace("{{" + key + "}}", str(val))

    return {"system": system, "user": user}


def list_commands() -> list:
    """List all available commands."""
    commands = []
    if COMMANDS_DIR.exists():
        for f in sorted(COMMANDS_DIR.glob("*.md")):
            cmd = load_command(f.stem)
            if cmd:
                commands.append(cmd)
    return commands


def list_workflows() -> list:
    """List all available workflows."""
    workflows = []
    if WORKFLOWS_DIR.exists():
        for f in sorted(WORKFLOWS_DIR.glob("*.md")):
            wf = load_workflow(f.stem)
            if wf:
                workflows.append(wf)
    return workflows
