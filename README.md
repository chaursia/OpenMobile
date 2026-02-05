# OpenMobile - Headless Autonomous Agent

OpenMobile is a Python-based autonomous agent designed to control Android devices locally via ADB and Termux, with remote control support through **Telegram** and **WhatsApp**.

## Core Features
- **Headless Mode:** Receives commands via messaging apps and reports back status/screenshots.
- **Local Brain:** Uses `llama3.2` and `llama3.2-vision` via Ollama.
- **Cross-App Logic:** Capable of orchestration (e.g., "Copy text from Email and paste to WhatsApp").
- **Security:** Authorized users whitelist.

## Setup Instructions

### 1. Prerequisites
In Termux (or PC with device connected):
```bash
pkg install android-tools termux-api python
pip install -r requirements.txt
```

### 2. Ollama Setup
Ensure Ollama is running (`ollama serve`) with:
- `ollama run llama3.2:3b`
- `ollama run llama3.2-vision`

### 3. Messaging Channel Setup (Headless)
To control your phone via Telegram, set these environment variables:
```bash
export TG_API_ID='your_api_id'
export TG_API_HASH='your_api_hash'
export TG_BOT_TOKEN='your_bot_token'
export ALLOWED_USERS='user_id1,user_id2'
```

### 4. Running OpenMobile

#### Headless Mode (Service)
```bash
python main.py --headless
```
Send `/goal Open WhatsApp and send Hi to Mom` to your bot on Telegram.

#### CLI Mode (Direct)
```bash
python main.py --goal "Open YouTube and search for Lo-fi"
```

## Project Structure
- `channels.py`: Telegram listener and WhatsApp monitor.
- `agent.py`: Asynchronous Agentic Loop with reporting.
- `vision.py`: `llama3.2-vision` interface with coordinate scaling.
- `actions.py`: ADB controller with scroll, notification reading, and app management.

## License
MIT
