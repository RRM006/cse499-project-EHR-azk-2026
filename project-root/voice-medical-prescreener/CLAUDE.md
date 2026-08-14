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

This is a **15-module** system (Module 5 is retired in the current design — see below; S23 added
**M16**, a doctor-side drug-info assistant with a server-attached disclaimer — ADR-0044).
We build it one module at a time.
**Status (Session 25, 2026-07-12): BOTH build cycles COMPLETE + the HUMAN LIVE RUN PASSED.** The
original 20-step build AND the **"Context Fixed Problem 2.0" cycle** are done (teal redesign,
bilingual portals, background-assessed submit, Dhaka times, M16 assistant, and **real OTP**:
hashed/expiring/single-use codes behind a pluggable sender seam, `OTP_CHANNEL=dev|textbee`,
`000000` bypass dev-channel-only — ADR-0045). DB = Alembic head **0013**
(18 tables) as of S38 — it had held at 0012 since S25. **192 tests passed at S25; the current count
is 931 (see the S38 paragraph below).**
**S25: the human live real-mic run PASSED on Windows 11** — TC-V1/V2/V3/F2/R1 all ✅ (STT "very
accurate", ~2 s latency). On that gate **Modules 1-14 went ✅** (M5 retired, **M15 stays 🟨** =
future retrain/regression pipeline). What's left is NOT build work: **rotate the 3 API keys** before
any public demo (still pending) + optionally log formal WER/precision-recall as thesis evidence.
Manual-testing findings go in `agent_docs/context fixed problem 3.0.md`; the three faculty future
requirements in `agent_docs/faculty_future_features.md`.
**The faculty Requirement 3 + 3b build (voice-first Patient Portal, ADR-0048 — supersedes
ADR-0027's voice-only rule) is built through Step S4** — mic opens itself after TTS → visible 3-2-1
confirmation window → the turn ends on silence → next question, **with typing always available as
the fallback** (S1 = `voice_loop` config + `GET /api/config`; S2 = the `[🎤 Speak] [⌨ Type]` switch;
S3 = auto-listen behind an echo guard; S4 = the endpointer). Plan + 12-point live checklist:
`faculty_future_features.md` §A–K. **⛔ Step S5 is NOT built** (`no_speech_ms` watchdog,
`max_answer_ms` cap, permission/visibility recovery) — verified absent and pinned by a test; its
permission/visibility half is **blocked** on the open mid-turn word-loss rule #1 decision, which is
the human's to make. **S6–S7 are not built either** and each needs its own "go".
**Session 38 (2026-08-14) completed a nineteen-item staff-portal UX + clinical-workflow brief**
(A1-A7 medic, B1-B7 doctor, C1-C4 workflow) — ADRs **0060/0061/0062/0063**, and the first schema
change since S25: **Alembic 0012 → 0013**, deliberately just **one column (`patients.height_cm`) and
one table (`clinical_notes`)**, no new dependency. Most of the brief added **no storage at all**.
**MEDIC:** "Triage" is explained where the word is used; the 10/10 line became an interactive
segmented meter that names which fields are empty; **Intake & Vitals was rebuilt into a real form**
with height and a **live BMI** (WHO + WHO **Asian** bands, derived and never stored); and the queue's
auto-refresh — which had been **silently replacing a medic's phone-search result every 15 s** — now
holds on a search, holds on a hidden tab, says which state it is in, and stops re-flashing the list.
⚠ **A6: the human asked for "a diabetic limit"; there is no such number**, so the portal shows the
published chart (fasting / OGTT / random / HbA1c) with the sample conditions each row depends on,
both unit systems, and the WHO-vs-ADA disagreement stated out loud — `glucose_reference()` takes
**no argument at all**.
**DOCTOR:** the prescription is **inline at the bottom of the case** instead of replacing it;
Advice and Required Tests are two vertical cards; **Required Tests is a searchable token editor**
over a ~50-entry bilingual vocabulary (a module, not a table) where **Enter always commits what was
typed**; "Assigned (0)" says what its emptiness means; and **"Accept & Write to EHR" now produces an
actual record** — an **HL7 FHIR R4 document Bundle** served as `application/fhir+json` through the
existing documents table. ⚠ Claimed honestly as *structurally valid and semantically conservative*
— not certified, not profiled. ⚠ **The AI suggested condition is excluded from it entirely** (the
disclaimer does not survive ingestion elsewhere); the doctor's own diagnosis is exported.
**DATES (ADR-0061):** policed **by category** — historical timestamps are never touched, a
prescription must be dated today, a follow-up/recall must not be in the past — enforced server-side
BEFORE the write. It fixed a real bug: the form stamped the **UTC** date, so a prescription written
between midnight and 6 a.m. Dhaka was dated the previous day. All staff clocks are now 12-hour with
a live Dhaka header clock; server-side "today" uses a **fixed UTC+06:00 offset, not `ZoneInfo`**
(Windows has no tz database; Bangladesh has had no DST since 2010).
**M16 (ADR-0063)** widened to medicines **and diagnostic tests** and, on **explicit opt-in**, which
tests might suit this patient. ⚠ The web search receives the doctor's typed question **and nothing
else, by signature**; the LLM's case context is de-identified and carries **no raw transcript**;
suggested tests are chips the doctor **clicks** in — nothing is ordered until a human generates the
prescription.
**C1-C4** — the four features S37 deferred are all built, each only after the reason for deferring
it was removed: the medic's referral history is **derived from `audit_log.actor_id`** and reports
what it **cannot** attribute; per-field verification lives inside the existing `summary_fields` JSON
and **does not touch the value or `source`**; and the recall and the doctor→medic note share one
table, addressed to a **role**, with no thread and no reply. → **931 tests pass, 2 skipped.**

**Session 37 (2026-08-13) gave the two STAFF portals their ROLES** (ADR-0058/0059): the medic queue
ordered by **urgency** not recency, wait/red-flag/completeness chips, a floor-load strip, **vitals
captured BEFORE the referral**, an **advisory** handover check that **can never block a forward**,
and referrals attributed to the forwarding medic; for the doctor, a patient **timeline** +
prescription history (`prescriptions` had been a *write-only* table) and a **Completed** scope so a
reviewed case stays reachable. Every S37 view is derived and read-only. UI:
`frontend_shared/motion.css` (staff only; every animation behind `prefers-reduced-motion`).
→ 767 tests. Full role/ownership reference: **`agent_docs/portal_roles.md`**.
**Sessions 34-36 ran three manual-testing/hardening cycles** (ADR-0055/0056/0057): the spoken-answer
read-back, spoken yes/no confirmation, one header clock, TTS pacing, and in **S36** a real
**patient-session boundary** (an epoch stopping one patient's in-flight responses reaching the
next), the phone number ending its own turn at eleven digits, "ঠিক আছে" finishing the review, the
auto-downloading raw transcript, an **output guard on M7's question**, and **MCP evaluated and
REJECTED** (ADR-0057 b). → 723 tests. Details: `changelog.md`.
⚠ **Real-mic status (unchanged since S37; S38 touched no voice code):** the human confirmed the
real-microphone run of the **S33-S36** voice changes **was carried out**. Recorded exactly that far:
**no per-claim results were supplied and none are documented**, and no defects came back. Do not
repeat "no microphone has exercised S33-S36" (no longer true), and do not upgrade the three specific
S36 claims to "verified" (no evidence). S25's itemised evidence stands unchanged.

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
- Frontend: plain **HTML/JS** (clinical-blue design system — ADR-0029, see below); React only "later", not now
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

## VOICE INTERACTION RULES (ADR-0027/0028, amended by ADR-0048)

- **VOICE IS THE PRIMARY / DEFAULT patient interaction — voice-first is the goal, not an
  option.** The portal should actively guide the patient toward speaking: AI speaks → mic
  opens itself → patient speaks → visible 3-2-1 countdown → submit → next question.
  **Typing is ALWAYS available** as the fallback/alternative so a patient is never blocked
  by a failed mic, a noisy room, poor recognition, or personal preference.
  ⚠ **This supersedes the old "patient input is VOICE ONLY / keyboard is a mic-failure
  fallback only" rule** (ADR-0027, as narrowed by ADR-0030). Do not re-apply the old rule.
- **One pipeline for both modes:** spoken and typed answers use the SAME endpoint and flow,
  differing only in `source` (`mic` | `manual`). Never build a second question/answer path.
- **UX priority: minimize clicks, waiting and complexity** — the target user is elderly or
  non-technical. The 3-second countdown is a **CONFIRMATION window, never a hard cutoff**:
  any resumed speech cancels it. A clipped answer is a **rule #1 defect**, not a UX nit.
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

## FRONTEND (follow this)

- **Design system = the shared token system in `frontend_shared/shared.css`** (structure per
  ADR-0029; palette evolved to **"Teal Medical"** in the 2.0 build STRUCT-3, ADR-0043): deep teal
  `#0F766E` primary, teal `#0D9488` secondary, green accent `#10B981`, teal-tinted bg `#F0FBF8`,
  10px radius, Inter for UI. It SUPERSEDES the old Mintlify rule; `DESIGN-mintlify.md` is kept only
  as historical reference (marked superseded at its top). The three portals share
  `frontend_shared/` (shared.css, shared.js with the ONE `TIER_LABELS` map, staff.js, tts.js).
- **`frontend_shared/motion.css` = the STAFF depth/motion layer (S37, ADR-0059).** Loaded by
  `/medic/` and `/doctor/` **after** shared.css; the kiosk must NOT load it. Rules: every
  `animation`/`@keyframes` stays inside `@media (prefers-reduced-motion: no-preference)`, nothing is
  conveyed by movement alone, only composited properties animate, and a looping animation is
  reserved for urgency. The two staff portals must never read as one screen (medic = amber `TRIAGE`
  operations desk, doctor = indigo `CLINICAL` workspace) — see `agent_docs/portal_roles.md`.
- **Bangla text always uses Noto Sans Bengali (NOT mono — mono breaks Bangla shaping).**
- **Bilingual EN/BN** via `data-en` / `data-bn` attributes + the `setLanguage()` helper.
- **Raw is never shown as editable and never modified (rule #1).** The medic/doctor 10-field
  cards edit only the DERIVED `summary_fields` (source becomes `human`); the verbatim panel is
  read-only. Risk tier codes on the wire are always `low|medium|high|critical`; display labels
  (incl. "Moderate", Bangla) live ONLY in `TIER_LABELS`.
- The legacy Module-1 transcript app (`frontend/index.html` + `app.js`) is unchanged and still
  served at `/`; its Raw/Corrected/Manual panels keep the fixed-height + stick-to-bottom scroll
  behavior. Kiosk = `/kiosk.html`; medic = `/medic/`; doctor = `/doctor/`.

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
10. `agent_docs/context fixed problem 3.0.md` — the NEXT fix/feature cycle (human pastes raw
    findings from manual testing; we turn them into a numbered, checkable tracker like 2.0)
11. `agent_docs/portal_roles.md` — what the patient/medic/doctor portals are each FOR, per-role
    feature tables, use cases, the data-ownership matrix, and what was deliberately NOT built
    (read this before adding anything to `/medic/` or `/doctor/`)
12. `agent_docs/faculty_future_features.md` — faculty-required FUTURE work, 3 requirements
    (quantized Moshi summary model + quantized on-device STT/TTS + fully voice-driven follow-up
    conversation) — research track, NOT current build work

**At the END of every session**, update `changelog.md` and `current_task.md`
(and `milestone_log.md` / `decisions.md` / `test_log.md` / `codebase_map.md` if
they changed). The exact steps are in `session_protocol.md`.
