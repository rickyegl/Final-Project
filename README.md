# Baldi Teacher Chatbot

Graphical AI teacher chatbot starring Baldi from *Baldi's Basics*, backed by the Google Gemini API. Built with modular components so you can scale into web services, messaging bots, or classroom tooling.

## Features
- Friendly desktop window with formatted responses (headings, emphasis, bullet points)
- Baldi persona prompt that blends humor with positive teaching tone
- Config-driven runtime (model, sampling options, history length)
- Gemini API client encapsulated for easy reuse or swapping providers
- GUI sits atop the same modular bot so you can still embed it in other apps or services

## Quick Start
1. **Install dependencies**
   ```bash
   pip install -e .
   ```
2. **Set your Gemini API key**
   ```bash
   export GEMINI_API_KEY="your-key"
   ```
   On Windows PowerShell:
   ```powershell
   $env:GEMINI_API_KEY="your-key"
   ```
3. **Run the graphical chatbot**
   ```bash
   python -m src.main
   ```
   or use the console script
   ```bash
   baldi-teacher
   ```

Want the original terminal experience?
   ```bash
   baldi-teacher-cli
   ```

Type `exit` or `quit` to end the session.

## Configuration
- Override runtime options via CLI flags (e.g., `--model`, `--history`, `--temperature`).
- Environment variables prefixed with `BALDI_` also work, for example `BALDI_MODEL`.
- Supply `--persona` with a text file to customize Baldi's personality for different classrooms.
- A Baldi image overlay appears in the lower-left corner by default, loading from `assets/baldi.webp`; point at a different asset with `--overlay-image` or disable with `--no-overlay`.
- The GUI swaps to `assets/thinking.png` while Baldi prepares a reply; override with `--thinking-image` for custom reactions.
- A local `.env` file is read automatically; set `GEMINI_API_KEY` there to avoid exporting variables each session.
- Resize the overlay with `--overlay-width` / `--overlay-height` (defaults 320px), or pass `0` to leave the image original size.
- On Windows the overlay background is transparent by default; use `--overlay-opaque` if the effect looks odd or your Tk build lacks support.

## Scaling the Bot
- `baldi_teacher/gui.py` hosts the Tkinter experience; repurpose it for whiteboard tools or teaching dashboards.
- `baldi_teacher/teacher_bot.py` cleanly separates conversation management from transport.
- `baldi_teacher/gemini_client.py` wraps Google Gemini calls; replace it to target other LLMs.
- Package entry point (`baldi-teacher`) and `AppConfig` make it straightforward to embed the bot in services, workers, or batch jobs.

## Development
- Run `pytest` to execute unit tests (none included yet).
- Contributions should keep persona prompts fun but respectful; Baldi motivates, never intimidates.
