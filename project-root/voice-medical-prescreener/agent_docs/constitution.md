# constitution.md — The Project Constitution

> This is the **stable** core of the project. It changes very rarely.
> If something here ever needs to change, treat it as a big decision and record
> it in `decisions.md`. Everything else in the project must obey this file.

---

## 1. Purpose (one paragraph)

Before a patient meets the doctor, they speak naturally in Bangla, Banglish, or a
regional dialect to describe their symptoms and history. The system transcribes
that speech, cleans and structures it, finds gaps and asks follow-up questions,
checks for emergencies, assesses risk, and hands the doctor a clear, structured
pre-screening report — so the doctor spends less time on documentation and misses
less critical information. **The system assists the doctor. It never replaces the
doctor and never diagnoses.**

---

## 2. The four non-negotiable rules

These are the rules the whole system is built around. They must never be broken,
in any module, for any reason.

1. **Preserve the patient's exact words.**
   Whatever the patient said is captured and stored *unchanged* as the "raw
   transcript". Spelling fixes, normalization, Banglish→Bangla conversion, and
   AI correction all happen in *separate, later* steps and are stored in
   *separate* fields. We must always be able to show exactly what was said.

2. **Never diagnose.**
   The system narrows the list of things worth considering ("differential") and
   surfaces information. It does not tell anyone what disease they have. The
   doctor decides.

3. **Emergency detection comes first.**
   Once the emergency module exists, red-flag symptoms (e.g. chest pain, stroke
   signs, severe breathing difficulty, loss of consciousness) are checked before
   anything else and trigger an alert immediately.

4. **Protect patient data.**
   Patient data is sensitive and must be handled carefully. During development we
   use synthetic or consented sample data only. We never send real patient data
   to a free AI API that may store or train on it. Real deployment will need
   encryption and a no-training (paid or local) AI provider.

---

## 3. The 15 modules and how they connect

The pipeline runs roughly top to bottom. Module 5 (emergency) runs in parallel and
can interrupt at any time. Modules 7→8→9 form a loop that repeats until enough
information is collected.

| # | Module | What it does | Depends on |
|---|--------|--------------|------------|
| 1 | Speech-to-Text | Live voice → raw text (Bangla/Banglish/dialect) | mic input |
| 2 | Text Processing & Normalization | Clean/correct text in a *separate* field | 1 |
| 3 | Information Extraction | Pull out symptoms, body parts, duration, severity, meds, history | 2 |
| 4 | Initial Clinical Summary | Short human-readable summary of the chief complaint | 3 |
| 5 | **Emergency Detection** | Flag life-threatening symptoms — **top priority** | 3 (runs in parallel) |
| 6 | Missing Information Analysis | List what is known vs. still missing | 3 |
| 7 | Follow-up Question Generation | Ask targeted questions (Bangla/English) to fill gaps | 6 |
| 8 | Response Processing & Profile Update | Re-run answers through 2–3, merge into profile | 2, 3, 7 |
| 9 | Case Completion Check | Score completeness; loop back to 7 if needed | 6, 8 |
| 10 | Risk Assessment Engine | Classify Low / Medium / High / Critical | 3, 5, 9 |
| 11 | Explainable AI (XAI) | Plain-language reason for the risk level | 10 |
| 12 | Structured Clinical Report | Assemble the full report (PDF + dashboard) | 4, 5, 10, 11 |
| 13 | EHR Database | Securely store transcripts, profiles, reports, audit logs | all |
| 14 | Doctor Dashboard | Web UI for the doctor to review/override/annotate | 12, 13 |
| 15 | Feedback & Continuous Learning | Doctor feedback improves the models over time | 13, 14 |

**Build order:** We are doing Module 1 first (live STT + correction), because every
other module depends on having accurate text to work with. We do NOT start later
modules until Module 1 is solid enough to feed them.

---

## 4. Tech constraints (the box we build inside)

- **Languages of input:** Standard Bangla, regional dialects (e.g. Sylheti,
  Chittagonian), and Banglish (Bangla–English code-switching). Also Roman Bangla /
  phonetic typing as an optional representation (e.g. "Amar nam ki" → আমার নাম কি).
- **Hardware:** No NVIDIA GPU. CPU-only by default. Must run well on a 6-core AMD
  CPU with 12–24 GB RAM. Any AMD-GPU acceleration is a bonus, never a requirement.
- **Platforms:** Must work identically on **Windows and Arch Linux**, from a single
  `requirements.txt` and a Python virtual environment (venv).
- **Cost:** Free and open-source strongly preferred. Free APIs allowed where they
  clearly help (e.g. LLM text correction), but always behind a swappable interface
  so we can change provider when free limits change.
- **Future:** A mobile app is planned later. The backend must be a clean API
  (WebSocket + REST) that a mobile app can reuse without rewriting the core.

---

## 5. Realistic expectations (so we don't fool ourselves)

- Bangla speech-to-text is hard. Out-of-the-box word error rate (WER) is often
  25–45%, and worse with dialects, code-switching, medical terms, and noise.
- "It runs" is **not** success. Success for an ML/NLP module is measured with
  numbers (WER, precision/recall, accuracy) recorded in `test_log.md`.
- The hardest challenges, in order: (1) Banglish code-switching, (2) regional
  dialects, (3) medical terms and drug names, (4) noisy clinic audio.
- This is exactly why rules #1 (keep raw words) and #2 (never diagnose) exist:
  the system must stay honest about its uncertainty.
