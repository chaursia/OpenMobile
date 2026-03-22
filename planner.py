"""
planner.py — Planner model for OpenMobile.

Uses qwen2.5:0.5b (ultra-lightweight, ~0.5B params) to:
  1. Understand the goal
  2. Read the screen description from the Vision Actor
  3. Review past steps from memory
  4. Decide WHAT action to take and WHY

Outputs a structured JSON PlannerResponse.
"""
import json
import asyncio
import requests
from config import OLLAMA_URL, PLANNER_MODEL, log

PLANNER_SYSTEM_PROMPT = """\
You are the Planner for OpenMobile, an autonomous Android agent.
You receive:
  - The user's GOAL
  - A SCREEN DESCRIPTION (what the Vision module sees on screen right now)
  - HISTORY (the last few steps taken so far)

Your job is to decide the single best next action.

Available actions and their parameter schemas:
  click          : {"x": int, "y": int}
  type           : {"text": str}
  scroll         : {"direction": "up"|"down"}
  open_app       : {"package_name": str}
  press_key      : {"keycode": int}        # Home=3, Back=4, Recents=187, Power=26
  long_press     : {"x": int, "y": int}
  clear_text     : {}
  back           : {}
  home           : {}
  recent_apps    : {}
  wait           : {"seconds": float}
  finish         : {"message": str}

Rules:
- If the goal is done, use finish.
- Do NOT repeat an action that already failed in history.
- If unsure of exact coordinates, set them to 0,0 — the Vision Actor will refine them.
- confidence: a float from 0.0 to 1.0 reflecting how sure you are.

Respond ONLY with valid JSON, exactly in this format:
{
  "thought": "Why I chose this action",
  "action": {"name": "action_name", "params": {}},
  "confidence": 0.85
}
"""


class PlannerModel:
    def __init__(self, ollama_url: str = OLLAMA_URL, model: str = PLANNER_MODEL):
        self.ollama_url = ollama_url
        self.model = model
        log(f"Planner initialised  →  model={model}", "INFO")

    def _build_prompt(self, goal: str, screen_desc: str, history: str) -> str:
        return (
            f"GOAL: {goal}\n\n"
            f"SCREEN (what Vision sees right now):\n{screen_desc}\n\n"
            f"HISTORY (recent steps):\n{history}\n\n"
            f"Decide the next action."
        )

    async def plan(self, goal: str, screen_desc: str, history: str) -> dict | None:
        """
        Calls qwen2.5:0.5b and returns a PlannerResponse dict:
          { "thought": str, "action": {"name": str, "params": dict}, "confidence": float }
        Returns None on failure.
        """
        prompt = self._build_prompt(goal, screen_desc, history)
        payload = {
            "model": self.model,
            "system": PLANNER_SYSTEM_PROMPT,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }
        try:
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    f"{self.ollama_url}/api/generate", json=payload, timeout=60
                ),
            )
            resp.raise_for_status()
            raw = resp.json().get("response", "{}")
            data = json.loads(raw)
            # Validate required fields
            if "action" not in data or "name" not in data["action"]:
                log("Planner response missing 'action.name'", "WARN")
                return None
            data.setdefault("thought", "")
            data.setdefault("confidence", 0.5)
            log(f"Planner → {data['action']['name']} (confidence={data['confidence']:.2f})", "PLAN")
            log(f"Planner thought: {data['thought']}", "DEBUG")
            return data
        except json.JSONDecodeError as e:
            log(f"Planner JSON parse error: {e}", "WARN")
            return None
        except Exception as e:
            log(f"Planner LLM error: {e}", "ERROR")
            return None
