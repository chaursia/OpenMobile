"""
test_modules.py — Smoke tests for OpenMobile modules.
No external services required (ADB/Ollama mocked).

Run: python test_modules.py
"""
import sys
import os
import base64
import unittest
from unittest.mock import patch, MagicMock
from io import BytesIO

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(__file__))


# ── 1. Config ──────────────────────────────────────────────────────────────────
class TestConfig(unittest.TestCase):
    def test_imports(self):
        import config
        self.assertTrue(hasattr(config, "VERSION"))
        self.assertTrue(hasattr(config, "PLANNER_MODEL"))
        self.assertTrue(hasattr(config, "VISION_MODEL"))
        self.assertTrue(hasattr(config, "CREATOR"))

    def test_creator_fields(self):
        from config import CREATOR
        for field in ("name", "github", "bug_report", "telegram"):
            self.assertIn(field, CREATOR, f"CREATOR missing '{field}'")

    def test_log_does_not_crash(self):
        from config import log
        log("Test message", "INFO")
        log("Debug message", "DEBUG")


# ── 2. Memory ──────────────────────────────────────────────────────────────────
class TestMemory(unittest.TestCase):
    def setUp(self):
        from memory import SessionMemory
        self.mem = SessionMemory()

    def test_reset(self):
        self.mem.reset("Open YouTube")
        self.assertEqual(self.mem.goal, "Open YouTube")
        self.assertEqual(self.mem.status, "running")
        self.assertEqual(self.mem.total_steps, 0)

    def test_add_step(self):
        self.mem.reset("Test goal")
        self.mem.add_step("I should click here", "click", {"x": 100, "y": 200}, "OK", "Home screen")
        self.assertEqual(self.mem.total_steps, 1)
        self.assertEqual(self.mem.last_action, "click({'x': 100, 'y': 200})")

    def test_context_window(self):
        self.mem.reset("Test goal")
        for i in range(7):
            self.mem.add_step(f"Thought {i}", "click", {"x": i, "y": i}, "OK")
        ctx = self.mem.get_context_window()
        # Should only contain last MEMORY_WINDOW steps
        self.assertIn("Thought 6", ctx)
        self.assertNotIn("Thought 0", ctx)  # Rolled off

    def test_mark_states(self):
        self.mem.reset("Test")
        self.mem.mark_done()
        self.assertEqual(self.mem.status, "done")
        self.mem.mark_failed()
        self.assertEqual(self.mem.status, "failed")


# ── 3. Actions (mocked ADB) ────────────────────────────────────────────────────
class TestActions(unittest.TestCase):
    def setUp(self):
        from actions import ControllerModule
        self.ctrl = ControllerModule(resolution=(1080, 2400))

    @patch("subprocess.run")
    def test_click(self, mock_run):
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        self.ctrl.click(540, 960)
        args = mock_run.call_args[0][0]
        self.assertIn("tap", args)
        self.assertIn("540", args)
        self.assertIn("960", args)

    @patch("subprocess.run")
    def test_scroll_uses_resolution(self, mock_run):
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        self.ctrl.scroll("down")
        args = mock_run.call_args[0][0]
        # Should use 1080/2 = 540 as center x
        self.assertIn("540", args)
        # Should NOT use hardcoded 1800 or 600 as-is (those were for 2400px height)
        # With resolution 2400, top=480, bot=1800 — these are still the same but derived correctly
        self.assertIn("swipe", args)

    @patch("subprocess.run")
    def test_perform_action_wait_returns_sentinel(self, mock_run):
        result = self.ctrl.perform_action("wait", {"seconds": 3.0})
        self.assertEqual(result, ("WAIT", 3.0))

    @patch("subprocess.run")
    def test_perform_action_finish_returns_finish(self, mock_run):
        result = self.ctrl.perform_action("finish", {"message": "Done"})
        self.assertEqual(result, "FINISH")

    def test_perform_action_unknown_returns_none(self):
        result = self.ctrl.perform_action("fly_to_moon", {})
        self.assertIsNone(result)


# ── 4. Vision (mocked ADB + PIL) ──────────────────────────────────────────────
class TestVision(unittest.TestCase):
    @patch("subprocess.run")
    def test_get_device_resolution_fallback(self, mock_run):
        mock_run.return_value = MagicMock(stdout="Physical size: 1080x2340", returncode=0)
        from vision import VisionModule
        vm = VisionModule()
        self.assertEqual(vm.resolution, (1080, 2340))

    def test_get_screenshot_b64_missing_file(self):
        from vision import VisionModule
        with patch("subprocess.run") as mr:
            mr.return_value = MagicMock(stdout="Physical size: 1080x2400", returncode=0)
            vm = VisionModule()
        vm.screenshot_path = "/nonexistent/screen.png"
        result = vm.get_screenshot_b64()
        self.assertIsNone(result)

    def test_get_screenshot_b64_with_dummy_image(self):
        """Creates a real tiny PNG, compresses it, checks b64 output."""
        from PIL import Image
        import tempfile, os
        from vision import VisionModule

        with patch("subprocess.run") as mr:
            mr.return_value = MagicMock(stdout="Physical size: 1080x2400", returncode=0)
            vm = VisionModule()

        # Create a tiny dummy PNG
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            dummy_path = f.name
        img = Image.new("RGB", (100, 200), color=(30, 30, 30))
        img.save(dummy_path, "PNG")

        vm.screenshot_path = dummy_path
        vm.compressed_path = dummy_path.replace(".png", "_comp.jpg")
        result = vm.get_screenshot_b64()

        os.unlink(dummy_path)
        if os.path.exists(vm.compressed_path):
            os.unlink(vm.compressed_path)

        self.assertIsNotNone(result)
        # Should be valid base64
        decoded = base64.b64decode(result)
        self.assertGreater(len(decoded), 0)


# ── 5. Planner prompt building ─────────────────────────────────────────────────
class TestPlanner(unittest.TestCase):
    def setUp(self):
        from planner import PlannerModel
        self.planner = PlannerModel()

    def test_build_prompt_contains_goal(self):
        prompt = self.planner._build_prompt("Open YouTube", "Home screen", "No steps yet.")
        self.assertIn("Open YouTube", prompt)
        self.assertIn("Home screen", prompt)
        self.assertIn("No steps yet.", prompt)


# ── 6. Executor prompt building ────────────────────────────────────────────────
class TestExecutor(unittest.TestCase):
    def setUp(self):
        from executor import ExecutorModel
        self.exec = ExecutorModel()

    def test_resolve_coords(self):
        coords = self.exec.resolve_coords([25.0, 50.0], (1080, 2400))
        self.assertEqual(coords, [270, 1200])

    def test_resolve_coords_fallback(self):
        coords = self.exec.resolve_coords([], (1080, 2400))
        self.assertEqual(coords, [540, 1200])

    def test_build_payload_contains_image(self):
        payload = self.exec._build_vision_payload("Open YouTube", "FAKEBASE64")
        self.assertIn("FAKEBASE64", payload["images"])
        self.assertIn("Open YouTube", payload["prompt"])


# ── Runner ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n\033[96m OpenMobile — Module Smoke Tests\033[0m\n")
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in [TestConfig, TestMemory, TestActions, TestVision, TestPlanner, TestExecutor]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
