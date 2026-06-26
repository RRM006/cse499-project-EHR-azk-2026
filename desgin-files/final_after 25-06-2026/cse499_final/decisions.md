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
- Status: Accepted (refined per-module by ADR-0026)

## ADR-0004 — 2026-06-18 — Backend = FastAPI + WebSocket; browser AudioWorklet capture
- Decision: Backend is FastAPI with native WebSockets. The browser captures mic
  audio as 16 kHz mono PCM via the Web Audio API / AudioWorklet and streams it
  over a WebSocket.
- Why: FastAPI's async model handles live audio streams cleanly and is the
  community standard for Whisper streaming servers. A clean WebSocket + REST API
  can be reused later by the planned mobile app.
- Rejected: Flask-SocketIO (less clean async); MediaRecorder-only capture (needs
  extra server-side decoding).
- Status: Accepted (WebSocket capture is Phase 1; Phase 0 STT is browser-side, ADR-0014)

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
  effectively unlimited; the real cap is the Gemini free tier.
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
- Status: Accepted — then superseded by ADR-0019

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
- Status: Accepted — STT installs mooted by ADR-0019 (may return later)

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

## ADR-0021 — 2026-06-21 — Session .docx is a derived export; DB stays source of truth (python-docx)
- Decision: On a successful `/api/correct`, auto-generate a Word `.docx` for the
  completed session. The DB remains the single source of truth; the `.docx` (and
  later PDF) is a DERIVED, regenerable artifact, never the system of record. Generate
  with `python-docx` (pure Python). Store files on the local filesystem behind a
  swappable `DocumentStorage` interface, under a configurable `documents_dir`
  (env-overridable, default `backend/data/documents/`, no hardcoded paths), named by
  a UUID. Record metadata in a new `Document` table (UUID PK, FK → Utterance, format,
  filename, rel_path, created_at). Generation is BEST-EFFORT: a docx failure logs but
  never fails the correction response. Document grain = one Utterance/session.
- Why: Treating Word as a presentation/export format (not the record) preserves rule
  #1 — the verbatim raw stays canonical in the DB and the file is always regenerable —
  and avoids lossy Bangla round-tripping through a zip-of-XML. python-docx needs no
  Word/LibreOffice/external binary, so it satisfies the one-requirements.txt
  cross-platform (Windows + Arch), CPU-only, free/OSS constraints. The storage seam +
  `format` seam + `build_writer()` registry mirror the existing Corrector pattern and
  leave clean paths for PDF, cloud (S3/MinIO), auth, and Patient/Visit grouping later.
- Rejected: DOCX as the source of truth (fragile, unqueryable, encoding risk);
  HTML→DOCX via pandoc or LibreOffice/Word COM (external binary / Windows-only —
  breaks cross-platform); generating during live transcription (raw still changing,
  pointless churn); building Patient/Visit tables now (over-engineering Phase 0);
  shipping PDF in this step (deferred behind the format seam).
- Status: Accepted

## ADR-0022 — 2026-06-21 — Alembic for schema migrations; auto-run at startup with baseline-stamp for legacy DBs
- Decision: Manage the DB schema with Alembic instead of `Base.metadata.create_all`.
  Scaffolding lives under `backend/` (`alembic.ini` with `script_location=%(here)s/migrations`,
  blank `sqlalchemy.url`; `migrations/env.py` pulls the URL from app settings and uses
  `render_as_batch=True` for SQLite ALTER). Two hand-authored revisions: `0001_baseline`
  recreates the ORIGINAL schema (utterances WITHOUT `stt_provider`, documents WITHOUT
  `kind`); `0002` adds `utterances.stt_provider` + `documents.kind`. `init_db()` now calls
  `run_migrations()`, which: stamps `0001_baseline` when it finds a legacy DB (tables exist
  but no `alembic_version`), then `upgrade head`. Fresh DBs run 0001+0002; migrated DBs no-op.
- Why: Fixes the live `sqlite3.OperationalError: table utterances has no column named
  stt_provider` (the column was added to the model in Session 3 but create_all never alters
  an existing table). Alembic adds columns in place, preserving data — no DB deletion — and
  is the right tool for the future EHR (Module 13) and production deployment. Verified on the
  real DB (2 rows preserved) and a fresh DB; idempotent re-run is a no-op.
- Rejected: Deleting/recreating the DB (loses data, unacceptable for an EHR foundation);
  a hand-rolled PRAGMA `ALTER TABLE ADD COLUMN` at startup (works but reinvents migration
  tooling the human explicitly asked to use properly); `alembic stamp head` only (would not
  actually add the missing column).
- Status: Accepted

## ADR-0023 — 2026-06-21 — Raw and corrected are exported as TWO separate, independent documents (documents.kind)
- Decision: Export the RAW transcript and the CORRECTED transcript as SEPARATE .docx
  files, each independently downloadable, rather than one combined file. Add a
  `documents.kind` column ("raw" | "corrected"; legacy rows "combined"). The raw .docx is
  generated when recording stops (frontend: save raw → POST /documents/raw); the corrected
  .docx on /api/correct (best-effort) and re-creatable via POST /documents/corrected.
  `DocumentWriter.render(utterance, *, kind)` renders one side (raw → title "Transcript";
  corrected → "Corrected Transcript"). New routes keep the `/api/*` prefix:
  GET /api/transcripts/{id} (returns raw+corrected text + both document links via
  `TranscriptDetailOut`), POST /api/transcripts/{id}/documents/{raw,corrected}.
- Why: Matches the requested workflow (download either version on its own; raw never
  overwritten by corrected — rule #1). Keeping the dedicated `documents` table + a `kind`
  column (instead of flat `raw_doc_path`/`corrected_doc_path` on the utterance) preserves
  version history and the future PDF/Markdown/multi-format path. Decided with the human
  (3 forks: documents-table+kind, Alembic, keep /api/* prefix).
- Rejected: Flat doc-path columns on `utterances` (one path each, no versions, metadata
  split across tables); a single combined doc (can't download the two independently);
  a parallel bare `/transcript/*` route set (mixes two conventions, static-mount edge cases).
- Status: Accepted (supersedes the single-combined-doc part of ADR-0021; the
  derived-artifact + DB-as-source-of-truth + storage/format seams of ADR-0021 still hold)

## ADR-0024 — 2026-06-25 — Retire the standalone Emergency module; fold a red-flag check into M10; keep module numbering with an M5 gap
- Decision: Remove the standalone Emergency Detection module (old Module 5), its
  `D1` decision diamond ("Emergency Detected?"), and the `AX` escalation alert from the
  Patient Journey flowchart; connect M4 directly to M6. Move the safety responsibility into
  **Module 10 (Risk Assessment)** as a **rule-based red-flag check** that maps clearly
  life-threatening symptoms (chest pain, stroke signs, severe breathing difficulty, loss of
  consciousness) to the **Critical** tier and surfaces them prominently; Module 12's report
  keeps a **Red Flags** section sourced from M10. Revise constitution rule #3 accordingly
  ("Surface red flags; never reassure falsely"; autonomous emergency triage/escalation is
  out of scope for this version). **Keep existing module numbers with a gap at M5** (M6–M15
  unchanged).
- Why: The human confirmed simplifying the flow (one fewer decision branch + alert). Folding
  the check into M10 keeps a medical pre-screening tool honest — it must never present a
  falsely reassuring picture — without the complexity of a separate parallel module and
  escalation pathway. Keeping the numbering avoids invalidating ADR-0001…0023 and every
  M6–M15 cross-reference across nine docs.
- Rejected: Deleting the emergency *capability* entirely (unsafe for a clinical tool — a
  red-flag patient could be triaged as Low; flagged as Open Flag 1 for the student to confirm);
  renumbering M6→M5 etc. (breaks the whole decision/test trail for no benefit); keeping the
  standalone module (the human explicitly removed it from the flow).
- Status: Accepted (amends constitution rule #3 and §3 module table)

## ADR-0025 — 2026-06-25 — Final full-stack: CONFIRM the existing stack; ADD browser TTS and a deploy path (no rewrite)
- Decision: Lock the stack as: Frontend = plain HTML/JS + CSS (Mintlify), served by FastAPI;
  Backend = Python 3.14 + FastAPI + Uvicorn (REST now, WebSocket reserved for Phase 1);
  Database = SQLite via SQLAlchemy + Alembic (config-driven URL → Postgres later);
  AI connector = one OpenAI-compatible client behind a `Corrector`/provider ABC;
  STT = browser Web Speech API (`bn-BD`); **TTS = browser Web Speech API `SpeechSynthesis`
  (new)**; Document export = python-docx; Deployment = local `uvicorn` (now), optional single
  Docker container / free PaaS (later). No microservices.
- Why: A working Phase 0 codebase (19 passing tests) already embodies ADR-0003/0004/0009/0010/
  0011/0019/0021/0022. Switching frameworks (React/Postgres/etc.) now would discard working
  code and violate CLAUDE.md's "small, reviewable changes". TTS via the same browser API that
  already does STT adds the M7 audio requirement with zero new dependency, no server round-trip,
  and no key.
- Rejected: Rewriting the frontend in React now (premature; CLAUDE.md says "React later");
  Postgres now (SQLite + config-driven URL already covers the swap); a cloud TTS service
  (adds a key, cost, and a network hop for a feature the browser already provides);
  microservices / docker-compose multi-service (over-engineering — CONFIRMED CHANGE 4 forbids it).
- Status: Accepted

## ADR-0026 — 2026-06-25 — Per-module free-API assignment to maximize free-tier longevity (refines ADR-0003)
- Decision: Assign LLM-dependent modules across THREE independent daily quota buckets so no
  single limit is the bottleneck: **Gemini 3 Flash** (free, ~1,500 req/day, resets midnight PT)
  for quality tasks (M2 correction, M4 summary, M11 XAI, M12 prose); **Gemini Flash-Lite**
  (higher RPM) for cheap structured extraction (M3, M8) to protect the main Flash quota;
  **Groq Llama 3.3 70B** (very fast LPU, ~1,000 req/day, resets midnight UTC) for live-loop
  tasks (M6, M7); **OpenRouter `:free`** as the universal fallback for every module
  (recommend a one-time $10 top-up to raise 50→1,000 req/day). M1 STT, M9 completion check,
  and M13/M14/M15 are LOCAL / NO-API. All providers are OpenAI-compatible, so the existing
  single client + a `base_url`/model swap (ADR-0011) implements the whole strategy via config.
- Why: Maximizes free longevity (priority order: free longevity > demo quality > raw
  performance). Spreading across buckets that reset at different times effectively multiplies
  daily capacity; routing quality-critical low-frequency work to Gemini and high-frequency
  loop work to Groq matches each provider's strength (Bangla quality vs. speed).
- Rejected: One provider for everything (single point of quota failure); Gemini 2.5 Pro
  (free tier removed April 2026 — Flash/Flash-Lite only); hard-coding model names in code
  (config-driven instead). NOTE: free-tier numbers drift — verify in each console
  (ai.google.dev/gemini-api/docs/rate-limits, console.groq.com/docs/rate-limits,
  openrouter.ai/docs/api/reference/limits). Synthetic/consented data only (rule #4).
- Status: Accepted (refines ADR-0003)

## ADR-0027 — 2026-06-25 — Voice interaction model: Web Speech STT (bn-BD) + SpeechSynthesis TTS; patient replies voice-only; manual text is a fallback
- Decision: Patient input is **voice only** (no keyboard for the patient). STT =
  `webkitSpeechRecognition`, `lang='bn-BD'`, `continuous=true`, `interimResults=true`
  (per ADR-0014/0020). TTS = `window.speechSynthesis` + `SpeechSynthesisUtterance`,
  `lang='bn-BD'`, choosing an installed Bangla voice if present (else default). The manual
  text box remains ONLY as a developer/accessibility fallback for mic failure.
- Why: Matches the kiosk/tablet patient experience and CONFIRMED CHANGE 2. Reusing the same
  browser API for both directions keeps it free, key-less, and cross-platform.
- Rejected: Keyboard input for patients (defeats the voice-first goal); a cloud TTS
  (unnecessary cost/dependency); removing the manual fallback (would break Module 1's
  required mic-failure path, constitution Module 1).
- Status: Accepted

## ADR-0028 — 2026-06-25 — Follow-up question presentation: on-screen text AND spoken audio simultaneously
- Decision: At M7, each follow-up question is **displayed as text on screen AND played as
  audio via TTS at the same time**. The patient answers by voice; their answer is captured
  by STT and sent to M8. The S7 flowchart node carries the subtitle
  "(Audio + Text display | Voice reply only)".
- Why: Dual presentation aids comprehension across literacy/accent/age ranges and keeps the
  question visible if the Bangla TTS voice is unavailable or low quality (the text is the
  built-in fallback). Required by CONFIRMED CHANGE 2.
- Rejected: Audio-only (fails when no Bangla voice is installed or in a noisy clinic);
  text-only (defeats the voice-first, low-literacy-friendly goal).
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
