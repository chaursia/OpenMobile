"""
dashboard.py — Termux TUI Dashboard for OpenMobile.
Built with `rich` — works in Termux with no native dependencies.

Launch: python main.py --dashboard
"""
import time
import subprocess
import requests
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.align import Align
from rich import box
from config import (
    VERSION, PROJECT_NAME, CREATOR,
    OLLAMA_URL, PLANNER_MODEL, VISION_MODEL,
    ALLOWED_USERS, MAX_STEPS, TG_API_ID,
    log
)

console = Console()

BANNER = r"""
  ___  _ __   ___ _ __ __  __       _     _ _
 / _ \| '_ \ / _ \ '_ \  \/  | ___ | |__ (_) | ___
| | | | |_) |  __/ | | | |\/| |/ _ \| '_ \| | |/ _ \
| |_| | .__/ \___|_| |_|_|  |_|\___/|_.__/|_|_|\___|
 \___/|_|   Headless Android AI Agent
"""


# ── Health Checks ──────────────────────────────────────────────────────────────

def check_adb() -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["adb", "devices"], capture_output=True, text=True, timeout=8
        )
        lines = [
            l.strip() for l in result.stdout.splitlines()
            if l.strip() and not l.startswith("List")
        ]
        connected = [l for l in lines if "device" in l and "offline" not in l]
        if connected:
            device_id = connected[0].split("\t")[0]
            return True, device_id
        return False, "No device connected"
    except FileNotFoundError:
        return False, "adb not found in PATH"
    except Exception as e:
        return False, str(e)


def check_ollama() -> tuple[bool, str]:
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if resp.status_code == 200:
            return True, "Running"
        return False, f"HTTP {resp.status_code}"
    except requests.ConnectionError:
        return False, "Not running (start with `ollama serve`)"
    except Exception as e:
        return False, str(e)


def check_model(model_name: str) -> tuple[bool, str]:
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if resp.status_code == 200:
            models = [m["name"] for m in resp.json().get("models", [])]
            # Match by prefix (e.g. "qwen2.5:0.5b" matches "qwen2.5:0.5b")
            for m in models:
                if m.startswith(model_name.split(":")[0]):
                    return True, m
            return False, f"Not pulled  (run: `ollama pull {model_name}`)"
    except Exception:
        pass
    return False, "Ollama unreachable"


# ── Renderables ────────────────────────────────────────────────────────────────

def make_banner() -> Panel:
    text = Text(BANNER, style="bold cyan", justify="left")
    version_line = Text(f"  Version {VERSION}  •  neurodev.in", style="dim cyan")
    from rich.console import Group
    return Panel(
        Align.center(Group(text, version_line)),
        border_style="cyan",
        padding=(0, 2),
    )


def make_setup_panel() -> Panel:
    adb_ok, adb_msg = check_adb()
    ollama_ok, ollama_msg = check_ollama()
    planner_ok, planner_msg = check_model(PLANNER_MODEL)
    vision_ok, vision_msg = check_model(VISION_MODEL)
    tg_ok = bool(TG_API_ID)

    def status(ok: bool, msg: str) -> Text:
        icon = "✅" if ok else "❌"
        color = "green" if ok else "red"
        return Text(f"{icon} {msg}", style=color)

    table = Table(box=None, show_header=False, padding=(0, 1))
    table.add_column("Item", style="bold white", min_width=22)
    table.add_column("Status")

    table.add_row("ADB Connection",       status(adb_ok,     adb_msg))
    table.add_row("Ollama Server",         status(ollama_ok,  ollama_msg))
    table.add_row(f"Planner ({PLANNER_MODEL})", status(planner_ok, planner_msg))
    table.add_row(f"Vision  ({VISION_MODEL})",  status(vision_ok,  vision_msg))
    table.add_row("Telegram Configured",   status(tg_ok,      "Yes" if tg_ok else "Set TG_API_ID env var"))

    return Panel(table, title="[bold yellow]🔌 Setup Status[/bold yellow]", border_style="yellow")


def make_config_panel() -> Panel:
    table = Table(box=None, show_header=False, padding=(0, 1))
    table.add_column("Key", style="bold white", min_width=20)
    table.add_column("Value", style="cyan")

    table.add_row("Ollama URL",       OLLAMA_URL)
    table.add_row("Planner Model",    PLANNER_MODEL)
    table.add_row("Vision Model",     VISION_MODEL)
    table.add_row("Max Steps",        str(MAX_STEPS))
    table.add_row("Allowed Users",    ", ".join(ALLOWED_USERS) or "[dim]All (no restriction)[/dim]")

    return Panel(table, title="[bold blue]⚙️  Config[/bold blue]", border_style="blue")


def make_usage_panel() -> Panel:
    lines = Text()
    lines.append("CLI Mode\n", style="bold white")
    lines.append("  python main.py --goal \"Open YouTube and search lo-fi\"\n", style="green")
    lines.append("  python main.py --goal \"Set alarm for 7 AM\"\n\n", style="green")
    lines.append("Headless Mode (Telegram)\n", style="bold white")
    lines.append("  python main.py --headless\n", style="green")
    lines.append("  Then send via Telegram:  /goal Open WhatsApp and message Mom\n\n", style="green")
    lines.append("WhatsApp Polling\n", style="bold white")
    lines.append("  python main.py --headless --whatsapp\n", style="green")
    lines.append("  Send via WA:  /goal Open Camera\n\n", style="green")
    lines.append("Setup Models (run once)\n", style="bold white")
    lines.append(f"  ollama pull {PLANNER_MODEL}\n", style="yellow")
    lines.append(f"  ollama pull {VISION_MODEL}\n", style="yellow")
    return Panel(lines, title="[bold green]📖 Usage Guide[/bold green]", border_style="green")


def make_creator_panel() -> Panel:
    lines = Text()
    lines.append(CREATOR["name"] + "\n", style="bold magenta")
    lines.append("\n")
    lines.append("🌐 Community:  ", style="dim")
    lines.append(CREATOR["community"] + "\n", style="cyan underline")
    lines.append("🐙 GitHub:     ", style="dim")
    lines.append(CREATOR["github"] + "\n", style="cyan underline")
    lines.append("📱 Telegram:   ", style="dim")
    lines.append(CREATOR["telegram"] + "\n", style="cyan underline")
    lines.append("\n")
    lines.append("🐛 Report a Bug\n", style="bold red")
    lines.append(CREATOR["bug_report"] + "\n", style="red underline")
    lines.append("\n")
    lines.append("📦 Project\n", style="bold white")
    lines.append(CREATOR["project"] + "\n", style="white underline")
    return Panel(lines, title="[bold magenta]👨‍💻 Creator & Contact[/bold magenta]", border_style="magenta")


def make_layout(memory=None) -> Table:
    """Builds the full dashboard layout."""
    root = Table.grid(expand=True)
    root.add_row(make_banner())

    # Row 1: Setup | Config
    row1 = Columns([make_setup_panel(), make_config_panel()], expand=True)
    root.add_row(row1)

    # Row 2: Usage | Creator
    row2 = Columns([make_usage_panel(), make_creator_panel()], expand=True)
    root.add_row(row2)

    # Row 3: Agent Status (if memory provided)
    if memory:
        status_color = {
            "idle": "dim", "running": "green",
            "done": "bold green", "failed": "bold red"
        }.get(memory.status, "white")

        agent_table = Table(box=None, show_header=False, padding=(0, 1))
        agent_table.add_column("Field", style="bold white", min_width=16)
        agent_table.add_column("Value")

        agent_table.add_row("Status",      Text(memory.status.upper(), style=status_color))
        agent_table.add_row("Goal",        memory.goal or "[dim]None[/dim]")
        agent_table.add_row("Steps Taken", str(memory.total_steps))
        agent_table.add_row("Last Action", memory.last_action or "[dim]—[/dim]")
        agent_table.add_row("Last Thought",
                            (memory.last_thought[:80] + "…") if len(memory.last_thought) > 80
                            else (memory.last_thought or "[dim]—[/dim]"))

        root.add_row(Panel(
            agent_table,
            title="[bold cyan]📊 Agent Status[/bold cyan]",
            border_style="cyan"
        ))

    return root


# ── Entry Point ────────────────────────────────────────────────────────────────

def run_dashboard(memory=None, refresh_secs: float = 2.0):
    """Runs the live-refreshing dashboard. Press Ctrl+C to exit."""
    console.clear()
    try:
        with Live(
            make_layout(memory),
            console=console,
            refresh_per_second=1 / refresh_secs,
            screen=True,
        ) as live:
            while True:
                time.sleep(refresh_secs)
                live.update(make_layout(memory))
    except KeyboardInterrupt:
        console.clear()
        console.print("[bold cyan]OpenMobile dashboard closed.[/bold cyan]")
