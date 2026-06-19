# codebase_map.md — Where Everything Lives

> A living map of the repo so Claude (and you) can find things without
> re-exploring the whole project each session. Update it whenever you add or move
> a folder/file. Keep each note to one line.

**Last updated:** 2026-06-19 (Session 2 — correction service + API + frontend added)

---

## Current structure (real, today)

```
voice-medical-prescreener/
├── CLAUDE.md                     # lean hub; Claude Code reads this every session
├── requirements.txt              # single cross-platform dep list (Py 3.14 needs SQLAlchemy>=2.0.51)
├── .gitignore                    # ignores .env, .venv/, *.db, data/, audio/, models/
├── .venv/                        # local virtualenv (gitignored)
├── .claude/launch.json           # dev-server config for the preview tool (uvicorn; Windows venv path)
├── agent_docs/                   # the project's shared brain (living docs) — unchanged set
│   └── ... (constitution, milestone_log, current_task, changelog, test_log,
│           decisions, codebase_map, session_protocol)
├── backend/                      # FastAPI app (foundation for the full app)
│   ├── .env                      # REAL config — gitignored (FILL IN the GEMINI_API_KEY)
│   ├── .env.example              # committed template (key names only)
│   ├── prescreener.db            # SQLite, created at runtime (gitignored)
│   ├── app/
│   │   ├── main.py               # FastAPI entry: lifespan init_db, /health, serves frontend
│   │   ├── core/config.py        # pydantic-settings: loads backend/.env
│   │   ├── api/routes_transcripts.py  # POST /api/correct, GET /api/transcripts
│   │   ├── schemas/transcript.py # CorrectRequest / TranscriptOut (Pydantic)
│   │   ├── services/correction/
│   │   │   ├── base.py            # Corrector ABC
│   │   │   └── openai_compatible.py  # OpenAICompatibleCorrector + build_corrector() + __main__ live check
│   │   └── db/
│   │       ├── database.py        # engine/session, init_db(), get_db()
│   │       ├── models.py          # Utterance: raw_text (write-once) + separate corrected_text
│   │       └── repository.py      # create_raw() / set_correction() — NO raw mutator
│   └── tests/
│       ├── test_raw_immutable.py  # rule #1 guard (3 tests)
│       └── test_corrector.py      # corrector guards, offline (4 tests)
└── frontend/                     # plain HTML/JS (served by FastAPI at /)
    ├── index.html                # mic controls, RAW box, CORRECTED box, manual fallback, recent list
    ├── app.js                    # Web Speech API (bn-BD); interim grey / final verbatim; POST /api/correct
    └── styles.css                # two-column layout; raw=amber, corrected=green
```

Run from the project root. App: `python -m uvicorn backend.app.main:app --reload --port 8000`
(use the venv's Python). Tests: `pytest backend/tests/` (7 passing).
All 6 Phase-0 build files exist; only the human-driven live test (step 6) remains.

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
