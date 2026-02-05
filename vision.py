import subprocess
import os
import requests
import base64
from PIL import Image
from io import BytesIO

class VisionModule:
    def __init__(self, ollama_url="http://localhost:11434", vision_model="llama3.2-vision"):
        self.ollama_url = ollama_url
        self.vision_model = vision_model
        self.screenshot_path = "screen.png"
        self.compressed_path = "screen_compressed.png"
        # Phone resolution (auto-detected via ADB or default)
        self.resolution = self._get_device_resolution()

    def _get_device_resolution(self):
        """Detects the phone resolution via ADB."""
        try:
            result = subprocess.run(["adb", "shell", "wm", "size"], capture_output=True, text=True)
            if "Physical size:" in result.stdout:
                size_str = result.stdout.split(":")[-1].strip()
                w, h = map(int, size_str.split("x"))
                return (w, h)
        except Exception:
            pass
        return (1080, 2400) # Default common resolution

    def capture_screen(self):
        """Captures the Android screen via ADB and pulls it to the local directory."""
        try:
            subprocess.run(["adb", "shell", "screencap", "-p", "/sdcard/screen.png"], check=True)
            subprocess.run(["adb", "pull", "/sdcard/screen.png", self.screenshot_path], check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error capturing screen: {e}")
            return False

    def process_image(self, max_size=(1024, 1024), quality=80):
        """Resizes and compresses for llama3.2-vision."""
        if not os.path.exists(self.screenshot_path):
            return None
        
        with Image.open(self.screenshot_path) as img:
            img.thumbnail(max_size)
            img.save(self.compressed_path, "JPEG", optimize=True, quality=quality)
        
        with open(self.compressed_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def find_element(self, query, image_base64):
        """Sends image to llama3.2-vision to get relative coordinates [x%, y%]."""
        prompt = f"""
        Analyze this screenshot. Find the "{query}".
        Provide the center coordinates as percentages [x%, y%].
        Example: If it's in the middle, respond "[50, 50]".
        Respond ONLY with the [x, y] coordinates.
        """
        
        payload = {
            "model": self.vision_model,
            "prompt": prompt,
            "stream": False,
            "images": [image_base64]
        }
        
        try:
            response = requests.post(f"{self.ollama_url}/api/generate", json=payload)
            response.raise_for_status()
            result = response.json().get("response", "").strip()
            return self._parse_and_scale_coords(result)
        except Exception as e:
            print(f"Error calling Vision LLM: {e}")
            return None

    def _parse_and_scale_coords(self, response_text):
        """Converts [x%, y%] string to absolute [x, y] pixels."""
        try:
            # Simple [x, y] extraction
            cleaned = response_text.replace("[", "").replace("]", "").replace("%", "").split(",")
            rx, ry = map(float, cleaned)
            
            # Scale to actual resolution
            abs_x = int((rx / 100.0) * self.resolution[0])
            abs_y = int((ry / 100.0) * self.resolution[1])
            return [abs_x, abs_y]
        except Exception:
            print(f"Failed to parse coordinates from: {response_text}")
            return None

if __name__ == "__main__":
    vision = VisionModule()
    print(f"Detected Resolution: {vision.resolution}")
