# CLAUDE.md — Voice Medical Pre-Screener

> Claude Code reads this file automatically at the start of every session.
> Keep it SHORT (under ~200 lines). The detailed, living docs live in
> `agent_docs/` and are listed at the bottom of this file.

## What this project is

An AI-powered, voice-based medical **pre-screening** system for Bangladesh.
A patient speaks naturally — in Bangla, Banglish (Bangla + English mixed), or a
regional dialect — *before* they see the doctor. The system:

1. transcribes their speech live,
2. cleans/corrects the text (in a separate step),
3. extracts clinical info, asks follow-up questions (spoken aloud + on screen),
4. assesses risk, and produces a structured report for the doctor.

This is a **15-module** system (Module 5 is retired in the current design — see below).
We build it one module at a time.
**Right now we are on Module 1 (live speech-to-text) + the text-correction step.**

## NON-NEGOTIABLE RULES (never break these)

1. **Never change the patient's exact words during transcription.** The raw
   transcript is stored unchanged. Any cleaning/correction happens in a
   *separate* later stage and is saved as a *separate* field. Raw is forever.
2. **The system never diagnoses.** It narrows the search space for the doctor.
   The doctor decides.
3. **Surface red flags; never reassure falsely.** The standalone emergency module
   (old M5) and its escalation alert were removed from the flow (ADR-0024); a
   lightweight **rule-based red-flag check now lives inside M10 (Risk Assessment)**,
   so clearly life-threatening symptoms still get flagged to the doctor. This
   version does **not** perform autonomous emergency triage/escalation.
4. **Patient data is sensitive.** Never send real patient data to a free AI API
   that may train on it, and Web Speech API sends audio to Google's cloud — so use
   **synthetic or consented sample data only** during development.

## HOW I WANT YOU (CLAUDE CODE) TO WORK WITH ME

- **Do NOT assume anything. Always plan with me first, then wait for my "go".**
- Before writing code, show a short plan: which files, what approach, and why.
- When there is a real choice, give me 2–3 options with simple trade-offs.
- Make **small, reviewable changes — one step at a time.** No giant code dumps.
- Everything must work on **both Windows and Arch Linux** (see constraints below).
- If anything is unclear, **ASK me. Do not guess.**

## TECH CONSTRAINTS (the hardware reality — respect this)

- **No NVIDIA GPU.** Two dev machines:
  - Windows desktop: Ryzen 5 3500X (6 core), 24 GB RAM, Radeon RX 570 (8 GB).
  - Arch Linux laptop: Ryzen 5 5500U (6c/12t), 12 GB RAM, integrated Vega.
- **CPU-only by default.** Do NOT depend on GPU acceleration (AMD GPU support for
  ML is unreliable on these cards — treat any GPU speedup as a bonus only).
- **Free / open-source strongly preferred.** Free APIs allowed where needed.
- Must run on Windows AND Linux from **one `requirements.txt` + a venv.**

## CURRENT STACK (LOCKED — full reasons in agent_docs/decisions.md ADR-0024..0028)

- Backend: Python 3.14 + **FastAPI + Uvicorn** (REST now; native WebSocket reserved for Phase 1 streaming)
- Database: **SQLite** via SQLAlchemy + **Alembic** migrations (config-driven URL → Postgres later)
- Live STT (quick-start path, current): **browser Web Speech API** (`SpeechRecognition`, Chrome/Edge, `lang="bn-BD"`)
- Live STT (robust path, Phase 1): **faster-whisper** (CTranslate2, int8, CPU)
- TTS for M7 audio: **browser Web Speech API** (`SpeechSynthesis`) — no server, no key
- Text correction / LLM tasks: **swappable OpenAI-compatible client** (one `Corrector`/provider class; `base_url`+model+key from `.env`)
- Document export: **python-docx** (DOCX now; PDF later behind the format seam)
- Frontend: plain **HTML/JS** (Mintlify design system); React only "later", not now
- Deployment: local = one `uvicorn` command; optional remote = single Docker container / free PaaS

## AI API STRATEGY (free-tier longevity — details in decisions.md ADR-0026)

All providers are OpenAI-compatible, so one client + a config swap covers everything.
Spread load across **three independent daily buckets** so no single quota is the bottleneck:
- **Gemini 3 Flash** (free, ~1,500 req/day, resets midnight PT) → quality tasks: M2 correction, M4 summary, M11 XAI, M12 prose.
- **Gemini Flash-Lite** (higher RPM) → cheap structured extraction: M3, M8 (protects the main Flash quota).
- **Groq** Llama 3.3 70B (very fast LPU, ~1,000 req/day, resets midnight UTC) → live-loop tasks: M6, M7.
- **OpenRouter `:free`** → universal fallback (tip: a one-time $10 top-up raises 50→1,000 req/day).
- M1 STT, M9 completion check, M13/M14/M15 = **LOCAL / NO-API**.
- ⚠ Free tiers may train on inputs → synthetic/consented data only (rule #4).

## VOICE INTERACTION RULES (CONFIRMED CHANGE 2 — ADR-0027/0028)

- **Patient input is VOICE ONLY** (no keyboard for the patient). A manual text box
  stays only as a developer/accessibility **fallback** when the mic fails (rule: Module 1 fallback).
- **M7 follow-up questions display as TEXT on screen AND play as AUDIO (TTS) simultaneously.**
- STT: `webkitSpeechRecognition`, `lang='bn-BD'`, `continuous=true`, `interimResults=true`.
- TTS: `speechSynthesis.speak(new SpeechSynthesisUtterance(text))`, `lang='bn-BD'`
  (pick a Bangla voice if installed, else default). Always keep the on-screen text as the fallback.

## COMMANDS

- Create venv (Windows): `python -m venv .venv && .venv\Scripts\activate`
- Create venv (Linux):   `python -m venv .venv && source .venv/bin/activate`
- Install deps:  `pip install -r requirements.txt`
- Run (Windows): `.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Run (Arch):    `.venv/bin/python -m uvicorn backend.app.main:app --reload --port 8001`
- Open:          http://localhost:8001 (Chrome)
- Run tests:     `pytest backend/tests/`

## FRONTEND / TRANSCRIPT UI (follow this)

- Overall visual design follows **`DESIGN-mintlify.md`** (Inter + Geist Mono,
  black pill buttons, mint-green accent reserved for CTA/active states, 12px cards,
  hairline borders). Transcript text uses Inter + **Noto Sans Bengali** (NOT mono — mono breaks Bangla).
- The transcript panels — **Raw**, **Corrected**, **Manual fallback** — share ONE
  behavior: fixed-height, vertically scrollable; auto-scroll to the newest line, but
  if the user scrolls up, pause auto-scroll and resume only at the bottom.
- Raw + Corrected are read-only (raw is never modified — rule #1); Manual is editable.
- Must stay responsive for very long transcripts (1000s of words).

## PROJECT MEMORY FILES — our shared brain (in `agent_docs/`)

**At the START of every session, read these in order:**
1. `agent_docs/session_protocol.md` — exactly how we start and end a session
2. `agent_docs/current_task.md` — what we are doing RIGHT NOW + the next step
3. `agent_docs/changelog.md` — recent session history (newest entry first)
4. `agent_docs/milestone_log.md` — status of all 15 modules

**Read these when relevant:**
5. `agent_docs/constitution.md` — full, stable project rules + architecture
6. `agent_docs/decisions.md` — why we chose each tool/library (ADR style)
7. `agent_docs/codebase_map.md` — where everything lives in the repo
8. `agent_docs/test_log.md` — what was tested + results (WER, accuracy, etc.)
9. `agent_docs/update_system_flowchart.md` — TikZ source of the Patient Journey flow

**At the END of every session**, update `changelog.md` and `current_task.md`
(and `milestone_log.md` / `decisions.md` / `test_log.md` / `codebase_map.md` if
they changed). The exact steps are in `session_protocol.md`.
