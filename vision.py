"""
vision.py — Screen capture and image processing for OpenMobile.

Handles:
  - ADB screencap and pull
  - Image compression before sending to vision LLM
  - Resolution auto-detection
"""
import subprocess
import os
import base64
from PIL import Image
from config import log


class VisionModule:
    def __init__(self):
        self.screenshot_path = "screen.png"
        self.compressed_path = "screen_compressed.jpg"
        self.resolution = self._get_device_resolution()
        log(f"Vision module ready — device resolution: {self.resolution[0]}x{self.resolution[1]}", "INFO")

    # ── Device Info ─────────────────────────────────────────────────────────────

    def _get_device_resolution(self) -> tuple[int, int]:
        """Auto-detects device resolution via ADB. Falls back to 1080x2400."""
        try:
            result = subprocess.run(
                ["adb", "shell", "wm", "size"],
                capture_output=True, text=True, timeout=10
            )
            if "Physical size:" in result.stdout:
                size_str = result.stdout.split(":")[-1].strip()
                w, h = map(int, size_str.split("x"))
                return (w, h)
        except Exception as e:
            log(f"Could not detect resolution via ADB: {e}", "WARN")
        return (1080, 2400)

    def is_adb_connected(self) -> bool:
        """Returns True if at least one ADB device/emulator is connected."""
        try:
            result = subprocess.run(
                ["adb", "devices"], capture_output=True, text=True, timeout=10
            )
            lines = [
                l.strip() for l in result.stdout.splitlines()
                if l.strip() and not l.startswith("List")
            ]
            return any("device" in l for l in lines)
        except Exception:
            return False

    # ── Screen Capture ───────────────────────────────────────────────────────────

    def capture_screen(self) -> bool:
        """Captures the Android screen via ADB screencap and pulls it locally."""
        try:
            subprocess.run(
                ["adb", "shell", "screencap", "-p", "/sdcard/screen.png"],
                check=True, capture_output=True, timeout=30
            )
            subprocess.run(
                ["adb", "pull", "/sdcard/screen.png", self.screenshot_path],
                check=True, capture_output=True, timeout=30
            )
            log("Screen captured successfully.", "DEBUG")
            return True
        except subprocess.CalledProcessError as e:
            log(f"ADB screencap failed: {e.stderr.decode(errors='ignore')}", "ERROR")
            return False
        except subprocess.TimeoutExpired:
            log("ADB screencap timed out.", "ERROR")
            return False

    # ── Image Processing ─────────────────────────────────────────────────────────

    def get_screenshot_b64(self, max_size: tuple = (1024, 1024), quality: int = 80) -> str | None:
        """
        Compresses the captured screenshot and returns it as a base64 string
        suitable for the moondream vision model.
        """
        if not os.path.exists(self.screenshot_path):
            log("Screenshot file not found for processing.", "WARN")
            return None
        try:
            with Image.open(self.screenshot_path) as img:
                img.thumbnail(max_size)
                # Convert RGBA → RGB if needed (PNG may have alpha channel)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.save(self.compressed_path, "JPEG", optimize=True, quality=quality)
            with open(self.compressed_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            log(f"Image processing failed: {e}", "ERROR")
            return None
