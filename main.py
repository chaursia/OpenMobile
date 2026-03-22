"""
main.py — Entry point for OpenMobile.

Modes:
  --dashboard          : Show TUI setup/status dashboard
  --headless           : Start Telegram (+ optionally WhatsApp) listener
  --headless --whatsapp: Enable WhatsApp polling alongside Telegram
  --goal "..."         : Run a single goal directly from CLI (testing)

Options:
  --planner-model      : Override planner model (default: qwen2.5:0.5b)
  --vision-model       : Override vision model (default: moondream)
  --max-steps N        : Override max agent steps
  --debug              : Enable verbose debug logging
"""
import argparse
import sys
import os
import asyncio

from config import (
    VERSION, PROJECT_NAME, TG_API_ID, TG_API_HASH, TG_BOT_TOKEN,
    PLANNER_MODEL, VISION_MODEL, MAX_STEPS, log
)


def print_startup_banner():
    print(f"\033[96m")
    print(r"  ___  _ __   ___ _ __ __  __       _     _ _      ")
    print(r" / _ \| '_ \ / _ \ '_ \  \/  | ___ | |__ (_) | ___ ")
    print(r"| | | | |_) |  __/ | | | |\/| |/ _ \| '_ \| | |/ _ \\")
    print(r"| |_| | .__/ \___|_| |_|_|  |_|\___/|_.__/|_|_|\___|")
    print(r" \___/|_|   Headless Android AI Agent")
    print(f"\033[0m")
    print(f"  Version \033[93m{VERSION}\033[0m  •  \033[90mneurodev.in\033[0m")
    print()


async def run_headless(agent, gateway, enable_whatsapp: bool):
    """Starts all listeners concurrently."""
    tasks = [gateway.start_telegram()]
    if enable_whatsapp:
        tasks.append(gateway.start_whatsapp_polling())
    log("OpenMobile is running in Headless Mode.", "SUCCESS")
    log("Send /goal <task> via Telegram to start.", "INFO")
    await asyncio.gather(*tasks)


def main():
    parser = argparse.ArgumentParser(
        description=f"OpenMobile v{VERSION} — Autonomous Android AI Agent",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dashboard", action="store_true",
        help="Show the TUI setup/status dashboard"
    )
    mode.add_argument(
        "--headless", action="store_true",
        help="Run as a Telegram/WhatsApp controlled service"
    )
    mode.add_argument(
        "--goal", type=str, metavar="GOAL",
        help="Run a single goal directly from CLI"
    )

    parser.add_argument(
        "--whatsapp", action="store_true",
        help="Enable WhatsApp notification polling (use with --headless)"
    )
    parser.add_argument(
        "--planner-model", type=str, default=PLANNER_MODEL,
        help=f"Planner LLM model (default: {PLANNER_MODEL})"
    )
    parser.add_argument(
        "--vision-model", type=str, default=VISION_MODEL,
        help=f"Vision Actor model (default: {VISION_MODEL})"
    )
    parser.add_argument(
        "--max-steps", type=int, default=MAX_STEPS,
        help=f"Maximum agent steps per goal (default: {MAX_STEPS})"
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Enable verbose debug output"
    )

    args = parser.parse_args()

    # ── Debug flag ─────────────────────────────────────────────────────────────
    if args.debug:
        os.environ["DEBUG"] = "1"

    print_startup_banner()

    # ── Dashboard mode ──────────────────────────────────────────────────────────
    if args.dashboard:
        try:
            from dashboard import run_dashboard
            log("Starting dashboard…", "INFO")
            run_dashboard()
        except ImportError:
            log("'rich' not installed. Run: pip install rich", "ERROR")
            sys.exit(1)
        return

    # ── Headless mode ───────────────────────────────────────────────────────────
    if args.headless:
        if not all([TG_API_ID, TG_API_HASH, TG_BOT_TOKEN]):
            log(
                "Headless mode requires TG_API_ID, TG_API_HASH, TG_BOT_TOKEN env vars.\n"
                "  Copy .env.example to .env and fill in your credentials.",
                "ERROR"
            )
            sys.exit(1)

        from agent import OpenMobileAgent
        from channels import CommunicationGateway

        agent = OpenMobileAgent(
            planner_model=args.planner_model,
            vision_model=args.vision_model,
        )

        async def agent_callback(goal, report_func):
            await agent.run(goal, report_func, max_steps=args.max_steps)

        gateway = CommunicationGateway(agent_callback)
        asyncio.run(run_headless(agent, gateway, args.whatsapp))
        return

    # ── CLI goal mode ───────────────────────────────────────────────────────────
    if args.goal:
        from agent import OpenMobileAgent

        agent = OpenMobileAgent(
            planner_model=args.planner_model,
            vision_model=args.vision_model,
        )

        async def cli_report(text: str, image_path: str = None):
            print(f"  {text}")
            if image_path:
                print(f"  📸 Screenshot saved: {image_path}")

        asyncio.run(agent.run(args.goal, cli_report, max_steps=args.max_steps))
        return

    # ── No mode selected ────────────────────────────────────────────────────────
    parser.print_help()
    print()
    log("Tip: run `python main.py --dashboard` to see setup status.", "INFO")


if __name__ == "__main__":
    main()
