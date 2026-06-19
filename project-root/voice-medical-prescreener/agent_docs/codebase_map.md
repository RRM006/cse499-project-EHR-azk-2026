# codebase_map.md — Where Everything Lives

> A living map of the repo so Claude (and you) can find things without
> re-exploring the whole project each session. Update it whenever you add or move
> a folder/file. Keep each note to one line.

**Last updated:** 2026-06-19 (Session 3 — multi-provider STT layer + installs + INSTALL.md)

---

## Current structure (real, today)

```
voice-medical-prescreener/
├── CLAUDE.md                     # lean hub; Claude Code reads this every session
├── INSTALL.md                    # install guide: which file installs which provider, models, disk, time
├── requirements.txt              # CORE deps (Browser + Groq + Gemini); + python-multipart
├── requirements-whisper.txt      # OPTIONAL: Local Whisper (faster-whisper, no torch)
├── requirements-banglaspeech.txt # OPTIONAL: BanglaSpeech2Text (transformers + torch)
├── requirements-qwen.txt         # OPTIONAL: Qwen3-ASR (qwen-asr + onnxruntime + torch) — invasive
├── .gitignore                    # ignores .env, .venv/, *.db, data/, audio/, models/
├── .venv/                        # local virtualenv (gitignored)
├── .claude/launch.json           # dev-server config for the preview tool (uvicorn; Windows venv path)
├── agent_docs/                   # the project's shared brain (living docs) — unchanged set
│   └── ... (constitution, milestone_log, current_task, changelog, test_log,
│           decisions, codebase_map, session_protocol)
├── backend/                      # FastAPI app (foundation for the full app)
│   ├── .env / .env.example       # config (gitignored real / committed template): keys + STT settings
│   ├── prescreener.db            # SQLite, created at runtime (gitignored); has stt_provider column
│   ├── app/
│   │   ├── main.py               # FastAPI entry: lifespan init_db + STT health log; serves frontend
│   │   ├── core/config.py        # pydantic-settings: keys, STT provider + model settings
│   │   ├── api/
│   │   │   ├── routes_transcripts.py  # POST /api/transcripts (store raw), /api/correct (by id), GET list
│   │   │   └── routes_stt.py     # GET /api/stt/providers, POST /api/transcribe (audio upload)
│   │   ├── schemas/transcript.py # StoreRawRequest / CorrectRequest / TranscriptOut / ProviderOut
│   │   ├── services/
│   │   │   ├── correction/       # Corrector ABC + OpenAICompatibleCorrector (Gemini)
│   │   │   └── stt/              # STT provider plugin layer:
│   │   │       ├── base.py        #   STTProvider ABC + ProviderInfo (health) + status codes
│   │   │       ├── registry.py    #   list_providers() / get_provider(); add a class here = new provider
│   │   │       ├── audio.py       #   decode webm/opus -> 16k mono float32 (PyAV); for local engines
│   │   │       ├── browser_webspeech.py  # kind=browser (client-side)
│   │   │       ├── groq_whisper.py        # kind=server, cloud (openai SDK @ Groq)
│   │   │       ├── local_whisper.py       # kind=server, faster-whisper int8 CPU
│   │   │       ├── banglaspeech.py        # kind=server, shhossain/whisper-*-bn via transformers
│   │   │       └── qwen_asr.py            # kind=server, Qwen3-ASR-1.7B (local, CPU)
│   │   └── db/
│   │       ├── database.py / get_db()      # engine/session, init_db()
│   │       ├── models.py          # Utterance: raw_text (write-once) + corrected_text + stt_provider
│   │       └── repository.py      # create_raw(stt_provider=) / set_correction() / get_by_id — NO raw mutator
│   └── tests/
│       ├── test_raw_immutable.py  # rule #1 guard (3 tests)
│       ├── test_corrector.py      # corrector guards, offline (4 tests)
│       └── test_stt_registry.py   # provider listing + health logic, lazy-import safety (6 tests)
└── frontend/                     # plain HTML/JS (served by FastAPI at /)
    ├── index.html                # provider dropdown, Start/Stop+timer, RAW + CORRECTED panels, manual fallback
    ├── app.js                    # provider switching; browser=live vs server=record→upload; copy/clear; errors
    └── styles.css                # status badges, recording pill, spinner; raw=amber, corrected=green
```

Run from the project root. App: `python -m uvicorn backend.app.main:app --reload --port 8000`
(use the venv's Python). Tests: `pytest backend/tests/` (**13 passing**).
Core + all 3 optional local engines are installed on the Windows box; only the
human-driven live test of each provider on real speech remains. See INSTALL.md.

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
