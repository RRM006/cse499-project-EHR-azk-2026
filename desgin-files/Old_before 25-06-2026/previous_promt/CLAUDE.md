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
3. extracts clinical info, checks for emergencies, asks follow-up questions,
4. assesses risk, and produces a structured report for the doctor.

This is a **15-module** system. We build it one module at a time.
**Right now we are on Module 1 (live speech-to-text) + the text-correction step.**

## NON-NEGOTIABLE RULES (never break these)

1. **Never change the patient's exact words during transcription.** The raw
   transcript is stored unchanged. Any cleaning/correction happens in a
   *separate* later stage and is saved as a *separate* field. Raw is forever.
2. **The system never diagnoses.** It narrows the search space for the doctor.
   The doctor decides.
3. **Emergency detection is the top priority** once that module exists.
4. **Patient data is sensitive.** Never send real patient data to a free AI API
   that may train on it. Use synthetic or consented sample data during development.

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

## CURRENT STACK (decided — full reasons in agent_docs/decisions.md)

- Backend: Python + **FastAPI + WebSockets**
- Live STT (robust path): **faster-whisper** (CTranslate2, int8, CPU)
- Live STT (quick-start path): **browser Web Speech API** (Chrome, lang="bn-BD")
- Text correction: **swappable LLM** (Gemini Flash primary; Groq / OpenRouter fallback)
- Frontend: plain **HTML/JS first**, React later
- Mobile app comes later — so keep the backend API clean and reusable

## COMMANDS (fill these in as we build them)

- Create venv (Windows): `python -m venv .venv && .venv\Scripts\activate`
- Create venv (Linux):   `python -m venv .venv && source .venv/bin/activate`
- Install deps:  `pip install -r requirements.txt`   *(file: TBD)*
- Run backend:   *(TBD)*
- Run frontend:  *(TBD)*
- Run tests:     *(TBD)*

## FRONTEND / TRANSCRIPT UI (follow this)

- Overall visual design follows **`DESIGN-mintlify.md`** (Inter + Geist Mono,
  black pill buttons, mint-green accent reserved for CTA/active states, 12px cards,
  hairline borders, flat surfaces).
- The three transcript panels — **Raw**, **Corrected**, **Manual fallback** — share
  ONE behavior: fixed-height, vertically scrollable; auto-scroll to the newest line
  as text is added, but if the user scrolls up, pause auto-scroll and resume only
  when they scroll back to the bottom.
- Raw + Corrected are read-only (raw is never modified — rule #1); Manual is editable.
- Must stay responsive for very long transcripts (1000s of words) — never overflow
  or break the layout.

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

**At the END of every session**, update `changelog.md` and `current_task.md`
(and `milestone_log.md` / `decisions.md` / `test_log.md` / `codebase_map.md` if
they changed). The exact steps are in `session_protocol.md`.
