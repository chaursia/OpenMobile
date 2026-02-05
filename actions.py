import subprocess
import json
import os

class ControllerModule:
    def __init__(self):
        pass

    def _run_adb(self, args):
        command = ["adb", "shell"] + args
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            print(f"ADB Error: {e.stderr}")
            return None

    def click(self, x, y):
        """Click at absolute pixel coordinates."""
        print(f"Action: Clicking at ({x}, {y})")
        return self._run_adb(["input", "tap", str(x), str(y)])

    def type_text(self, text):
        formatted_text = text.replace(" ", "%s")
        print(f"Action: Typing: {text}")
        return self._run_adb(["input", "text", formatted_text])

    def swipe(self, x1, y1, x2, y2, duration=500):
        print(f"Action: Swiping from ({x1}, {y1}) to ({x2}, {y2})")
        return self._run_adb(["input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration)])

    def scroll(self, direction="down"):
        """Performs a generic scroll gesture."""
        print(f"Action: Scrolling {direction}")
        if direction == "down":
            self.swipe(540, 1800, 540, 600)
        else:
            self.swipe(540, 600, 540, 1800)

    def open_app(self, package_name):
        print(f"Action: Opening {package_name}")
        return self._run_adb(["monkey", "-p", package_name, "-c", "android.intent.category.LAUNCHER", "1"])

    def press_key(self, keycode):
        return self._run_adb(["input", "keyevent", str(keycode)])

    def read_notifications(self):
        """Reads incoming notifications via Termux:API."""
        try:
            result = subprocess.run(["termux-notification-list"], capture_output=True, text=True)
            return json.loads(result.stdout)
        except Exception as e:
            print(f"Error reading notifications: {e}")
            return []

    def perform_action(self, action_type, params):
        """Generic action dispatcher for the agent."""
        if action_type == "click":
            return self.click(params.get("x"), params.get("y"))
        elif action_type == "type":
            return self.type_text(params.get("text"))
        elif action_type == "scroll":
            return self.scroll(params.get("direction", "down"))
        elif action_type == "open_app":
            return self.open_app(params.get("package_name"))
        elif action_type == "press_key":
            return self.press_key(params.get("keycode"))
        elif action_type == "wait":
            import time
            time.sleep(params.get("seconds", 2))
        return None

if __name__ == "__main__":
    ctrl = ControllerModule()
    # ctrl.scroll("down")
