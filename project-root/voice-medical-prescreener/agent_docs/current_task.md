# current_task.md — What We Are Doing RIGHT NOW

> This is a small, throwaway snapshot. It gets **overwritten** every session.
> It is NOT a history log (that is `changelog.md`). It answers only:
> "If I open a brand-new Claude Code session, what do I need to know to continue?"

---

**Date:** 2026-06-19
**Phase:** Phase 0 — Quick working demo (now multi-provider STT)
**Module:** Module 1 — Speech-to-Text (+ the correction step)

## Where we are right now
The app supports **5 swappable STT providers** with a frontend dropdown, all
installed and reporting "available" on the Windows dev box:
- browser_webspeech (live, Chrome/Edge) · groq_whisper (cloud) ·
  local_whisper (faster-whisper) · banglaspeech2text (transformers, shhossain/
  whisper-*-bn) · qwen_asr (Qwen3-ASR-1.7B, local).
- Pipeline unchanged: mic → STT provider → RAW (immutable, stored) → Gemini → corrected.
- Backend: `backend/app/services/stt/` (ABC + registry + health + audio decode + 5
  providers). Endpoints: `GET /api/stt/providers`, `POST /api/transcribe`,
  `POST /api/transcripts`, `POST /api/correct` (by utterance_id), `GET /api/transcripts`.
- Frontend: provider dropdown + status badges, Start/Stop, MM:SS timer + 5-min
  auto-stop, raw/corrected panels (copy/clear), manual fallback, error banner.
- Tests: `pytest backend/tests/` = **13 passed**. Verified the decode→transcribe
  code path for local_whisper and banglaspeech2text with a synthetic clip.

Install layout: core = requirements.txt; optional engines = requirements-whisper.txt,
requirements-banglaspeech.txt, requirements-qwen.txt. Full guide in INSTALL.md.

## Known caveats to carry forward
- `qwen-asr` is INVASIVE: installing it bumped fastapi→0.137, starlette→1.3,
  transformers→4.57, huggingface_hub→0.36 (+gradio/flask). App still works, but if it
  destabilizes, run Qwen in its OWN venv.
- Live Groq STT and a live Qwen run were NOT done (quota / 3.4 GB + slow CPU).
- The Groq key was pasted in chat earlier — human should REGENERATE it.
- `.env` changes need a server RESTART (uvicorn --reload only watches .py).

## The one thing we are doing next
**Human-driven live testing of all providers + sample collection.**
1. Run server, open http://localhost:8000 in Chrome (keys in backend/.env).
2. For each provider: record Bangla/Banglish/Roman Bangla → confirm RAW is verbatim,
   Correct works, raw never changes. Note rough latency + did correction preserve meaning.
3. First Qwen click downloads ~3.4 GB and is slow — expect a long wait.
4. Collect ~50 sample utterances (Phase 0 "move on" gate); record latency/WER in test_log.

## Exact next step for Claude Code
Wait for the human's live-test results. Then: help debug any provider failures,
record numbers in `test_log.md`, and (optional) add a mocked test for
`POST /api/transcribe` / `/api/correct` so CI covers the routes offline.

## Reminders
- Raw words are never edited (rule #1). Correction is a separate field/column.
- Synthetic/consented data only — cloud STT (Groq) + Gemini may log input (rule #4).
- Plan first, one small step at a time. Do not assume. (CLAUDE.md)
- Run (Windows): `.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8000`
- Run (Arch):    `.venv/bin/python -m uvicorn backend.app.main:app --reload --port 8000`
- Tests: `pytest backend/tests/`  ·  Python 3.14 needs SQLAlchemy>=2.0.51 & torch>=2.9.
