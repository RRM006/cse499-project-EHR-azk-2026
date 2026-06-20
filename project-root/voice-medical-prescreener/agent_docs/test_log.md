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
- **Module 5 (Emergency):** recall on a fixed list of red-flag phrases (we want
  to almost never miss an emergency).
- **Module 10 (Risk):** accuracy / confusion matrix on labeled cases.

## How to measure WER (quick note for later)
WER = (substitutions + insertions + deletions) / number of words in the reference.
Use the `jiwer` Python package against a small set of audio clips that we have
transcribed by hand (the "ground truth"). Record the model + machine each time.

---

## Test entries (newest first)

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
