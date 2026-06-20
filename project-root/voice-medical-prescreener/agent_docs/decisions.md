# decisions.md — Decision Record (ADR style)

> A short, dated record of real design choices: what we chose, why, and what we
> rejected. This stops the same decision being silently re-opened weeks later,
> and gives the thesis a ready-made trail of justified choices.
>
> Template:
> ```
> ## ADR-NNNN — YYYY-MM-DD — <title>
> - Decision: <what we will do>
> - Why: <the reason>
> - Rejected: <the main alternative(s) and why not>
> - Status: Accepted | Superseded by ADR-XXXX
> ```

---

## ADR-0001 — 2026-06-18 — Use a markdown project-memory system
- Decision: Maintain a lean `CLAUDE.md` at the project root plus an `agent_docs/`
  folder of living docs (constitution, milestone_log, current_task, changelog,
  test_log, decisions, codebase_map, session_protocol).
- Why: Claude Code starts each session with a blank memory; it auto-reads
  `CLAUDE.md`. Pointing from a short `CLAUDE.md` to detailed docs gives continuity
  across sessions without bloating context. Keeps a big 15-module project organized.
- Rejected: Keeping everything in chat (forgotten each session); one huge file
  (Claude follows instructions worse when the file is very long).
- Status: Accepted

## ADR-0002 — 2026-06-18 — STT: faster-whisper (CPU int8) as backbone; Web Speech API for quick start; keep STT swappable
- Decision: Robust path = faster-whisper (CTranslate2) running int8 on CPU.
  Quick-start path = the browser Web Speech API. Put STT behind a swappable
  interface so we can switch offline/online backends.
- Why: faster-whisper is fast and accurate enough on CPU and runs the same on
  Windows and Linux (no NVIDIA needed). Web Speech API gives an instant free live
  Bangla demo with zero setup. A swappable interface protects us if one path fails.
- Rejected: Vosk (no maintained Bangla model today); original OpenAI Whisper on
  CPU (too slow); CTranslate2 on AMD GPU (no ROCm support — CUDA/CPU only).
- Status: Accepted

## ADR-0003 — 2026-06-18 — Text correction via a swappable free LLM (Gemini Flash primary)
- Decision: Do downstream text correction with a free LLM behind a `Corrector`
  interface. Primary = Google Gemini Flash; fallback = Groq, then OpenRouter.
- Why: Free LLMs handle Bangla/Banglish correction well, including code-switching
  that dedicated transliteration models struggle with. All are OpenAI-compatible,
  so swapping providers is easy. Fallback protects against free rate limits.
- Rejected: Hard-coding a single provider (free limits and availability change
  often). Sending real patient data to any of these (privacy — synthetic only).
- Status: Accepted

## ADR-0004 — 2026-06-18 — Backend = FastAPI + WebSocket; browser AudioWorklet capture
- Decision: Backend is FastAPI with native WebSockets. The browser captures mic
  audio as 16 kHz mono PCM via the Web Audio API / AudioWorklet and streams it
  over a WebSocket.
- Why: FastAPI's async model handles live audio streams cleanly and is the
  community standard for Whisper streaming servers. A clean WebSocket + REST API
  can be reused later by the planned mobile app.
- Rejected: Flask-SocketIO (less clean async); MediaRecorder-only capture (needs
  extra server-side decoding).
- Status: Accepted

## ADR-0005 — 2026-06-18 — Raw transcript is immutable (two-stage capture → normalize)
- Decision: The raw ASR output is stored unchanged in its own field forever. All
  cleaning, correction, and transliteration produce *separate* fields. Plan to
  enforce this later with a guard (a Claude Code PreToolUse hook and/or a test
  that fails if raw is mutated) — not just a written rule.
- Why: This is the project's core clinical/ethical rule (constitution #1): we must
  always be able to show exactly what the patient said.
- Rejected: Correcting text "in place" (would destroy the original record).
- Status: Accepted

## ADR-0006 — 2026-06-18 — CPU-only by default; defer AMD GPU acceleration
- Decision: Build for CPU. Treat any AMD-GPU speedup (e.g. whisper.cpp + Vulkan)
  as an optional experiment, never a dependency.
- Why: No NVIDIA GPU. AMD-GPU ML on the RX 570 (old) and integrated Vega is
  unreliable (silent fallback to CPU is common). Chasing it would waste time.
- Rejected: Building around ROCm/Vulkan GPU acceleration up front.
- Status: Accepted

## ADR-0007 — 2026-06-18 — One cross-platform requirements.txt + venv
- Decision: Use a single `requirements.txt` and a Python venv that works on both
  Windows and Arch Linux. Isolate any hard-to-install package (e.g. fairseq-based
  IndicXlit transliteration) as an *optional* extra so it never blocks core setup.
- Why: Keeps setup identical on both machines and avoids "works on one OS only".
- Rejected: Separate dependency files per OS (drift and confusion).
- Status: Accepted

## ADR-0009 — 2026-06-19 — Build the real backend/ + frontend/ foundation (no throwaway demo folder)
- Decision: Instead of a disposable `phase0_webspeech_demo/` folder, build the
  Phase 0 demo as the first vertical slice of the real app structure:
  `backend/app/{core,api,schemas,services,db}` + `frontend/`. One FastAPI server
  serves the static frontend AND the API.
- Why: The human asked for a foundation that scales into the full CSE499 app
  without later restructuring. One server = one run command, no CORS, clean growth.
- Rejected: A siloed phase0 folder (would need migration later); separate
  frontend/backend servers (adds CORS + two run commands for a tiny demo).
- Status: Accepted

## ADR-0010 — 2026-06-19 — Persistence = SQLite via a repository layer; raw is write-once
- Decision: Persist utterances in SQLite from Phase 0, behind a small repository
  (`create_raw`, `set_correction`, `get_recent`). `Utterance.raw_text` is written
  once; corrections go in a separate `corrected_text` column. The repository has
  NO raw-mutating function, and a test (`test_raw_immutable.py`) guards it.
  `database_url` is config-driven so SQLite → Postgres later needs no code change.
- Why: Foundation for the future EHR (Module 13); enforces constitution rule #1 in
  code, not just prose (per ADR-0005's intent).
- Rejected: Flat JSON files (needs migration later); no persistence (loses the
  ~50-sample collection goal).
- Status: Accepted

## ADR-0011 — 2026-06-19 — Correction uses the OpenAI-compatible client (Gemini now, others later)
- Decision: Implement correction behind a `Corrector` ABC, with one
  `OpenAICompatibleCorrector` that uses the `openai` SDK pointed at Gemini's
  OpenAI-compatible base URL (config-driven provider/model/base_url/key). Swapping
  to Groq/OpenRouter later = change config only.
- Why: All three providers are OpenAI-compatible, so one client + a base_url swap
  satisfies ADR-0003's swappability with the least code.
- Rejected: The dedicated `google-genai` SDK (would need a different client per
  provider); hardcoding a single provider.
- Status: Accepted

## ADR-0012 — 2026-06-19 — Pin SQLAlchemy >= 2.0.51 (Python 3.14 compatibility)
- Decision: Require `SQLAlchemy==2.0.51` (not 2.0.36).
- Why: 2.0.36 crashes on Python 3.14.4 with a typing-union `__getitem__` error when
  declaring `Mapped[str | None]` columns. 2.0.51 fixes it; verified by passing tests.
- Rejected: Avoiding `X | None` annotations (fights the modern style and still risky
  on 3.14); pinning an older Python (the Windows dev machine is on 3.14.4).
- Status: Accepted

## ADR-0013 — 2026-06-19 — POST /api/correct persists RAW before correcting
- Decision: The `/api/correct` endpoint stores the raw text (write-once) BEFORE
  calling the LLM. If the LLM call fails, it returns HTTP 502 but the raw record is
  kept (with `corrected_text` null). Misconfiguration (missing key / bad provider)
  fails fast with HTTP 500 before anything is stored.
- Why: Constitution rule #1 — the patient's words must never be lost, even when the
  (free, rate-limited, network-dependent) correction step fails.
- Rejected: Correcting first then storing both (loses raw if the call fails);
  silently returning 200 with no correction (hides failures from the UI).
- Status: Accepted

## ADR-0014 — 2026-06-19 — Live transcription is browser-side; backend hit only on "Correct"
- Decision: In Phase 0, live STT runs entirely in the browser (Web Speech API,
  Chrome/Edge, `bn-BD`) talking to Google's cloud. Our FastAPI backend is invoked
  only when the user clicks "Correct" (one Gemini request per click). Talking is
  effectively unlimited; the real cap is the Gemini free tier (~15 req/min,
  ~1,500/day on flash).
- Why: Matches the Phase 0 goal of a zero-ML-setup demo and the build plan's
  quick-start path. Keeps the loop simple and the backend stateless during speech.
- Rejected: Streaming audio to the backend in Phase 0 (that is Phase 1 with
  faster-whisper over WebSocket, not needed for the demo).
- Status: Accepted (Phase 0 only; Phase 1 moves STT server-side)

## ADR-0015 — 2026-06-19 — Multi-provider STT behind a plugin layer; frontend switching
- Decision: Support 5 swappable STT providers (browser_webspeech, groq_whisper,
  local_whisper, banglaspeech2text, qwen_asr) behind an `STTProvider` ABC + registry
  in `backend/app/services/stt/`, chosen from a frontend dropdown. Two data paths:
  browser providers transcribe client-side (live); server providers record audio
  (MediaRecorder, ≤5 min) and upload to `POST /api/transcribe`.
- Why: The human wants provider flexibility from the start; the plugin layer means
  adding an engine is one new class. Mirrors the existing Corrector pattern (ADR-0003).
- Rejected: Browser-only STT; true live streaming for all engines (WebSocket+VAD
  chunking — too complex/slow on CPU for Phase 0).
- Status: Accepted

## ADR-0016 — 2026-06-19 — Drop the banglaspeech2text package; use transformers directly
- Decision: Do NOT install the `banglaspeech2text` PyPI package. Run the same models
  (`shhossain/whisper-*-bn`) via `transformers` instead.
- Why: The package is unmaintained and pins `huggingface-hub==0.11.1`, which conflicts
  with faster-whisper and breaks installation. transformers shares a modern
  huggingface-hub with the other engines — same models, no dependency hell.
- Rejected: Pinning old huggingface-hub (breaks faster-whisper); separate venv just
  for banglaspeech (unnecessary once we drop the package).
- Status: Accepted

## ADR-0017 — 2026-06-19 — Per-provider optional requirements files; rich provider health
- Decision: Core install (requirements.txt) = Browser + Groq + Gemini. Each local
  engine has its own optional file: requirements-whisper.txt,
  requirements-banglaspeech.txt, requirements-qwen.txt (torch left unpinned so pip
  picks a Python-compatible build). Providers report installed/configured/ready +
  a status code (available | missing_api_key | missing_package | missing_model |
  unsupported_platform | error) surfaced in the dropdown, `GET /api/stt/providers`,
  and a startup log. Documented in INSTALL.md.
- Why: Avoid dependency conflicts and make "why is this disabled?" obvious. Keep the
  core light and cross-platform.
- Rejected: One monolithic requirements-local.txt (caused the conflict); disabling
  providers without explaining why.
- Status: Accepted

## ADR-0018 — 2026-06-19 — Persist raw at transcription; /api/correct works by utterance_id
- Decision: Raw is created at the transcription step (`/api/transcribe` for server
  providers, `/api/transcripts` for browser/manual), tagged with `stt_provider`.
  `/api/correct` takes `{utterance_id}` and only fills the separate corrected field.
- Why: Matches the immutable pipeline (one utterance flows through both stages) and
  keeps raw write-once (rule #1). Breaking change to the old `/api/correct {raw_text}`,
  acceptable in Phase 0; frontend updated in lockstep.
- Status: Accepted

## ADR-0019 — 2026-06-20 — Module 1 STT = browser Web Speech API only (remove multi-provider layer)
- Decision: Revert the 5-provider STT architecture. Module 1 uses ONLY the browser
  Web Speech API (Chrome/Edge, bn-BD). Delete the STT plugin/registry/health code,
  Groq/local/Qwen/BanglaSpeech providers, their requirements files, STT config, and
  python-multipart. Keep a clean seam (the `Utterance.stt_provider` string column)
  so providers can return in a later module.
- Why: The human judged the multi-provider system too much for Module 1; it added
  heavy, invasive dependencies (qwen-asr bumped fastapi/starlette) and complexity.
  Get the browser pipeline stable first.
- Rejected: Keeping all 5 providers; keeping the plugin layer "just in case"
  (dead code). Recreate the venv to restore a clean core instead.
- Status: Accepted (supersedes ADR-0015, ADR-0017 for now; those may be revisited
  when offline STT returns in a later module)

## ADR-0020 — 2026-06-20 — Continuous recording UX + Mintlify frontend + scrollable panels
- Decision: Recording is continuous: no max duration, append-only verbatim
  transcript, brief pauses keep going (restart recognition on `onend`), auto-stop
  only after ~10s of continuous silence or on user Stop. The frontend follows
  `DESIGN-mintlify.md` (Inter, black pill buttons, mint-green accent, 12px cards).
  The three transcript panels (Raw/Corrected/Manual) share one behavior:
  fixed-height, scrollable, stick-to-bottom auto-scroll that pauses when the user
  scrolls up and resumes at the bottom. Transcript text uses Inter + Noto Sans
  Bengali (NOT Geist Mono — mono breaks Bangla rendering).
- Why: Matches a real doctor–patient conversation; keeps long transcripts usable
  without breaking layout; gives the project a consistent, documented visual system.
- Rejected: 5-minute cap; clearing/replacing transcript on pause; Geist Mono for
  Bangla transcript content.
- Status: Accepted

## ADR-0008 — 2026-06-18 — Default Whisper model is small/base; upgrade to a Bangla fine-tune later
- Decision: Start with Whisper `small` (or `base` if we need a snappier live feel)
  for streaming on CPU. Upgrade to a Bangla-fine-tuned model (e.g.
  `tugstugi/whisper-medium` converted to CTranslate2) in Phase 2 if accuracy needs
  it and latency stays usable.
- Why: tiny/base/small run faster than real time on CPU; medium is near/below real
  time on a 6-core CPU. Accuracy is the real constraint, so we upgrade deliberately.
- Rejected: Starting with large-v3 (too slow on CPU, and poor on Bangla unless
  fine-tuned).
- Status: Accepted
