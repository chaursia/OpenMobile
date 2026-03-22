"""
channels.py — Communication gateways for OpenMobile.

Supports:
  - Telegram (bot via Telethon)
  - WhatsApp (polling via Termux:API notifications)
"""
import asyncio
import json
import subprocess
import time
from config import (
    TG_API_ID, TG_API_HASH, TG_BOT_TOKEN,
    ALLOWED_USERS, WA_POLL_INTERVAL, log
)

try:
    from telethon import TelegramClient, events
    TELETHON_AVAILABLE = True
except ImportError:
    TELETHON_AVAILABLE = False
    log("telethon not installed — Telegram support disabled.", "WARN")


class CommunicationGateway:
    def __init__(self, agent_callback):
        """
        agent_callback(goal: str, report_func) → awaitable
        report_func(text: str, image_path: str | None = None) → awaitable
        """
        self.agent_callback = agent_callback
        self.tg_client = None
        self._wa_seen_ids: set = set()  # track processed WA notification IDs

        if TELETHON_AVAILABLE and all([TG_API_ID, TG_API_HASH, TG_BOT_TOKEN]):
            try:
                self.tg_client = TelegramClient(
                    "openmobile_session",
                    int(TG_API_ID),
                    TG_API_HASH,
                )
                log("Telegram client created.", "INFO")
            except Exception as e:
                log(f"Failed to create Telegram client: {e}", "ERROR")

    # ── Telegram ──────────────────────────────────────────────────────────────

    async def start_telegram(self):
        """Starts the Telegram bot listener."""
        if not self.tg_client:
            log("Telegram credentials missing or telethon not installed.", "WARN")
            return

        await self.tg_client.start(bot_token=TG_BOT_TOKEN)

        @self.tg_client.on(events.NewMessage)
        async def handler(event):
            sender_id = str(event.sender_id).strip()

            # Security: allowlist check
            if ALLOWED_USERS and sender_id not in ALLOWED_USERS:
                await event.reply("🚫 Unauthorized. Contact the device owner.")
                log(f"Rejected message from {sender_id}", "WARN")
                return

            msg_text = event.message.message.strip()

            if msg_text.startswith("/goal "):
                goal = msg_text[len("/goal "):].strip()
                if not goal:
                    await event.reply("⚠️ Usage: /goal <your task>")
                    return

                await event.reply(f"✅ Task received: {goal}\nStarting execution…")

                async def report(text: str, image_path: str = None):
                    try:
                        if image_path:
                            await event.reply(text, file=image_path)
                        else:
                            await event.reply(text)
                    except Exception as e:
                        log(f"TG report error: {e}", "WARN")

                try:
                    await self.agent_callback(goal, report)
                except Exception as e:
                    log(f"Agent error during TG task: {e}", "ERROR")
                    await event.reply(f"❌ Agent error: {e}")

            elif msg_text == "/status":
                await event.reply("🤖 OpenMobile is online and ready.\nSend /goal <task> to start.")

            elif msg_text == "/help":
                await event.reply(
                    "📖 *OpenMobile Help*\n\n"
                    "/goal <task> — Execute a task on the device\n"
                    "/status — Check if agent is online\n"
                    "/help — Show this message\n\n"
                    "Example: `/goal Open YouTube and search for lo-fi music`"
                )
            else:
                await event.reply(
                    "🤔 Unknown command. Try:\n"
                    "/goal <task>\n/status\n/help"
                )

        log("Telegram listener active. Waiting for commands…", "SUCCESS")
        await self.tg_client.run_until_disconnected()

    # ── WhatsApp (Termux:API polling) ─────────────────────────────────────────

    def _get_wa_notifications(self) -> list[dict]:
        """Fetches WhatsApp notifications via termux-notification-list."""
        try:
            result = subprocess.run(
                ["termux-notification-list"],
                capture_output=True, text=True, timeout=10
            )
            notifications = json.loads(result.stdout or "[]")
            return [n for n in notifications if n.get("packageName") == "com.whatsapp"]
        except Exception as e:
            log(f"WA notification fetch error: {e}", "WARN")
            return []

    async def start_whatsapp_polling(self):
        """
        Polls WhatsApp notifications every WA_POLL_INTERVAL seconds.
        Triggers the agent when a new /goal message arrives from an allowed sender.
        """
        log(f"WhatsApp polling started (interval={WA_POLL_INTERVAL}s).", "INFO")

        while True:
            notifs = self._get_wa_notifications()
            for notif in notifs:
                notif_id = notif.get("id", "")
                if notif_id in self._wa_seen_ids:
                    continue
                self._wa_seen_ids.add(notif_id)

                sender = notif.get("title", "").strip()
                content = notif.get("content", "").strip()

                # Security: allowlist check (WA uses display names, not IDs)
                if ALLOWED_USERS and sender not in ALLOWED_USERS:
                    continue

                if content.startswith("/goal "):
                    goal = content[len("/goal "):].strip()
                    if not goal:
                        continue
                    log(f"WhatsApp goal from {sender}: {goal}", "INFO")

                    async def wa_report(text: str, image_path: str = None):
                        log(f"[WA Report] {text}", "INFO")

                    try:
                        await self.agent_callback(goal, wa_report)
                    except Exception as e:
                        log(f"Agent error during WA task: {e}", "ERROR")

            await asyncio.sleep(WA_POLL_INTERVAL)
