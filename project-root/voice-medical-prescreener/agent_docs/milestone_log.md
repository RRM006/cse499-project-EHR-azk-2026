# milestone_log.md — Big-Picture Status Board

> This answers one question: **"Where are we in the whole project right now?"**
> Update the status when a module's state changes. Keep the "Done means" line
> honest and testable — not "works well", but a real, checkable definition.

**Status keys:** ⬜ Not started · 🟨 In progress · 🟦 Blocked · ✅ Done

**Last updated:** 2026-06-19 (Session 3 — multi-provider STT + provider health + installs)
**Current phase:** Phase 0 (quick demo), expanded to multi-provider STT.
**Module in focus:** Module 1 — Speech-to-Text.
**Progress:** Full stack built with **5 swappable STT providers** + frontend dropdown
+ provider health reporting. All engines installed on the Windows box (13 tests pass;
local transcribe paths validated). Next: human live-tests each provider in Chrome,
collects ~50 samples, records latency/WER. Module 1 stays 🟨 until that's done.

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

**Multi-provider STT (Session 3):** provider/plugin layer ✅ · 5 providers wired ✅
· frontend dropdown + health badges ✅ · all engines installed + local paths
validated ✅ · live test of each provider on real speech ⬜ (next).

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
