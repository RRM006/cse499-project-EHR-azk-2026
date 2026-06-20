# codebase_map.md — Where Everything Lives

> A living map of the repo so Claude (and you) can find things without
> re-exploring the whole project each session. Update it whenever you add or move
> a folder/file. Keep each note to one line.

**Last updated:** 2026-06-19 (Session 3 — multi-provider STT layer + installs + INSTALL.md)

---

## Current structure (real, today)

```
voice-medical-prescreener/
├── CLAUDE.md                     # lean hub; includes the Frontend/Transcript-UI rules
├── DESIGN-mintlify.md            # frontend design system the UI follows
├── INSTALL.md                    # install + run guide (browser-only Module 1)
├── requirements.txt              # CORE deps only (FastAPI, uvicorn, pydantic-settings, SQLAlchemy, openai, pytest)
├── .gitignore                    # ignores .env, .venv/, *.db, data/, audio/, models/
├── .venv/                        # local virtualenv (gitignored)
├── .claude/launch.json           # preview dev-server config (uvicorn; venv python; PORT 8001)
├── agent_docs/                   # the project's shared brain (living docs)
│   └── ... (constitution, milestone_log, current_task, changelog, test_log,
│           decisions, codebase_map, session_protocol)
├── backend/                      # FastAPI app
│   ├── .env / .env.example       # config (gitignored real / committed template): Gemini correction keys
│   ├── prescreener.db            # SQLite, created at runtime (gitignored); has stt_provider column
│   ├── app/
│   │   ├── main.py               # FastAPI entry: lifespan init_db; serves frontend (+ placeholder)
│   │   ├── core/config.py        # pydantic-settings: correction (Gemini) + db settings
│   │   ├── api/routes_transcripts.py  # POST /api/transcripts (store raw), /api/correct (by id), GET list
│   │   ├── schemas/transcript.py # StoreRawRequest / CorrectRequest / TranscriptOut
│   │   ├── services/correction/  # Corrector ABC + OpenAICompatibleCorrector (Gemini)  [STT layer REMOVED]
│   │   └── db/
│   │       ├── database.py        # engine/session, init_db(), get_db()
│   │       ├── models.py          # Utterance: raw_text (write-once) + corrected_text + stt_provider
│   │       └── repository.py      # create_raw(stt_provider=) / set_correction() / get_by_id — NO raw mutator
│   └── tests/
│       ├── test_raw_immutable.py  # rule #1 guard (3 tests)
│       └── test_corrector.py      # corrector guards, offline (4 tests)
└── frontend/                     # plain HTML/JS (served by FastAPI at /), Mintlify-styled
    ├── index.html                # Start/Stop + ● Recording + count-up timer; RAW / CORRECTED / Manual panels
    ├── app.js                    # Web Speech API continuous recording; ~10s-silence auto-stop; stick-to-bottom auto-scroll
    └── styles.css                # DESIGN-mintlify tokens; fixed-height scrollable panels; pill buttons
```

REMOVED in Session 4 (browser-only simplification): `services/stt/**`,
`api/routes_stt.py`, `tests/test_stt_registry.py`, `requirements-{whisper,
banglaspeech,qwen}.txt`, and the STT config/.env block.

Run from the project root. App: `python -m uvicorn backend.app.main:app --reload --port 8001`
(use the venv's Python). Tests: `pytest backend/tests/` (**7 passing**).

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
