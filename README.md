# KiroNav

**The ghost that helps you USE any software.**

KiroNav is an AI-powered software navigation assistant built for the Kiro Hackathon (RETO 3 - Specialized Agents). Using Gemini Live API, it watches your screen in real-time and guides you step-by-step through any software task.

## What is KiroNav?

Remember Clippy? Imagine Clippy with actual intelligence. KiroNav is a friendly ghost character (inspired by Kiro's mascot) that:

- **Watches your screen** in real-time via Gemini Live API
- **Listens to your voice** or reads your text commands
- **Guides you step-by-step** by highlighting regions, drawing arrows, and showing instructions
- **Doesn't do things for you** — it teaches you how to do them yourself

## How It Works

```
User opens KiroNav → Ghost appears (transparent, floating)
    ↓
User clicks ghost → "What can I help you with?"
    ↓
User speaks/types: "I want to send an email"
    ↓
Gemini Live sees the screen → Understands context
    ↓
KiroNav creates tutorial → Highlights "Compose" button
    ↓
User follows guidance → Step by step → Task complete!
```

## Tech Stack

- **UI**: Flet (Python, cross-platform)
- **AI**: Gemini Live API (real-time voice + vision)
- **Screen Capture**: mss (Python)
- **Voice**: pyaudio (16kHz in, 24kHz out)
- **Character**: Custom SVG ghost (inspired by Kiro)

## The Ghost

KiroNav's character is inspired by Kiro's ghost mascot but with a teal color scheme. The ghost has no mouth — all expression comes through eye movement and transparency animations:

- **Idle**: Ghost floats, eyes looking around
- **Watching**: Eyes follow cursor/screen activity
- **Speaking**: Eyes blink (open/close cycle)
- **Happy**: Eyes close in satisfaction

## Monetization Concept

- **Free Tier**: Simple tutorials (<10 steps) — send email, change settings
- **Pro Tier**: Complex tutorials (unlimited steps) — learn Figma, configure server
- **Enterprise**: Onboarding for teams, custom integrations

## Project Structure

```
kiroNav/
├── main.py                    # Entry point + KiroNavApp class
├── core/
│   ├── __init__.py
│   ├── gemini_live.py         # Gemini Live API session
│   ├── screen_capture.py      # mss screen capture (1 FPS)
│   └── audio_handler.py       # pyaudio input/output (16kHz in, 24kHz out)
├── ui/
│   ├── __init__.py
│   ├── ghost.py               # Ghost character with 4 states
│   ├── speech_bubble.py       # Input/output bubble
│   ├── guide_panel.py         # Steps + todolist panel
│   └── overlay_renderer.py    # Highlights + arrows overlay
├── tools/
│   └── function_tools.py      # Gemini Live function calling tools
├── prompts/
│   └── system_prompt.txt      # System prompt for Gemini
├── assets/
│   └── ghost/                 # SVG animations (idle, watch, speak, happy)
├── tests/
├── .env                       # API key (gitignored)
├── .env.example               # Example env file
├── .gitignore
├── requirements.txt
├── pyproject.toml
├── SCOPE.md                   # Full project scope
└── README.md
```

## Setup

```bash
# Clone the repository
git clone https://github.com/your-username/kiroNav.git
cd kiroNav

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Set up Google AI Studio API key
export GOOGLE_API_KEY="your-api-key-here"

# Run KiroNav
python main.py
```

## API Key Setup

1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Click "Create API key"
3. Copy the generated key
4. Set it as environment variable: `export GOOGLE_API_KEY="your-key"`

## Hackathon Submission

- **Challenge**: RETO 3 — Specialized Agents
- **Pitch**: "Kiro is the ghost that helps you code. KiroNav is the ghost that helps you USE any software. Same spirit, new superpower."
- **Demo**: 5-minute video showing real-time software guidance
- **Built with**: Kiro IDE + Gemini Live API + Flet

## License

MIT

## Troubleshooting

### No audio devices found
KiroNav requires a microphone and speakers. If you see "No audio devices found":
- Linux: Install PortAudio: `sudo pacman -S portaudio`
- macOS: Grant microphone permissions in System Preferences
- Windows: Check audio device settings

### Screen capture fails
KiroNav uses `mss` for screen capture. If it fails:
- Linux: Ensure X11 or Wayland is running
- macOS: Grant screen recording permissions
- Windows: No additional setup needed

### Gemini connection fails
- Verify your API key is set: `echo $GOOGLE_API_KEY`
- Check you have quota in Google AI Studio
- Ensure you have internet connection
