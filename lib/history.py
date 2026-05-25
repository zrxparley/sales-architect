"""
Command execution history tracking.
Logs each command to ~/.sa-history.json for later review.
"""

import json
from datetime import datetime
from pathlib import Path

HISTORY_FILE = Path.home() / ".sa-history.json"


def log_history(command: str, context: dict, output_file: str) -> None:
    """Log a command execution to history."""
    history = _load_history()

    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "command": command,
        "customer_name": context.get("customer_name", ""),
        "industry": context.get("industry", ""),
        "topic": context.get("topic", ""),
        "competitor": context.get("competitor", ""),
        "output_file": output_file,
    }

    history.append(entry)

    # Keep last 100 entries
    if len(history) > 100:
        history = history[-100:]

    HISTORY_FILE.write_text(
        json.dumps(history, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def show_history(filter_cmd: str = None, filter_customer: str = None, limit: int = 20) -> None:
    """Display command history."""
    history = _load_history()

    if not history:
        print("\n  暂无历史记录\n")
        return

    # Apply filters
    if filter_cmd:
        history = [h for h in history if h.get("command") == filter_cmd]
    if filter_customer:
        history = [h for h in history if filter_customer.lower() in h.get("customer_name", "").lower()]

    # Show recent entries
    entries = history[-limit:]

    print(f"\n  \033[1m最近 {len(entries)} 条记录:\033[0m\n")

    for entry in reversed(entries):
        ts = entry.get("timestamp", "")[:16].replace("T", " ")
        cmd = entry.get("command", "?")
        customer = entry.get("customer_name", "")
        industry = entry.get("industry", "")
        output = entry.get("output_file", "")

        label = customer or entry.get("topic", "") or "—"
        detail = f" ({industry})" if industry else ""

        print(f"  {ts}  {cmd:<14} {label}{detail}")
        if output:
            print(f"  {' ' * 16} → {output}")
        print()

    if len(history) > limit:
        print(f"  (还有 {len(history) - limit} 条更早的记录，使用 --limit 查看更多)\n")


def clear_history() -> None:
    """Clear all history."""
    HISTORY_FILE.write_text("[]\n", encoding="utf-8")


def _load_history() -> list:
    """Load history from file."""
    if not HISTORY_FILE.exists():
        return []

    try:
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []
