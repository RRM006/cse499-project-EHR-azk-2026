# changelog.md — Session-by-Session History

> The running memory of the project. **Newest entry at the top.**
> One short entry per session. This is what a new session reads to remember
> "what happened recently and why", so we never re-explain or re-litigate.
>
> Template for each entry:
> ```
> ## Session N — YYYY-MM-DD — <short title>
> - Did: <what we actually built or changed>
> - Decided: <any decision; also add it to decisions.md>
> - Broke / problem: <anything that failed or is fragile>
> - Deferred: <what we chose NOT to do yet, and why>
> - Next: <the one thing to do next — also update current_task.md>
> ```

---

## Session 6 — 2026-06-21 — Two separate raw/corrected .docx + Alembic migration (fix stt_provider bug)
- Did: (A) FIXED the live `sqlite3.OperationalError: table utterances has no column named
  stt_provider` by adopting **Alembic**. New `backend/alembic.ini` + `backend/migrations/`
  (env.py reads the URL from app settings, `render_as_batch=True` for SQLite) with two
  revisions: `0001_baseline` (original schema) and `0002` (adds `utterances.stt_provider` +
  `documents.kind`). `init_db()` now runs `run_migrations()` — stamps the baseline on a
  legacy DB, then `upgrade head`; fresh DBs build from scratch; re-runs no-op. Verified on
  the REAL db (2 rows preserved) + a fresh db; backed up the pre-migration db to
  `backend/data/prescreener.db.pre-alembic.bak`. (B) Split document export into TWO separate,
  independently downloadable files: added `documents.kind` ("raw"|"corrected"; legacy
  "combined"); `DocumentWriter.render(utterance, *, kind)` → DocxWriter renders raw-only
  ("Transcript") or corrected-only ("Corrected Transcript"); `generate_session_document(kind=…)`;
  repo `create_document(kind=…)` + `get_latest_document`. New routes (kept `/api/*`):
  `GET /api/transcripts/{id}` (TranscriptDetailOut: raw+corrected text + both doc links),
  `POST /api/transcripts/{id}/documents/raw`, `…/documents/corrected`; `/api/correct` now
  best-effort generates the CORRECTED doc and returns the detail. (C) Frontend: raw is now
  saved + a raw .docx generated when recording STOPS (not only on Correct); added per-panel
  "Download Raw/Corrected .docx" buttons (enabled when each file exists), loading states
  (Saving…/Generating document…/Correcting text…), and the exact spec error strings.
  (D) Config: added `STT_PROVIDER` + `DOCUMENT_OUTPUT_PATH` (alias of DOCUMENTS_DIR) +
  documented `DATABASE_URL`; updated `.env.example` and `.env`. Added a `backend-linux`
  launch.json config (the existing one is Windows-only `.venv/Scripts/python.exe`).
- Decided: Alembic + auto-migrate-at-startup with legacy baseline-stamp (ADR-0022); raw and
  corrected exported as SEPARATE docs via a `documents.kind` column, dedicated documents
  table kept over flat path columns, `/api/*` prefix kept (ADR-0023, decided with the human).
- Broke / problem: One real issue surfaced at END of session — `preview_start` failed with
  `spawn .venv/Scripts/python.exe ENOENT`: the DEFAULT `.claude/launch.json` config uses the
  WINDOWS venv path, which doesn't exist on Arch. Workaround: launch the new `backend-linux`
  config (`.venv/bin/python`) explicitly — that starts cleanly (earlier this session the
  server ran fine that way). NOT yet OS-robust (no single launch.json default works on both
  machines; the preview panel picks the first config). Test gotchas fixed during dev:
  TestClient runs sync endpoints in a threadpool, so the route test needed `StaticPool` to
  share the in-memory SQLite across threads; the preview screenshot tool timed out (renderer),
  but functional verification via preview_eval was conclusive. A synthetic session #3 raw doc
  was created in the dev DB during verification (harmless; gitignored, like S5's session #5).
- Deferred: LIVE Gemini correction in-browser + opening both .docx in Word/LibreOffice to
  confirm Bangla renders (human's manual check — not auto-run to save free quota). PDF /
  Markdown writers (format seam ready), version-history UI, auth, cloud storage, Patient/Visit
  tables. Still deferred from S4/S5: the human live mic test + ~50 samples + WER/latency.
- Next: Human live test in Chrome — record → Stop (raw .docx auto-saves + downloads) →
  Correct (corrected .docx) → open both, confirm Bangla renders + RAW unchanged; collect
  samples. See `current_task.md`.

## Session 5 — 2026-06-21 — Auto-generate & store .docx per session + Saved Documents UI
- Did: Added automatic Word-document export for completed sessions (additive, nothing
  existing broken). New `Document` SQLAlchemy model (UUID PK, FK → Utterance, format,
  filename, rel_path, created_at) + repo `create_document`/`get_document`/
  `list_documents`. New `services/documents/` layer: `DocumentWriter` ABC, `DocxWriter`
  (python-docx; renders Raw verbatim + Corrected + metadata; Bengali font set on Latin
  AND complex-script slots), `storage.py` filesystem abstraction (S3-swappable), and a
  `build_writer()` seam + `generate_session_document()` orchestrator. New routes
  `GET /api/documents` (list) and `GET /api/documents/{id}/download` (FileResponse, Word
  media type). `/api/correct` now best-effort generates the .docx after a successful
  correction (a docx failure logs but never fails the correction). Added `documents_dir`
  config (env-overridable, default `backend/data/documents`, no hardcoded paths) and
  `python-docx==1.1.2` to requirements.txt. Frontend: "Saved documents (.docx)" panel
  (Mintlify-styled) listing docs with download links, auto-refreshed after correction.
- Decided: A `.docx` is a DERIVED export artifact; the DB stays the source of truth
  (regenerable, preserves rule #1, avoids Bangla round-trip loss). python-docx (pure
  Python, cross-platform). Filesystem storage now, behind a swappable interface.
  Document grain = one Utterance/session; NO Patient/Visit tables yet. DOCX now, PDF
  later (clean `format` seam). (ADR-0021.)
- Broke / problem: Nothing broke. Note: passing a multi-line python `-c` with Bangla
  string literals through PowerShell mangled the quotes — used a temp script file
  instead (deleted after). Port-8000 orphaned-socket workaround (port 8001) still stands.
- Deferred: PDF generation + in-browser preview; Patient/Visit data model; auth on the
  document routes; cloud (S3/MinIO) storage. All have seams left in place. Still
  deferred from S4: the human live mic test + ~50 samples + WER/latency.
- Next: Human live test — record/correct in Chrome, confirm a .docx auto-saves and
  downloads + opens correctly (Bangla renders), alongside the mic/sample collection.

## Session 4 — 2026-06-20 — Simplify to browser-only STT + Mintlify UI + scrollable panels
- Did: (A) REMOVED the multi-provider STT architecture per the human's new plan —
  deleted `backend/app/services/stt/`, `api/routes_stt.py`, `test_stt_registry.py`,
  the three `requirements-*.txt`, all STT config + the `.env` STT block,
  `python-multipart`, and the startup health log. Recreated the venv from
  requirements.txt (clean core: fastapi 0.115.6, starlette 0.41.3; torch/
  transformers/qwen gone). Module 1 STT is now ONLY the browser Web Speech API.
  Rewrote the frontend for continuous recording: no cap, append-only verbatim
  transcript, brief pauses keep going (restart on `onend`), auto-stop after ~10s
  of silence. (B) Restyled the whole frontend to `DESIGN-mintlify.md` (Inter font,
  black pill buttons, mint-green accent for Start + active, 12px cards, hairline
  borders) and made the 3 transcript panels (Raw/Corrected/Manual) fixed-height,
  scrollable, with stick-to-bottom auto-scroll. Added the Frontend/Transcript-UI
  rules to CLAUDE.md.
- Decided: Browser Web Speech API is the only Module 1 STT (others return later);
  keep a clean seam (the `stt_provider` column stays). Drop the banglaspeech2text
  package permanently. Frontend follows DESIGN-mintlify.md. (ADR-0019, ADR-0020.)
- Broke / problem: A previous session left an ORPHANED socket holding port 8000
  (process dead, leaked handle keeps it LISTENING; clears on reboot). Worked around
  by switching `.claude/launch.json` to **port 8001**.
- Deferred: Live mic test of the continuous-recording + 10s-silence behavior (the
  human's manual check in Chrome). Collecting ~50 samples + WER/latency. Switching
  launch.json back to 8000 after a reboot. Regenerating the (now-removed) Groq key
  is moot since Groq STT was removed.
- Next: Human does the live mic test (speak, pause briefly, then go silent ~10s to
  confirm auto-stop) and collects samples. See `current_task.md`.

## Session 3 — 2026-06-19 — Multi-provider STT (5 providers) + provider health + installs
- Did: Re-planned Phase 0 to support 5 swappable STT providers with frontend
  switching. Built `backend/app/services/stt/` (STTProvider ABC + ProviderInfo
  health + registry + audio.py decode + 5 providers: browser_webspeech,
  groq_whisper, local_whisper, banglaspeech2text, qwen_asr). Added endpoints
  `GET /api/stt/providers`, `POST /api/transcribe`, `POST /api/transcripts`;
  refactored `/api/correct` to correct by utterance_id; added `Utterance.stt_provider`.
  Rewrote the frontend (provider dropdown + status badges, Start/Stop, MM:SS timer
  with 5-min auto-stop, raw/corrected copy+clear, manual fallback, error banner).
  Added a startup STT health log. Then FIXED 5 issues the human reported: documented
  QWEN_ASR_MODEL_DIR (optional, auto-download); rich provider health
  (available/missing_api_key/missing_package/missing_model/unsupported_platform/error)
  shown in the UI; resolved the huggingface-hub dependency conflict; split installs
  into per-provider requirements files; wrote INSTALL.md. INSTALLED all engines and
  verified the local transcribe paths.
- Decided: Drop the unmaintained `banglaspeech2text` pip package (pins
  huggingface-hub==0.11.1) and run shhossain/whisper-*-bn via `transformers`
  instead. Per-provider optional requirements files. Server STT = record→upload→
  transcribe; browser stays live. (ADR-0015 to ADR-0018.)
- Broke / problem: `requirements-local.txt` had a real conflict (fixed by the split).
  `torch==2.5.1` pin had no Python-3.14 wheel → unpinned (got torch 2.12.1).
  `qwen-asr` is INVASIVE: it bumped fastapi 0.115→0.137, starlette→1.3, transformers
  5→4.57, huggingface_hub→0.36 and pulled gradio/flask. App still works (13 tests
  pass, server boots) but Qwen may warrant its own venv.
- Deferred: Live Groq STT test (would spend the human's free quota). Qwen live run
  (3.4 GB download + very slow on CPU) — installed/ready but unverified. WER/latency
  on real Bangla speech. Regenerating the exposed Groq key (human action).
- Next: Human runs the live mic test for each provider in Chrome, collects ~50
  samples, and records real latency/WER. See `current_task.md`.

## Session 2 — 2026-06-19 — Phase 0 Steps 3–5: correction service + API + frontend
- Did: Built the correction service (Step 3): `services/correction/base.py`
  (`Corrector` ABC) + `openai_compatible.py` (`OpenAICompatibleCorrector` +
  `build_corrector()` + strict prompt + manual `__main__` live check) and
  `test_corrector.py` (4 offline guards). Built the API (Step 4):
  `schemas/transcript.py`, `api/routes_transcripts.py` (`POST /api/correct`,
  `GET /api/transcripts`), and `main.py` (lifespan `init_db`, `/health`, serves
  frontend or a placeholder). Built the frontend (Step 5): `frontend/index.html`,
  `app.js` (Web Speech API bn-BD, interim grey / final verbatim), `styles.css`.
  Fixed `.claude/launch.json` to use the venv Python. Ran the server via the
  preview tool and verified the page renders with no console errors.
- Decided: `POST /api/correct` persists RAW *before* calling the LLM, so raw
  survives a correction failure (502 with raw kept); misconfig fails fast (500).
  Recorded as ADR-0013.
- Broke / problem: `launch.json` first used system `python` (no uvicorn) → fixed to
  `.venv/Scripts/python.exe` (Windows-specific; Arch needs `.venv/bin/python`).
- Deferred: Live Gemini call NOT auto-run (spends free-tier quota) — left as a
  manual check for the human. No automated test for `/api/correct` (would hit the
  network). Groq/OpenRouter still interface-only. Frontend = plain HTML/JS (React later).
- Next: Step 6 — human runs the end-to-end live mic test in Chrome on both
  machines and collects ~50 sample utterances. See `current_task.md`.

## Session 1 — 2026-06-19 — Phase 0 scaffolding + backend skeleton (Steps 1–2)
- Did: Approved the Phase 0 plan, then built the foundation (not a throwaway
  demo folder): `requirements.txt`, `.gitignore`, `backend/.env` + `.env.example`,
  and the backend skeleton — `backend/app/core/config.py` (pydantic-settings),
  `backend/app/db/` (database.py, models.py `Utterance`, repository.py), and
  `backend/tests/test_raw_immutable.py`. Installed deps in `.venv` and ran tests.
- Decided: Build the real `backend/` + `frontend/` structure now (foundation for
  the full app); SQLite via a repository layer; one FastAPI server serving the
  frontend; mic + manual-text fallback; correction via the OpenAI-compatible
  client pointed at Gemini (swappable). Recorded as ADR-0009 to ADR-0011.
- Broke / problem: Pinned `SQLAlchemy==2.0.36` crashed on Python 3.14.4
  (typing-union `__getitem__` bug). Fixed by upgrading to `2.0.51` and re-pinning.
- Deferred: Gemini code + the actual network call, API routes, frontend
  (Steps 3–5). Groq/OpenRouter fallback (interface only). The human still needs to
  REGENERATE the pasted Gemini key and put it in `backend/.env`.
- Next: Step 3 — correction service (`Corrector` ABC + `OpenAICompatibleCorrector`
  with the strict correct-only prompt). See `current_task.md`.

## Session 0 — 2026-06-18 — Project setup & memory system
- Did: Created the project memory system: `CLAUDE.md` plus `agent_docs/`
  (constitution, milestone_log, current_task, changelog, test_log, decisions,
  codebase_map, session_protocol). No code yet.
- Decided: Locked in the starting stack and key choices — recorded as
  ADR-0001 to ADR-0008 in `decisions.md`.
- Broke / problem: None (nothing built yet).
- Deferred: All actual coding. AMD-GPU acceleration deferred (CPU-only first).
  Real Bangla-fine-tuned model deferred to Phase 2.
- Next: Build the Phase 0 demo (browser Web Speech API live Bangla transcription
  + free-LLM correction). Plan it with the human before coding.
  See `current_task.md`.
