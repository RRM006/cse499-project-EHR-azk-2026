# milestone_log.md — Big-Picture Status Board

> This answers one question: **"Where are we in the whole project right now?"**
> Update the status when a module's state changes. Keep the "Done means" line
> honest and testable — not "works well", but a real, checkable definition.

**Status keys:** ⬜ Not started · 🟨 In progress · 🟦 Blocked · ✅ Done · ⛔ Retired

**Last updated:** 2026-07-05 (Session 9 — Part-2 human test done → fix/feature build started)
**Current phase:** Fix/feature build from the human's Part-2 live test — 20-step approved plan
(spec: `context_fixed_problem.md`), one step per "go". Steps 1–5 DONE (legacy isolation
ADR-0031; Alembic 0010 applied ADR-0032; visit-grain docx seam — transcript + summary_report
export routes live; shared.js `fieldValue()` + C2 `TIER_BANDS`; M3/M8 bilingual values
ADR-0033 — `value_en`+`value_bn` in one extraction call, full back-compat). **121 tests pass.**
**Module in focus:** cross-cutting (portals + kiosk); next = step 6 (kiosk OTP auto-advance).
**Progress:** Session 8 built the reconciled system end to end (see `changelog.md` S8 +
`reconciliation.md`). **DB:** all 15 architecture.md tables applied (Alembic head `0009_audit_log`).
**Backend:** kiosk phone + stub OTP → visit; intake (M3/M4/M6); follow-up loop (M7/M8/M9);
**M10 risk with a LOCAL red-flag rule that forces Critical even if every LLM is down** + M11 XAI;
M12 local report (Red Flags + no-diagnosis disclaimer); staff submit→auto-assess→queue→assign→
review→feedback; audit_log on every state change. **Frontend:** patient kiosk (`/kiosk.html`),
medic (`/medic/`), doctor (`/doctor/`) — clinical-blue design (ADR-0029), bilingual, TTS+STT.
**104 tests pass.** Everything below moves off ⬜; most modules are ✅-on-happy-path but stay
🟨 until the human live run records real numbers (TC-V2/V3/F2/R1/A1) with real API keys. Module 1
also still awaits the live mic test + ~50 samples + WER/latency.
**Session 8b:** the ADR-0029 design-system switch is now reflected in the docs (CLAUDE.md +
DESIGN-mintlify SUPERSEDED). **First live Gemini call verified** (M2 correction, correction-only).
**Live-run key gap:** only Gemini is keyed — Groq + OpenRouter empty, so M6/M7 can't run live until
a key is added (all still pass offline). No module status changed from Session 8.
**Session 8c:** key gap CLOSED (all three keys in `backend/.env`). **Live-run Part 1 PASSED** —
the full M3→M12 pipeline ran live with synthetic typed text; `module_events` shows every module
on its ADR-0026 bucket (M3/M8 flash-lite, M4/M10/M11 flash, M6/M7 groq, M12 local), 13/13 ok,
zero fallbacks, latencies 0.5–8.6 s. 104 tests still pass. Modules stay 🟨 (not ✅) because the
statuses gate on the HUMAN real-voice run (TC-V2/V3/F2/R1/A1) — that is now the only thing
between most modules and ✅-on-live-path. M1 also still awaits the mic test + ~50 samples + WER.
**Session 9:** the human RAN the Part-2 real-mic test; findings became the work spec
`context_fixed_problem.md` (STRUCT/KIOSK-1..7/MEDIC-1..7/DOCTOR-1..7) and a 20-step plan was
approved (decisions locked in `current_task.md`: C1 suggestion-not-diagnosis, C2 display-only
risk bands, DB-backed prescriptions/reports via Alembic 0010, stored bilingual values, DB
letterhead, KIOSK-7 resume loop). Step 1 DONE: legacy demo isolated at `/legacy/`, landing page
at `/`, startup entry-point log (ADR-0031). Step 2 DONE: Alembic **0010** applied (nullable
`documents.utterance_id` for visit-grain exports, patient vitals, letterhead columns,
`prescriptions` table — ADR-0032, architecture.md §8). **113 tests pass.** Module statuses
unchanged — the affected areas (M7 loop UX, M12 exports, M14 dashboards) move when their
steps land.

---

## The 15 modules

| # | Module | Status | "Done" means (testable) |
|---|--------|:------:|--------------------------|
| 1 | Speech-to-Text | 🟨 | Live mic audio is transcribed and the **raw** Bangla/Banglish text appears on screen within ~3s; raw text is stored unchanged; works on both Windows and Linux; manual text-input fallback exists. |
| 2 | Text Processing & Normalization | 🟨 | Given raw text, a separate cleaned/normalized field is produced (spelling, fillers removed, sentence boundaries); raw is never modified; measured on a small test set. **Built** (existing `/api/correct` corrector, reused as M2); live accuracy on a test set still pending. |
| 3 | Information Extraction | 🟨 | From normalized text, symptoms / body part / duration / severity / meds / history are extracted as structured fields; precision & recall recorded in test_log. **Built** (`services/intake.py`, M3 → 10-field `summary_fields` JSON); precision/recall on real data pending. |
| 4 | Initial Clinical Summary | 🟨 | A 2–4 sentence chief-complaint summary is generated from extracted fields and shown to the doctor. **Built** (`services/intake.py`, M4). |
| 5 | ~~Emergency Detection~~ | ⛔ | **RETIRED (Session 7, ADR-0024).** The standalone module + its flowchart diamond/alert are removed. Its job is now a **rule-based red-flag check inside Module 10** (see M10). Number 5 is left as a permanent gap so M6–M15 keep their IDs. |
| 6 | Missing Information Analysis | 🟨 | System outputs a checklist of present vs. missing data points for the case. Now fed **directly by M4** (M4→M6, no emergency branch). **Built** (`services/intake.py`, M6 → `case_profiles.gaps`). |
| 7 | Follow-up Question Generation | 🟨 | System generates prioritized follow-up questions (Bangla/English) for the gaps, no repeats of answered items; each question is **shown as text AND spoken via TTS**, and the patient replies **by voice only** (ADR-0027/0028). **Built** (`services/followup.py` + kiosk STT/TTS); live voice loop pending (TC-V3/F2). |
| 8 | Response Processing & Profile Update | 🟨 | Patient answers are re-processed and merged into the profile with conflict handling. **Built** (`services/profile_update.py`, M8; human-edited fields are never overwritten). |
| 9 | Case Completion Check | 🟨 | A completeness score is computed; loops back to Module 7 until threshold or max turns reached. **Built** (`services/completion.py`, LOCAL; threshold + max-turn exit, both env-tunable). |
| 10 | Risk Assessment Engine | 🟨 | Each case is classified Low/Medium/High/Critical from rules + model; **a rule-based red-flag check forces Critical for clearly life-threatening symptoms (chest pain, stroke signs, severe breathing difficulty, loss of consciousness) and surfaces them prominently**; accuracy + red-flag recall recorded on a labeled test set. **Built** (`services/risk.py` + `red_flags.py`; rule survives total LLM outage; red-flag recall enforced per-phrase in tests). Accuracy on labeled real data pending. |
| 11 | Explainable AI (XAI) | 🟨 | Every risk output has a plain-language reason listing the contributing factors. **Built** (`services/risk.py`, M11; deterministic fallback so no risk row is ever reason-less). |
| 12 | Structured Clinical Report | 🟨 | A full report (all sections) is generated and exportable as PDF + dashboard view; contains **no diagnosis**; includes a **Red Flags** section sourced from M10. **Built** (`services/report.py`, LOCAL assembly + disclaimer; shown in doctor portal). Per-visit `.docx` export of the summary report + raw transcript SHIPPED (S9 step 3, `visit_docx.py`); PDF still pending. |
| 13 | EHR Database | 🟨 | Transcripts, profiles, reports, and audit logs are stored and retrievable by patient ID/date; data encrypted. **Built** (all 15 tables, Alembic head `0009`; retrieval by phone + status; `audit_log` on every state change). Encryption-at-rest still pending. |
| 14 | Doctor Dashboard | 🟨 | Web UI shows report, risk, flags, XAI; doctor can override/annotate; high/critical cases alerted. **Built** (`frontend_doctor/`: queue, risk/red-flags/XAI panel, field edit, Override/Accept). |
| 15 | Feedback & Continuous Learning | 🟨 | Doctor feedback is collected and usable to retrain/fine-tune; regression check before deploying updates. **Built** (feedback stored via `POST /api/visits/{uuid}/feedback`); retrain/regression pipeline still future. |

---

## Roadmap phases (how we get Module 1 right first)

These come from the build plan. Each phase has a clear "move on when" gate.

### Phase 0 — Quick working demo  ⬅️ WE ARE HERE (planning locked; starting Phase A next)
**Goal:** Prove the whole loop (live voice → raw text → corrected text → screen)
with zero ML setup, using the browser Web Speech API + one free LLM for correction.
**Move on when:** I can speak Bangla/Banglish into the browser, see the raw text
live, see a corrected version beside it, and the raw text is stored unchanged.
(Also: ~50 real sample utterances collected for later testing.)
**Build steps (6):** 1 scaffolding ✅ · 2 backend skeleton ✅ · 3 correction service ✅
· 4 API routes + static serving ✅ · 5 frontend (mic + boxes + fallback) ✅
· 6 end-to-end live test + collect ~50 samples ⬜ (human-driven, still pending).

**Session 7 (architect lock):** flowchart updated (Emergency removed, M4→M6 direct); stack +
per-module API strategy + voice model locked; all tracking docs rewritten. No code. The full
sequential build plan (Phases A–I) now lives in the architect output / the build plan; the
**first coding step is Phase A / Step A1 — add browser TTS to the frontend.**

**Multi-provider STT (Session 3):** built — then REMOVED in Session 4 (scope
simplified to browser-only for Module 1; may return in a later module).

**Browser-only STT (Session 4):** continuous recording (no cap, append-only,
~10s-silence auto-stop) ✅ · Mintlify UI + scrollable stick-to-bottom panels ✅
· live mic test on real speech + ~50 samples ⬜ (next, human).

**Document export (Session 5):** every completed session auto-saves a `.docx`
(python-docx; derived artifact, DB is source of truth) ✅ · `GET /api/documents`
list + `/download` ✅ · Saved-documents frontend panel ✅. Early groundwork toward
Module 12 (Structured Clinical Report) and Module 13 (EHR storage) — those modules
stay ⬜ (no clinical content/extraction yet; this only exports raw + corrected).

**Two-file export + Alembic (Session 6):** RAW and CORRECTED exported as SEPARATE,
independently downloadable `.docx` (raw on Stop, corrected on Correct) via a
`documents.kind` column ✅ · routes `GET /api/transcripts/{id}`,
`POST /api/transcripts/{id}/documents/{raw,corrected}` ✅ · per-panel download buttons +
loading/error states ✅ · **Alembic** schema migrations, auto-run at startup, fixing the
`no column named stt_provider` bug in place (data preserved) ✅. 19 tests pass.

### Phase 1 — Robust local core
**Goal:** FastAPI + WebSocket backend streaming live mic audio to faster-whisper
(int8, CPU); store immutable raw + corrected text; verified working on both
Windows and Arch Linux from one requirements.txt.
**Move on when:** Live transcription runs locally on both machines with usable
latency, and raw/corrected are saved separately. Module 1 = ✅ at this point.

### Phase 2 — Bangla accuracy
**Goal:** Swap in a Bangla-fine-tuned Whisper model (e.g. tugstugi/whisper-medium
converted to CTranslate2); add Banglish→Bangla transliteration (IndicXlit) + LLM
normalization (Module 2); measure WER on our own samples.
**Move on when:** WER on our real samples is recorded and acceptable, and a
separate normalized field is produced. This begins Module 2.

### Phase 3 — Stretch / thesis contribution
**Goal:** Fine-tune on medical Bangla data, and/or harden the API for the future
mobile app. Optional speaker separation (doctor vs patient).

---

## Notes
- Nothing is "done" until its testable definition above is met **and** the result
  is written in `test_log.md`.
- If a later module is tempting to start early, check the dependency column in
  `constitution.md` first.
- **Emergency safety did not go away** — it moved into Module 10 as a rule-based red-flag
  check (ADR-0024). A medical pre-screening tool must never present a falsely reassuring
  picture (Open Flag 1 if the student wants to revisit this).
