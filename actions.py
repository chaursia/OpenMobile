"""
actions.py — ADB action library for OpenMobile.
All hardware interactions go through this module.
Fixed bugs:
  - scroll() now uses detected resolution instead of hardcoded coords
  - wait() returns a coroutine-safe sentinel (actual sleep done in agent.py)
  - Added: long_press, back, home, recent_apps, clear_text, get_installed_apps, whatsapp_send
"""
import subprocess
import json
import time
from config import log


class ControllerModule:
    def __init__(self, resolution: tuple[int, int] = (1080, 2400)):
        self.resolution = resolution

    # ── Private ADB helper ───────────────────────────────────────────────────────

    def _run_adb(self, args: list, timeout: int = 15) -> str | None:
        command = ["adb", "shell"] + args
        try:
            result = subprocess.run(
                command, capture_output=True, text=True,
                check=True, timeout=timeout
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            log(f"ADB error: {e.stderr.strip()}", "ERROR")
            return None
        except subprocess.TimeoutExpired:
            log("ADB command timed out.", "ERROR")
            return None

    def _run_system(self, args: list, timeout: int = 15) -> str | None:
        """Runs a non-ADB-shell system command (e.g. adb pull, termux-*)."""
        try:
            result = subprocess.run(
                args, capture_output=True, text=True, timeout=timeout
            )
            return result.stdout.strip()
        except Exception as e:
            log(f"System command error: {e}", "ERROR")
            return None

    # ── Basic Input ──────────────────────────────────────────────────────────────

    def click(self, x: int, y: int) -> str | None:
        log(f"TAP ({x}, {y})", "ACTION")
        return self._run_adb(["input", "tap", str(x), str(y)])

    def long_press(self, x: int, y: int, duration: int = 800) -> str | None:
        """Long-press at (x, y) for `duration` ms."""
        log(f"LONG PRESS ({x}, {y}) for {duration}ms", "ACTION")
        # Swipe with zero movement = long press
        return self._run_adb(["input", "swipe",
                               str(x), str(y), str(x), str(y), str(duration)])

    def type_text(self, text: str) -> str | None:
        # ADB input text requires spaces as %s
        formatted = text.replace(" ", "%s").replace("'", "\\'")
        log(f"TYPE: {text}", "ACTION")
        return self._run_adb(["input", "text", formatted])

    def clear_text(self) -> None:
        """Selects all text in focused field and deletes it."""
        log("CLEAR TEXT", "ACTION")
        # Select all (Ctrl+A) then delete
        self._run_adb(["input", "keyevent", "--longpress", "29"])  # Ctrl+A
        self._run_adb(["input", "keyevent", "67"])                 # DEL

    # ── Navigation ───────────────────────────────────────────────────────────────

    def press_key(self, keycode: int) -> str | None:
        log(f"KEY: {keycode}", "ACTION")
        return self._run_adb(["input", "keyevent", str(keycode)])

    def back(self) -> str | None:
        log("BACK", "ACTION")
        return self._run_adb(["input", "keyevent", "4"])

    def home(self) -> str | None:
        log("HOME", "ACTION")
        return self._run_adb(["input", "keyevent", "3"])

    def recent_apps(self) -> str | None:
        log("RECENTS", "ACTION")
        return self._run_adb(["input", "keyevent", "187"])

    # ── Scroll / Swipe ──────────────────────────────────────────────────────────

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 400) -> str | None:
        log(f"SWIPE ({x1},{y1})→({x2},{y2})", "ACTION")
        return self._run_adb(["input", "swipe",
                               str(x1), str(y1), str(x2), str(y2), str(duration)])

    def scroll(self, direction: str = "down") -> str | None:
        """Scrolls using the device's actual resolution (not hardcoded coords)."""
        w, h = self.resolution
        cx = w // 2
        top = int(h * 0.20)
        bot = int(h * 0.75)
        log(f"SCROLL {direction.upper()} (res={w}x{h})", "ACTION")
        if direction == "down":
            return self.swipe(cx, bot, cx, top)
        else:
            return self.swipe(cx, top, cx, bot)

    # ── Apps ─────────────────────────────────────────────────────────────────────

    def open_app(self, package_name: str) -> str | None:
        log(f"OPEN APP: {package_name}", "ACTION")
        return self._run_adb([
            "monkey", "-p", package_name,
            "-c", "android.intent.category.LAUNCHER", "1"
        ])

    def get_installed_apps(self) -> list[str]:
        """Returns a list of installed package names."""
        result = self._run_adb(["pm", "list", "packages"])
        if not result:
            return []
        packages = [
            line.replace("package:", "").strip()
            for line in result.splitlines()
            if line.startswith("package:")
        ]
        log(f"Found {len(packages)} installed packages.", "DEBUG")
        return packages

    # ── Notification Reading ─────────────────────────────────────────────────────

    def read_notifications(self) -> list[dict]:
        """Reads notifications via Termux:API (requires termux-api package)."""
        try:
            result = self._run_system(["termux-notification-list"], timeout=10)
            if result:
                return json.loads(result)
        except Exception as e:
            log(f"Error reading notifications: {e}", "WARN")
        return []

    # ── WhatsApp (ADB-based) ──────────────────────────────────────────────────────

    def whatsapp_send(self, contact: str, message: str) -> bool:
        """
        Sends a WhatsApp message to `contact` via ADB UI automation.
        Opens WhatsApp, searches the contact, types and sends the message.
        This is best-effort — depends on screen state.
        """
        log(f"WHATSAPP → {contact}: {message[:40]}…", "ACTION")
        wa_pkg = "com.whatsapp"
        # 1. Open WhatsApp
        self.open_app(wa_pkg)
        time.sleep(2)
        # 2. Tap search (magnifier icon) — usually top-right area
        w, h = self.resolution
        self.click(int(w * 0.85), int(h * 0.04))
        time.sleep(1)
        # 3. Type contact name
        self.type_text(contact)
        time.sleep(2)
        # 4. Tap first result (approx)
        self.click(w // 2, int(h * 0.18))
        time.sleep(1)
        # 5. Tap message input bar (bottom center)
        self.click(int(w * 0.45), int(h * 0.95))
        time.sleep(0.5)
        # 6. Type message
        self.type_text(message)
        time.sleep(0.5)
        # 7. Tap send button (right of input bar)
        self.click(int(w * 0.93), int(h * 0.95))
        log(f"WhatsApp message sent to {contact}.", "SUCCESS")
        return True

    # ── Dispatcher ────────────────────────────────────────────────────────────────

    def perform_action(self, action_type: str, params: dict):
        """
        Generic dispatcher called by agent.py.
        Returns:
          - None       : action executed (or failed silently)
          - "WAIT"     : agent should await asyncio.sleep(seconds)
          - "FINISH"   : goal reached
        """
        action_type = action_type.lower()
        try:
            if action_type == "click":
                self.click(int(params.get("x", 0)), int(params.get("y", 0)))
            elif action_type == "long_press":
                self.long_press(int(params.get("x", 0)), int(params.get("y", 0)))
            elif action_type == "type":
                self.type_text(params.get("text", ""))
            elif action_type == "clear_text":
                self.clear_text()
            elif action_type == "scroll":
                self.scroll(params.get("direction", "down"))
            elif action_type == "swipe":
                self.swipe(
                    int(params.get("x1", 0)), int(params.get("y1", 0)),
                    int(params.get("x2", 0)), int(params.get("y2", 0)),
                    int(params.get("duration", 400)),
                )
            elif action_type == "open_app":
                self.open_app(params.get("package_name", ""))
            elif action_type == "press_key":
                self.press_key(int(params.get("keycode", 4)))
            elif action_type == "back":
                self.back()
            elif action_type == "home":
                self.home()
            elif action_type == "recent_apps":
                self.recent_apps()
            elif action_type == "wait":
                return ("WAIT", float(params.get("seconds", 2.0)))
            elif action_type == "finish":
                return "FINISH"
            else:
                log(f"Unknown action type: '{action_type}'", "WARN")
        except Exception as e:
            log(f"Action '{action_type}' raised exception: {e}", "ERROR")
        return None
