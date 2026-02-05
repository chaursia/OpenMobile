import argparse
import sys
import os
import asyncio
from agent import OpenMobileAgent
from channels import CommunicationGateway

async def run_headless(agent, gateway):
    """Starts the messenger listeners and waits for commands."""
    print("OpenMobile is running in Headless Mode.")
    print("Authorized Users can send /goal <task> via Telegram/WhatsApp.")
    
    # Start Telegram Listener
    await gateway.start_telegram()

def main():
    parser = argparse.ArgumentParser(description="OpenMobile - Autonomous Local Agent (Messenger Controlled)")
    parser.add_argument("--headless", action="store_true", help="Run as a messenger-controlled service")
    parser.add_argument("--goal", type=str, help="Direct goal command (for testing)")
    parser.add_argument("--model", type=str, default="llama3.2:3b", help="Reasoning model")
    parser.add_argument("--vision-model", type=str, default="llama3.2-vision", help="Vision model")
    
    args = parser.parse_args()

    # ENV Check for TG
    if args.headless:
        if not all([os.environ.get("TG_API_ID"), os.environ.get("TG_API_HASH"), os.environ.get("TG_BOT_TOKEN")]):
            print("Error: Headless mode requires TG_API_ID, TG_API_HASH, and TG_BOT_TOKEN env vars.")
            sys.exit(1)

    agent = OpenMobileAgent(model=args.model, vision_model=args.vision_model)

    if args.headless:
        # Create Gateway with agent callback
        async def agent_callback(goal, report_func):
            await agent.run(goal, report_func)

        gateway = CommunicationGateway(agent_callback)
        asyncio.run(run_headless(agent, gateway))
    elif args.goal:
        # Direct CLI run (asynchronous)
        async def cli_report(text, image_path=None):
            print(f"[AGENT] {text}")
            if image_path: print(f"[SCREENSHOT] {image_path}")
            
        asyncio.run(agent.run(args.goal, cli_report))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
