import subprocess
import json
import time
import os
from telethon import TelegramClient, events

# Configuration for Telegram (User needs to fill these in)
API_ID = os.environ.get("TG_API_ID")
API_HASH = os.environ.get("TG_API_HASH")
BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
ALLOWED_USERS = os.environ.get("ALLOWED_USERS", "").split(",")

class CommunicationGateway:
    def __init__(self, agent_callback):
        self.agent_callback = agent_callback
        self.tg_client = None
        if API_ID and API_HASH and BOT_TOKEN:
            self.tg_client = TelegramClient('openmobile_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

    async def start_telegram(self):
        """Starts the Telegram listener."""
        if not self.tg_client:
            print("Telegram credentials missing. Skipping Telegram listener.")
            return

        @self.tg_client.on(events.NewMessage)
        async def handler(event):
            sender_id = str(event.sender_id)
            if sender_id not in ALLOWED_USERS:
                await event.reply("Unauthorized user.")
                return

            msg_text = event.message.message
            if msg_text.startswith("/goal "):
                goal = msg_text[len("/goal "):]
                await event.reply(f"Acknowledged. Starting task: {goal}")
                
                # Report callback to send updates back to TG
                async def report(text, image_path=None):
                    if image_path:
                        await event.reply(text, file=image_path)
                    else:
                        await event.reply(text)

                # Trigger Agent
                await self.agent_callback(goal, report)

        print("Telegram listener active.")
        await self.tg_client.run_until_disconnected()

    def check_whatsapp_notifications(self):
        """
        Monitors WhatsApp via termux-notification-list.
        Note: This is a polling-based approach since Termux doesn't have a direct WA API.
        """
        try:
            result = subprocess.run(["termux-notification-list"], capture_output=True, text=True)
            notifications = json.loads(result.stdout)
            
            for notif in notifications:
                if notif.get("packageName") == "com.whatsapp":
                    sender = notif.get("title")
                    content = notif.get("content")
                    
                    if sender in ALLOWED_USERS:
                        print(f"WhatsApp goal received from {sender}: {content}")
                        return content
        except Exception as e:
            print(f"Error checking WA notifications: {e}")
        return None

    def send_whatsapp_reply(self, recipient, message):
        """
        Replies to WhatsApp using ADB. 
        Note: This requires the screen to be on and WA to be accessible, or using a background strategy.
        Simplest version: Open WA, search for contact, type message.
        """
        print(f"Replying to WhatsApp ({recipient}): {message}")
        # Implementation depends on the 'actions.py' module
        pass

if __name__ == "__main__":
    # Example usage (standalone test)
    async def mock_agent(goal, report_func):
        await report_func(f"Processing: {goal}")
        time.sleep(2)
        await report_func("Task complete!")

    # gate = CommunicationGateway(mock_agent)
    # import asyncio
    # asyncio.run(gate.start_telegram())
