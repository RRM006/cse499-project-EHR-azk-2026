# codebase_map.md — Where Everything Lives

> A living map of the repo so Claude (and you) can find things without
> re-exploring the whole project each session. Update it whenever you add or move
> a folder/file. Keep each note to one line.

**Last updated:** 2026-07-10 (Session 22 — new test files so far this cycle:
`backend/tests/test_followup_min_questions.py` (S20, P1-3),
`backend/tests/test_submit_background.py` (S21, P1-5), and
`backend/tests/test_patient_demographics.py` (S22, P2-2) → suite **166**. Otherwise edits to
existing files only: S19 = `shared.css` (Teal Medical, ADR-0043), `shared.js` (`logout()`,
placeholder i18n), `kiosk.js`/`kiosk.html`, medic/doctor headers; S20 = `config.py`
(+`followup_min_questions`), `routes_followup.py` (floor gate), `services/followup.py` (deepening
M7 prompt), kiosk missing-field highlight; S21 = `routes_dashboard.py`
(`_post_submit_assessment` BackgroundTasks job); S22 = `kiosk.html` (P1-6 teal retint),
`shared.js`/`staff.js` (P2-1 `parseUtc`/`dhakaTime`/`dhakaDateTime`), `services/intake.py`
(+`apply_demographics`, new `patient_demographics` extraction key),
`services/profile_update.py` (calls the writer), `schemas/dashboard.py` +
`routes_dashboard.py` (extended vitals PATCH), `frontend_medic/index.html` (Gender row +
identity editor). Still coming: `Visit.submitted_at`+Alembic 0011, an OTP table,
`routes_assistant.py` — update this map when those land.)

---

## Current structure (real, today)

> Session 8 built the whole reconciled system. Session 9 moved the old Module-1 transcript app
> into `frontend_legacy/` (served at `/legacy/`, behavior unchanged — ADR-0031) and put a
> portal landing page at `/`.

```
voice-medical-prescreener/
├── CLAUDE.md · DESIGN-mintlify.md · INSTALL.md · README.md
│     # CLAUDE.md frontend section points at the clinical-blue system (ADR-0029, done S8b);
│     # DESIGN-mintlify.md carries a SUPERSEDED banner — design source of truth is frontend_shared/shared.css.
├── requirements.txt              # CORE deps (FastAPI, uvicorn, pydantic-settings, SQLAlchemy, alembic, openai, python-docx, pytest)
├── .gitignore                    # ignores .env, .venv/, *.db, *.db.*.bak, *.bak, data/, audio/, models/
├── .claude/launch.json           # preview dev-server configs (uvicorn; PORT 8001): Windows + backend-linux
├── agent_docs/                   # the project's shared brain (living docs) — now incl. architecture.md,
│   │                              #   reconciliation.md, mockups-redesign.html, update_system_flowchart.md,
│   │                              #   context_fixed_problem.md (20-step spec, all ✅), human_live_run_guide.md (S14: human handoff),
│   │                              #   context fixed problem 2.0.md (S18: UI/UX + fixes + OTP + doctor chatbot — now a checkable BUILD TRACKER; STRUCT-1 ✅)
│   └── ... (constitution, milestone_log, current_task, changelog, test_log, decisions, codebase_map, session_protocol)
├── backend/
│   ├── .env / .env.example       # + DEV_OTP (stub OTP), per-bucket model names (ADR-0026)
│   ├── alembic.ini · migrations/env.py (render_as_batch)
│   ├── migrations/versions/      # 0001_baseline · 0002_add_stt_provider_and_doc_kind ·
│   │                              #   0003_aggregate_root (clinics/users/patients/visits + deltas + backfill + seeds) ·
│   │                              #   0004_intake_profile (case_profiles, module_events) · 0005_followup_questions ·
│   │                              #   0006_risk_xai · 0007_reports · 0008_doctor_reviews_feedback · 0009_audit_log ·
│   │                              #   0010_prescriptions_letterhead (visit-grain docs, vitals, letterhead, prescriptions — ADR-0032)
│   ├── prescreener.db            # SQLite (gitignored); 16 tables + alembic_version (head 0010)
│   ├── prescreener.db.pre-000{3,4,5,6,7}.bak · .pre-0010.bak  # per-migration backups (gitignored)
│   ├── data/documents/           # generated .docx (gitignored)
│   ├── app/
│   │   ├── main.py               # lifespan init_db + ENTRY_POINTS startup log; registers transcripts, documents,
│   │   │                          #   visits, followup, risk, dashboard, report routers; mounts /shared /medic
│   │   │                          #   /doctor /legacy + landing/kiosk at / (ADR-0031)
│   │   ├── core/
│   │   │   ├── config.py         # + dev_otp, followup_max_questions, completeness_threshold, per-bucket models
│   │   │   └── llm_providers.py  # provider registry + MODULE_PROVIDERS map (ADR-0026); S17: FALLBACK_ORDER
│   │   │                          #   assigned→Groq→Cerebras→Mistral→OpenRouter + optional Cerebras/Mistral buckets (ADR-0041)
│   │   ├── api/
│   │   │   ├── routes_transcripts.py · routes_documents.py   # (existing, untouched)
│   │   │   ├── routes_visits.py  # NEW: patients/lookup + verify-otp; visits CRUD + utterances; intake; profile
│   │   │   ├── routes_visit_documents.py # S9: POST /api/visits/{uuid}/documents/{transcript|summary_report}
│   │   │   ├── routes_followup.py# NEW: followup/next (M7) · followup/answer (M8+M9); S11: ?scope=fields
│   │   │   │                      #   = KIOSK-7 resume loop (no threshold gate; ADR-0034)
│   │   │   ├── routes_risk.py    # NEW: assess (M10 + rule) · risk (latest + XAI); S11: risk/override
│   │   │   │                      #   (MEDIC-3 human row, audit-logged, red-flag guard — ADR-0035)
│   │   │   ├── routes_dashboard.py # NEW: users list · submit (→auto-assess; S12: +M10C suggestion, best-effort) ·
│   │   │   │                      #   dashboard queues · field-edit PATCH · assign; S12: PATCH profile/condition
│   │   │   │                      #   (C1 staff edit, ADR-0036) + PATCH patients/{id}/vitals (ADR-0037)
│   │   │   ├── routes_report.py  # NEW: report (M12) · review (M14) · feedback (M15)
│   │   │   └── routes_prescription.py # S13: GET .../prescription/context (letterhead prefill, DOCTOR-4/5, ADR-0038) +
│   │   │                          #   POST .../prescription (DOCTOR-6 save row + render .docx, ADR-0039)
│   │   ├── schemas/              # transcript, document (existing) + visit, patient, profile, followup, risk, dashboard,
│   │   │                          #   prescription (S13: letterhead context + create/created — no diagnosis field, rule #2)
│   │   ├── services/
│   │   │   ├── correction/       # (existing) reused as M2
│   │   │   ├── documents/        # (existing) DocxWriter + storage; S9 + visit_docx.py (visit-grain
│   │   │   │                      #   transcript/summary_report writers) + generate_visit_document();
│   │   │   │                      #   S12: summary_report renders the C1 block + regenerates FRESH (ADR-0037);
│   │   │   │                      #   S13: render_prescription() + generate_prescription_document() (DOCTOR-6, ADR-0039)
│   │   │   ├── llm_client.py     # call_module() — assigned bucket → fallback; S17 (ADR-0041): logs EVERY
│   │   │   │                      #   attempt, 429/quota cooldown (60s/15min, fail-open), reset_cooldowns()
│   │   │   ├── intake.py         # NEW: M3 extract (10-field summary_fields; bilingual value_en/value_bn since S9,
│   │   │   │                      #   ADR-0033) → M4 summary → M6 gaps
│   │   │   ├── followup.py       # NEW: M7 question gen (Groq; no repeats; stored + spoken); S11:
│   │   │   │                      #   missing_summary_fields() + missing-override param (resume scope)
│   │   │   ├── profile_update.py # NEW: M8 re-extract + merge (human fields protected)
│   │   │   ├── completion.py     # NEW: M9 completeness (LOCAL)
│   │   │   ├── risk.py           # NEW: M10 classify + M11 XAI (rule forces critical; deterministic fallback);
│   │   │   │                      #   S11: override_assessment() + RiskOverrideBlocked (ADR-0035)
│   │   │   ├── suggestion.py     # S12: M10C — C1 "Possible Condition (AI Suggestion – Not a Diagnosis)"
│   │   │   │                      #   (ADR-0036: separate call from M10; disclaimer CONSTANTS embedded in the
│   │   │   │                      #   stored entities["suggested_condition"]; best-effort, never blocks submit)
│   │   │   ├── red_flags.py      # NEW: RED_FLAG_RULES (5 categories, bn/banglish/en) — LOCAL, no API
│   │   │   ├── report.py         # NEW: M12 local report assembly (Red Flags + disclaimer); S12: sections gain
│   │   │   │                      #   patient vitals + suggested_condition (ADR-0037)
│   │   │   └── audit.py          # NEW: audit() one-line append writer
│   │   └── db/
│   │       ├── database.py       # engine/session; run_migrations() + _legacy_stamp_revision() (mixed-state fix)
│   │       ├── models.py         # Utterance/Document (+visit_id/role/seq; utterance_id nullable since 0010) + Clinic/User/
│   │       │                      #   Patient/Visit + CaseProfile/ModuleEvent/FollowupQuestion/RiskAssessment/XaiExplanation/
│   │       │                      #   Report/DoctorReview/Feedback/AuditLog + Prescription (0010, ADR-0032)
│   │       ├── repository.py     # (existing) utterance/document session-grain writers (NO raw mutator)
│   │       ├── repository_visits.py # NEW: normalize_phone, get/create patient+visit, add_utterance, set_visit_status
│   │       └── seed.py           # S13: seed_demo_letterhead() — idempotent, fills NULL letterhead columns at startup
│   └── tests/                    # 6 existing suites + test_migration_0003 · test_routes_visits · test_intake ·
│                                  #   test_followup_loop · test_risk · test_staff_routes · test_report_review ·
│                                  #   test_routes_static (entry points + legacy isolation) ·
│                                  #   test_migration_0010 (visit-grain docs + prescriptions) ·
│                                  #   test_visit_documents (transcript verbatim + summary report) ·
│                                  #   test_bilingual_fields (value_en/value_bn + legacy back-compat) ·
│                                  #   test_resume_loop (KIOSK-7 scope=fields, S11) ·
│                                  #   test_risk_override (MEDIC-3 human row + red-flag guard, S11) ·
│                                  #   test_suggested_condition (C1 M10C + edit path + disclaimer, S12) ·
│                                  #   test_medic_summary (vitals PATCH + docx freshness, S12) ·
│                                  #   test_prescription_context (DOCTOR-4/5 letterhead prefill + seed, S13) ·
│                                  #   test_prescription_docx (DOCTOR-6 save row + .docx + Diagnosis-never-AI, S13) ·
│                                  #   conftest.py (S17: autouse LLM-cooldown reset) ·
│                                  #   test_llm_client (S17: per-attempt logging + cooldown switching, ADR-0041)  (156 total)
├── frontend/                     # patient side (served at /)
│   ├── index.html                # NEW (S9): landing page linking the 4 entry points (ADR-0031)
│   ├── kiosk.html · kiosk.js     # patient kiosk (at /kiosk.html): phone→OTP (auto-advance/Backspace/paste, S10
│   │                              #   KIOSK-1)→voice chat (per-bubble 🔊 icons + no-bn-voice hint banner, S10
│   │                              #   KIOSK-2/3)→summary (S11: per-field cards KIOSK-5, bilingual values KIOSK-6,
│   │                              #   raw .docx download KIOSK-4, resume voice dock + progress chip KIOSK-7)
│   │                              #   →submit→auto-logout
├── frontend_legacy/              # OLD Module-1 transcript app, isolated (served at /legacy/ — ADR-0031)
│   ├── index.html · app.js · styles.css   # unchanged behavior; asset refs made relative
├── frontend_shared/              # NEW: shared portal assets (mounted at /shared)
│   ├── shared.css                # clinical-blue design system (ADR-0029) + Noto Sans Bengali
│   ├── shared.js                 # TIER_LABELS (only place codes→labels), TIER_BANDS/tierBand (C2, display-only),
│   │                              #   fieldValue() (bilingual value_bn/value_en + {value} legacy), EN/BN helper, api()/showError()
│   ├── staff.js                  # queue render, phone lookup, verbatim panel, 10 editable field cards; S11:
│   │                              #   fully bilingual (labels+icons via t(), values via fieldValue(),
│   │                              #   staffLanguageRefresh() hook) — raw text re-rendered, never translated;
│   │                              #   S12: renderConditionCard() (C1 — portals opt in via #condition-card mount;
│   │                              #   the kiosk never has one)
│   └── tts.js                    # speak() via speechSynthesis bn-BD (Step A1); text stays the fallback
├── frontend_medic/index.html     # NEW medic portal (at /medic/): login→queue→verbatim+fields→Assign & Forward;
│                                  #   S11: EN/বাংলা toggle (MEDIC-1), ↻ Refresh Queue (MEDIC-5), risk panel
│                                  #   with C2 bands + override control (MEDIC-3); S12: #condition-card mount
│                                  #   (MEDIC-4) + post-referral summary screen with weight inline-edit +
│                                  #   summary_report .docx download (MEDIC-6/7)
└── frontend_doctor/index.html    # NEW doctor portal (at /doctor/): login→queue→risk/red-flag/XAI panel→Override/Accept;
                                   #   S12: fully bilingual (renderSafety() from state), ↻ Queue removed (DOCTOR-1/2),
                                   #   print CSS + responsive nav (DOCTOR-7 base)
```

REMOVED in Session 4 (browser-only): `services/stt/**`, `api/routes_stt.py`, the per-provider
requirements files, the STT config/.env block. (Still gone.)

Run from the project root. App: `python -m uvicorn backend.app.main:app --reload --port 8001`
(use the venv's Python). Tests: `pytest backend/tests/` (**156 passing**). Schema is Alembic-managed
and migrates at startup — never delete the DB. Entry points: `/` (landing), `/kiosk.html`,
`/medic/`, `/doctor/`, `/legacy/`.

---

## Planned structure (final locked stack — built incrementally via the build plan)

> This is the target layout the Phase A–I build plan grows the repo into. It EXTENDS the
> current structure (same FastAPI + SQLite + plain-HTML stack — ADR-0025); it is not a rewrite.
> Each module gets its own small service file; the patient pipeline is orchestrated in one
> place; the doctor dashboard is a second static page. Build it folder-by-folder, with the
> human's "go" each step. Treat anything not yet on disk as TBD.

```
voice-medical-prescreener/
├── backend/
│   ├── app/
│   │   ├── main.py                     # adds the patient-flow + report + dashboard routers
│   │   ├── core/
│   │   │   ├── config.py               # + per-module model/provider settings (ADR-0026), TTS lang
│   │   │   └── llm_providers.py        # provider registry: Gemini Flash / Flash-Lite / Groq / OpenRouter (base_url+model+key, fallback order)
│   │   ├── api/
│   │   │   ├── routes_transcripts.py   # (existing) raw + correct + docs
│   │   │   ├── routes_documents.py     # (existing) list + download
│   │   │   ├── routes_intake.py        # NEW: POST /api/intake/text → runs M2→M3→M4→M6, returns summary + gaps
│   │   │   ├── routes_followup.py      # NEW: POST /api/followup/next (M7 question) · POST /api/followup/answer (M8 + M9 loop check)
│   │   │   ├── routes_report.py        # NEW: GET /api/report/{case_id} (M10 risk + red-flags, M11 XAI, M12 report; PDF later)
│   │   │   └── routes_dashboard.py     # NEW: doctor-facing list/detail/override (M14)
│   │   ├── services/
│   │   │   ├── correction/             # (existing) Corrector ABC + OpenAICompatibleCorrector  → reused as M2
│   │   │   ├── llm_client.py           # NEW: thin call(provider_key, prompt) wrapper w/ automatic fallback (uses llm_providers)
│   │   │   ├── extraction.py           # NEW M3: normalized text → structured entities (Gemini Flash-Lite)
│   │   │   ├── summary.py              # NEW M4: entities → 2–4 sentence chief-complaint summary (Gemini Flash)
│   │   │   ├── missing_info.py         # NEW M6: present-vs-missing checklist (fed directly by M4 — no emergency branch)
│   │   │   ├── followup.py             # NEW M7: gaps → prioritized questions (Groq); served as text + spoken via browser TTS
│   │   │   ├── profile_update.py       # NEW M8: re-run answers through M2/M3, merge into the case profile
│   │   │   ├── completion.py           # NEW M9: completeness score + loop-back decision (LOCAL / NO-API)
│   │   │   ├── risk.py                 # NEW M10: Low/Med/High/Critical + RULE-BASED RED-FLAG CHECK → forces Critical (ADR-0024)
│   │   │   ├── red_flags.py            # NEW: the red-flag phrase/rule list used by risk.py (chest pain, stroke signs, etc.)
│   │   │   ├── xai.py                  # NEW M11: plain-language reason for the risk level (Gemini Flash)
│   │   │   ├── report.py               # NEW M12: assemble full report incl. a Red Flags section (no diagnosis); PDF writer later
│   │   │   └── documents/              # (existing) DocxWriter + storage; PDF writer slots in behind the format seam
│   │   ├── pipeline/
│   │   │   └── orchestrator.py         # NEW: runs the patient journey M1→M2→M3→M4→M6→(M7→M8→M9 loop)→M10→M11→M12 (M13 store)
│   │   ├── schemas/
│   │   │   ├── transcript.py / document.py   # (existing)
│   │   │   ├── case.py                 # NEW: CaseProfile, Entities, Gaps, Question, Answer
│   │   │   └── report.py               # NEW: RiskResult (incl. red_flags[]), XAIReason, ClinicalReport
│   │   └── db/
│   │       ├── models.py               # + Case/Profile/Report/AuditLog tables (M13) via NEW Alembic revisions (never edit old ones)
│   │       └── migrations/versions/    # 0003+ add the new tables (ADR-0022 rule: new revision per schema change)
│   └── tests/                          # + test_extraction / test_risk_red_flags (TC-R1) / test_followup_loop / test_api_fallback / test_flow_m4_m6
├── frontend/                           # patient UI (Mintlify), plain HTML/JS — ADR-0025
│   ├── index.html                      # + TTS test button (Phase A), later the live follow-up Q&A view
│   ├── app.js                          # + speak(text) via window.speechSynthesis (bn-BD); voice-only answer capture
│   ├── tts.js                          # NEW (optional split): SpeechSynthesis helper + Bangla-voice selection
│   └── styles.css                      # (existing tokens)
├── frontend_doctor/                    # NEW: doctor dashboard (second static page; M14)
│   ├── index.html                      # report view: summary, risk + red flags, XAI, override/annotate
│   └── dashboard.js                    # fetches /api/dashboard + /api/report/{id}
├── requirements.txt                    # single cross-platform list (no new heavy deps for TTS — browser-native)
├── .env.example                        # + per-provider key names (GEMINI_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY) — names only
└── docker/                             # OPTIONAL Phase I: single Dockerfile + one compose file (one service — NOT microservices)
```

---

## Important file rules
- **Never commit secrets.** API keys live in a `.env` file that is gitignored.
  `.env.example` (committed) just lists the key *names*.
- **Raw vs corrected** must be obvious in both the code and the data layout
  (separate fields/files), per constitution rule #1.
- **One service file per module**, called through `pipeline/orchestrator.py`; keep each file
  small and reviewable (CLAUDE.md). LLM calls go through `llm_client.py` so the per-module
  provider + fallback (ADR-0026) is configured in ONE place, not scattered.
- **Schema changes = a NEW Alembic revision** (0003, 0004, …). Never edit an applied revision
  and never delete the DB (ADR-0022).
- **The red-flag check lives in `risk.py`/`red_flags.py` (Module 10)** — there is no separate
  emergency module/route/node anymore (ADR-0024).
