# codebase_map.md — Where Everything Lives

> A living map of the repo so Claude (and you) can find things without
> re-exploring the whole project each session. Update it whenever you add or move
> a folder/file. Keep each note to one line.

**Last updated:** 2026-06-19 (Session 1 — scaffolding + backend skeleton added)

---

## Current structure (real, today)

```
voice-medical-prescreener/
├── CLAUDE.md                     # lean hub; Claude Code reads this every session
├── requirements.txt              # single cross-platform dep list (Py 3.14 needs SQLAlchemy>=2.0.51)
├── .gitignore                    # ignores .env, .venv/, *.db, data/, audio/, models/
├── .venv/                        # local virtualenv (gitignored)
├── agent_docs/                   # the project's shared brain (living docs)
│   ├── constitution.md           # stable rules + 15-module architecture
│   ├── milestone_log.md          # status of all 15 modules + roadmap phases
│   ├── current_task.md           # what we are doing right now (overwritten each session)
│   ├── changelog.md              # session-by-session history (newest first)
│   ├── test_log.md               # what was tested + results (WER, accuracy...)
│   ├── decisions.md              # dated design decisions (ADR style)
│   ├── codebase_map.md           # THIS file
│   └── session_protocol.md       # copy-paste prompts to start/end a session
└── backend/                      # FastAPI app (foundation for the full app)
    ├── .env                      # REAL config — gitignored, placeholder key (FILL IN)
    ├── .env.example              # committed template (key names only)
    ├── app/
    │   ├── core/config.py        # pydantic-settings: loads backend/.env
    │   └── db/
    │       ├── database.py        # SQLAlchemy engine/session, init_db(), get_db()
    │       ├── models.py          # Utterance: raw_text (write-once) + separate corrected_text
    │       └── repository.py      # create_raw() / set_correction() — NO raw mutator
    └── tests/test_raw_immutable.py  # guard for constitution rule #1 (3 tests, passing)
```

Not built yet: `backend/app/{api,schemas,services}`, `backend/app/main.py`,
`frontend/`. (See "Planned structure" below.) `backend/prescreener.db` is created
at runtime once the app runs (gitignored).

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
