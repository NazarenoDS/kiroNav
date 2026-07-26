# KiroNav

**The ghost that helps you USE any software.**

KiroNav is an AI-powered software navigation assistant built for the Kiro Hackathon (RETO 3 - Specialized Agents). It sees your screen, understands what's on it, and guides you step-by-step through any task.

## What is KiroNav?

A friendly ghost floats on your screen. You tell it what you need help with. It looks at your screen, figures out where you are, and tells you exactly what to click, type, or do next. Step by step. Like a patient friend sitting next to you.

**It does NOT do things for you.** It teaches you how to do them yourself.

## How It Works

```
Ghost floats on screen → You click it → Type what you need
    ↓
Screen captured → AI sees your screen → Analyzes context
    ↓
Returns step-by-step guide → You follow along
    ↓
Click ghost to advance → Fresh screenshot → Next steps
    ↓
Task complete → Ghost celebrates!
```

You can also just ask questions: "Do you see a browser?" and it will describe what it observes on your screen.

## Tech Stack

| Component | Technology | Purpose |
|---|---|---|
| UI | Flet 0.86 (Python) | Transparent floating widget |
| AI | Kiro Gateway → Claude Sonnet 4.5 | Vision + guidance via Kiro models catalog |
| Screen Capture | mss / grim | Cross-platform (Windows/X11/Wayland) |
| Character | SVG | Ghost with 4 expression states |

## The Ghost

A teal ghost inspired by Kiro's mascot. No mouth — all expression through eyes:

| State | When |
|---|---|
| **Idle** | Waiting for you |
| **Watching** | Processing your request |
| **Speaking** | Showing a response |
| **Happy** | Task completed |

## Setup

### Prerequisites

- Python 3.10+
- [Kiro IDE](https://kiro.dev/downloads/) installed and logged in (provides authentication)
- Git

### 1. Clone and install

```bash
git clone https://github.com/your-username/kiroNav.git
cd kiroNav

python -m venv venv
venv\Scripts\activate  # Windows
# or: source venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
```

### 2. Set up Kiro Gateway

KiroNav uses [Kiro Gateway](https://github.com/Jwadow/kiro-gateway) to access models from the Kiro catalog using your IDE credentials.

```bash
# Clone gateway inside the project (already in .gitignore)
git clone https://github.com/Jwadow/kiro-gateway.git

# Install gateway dependencies
pip install -r kiro-gateway/requirements.txt

# Configure gateway
echo 'KIRO_CREDS_FILE="~/.aws/sso/cache/kiro-auth-token.json"' > kiro-gateway/.env
echo 'PROXY_API_KEY="kironav-local-dev"' >> kiro-gateway/.env
```

> The credentials file is created automatically when you log into Kiro IDE.

### 3. Run

Open two terminals:

**Terminal 1 — Gateway:**
```bash
cd kiro-gateway
python main.py --port 8100
```

Wait until you see: `Uvicorn running on http://0.0.0.0:8100`

**Terminal 2 — KiroNav:**
```bash
python main.py
```

The ghost appears on your screen. Click it to start.

### Wayland (Linux)

If you're on Wayland, install `grim` for screen capture:
```bash
sudo pacman -S grim    # Arch
sudo apt install grim  # Debian/Ubuntu
```

## Configuration

Create a `.env` file (optional, defaults work):

```env
KIRO_GATEWAY_URL=http://localhost:8100/v1
KIRO_API_KEY=kironav-local-dev
KIRO_MODEL=claude-sonnet-4-5
```

## Project Structure

```
kiroNav/
├── main.py                    # App entry point + orchestration
├── core/
│   ├── kiro_backend.py        # Kiro Gateway API client (OpenAI SDK + vision)
│   └── screen_capture.py      # mss/grim screen capture
├── ui/
│   ├── ghost.py               # Ghost character (4 SVG states)
│   ├── speech_bubble.py       # Text input / AI output
│   └── guide_panel.py         # Step-by-step tutorial panel
├── prompts/
│   └── kiro_system_prompt.txt # System prompt with JSON output contract
├── assets/ghost/              # SVG files (idle, watch, speak, happy)
├── kiro-gateway/              # Local gateway (gitignored)
├── requirements.txt
├── pyproject.toml
├── SCOPE.md
└── README.md
```

## Architecture

```
┌──────────────────────────────────────┐
│          KiroNavApp (main.py)        │
│   Ghost + SpeechBubble + GuidePanel  │
├──────────────────────────────────────┤
│  ScreenCapture     │  KiroBackend    │
│  (mss/grim → PNG)  │  (OpenAI SDK)   │
│                    │       ↓         │
│                    │  Kiro Gateway   │
│                    │  (localhost:8100)│
│                    │       ↓         │
│                    │  Kiro Models    │
│                    │  (Claude Sonnet)│
└──────────────────────────────────────┘
```

## Hackathon

- **Challenge**: RETO 3 — Specialized Agents
- **Pitch**: "Kiro is the ghost that helps you code. KiroNav is the ghost that helps you USE any software."
- **Built with**: Kiro IDE + Kiro Models Catalog + Flet

## Troubleshooting

### Ghost doesn't appear
- Make sure Flet 0.86+ is installed: `pip install flet>=0.86.0`
- First launch downloads the Flet runtime — wait for "Preparing Flet..." to finish

### "Connection refused" error
- Start the gateway first: `python kiro-gateway/main.py --port 8100`
- Check it's healthy: `curl http://localhost:8100/health`

### Gateway authentication fails
- Open Kiro IDE and make sure you're logged in
- Check that `~/.aws/sso/cache/kiro-auth-token.json` exists

### Screen capture issues
- **Windows**: Works out of the box
- **Wayland**: Install `grim`
- **macOS**: Grant screen recording permission

## License

MIT
