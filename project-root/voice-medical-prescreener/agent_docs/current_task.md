# current_task.md — What We Are Doing RIGHT NOW

> This is a small, throwaway snapshot. It gets **overwritten** every session.
> It is NOT a history log (that is `changelog.md`). It answers only:
> "If I open a brand-new Claude Code session, what do I need to know to continue?"

---

**Date:** 2026-06-19
**Phase:** Phase 0 — Quick working demo
**Module:** Module 1 — Speech-to-Text (+ the correction step)

## Where we are right now
Scaffolding (Step 1) and the backend skeleton (Step 2) are DONE and verified:
- `requirements.txt`, `.gitignore`, `backend/.env` + `.env.example` exist.
- Backend skeleton built: `backend/app/core/config.py`, `backend/app/db/`
  (database.py, models.py `Utterance`, repository.py), `backend/tests/`.
- `.venv` created, deps installed (Python 3.14.4, Windows), `pytest` = 3 passed.
- Raw-immutability guard is in place and passing (constitution rule #1).

We follow a 6-step build order and STOP for review between each step. Steps 1–2
are complete. **No Gemini code, no API routes, no frontend yet.**

## The one thing we are doing next
**Step 3 — the correction service (no API routes yet).** Build:
- `backend/app/services/correction/base.py` — `Corrector` ABC: `correct(raw_text) -> str`.
- `backend/app/services/correction/openai_compatible.py` — `OpenAICompatibleCorrector`
  using the `openai` SDK pointed at Gemini's OpenAI-compatible base URL (from config).
  Strict prompt: "Correct spelling/grammar of this Bangla / Banglish / Roman-Bangla
  medical utterance. Do NOT add, remove, translate away, or infer any symptom or
  meaning. Return only the corrected text." Raw is sent; raw is never overwritten.

This is the FIRST step that can hit the network, so the real key-using call stays
behind a tiny manual check the human runs themselves — do not auto-call Gemini.

## Exact next step for Claude Code
Show the plan for the two files above, then wait for "go" before writing them.

## BLOCKER / action for the human
- **REGENERATE the Gemini key** (the one pasted in chat is compromised) and put the
  new value in `backend/.env` (replace `PASTE_YOUR_REGENERATED_KEY_HERE`).
  Step 3 code can be written without it, but testing the live call needs it.

## Reminders
- Raw words are never edited (constitution rule #1). Correction is a separate field.
- Plan first, code second, one small step at a time. Do not assume. (CLAUDE.md)
- Cross-platform (Windows + Linux). Run commands from the project root.
  Run app:  `uvicorn backend.app.main:app --reload`   Test:  `pytest backend/tests/`
- Python 3.14 needs SQLAlchemy >= 2.0.51 (older pins crash).
