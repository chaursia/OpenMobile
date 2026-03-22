"""
agent.py — Dual-model consensus agent loop for OpenMobile.

Architecture (per step):
  1. Observe   → capture screenshot (ADB)
  2. Both LLMs run in PARALLEL:
       Vision Actor (moondream) → analyses screenshot → screen_description + suggested_coords
       (Planner waits for Vision output first, then plans)
  3. Planner (qwen2.5:0.5b) → reads screen_description + history → decides action + confidence
  4. Consensus:
       if confidence >= CONFIDENCE_THRESHOLD → use Planner's action as-is
       else → use Planner's action TYPE but override coords with Vision Actor's suggestion
  5. Execute   → dispatch to ControllerModule (ADB)
  6. Memory    → record step
  7. Retry     → up to RETRY_LIMIT times on failure before skipping step
"""
import asyncio
from config import (
    CONFIDENCE_THRESHOLD, MAX_STEPS, STEP_DELAY, RETRY_LIMIT,
    OLLAMA_URL, PLANNER_MODEL, VISION_MODEL, log
)
from vision import VisionModule
from actions import ControllerModule
from planner import PlannerModel
from executor import ExecutorModel
from memory import SessionMemory


class OpenMobileAgent:
    def __init__(
        self,
        planner_model: str = PLANNER_MODEL,
        vision_model: str = VISION_MODEL,
        ollama_url: str = OLLAMA_URL,
    ):
        self.vision_module = VisionModule()
        self.controller = ControllerModule(resolution=self.vision_module.resolution)
        self.planner = PlannerModel(ollama_url=ollama_url, model=planner_model)
        self.executor = ExecutorModel(ollama_url=ollama_url, model=vision_model)
        self.memory = SessionMemory()
        log("OpenMobile Agent ready.", "SUCCESS")

    # ── Consensus Logic ────────────────────────────────────────────────────────

    def _apply_consensus(
        self,
        planner_resp: dict,
        executor_resp: dict,
    ) -> dict:
        """
        Merge Planner + Executor outputs into a final action dict.

        Rules:
        - If planner confidence is high → trust planner fully
        - If planner confidence is low AND planner action is a 'click' type →
          override coordinates with vision actor's suggested_coords
        - Always trust planner for non-click actions (scroll, open_app, etc.)
        """
        action = planner_resp["action"].copy()
        confidence = planner_resp.get("confidence", 0.5)

        coord_actions = {"click", "long_press"}
        if confidence < CONFIDENCE_THRESHOLD and action["name"] in coord_actions:
            suggested = executor_resp.get("suggested_coords", [50.0, 50.0])
            abs_coords = self.executor.resolve_coords(
                suggested, self.vision_module.resolution
            )
            action["params"]["x"] = abs_coords[0]
            action["params"]["y"] = abs_coords[1]
            log(
                f"Low confidence ({confidence:.2f}) — Vision coords override: "
                f"{abs_coords[0]},{abs_coords[1]}",
                "PLAN",
            )
        else:
            log(f"High confidence ({confidence:.2f}) — Planner coords used.", "PLAN")

        return action

    # ── Single Step ─────────────────────────────────────────────────────────────

    async def _run_step(self, step_num: int, goal: str, report_func) -> str:
        """
        Executes one observe→plan→act cycle.
        Returns "FINISH", "CONTINUE", or "FAIL".
        """
        await report_func(f"📷 Step {step_num}: Capturing screen…")

        # ── 1. Observe ──────────────────────────────────────────────────────────
        if not self.vision_module.capture_screen():
            await report_func("❌ Failed to capture screen. Retrying…")
            return "FAIL"

        image_b64 = self.vision_module.get_screenshot_b64()
        if not image_b64:
            await report_func("❌ Failed to process screenshot. Retrying…")
            return "FAIL"

        # ── 2. Vision Actor analyses the screen ─────────────────────────────────
        await report_func("👁️ Vision Actor: analysing screen…")
        executor_resp = await self.executor.analyse(goal, image_b64)
        if not executor_resp:
            await report_func("⚠️ Vision Actor failed — proceeding with Planner only.")
            executor_resp = {
                "screen_description": "Screen analysis unavailable.",
                "suggested_coords": [50.0, 50.0],
            }

        screen_desc = executor_resp.get("screen_description", "Unknown")
        await report_func(f"🖥️ Screen: {screen_desc}")

        # ── 3. Planner decides action ────────────────────────────────────────────
        await report_func("🧠 Planner: deciding next action…")
        history_ctx = self.memory.get_context_window()
        planner_resp = await self.planner.plan(goal, screen_desc, history_ctx)
        if not planner_resp:
            await report_func("⚠️ Planner failed to respond. Retrying…")
            return "FAIL"

        thought = planner_resp.get("thought", "")
        await report_func(f"💭 Thought: {thought}")

        # ── 4. Consensus ─────────────────────────────────────────────────────────
        action = self._apply_consensus(planner_resp, executor_resp)
        action_name = action.get("name", "unknown")
        action_params = action.get("params", {})
        await report_func(f"⚡ Action: {action_name}({action_params})")

        # ── 5. Execute ───────────────────────────────────────────────────────────
        result = self.controller.perform_action(action_name, action_params)

        if result == "FINISH":
            finish_msg = action_params.get("message", "Goal complete.")
            await report_func(f"✅ {finish_msg}")
            self.memory.add_step(thought, action_name, action_params,
                                 "FINISH", screen_desc)
            return "FINISH"

        if isinstance(result, tuple) and result[0] == "WAIT":
            wait_secs = result[1]
            await report_func(f"⏳ Waiting {wait_secs}s…")
            await asyncio.sleep(wait_secs)

        self.memory.add_step(thought, action_name, action_params, "OK", screen_desc)
        return "CONTINUE"

    # ── Main Agent Loop ─────────────────────────────────────────────────────────

    async def run(self, goal: str, report_func, max_steps: int = MAX_STEPS):
        """
        Main headless agentic loop with retry logic and session memory.
        report_func(text, image_path=None) → sends updates to caller (Telegram / CLI).
        """
        self.memory.reset(goal)
        await report_func(f"🚀 Starting task: {goal}")

        for step in range(1, max_steps + 1):
            self.memory.status = "running"
            step_result = "FAIL"

            # Retry loop
            for attempt in range(1, RETRY_LIMIT + 2):
                if attempt > 1:
                    await report_func(f"🔄 Retry {attempt - 1}/{RETRY_LIMIT}…")
                    await asyncio.sleep(STEP_DELAY)

                step_result = await self._run_step(step, goal, report_func)
                if step_result != "FAIL":
                    break

            if step_result == "FINISH":
                self.memory.mark_done()
                # Send final screenshot
                if self.vision_module.capture_screen():
                    await report_func("📸 Final state:", image_path="screen.png")
                await report_func(
                    f"🎉 Task complete in {step} step(s)! "
                    f"Total steps: {self.memory.total_steps}"
                )
                return

            if step_result == "FAIL":
                await report_func(
                    f"⛔ Step {step} failed after {RETRY_LIMIT} retries. Aborting."
                )
                self.memory.mark_failed()
                return

            # Wait between steps to let the UI settle
            await asyncio.sleep(STEP_DELAY)

        # Reached max steps without finishing
        self.memory.mark_failed()
        await report_func(
            f"⏱️ Reached max steps ({max_steps}) without completing the goal. "
            f"Last thought: {self.memory.last_thought}"
        )
