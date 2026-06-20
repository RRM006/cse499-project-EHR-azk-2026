# Installation Guide — Voice Medical Pre-Screener

Works identically on **Windows** and **Arch Linux**. Python 3.11+ (3.14 OK).
Module 1 uses the **browser Web Speech API** for speech-to-text (client-side, in
Chrome/Edge) — there is nothing heavy to install and no ML dependencies.

## Setup

```bash
# from the project root: voice-medical-prescreener/
python -m venv .venv
# Windows (if blocked by execution policy, run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process` first):
.venv\Scripts\activate
# Arch Linux:
source .venv/bin/activate

pip install -r requirements.txt
cp backend/.env.example backend/.env   # then add your Gemini key
```

Set `GEMINI_API_KEY` in `backend/.env` (free key: https://aistudio.google.com/apikey).
Used only for the **Correct** step.

## Run

```bash
python -m uvicorn backend.app.main:app --reload --port 8000
# open http://localhost:8000 in Chrome or Edge (the mic needs the Web Speech API)
```

> Restart the server after editing `backend/.env` — uvicorn's `--reload` only
> watches `.py` files.

## The pipeline

Microphone → Chrome Web Speech API → **Raw transcript (immutable, stored)** →
Gemini Flash → **Corrected transcript** (separate panel; raw is never modified).

- Recording is continuous: speak as long as you want; brief pauses keep going; it
  auto-stops after ~10 s of continuous silence (or when you click Stop).
- A manual text box is provided as a fallback when the mic isn't usable.

## Tests

```bash
pytest backend/tests/          # offline; no network
```

## Notes

- Speech recognition needs **Chrome/Edge + internet** (Google's engine); the page
  shows a clear message in unsupported browsers.
- Use **synthetic or consented** data only — Gemini may log free-tier input.
- Other STT engines (local/offline) were removed for Module 1 and may return in a
  later module; the backend keeps a clean seam for that.
