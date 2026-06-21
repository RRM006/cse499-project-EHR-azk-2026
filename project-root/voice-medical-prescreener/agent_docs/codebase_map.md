# codebase_map.md — Where Everything Lives

> A living map of the repo so Claude (and you) can find things without
> re-exploring the whole project each session. Update it whenever you add or move
> a folder/file. Keep each note to one line.

**Last updated:** 2026-06-21 (Session 6 — two separate raw/corrected .docx + Alembic migration)

---

## Current structure (real, today)

```
voice-medical-prescreener/
├── CLAUDE.md                     # lean hub; includes the Frontend/Transcript-UI rules
├── DESIGN-mintlify.md            # frontend design system the UI follows
├── INSTALL.md                    # install + run guide (browser-only Module 1)
├── requirements.txt              # CORE deps (FastAPI, uvicorn, pydantic-settings, SQLAlchemy, alembic, openai, python-docx, pytest)
├── .gitignore                    # ignores .env, .venv/, *.db, data/ (incl. generated docs), audio/, models/
├── .venv/                        # local virtualenv (gitignored)
├── .claude/launch.json           # preview dev-server configs (uvicorn; PORT 8001): Windows + backend-linux (.venv/bin/python)
├── agent_docs/                   # the project's shared brain (living docs)
│   └── ... (constitution, milestone_log, current_task, changelog, test_log,
│           decisions, codebase_map, session_protocol)
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

## Planned structure (what we expect to add — not built yet)

> This is a sketch to guide us. We will confirm the real layout with the human
> before creating it. Treat everything below as TBD.

```
voice-medical-prescreener/
├── phase0_webspeech_demo/        # Phase 0: browser Web Speech API + LLM correction
│   ├── index.html                #   the demo page (mic + raw box + corrected box)
│   └── ...                        #   (minimal backend for the LLM call, TBD)
│
├── backend/                      # Phase 1+: FastAPI app
│   ├── main.py                   #   FastAPI entry point (TBD)
│   ├── stt/                      #   speech-to-text module (swappable backends)
│   ├── correction/               #   LLM correction module (swappable providers)
│   └── ...
│
├── frontend/                     # web UI (plain HTML/JS first, React later)
├── data/                         # sample audio + ground-truth transcripts (synthetic/consented)
├── tests/                        # automated tests (incl. the raw-immutability guard)
├── requirements.txt              # single cross-platform dependency list
├── .env.example                  # shows which API keys are needed (no real keys!)
└── .gitignore                    # must ignore .env, .venv, models, audio data
```

---

## Important file rules
- **Never commit secrets.** API keys live in a `.env` file that is gitignored.
  `.env.example` (committed) just lists the key *names*.
- **Raw vs corrected** must be obvious in both the code and the data layout
  (separate fields/files), per constitution rule #1.
