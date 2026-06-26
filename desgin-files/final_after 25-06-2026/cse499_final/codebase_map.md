# codebase_map.md — Where Everything Lives

> A living map of the repo so Claude (and you) can find things without
> re-exploring the whole project each session. Update it whenever you add or move
> a folder/file. Keep each note to one line.

**Last updated:** 2026-06-25 (Session 7 — architect planning lock; planned structure rewritten,
real structure unchanged from Session 6)

---

## Current structure (real, today)

> Unchanged since Session 6 — Session 7 was planning only (no code written).

```
voice-medical-prescreener/
├── CLAUDE.md                     # lean hub; includes the Frontend/Transcript-UI rules + voice rules
├── DESIGN-mintlify.md            # frontend design system the UI follows
├── INSTALL.md                    # install + run guide (browser-only Module 1)
├── requirements.txt              # CORE deps (FastAPI, uvicorn, pydantic-settings, SQLAlchemy, alembic, openai, python-docx, pytest)
├── .gitignore                    # ignores .env, .venv/, *.db, data/ (incl. generated docs), audio/, models/
├── .venv/                        # local virtualenv (gitignored)
├── .claude/launch.json           # preview dev-server configs (uvicorn; PORT 8001): Windows + backend-linux (.venv/bin/python)
├── agent_docs/                   # the project's shared brain (living docs)
│   └── ... (constitution, milestone_log, current_task, changelog, test_log,
│           decisions, codebase_map, session_protocol)  + update_system_flowchart.md (TikZ)
├── backend/                      # FastAPI app
│   ├── .env / .env.example       # config (gitignored real / committed template): Gemini keys + STT_PROVIDER, DATABASE_URL, DOCUMENT_OUTPUT_PATH
│   ├── alembic.ini               # Alembic config (script_location=%(here)s/migrations; URL from app settings)
│   ├── migrations/               # Alembic env.py (URL from settings, render_as_batch) + script.py.mako
│   │   └── versions/             #   0001_baseline (orig schema) · 0002_add_stt_provider_and_doc_kind
│   ├── prescreener.db            # SQLite, created/migrated at runtime (gitignored); utterances + documents + alembic_version
│   ├── data/documents/           # generated .docx files (gitignored); path via documents_dir (env DOCUMENT_OUTPUT_PATH)
│   ├── data/prescreener.db.pre-alembic.bak  # one-off pre-migration backup (gitignored)
│   ├── app/
│   │   ├── main.py               # FastAPI entry: lifespan init_db; registers transcripts + documents routers; serves frontend
│   │   ├── core/config.py        # pydantic-settings: stt_provider + correction (Gemini) + db + documents_dir (DOCUMENT_OUTPUT_PATH alias)
│   │   ├── api/routes_transcripts.py  # POST /api/transcripts (store raw) · GET list · GET /{id} (detail+doc links) ·
│   │   │                          #   POST /{id}/documents/{raw,corrected} · POST /api/correct (by id; best-effort corrected .docx)
│   │   ├── api/routes_documents.py    # GET /api/documents (list), GET /api/documents/{id}/download (FileResponse, any kind)
│   │   ├── schemas/transcript.py # StoreRawRequest / CorrectRequest / TranscriptOut / TranscriptDetailOut (raw+corrected docs)
│   │   ├── schemas/document.py   # DocumentOut (incl. kind + computed download_url)
│   │   ├── services/correction/  # Corrector ABC + OpenAICompatibleCorrector (Gemini)  [STT layer REMOVED]
│   │   ├── services/documents/   # DocumentWriter ABC (render(utterance,*,kind)) + DocxWriter (raw/corrected single-kind, Bangla font);
│   │   │                          #   storage.py (FS, swappable); __init__ build_writer() + generate_session_document(kind=…)
│   │   └── db/
│   │       ├── database.py        # engine/session; run_migrations() (auto stamp+upgrade) called by init_db(); get_db()
│   │       ├── models.py          # Utterance (raw write-once + corrected + stt_provider) + Document (UUID PK, FK, kind)
│   │       └── repository.py      # create_raw/set_correction/get_by_id (NO raw mutator) + create/get/list/get_latest_document
│   └── tests/
│       ├── test_raw_immutable.py  # rule #1 guard (3 tests)
│       ├── test_corrector.py      # corrector guards, offline (4 tests)
│       ├── test_docx_writer.py    # raw/corrected single-kind render + rule-#1-verbatim guard, offline (5 tests)
│       ├── test_documents_repo.py # repo (kind) + generate orchestrator + get_latest_document, in-memory DB + temp storage (4 tests)
│       ├── test_migration.py      # Alembic: legacy DB keeps rows + fresh DB full schema, temp file DBs (2 tests)
│       └── test_routes_documents.py # full two-doc workflow via TestClient (StaticPool, fake corrector, temp storage) (2 tests)
└── frontend/                     # plain HTML/JS (served by FastAPI at /), Mintlify-styled
    ├── index.html                # Start/Stop + timer; RAW/CORRECTED/Manual panels + per-panel Download .docx; Saved-documents panel
    ├── app.js                    # Web Speech API; save raw + raw .docx on Stop; correct → corrected .docx; download buttons; status/errors
    └── styles.css                # DESIGN-mintlify tokens; fixed-height scrollable panels; pill buttons; .doc-link; .download-btn
```

REMOVED in Session 4 (browser-only simplification): `services/stt/**`,
`api/routes_stt.py`, `tests/test_stt_registry.py`, `requirements-{whisper,
banglaspeech,qwen}.txt`, and the STT config/.env block.

Run from the project root. App: `python -m uvicorn backend.app.main:app --reload --port 8001`
(use the venv's Python). Tests: `pytest backend/tests/` (**19 passing**). Schema is managed
by Alembic and migrates automatically at startup — never delete the DB.

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
