# Niramoy — Technical Brief (Your Interview Crib Sheet)

> Everything you should be able to explain about your own system, in plain language, grounded only in what the project actually contains. Read it once end-to-end, then skim the headers before the interview. Nothing here is invented — where something isn't built or isn't measured, it says so.

---

## 1. What it is, in one paragraph

Niramoy is a **voice-first medical pre-screening** system for Bangladeshi clinics. Before seeing the doctor, a patient speaks their symptoms naturally — in Bangla, Banglish (Bangla–English mix), or a regional dialect. The system transcribes the speech live, cleans it in a **separate** step (never touching the original), extracts structured clinical information, asks follow-up questions (spoken aloud and shown on screen), assesses a risk level with red-flag detection and a plain-language explanation, and hands the doctor a structured report — all before the consultation. It **assists** the doctor; it **never diagnoses**.

It's organised as **15 modules** (M1–M15). M1–M14 are built, **M5 (standalone emergency detection) was deliberately retired** and folded into M10, and **M15 (a retrain/continuous-learning pipeline) is future work**. A later addition, **M16**, is a doctor-side drug/test information assistant.

---

## 2. The four non-negotiable rules (know these cold — they explain most decisions)

1. **Raw words are immutable.** The patient's exact utterance is stored once and never edited. Cleaning, correction, and Banglish→Bangla normalisation happen in *separate, later* fields. Enforced by code and a test.
2. **The system never diagnoses.** It narrows the differential and surfaces information; the doctor decides.
3. **Surface red flags, never falsely reassure.** A rule-based red-flag check (inside M10) forces life-threatening symptoms to the Critical tier, independent of the AI.
4. **Protect patient data.** Development uses synthetic/consented data only, because free AI tiers and the browser speech API send data to third parties.

---

## 3. Architecture at a glance

**Layers:** `browser portals (HTML/JS)` → `FastAPI REST API` → `service layer (one file per module)` → `repository` → `SQLite (SQLAlchemy + Alembic)`.

- **Backend:** Python + **FastAPI + Uvicorn**. REST today; a native WebSocket is reserved for future streaming STT.
- **Database:** **SQLite** via **SQLAlchemy**, schema evolved with **Alembic migrations**. Config-driven DB URL → can point at **Postgres** later with no code change. Currently **18 tables, 14 migrations (Alembic head 0014).**
- **Frontend:** plain **HTML/CSS/JS** (no framework) on a shared **"Teal Medical" design system**. Three portals + a landing directory + a legacy transcript demo.
- **AI/LLM:** one **swappable, OpenAI-compatible client**; all providers speak the same API.
- **Runs** with a single command: `uvicorn backend.app.main:app`. Cross-platform (Windows + Arch Linux) from one `requirements.txt`. **CPU-only, no GPU dependency** (hardware constraint).

**Why this shape:** the design goal was "add features without major changes." Every table hangs off the `visit` aggregate root; new module outputs are new child tables; new module *runs* are just a new `module_code` value — no schema change. Evolving structured data lives in JSON columns; it's promoted to a real column only when you need to filter on it.

---

## 4. The three portals (roles) and the handover chain

| Portal | URL | Who | Does |
|---|---|---|---|
| **Patient** | `/kiosk.html` | Patient (often elderly/non-technical) | Voice-first intake: phone+OTP → speak → summary → submit |
| **Medic** | `/medic/` | Triage staff | Urgency-ordered queue; verify AI fields vs raw words; record vitals; forward to a doctor |
| **Doctor** | `/doctor/` | Physician | Safety story first (tier/red-flags/XAI); history; review; prescribe; write to EHR |

**Handover = the visit `status`:** `in_progress` → (patient submits) `awaiting_review` → (medic forwards) `awaiting_doctor` → (doctor reviews) `reviewed`/`closed`. One-directional, no back-channel by design. The medic and doctor read the **same** `case_profiles` row — there's no copy and no message passing.

---

## 5. The 15 modules (the pipeline)

| # | Module | What it does |
|---|---|---|
| M1 | Speech-to-Text | Live voice → raw text (browser Web Speech API, `bn-BD`) |
| M2 | Text Processing | Clean/correct in a **separate** field (LLM) |
| M3 | Information Extraction | Symptoms, body part, duration, severity, meds, history (LLM) |
| M4 | Clinical Summary | Short chief-complaint summary (LLM) |
| ~~M5~~ | ~~Emergency Detection~~ | **Retired** — red-flag check moved into M10 |
| M6 | Missing-Info Analysis | Known-vs-missing checklist |
| M7 | Follow-up Questions | Targeted questions, spoken + on screen (LLM) |
| M8 | Response Processing | Re-run answers through M2/M3, merge into profile |
| M9 | Completion Check | Score completeness; loop or stop (local; bounded) |
| M10 | Risk Assessment | Low/Medium/High/Critical + **rule-based red-flag** override |
| M11 | Explainable AI (XAI) | Plain-language reason for the risk (LLM) |
| M12 | Structured Report | Assemble the doctor-facing report (no diagnosis) |
| M13 | EHR Database | Store everything, audited |
| M14 | Doctor Dashboard | Review/override/annotate/prescribe |
| M15 | Feedback/Learning | **Future** retrain + regression pipeline |
| M16 | Drug/Test Assistant | Doctor-side info lookup with a server-attached disclaimer |

**Which parts are LLM vs local:** M2, M3, M4, M7, M8, M10 (tier), M11, M12, M16 use the LLM. **M1 (STT), M9 (completeness), and the M10 red-flag rule are local/no-API.** The follow-up loop is **bounded server-side** (min ~4, max ~5 questions, completeness threshold ~0.7) so it can never run forever.

---

## 6. The AI / LLM strategy (a favourite interview topic)

- **One client, many providers.** All providers are OpenAI-compatible, so a single `llm_client` swaps `base_url` + model + key from config. Providers used: **Gemini Flash** (quality tasks), **Gemini Flash-Lite** (cheap structured extraction), **Groq** (fast live-loop tasks), plus **Cerebras** and **OpenRouter** as fallbacks.
- **Redundancy has three multiplying dimensions:** **buckets** (providers, in a fallback order) × **keys** (up to 3–4 per provider, each its own free quota) × **models** (each setting accepts a comma-separated list). Order: every model of key 1, then key 2, then key 3, then the next provider. A rate-limit (429) cools down only that one (provider, key, model) path, temporarily — nothing is permanently disabled.
- **Why:** free tiers are metered and their models get retired without notice. This came from a real pre-demo outage.
- **The future swap:** because everything goes through this one client, a local quantized model (served behind any OpenAI-compatible local server) becomes a config change — the cloud chain can even stay as a fallback during evaluation.

---

## 7. The voice flow (what's built vs. what's next)

**Built (the hands-free "happy path"):**
- Phone + OTP login (OTP can be spoken digit-by-digit or typed).
- AI speaks the question (TTS) **and** shows it as text.
- The mic **opens itself** after the audio ends, behind an **echo guard** (never starts while TTS is speaking → the AI's voice can't contaminate the transcript).
- Continuous recognition with interim results; a **silence-based 3-2-1 confirmation window**; **barge-in cancels** it (resumed speech keeps listening).
- A **spoken read-back** of each answer ("I heard you say…") that can be confirmed by voice ("হ্যাঁ/না").
- **Voice ↔ typing toggle**, always visible; both use the **same endpoint and pipeline** (differ only by `source: mic|manual`).
- Config-tunable timings served by `GET /api/config` (countdown, TTS guard, etc.).

**Not built yet (Step "S5"):** automatic no-speech re-prompt, an empty-answer guard beyond the basic one, a hard max-answer cap that's actually wired in, and mic-permission/tab-visibility recovery. Part of it is intentionally blocked on a human decision about how to handle mid-turn word loss. **Be honest about this line if asked.**

**STT/TTS specifics:** STT is the **browser Web Speech API** (`webkitSpeechRecognition`, `lang='bn-BD'`, Chrome/Edge, needs internet). TTS is **server-side edge-tts** (Microsoft neural Bangla voice) with **espeak-ng** as an offline fallback; an installed browser Bangla voice wins if present. On-screen text is always the mandatory fallback channel.

---

## 8. Data model & data flow (the essentials)

- **`visits` is the aggregate root.** One pre-screening = one visit. Everything hangs off it: `utterances`, `case_profiles`, `followup_questions`, `risk_assessments`, `xai_explanations`, `reports`, `documents`, `doctor_reviews`, `feedback`, `module_events`, plus `clinics`, `users`, `patients`, `prescriptions`, `clinical_notes`, `audit_log`, `otp_codes`.
- **`utterances`:** `raw_text` (write-once, immutable) + `corrected_text` (separate, nullable). This *is* rule #1 in the schema.
- **`case_profiles.entities.summary_fields`:** the 10 fixed fields as JSON, each `{value, source: 'ai'|'human', edited_by?, verified_by?}`. Staff edits set `source='human'`; the AI merge (M8) never overwrites a human value. "Verified" is provenance only — it never changes the value.
- **`risk_assessments`:** append-only; latest row wins; `red_flags` + `rule_overrode` make the safety override queryable.
- **`documents`:** export files (DOCX/PDF/FHIR) are **regenerable** — the DB is the source of truth; documents are a *rendering*, not a second record.
- **`audit_log` + `module_events`:** append-only. `module_events` records which provider served each call and its latency — the free-tier strategy is observable as data.
- **Patient identity is keyed by phone.** A subtle real bug: because a name persists per phone across visits, a name once entered shows on later visits. The fix: the UI shows the name's **origin** (derived from `audit_log`), reporting **`unknown`** rather than guessing — and never claims a name was given "here" when it wasn't.

**End-to-end data flow:** mic → raw utterance (stored) → M2 correction → M3/M4 extraction+summary → M6 gaps → M7 question → patient answer (new utterance) → M8 merge → M9 completeness (loop or stop) → M10 risk + red flags → M11 XAI → M12 report → medic verify/vitals → doctor review/prescribe → M13 store + `documents` export.

---

## 9. Security & privacy (be precise and honest)

- **What's real:** real **OTP** — codes are **hashed, expiring, single-use**, behind a pluggable sender (`dev` logs to server; `textbee` sends real SMS via an Android gateway). A `000000` dev bypass works **only** on the dev channel. All state-changing calls write an `audit_log` row. The `clinic_id` tenancy seam exists from day one.
- **What's stubbed/honest:** **staff authentication is stubbed** (demo logins; real auth is a later phase). Data is **not encrypted at rest** yet.
- **The known privacy trade-offs (state them yourself):** the **browser Web Speech API sends audio to Google**; **edge-tts sends the question text to Microsoft**; **free LLM tiers may train on inputs**. That's why development is synthetic/consented-only, and it's the single biggest reason the roadmap is **on-device**.

---

## 10. Testing & how you debug

- **~1,196 automated tests** (pytest), 2 skipped, 0 failing at last count — covering the follow-up loop, intake, triage, risk, red-flag override, OTP, TTS, migrations, the multi-key provider fallback, raw-immutability, kiosk behaviours, and static-asset presence.
- **Tests are offline** — no network, no real API calls (rule #4).
- **A real debugging lesson you can tell:** a medic "Edit" button did nothing. It wasn't the handler or the API — a CSS `transform` under a `perspective` was **rescaling a card on press**, so `mousedown` and `mouseup` landed on different elements and the click never fired. The fix was to carry depth in the **shadow**, not a transform. The meta-lesson: a programmatic `.click()` can't catch a hit-target defect — you have to drive a real mouse. (There's a test pinning it now.)
- **Decision records:** ~69 **ADRs** document *why* each choice was made — an unusually complete paper trail for a student project.

---

## 11. Key files / where things live (so you can name them)

- `backend/app/main.py` — FastAPI app; mounts the API routers and the static portals.
- `backend/app/api/routes_*.py` — thin REST routers (visits, followup, risk, dashboard, prescription, report, assistant, tts, config, …).
- `backend/app/services/*.py` — one file per module: `intake.py`, `followup.py`, `risk.py`, `red_flags.py`, `triage.py`, `clinical_reference.py`, `ehr_export.py` (FHIR), `ehr_pdf.py` (Bangla PDF), `llm_client.py`, `identity.py`, `otp/`, `tts/`, `correction/`.
- `backend/app/core/config.py` + `llm_providers.py` — config and the provider/fallback registry.
- `backend/app/db/models.py` — all 18 SQLAlchemy tables; `migrations/versions/0001…0014`.
- `frontend/kiosk.html` + `kiosk.js` — the patient voice portal (the big one).
- `frontend_medic/`, `frontend_doctor/`, `frontend_shared/` (`shared.css`, `shared.js`, `staff.js`, `tts.js`, `motion.css`).
- `agent_docs/` — the living project brain: `constitution.md`, `architecture.md`, `decisions.md` (ADRs), `portal_roles.md`, `test_log.md`.

---

## 12. Engineering decisions & why (quick-fire)

- **FastAPI over Flask:** async model suits future WebSocket streaming; clean typed REST now.
- **SQLite now, Postgres later:** zero-setup for the capstone; one config URL to switch; migrations mean you never delete the DB.
- **Plain HTML/JS, no React:** fastest path to a working kiosk for elderly users; the target device is a browser + mic; React was deferred, not needed.
- **Browser Web Speech API for STT:** free, live, `bn-BD`, zero ML setup — the right *quick-start* path. The robust local path (faster-whisper, int8, CPU) is planned Phase-1 behind an STT seam.
- **One OpenAI-compatible LLM client:** provider independence + the future local-model swap.
- **fpdf2 + HarfBuzz for the PDF (not ReportLab):** ReportLab can't shape Bengali conjuncts; the renderer **refuses** rather than ship mangled Bangla (that would break rule #1 in the one export a human reads).
- **HL7 FHIR R4 bundle for the EHR write:** a real interoperability standard; claimed honestly as *structurally valid and conservative*, not certified. The AI's suggested condition is **excluded** from it — the doctor's own diagnosis is exported.
- **Fixed UTC+06:00 offset, not a tz database:** Windows lacks a tz DB, and Bangladesh has had no DST since 2010 — this fixed a real bug where prescriptions written after midnight Dhaka got yesterday's UTC date.

---

## 13. Limitations (say them before you're asked)

Cloud STT (Google); free-tier LLMs → synthetic/consented data only; **no formal WER/accuracy measured yet**; staff auth stubbed; no encryption at rest; SQLite single-node; fully-automatic voice endpointing (S5) unfinished; appearance of the newest UI changes verified by behaviour/tests, not always by a browser render.

## 14. Realistic future (grounded in the plan)

1. **On-device quantized summary model** (the team's Moshi work) → replaces the LLM API for extraction/summary; local, private, no quota.
2. **On-device quantized STT/TTS** → replaces the browser speech APIs → fully offline, removes the Google/Microsoft data path.
3. **Finish the fully hands-free follow-up loop** (S5 robustness).
4. **Productionisation:** real auth, Postgres, encryption at rest, a single-container deploy.
5. **Formal evaluation:** WER, extraction precision/recall on a held-out Bangla/Banglish set — recorded as thesis evidence.

---

## 15. Your ownership line (rehearse this)

"I built this with AI coding assistance, and I directed it end to end. I chose the architecture and the stack, set the non-negotiable rules, debugged the hard defects, wrote and curated the tests and decision records, and ran the live tests myself. I can open any file and tell you what it does and why it's there. Ask me anything."
