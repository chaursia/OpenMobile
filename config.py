"""
config.py — Central configuration for OpenMobile.
Loads environment variables from .env (if present) and exposes them as constants.
"""
import os
from pathlib import Path

# ── Load .env if available (graceful fallback if python-dotenv not installed) ──
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass  # python-dotenv optional; env vars can be exported manually

# ── Version ────────────────────────────────────────────────────────────────────
VERSION = "2.0.0"
PROJECT_NAME = "OpenMobile"

# ── Creator Info ────────────────────────────────────────────────────────────────
CREATOR = {
    "name": "Divyanshu Chaursia",
    "github": "https://github.com/chaursia",
    "project": "https://github.com/chaursia/OpenMobile",
    "telegram": "@divyanshuchaursia",
    "bug_report": "https://github.com/chaursia/OpenMobile/issues",
    "community": "https://neurodev.in",
}

# ── Ollama ──────────────────────────────────────────────────────────────────────
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")

# ── Models ──────────────────────────────────────────────────────────────────────
# Lightweight planner (text reasoning) — ~0.5 B params
PLANNER_MODEL = os.environ.get("PLANNER_MODEL", "qwen2.5:0.5b")
# Lightweight vision actor (screen analysis) — ~1.6 B params
VISION_MODEL = os.environ.get("VISION_MODEL", "moondream")

# ── Agent ───────────────────────────────────────────────────────────────────────
MAX_STEPS = int(os.environ.get("MAX_STEPS", "15"))
STEP_DELAY = float(os.environ.get("STEP_DELAY", "2.0"))   # seconds between steps
RETRY_LIMIT = int(os.environ.get("RETRY_LIMIT", "2"))      # retries per step on failure
# Planner confidence threshold: below this, defer to vision actor's coords
CONFIDENCE_THRESHOLD = float(os.environ.get("CONFIDENCE_THRESHOLD", "0.70"))
# Rolling memory window (last N steps included in prompts)
MEMORY_WINDOW = int(os.environ.get("MEMORY_WINDOW", "5"))

# ── Telegram ────────────────────────────────────────────────────────────────────
TG_API_ID = os.environ.get("TG_API_ID")
TG_API_HASH = os.environ.get("TG_API_HASH")
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
ALLOWED_USERS = [
    u.strip() for u in os.environ.get("ALLOWED_USERS", "").split(",") if u.strip()
]

# ── WhatsApp polling ─────────────────────────────────────────────────────────────
WA_POLL_INTERVAL = int(os.environ.get("WA_POLL_INTERVAL", "5"))  # seconds

# ── Debug ────────────────────────────────────────────────────────────────────────
DEBUG = os.environ.get("DEBUG", "0").strip().lower() in ("1", "true", "yes")

def log(msg: str, level: str = "INFO"):
    """Simple coloured terminal logger."""
    prefix = {
        "INFO":    "\033[94m[INFO]\033[0m",
        "SUCCESS": "\033[92m[OK]  \033[0m",
        "WARN":    "\033[93m[WARN]\033[0m",
        "ERROR":   "\033[91m[ERR] \033[0m",
        "DEBUG":   "\033[90m[DBG] \033[0m",
        "AGENT":   "\033[95m[AGNT]\033[0m",
        "PLAN":    "\033[96m[PLAN]\033[0m",
        "VISION":  "\033[93m[VISN]\033[0m",
        "ACTION":  "\033[92m[ACT] \033[0m",
    }.get(level.upper(), "[LOG] ")
    if level.upper() == "DEBUG" and not DEBUG:
        return
    print(f"{prefix} {msg}")
