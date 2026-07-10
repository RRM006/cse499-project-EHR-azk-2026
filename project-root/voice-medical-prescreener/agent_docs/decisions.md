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

## ADR-0029 — 2026-07-03 — Adopt the mockup's clinical-blue design system for all three portals (supersedes the Mintlify frontend rule)
- Decision: The visual system of `agent_docs/mockups-redesign.html` (clinical blue
  `#0F4C81` primary, bright blue `#2A75D3`, green accent `#10B981`, 8px radius, Inter,
  bilingual EN/BN via `data-en`/`data-bn`) becomes the project design for the Patient
  kiosk, Medic portal, and Doctor portal. `DESIGN-mintlify.md` and CLAUDE.md's frontend
  rules are to be updated accordingly. Unchanged regardless of skin: Noto Sans Bengali
  for Bangla text (never mono), and the transcript-panel behavior (fixed height,
  scrollable, stick-to-bottom, raw read-only).
- Why: The mockup is the reviewed, human-approved product direction; keeping two design
  systems would guarantee drift. This contradicted a locked CLAUDE.md rule, so it was
  flagged explicitly and decided by the human (2026-07-03), not silently resolved.
- Rejected: Keeping Mintlify and restyling the mockup layouts (double work, and the human
  prefers the clinical look); mixing both systems per portal (incoherent product).
- Status: Accepted (supersedes the DESIGN-mintlify.md visual rule; CLAUDE.md update pending)

## ADR-0030 — 2026-07-03 — Mockup reconciliation: medic role, doctor assignment, awaiting_doctor status, stub OTP, 10-field summary JSON shape
- Decision: (a) `users.role` CHECK gains **'medic'** (real triage-staff role). (b) New
  nullable `visits.assigned_doctor_id` FK → `users.id` records the medic→doctor
  assignment; `doctor_reviews` remains append-only doctor actions only. (c) `visits.status`
  CHECK gains **'awaiting_doctor'** (patient submit → `awaiting_review` → medic forward →
  `awaiting_doctor` → doctor accept → `reviewed`); the kiosk auto-logout/reset is purely
  frontend state. (d) Patient identification = phone number stored normalized in
  `patients.external_ref` (unique per clinic) + a **stubbed** OTP verify endpoint checking
  a `DEV_OTP` env value — no SMS gateway, no session table (the kiosk session is
  `visits.uuid`). (e) The 10-fixed-field summary is a Pydantic-enforced
  `summary_fields` JSON shape inside `case_profiles.entities` (per-field
  `{value, source: 'ai'|'human', edited_by?, edited_at?}`), not promoted columns
  (§6.2 rule); staff field edits are additionally logged append-only in `audit_log`.
  (f) Risk tier codes stay `low/medium/high/critical`; "Moderate" is a display label in
  one shared frontend `TIER_LABELS` map. Clarification: ADR-0027's voice-only rule
  governs *clinical* input; typing a phone number/OTP for identification is allowed.
  All schema deltas land inside the not-yet-written rev `0003` (ADR-0022 preserved).
- Why: The mockup introduced workflow (triage + assignment + phone lookup) that the locked
  schema didn't model; these are the smallest additions that keep every architecture.md §0
  principle (aggregate root, JSON-for-evolving-data, append-only, module_events) intact.
  Full analysis: `agent_docs/reconciliation.md`.
- Rejected: Treating medic as a relabeled 'desk' (human confirmed it is a distinct role);
  an assignments/auth-session table (overkill for the demo; a column + visit uuid suffice);
  promoting the 10 fields to real columns (nothing filters/sorts on them in SQL yet);
  real SMS OTP (cost + dependency, not needed to prove the capstone).
- Status: Accepted (extends ADR-0024–0028; schema deltas recorded in architecture.md §7)

## ADR-0031 — 2026-07-05 — Legacy Phase-0 demo isolated at /legacy/; root becomes a portal landing page
- Decision: (a) The Phase-0 transcript demo (`index.html` + `app.js` + `styles.css`) moves
  from `frontend/` into its own `frontend_legacy/` folder, mounted at **`/legacy/`**
  (`git mv`, history preserved); its asset refs become relative (`/styles.css` → `styles.css`)
  so it is self-contained under the new mount. Its `/api/*` routes are untouched — the demo
  stays fully working. (b) `/` becomes a small clinical-blue **landing page**
  (`frontend/index.html`) linking the four app entry points: kiosk, medic, doctor, legacy.
  (c) `main.py` keeps an `ENTRY_POINTS` list and logs it at startup (STRUCT-2) — "4 links"
  was confirmed by the human to mean the four app entry points, not the four legacy artifacts.
- Why: The legacy demo owning `/` made the new full-stack app look secondary and mixed two
  generations of frontend in one folder (`context_fixed_problem.md` §0.1). A separate folder +
  clearly-named route makes the demo obviously distinct and unable to interfere with the
  portals, without deleting anything.
- Rejected: Deleting the demo (still useful reference + its tests guard the M2 seam);
  `/demo/` as the route (human chose `/legacy/`); redirecting `/` to the kiosk (a directory
  page serves all roles, and kiosks can be bookmarked to `/kiosk.html` directly).
- Status: Accepted

## ADR-0032 — 2026-07-05 — Rev 0010: visit-grain documents, DB letterhead, vitals, prescriptions table
- Decision: One new Alembic revision `0010_prescriptions_letterhead` (applied; backup
  `prescreener.db.pre-0010.bak`): (a) `documents.utterance_id` becomes NULLABLE so
  visit-grain exports (full-visit transcript / summary report / prescription) can exist —
  they set the already-present `visit_id` and new data-level `kind` values
  ('transcript'|'summary_report'|'prescription'); (b) `patients` gains `weight_kg` + `bp`
  (age/gender already existed as `birth_year`/`sex`); (c) prescription letterhead lives in
  DB columns — `users.qualification/registration_no/specialization/signature_path`,
  `clinics.address/logo_path`; (d) new `prescriptions` table (`visit_id`, `doctor_id`,
  `payload` JSON, `document_id` FK → documents) — the form shape is JSON (principle 3), the
  `Diagnosis` field inside `payload` is human-doctor-authored ONLY (rule #2, decision C1),
  and `document_id` makes the exported `.docx` retrievable by doctor and patient.
- Why: The Session-9 spec (DOCTOR-3/4/5/6, MEDIC-6/7, KIOSK-4) needs visit-level exports,
  patient vitals, and a professional prescription with a reusable letterhead; the human
  chose DB-backed storage over file-only and per-entry manual letterhead input.
- Rejected: A separate `visit_documents` table (the existing `documents` table already had
  `visit_id` since 0003 — one table, two grains, no duplication); a CHECK constraint on
  `documents.kind` (kept constraint-free since 0002, new kinds stay additive); storing the
  prescription as promoted columns (medicines are a variable-length list — JSON fits §6.2);
  numeric AI risk-score columns (decision C2: display-only tier→band mapping, nothing stored).
- Status: Accepted

## ADR-0033 — 2026-07-05 — Bilingual summary values: one extraction call fills value_en + value_bn; `value` mirrors value_en
- Decision: (a) The M3/M8 extraction prompt returns each of the 10 fields as
  {"en", "bn"} — the SAME content written once in English and once in Bangla script —
  so bilingual display costs ZERO extra LLM calls (one extraction, not extraction +
  translation). (b) Stored shape: `{value, value_en, value_bn, source, ...}` where
  `value` MIRRORS `value_en` — every pre-Session-9 consumer (queue main_problem, staff.js,
  docx writers) and every stored legacy row keeps working unchanged; readers fall back
  across the three slots (`shared.js fieldValue()`, `completion.field_has_text()`,
  `visit_docx._field_value()`). (c) A plain-string model reply is salvaged as English.
  (d) M9 counts a field filled if ANY slot has text (a Bangla-only value is not "missing").
  (e) A staff PATCH edit writes the typed text into ALL slots untranslated — staff text is
  authoritative and is never machine-translated (no quota on edits; M8 still never
  overwrites 'human' fields).
- Why: KIOSK-6/DOCTOR-2/MEDIC-1 need the VALUES (not just labels) to follow the language
  toggle; the human chose generate-once-and-store over on-the-fly client translation
  (which would burn quota on every toggle). JSON shape evolution needs no migration
  (principle 3).
- Rejected: A separate translation call per language (double quota); storing only
  value_en/value_bn and dropping `value` (breaks every existing consumer and stored row);
  machine-translating staff edits (staff words are authoritative; silent translation could
  distort clinical meaning).
- Status: Accepted

## ADR-0034 — 2026-07-06 — KIOSK-7 resume loop = `?scope=fields` on the existing M7–M9 endpoints
- Decision: The kiosk summary-screen resume loop reuses `POST /followup/next` and
  `POST /followup/answer` with a `?scope=fields` query param. In that scope: (a) the
  0.7 completeness-threshold gate does NOT apply — "complete" means all 10 summary
  fields carry text, or the generator stops; (b) the missing list = the summary-field
  KEYS empty in every language slot (`missing_summary_fields()`, reusing M9's
  `field_has_text`), and the stored `target_gap` is forced to a real field key (the
  LLM's echo is never trusted), so the followup_questions no-repeat memory guarantees
  a field answered "নেই / No / জানি না" is never asked again even if the extractor
  leaves it blank; (c) the per-visit question cap (`followup_max_questions`) is ONE
  budget SHARED with the main conversation loop; (d) the kiosk UI is FAIL-OPEN —
  cap reached or API error → Confirm & Submit comes back; the patient is never trapped.
- Why: One code path (generation, no-repeat memory, cap, M8 merge, M9 rescore) instead
  of a parallel loop; the shared cap is the strongest patient-fatigue guard and the
  literal reading of the approved KIOSK-7 decision; fail-open matches the Module-1
  fallback principle (a hiccup must never block care).
- Rejected: Separate `/followup/resume-*` endpoints (duplicated guards/schemas);
  a separate resume budget (more questions, a new config knob, weaker fatigue guard);
  deterministically writing "নেই" into the field from the frontend (fabricates a
  derived value outside M8's provenance rules).
- Status: Accepted

## ADR-0035 — 2026-07-06 — MEDIC-3 risk override = appended human assessment row; staff cannot downgrade a red-flag Critical
- Decision: `POST /api/visits/{uuid}/risk/override` appends a NEW `risk_assessments`
  row with `model_provider='human'` — AI rows are never edited (append-only history
  stands). The human row carries the latest row's `red_flags` AND `rule_overrode`
  forward, and gets a stored XAI reason ("…by staff override. Reason: …") so no risk
  row is ever reason-less (constitution). Every override lands in `audit_log`
  (`action='risk_override'`, detail = {from, to, reason}, actor_id = the medic). GUARD:
  if the current tier is a red-flag Critical, any staff downgrade is refused (409) —
  only the doctor's review can override it (rule #2: the doctor decides; rule #3:
  never falsely reassure). The wire accepts tier CODES only — no numeric scores (C2).
- Why: Zero migration (every reader — GET /risk, the dashboard queue, the doctor
  panel — already takes the latest row, so the override propagates everywhere
  automatically); full auditable history; the deterministic red-flag rule stays
  un-silenceable below the doctor role.
- Rejected: An `override_tier` column on risk_assessments (migration + every reader
  updated); editing the AI row in place (destroys the audit story); allowing the
  downgrade with a mandatory reason (a data-entry-level role could silence the one
  safety rule that survives total LLM outage).
- Status: Accepted

## ADR-0036 — 2026-07-06 — C1 suggested condition = separate M10C call; stored in `entities` with an embedded disclaimer; staff-only
- Decision: The "Possible Condition (AI Suggestion – Not a Diagnosis)" (MEDIC-4,
  decision C1) is generated by a NEW module code **M10C** on the Gemini **Flash**
  bucket — deliberately a SEPARATE LLM call from M10, whose risk prompt hard-forbids
  naming diseases and must never be contaminated. One call returns bilingual JSON
  (`condition_en/bn`, `reasoning_en/bn` — ADR-0033 pattern). Stored at
  `case_profiles.entities["suggested_condition"]` (no migration, principle 3) with
  provenance like the 10 fields (`source: ai|human`, `edited_by/at`) and the
  **"not a diagnosis" disclaimer constants embedded IN the stored object**, so every
  payload that carries the suggestion carries the disclaimer — impossible to forget.
  Trigger: best-effort inside kiosk submit (with `assess_visit`); a failed call means
  "no suggestion", never a blocked submit. Edit path:
  `PATCH /api/visits/{uuid}/profile/condition` (medic/doctor/admin only, 403 otherwise;
  staff text fills all language slots untranslated; server re-attaches the disclaimer;
  audit_log `profile.condition_edit`). UI: `renderConditionCard()` in shared staff.js —
  portals opt in via a `#condition-card` mount (medic now, doctor at step 17); the
  patient kiosk has no mount and never shows it. HARD BOUNDARY (rule #2): this value
  NEVER pre-fills the doctor's prescription Diagnosis field (step 18 defaults it EMPTY).
- Why: A separate prompt keeps the safety-critical M10 prompt untouched; the embedded
  disclaimer makes rule #2 labeling testable as a payload property; entities JSON
  needs no migration and rides every existing profile reader.
- Rejected: Piggybacking condition-naming onto the M10 call (prompt contamination of
  the one classifier the red-flag rule guards); a `case_profiles` column (migration
  for one JSON blob); a pseudo-key inside the 10-field endpoint (would loosen
  `SUMMARY_FIELD_KEYS` validation); LLM-generated disclaimer text (must be a constant).
- Status: Accepted

## ADR-0037 — 2026-07-06 — MEDIC-6/7: post-referral snapshot screen; vitals PATCH; summary_report .docx regenerates fresh at download
- Decision: (a) After "Submit & Forward" the medic lands on a summary screen rendered
  from a SNAPSHOT of the case as referred (no re-fetch) — it is a hand-off
  confirmation artifact; the .docx, not the screen, is the always-current record.
  (b) Patient vitals get their own staff-only endpoint,
  `PATCH /api/patients/{patient_id}/vitals` (`weight_kg` 0–500 + free-form `bp`,
  403 for non-staff, audit `patient.vitals_edit`) — patient-scoped so the doctor
  portal reuses it; vitals are staff-recorded facts, not AI-derived profile fields.
  (c) `GET /visits/{uuid}` embeds the patient (`VisitDetailWithPatientOut`, defined
  in schemas/patient.py because patient.py already imports visit.py — avoids a
  schema import cycle). (d) `generate_visit_document(kind="summary_report")` now
  assembles a **fresh M12 report every time** instead of reusing `latest_report` —
  a docx downloaded after a field edit or risk override must show the current
  state ("download must actually work" includes not being silently stale). Report
  rows are append-only, so regenerating preserves history. The report sections
  gained `patient_profile.weight_kg/bp` and the C1 `suggested_condition` object
  (its embedded disclaimer renders in the docx); the docx still prints tier CODES
  only — C2 bands stay exclusively in `shared.js` `TIER_BANDS`.
- Why: One GET serves the staff detail screens; the freshness rule turns a subtle
  correctness bug into a guaranteed property (regression-tested); patient-scoped
  vitals avoid duplicating the edit path per portal.
- Rejected: Re-fetching everything for the post-referral screen (extra calls for a
  confirmation view); storing vitals inside `summary_fields` (they are not
  extracted-from-speech content and must not be M8-mergeable); keeping
  latest-report reuse with a manual "regenerate" button (staff would forget).
- Status: Accepted

## ADR-0038 — 2026-07-06 — DOCTOR-4/5 prescription: form + letterhead-prefill in step 18, save + .docx at Submit in step 19; Diagnosis never AI-filled
- Decision: (a) The prescription work splits cleanly: **step 18 = the form + a
  read-only prefill endpoint**; the DB write (a `prescriptions` row) and the .docx are
  created **together at Submit in the DOCTOR-6 step (19)** — matching DOCTOR-6's "after
  Submit → generate + save + download" wording. Nothing persists in step 18.
  (b) Prefill endpoint `GET /api/visits/{uuid}/prescription/context?doctor_id=` returns
  **letterhead only** (clinic {name,address,logo_path} + doctor
  {qualification,registration_no,specialization,signature_path}); the patient details and
  the 10 symptom fields are assembled client-side from the already-loaded case, so they
  are not re-sent. 404 on unknown visit/doctor, 400 if the user is not a doctor.
  (c) The **Diagnosis field is always EMPTY on load and authored by the doctor** — it is
  never pre-filled from the C1 AI suggested condition (constitution rule #2, human
  decision C1 / ADR-0036). The context contract has no diagnosis/condition field at all.
  (d) **Letterhead is seeded, editable in the form, saved in the prescription payload**:
  an idempotent `seed_demo_letterhead()` (run in `lifespan`) fills NULL letterhead columns
  on the demo clinic + doctors with sample values; the form prefills from them and the
  doctor can edit, but edits ride inside the prescription `payload` JSON and are NOT
  written back to the `users`/`clinics` rows (so the seeded profile stays the reusable
  default). Medicine rows add/remove; symptoms auto-fill from `summary_fields`.
- Why: Persisting at Submit keeps one write path (row + doc created atomically with a
  linked `document_id`) and leaves step 18 a tight, testable read-only slice. Seeding
  makes the demo letterhead look professional on both machines with no manual DB step;
  filling NULLs only means it never clobbers a real edit and is safe on every startup.
- Rejected: Saving a draft prescription row in step 18 (two write paths + upsert/draft
  state the spec never asked for); writing letterhead edits back to the profile (more
  endpoints, and the seeded default is enough for reuse); extending `UserOut`/`GET /users`
  with letterhead (pollutes the login contract shared by both portals).
- Status: Accepted

## ADR-0039 — 2026-07-06 — DOCTOR-6: prescription Submit = dedicated POST that saves the row + renders the .docx; a new prescription per Submit
- Decision: Submit is a dedicated `POST /api/visits/{uuid}/prescription` with body
  `{doctor_id, payload}` (NOT the `/documents/{kind}` seam, which regenerates from stored
  state and takes no body). It renders the .docx locally (`render_prescription(payload)` in
  `visit_docx.py`), stores it via the existing storage seam + `repo.create_document`
  (kind `"prescription"`, `visit_id` set, `utterance_id` NULL), and persists a
  `prescriptions` row linked by `document_id` (`generate_prescription_document()` in
  `services/documents/__init__.py`). Returns `{prescription_id, document: DocumentOut}`;
  the UI auto-downloads via the existing `GET /documents/{id}/download`. **A new
  prescription + document is created per Submit** (append; documents are already
  append-only) — no upsert/versioning. Audit `prescription.created`.
- Why: The prescription needs the form payload as a request body, so it can't reuse the
  regenerate-from-state document endpoint. Storing the whole form as `payload` JSON (rev
  0010) keeps the shape migration-free. Crucially, the .docx writer reads ONLY the submitted
  payload — it never touches `entities["suggested_condition"]` — so the Diagnosis is
  structurally incapable of being AI-filled (rule #2); a regression test posts an empty
  diagnosis with a stored AI condition and asserts the condition never appears in the docx.
- Rejected: Adding `"prescription"` to `VISIT_DOCUMENT_KINDS` + the `/documents/{kind}`
  route (no body channel for the form); upserting one prescription per visit (append is
  simpler and preserves every issued version); generating the docx client-side (python-docx
  server-side keeps one rendering path and the file server-stored for later retrieval).
- Status: Accepted

## ADR-0040 — 2026-07-07 — Linux (Arch) browser TTS = speech-dispatcher + espeak-ng, stay on Chromium
- Decision: On Linux, the kiosk's browser `speechSynthesis` (M7 audio) is provided by the system
  **speech-dispatcher** daemon with **espeak-ng** as its output module (both from `pacman`).
  We **stay on Chromium** (do NOT require Google Chrome) since the human's mic/STT already works
  there. The daemon must be reachable when Chromium starts: keep the shipped, `enabled`
  **`speech-dispatcher.socket`** started (`systemctl --user start speech-dispatcher.socket`) so
  socket-activation spins up the daemon on connect (Chromium's sandbox can't spawn it itself), and
  launch Chromium once with **`--enable-speech-dispatcher`** after a **full process restart**
  (`pkill chromium` — a reload/new-window is not enough on Wayland; the voice list is read only at
  process start). No application code change — `frontend_shared/tts.js` already picks any `bn*`
  voice and degrades to on-screen text when none exists (ADR-0028).
- Why: On a fresh Arch box neither package is installed, so `speechSynthesis.getVoices()` is empty
  and 🔊 is silent. This is a host-setup gap, not a code bug. Verified end to end on the Arch laptop
  (espeak-ng renders a valid Bengali WAV; after the restart `getVoices()` is non-empty and 🔊 speaks)
  — **TC-V2 audio PASS on Arch**. The espeak-ng Bengali voice is robotic; acceptable because the
  on-screen text is always the primary channel (ADR-0028).
- Rejected: Switching to Google Chrome (AUR) just for voices (unnecessary — Chromium works once the
  daemon is present; also complicates the human's setup); a server-side TTS service (adds a runtime
  dep + a network hop, against the "no server, no key" TTS choice in ADR-0027/0028). Windows path is
  unchanged (Settings → Speech → add a Bengali voice; guide PART 1). Both documented in
  `agent_docs/human_live_run_guide.md` (Windows PART 1, Arch PART 1B).
- Status: Accepted

## ADR-0041 — 2026-07-07 — Quota-aware provider cooldown + extended free fallback chain
- Decision: (1) `llm_client.call_module` logs EVERY provider attempt to `module_events`
  (status `error` rows carry provider + truncated message + latency), not just the final outcome.
  (2) A provider that returns a 429/rate-limit/quota error goes on an in-process **cooldown**
  (60 s for a per-minute limit; 15 min when the message looks daily/quota) and is skipped by
  subsequent calls; **fail-open** — if every provider is cooling down, the full chain is tried
  anyway. (3) The fallback chain is now data in `llm_providers.FALLBACK_ORDER`:
  assigned bucket → **Groq → Cerebras → Mistral → OpenRouter**, blank-key buckets auto-skipped.
  The two Gemini buckets are deliberately NOT cross-fallbacks (they hold the ADR-0026 quality-task
  quota); OpenRouter stays LAST (smallest free allowance, ~50 req/day). New optional `.env` keys:
  `CEREBRAS_API_KEY` (free ~1M tok/day, OpenAI-compatible) and `MISTRAL_API_KEY` (free ~1B
  tok/month **but trains on inputs** — rule #4: leave blank unless data is synthetic/consented).
- Why: the 2026-07-06 live run showed M4 (summary formatting) failing invisibly: Gemini Flash's
  free tier is only ~10 RPM / 1,500 RPD, its failure was never logged, and the only fallback
  (OpenRouter `:free`) 429'd 10× in ~9 s — while Groq's ~1,000 req/day sat unused. Cooldown +
  a wider all-free chain keeps the pipeline serving patients at zero cost and makes every failure
  visible in `module_events`.
- Rejected: paid tiers (project rule: free-first); persisting cooldowns in the DB (over-engineering
  for a single-process uvicorn app; in-memory resets on restart, which is also the recovery hatch);
  retry-with-backoff inside one call (adds patient-facing latency — switching buckets is faster);
  Gemini buckets as universal fallbacks (would cannibalize the quality-task quota).
- Status: Accepted

## ADR-0042 — 2026-07-09 — "Context Fixed Problem 2.0" build approach (UI evolve-theme + background submit)
- Decision: For the new work spec `agent_docs/context fixed problem 2.0.md`:
  (1) **UI/UX = *evolve the theme*, not rebuild.** Shift the shared `:root` design tokens in
  `frontend_shared/shared.css` toward the teal/modern look of the human's reference screenshots
  (add a teal secondary, softer surfaces, refined shadows/radius) + light per-portal polish, while
  **keeping every existing page layout and wired feature intact**. No 1:1 copy of the screenshots.
  (2) **Confirm & Submit = *assess in background*.** Move the 3 blocking LLM calls in
  `submit_visit` (M10 risk + M11 XAI + M10C suggestion) into a FastAPI `BackgroundTasks` job so the
  endpoint returns instantly; status→`awaiting_review` + audit stay synchronous, so the case still
  enters the queue immediately and the risk badge fills in on the staff portals' 15 s auto-refresh.
  (3) **Force 4–5 follow-ups:** the M7 loop must ask a *minimum* (~4, cap 5) of clinically useful,
  history-based questions even when the 10 summary fields are already filled — a new
  `followup_min_questions` gate + a broadened M7 prompt.
  (4) **Dhaka time is formatted browser-side** (`Intl` `timeZone:'Asia/Dhaka'`) to stay
  cross-platform (avoids the Windows Python `tzdata` gap); storage stays tz-aware UTC.
  (5) **Real OTP = a persisted, expiring code + a pluggable sender seam, with `000000` kept as a
  universal dev/demo bypass** (see Rejected for the channel reality).
  (6) **Doctor drug-info chatbot** = free web search (a no-key dep, e.g. DuckDuckGo/`ddgs`) →
  existing `call_module()` → structured answer, always shown with the disclaimer "AI-generated
  information. Please verify before prescribing."
  Execution is priority-by-priority (P1 patient → P2 medic → P3 doctor → P4 OTP), functional fixes
  before polish, ONE reviewable item per human "go".
- Why: the reference look is achievable purely through tokens because all portals already consume
  the shared design system — lowest risk, consistent, no re-wiring. Background assessment removes
  the only real submit-latency source without changing behaviour the staff sees. Browser-side Dhaka
  formatting keeps Windows + Arch identical with zero new deps.
- Rejected: a per-portal layout rebuild to mirror the screenshots 1:1 (high effort + high risk of
  breaking wired functionality). Keeping submit synchronous-but-parallel (still makes the patient
  wait; background is faster and the staff refresh masks the delay). Backend `ZoneInfo` for Dhaka
  (needs the `tzdata` package on Windows — an avoidable cross-platform trap). A *free, reliable*
  OTP-to-any-phone channel — it does not exist: WhatsApp Business API + BD SMS gateways cost
  money/approval, and a Telegram bot cannot cold-message a phone number (it needs a `chat_id` from
  a prior `/start`); hence the pluggable seam + `000000` bypass, with the concrete free channel
  (email-OTP or Telegram-for-opted-in) confirmed with the human before it is built. The faculty
  "Future Features" (quantized Moshi summary model; quantized on-device STT/TTS) are explicitly
  **out of scope** for this spec (future research track).
- Status: Accepted

## ADR-0043 — 2026-07-10 — Shared palette evolved to "Teal Medical" (STRUCT-3; supersedes ADR-0029's colors, keeps its structure)
- Decision: The shared design tokens in `frontend_shared/shared.css` move from clinical blue to
  **Teal Medical**: primary `#0F766E` (hover `#0B5751`), secondary `#0D9488`, accent stays
  `#10B981`, bg `#F0FBF8`, border `#D9E7E4`, focus `#14B8A6`, radius 8→10px, teal-tinted shadows.
  The few hardcoded blue tints in shared.css (lang-toggle, hovers, queue active, verbatim/field
  headers, `.source-ai`, input focus ring) follow the teal scheme. **Everything else from ADR-0029
  is unchanged**: component structure, layouts, Inter + Noto Sans Bengali, semantic risk-badge
  colors (red/orange/amber/green), and the safety-panel reds. CLAUDE.md's FRONTEND section updated.
- Why: the human's 2.0 reference screenshots use a modern teal/blue medical look. The human chose
  Option A (teal-forward) over Option B (ocean blue + teal) from live in-browser previews of both
  palettes on the real medic portal. Token-only change = every portal restyles consistently with
  zero layout/JS risk. Primary-on-white ≈ 5.9:1 contrast (WCAG AA).
- Rejected: Option B "Ocean Blue + Teal" (human preferred the decisive teal); a per-portal layout
  rebuild to copy the screenshots 1:1 (ADR-0042 already rejected); recoloring the semantic risk
  badges (risk colors must stay conventional red/amber/green).
- Status: Accepted

## ADR-0044 — 2026-07-10 — M16 doctor drug-info assistant: visit-scoped, Flash bucket, server-attached disclaimer, ddgs-only
- Decision: P3-3's chatbot is module **M16** (`services/assistant.py` + `routes_assistant.py` +
  `schemas/assistant.py`). Design points: (a) endpoint is **visit-scoped**
  (`POST /api/visits/{uuid}/assistant/drug-info`) so every call logs a `module_events` row against
  the case the doctor is reviewing (`visit_id` is NOT NULL there, and the audit linkage is wanted);
  (b) M16 is assigned to the **Gemini Flash bucket** (quality/safety task per ADR-0026, with the
  ADR-0041 fallback chain); (c) the mandatory disclaimer "AI-generated information. Please verify
  before prescribing." (+ Bangla) is attached **server-side on every response** and the fields are
  REQUIRED in the Pydantic response contract — never left to the model (rule #2); (d) web search =
  `ddgs==9.14.4` ONLY (DuckDuckGo, free, no key; its `primp` dep ships Windows x64 + manylinux
  wheels) — no separate httpx dep; (e) search is **best-effort**: failure degrades to a
  sourceless general-knowledge answer (the UI says so), a non-JSON model reply is salvaged as the
  answer, only a dead provider chain is an error (502); (f) the search request carries ONLY the
  doctor's typed question, never patient data (rule #4), and the UI renders all model output via
  `textContent` (never innerHTML).
- Why: visit-scoping matches the doctor's actual workflow (asking from an open case) and reuses
  the existing observability/audit spine with zero schema change; Flash fits a correctness-first
  task; the server-attached disclaimer makes rule #2 structural instead of prompt-dependent;
  fail-open search keeps the assistant useful on a flaky connection without spending extra quota.
- Rejected: a global (visit-less) endpoint (needs a nullable `module_events.visit_id` migration
  and loses case linkage); Groq bucket (speed matters less than quality here; Groq stays the
  live-loop + fallback lane); adding `httpx` + hand-rolled search scraping (ddgs already covers
  it); trusting the LLM to include the disclaimer (violates rule #2 by construction).
- Status: Accepted
