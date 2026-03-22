# OpenMobile v2.0 — Headless Autonomous Android Agent

OpenMobile is a Python-based autonomous agent that controls an Android device locally via ADB and Termux, with remote control support through **Telegram** and **WhatsApp**.

It uses **two lightweight AI models running in collaboration** — a Planner and a Vision Actor — to understand your commands, read the screen, and execute actions.

---

## ✨ What's New in v2.0

| Feature | Details |
|---|---|
| **Dual-Model Architecture** | `qwen2.5:0.5b` (Planner) + `moondream` (Vision Actor) work together per step |
| **Screen-aware agent** | Vision Actor analyses every screenshot before the Planner decides |
| **Session memory** | Agent remembers past steps — no infinite loops |
| **Retry logic** | Automatic retry with backoff on step failure |
| **Termux TUI Dashboard** | `python main.py --dashboard` — setup status, usage guide, creator info |
| **More actions** | `long_press`, `back`, `home`, `recent_apps`, `clear_text`, `whatsapp_send` |
| **WhatsApp polling** | Receive commands via WhatsApp notification monitoring |
| **`.env` support** | Copy `.env.example` → `.env` instead of exporting variables manually |

---

## 🧠 How It Works (Dual-Model Loop)

Each step of the agent loop:

```
1. Capture screenshot (ADB screencap)
         │
         ▼
2. moondream (Vision Actor) — analyses screenshot
   → "Search bar visible, 4 app icons on home screen"
   → Suggested element + coordinates
         │
         ▼
3. qwen2.5:0.5b (Planner) — reads screen description + history
   → Thought: "I need to open YouTube via the app drawer"
   → Action: open_app(com.google.android.youtube)
   → Confidence: 0.92
         │
         ▼
4. Consensus:
   confidence ≥ 0.70 → use Planner's action as-is
   confidence < 0.70 → keep Planner's action type, use Vision's coordinates
         │
         ▼
5. Execute via ADB → record step in memory → repeat
```

---

## 🚀 Setup Instructions

### 1. Termux Environment

```bash
pkg update && pkg upgrade
pkg install android-tools termux-api python libjpeg-turbo libpng
termux-setup-storage

git clone https://github.com/chaursia/OpenMobile.git
cd OpenMobile
pip install -r requirements.txt
```

### 2. Pull AI Models (Ollama)

Install [Ollama](https://ollama.com) in Termux or on a networked PC, then:

```bash
ollama pull qwen2.5:0.5b    # Planner — ~400 MB
ollama pull moondream        # Vision Actor — ~1.7 GB
```
> [!TIP]
> Use Ollama on a PC instead of the phone if device have less than 6 GB RAM


> [!TIP]
> If Ollama is running on a PC instead of the phone, set `OLLAMA_URL=http://<pc-ip>:11434` in your `.env`.

### 3. ADB Configuration

Enable **Developer Options** → **USB Debugging** on your Android device.

**Wireless ADB (recommended for Termux):**
1. Enable **Wireless Debugging** in Developer Options
2. Tap **Pair device with pairing code** — note the IP, port, and code
3. In Termux: `adb pair <ip>:<port>` then `adb connect <ip>:<port>`

> [!IMPORTANT]
> Some devices require **USB Debugging (Security Settings)** for ADB to simulate taps/swipes.

### 4. Environment Configuration

```bash
cp .env.example .env
nano .env    # fill in your credentials
```

Key variables:

| Variable | Description |
|---|---|
| `TG_API_ID` / `TG_API_HASH` | From [my.telegram.org](https://my.telegram.org) |
| `TG_BOT_TOKEN` | From [@BotFather](https://t.me/botfather) |
| `ALLOWED_USERS` | Comma-separated Telegram user IDs (from [@userinfobot](https://t.me/userinfobot)) |
| `OLLAMA_URL` | Default: `http://localhost:11434` |
| `PLANNER_MODEL` | Default: `qwen2.5:0.5b` |
| `VISION_MODEL` | Default: `moondream` |

---

## 🛠️ Usage

### Dashboard (check setup status first!)

```bash
python main.py --dashboard
```

Shows ADB connection, Ollama status, model availability, config, usage guide, and creator info. Refreshes every 2 seconds.

### CLI Mode (direct testing)

```bash
python main.py --goal "Open YouTube and search for lo-fi music"
python main.py --goal "Set an alarm for 7 AM"
python main.py --goal "Open WhatsApp and message Mom" --debug
```

### Headless Mode (Telegram controlled)

```bash
python main.py --headless
```

Then send commands to your bot via Telegram:

```
/goal Open Instagram and like the first post
/goal Go to Settings and enable Wi-Fi
/status
/help
```

### Headless + WhatsApp

```bash
python main.py --headless --whatsapp
```

Send `/goal <task>` from WhatsApp — the agent polls notifications every 5 seconds.

### CLI Options

```
--goal "..."          Run a single task directly
--headless            Start Telegram listener
--whatsapp            Enable WhatsApp polling (use with --headless)
--dashboard           Show TUI dashboard
--planner-model       Override planner model (default: qwen2.5:0.5b)
--vision-model        Override vision model (default: moondream)  
--max-steps N         Max steps per goal (default: 15)
--debug               Verbose debug output
```

---

## 📂 Project Structure

```
OpenMobile/
├── main.py          # Entry point
├── agent.py         # Dual-model consensus loop
├── planner.py       # Planner model (qwen2.5:0.5b)
├── executor.py      # Vision Actor model (moondream)
├── vision.py        # ADB screen capture + compression
├── actions.py       # ADB action library
├── channels.py      # Telegram + WhatsApp gateways
├── dashboard.py     # Termux TUI dashboard
├── memory.py        # Session step memory
├── config.py        # Central config + env loading
├── .env.example     # Config template
├── requirements.txt
└── test_modules.py  # 19 smoke tests
```

---

## ⚠️ Troubleshooting

| Problem | Fix |
|---|---|
| `adb: not found` | Run `pkg install android-tools` in Termux |
| `Ollama not running` | Open a new Termux session and run `ollama serve` |
| Agent taps wrong spot | Enable `--debug` to see Vision Actor's screen description |
| `TG_API_ID missing` | Copy `.env.example` to `.env` and fill in credentials |
| `moondream not found` | Run `ollama pull moondream` |
| Any error while running `/goal <Task>` (connection failed etc) | It might by crashing due to low RAM . Run ollama On PC & update .env file|

---

## 🧪 Running Tests

```bash
python test_modules.py
# Ran 19 tests — OK ✅
```

---

## 📄 License

MIT

---

> Built with ❤️ at [neurodev.in](https://neurodev.in)
