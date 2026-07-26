# KiroNav — Project Scope

## Overview

**KiroNav** is an AI-powered software navigation assistant that watches your screen and guides you step-by-step through any software task. A friendly ghost character floats on your screen, reads your requests, and teaches you how to use any application.

## Core Concept

**The Problem**: Millions of people (elderly, non-technical users, new employees) don't know how to use software. Tutorials are text-heavy videos that nobody watches.

**The Solution**: A real-time AI assistant that sees your screen and guides you visually — like having a patient friend looking over your shoulder.

**Key Differentiator**: KiroNav does NOT do things FOR the user. It teaches them HOW to do it themselves.

## Hackathon Context

- **Challenge**: RETO 3 — Specialized Agents
- **Deadline**: July 27, 2026
- **Team**: Solo developer
- **Pitch**: "Kiro is the ghost that helps you code. KiroNav is the ghost that helps you USE any software. Same spirit, new superpower."

## Architecture

### Current Stack

| Component | Technology | Purpose |
|---|---|---|
| UI | Flet 0.86 (Python) | Cross-platform transparent floating widget |
| AI | Kiro Gateway → Claude Sonnet 4.5 | Vision + text inference via Kiro models catalog |
| Screen Capture | mss / grim | Capture screen (Windows/X11/Wayland) |
| Character | SVG | Ghost with 4 expression states |

### Flow

```
User clicks ghost → Input dialog appears
    ↓
User types request → Screen captured as PNG
    ↓
PNG + prompt sent to Kiro Gateway (localhost:8100)
    ↓
Model analyzes screenshot → Returns JSON {summary, steps[], done}
    ↓
GuidePanel renders steps → User clicks ghost to advance
    ↓
Fresh screenshot → Model gives next steps → Until done
```

### Design Decisions

1. **Gemini Live → Kiro Gateway**: Originally planned for Gemini Live (WebSocket + audio + function calling). Pivoted because: no Windows native CLI support, simpler architecture with HTTP API, uses Kiro tokens directly.

2. **Flet over Electron**: Single Python codebase for desktop + mobile (future). Transparent window, always-on-top, frameless — native feel without JS complexity.

3. **No overlays (MVP)**: Visual highlights/arrows deferred to post-hackathon. Step-by-step text guidance is sufficient for the demo.

4. **No audio (MVP)**: Voice I/O deferred. Text input works cross-platform without permission issues.

## MVP Scope

### DONE

- [x] Ghost SVG floating on screen (transparent window)
- [x] Screen capture (Windows, X11, Wayland)
- [x] AI vision analysis via Kiro Gateway
- [x] Speech bubble (text input + AI responses)
- [x] Step-by-step tutorial guide panel
- [x] Question answering (describe what's on screen)
- [x] Multi-turn conversation context
- [x] Draggable window
- [x] System prompt for KiroNav personality

### FUTURE (Post-hackathon)

- [ ] Audio input (speech-to-text)
- [ ] Visual overlays (highlights, arrows on screen)
- [ ] Mobile version (Flet build apk/ipa)
- [ ] Deploy as Kiro product (bundled with gateway)
- [ ] Tutorial history / persistence
- [ ] Complex task breakdown (todolist mode)

## Success Criteria

### Functional
- [x] Ghost appears and floats on screen
- [x] Screen capture works
- [x] AI analyzes screenshots correctly
- [x] Step-by-step guidance works
- [x] Questions about screen content answered

### Demo
- [ ] Video showing complete workflow
- [ ] Repository public on GitHub
- [ ] README with setup instructions
