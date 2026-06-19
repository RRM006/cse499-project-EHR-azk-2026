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
