"""
memory.py — Session memory for OpenMobile agent.

Keeps a rolling history of steps so the LLMs can reason about
what has already been tried without hallucinating.
"""
from dataclasses import dataclass, field
from typing import Optional, List
from config import MEMORY_WINDOW


@dataclass
class Step:
    step_num: int
    thought: str
    action_name: str
    action_params: dict
    result: str          # "OK" | "FAIL" | "FINISH"
    screen_desc: str = ""


class SessionMemory:
    """Stores the step history for a single goal execution."""

    def __init__(self):
        self.goal: str = ""
        self.steps: List[Step] = []
        self.total_steps: int = 0
        self.last_thought: str = ""
        self.last_action: str = ""
        self.status: str = "idle"  # idle | running | done | failed

    def reset(self, goal: str):
        self.goal = goal
        self.steps = []
        self.total_steps = 0
        self.last_thought = ""
        self.last_action = ""
        self.status = "running"

    def add_step(self, thought: str, action_name: str, action_params: dict,
                 result: str, screen_desc: str = ""):
        self.total_steps += 1
        s = Step(
            step_num=self.total_steps,
            thought=thought,
            action_name=action_name,
            action_params=action_params,
            result=result,
            screen_desc=screen_desc,
        )
        self.steps.append(s)
        self.last_thought = thought
        self.last_action = f"{action_name}({action_params})"

    def get_context_window(self) -> str:
        """Returns the last MEMORY_WINDOW steps as a plain-text summary for prompts."""
        recent = self.steps[-MEMORY_WINDOW:]
        if not recent:
            return "No steps taken yet."
        lines = []
        for s in recent:
            lines.append(
                f"Step {s.step_num}: thought='{s.thought}' | "
                f"action={s.action_name}({s.action_params}) | result={s.result}"
            )
        return "\n".join(lines)

    def mark_done(self):
        self.status = "done"

    def mark_failed(self):
        self.status = "failed"
