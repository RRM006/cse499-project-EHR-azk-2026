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
