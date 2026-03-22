"""
executor.py — Vision Actor model for OpenMobile.

Uses moondream (~1.6B) to:
  1. Analyse the current screenshot
  2. Describe what is visible on screen
  3. Suggest the UI element to interact with and its approximate coordinates

The Planner reads this description before deciding its action.
The Executor also provides a coordinate fallback when Planner confidence is low.
"""
import json
import asyncio
import requests
from config import OLLAMA_URL, VISION_MODEL, log

VISION_DESCRIBE_PROMPT = """\
You are the Vision Actor for OpenMobile, an Android device agent.

Analyze the Android screenshot and respond ONLY with valid JSON:
{
  "screen_description": "Short description of what is on screen (apps visible, text, icons, current app etc.)",
  "ui_elements": ["list", "of", "visible", "interactive", "elements"],
  "suggested_element": "The element most likely needed for the goal",
  "suggested_coords": [x_percent, y_percent]
}

suggested_coords are percentages (0–100) of width and height.
If the screen is a home screen, describe the icons visible.
If the screen is inside an app, describe the key interactive elements.
Keep screen_description under 100 words.
Respond ONLY with the JSON, no other text.
"""


class ExecutorModel:
    def __init__(self, ollama_url: str = OLLAMA_URL, model: str = VISION_MODEL):
        self.ollama_url = ollama_url
        self.model = model
        log(f"Executor initialised →  model={model}", "INFO")

    def _build_vision_payload(self, goal: str, image_b64: str) -> dict:
        return {
            "model": self.model,
            "prompt": (
                f"The user's goal is: '{goal}'\n\n"
                f"{VISION_DESCRIBE_PROMPT}"
            ),
            "stream": False,
            "images": [image_b64],
        }

    async def analyse(self, goal: str, image_b64: str) -> dict | None:
        """
        Sends the screenshot to moondream and returns an ExecutorResponse dict:
          {
            "screen_description": str,
            "ui_elements": list[str],
            "suggested_element": str,
            "suggested_coords": [float, float]   # percentages 0–100
          }
        Returns None on failure.
        """
        payload = self._build_vision_payload(goal, image_b64)
        try:
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    f"{self.ollama_url}/api/generate", json=payload, timeout=90
                ),
            )
            resp.raise_for_status()
            raw = resp.json().get("response", "{}").strip()

            # moondream sometimes wraps JSON in markdown fences — strip them
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()

            data = json.loads(raw)
            data.setdefault("screen_description", "Unknown screen state.")
            data.setdefault("ui_elements", [])
            data.setdefault("suggested_element", "")
            data.setdefault("suggested_coords", [50.0, 50.0])

            log(f"Vision → {data['screen_description'][:80]}…", "VISION")
            log(f"Vision suggested: {data['suggested_element']} @ {data['suggested_coords']}", "DEBUG")
            return data

        except json.JSONDecodeError as e:
            log(f"Executor JSON parse error: {e}", "WARN")
            # Return minimal fallback so the planner can still proceed
            return {
                "screen_description": "Unable to parse screen description.",
                "ui_elements": [],
                "suggested_element": "",
                "suggested_coords": [50.0, 50.0],
            }
        except Exception as e:
            log(f"Executor LLM error: {e}", "ERROR")
            return None

    def resolve_coords(self, suggested_coords: list, resolution: tuple) -> list[int]:
        """
        Converts [x%, y%] from vision model → absolute pixel [x, y].
        resolution = (width, height) in pixels.
        """
        try:
            rx, ry = float(suggested_coords[0]), float(suggested_coords[1])
            abs_x = int((rx / 100.0) * resolution[0])
            abs_y = int((ry / 100.0) * resolution[1])
            return [abs_x, abs_y]
        except Exception as e:
            log(f"Coord resolution failed: {e}", "WARN")
            w, h = resolution
            return [w // 2, h // 2]
