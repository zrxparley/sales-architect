"""
Output formatting and file saving using Rich library.
"""

import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.live import Live
from rich.text import Text


# Global console instance
console = Console()


def print_header(title: str):
    """Print a styled header using Rich Panel."""
    console.print(Panel(f"[bold blue]{title}[/bold blue]",
                       style="blue",
                       width=60,
                       padding=(1, 2)))


def print_success(msg: str):
    """Print success message."""
    console.print(f"  [green]✓[/green] {msg}")


def print_warning(msg: str):
    """Print warning message."""
    console.print(f"  [yellow]![/yellow] {msg}")


def print_error(msg: str):
    """Print error message."""
    console.print(f"  [red]✗[/red] {msg}", style="red")


def print_info(msg: str):
    """Print info message."""
    console.print(f"  [blue]ℹ[/blue] {msg}")


def display_streaming(text: str):
    """Print text chunk for streaming display."""
    console.print(text, end="", highlight=False)
    console.file.flush()


def format_plain(text: str) -> str:
    """Strip markdown formatting for plain text output."""
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"__(.*?)__", r"\1", text)
    text = re.sub(r"_(.*?)_", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"```[\w]*\n?", "", text)
    text = re.sub(r"`(.*?)`", r"\1", text)
    return text.strip()


def format_terminal(text: str) -> str:
    """Convert markdown to Rich Markdown for terminal display."""
    # Rich handles markdown rendering, so we just return the text
    # The actual rendering happens in display_markdown()
    return text


def display_markdown(text: str):
    """Display markdown content using Rich Markdown."""
    md = Markdown(text)
    console.print(md)


def print_lead_score_report(score_data: dict):
    """Print a formatted lead score report using Rich Table."""
    # Create table
    table = Table(title="[bold blue]线索评估报告[/bold blue]",
                 show_header=True,
                 header_style="bold cyan",
                 width=80)

    table.add_column("维度", style="cyan", width=20)
    table.add_column("分数", style="green", justify="right", width=10)
    table.add_column("理由", style="white", width=50)

    # Add rows
    for dimension, data in score_data.get("dimensions", {}).items():
        score = data.get("score", 0)
        reason = data.get("reason", "")
        table.add_row(dimension, str(score), reason)

    # Print table
    console.print(table)

    # Print total score
    total = score_data.get("total_score", 0)
    recommendation = score_data.get("recommendation", "")

    console.print()
    console.print(Panel(
        f"[bold green]综合评分: {total}/100[/bold green]\n"
        f"[bold]建议: {recommendation}[/bold]",
        title="[bold]评估结果[/bold]",
        border_style="green",
        padding=(1, 2)
    ))

    # Print risks if present
    risks = score_data.get("risks", [])
    if risks:
        console.print()
        console.print("[bold yellow]⚠ 风险提示:[/bold yellow]")
        for i, risk in enumerate(risks, 1):
            console.print(f"  {i}. {risk}")


def print_strategy_report(strategy_data: dict):
    """Print a formatted strategy report using Rich."""
    # Main analysis
    console.print(Panel(
        f"[bold blue]战略分析报告[/bold blue]\n\n"
        f"[bold]客户:[/bold] {strategy_data.get('customer', 'N/A')}\n"
        f"[bold]行业:[/bold] {strategy_data.get('industry', 'N/A')}",
        border_style="blue"
    ))

    # Pain points
    pain_points = strategy_data.get("pain_points", [])
    if pain_points:
        console.print()
        console.print("[bold cyan]核心痛点:[/bold cyan]")
        for i, point in enumerate(pain_points, 1):
            console.print(f"  {i}. {point}")

    # Strategic options
    options = strategy_data.get("options", [])
    if options:
        console.print()
        console.print("[bold cyan]战略选项:[/bold cyan]")
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("选项", style="cyan", width=30)
        table.add_column("优势", style="green", width=25)
        table.add_column("风险", style="yellow", width=25)

        for option in options:
            table.add_row(
                option.get("name", ""),
                option.get("advantage", ""),
                option.get("risk", "")
            )
        console.print(table)


def create_live_display():
    """Create a Live display context for streaming output."""
    return Live("", console=console, refresh_per_second=4)


def update_live_display(live: Live, content: str):
    """Update the live display with new content."""
    live.update(content)


def save_output(text: str, command: str, context: dict, output_dir: str) -> str:
    """Save output to file. Returns the file path."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y%m%d")
    name_parts = [command]
    for key in ("customer_name", "industry", "topic", "competitor"):
        if key in context and context[key]:
            name_parts.append(context[key])
            break

    filename = "-".join(name_parts) + f"-{date_str}.md"
    filename = re.sub(r'[<>:"/\\|?*]', "_", filename)

    filepath = out / filename
    filepath.write_text(text, encoding="utf-8")
    return str(filepath)


# Keep old constants for backward compatibility
BOLD = "\033[1m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
RED = "\033[0;31m"
DIM = "\033[2m"
RESET = "\033[0m"
