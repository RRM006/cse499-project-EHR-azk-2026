# milestone_log.md — Big-Picture Status Board

> This answers one question: **"Where are we in the whole project right now?"**
> Update the status when a module's state changes. Keep the "Done means" line
> honest and testable — not "works well", but a real, checkable definition.

**Status keys:** ⬜ Not started · 🟨 In progress · 🟦 Blocked · ✅ Done

**Last updated:** 2026-06-21 (Session 6 — two separate raw/corrected .docx + Alembic migration)
**Current phase:** Phase 0 (quick demo) — browser-only STT.
**Module in focus:** Module 1 — Speech-to-Text (+ document-export groundwork).
**Progress:** Single STT path (browser Web Speech API) + Mintlify UI with fixed-height
scrollable panels. NEW this session: RAW and CORRECTED are now exported as TWO separate,
independently downloadable Word `.docx` files (raw on Stop, corrected on Correct) via a
`documents.kind` column behind the existing writer/storage/format seams; and the DB schema
is now managed by **Alembic** (auto-migrate at startup), which FIXED the live
`no column named stt_provider` error in place without deleting the DB (2 real rows preserved).
**19 tests pass**; the manual-text → raw-.docx flow verified end-to-end in the browser.
Module 1 stays 🟨 until the human live mic test + ~50 samples + latency/WER are recorded.

---

## The 15 modules

| # | Module | Status | "Done" means (testable) |
|---|--------|:------:|--------------------------|
| 1 | Speech-to-Text | 🟨 | Live mic audio is transcribed and the **raw** Bangla/Banglish text appears on screen within ~3s; raw text is stored unchanged; works on both Windows and Linux; manual text-input fallback exists. |
| 2 | Text Processing & Normalization | ⬜ | Given raw text, a separate cleaned/normalized field is produced (spelling, fillers removed, sentence boundaries); raw is never modified; measured on a small test set. |
| 3 | Information Extraction | ⬜ | From normalized text, symptoms / body part / duration / severity / meds / history are extracted as structured fields; precision & recall recorded in test_log. |
| 4 | Initial Clinical Summary | ⬜ | A 2–4 sentence chief-complaint summary is generated from extracted fields and shown to the doctor. |
| 5 | Emergency Detection | ⬜ | Red-flag symptoms trigger an alert before the rest of the pipeline; tested against a list of known emergency phrases with recorded hit rate. |
| 6 | Missing Information Analysis | ⬜ | System outputs a checklist of present vs. missing data points for the case. |
| 7 | Follow-up Question Generation | ⬜ | System generates prioritized follow-up questions (Bangla/English) for the gaps, no repeats of answered items. |
| 8 | Response Processing & Profile Update | ⬜ | Patient answers are re-processed and merged into the profile with conflict handling. |
| 9 | Case Completion Check | ⬜ | A completeness score is computed; loops back to Module 7 until threshold or max turns reached. |
| 10 | Risk Assessment Engine | ⬜ | Each case is classified Low/Medium/High/Critical from rules + model; accuracy recorded on a labeled test set. |
| 11 | Explainable AI (XAI) | ⬜ | Every risk output has a plain-language reason listing the contributing factors. |
| 12 | Structured Clinical Report | ⬜ | A full report (all sections) is generated and exportable as PDF + dashboard view; contains no diagnosis. |
| 13 | EHR Database | ⬜ | Transcripts, profiles, reports, and audit logs are stored and retrievable by patient ID/date; data encrypted. |
| 14 | Doctor Dashboard | ⬜ | Web UI shows report, risk, flags, XAI; doctor can override/annotate; high/critical cases alerted. |
| 15 | Feedback & Continuous Learning | ⬜ | Doctor feedback is collected and usable to retrain/fine-tune; regression check before deploying updates. |

---

## Roadmap phases (how we get Module 1 right first)

These come from the build plan. Each phase has a clear "move on when" gate.

### Phase 0 — Quick working demo  ⬅️ WE ARE HERE
**Goal:** Prove the whole loop (live voice → raw text → corrected text → screen)
with zero ML setup, using the browser Web Speech API + one free LLM for correction.
**Move on when:** I can speak Bangla/Banglish into the browser, see the raw text
live, see a corrected version beside it, and the raw text is stored unchanged.
(Also: ~50 real sample utterances collected for later testing.)
**Build steps (6):** 1 scaffolding ✅ · 2 backend skeleton ✅ · 3 correction service ✅
· 4 API routes + static serving ✅ · 5 frontend (mic + boxes + fallback) ✅
· 6 end-to-end live test + collect ~50 samples ⬜ (human-driven, next).

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
