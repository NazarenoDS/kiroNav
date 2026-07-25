# KiroNav — Project Scope

## Overview

**KiroNav** is an AI-powered software navigation assistant that uses Gemini Live API to watch your screen in real-time and guide you step-by-step through any software task. A friendly ghost character (inspired by Kiro's mascot) floats on your screen, listens to your requests, and marks/highlights exactly what you need to do.

## Core Concept

**The Problem**: Millions of people (elderly, non-technical users, new employees) don't know how to use software. Tutorials are text-heavy videos that nobody watches.

**The Solution**: A real-time AI assistant that watches your screen and guides you visually — like having a patient friend looking over your shoulder.

**Key Differentiator**: KiroNav does NOT do things FOR the user. It teaches them HOW to do it themselves by highlighting, marking, and explaining each step.

## Hackathon Context

- **Challenge**: RETO 3 — Specialized Agents
- **Deadline**: July 27, 2026 (5 days from July 22)
- **Team**: Solo developer
- **Pitch**: "Kiro is the ghost that helps you code. KiroNav is the ghost that helps you USE any software. Same spirit, new superpower."

## User Flow

### Complete Flow

```
1. IDLE STATE
   - Ghost appears transparent, floating in bottom-right corner
   - Ghost is idle, eyes looking around subtly

2. ACTIVATION
   - User clicks on ghost
   - Ghost rises opacity (becomes more visible)
   - Speech bubble appears: "¿En qué te puedo ayudar?"

3. INPUT
   - Single click → Keyboard opens for text input
   - Long press → Microphone activates for voice input

4. PROCESSING
   - User says/types: "Quiero mandar un mail por Gmail"
   - Gemini Live receives screen frames via WebSocket
   - AI analyzes: "User is in Gmail inbox, wants to send email"
   - AI creates tutorial steps

5. GUIDANCE
   - Ghost transitions to "watching" state
   - Step 1: highlight_region on "Compose" button
   - Speech bubble: "Hacé click en el botón rojo de arriba que dice 'Redactar'"
   - Ghost speaks the instruction via audio

6. NAVIGATION
   - User clicks "Compose"
   - Ghost verifies screen changed
   - Step 2: highlight_region on "To" field
   - Continue until task complete

7. COMPLETION
   - Ghost transitions to "happy" state
   - Speech bubble: "¡Listo! Mandaste tu primer mail. ¡Felicidades!"
   - Ghost returns to idle
```

### Complex Tasks (Todolist)

For tasks with many steps (>10), KiroNav creates a markdown todolist:

```markdown
## Aprender Figma — Pasos

- [ ] Abrir Figma
- [ ] Crear nuevo proyecto
- [ ] Conocer la interfaz (herramientas, paneles)
- [ ] Dibujar un rectángulo
- [ ] Agregar texto
- [ ] Agrupar elementos
- [ ] Exportar diseño
- [ ] ...
```

Each step gets highlighted as the user progresses.

## Technical Architecture

### Stack

| Component | Technology | Purpose |
|---|---|---|
| UI | Flet (Python) | Cross-platform desktop app |
| AI | Gemini Live API | Real-time voice + vision |
| Screen Capture | mss | Capture screen frames at 1 FPS |
| Voice | pyaudio | Audio input/output |
| Overlays | Flet Canvas | Render highlights, arrows, text |
| Character | SVG | Ghost animations |

### Gemini Live Integration

- **Model**: `gemini-3.1-flash-live-preview`
- **Protocol**: WebSocket (WSS)
- **Input**: Screen frames (JPEG, 1 FPS) + Audio (16kHz PCM)
- **Output**: Audio (24kHz PCM) + Function calls
- **Tools**: highlight_region, draw_arrow, show_step, show_todolist, complete_tutorial

### Function Calling Tools

```python
tools = [
    {
        "name": "highlight_region",
        "description": "Highlight a region on screen with colored box",
        "parameters": {
            "x": "number (0-1 normalized)",
            "y": "number (0-1 normalized)",
            "width": "number (0-1 normalized)",
            "height": "number (0-1 normalized)",
            "color": "string (red/blue/green/yellow/orange)",
            "label": "string (optional)"
        }
    },
    {
        "name": "draw_arrow",
        "description": "Draw arrow pointing to location",
        "parameters": {
            "from_x": "number", "from_y": "number",
            "to_x": "number", "to_y": "number",
            "color": "string"
        }
    },
    {
        "name": "show_step",
        "description": "Show step instruction in speech bubble",
        "parameters": {
            "step_number": "number",
            "instruction": "string",
            "total_steps": "number"
        }
    },
    {
        "name": "show_todolist",
        "description": "Show markdown todolist for complex tasks",
        "parameters": {
            "title": "string",
            "steps": "array of strings"
        }
    },
    {
        "name": "complete_tutorial",
        "description": "Tutorial completed successfully",
        "parameters": {
            "summary": "string"
        }
    }
]
```

## Ghost Character

### Design Principles

- **No mouth**: All expression through eye movement and transparency
- **Teal color**: #00D9A3 (distinct from Kiro's purple)
- **Glow effect**: Subtle glow for visibility
- **Floating animation**: Gentle up/down movement

### Animation States

| State | Eyes | Opacity | When |
|---|---|---|---|
| **idle** | Open, looking around | 0.7 | No activity |
| **watching** | Following cursor | 0.85 | Guiding user |
| **speaking** | Blinking (open/close) | 0.85 | Giving instructions |
| **happy** | Closed/squinted | 0.9 | Tutorial complete |
| **thinking** | Closed | 0.75 | Processing |

### SVG Files

- `idle.svg` — Original ghost, static
- `watch.svg` — Eyes shifted right (following)
- `speaking.svg` — Eyes as horizontal lines (blinking)
- `happy.svg` — Eyes slightly closed (satisfaction)

## MVP Scope

### IN SCOPE (Must Have)

- [ ] Ghost SVG floating on screen (transparent window)
- [ ] Gemini Live session (screen + voice)
- [ ] Function calling tools (highlight, arrow, step, todolist)
- [ ] Speech bubble (input/output)
- [ ] Step-by-step navigation
- [ ] Text + voice input
- [ ] Basic tutorial flow (send email)
- [ ] System prompt for KiroNav personality

### OUT OF SCOPE (Nice to Have)

- [ ] Deploy web (desktop only for MVP)
- [ ] Persistencia de datos
- [ ] Monetización real (concept only)
- [ ] Múltiples idiomas
- [ ] Historial de tutoriales
- [ ] Complex ghost animations (5 static SVGs sufficient)

## Monetization Concept

### Free Tier

- Simple tutorials (<10 steps)
- Examples: Send email, change settings, basic navigation
- Limited to 5 tutorials/day

### Pro Tier

- Complex tutorials (unlimited steps)
- Examples: Learn Figma, configure server, advanced workflows
- Unlimited tutorials
- Token-based pricing

### Enterprise

- Team onboarding
- Custom integrations
- Analytics dashboard
- Priority support

## Timeline

| Day | Date | Deliverable |
|---|---|---|
| 1 | Jul 22 | Ghost SVG + Gemini Live session + System prompt |
| 2 | Jul 23 | Function calling + Overlays + Basic tutorial |
| 3 | Jul 24 | UI polish + Voice input + Step navigation |
| 4 | Jul 25 | Real app testing + Prompt tuning + Edge cases |
| 5 | Jul 26-27 | Demo video + README + Deploy + Submission |

## Success Criteria

### Functional

- [ ] Ghost appears and floats on screen
- [ ] Gemini Live session connects successfully
- [ ] Screen frames stream to Gemini
- [ ] Voice input/output works
- [ ] Function calls render overlays
- [ ] Step-by-step guidance works for "send email" scenario

### Demo

- [ ] 5-minute video shows complete workflow
- [ ] Video includes: problem → solution → tech → monetization
- [ ] Repository public on GitHub
- [ ] README with setup instructions

### Hackathon

- [ ] RETO 3 submission complete
- [ ] All deliverables submitted
- [ ] Pitch ready: "Kiro ghost + navigation = KiroNav"
