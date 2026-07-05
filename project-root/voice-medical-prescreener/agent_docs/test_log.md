# test_log.md — What Was Tested + Results

> For an ML/NLP project, "it runs" is NOT success. This file records **numbers**:
> what we tested, how, and the result — including failed runs. This makes progress
> verifiable and gives the thesis real evidence.
>
> Template for each entry:
> ```
> ## YYYY-MM-DD — Module N — <what was tested>
> - Setup: <model/library/version, machine: Windows or Linux, sample data used>
> - Metric(s): <e.g. WER, precision, recall, accuracy, latency>
> - Result: <the numbers>
> - Notes: <what helped / hurt, errors, next idea>
> ```

---

## Metrics we care about (per module)

- **Module 1 (STT):** Word Error Rate (WER, lower is better), latency (seconds
  from speech to text), and whether it ran on CPU on both OSes.
- **Module 2 (Normalization):** % of fields correctly normalized; raw left intact.
- **Module 3 (Extraction):** precision & recall for each entity type (symptom,
  duration, severity, medication, etc.).
- **Module 7 (Follow-up + TTS):** question is shown as text AND spoken; whether a
  Bangla (`bn-BD`) voice exists per OS; patient voice reply round-trips to text.
- **Module 10 (Risk + red-flag):** **red-flag recall** on a fixed list of
  life-threatening phrases (we want to almost never miss one → it must force Critical),
  plus overall Low/Med/High/Critical accuracy / confusion matrix on labeled cases.

## How to measure WER (quick note for later)
WER = (substitutions + insertions + deletions) / number of words in the reference.
Use the `jiwer` Python package against a small set of audio clips that we have
transcribed by hand (the "ground truth"). Record the model + machine each time.

---

## Planned test cases (added Session 7 — to run as each step is built)

> These are **not yet executed** — they define what "done" looks like for the new
> voice + flow + API work so a future session can fill in real numbers.

- **TC-V1 — STT voice input (Module 1, existing):** speak 10 Bangla + 10 Banglish
  sentences in Chrome; confirm each appends live & verbatim to RAW, raw is stored
  unchanged, and record rough latency + by-hand WER per sentence. (Still the human's
  pending live test from S4–S6.)
- **TC-V2 — TTS playback (Module 7 / Phase A Step A1):** call `speak('আপনার কতদিন
  ধরে জ্বর হচ্ছে?')`; PASS = audio plays AND the same text is visible on screen.
  Record per OS (Windows / Arch) whether a `bn-BD` voice was available in
  `speechSynthesis.getVoices()`; if none, PASS still requires the on-screen text
  fallback to show (Open Flag 4).
- **TC-V3 — Voice-only reply loop (Module 7→8):** after a TTS question, speak an
  answer; PASS = the answer is transcribed to text and accepted with NO keyboard
  input; the manual text box is used only when the mic is unavailable.
- **TC-A1 — API fallback chain (ADR-0026):** force the primary provider to fail
  (bad key / simulated 429); PASS = the request transparently falls back to
  OpenRouter `:free` and still returns a corrected/structured result; the provider
  actually used is logged.
- **TC-F1 — Flow M4→M6 direct (ADR-0024):** with the Emergency module removed,
  PASS = a case flows M4 → M6 with no emergency branch, and there is no `D1`/`AX`
  node or "Emergency Detected?" step anywhere in the pipeline or UI.
- **TC-F2 — Follow-up loop (Module 9→7):** an incomplete profile loops back to M7
  and asks only for still-missing items (no repeats of answered questions); PASS =
  loop exits when the completeness threshold or max turns is reached.
- **TC-R1 — Red-flag check (Module 10, ADR-0024):** feed a fixed list of clearly
  life-threatening phrases (e.g. "বুকে প্রচণ্ড ব্যথা", severe breathing difficulty,
  stroke signs, loss of consciousness); PASS = every one is forced to **Critical**
  and surfaced in the M12 **Red Flags** section. Record red-flag recall (target:
  no misses on the list).

---

## Test entries (newest first)

## 2026-07-05 — Session 9 — Fix/feature build steps 1–5: suite 104 → 121, all offline (no live LLM)
- Setup: Python 3.14 on Windows (`.venv`); `pytest backend/tests/` after every step; all new
  tests offline per rule #4 (LLM boundary faked; temp-dir document storage; throwaway SQLite
  files for migration gates). Browser checks via the preview panel on the real server (port 8001).
- Metric(s): test count / pass rate per step; migration data-preservation; docx content checks.
- Result: **121/121 passing** (was 104). Step-by-step: +5 `test_routes_static` (all 5 entry
  points 200; legacy isolated at /legacy/; landing links all four; kiosk untouched) → 109.
  +4 `test_migration_0010` (legacy-DB upgrade keeps raw text byte-identical + document link;
  fresh DB has prescriptions table + all new columns; visit-grain document inserts with
  utterance_id NULL; prescription JSON payload round-trips) → 113. +3 `test_visit_documents`
  (transcript .docx contains all 4 Bangla raw turns BYTE-EXACT in order; summary report has
  10 bilingual labels + stored values + vitals + no-diagnosis disclaimer; route guards
  400/404) → 116. +5 `test_bilingual_fields` (en+bn fill, plain-string salvage→English,
  legacy `{value}` rows validate + score 0.6, any-slot counting, bn-only counts) → 121.
  Rev 0010 applied to the REAL dev DB: upgrade 0009→0010 clean, head confirmed, backup
  `prescreener.db.pre-0010.bak` taken first.
- Browser verification (step 4, real Chrome preview, zero console errors): `fieldValue()`
  legacy `{value}` ✓ · en pick "Headache" ✓ · bn pick "মাথা ব্যথা" ✓ · cross-language
  fallback ✓ · whitespace/null → '' ✓ · `tierBand()` low '0–25%', critical '76–100%',
  unknown '—' ✓.
- Notes: two would-be bugs caught before shipping: legacy index.html's absolute
  `/styles.css`/`/app.js` refs (would 404 under /legacy/) and `documents.utterance_id`
  NOT NULL (would block every visit-grain export). Existing English-only stored rows stay
  as-is until re-extracted — readers fall back across slots (ADR-0033). TC-V2/V3/F2/R1/A1
  (human real-mic run) remain pending — re-run AFTER the kiosk fixes land (steps 6–11).

## 2026-07-03 — Session 8c — Live-run Part 1: FULL pipeline live (M3→M12), all three API buckets
- Setup: Python 3.14 on Windows; server via uvicorn port 8001. **All three keys real** in
  `backend/.env` (Gemini + Groq + OpenRouter — Groq/OpenRouter added this session). Driven by a
  scratch script over the REST API with SYNTHETIC typed Banglish (no mic; rule #4):
  lookup(01712345678) → OTP 000000 → visit → 2 utterances ("amar 3 din dhore matha betha ar
  halka jor ache", "raate ghum hocche na, matha ta dan dike beshi betha kore") → /intake →
  followup next/answer ×2 → /assess → /report.
- Metric(s): end-to-end success; per-module provider + latency + fallback from `module_events`;
  loop exit; risk tier sanity; test-suite regression.
- Result: **PASS end to end.** `module_events` = 13 rows, **13/13 status=ok, 0 fallbacks**:
  M3=gemini_flash_lite (1658/1899 ms), M4=gemini_flash (8577/3714 ms), M6=groq (859/850 ms),
  M7=groq (671/484 ms), M8=gemini_flash_lite (1426/2516 ms), M10=gemini_flash (4093 ms),
  M11=gemini_flash (3437 ms), M12=local. Providers match the ADR-0026 bucket map exactly.
  Follow-up loop: 2 real Bangla questions ("আপনার জ্বর কত দিন ধরে আছে?", "আপনার শরীরের তাপমাত্রা
  কত ছিল?"), no repeats, exited complete=True at completeness 0.7. Risk: tier=**medium**,
  red_flags=[] (correct: 3-day headache + mild fever is not a red-flag case), M11 gave a
  plain-language reason. Report generated. `pytest backend/tests/`: **104 passed** (3.88 s).
- Notes: This effectively covers TC-F1 (M4→M6 direct, live) and the no-repeat/exit half of
  TC-F2 in a typed run; TC-V2/V3 (voice), TC-R1 (red-flag → Critical, live) and TC-A1
  (forced-fallback) still need the human Part-2 run. Windows console needs
  `PYTHONIOENCODING=utf-8` to print Bangla from scripts (cp1252 crash — cosmetic only).
  Keys were pasted in chat → rotate before any public demo.

## 2026-07-03 — Session 8b — FIRST live LLM call (Gemini M2 correction) + ADR-0029 doc rewrite
- Setup: Python 3.14 on Windows; `.venv`. Real `GEMINI_API_KEY` in `backend/.env` (Groq +
  OpenRouter keys EMPTY). One live call via
  `python -m backend.app.services.correction.openai_compatible "<synthetic Banglish>"`
  (model `gemini-flash-latest`). Synthetic data only (rule #4).
- Metric(s): does a real Gemini call succeed? does it obey the correction-only prompt (no
  translation / no diagnosis / same script)?
- Result: **PASS — the live Gemini path works** (first live verification in 8 sessions).
  * RAW:       `ami 3 din dhore onek jor ar mathabetha te vugchi, sathe kashi o ache`
  * CORRECTED: `ami 3 din dhore onek jor ar mathabethate bhugchi, sathe kashi o ache`
  * Behavior correct: fixed spelling only (`vugchi`→`bhugchi`, `mathabetha te`→`mathabethate`),
    kept Banglish/Roman script (NO conversion to Bangla), no translation, no diagnosis, no added
    symptoms (rules #1/#2 upheld). ~1 request spent.
- Notes: **Full live intake/loop is BLOCKED on keys, not code** — M6/M7 are Groq-bucket and both
  Groq + OpenRouter are empty, so `provider_chain_for_module` returns [] → LLMCallError for those
  modules. Add a Groq OR OpenRouter key to run the full pipeline live. The real-voice kiosk run
  (mic) remains the human's task. TC-V2/V3/F2/R1(live)/A1(live) still pending.

## 2026-07-03 — Session 8 — Full-stack build: DB 0003–0009 + M3–M12 backend + 3 portals
- Setup: Python 3.14 on **Windows**; `.venv` (had to `pip install -r requirements.txt` — alembic
  was missing, S6 ran on Arch). Server on port 8001 via the preview tool. Unit/route tests on
  in-memory SQLite (StaticPool) with the **LLM layer faked** (no network, no quota); migration
  tests on throwaway SQLite files; real-DB migrations verified on a COPY then applied to the real DB
  (backups `prescreener.db.pre-000{3,4,5,6,7}.bak`). Browser checks via preview_eval/snapshot.
- Metric(s): test pass/fail; migration data-preservation; red-flag recall; API status; UI render.
- Result:
  * `pytest backend/tests/` → **104 passed** (was 19). New suites: `test_migration_0003` (4:
    legacy backfill keeps raw byte-identical, fresh schema + seeds, CHECK accepts medic/
    awaiting_doctor + rejects bogus, mixed-state-legacy regression), `test_routes_visits` (4),
    `test_intake` (3), `test_followup_loop` (4), `test_risk` (**~70** — every red-flag phrase is a
    parametrized case), `test_staff_routes` (2), `test_report_review` (2). The 19 baseline never
    regressed.
  * **TC-R1 (red-flag recall) — offline PASS with zero misses:** every phrase in
    `RED_FLAG_RULES` (5 categories, Bangla/Banglish/English) forces tier `critical`; verified it
    still forces `critical` when BOTH the M10 and M11 LLM calls fail (simulated outage), and when
    the phrase appears only in RAW (uncorrected) text. Benign text triggers nothing. Model failure
    WITHOUT a flag degrades to `medium`, never silently `low` (rule #3).
  * **Migration data preservation:** real Windows DB (mixed-state legacy: had `stt_provider`,
    lacked `documents.kind`) migrated `→ 0009`; **5 utterances preserved, raw byte-identical, 5
    synthetic closed visits backfilled, 0 orphans**; re-run is a no-op (idempotent). Also fixed a
    latent crash: blind stamp-at-0001 died with `duplicate column name: stt_provider`;
    `_legacy_stamp_revision()` now stamps by actual columns (regression-tested).
  * **Fallback logging (TC-A1, offline):** forcing the primary provider to fail makes intake fall
    to OpenRouter and logs `module_events.status='fallback'` with the provider — verified per module.
  * **Browser smoke (no quota spent):** `/kiosk.html` → phone `1715984632` → OTP `000000` →
    conversation screen with the Bangla opening question rendered AND queued for TTS; 0 console
    errors, 0 failed network requests, Bangla renders correctly (Noto Sans Bengali). `/medic/`
    login → seeded "Medic Rahman", doctors dropdown populated, empty queue (correct — nothing
    submitted). `/doctor/` login → "Dr. M. Rahman", assigned queue renders.
- Notes: NOT yet run — the LIVE end-to-end with real Gemini/Groq keys (intake/followup/assess/xai
  actually calling the models). That's the human's next step (spends quota; rule #4 synthetic data
  only). Still open: TC-V2 (bn-BD TTS voice availability per OS), TC-V3 (voice-only reply loop),
  TC-F2 on real speech, real-data accuracy for M3/M10, WER/latency, and the S4–S6 mic test + ~50
  samples.

## 2026-06-25 — Session 7 — Architect planning lock (no code run)
- Setup: Planning/documentation session only. No server started, no `pytest` run, no
  models executed. Working code is unchanged from Session 6 (still 19 tests on disk).
- Metric(s): none (nothing executed).
- Result: N/A — see the "Planned test cases" block above for the test contract added this
  session (TC-V1…TC-R1). The 19-passing-tests figure from 2026-06-21 still stands because no
  code changed.
- Notes: The Emergency module was retired and replaced by a rule-based red-flag check in
  Module 10 (ADR-0024); TC-R1 makes red-flag recall a first-class, measured metric so the
  safety change is verifiable. Next executable test will be TC-V2 (browser TTS) once Phase A
  Step A1 is built.

## 2026-06-21 — Module 1 (+ doc export) — Two separate raw/corrected .docx + Alembic migration
- Setup: Python 3.14.3 on **Arch Linux**; `.venv`. Added `alembic==1.14.0`. Server run on
  port 8001 via the preview tool (`backend-linux` launch config). Unit tests on in-memory
  SQLite (StaticPool for the route test) + temp-dir storage + a fake corrector; migration
  tests on throwaway SQLite FILES; end-to-end checks via preview_eval against the real DB/FS.
- Metric(s): test pass/fail; migration correctness + data preservation; file validity
  (bytes, Word content-type); HTTP status/headers.
- Result:
  * `pytest backend/tests/` → **19 passed in ~1.2s** (raw_immutable 3 + corrector 4 +
    docx_writer 5 + documents_repo 4 + migration 2 + routes_documents 2). The docx_writer
    tests assert raw doc holds RAW verbatim and NOT the correction, and vice-versa (rule #1).
  * **DB bug FIXED & verified.** Before: live `utterances` had columns up to `corrected_at`
    but NO `stt_provider`. After `run_migrations()` on the real DB: `stt_provider` +
    `documents.kind` present, `alembic_version = 0002_add_stt_provider_and_doc_kind`, and
    **both original utterance rows preserved (count = 2)**. Fresh-DB path (0001→0002) builds
    the full schema from scratch; a second `upgrade head` is a no-op. Migration unit tests
    (legacy-DB-keeps-rows + fresh-DB-full-schema) pass. Pre-migration DB backed up to
    `backend/data/prescreener.db.pre-alembic.bak`.
  * End-to-end in the browser (manual-text path; no Gemini): typing a Banglish utterance +
    "Use this text as RAW" → raw saved, **raw .docx generated**, "Download Raw .docx" button
    enabled, `GET /api/documents` lists kind=`raw` filename `raw-session-3-20260621.docx`,
    and downloading it → HTTP 200, Content-Type
    `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, **36,913 bytes**.
    Both download buttons start disabled (is-disabled, no href). Startup logs: 0 errors.
  * Route integration test (TestClient, fake corrector): save → raw .docx → GET detail →
    400 on corrected-before-correction → correct (RAW unchanged, corrected stored) →
    corrected .docx → both files download as Word docs; unknown ids → 404.
- Notes: The LIVE Gemini correction in-browser + opening both .docx in Word/LibreOffice to
  confirm real Bangla rendering is still the human's manual check (not auto-run — saves free
  quota). The preview screenshot tool timed out (renderer); preview_eval gave conclusive
  functional proof. On Arch, launch the preview via the **`backend-linux`** config — the
  default Windows config fails with `spawn .venv/Scripts/python.exe ENOENT`. No WER/latency
  on real speech yet — still the human's next step.

## 2026-06-21 — Module 1 (+ doc export) — Auto .docx generation + list/download
- Setup: Python 3.14.4 on Windows; `.venv`. Added `python-docx==1.1.2`. Server run on
  port 8001 via the preview tool. Unit tests on in-memory SQLite + temp-dir storage;
  end-to-end checks via preview_eval (browser fetch) against the real DB/filesystem.
- Metric(s): test pass/fail; file validity (size, zip magic); HTTP status/headers.
- Result:
  * `pytest backend/tests/` → **13 passed in 1.78s** (3 raw_immutable + 4 corrector +
    4 docx_writer + 2 documents_repo). The 6 new tests include a rule-#1 guard at the
    export layer (RAW text appears verbatim in the rendered .docx).
  * End-to-end (no Gemini; correction inserted directly): generated a real **35,799-byte**
    `.docx`; file written under `documents_dir` named by UUID; `EXISTS=True`.
  * `GET /api/documents` → 200, lists the doc (id, utterance_id, format, filename,
    created_at). `GET /api/documents/{id}/download` → 200, Content-Type
    `application/vnd.openxmlformats-officedocument.wordprocessingml.document`,
    Content-Disposition `attachment; filename="session-5-20260621.docx"`, body 35,799
    bytes, first 2 bytes = `PK` (valid .docx/zip magic).
  * Frontend "Saved documents (.docx)" panel renders the row + mint-green download
    pill link (`/api/documents/{id}/download`); empty-state message shown when none.
    Server booted with 0 errors in logs.
- Notes: The LIVE Gemini correction + the .docx opened in Word/LibreOffice with real
  Bangla rendering is still the human's manual check (Bengali font set on Latin AND
  complex-script slots; needs a Bengali-capable font installed to render). No WER/
  latency on real speech yet — still the human's next step.

## 2026-06-20 — Module 1 — Browser-only simplification + Mintlify UI + scroll behavior
- Setup: Python 3.14.4 on Windows; venv RECREATED from requirements.txt (clean core:
  fastapi 0.115.6, starlette 0.41.3 — torch/transformers/qwen removed). Server run on
  port 8001 via the preview tool (port 8000 had an orphaned socket). Browser checks
  via preview_eval / console logs.
- Metric(s): test pass/fail; endpoint presence; CSS/JS behavior (fonts, scroll).
- Result:
  * `pytest backend/tests/` → **7 passed** (test_raw_immutable + test_corrector;
    test_stt_registry removed). 0 console errors on the page.
  * Routes now exactly: `/api/correct`, `/api/transcripts`, `/health` (+ static).
    `/api/stt/providers` → 404, `/api/transcribe` → gone. STT endpoints removed.
  * UI: Inter font loaded; Start button mint-green pill (rgb(0,212,164), radius
    9999px); transcript panels fixed-height 280px (220px mobile), overflow-y auto,
    scrollable.
  * Auto-scroll: sticks to bottom on append; scroll-up sets stick=false and append
    does NOT yank down; returning to bottom sets stick=true and append follows.
    Verified all four conditions true.
  * Mobile (375px): single-column grid, 220px panels, no horizontal overflow
    (bodyScrollWidth == viewport).
  * One live store→correct round-trip succeeded earlier this day (raw immutable,
    corrected separate).
- Notes: Live mic continuous-recording + ~10s-silence auto-stop is the human's
  manual Chrome check (can't automate the mic). No WER/latency on real speech yet.

## 2026-06-19 — Module 1 (infra) — Multi-provider STT: installs, health, transcribe paths
- Setup: Python 3.14.4 on Windows; `.venv`. Installed faster-whisper 1.1.0
  (requirements-whisper.txt), transformers 5.12.1→4.57.6 + torch 2.12.1 (banglaspeech),
  qwen-asr 0.0.6 (qwen). Synthetic 2-second 16 kHz WAV used to exercise the code path.
- Metric(s): test pass/fail; dependency resolution; transcribe-path success; provider health.
- Result:
  * `pytest backend/tests/` → **13 passed** (immutability + corrector + STT registry).
  * Dependency conflict RESOLVED: requirements-whisper.txt installed cleanly with
    huggingface-hub 1.20.1 (the old banglaspeech2text==0.0.7 / hub==0.11.1 pin is gone).
  * `torch==2.5.1` had NO Python-3.14 wheel; unpinned → torch 2.12.1 installed.
  * After all installs, `GET /api/stt/providers` → all 5 status=available, ready=True;
    app boots under fastapi 0.137.2 / starlette 1.3.1 (only a TestClient deprecation warning).
  * Transcribe code path validated on the synthetic clip (no crash, returns a str;
    empty text expected for a pure tone): local_whisper (faster-whisper base, int8)
    and banglaspeech2text (shhossain/whisper-base-bn via transformers).
- Notes: `qwen-asr` install was invasive (bumped fastapi/starlette/transformers/
  huggingface_hub, pulled gradio/flask) — app still works. NOT yet tested live:
  Groq STT (would spend free quota) and Qwen (3.4 GB download + very slow on CPU).
  No WER/latency on real Bangla speech yet — that is the human's next step. Rough
  latency ESTIMATES (10 s clip, CPU): Browser ~live; Groq ~1–3 s; local_whisper base
  ~2–5 s; banglaspeech base-bn ~10–25 s; Qwen ~30 s–minutes. Gemini correction +1–3 s.

## 2026-06-19 — Module 1 (infra) — Correction guards + API/frontend smoke test
- Setup: Python 3.14.4 on Windows; `.venv`. Backend served via the preview tool
  (uvicorn on port 8000). Browser checks via preview_eval / console logs.
- Metric(s): test pass/fail; HTTP status of endpoints; JS console errors.
- Result:
  * `pytest backend/tests/` → **7 passed** (3 immutability + 4 corrector guards).
  * Endpoints: `/`, `/app.js`, `/styles.css` → 200; `/api/transcripts` → 200 `[]`;
    `/health` → 200; routes = `/`, `/api/correct`, `/api/transcripts`, `/health`.
  * Frontend: page renders, all elements present, Web Speech API detected,
    **0 console errors**, recent-list fetch returned 200.
- Notes: Corrector guards are OFFLINE (no network) — empty input short-circuits,
  provider selection, missing-key → RuntimeError, unknown-provider → ValueError.
  The LIVE Gemini call (`POST /api/correct` / the module `__main__`) was NOT run
  this session (spends free-tier quota) — that is the human's Step-6 live test.
  No WER/latency numbers yet; those come from the live test on real utterances.

## 2026-06-19 — Module 1 (infra) — Raw-immutability guard + clean install
- Setup: Python 3.14.4 on Windows; `.venv`; deps from `requirements.txt`
  (fastapi 0.115.6, uvicorn 0.34.0, pydantic-settings 2.7.1, SQLAlchemy 2.0.51,
  openai 1.59.6, pytest 8.3.4). DB = in-memory SQLite for the test.
- Metric(s): test pass/fail (not an ML metric — this is an infra guard).
- Result: `pytest backend/tests/` → **3 passed in 0.43s**. Confirms: raw text is
  stored verbatim (spaces preserved), `set_correction` never alters `raw_text`,
  and the repository exposes no raw-mutating function.
- Notes: `pip install -r requirements.txt` succeeded with wheels only (no compiler)
  on Python 3.14. SQLAlchemy 2.0.36 crashed on 3.14 (typing-union bug) → upgraded
  to 2.0.51 (see ADR-0012). `git check-ignore` confirms `backend/.env` is ignored
  and `backend/.env.example` is tracked.

## 2026-06-18 — Setup
- No tests yet. Nothing built.
- First ML test will be: Phase 0 demo — can it transcribe ~10 spoken Bangla/Banglish
  sentences live, and is the raw text stored unchanged? (latency + a rough
  by-hand WER on those 10 sentences).
