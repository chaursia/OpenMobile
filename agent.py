import json
import requests
import time
import asyncio
from vision import VisionModule
from actions import ControllerModule

class OpenMobileAgent:
    def __init__(self, model="llama3.2:3b", vision_model="llama3.2-vision", ollama_url="http://localhost:11434"):
        self.model = model
        self.vision = VisionModule(ollama_url, vision_model)
        self.controller = ControllerModule()
        self.ollama_url = ollama_url
        self.system_prompt = """
        You are OpenMobile, an autonomous agent controlling an Android device.
        Your goal is to fulfill the user's request by taking one step at a time.
        
        Available Actions:
        - click(x, y): Clicks on absolute pixel coordinates.
        - type(text): Types text.
        - scroll(direction): Scrolls "up" or "down".
        - open_app(package_name): Opens an app.
        - press_key(keycode): Home=3, Back=4, Power=26.
        - wait(seconds): Pause execution.
        - finish(message): Goal reached.
        
        Respond ONLY with a JSON object:
        {
          "thought": "I need to open Telegram to see the message.",
          "action": {"name": "open_app", "params": {"package_name": "org.telegram.messenger"}}
        }
        """

    async def _get_llm_response(self, prompt):
        payload = {
            "model": self.model,
            "system": self.system_prompt,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }
        try:
            # Running synchronous request in executor to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: requests.post(f"{self.ollama_url}/api/generate", json=payload))
            response.raise_for_status()
            data = response.json()
            return json.loads(data.get("response", "{}"))
        except Exception as e:
            print(f"Error calling LLM: {e}")
            return None

    async def execute_action(self, action_data, report_func):
        name = action_data.get("name")
        params = action_data.get("params", {})
        
        await report_func(f"Executing: {name} with {params}")
        
        # Dispatch to controller
        self.controller.perform_action(name, params)
        
        if name == "finish":
            return "FINISH"
        return "CONTINUE"

    async def run(self, goal, report_func, max_steps=15):
        """The Headless Agentic Loop."""
        await report_func(f"Starting Task: {goal}")
        
        for step in range(max_steps):
            # Observe
            if not self.vision.capture_screen():
                await report_func("Critical Error: Failed to capture screen.")
                break
            
            # Process Image
            current_b64 = self.vision.process_image()
            if not current_b64:
                await report_func("Critical Error: Failed to process screen image.")
                break

            # Vision analysis (optional step: first ask vision what it sees)
            # For now, we combine vision + thought in one go or use uiautomator dump
            prompt = f"Goal: {goal}\nStep {step+1}. Analyse the screen and decide the next action."
            
            response_data = await self._get_llm_response(prompt)
            if not response_data:
                await report_func("Error: LLM did not provide a valid response.")
                break
            
            thought = response_data.get("thought")
            action = response_data.get("action")
            
            await report_func(f"Step {step+1} Thought: {thought}")
            
            # If the action requires coordinates, we might need to call vision specifically
            # but usually the LLM can predict location if it's the vision model itself.
            
            result = await self.execute_action(action, report_func)
            if result == "FINISH":
                await report_func(f"Success: {action.get('params', {}).get('message', 'Goal reached.')}")
                # Send final screenshot
                await report_func("Final State:", image_path="screen.png")
                break
            
            await asyncio.sleep(2) # Stabilize after action

if __name__ == "__main__":
    # Test agent with print report
    async def print_report(text, image_path=None):
        print(f"[REPORT] {text}")
        if image_path: print(f"[IMAGE] {image_path}")

    agent = OpenMobileAgent()
    # asyncio.run(agent.run("Open WhatsApp", print_report))
