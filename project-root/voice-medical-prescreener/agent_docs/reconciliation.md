# reconciliation.md — Mockup ↔ Locked Architecture Reconciliation + Sequential Build Plan

> **Created:** 2026-07-03 (Session 8). **Status:** Approved by the human.
> Reconciles `agent_docs/mockups-redesign.html` (three-portal UI mockup) against
> `agent_docs/architecture.md` (locked data/API design), the capstone brief
> (`Conext_for_CSE499_capston_Project.md`, repo root) and the flowchart. The build plan
> below LAYERS ON TOP of architecture.md's G0–G7 Alembic staging — it does not replace it.
>
> Human decisions recorded here (2026-07-03): (1) **medic is a real, new role**;
> (2) **OTP is a stub** for the capstone demo; (3) **the mockup's clinical-blue design
> system becomes the project design**, superseding the Mintlify rule (ADR-0029).

---

## 1. Verified current state (what actually exists, Session 6 codebase)

- DB: only `utterances` + `documents` (Alembic `0001_baseline`, `0002_add_stt_provider_and_doc_kind`).
  No `visits` / `patients` / `users` / `clinics` yet; `documents.utterance_id` is the session grain.
- API: flat routes only — `POST/GET /api/transcripts`, `GET /api/transcripts/{id}`,
  `POST /api/transcripts/{id}/documents/{raw,corrected}`, `POST /api/correct`,
  `GET /api/documents`, `GET /api/documents/{id}/download`, `/health`.
  None of architecture.md §4's `/api/visits/...` routes exist yet.
- **Rev `0003` is unwritten**, so every CHECK constraint planned for G0 can still be
  defined freely without editing any applied migration (ADR-0022 discipline preserved).
- 19 tests pass (baseline — must never regress). Raw immutability + .docx export code untouched.

## 2. Reconciliation table

| # | Mockup element | architecture.md gap | Resolution | Principle check | Deviation? |
|---|---|---|---|---|---|
| a1 | "Medic" triage role | `users.role` CHECK = doctor/desk/admin | Add `'medic'` to the CHECK **inside the not-yet-written `0003`** | users seam unchanged | No |
| a2 | Medic → doctor assignment ("Assign Doctor" + "Submit & Forward") | No assignment field; `doctor_reviews` is append-only doctor *actions* (wrong tool) | New nullable `visits.assigned_doctor_id` FK → `users.id`. A workflow attribute of the aggregate root; `doctor_reviews` unchanged | Aggregate root (P2) ✓; append-only (P4) untouched | No |
| b | Phone + OTP patient login | `patients.external_ref` comment says "phone hash"; no auth table | Phone = patient lookup key: normalized `+880…` stored in `external_ref` (unique per clinic; hashing deferred). **OTP = stub**: verify endpoint checks `DEV_OTP` from `.env`. **No session table** — the kiosk "session" is `visits.uuid`. Real SMS gateway = later swap behind one function | Config-driven (P7) ✓; no new table | No |
| c | 10-fixed-field summary (patient review + medic/doctor edit cards) | `entities` JSON is free-form | Keep JSON (P3): a `summary_fields` object inside `case_profiles.entities`, exactly 10 keys — `main_problem`, `onset_duration`, `symptom_details` {location, character, worse, better, pain_severity_0_10}, `associated_symptoms`, `medical_history`, `current_medicines`, `allergies`, `recent_changes_exposures`, `treatments_tried`, `current_concern` — each `{value, source: 'ai'\|'human', edited_by?, edited_at?}` (powers the AI-Extracted / Human-Edited badges). Shape enforced by a Pydantic schema in code, NOT columns (§6.2: nothing is filtered/sorted in SQL yet). Staff edits also logged append-only in `audit_log` (`action='profile.field_edit'`, detail={field, old, new}) | P3 ✓; §6.2 ✓; P4 ✓ | No |
| d | Kiosk auto-logout / medic forward flow | `visits.status` CHECK lacks a medic→doctor stage | Countdown/reset = **purely frontend state**. Backing transitions: patient "Confirm & Submit" → `awaiting_review` (medic queue); medic "Submit & Forward" → NEW status **`'awaiting_doctor'`** (doctor queue; added in unwritten `0003`); doctor "Accept & Write to EHR" → `reviewed` + `completed_at` + a `doctor_reviews` row | Small closed enum; no applied migration touched | No |
| e | Risk badge "Moderate" | tier CHECK uses `'medium'` | Display-label mismatch only. Schema/API keep tier codes; ONE shared frontend `TIER_LABELS` map ({low, medium, high, critical} → {en, bn} labels) used by all portals | Data/display separation ✓ | No |
| f1 | Mockup's clinical-blue design system | Contradicts CLAUDE.md's DESIGN-mintlify rule | **Human decided: mockup wins** → ADR-0029; DESIGN doc + CLAUDE.md frontend rule to be updated | — | **Yes — flagged, human-approved** |
| f2 | OTP typed on keyboard | ADR-0027 voice-only | Voice-only governs *clinical* input, not identification. Clarification recorded in ADR-0030 | ADR-0027 intact | No |
| f3 | Mockup XAI copy names "acute coronary syndrome" | Rule #2: never diagnose | Content guideline: M11 prompts cite drivers (symptoms, age, duration, red-flag phrase) WITHOUT disease names. Mockup copy only, not schema | Rule #2 preserved | No (guideline) |
| f4 | Admin CSS + "Niramoy Admin Center" string | No admin portal in any doc | Explicitly out of scope; dead CSS ignored | — | No |
| f5 | Assistant questions in chat thread / verbatim panel | — | Already modeled: `utterances.role='system'` + `followup_questions` | ✓ | No |
| f6 | Medic queue shows risk tiers at intake | Implies M10 runs before staff review | Matches the flowchart (M10 before M14): assess runs when the patient submits. Sequencing note only | ✓ | No |
| f7 | "Speak Again" correction loop from summary | — | More utterances + re-run extraction; raw immutability (rule #1) unaffected | Rule #1 ✓ | No |
| f8 | "Override to Low-Risk" / "Accept & Write to EHR" | — | `doctor_reviews.override_tier` + status → `reviewed`. The DB **is** the EHR (M13) — "Write to EHR" is a transition + review row, not a new store | P4 ✓ | No |

**Net schema delta vs. architecture.md — three small additions**, all inside the unwritten
`0003`: the `'medic'` role value, the `'awaiting_doctor'` status value, and
`visits.assigned_doctor_id`, plus one documented JSON shape (`summary_fields`).
No Session-7 locked decision (M5 retirement, red-flag-in-M10, voice-only, ADR-0024–0026)
is disturbed.

## 3. Sequential build plan (Database → Backend → Frontend)

Rules for every step: small + independently testable; Alembic upgrade verified on a COPY of
the real DB and on a fresh DB; the 19 baseline tests must pass; raw/corrected transcript
logic and .docx export code are never touched; plan-then-"go" per CLAUDE.md before each step.

### Database (Alembic revs; ADR-0022 discipline)

| Step | Rev | Stage | Adds | Gate |
|---|---|---|---|---|
| DB-1 | `0003` | G0+ | `clinics`, `users` (role CHECK incl. **'medic'**), `patients` (phone in `external_ref`, unique per clinic), `visits` (status CHECK incl. **'awaiting_doctor'**; **`assigned_doctor_id`** FK nullable); `utterances` += nullable `visit_id`, `role` (default 'patient'), `seq`; `documents` += nullable `visit_id`. Legacy utterances attach to one synthetic "legacy" visit. Seed: 1 clinic, 1 medic, 2 doctors, 1 admin | old data preserved; 19 tests pass |
| DB-2 | `0004` | G1 | `case_profiles` (with `summary_fields` shape doc), `module_events` | profile writable per visit |
| DB-3 | `0005` | G2 | `followup_questions` | — |
| DB-4 | `0006` | G3 | `risk_assessments`, `xai_explanations` | — |
| DB-5 | `0007` | G4 | `reports` | — |
| DB-6 | `0008` | G5 | `doctor_reviews`, `feedback` | — |
| DB-7 | `0009` | G6 | `audit_log` (incl. `profile.field_edit`) | — |

### Backend (thin router → service → repo per stage; flat routes kept as aliases)

| Step | Needs | Routes / work |
|---|---|---|
| BE-1 | DB-1 | `POST/GET /api/visits`, `GET /api/visits/{uuid}`, `POST /api/visits/{uuid}/utterances` (+ `/api/transcripts` alias); `POST /api/patients/lookup` (phone → patient + open visit); stub `POST /api/patients/verify-otp` (`DEV_OTP`) |
| BE-2 | DB-2 | `POST /api/visits/{uuid}/intake` (M2→M3→M4→M6, providers per ADR-0026), `GET /api/visits/{uuid}/profile`; every run logs `module_events` |
| BE-3 | DB-3 | `POST /api/visits/{uuid}/followup/next` + `/followup/answer` (M7–M9 loop; answers are utterances) |
| BE-4 | DB-4 | `POST /api/visits/{uuid}/assess` + `GET /api/visits/{uuid}/risk` (M10 red-flag rule forces critical — ADR-0024; M11 XAI without disease names) |
| BE-5 | DB-1..4 | `GET /api/dashboard?role=medic\|doctor` (queues by status/assignment); `PATCH /api/visits/{uuid}/profile/fields/{key}` (staff edit → `summary_fields` update + audit row); `POST /api/visits/{uuid}/assign` (sets `assigned_doctor_id`, status → `awaiting_doctor`) |
| BE-6 | DB-5/6 | `POST/GET /api/visits/{uuid}/report`; `POST /api/visits/{uuid}/review` (override tier / accept → `reviewed`); `POST /api/visits/{uuid}/feedback`. Auth stays stubbed (`core/security.py`) |
| BE-7 | DB-7 | audit rows on every state change; per-visit document export kinds |

### Frontend (three static portals; clinical-blue system per ADR-0029)

| Step | Needs | Work |
|---|---|---|
| FE-0 | — | Shared layer: mockup CSS vars/components extracted; `TIER_LABELS` map; bilingual `data-en/data-bn` helper; `tts.js` with `speak()` + bn-BD voice pick (this is still Phase A / Step A1's helper) |
| FE-1 | BE-1..3 | **Patient kiosk (`frontend/`)**: phone → stub OTP → chat-thread voice conversation (Web Speech STT + TTS, ADR-0027/0028; mic-failure text fallback) → 10-field summary review → Confirm & Submit → auto-logout countdown → full local reset |
| FE-2 | BE-1/2/4/5 | **Medic portal (`frontend_medic/`)**: stub login → queue (`awaiting_review`, tier badges) + phone lookup → detail: collapsible read-only RAW verbatim panel + 10 editable field cards (AI/Human badges) + Assign Doctor + Submit & Forward |
| FE-3 | BE-4/5/6 | **Doctor portal (`frontend_doctor/`)**: stub login → assigned queue (`awaiting_doctor`) → detail: verbatim panel + risk/red-flag/XAI safety panel + 10 field cards + Override to Low-Risk / Accept & Write to EHR |

### Verification per step
- DB: Alembic upgrade on a copy of the real DB + a fresh DB; `pytest backend/tests/` (19 baseline pass) + new per-stage tests.
- BE: route tests (TestClient + StaticPool in-memory SQLite, as in Session 6).
- FE: preview server on port 8001; snapshot + interaction checks; TTS/STT human-verified per test_log TC-V2/TC-V3.
