# OpenMobile - Headless Autonomous Agent

OpenMobile is a Python-based autonomous agent designed to control Android devices locally via ADB and Termux, with remote control support through **Telegram** and **WhatsApp**.

## Core Features
- **Headless Mode:** Receives commands via messaging apps and reports back status/screenshots.
- **Local Brain:** Uses `llama3.2` and `llama3.2-vision` via Ollama.
- **Cross-App Logic:** Capable of orchestration (e.g., "Copy text from Email and paste to WhatsApp").
- **Security:** Authorized users whitelist.

---

## 🚀 Setup Instructions

### 1. Termux Environment Setup
First, ensure your Termux environment is up to date and has the necessary permissions.

```bash
pkg update && pkg upgrade
pkg install android-tools termux-api python
termux-setup-storage
```

Clone the repository and install Python dependencies:
```bash
git clone https://github.com/chaursia/OpenMobile.git
cd OpenMobile
pip install -r requirements.txt
```

### 2. ADB Configuration (Crucial)
OpenMobile uses ADB to control your phone. You must enable **Developer Options** and **USB Debugging** on your Android device.

#### Connection Methods:
- **USB:** Connect to a PC, run `adb devices` to authorize.
- **On-Device (Wireless ADB):** 
  1. Enable **Wireless Debugging** in Developer Options.
  2. Use the "Pair device" option to get a port and pairing code.
  3. In Termux, run: `adb pair ipaddr:port` followed by `adb connect ipaddr:port`.

> [!IMPORTANT]
> Some devices require "USB Debugging (Security Settings)" to be enabled for ADB to simulate taps/swipes.

### 3. Ollama (The Brain)
OpenMobile requires a local Ollama server. 
1. Install Ollama in Termux (or run it on a networked PC).
2. Pull the required models:
```bash
ollama pull llama3.2:3b
ollama pull llama3.2-vision
```
3. Ensure the server is accessible at `http://localhost:11434`.

### 4. Messaging Channel Setup (Headless Control)
To control OpenMobile via Telegram, you need to set up a Bot and get API credentials.

#### Step 4a: Get Telegram API Credentials
1. Go to [my.telegram.org](https://my.telegram.org) and create an "App" to get your `API_ID` and `API_HASH`.
2. Message [@BotFather](https://t.me/botfather) on Telegram to create a new bot and get your `BOT_TOKEN`.
3. Message [@userinfobot](https://t.me/userinfobot) to get your own `USER_ID`.

#### Step 4b: Set Environment Variables
```bash
export TG_API_ID='your_api_id'
export TG_API_HASH='your_api_hash'
export TG_BOT_TOKEN='your_bot_token'
export ALLOWED_USERS='your_user_id' # Comma-separated list
```

---

## 🛠️ Usage

### Headless Mode (Service)
This mode starts the Telegram listener. You can then send commands to your bot from any device.
```bash
python main.py --headless
```
**Example Commands to send via Telegram:**
- `/goal Open WhatsApp and send "Starting my day" to Mom`
- `/goal Go to Instagram and find a photo of a cat`

### CLI Mode (Direct)
Use this for local testing without Telegram.
```bash
python main.py --goal "Open YouTube and search for Lo-fi"
```

---

## 📂 Project Structure
- `main.py`: Entry point for Headless and CLI modes.
- `channels.py`: Telegram listener and WhatsApp monitoring gateway.
- `agent.py`: Asynchronous Think-Act-Observe loop.
- `vision.py`: Screen analysis and coordinate resolution.
- `actions.py`: ADB command library (tap, swipe, scroll, apps).

## ⚠️ Troubleshooting
- **ADB Unauthorized:** Ensure you've clicked "Always allow from this computer" on your phone's ADB prompt.
- **Ollama Timeout:** Ensure Ollama is running in the background. If running on a PC, update `main.py` with the PC's IP.
- **Coordinates Offset:** If taps are missing, check if `vision.py` is detecting the correct resolution.

## License
MIT
