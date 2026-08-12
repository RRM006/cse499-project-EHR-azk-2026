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

## ADR-0045 — 2026-07-11 — P4-1 real OTP: hashed single-use codes + pluggable sender seam (dev log default, TextBee real-SMS demo channel)
- Decision: The kiosk OTP stub becomes REAL verification. (1) **Storage:** new `otp_codes` table
  (Alembic **0012**) keyed by the normalized phone (nullable `patient_id` audit link) holding ONLY
  a salted SHA-256 hash — plaintext exists solely in the sender call and is never persisted,
  audited or logged (the dev-channel server log is the one sanctioned exception; that is its
  entire purpose). (2) **Policy (channel-independent, `services/otp/service.py`):** 6 random
  digits via `secrets` (regenerated if ever equal to the bypass code), 5-min expiry
  (`OTP_TTL_SECONDS`), single-use (`consumed_at`), constant-time compares (`hmac.compare_digest`
  on hashes — also unicode-safe), 5-attempt lockout that rejects even the CORRECT code (HTTP 429;
  a fresh code unlocks), 60 s resend throttle (re-lookup returns `otp_sent=false` +
  `retry_after_seconds`, the outstanding code stays valid), exactly one live code per phone (a new
  issue voids predecessors), and send-failure voids the fresh code (502). (3) **Seam:** `OtpSender`
  ABC + `get_sender()` factory on `OTP_CHANNEL`: `dev` = `DevLogSender` (code printed to the
  server log via the `uvicorn.error` logger) — the Option-A default; `textbee` = `TextBeeSender`
  (real SMS through a TextBee.dev Android-SIM gateway via httpx, now a pinned direct dep).
  (4) **Bypass containment:** `000000` is honored ONLY inside the `otp_channel == "dev"` branch
  AND with `OTP_DEV_BYPASS=true` — structurally impossible under any production channel (a test
  asserts textbee+flag-on still rejects it). Kiosk UX unchanged; existing tests unaffected because
  the default config reproduces the old behavior. Also fixed in passing: `migrations/env.py` now
  calls `fileConfig(..., disable_existing_loggers=False)` — the default silently disabled every
  `uvicorn.*` logger at startup (banner/access/OTP lines invisible), a pre-existing bug.
- Why: P4-1 required a real OTP while keeping the free dev/demo path. S24 research showed no
  truly free SMS-OTP to arbitrary BD numbers exists (Twilio BD $0.5962/SMS, trial only to
  verified numbers; WhatsApp auth ~$0.0113/msg behind Meta Business verification; Firebase phone
  auth is Blaze-plan-only with a billing card; Telegram Gateway $0.01/code but recipients must
  have Telegram; email free tiers verify the wrong identifier). TextBee (open-source, own BD SIM)
  is the only free REAL-SMS option — demo-grade, perfect for the capstone. Hash-only storage +
  the structural bypass gate make the security properties hold identically for every channel.
- Rejected: Firebase phone auth (paid + client-SDK/reCAPTCHA rework of the kiosk); WhatsApp
  (paid + heaviest setup); Telegram Gateway/bot as primary (excludes non-Telegram walk-in
  patients; bots cannot cold-message a number); email OTP (kiosk patients often have no email;
  verifies email, not the phone the DB keys on); storing plaintext or reversible codes (rule #4);
  a bypass flag independent of channel (accident-prone — the flag alone must never be able to
  open production). Production later = a BTRC-approved BD aggregator (~৳0.30–0.40/OTP, e.g.
  sms.bd/Alpha/MiM) as one new `OtpSender` subclass — no core change.
- Status: Accepted

## ADR-0046 — 2026-07-12 — Move the 15-module board to ✅ on the passed HUMAN live-voice gate (formal WER deferred as evidence)
- Decision: After the human live real-mic run PASSED on Windows 11 (S25 — TC-V1/V2/V3/F2/R1 all ✅,
  STT very accurate, ~2 s latency, TTS spoke, follow-ups good, no bugs), flip **Modules 1–14 from
  🟨 → ✅** in `milestone_log.md`. M5 stays retired (⛔); **M15 stays 🟨** (its "Done means" needs a
  retrain/regression pipeline that does not exist yet). The move is recorded WITH a standing caveat
  in `milestone_log.md` + `test_log.md`: this run was **qualitative** (no by-hand WER / precision-
  recall / labeled test set) and **Windows-only** — collecting formal metrics on ~50 samples remains
  the recommended thesis-evidence follow-up, but is NOT a blocker for the board state.
- Why: The 15-module board had explicitly gated on "the HUMAN live-voice run" since S8 — that was the
  one thing standing between the built-and-offline-tested modules and ✅. The run happened and passed
  cleanly, so holding the whole board at 🟨 would misrepresent project status for the capstone. The
  caveat keeps us honest about the evidence still owed without blocking the status.
- Rejected: (a) "Flip M1 & M7 only" (the two modules whose "Done means" the live run most directly
  proves) — technically tightest but under-reports the many modules that were only live-gated;
  (b) "Change no marks; keep all 🟨 until formal WER exists" — most conservative but leaves the board
  contradicting its own "gates on the human live run" note now that the gate is cleared. The human
  chose the middle-bold option (flip 1–14) with the metrics caveat attached.
- Status: Accepted

## ADR-0047 — 2026-08-08 — Faculty Requirement 3 (fully voice-driven follow-up) = research-track, client-side turn-taking, independent of Reqs 1 & 2
- Decision: File the faculty's third future requirement — the follow-up conversation must become
  fully voice-driven (AI speaks → mic opens itself → patient answers → answer captured automatically
  → next question, with no screen contact mid-conversation) — in `faculty_future_features.md` as
  **Requirement 3, ⬜ NOT STARTED research track**, NOT as an item in the `context fixed problem 3.0`
  bug cycle. Scope it as a **client-side turn-taking change**: the basic loop needs **no backend
  change**, and it is **independent of Reqs 1 & 2** (touches no model), so it can be scheduled at any
  point. When built, it ships behind a `voice_loop = manual | auto` config switch following the
  ADR-0045 pattern (switch lives in `.env`, the existing tap-to-talk path is never deleted).
- Why: Reading the code rather than assuming showed the server loop is **already autonomous** —
  `POST /followup/answer` returns `next_question` in the same response after M8 merge + M9 check, and
  `kiosk.js submitPatientTurn()` already chains it into `assistantSays()`. Faculty steps 4–8 therefore
  work today; only steps 2–3 (the two mic taps in `toggleListening()`) are manual. That reframes the
  requirement from "rebuild the conversation engine" to "automate two taps in the browser", and the
  seams already exist: `speak(text, {onend})` in `tts.js` (unused today), `interimResults = true` for
  silence-based endpointing, `stopListening(true)` to submit, `activeDock()` to cover the KIOSK-7
  resume dock. It is *not* a bug — tap-to-talk was a deliberate 2.0 choice (explicit turn boundaries =
  clean verbatim record, no echo risk) and the S25 live run passed with it; going hands-free changes
  the kiosk's interaction contract and introduces real speech-engineering risk (endpointing, TTS echo,
  waiting-room noise), so it needs its own planned cycle. Two rule-#1 hazards are recorded up front:
  an endpointer that clips an answer, and TTS echo transcribed into a `patient` utterance, are
  **correctness defects, not UX nits**. The existing server-side caps
  (`followup_max_questions = 5` / `min = 4` / `threshold = 0.7`) are what make hands-free safe — the
  cap ends the conversation, not the patient's finger.
- Rejected: (a) **File it as a 3.0 bug** — wrong cycle; 3.0 is for manual-testing defects, and nothing
  here is broken. (b) **Fold it into Requirement 2** (wait for the quantized STT/TTS work) — the
  cleanest full-duplex end-state, but it would block a frontend-only, independently demoable win
  behind the heaviest research item; instead Req 3 is kept achievable on the CURRENT browser stack,
  with full-duplex noted as its final step once Req 2's streaming STT provides real VAD.
  (c) **Start building it now** — out of scope for a documentation-only session and it needs the
  human's "go" plus its own plan (CLAUDE.md workflow).
- Status: Accepted (scope EXTENDED by ADR-0048 — Req 3 now also covers dual voice/typing input)

## ADR-0048 — 2026-08-08 — Requirement 3b: dual input (voice AND typing, patient-switchable) — supersedes ADR-0027's "voice-only" clinical-input rule
- Decision: Extend faculty Requirement 3 from "remove the two mic taps" to **"every patient
  interaction in the Patient Portal after phone login supports BOTH voice and typing, switchable at
  will"** (`faculty_future_features.md` §3b). Specifically: (a) a persistent, always-visible
  `[🎤 Voice] [⌨ Type]` mode control in **both** kiosk docks, with the active mode always obvious;
  (b) the ~3-second silence window is a **visible CONFIRMATION countdown, not a hard cutoff** — any
  resumed speech cancels it and listening continues; (c) the mic never opens while
  `speechSynthesis.speaking`, guarded by a delay **plus** a fallback timer for the case where `onend`
  never fires (no installed voice); (d) **one** answer pipeline — voice and typing keep using the
  existing `POST /followup/answer` with `source: mic|manual`, no duplicated flow; (e) it ships behind
  the `voice_loop = manual | auto` switch of ADR-0047, with timings (`silence_ms`, `countdown_ms`,
  `no_speech_ms`, `tts_guard_ms`, `max_answer_ms`) served to the kiosk by a **new public
  `GET /api/config`** so a clinic can tune them for elderly patients without editing JS;
  (f) `AnswerRequest.raw_text` gains a non-blank minimum so "never silently submit an empty answer" is
  enforced **server-side**, not only in the browser. **No schema change — stays at Alembic head 0012.**
  Built in 7 individually GO-gated steps (§J of `faculty_future_features.md`).
- **Supersedes:** the clinical-input half of **ADR-0027** ("Patient input is voice only … the manual
  text box remains ONLY as a developer/accessibility fallback") and the corresponding
  `CLAUDE.md` VOICE INTERACTION RULES line, as narrowed by **ADR-0030** (typing allowed only for
  phone/OTP). Typing becomes a **first-class patient input for clinical answers**. ADR-0027's TTS half
  and **ADR-0028** (questions shown as text AND spoken) are **unaffected**.
- Why: The human's explicit expansion — patients must not be forced into one modality. Inspection
  showed the hard part is already done: voice and typing **already** converge on one endpoint
  (`sendTypedFallback()` → `submitPatientTurn(text,'manual')`), so "one common pipeline" costs nothing
  to honor; what is wrong is only the *framing* — typing hides behind a "Microphone issue?" link.
  Making the countdown a confirmation window (not a cutoff) is the direct mitigation for the R1
  rule-#1 hazard recorded in ADR-0047: a clipped answer corrupts the verbatim record. Serving the
  timings from `.env` follows ADR-0045 and keeps tap-to-talk selectable as the comparison baseline.
- Rejected: (a) **Reinterpreting ADR-0027 silently** — a locked governing rule must be superseded on
  the record, and `CLAUDE.md`'s rule text edited, not quietly re-read. (b) **A separate typing flow**
  — would duplicate the M7–M9 logic for no gain. (c) **Pre-filling the text box with the captured STT
  buffer on a Voice→Type switch** — a typed edit on top of STT text would be stored as one utterance
  whose `source`/`stt_provider` provenance is false; switching clears the buffer instead (offered to
  the human as an option, not chosen). (d) **Passing `echoCancellation` constraints** — impossible:
  the Web Speech API opens its own audio stream, so echo protection is structural gating only.
  (e) **Adding vitest + jsdom for the timer logic** — real coverage, but it breaks the
  "one requirements.txt + a venv" cross-platform constraint; deferred to the human's choice.
- **RESOLVED by the human, same session (S28):** (1) **The 3-second visible countdown IS the silence
  window itself** — speech stops → 3 → 2 → 1 → submit if still silent; **any** resumed speech cancels
  it immediately and listening continues. Chosen for clear feedback with minimum delay; the rejected
  alternative was a separate quiet-detect phase before the countdown (≈4.2–6 s). (2) **Frontend tests =
  (a) static-source assertions via the existing `TestClient` pattern** — no vitest/jsdom, keeping the
  "one requirements.txt + a venv" constraint intact; the real mic/TTS/silence/countdown/barge-in
  behaviour is proven **only** by the live Chrome run (§K). (3) **`CLAUDE.md` updated — YES.**
- **Project priority recorded by the human (S28):** *voice is the main goal and primary UX, not an
  optional feature.* The portal must actively guide patients toward speaking, automating the voice
  interaction wherever possible; typing exists so that a patient is **never blocked** by recognition
  failure, mic/environment problems, or personal preference. UX priority = **minimize clicks, waiting
  and complexity** for elderly/non-technical patients. Ideal flow: **AI speaks → mic opens
  automatically → patient speaks → 3-second visible countdown → submit → AI speaks the next question
  → repeat.**
- **Implementation decisions taken during S2/S3 (recorded here rather than as separate ADRs — they
  implement this ADR, they do not choose a different architecture):**
  1. **The stale-callback guard lives in `tts.js`, at the single TTS entry point — not in
     `kiosk.js`.** Discovered while building S3: **Chrome fires `onend` for an utterance that
     `speechSynthesis.cancel()` killed**, so a cancelled question's callback would open the mic while
     the NEXT question is still audible — the AI's own voice into a `patient` utterance. A generation
     token in `speak()` drops superseded callbacks, and `onerror` is bridged to the same handler so a
     failed utterance cannot strand a caller waiting to listen. Putting it at the seam means every
     current and future caller inherits the protection. **Measured**: two questions 200 ms apart →
     exactly one mic-open, after the second.
  2. **Auto-open calls the same `toggleListening()` a tap calls.** One code path, so the automatic
     and manual routes can never drift apart in behaviour.
  3. **A mode switch is a first-class cancel.** `cancelPendingMic()` runs on a tap, a mode switch,
     "Done", and the logout reset — a deliberate human action always beats a pending auto-open.
  4. **Switching Voice→Type discards the un-submitted STT buffer** rather than pre-filling the text
     box (rejected option (c) above), so no stored utterance ever carries false `source`/
     `stt_provider` provenance.
  5. **The per-bubble 🔊 replay stays plain `speak()`** — reviewing an earlier turn must never open
     the microphone.
- Status: **Accepted.** **Step S1 implemented in S28** (backend only, zero UX change): `voice_loop` +
  the four timings in `core/config.py` with `resolved_voice_loop` normalization, the new public
  `GET /api/config` (`routes_config.py` + `schemas/kiosk_config.py`, secret-free by construction and
  test-asserted), and the non-blank `raw_text` guard on `AnswerRequest` that returns the value
  **unchanged** (rule #1). **Steps S2 and S3 also implemented in S28** — the `[🎤 Speak] [⌨ Type]`
  switch in both docks, then auto-listen with the echo guard and the `max(3 s, len×80 ms)` safety net
  for machines where `onend` never fires. **192 → 234 tests pass** (+19 S1, +11 S2, +12 S3, zero
  regressions). **Steps S4–S7 are NOT built** — each needs its own "go", and S4–S6 can only be proven
  by the human's live Chrome run with a real microphone.
  **UPDATE (S29): Step S4 is implemented AND its live run PASSED** — silence detection, the visible
  3-2-1 confirmation countdown driven by `countdown_ms`, barge-in cancel on every `onresult` tick, and
  a flush-before-submit (`recognition.stop()` → submit from `onend`, else a 600 ms grace) so the tail
  Chrome had not yet marked `isFinal` is not dropped (rule #1). **234 → 247 tests.** S5–S7 remain.

## ADR-0049 — 2026-08-08 — Bangla TTS: add a server-side provider seam with local espeak-ng; supersedes ADR-0040's rejection of server-side TTS (on Windows only the browser path is impossible)
- Context: after the S4 live run passed, the remaining defect was that the patient could not **hear**
  Bangla questions on Windows. **Verified root cause, not a guess:** Bengali is **absent from
  Microsoft's entire Windows TTS voice list** (checked against Microsoft's own "supported languages and
  voices" appendix — no `bn-BD`, no `bn-IN`, in neither the classic nor the Natural-voices table), and
  the dev machine confirms it: only `Microsoft David/Zira (en-US)`, no `bn` token in either the
  `Speech\Voices\Tokens` or the `Speech_OneCore\Voices\Tokens` hive, and no Bengali language pack.
  **So ADR-0040's "Windows path is unchanged (Settings → Speech → add a Bengali voice)" documents a
  step that cannot succeed**, and `human_live_run_guide.md` PART 1 was instructing the human to do the
  impossible. The Arch path (ADR-0040: speech-dispatcher + espeak-ng) remains correct and untouched.
- Decision: introduce a **server-side TTS provider seam** (`backend/app/services/tts/`, deliberately
  mirroring the ADR-0045 OTP sender seam: `base.py` ABC + provider module + `service.py` selector) with
  **`EspeakNgProvider`** as the first provider, exposed by a new public **`GET /api/tts?text=&lang=`**
  returning `audio/wav`. The frontend keeps ONE entry point — `speak(text, {onend})` in `tts.js` — which
  now walks a chain: **(1) a real browser voice for the active UI language → (2) `GET /api/tts` →
  (3) return `false`.** `TTS_PROVIDER=browser` restores the exact pre-ADR-0049 behaviour without
  deleting anything.
- Why espeak-ng and not something better-sounding:
  1. **It is not a new engine for this project.** ADR-0040 already accepted espeak-ng's Bengali on Arch
     (TC-V2 audio PASS), so Bangla now sounds the same on both dev machines.
  2. **No question text leaves the machine.** M7 questions are derived from what the patient said, so a
     cloud TTS would export patient-derived content to a third party (rule #4). This does not.
  3. **Zero new Python dependencies** — stdlib `subprocess`, so "one `requirements.txt`, all pure-Python
     wheels" is intact. Text is passed via **stdin** (`--stdin`), never argv, so Bangla never goes
     through Windows argv encoding, and `shell=False` leaves no injection surface.
  4. Robotic quality is already an accepted trade-off: ADR-0028 makes the on-screen text the primary
     channel, and ADR-0040 accepted exactly this voice.
- **Failure is loud, never silent.** The old `speak()` returned `true` whenever `speechSynthesis` merely
  *existed*, so a Bangla question with no Bangla voice was read by an en-US voice — audible nonsense
  that looked like success. Now Bangla demands a matching voice; a missing engine is a **503** (not a
  silent 200), `speak()` returns **false**, and the KIOSK-2 banner keeps telling the patient the truth.
  `/api/config` gained **`server_tts: bool`** — a *capability*, reflecting whether the engine is really
  installed, never the provider's name or path (that file's own no-disclosure rule).
- **The rule #1 trap this created, and the fix.** Server audio plays through an `<audio>` element, and
  `speechSynthesis.speaking` is **false** the entire time it does — including while the request is still
  in flight. Left alone, S3's echo guard would have opened the microphone while the AI was audible and
  transcribed the AI's own question into the patient's verbatim record. Fixed by adding **`ttsSpeaking()`**
  (true for either provider, and true from the moment the request is created) and swapping that **one
  predicate** in `openMicWhenQuiet()`; `toggleListening()` likewise calls **`ttsCancel()`** instead of
  `speechSynthesis.cancel()` so a deliberate tap silences server audio too. **No S4 countdown, silence
  or barge-in logic was touched.**
- Also fixed, because it was actively breaking verification: Starlette's `StaticFiles` sends no
  `Cache-Control`, so Chrome applied heuristic freshness and served a **stale `shared.js`** — which
  silently sent every question down the wrong language path. Static mounts now use
  `RevalidatedStaticFiles` (`no-cache, must-revalidate`; the existing ETag keeps it a cheap 304). On a
  clinic kiosk that staleness would silently disable Bangla audio after an update. For the same reason
  `tts.js` reads the active language from the **`lang` localStorage key shared.js already owns** rather
  than from a shared.js helper — no cross-file version skew.
- Rejected, each on verified grounds: **Piper** (checked `VOICES.md` — **no Bengali voice at all**);
  **`facebook/mms-tts-ben`** (real bn VITS model, but needs torch+transformers and is **CC-BY-NC-4.0**,
  i.e. non-commercial — parked as the natural fit for faculty **Requirement 2**, the quantized on-device
  model, which drops into this seam as one subclass); **edge-tts** (genuine bn-BD neural voices
  `NabanitaNeural`/`PradeepNeural`, free and key-less, but pulls the binary `aiohttp` dependency and
  ships question text to Microsoft — kept as a documented future provider for clinics that want
  naturalness over locality); **a Windows Settings Bengali voice** (impossible, see Context);
  **switching the kiosk to Edge** (may expose bn-BD online voices with zero code, worth trying, but it
  is per-machine host setup that helps neither Chrome nor a reproducible demo, and this seam makes an
  installed browser voice win automatically anyway).
- Status: **Accepted and implemented; audio pipeline VERIFIED end to end, human audibility still
  outstanding.** 247 → **277 tests pass, 0 skipped** (+30). espeak-ng 1.52.0 was installed on the
  Windows box via winget and **does carry a Bengali voice** (`bn`, `inc\bn`).
  Objectively measured, in this order:
  1. Engine: a Bangla question renders **exit 0, 158,098 bytes, valid RIFF/WAVE, 22,050 Hz, 3.58 s**.
  2. Endpoint: `GET /api/tts?lang=bn` → **200, `audio/wav`, 157,438 bytes, 3.57 s**,
     `Cache-Control: private, max-age=300`; `/api/config` → **`"server_tts": true`**.
  3. Kiosk: the KIOSK-2 "no Bangla voice" banner is now **hidden** (`banglaAudioAvailable() === true`)
     even though `banglaVoiceAvailable()` is still false — i.e. the fallback, not a browser voice.
  4. Playback really happens: `onend` fired at **3877 ms**, matching the 3.57 s clip — whereas the
     error path was measured at **22 ms**, so this is completed playback, not a silent failure.
  5. **The rule #1 integration proof:** with `toggleListening` spied, the mic opened **exactly once, at
     4110 ms**. `ttsSpeaking()` was true at 509/1525/2553/3583 ms and the mic stayed **shut** the whole
     time, opening only after audio ended plus `tts_guard_ms`. Without the predicate swap it would have
     opened at ~400 ms, in the middle of the AI speaking.
  6. English still speaks via the browser voice and delivers `onend`; `voice_loop=manual` and Type mode
     are unaffected; **S4's countdown/silence/barge-in code was not touched**.
  Also hardened during verification: `resolve_binary()` now falls back to the installers' well-known
  paths after `shutil.which`, because the Windows MSI updates the **machine** PATH and any process
  started before the install cannot see it — a clinic would otherwise get "not installed" forever.
  **LIVE RUN VERDICT (human, end of S29) — the seam PASSED, the voice FAILED:**
  ✅ **Mic timing PASS** (the echo guard holds against real audio) · ✅ **Countdown PASS** (S4 intact) ·
  ✅ **Transcript clean — "Yes": ZERO AI words in the patient's verbatim record, so rule #1 holds
  end-to-end with a server TTS provider** · ✅ **English PASS** · ❌ **Bangla voice: "Too robotic."**
  Two defects reported, both filed as **TTS-1 / TTS-2** in `context fixed problem 3.0.md`:
  (a) *"no gap when tts Bangla and English hear … sometimes 2 question hear at a same time"* — **root
  caused to `services/followup.py:45`**, which forces every M7 question into ONE bilingual string
  `"<Bangla> (<English>)"`, so TTS reads both halves in one breath. **Pre-existing since S25**, merely
  exposed by ADR-0049 (espeak `-v bn` also applies Bengali phonetics to the English half). Not an
  overlap bug — one utterance containing two questions.
  (b) the robotic voice → **ADR-0050**.
  So: **ADR-0049's architecture is retained and validated; only its first provider is rejected.**

## ADR-0050 — 2026-08-08 — Bangla TTS naturalness: keep the ADR-0049 seam, REPLACE espeak-ng as the default provider (provider undecided)
- Context: the S29 live run answered ADR-0049's one open question. Everything structural passed — mic
  timing, the S4 countdown, English audio, and critically **transcript clean = zero AI words (rule #1)**.
  The human's verdict on the voice itself was **"Too robotic"**, with the explicit goal *"i want make it
  like human not too robotic"*. espeak-ng is a **formant synthesizer**, so this is **inherent, not
  tunable**: `TTS_SPEED_WPM` and voice variants change speed and pitch, never naturalness. No amount of
  configuration will satisfy this requirement.
- Decision (**the part that is settled**): the **provider seam introduced by ADR-0049 stays exactly as
  built** — it is doing its job, and this is the swap it was designed for. Replacing the voice is **one
  new `TtsProvider` subclass plus a `TTS_PROVIDERS` entry**: no route change, no frontend change, no
  schema change, and no risk to S1–S4. **espeak-ng is demoted, not deleted** — it remains the offline,
  zero-dependency, no-network fallback (and the Arch path, ADR-0040), which is worth keeping precisely
  because it is the only option that never sends patient-derived text anywhere.
- **DEFERRED — the provider itself is NOT chosen. Do not assume one.** Researched in S29:
  1. **edge-tts** — real `bn-BD` neural voices (`NabanitaNeural` female / `PradeepNeural` male), free,
     no API key, natural Dhaka accent. Costs: a binary `aiohttp` dependency (breaking the "all
     pure-Python wheels" property), an internet dependency at the kiosk, and **it sends the question
     text to Microsoft**.
  2. **`facebook/mms-tts-ben`** — real neural VITS, fully local. Costs: torch + transformers (heavy on a
     CPU-only box) and **CC-BY-NC-4.0**, i.e. non-commercial only — acceptable for a thesis, not for a
     deployed clinic.
  3. **Microsoft Edge as the kiosk browser** — may expose Microsoft's online `bn-BD` voices with zero
     code, and the seam already prefers a browser voice automatically. **Unverified**; per-machine host
     setup; helps neither Chrome nor a reproducible demo.
- ⚠ **The rule #4 trade-off must be decided consciously, not slipped in.** M7 questions are DERIVED from
  what the patient said, which is exactly why ADR-0049 chose a local engine. Options 1 and 3 export
  patient-derived text to a third party. Choosing naturalness over locality is a legitimate call for a
  research prototype on synthetic data — but it is the **human's** call and must be recorded here, and it
  changes what may be said about privacy in the thesis.
- ⚠ **Overlaps faculty Requirement 2** (quantized on-device Bangla STT/TTS), which is the principled
  long-term answer and now has a seam waiting for it. Next session must decide whether this is a 3.0
  quick win (edge-tts) or folds into Req 2.
- Status: ~~Proposed~~ → **ACCEPTED and IMPLEMENTED (S30, 2026-08-08).** ADR-0049 remains **Accepted**
  (its seam, its 503-not-silence contract, its `ttsSpeaking()` echo guard and its static-asset
  `no-cache` fix all stand); only its default provider is superseded.

### S30 resolution — the human chose **edge-tts**, and a **local fallback**
- **⚠ One fact above was WRONG and it changed the comparison.** This ADR framed edge-tts's cost as a
  *"binary `aiohttp` dependency"* and never checked its license. Verified in S30 from PyPI metadata:
  **edge-tts 7.2.8 is LGPL-3.0** — used as an ordinary pip-installed library that imposes **no
  copyleft on this project's own code and carries no non-commercial clause**. Meanwhile
  `facebook/mms-tts-ben` is **CC-BY-NC-4.0** (confirmed on the HF model card): non-commercial only,
  which bars a real clinic deployment. **On licensing, the option this ADR described as the safe local
  choice is the more restrictive one.** Also: `requirements.txt` already ships a binary dependency
  (`ddgs` → `primp`, documented in the file), so "all pure-Python wheels" was already qualified and
  `aiohttp` breaks no property that was still intact.
- **Provider decision: `edge` (Microsoft neural `bn-BD`) is now the DEFAULT**, with espeak-ng
  **demoted, not deleted** — still selectable via `TTS_PROVIDER=espeak` and still the automatic
  fallback. Rejected: `facebook/mms-tts-ben` (CC-BY-NC-4.0 + torch/transformers ≈ 2–3 GB on two
  CPU-only boxes) and gTTS (MIT and pure-Python, but an unofficial endpoint and the same privacy cost
  for a less natural voice).
- **⚠ RULE #4 DECISION, MADE EXPLICITLY BY THE HUMAN — this is the part that matters for the thesis.**
  M7 questions are **derived from what the patient said**, and this provider **sends that text to
  Microsoft**. That cost was accepted knowingly for a research prototype running on synthetic data.
  The reasoning that tipped it: the system **already** sends the patient's *actual audio* to Google via
  the Web Speech API (rule #4 says so itself), so this adds a second processor of **strictly less
  sensitive, derived text** rather than crossing a new boundary. **It still limits what the thesis may
  claim about privacy, and that claim must be written accordingly.** A deployment that cannot accept it
  has a one-value escape hatch: `TTS_PROVIDER=espeak`.
- **Failure behaviour (also the human's choice): fall back to espeak-ng, don't go silent.** A network
  voice can fail at the worst moment, and for a clinic kiosk a robotic question beats a silent one. The
  chain is primary → local → `TtsUnavailable`. If BOTH fail the error **names both providers** (a clinic
  debugging silence must not be told only about the fallback), the route still returns **503, never a
  silent 200**, and the fallback is logged at **WARNING** — a clinic quietly running on the robotic
  voice for a week is exactly the silent degradation this project keeps refusing to ship.
  `TTS_LOCAL_FALLBACK=false` restores ADR-0049's original bare-503 contract.
- **The seam held.** Adding the provider was one `TtsProvider` subclass (`services/tts/edge.py`) + one
  `PROVIDER_FACTORIES` entry + `.env` settings — **no route change, no frontend change, no schema
  change, no Alembic migration.** Microsoft returns **MP3, not WAV**, and that needed nothing extra
  because the ABC already carries `media_type` per provider through to the `Response`, and `<audio>`
  plays MP3 natively. Two small generalisations were needed and are worth noting: `MAX_TEXT_CHARS`
  moved from `espeak.py` to `base.py` (it is the *endpoint's* contract — importing it from a specific
  engine made a local binary's constant the API's limit by accident), and availability became
  `TtsProvider.available()` (default True) instead of a duck-typed `resolve_binary` probe, because
  "is the engine present?" is only answerable for a *local* engine. `available()` deliberately does
  **not** touch the network: it runs on every kiosk page load.
- Verified in S30: **318 tests pass, 1 skipped** (was 297). The new `test_tts_edge_provider.py` (21) is
  **offline by default** — every network call is monkeypatched, because a suite that needs the internet
  fails in a lab with no wifi; the single real network test is opt-in via `TTS_LIVE=1` and passed.
  Live through the running server: `bn` and `en` both return `audio/mpeg` in **~0.8 s**, playback
  completed at **3013 ms**, and `ttsSpeaking()` was **true throughout** — so the S3 echo guard still
  holds against the new provider's network latency (rule #1). The `<audio>` element was observed
  requesting **only the Bangla half** (`/api/tts?lang=bn&text=আপনার জ্বর কত দিন ধরে?`), i.e. ADR-0051
  and this ADR compose correctly.
- ⚠ **Still unproven: naturalness.** Bytes, MIME type, latency and completed playback are measured;
  whether the voice sounds human to a Bangladeshi patient is the human's live listen, still pending.
- Faculty **Requirement 2** (quantized on-device Bangla STT/TTS) is unchanged and still the principled
  long-term answer; `facebook/mms-tts-ben` remains its natural candidate, and it now drops into this
  same seam as one more subclass.

#### Amendment (S30, later the same day) — **option 3 is now DISPROVEN, and it strengthens this ADR**
Option 3 above ("Microsoft Edge as the kiosk browser — may expose Microsoft's online `bn-BD` voices
with zero code; **unverified**") was tested against **real Microsoft Edge 151.0.4129.72** and is
**FALSE**. Edge exposes **26 voices across 21 languages and NOT ONE Bengali voice** (`bnVoices: []`;
languages present: de, en×5, es×2, fr×2, it, ja, ko, nl, pl, pt-BR, ru, tr, zh×3). Microsoft's
**browser** ships no Bengali voice even though Microsoft's **edge-tts service** — which this ADR's
chosen provider calls — has `bn-BD-NabanitaNeural` and `bn-BD-PradeepNeural`. Same vendor, different
surface. **Consequence:** in Edge, `_pickVoice('bn')` returns null and the ADR-0049 chain falls through
to provider 2, so **the server-side `edge-tts` provider is the Bangla route in Edge exactly as it is in
Chrome** — there is no browser-dependent divergence to design around, and "switch the clinic to Edge"
was never a real alternative to this ADR. Edge also reports `canPlayType('audio/mpeg') = "probably"`,
so it plays this provider's MP3 output. Recorded in `test_log.md` (2026-08-08, Edge compatibility
probe). ⚠ This amendment concerns **TTS only**; whether Edge's **STT** backend supports `bn-BD` is a
separate, still-**unproven** question tracked in `current_task.md`.

## ADR-0051 — 2026-08-08 — TTS-1: speak ONE language (the active UI language), display BOTH
- Context: the S29 live listen reported *"there are no gap when tts Bangla and English hear . some
  time 2 question hear at a same time this is confusing"*. **Root-caused, not guessed:** the M7 prompt
  in `backend/app/services/followup.py` asks the model for
  `"question": "<Bangla question> (<English question>)"`, so **every question is a SINGLE string
  containing both languages**. A synthesizer reads it in one breath. This is not an overlap bug and not
  caused by ADR-0049 — it has existed since S25; espeak-ng merely exposed it, because `-v bn` also
  applies Bengali phonetics to the English half.
- Decision (**the human chose option (a)**): **speech gets only the half matching the active UI
  language.** Option (b) — both halves separated by a real pause — was rejected: it adds ~1 s per
  question, and the target user is elderly or non-technical, so it works against ADR-0048's explicit
  "minimize clicks, waiting and complexity" priority.
- **The fix is TTS-ONLY, and that boundary is the point of this ADR.** The stored `system` utterance
  and the on-screen bubble keep the **full bilingual string, unchanged**: `followup.py` stores
  `question_text` verbatim, and ADR-0028 makes the on-screen text the fallback for anyone who cannot
  hear the audio — so it must never shrink to whatever happened to be spoken. `followup.py` itself was
  deliberately NOT touched; returning the halves as separate server fields would change the M7 contract
  and what the medic/doctor portals display — a much larger change nobody asked for.
- Implementation, and why it is shaped this way:
  1. **One entry point.** `spokenHalf(text, short)` is applied inside `speak()` in
     `frontend_shared/tts.js`, not in `askAloud()`. Doing it at the call site would have missed the
     resume-question path and the assistant replay button.
  2. **Both providers get the split half** — `new SpeechSynthesisUtterance(speech)` AND
     `encodeURIComponent(speech)`. Splitting only the browser path would leave the defect fully alive
     on Windows, where the server path is the ONLY Bangla route (ADR-0049).
  3. **Conservative pattern, deliberately.** It matches only a Bangla-script head followed by a
     TRAILING parenthesised Latin-script tail. A monolingual parenthetical ("fever (above 100F)"), a
     Bangla parenthetical, nested parentheses, or a `(...)` that is not at the very end all fail to
     match and are spoken **whole**. The failure mode of a splitter is speaking LESS than the question,
     so when it is unsure it loses seconds, never words.
  4. **`verbatim: true` opts out**, and the per-bubble 🔊 on a PATIENT bubble uses it: those are the
     patient's own captured words, and reading back only part of what someone said would be a rule #1
     defect in spirit, even though nothing stored changes.
- Consequences: the patient hears a shorter, single-language question; the screen still shows both
  languages, so a bilingual reader loses nothing and the cannot-hear-the-audio fallback is intact. A
  question the pattern cannot confidently split is spoken exactly as before — the old behaviour is the
  safe default, not an error state.
- Verification: **297 tests pass, 0 skipped** (was 277). `backend/tests/test_tts_bilingual_split.py`
  (20 tests) **extracts the shipped regex literal from the served `tts.js` and runs it**, so the rule is
  exercised rather than asserted about, and separately pins that the stored text, the on-screen bubble
  and the M7 prompt are unchanged. Cross-checked in a real JS engine: Chrome's own `spokenHalf` agrees
  case-for-case on 8 inputs, and `/api/tts` was observed receiving only the Bangla half.
- Status: **Accepted (code shipped). ⚠ The human has NOT yet heard it** — the tests prove which string
  reaches each provider, not that it sounds right. Independent of ADR-0050 (TTS-2, voice naturalness),
  which remains **Proposed** and unstarted.

## ADR-0052 — 2026-08-11 — Faculty-demo cycle: required pre-screening info is server-gated; identity (name/age/area) lives OUTSIDE the 10 fields
- Decision (the human's, recorded during the F1–F6 build):
  (a) **The 10-field `summary_fields` contract stays byte-identical.** Patient name, age and the
      body/health **area** are required information, but they are NOT promoted to fields 11/12.
      Name and age use the existing `patients` columns; the area gets its own key
      `case_profiles.entities["problem_area"]` — beside `summary_fields`, the same pattern
      `suggested_condition` already uses (ADR-0036). Rejected: extending to 12 fields, which would
      ripple through `SUMMARY_FIELD_KEYS`, `staff.js`, `visit_docx.py`, `report.py`, the completeness
      math and every stored row.
  (b) **"Required" has two kinds, not one.** `MUST_HAVE_VALUE` (main_problem) must carry text;
      `MUST_HAVE_BEEN_ASKED` (onset, symptom details, medicines, allergies) must have been PUT to the
      patient but may legitimately end empty. The human's rule: *"do not artificially force every one
      of the 10 fields to contain an answer when a field is genuinely not applicable."* Forcing a
      value would push a patient into inventing one, and an invented answer in a medical record is
      worse than an empty one.
  (c) **The gate is server-side** — `services/requirements.py` is the ONE definition, served by
      `GET /api/visits/{uuid}/readiness` and enforced by `POST .../submit?require_complete=true`.
      The kiosk hides Confirm & Submit on the same verdict, so screen and server cannot disagree.
  (d) **`require_complete` is opt-IN, not the default.** The same endpoint serves staff/walk-in paths
      that never ran the kiosk interview and legitimately submit partial cases; making it
      unconditional would block them and would have forced three unrelated test fixtures
      (`test_report_review`, `test_suggested_condition`, `test_risk_override`) to stop modelling
      sparse cases. **The kiosk always sends it.** ⚠ Known limitation, accepted deliberately: a client
      that omits the flag skips the check. The threat model here is a patient pressing Next, not a
      hostile client.
  (e) **The resume loop gets its OWN budget** (`followup_resume_max_questions = 8`) on top of
      `followup_max_questions = 5`. They shared one cap of 5, which the main loop spent entirely — so
      the loop that exists to fill gaps routinely had zero questions left. No schema change: the
      resume scope simply compares against `main + resume`, so questions need no scope column.
  (f) **The resume scope names the field; the model does not choose it** (F2). M7's echoed
      `target_gap` used to be "repaired" to `remaining[0]` whenever it wasn't an exact key, which
      filed the question against a DIFFERENT field — the asked field stayed "unasked" and was asked
      again, while an unasked field was marked answered and never revisited. That is the
      question/answer mismatch the human reported. The server now puts the field in the prompt and
      records that same field, on the JSON-salvage path too.
  (g) **Requiring identity is only safe because it is askable.** The kiosk's `INTAKE_SCRIPT` asks
      area → name → age → free description, and re-asks any of the three on the review screen via the
      existing resume dock. A requirement nothing can ask about would trap the patient; a test pins
      that every `IDENTITY_REQUIREMENTS` key has a matching script entry.
- Why: requirements 3A/3B/3C/6 of the faculty-demo list. Inspection showed the follow-up loop was
  ALREADY context-aware (M7 receives the whole conversation, the gap list and the asked list), so the
  work was never "replace the questionnaire" — it was to give M7 the two contexts it lacked (age,
  area) and to stop the budget starving the gap-filling loop.
- Rules preserved: raw utterances still insert-only and verbatim (rule #1) — the scripted opening is
  ordinary turns through the SAME endpoint, no second pipeline (ADR-0048); no diagnosis added
  (rule #2) — the area prompt says explicitly *"this is a location, not a diagnosis"*.
- Status: Accepted (code shipped, 392 tests). Alembic unchanged at **0012**.

## ADR-0053 — 2026-08-11 — F5: identification by voice on the existing engine; "a Unicode decimal digit is a digit"

- Context: the faculty demo flow is *speak the phone number -> speak the OTP -> interview*, but the
  two identification screens were keyboard-only, and the two languages DISAGREED about Bangla
  digits in opposite directions. Python's `re.sub(r"\D", "", ...)` is Unicode-aware, so it KEPT
  `০১৭...` and the ASCII `startswith("880")`/length checks below it then failed -> `ValueError`
  -> HTTP 400. JS `replace(/\D/g,'')` is ASCII-only, so the same digits were SILENTLY DELETED as the
  patient typed them into an OTP box. Neither was a strictness decision; both were accidents of one
  regex escape meaning different things in two languages.
- Decision (a) — ONE cross-language contract: **a decimal digit is a digit whatever script it is
  written in.** Server: `to_ascii_digits()` in `db/repository_visits.py` folds via
  `unicodedata.decimal` (the Nd category — NOT `str.isdigit()`, which would read a `2` out of `m2`).
  Kiosk: `unicodeDigit()`/`asciiDigits()` fold ASCII + Bangla. The server is deliberately the MORE
  permissive of the two: it must never be the thing that rejects a valid number.
- Decision (b) — identification reuses the ONE recognizer. Two more entries in the `DOCKS` map
  (`phone`, `otp`) plus `state.identifyStep` and two branches at the single routing point in
  `stopListening()`. The human's explicit regression rule was "do NOT build a second recognizer";
  the payoff is that S3's echo guard, S4's confirmation countdown, S2's Speak/Type switch and S31's
  terminal-error handling all apply to identification with no new logic. The identification docks
  declare NO `fallback` row on purpose — the number field and the OTP boxes are simultaneously the
  typed path and the display of what was heard, so they stay visible in voice mode.
- Decision (c) — the two screens are deliberately ASYMMETRIC. A spoken PHONE NUMBER is read back
  (large, grouped, in the local 11-digit form, spoken digit-by-digit) and requires an explicit
  confirmation tap: a wrong digit here sends the patient's verification code to a stranger's
  handset, and nothing about that is self-correcting. A spoken OTP fills the six boxes and is handed
  straight to F1's existing `maybeAutoVerify()`: a wrong code is rejected, cleared and re-asked by
  code that already exists, so a confirmation step would cost a tap and buy no safety (ADR-0048's
  "minimize clicks"). A TYPED number is not re-confirmed either — the patient can already see it.
- Decision (d) — the phone screen is TAP-to-start; auto-listen begins at the OTP screen. That screen
  is the kiosk's first paint, where no user gesture has happened: arming a recognizer there raises
  the microphone permission prompt unprompted and lets Chrome block the TTS. The one tap is the
  gesture that unlocks audio and permission for the whole session. This is a deliberate, narrow
  exception to ADR-0048's "the mic opens itself", taken to protect it everywhere else.
- Decision (e) — digit-WORD vocabulary is single digits 0-9 only, in Bangla and English, plus the
  spelling variants the recognizer really returns. English homophones (`to`/`too`/`for`/`won`/`ate`)
  and Bangla compounds (এগারো, তেইশ) are excluded ON PURPOSE: a MISSED digit shows up in the
  read-back and the patient fixes it, whereas an INVENTED digit reads as correct.
- Rules preserved: rule #1 is untouched — identification digits are not clinical utterances and are
  never stored as raw text; no visit exists yet at this point in the flow, which is exactly why
  `activeDock()` and `stopListening()` check `identifyStep` FIRST. Typing remains available on both
  screens in both modes (ADR-0048). Rule #4 unchanged: the Web Speech API already sends audio to
  Google, and this adds phone/OTP digits to what it hears -- worth stating plainly in the thesis's
  privacy section, and one more reason `OTP_CHANNEL=dev` + synthetic numbers stay the dev default.
- Two defects found only by EXECUTING the shipped code in a browser, not by any assertion:
  (1) `[^\p{L}\p{N}]+` shredded Bangla words at their own vowel marks (category M, not L/N), so
  the eleven-digit sentence returned "118" -- `এক` and `আট` are the only two digit words with no
  combining mark; (2) `ছয়` and `নয়` each have two encodings that render identically (precomposed
  U+09DF vs ya+nukta) and are `!==` in JS, so one spelling silently dropped a digit. Fixed by
  `\p{M}` in the split class and an NFC fold; both are now test-pinned.
- Status: Accepted (code shipped, **438 tests pass, 1 skipped**). Alembic unchanged at **0012** — no
  schema change. NOT proven: what Chrome's `bn-BD` recognizer actually returns for spoken digits.
  No microphone was ever involved; that gate is the human's live run.

## ADR-0054 — 2026-08-11 — P1/P2/P3: the avatar's state is DERIVED not pushed; elderly sizing is kiosk-scoped; validation is reported in three tiers

- Context: the faculty-demo list ended with three items that are all about the patient UNDERSTANDING
  the system rather than about new clinical capability — a robotic doctor, an elderly-friendly
  interface, and evidence that questions suit the patient's age.
- Decision (a) — **the avatar may never be able to lie.** Its five live states are DERIVED, in one
  reader (`currentAvatarState()`), from the same variables the rest of the kiosk already acts on:
  `listening`, `ttsSpeaking()`, `state.busy`. There is deliberately NO `setAvatarState('speaking')`
  at call sites, because a scattered setter drifts out of sync with the microphone and the one
  question this component answers is "is it my turn?". The precedence is a contract, not a
  preference: **listening > speaking > processing > idle.** Listening outranks everything because a
  patient who believes the kiosk stopped listening stops talking mid-answer — a rule #1 defect.
  Speaking outranks processing because `state.busy` stays TRUE across `assistantSays()`, so a
  busy-first test would caption a talking doctor with "please wait". Only `done` and `error` may be
  PUSHED, since no live variable can express "finished" or "failed", and `error` therefore expires
  with its 8 s banner so a recovered patient is not told the kiosk is still broken.
- Decision (b) — **polled, not evented.** Neither speech path emits a "still speaking" event:
  speechSynthesis fires only start/end, and the ADR-0049 server-TTS fallback is an `<audio>` element
  whose request latency is part of speaking. A 200 ms poll of the SAME predicate the S3 echo guard
  uses is what keeps the face and the microphone agreeing. `refreshAvatar()` writes nothing when the
  state is unchanged, so CSS animations are never restarted.
- Decision (c) — **CSS-only 3D, no library and no asset.** Hardware is CPU-only and the kiosk must
  work offline, so the doctor is built from transforms, gradients and keyframes. "3D" enhances the
  avatar; it does not become an application. Every state also carries a NON-COLOUR cue (mouth
  motion, pulse rings, scanning eyes, flipped mouth) because colour alone fails a low-vision
  patient, and `prefers-reduced-motion` keeps the meaning via the lamp colour and the status text.
- Decision (d) — **elderly sizing is scoped to `kiosk.html`, NOT `shared.css`.** shared.css is the
  design system for all three portals; enlarging `.btn` there would inflate the medic and doctor
  dashboards, which trained staff use on desktops. The patient is the one who is elderly and
  non-technical, so only the patient portal grows: 52px buttons, 54px inputs, 60px OTP boxes,
  1.12rem chat, 44px minimum touch targets, and visible focus rings on every control.
- Decision (e) — **two responsive axes are treated as different problems.** Short screens run out of
  VERTICAL room and push the primary action under the fold (`max-height: 820px`); narrow screens run
  out of HORIZONTAL room and overflow the six OTP boxes and the two-column summary
  (`max-width: 620px`). One breakpoint cannot serve both.
- Decision (f) — **age-appropriateness is reported in THREE EXPLICIT TIERS, and tier 3 is not
  claimed.** Tier 1 (deterministic code) and tier 2 (prompt content) are proven by the suite. Tier 3
  — that the model OBEYS — cannot be proven by asserting against a stub we wrote ourselves, so it is
  left unproven with an opt-in `M7_LIVE=1` probe instead of a fake green test. The project's
  standing rule that automated tests must not be reported as model validation is now structural.
- Rules preserved: rule #1 — the avatar reads state and never writes to a transcript; identification
  and avatar work add no stored text. Rule #2 — the no-diagnosis constraint is asserted
  unconditionally across both age tiers. The 10-field summary shape is age-invariant, proven by
  running the real requirements gate for a 19- and a 78-year-old and comparing what it demands.
- Status: Accepted (code shipped, **480 tests pass, 2 skipped**). Alembic unchanged at **0012**.
  NOT proven: any microphone behaviour, and whether the model's questions actually differ by age.

## ADR-0055 — 2026-08-12 — S34: a spoken answer is READ BACK before it is stored; the review submits itself on one shared countdown

- Context: the human ran the kiosk by hand and reported four things — a spoken phone number showed
  the WORDS rather than the digits; there was no way to hear what the machine had understood of an
  answer, or to correct it; the review screen could only be READ, never heard; and a finished review
  sat there until somebody pressed a button. Underneath the first was a real defect, and underneath
  the second a real gap: between S4 and now, a captured answer went from the recogniser straight into
  the patient's permanent record with no human confirmation anywhere in the path.

- Decision (a) — **a decimal digit is a digit in whatever SCRIPT the recogniser writes it, including
  a transliteration.** ADR-0053 established the character-level half. The word-level half was still
  half-done: the kiosk listens at `lang='bn-BD'` (it must — every clinical answer is Bangla), and a
  Bangla-language recogniser handed "one two three" does not return Latin text, it returns
  `ওয়ান টু থ্রি`. So the ten English keys in `SPOKEN_DIGITS` could never be hit by a patient SPEAKING
  English digits; they only ever matched typed or pasted text. Ten transliterations were added. The
  safety rule for adding them is unchanged and is what keeps the map honest: a word is only mapped if
  it cannot arise in ordinary speech. `ও` — "and", "he/she", one of the commonest words in Bangla, and
  what an English "oh" transliterates to — is deliberately NOT mapped. **A missed digit is caught by
  the read-back; an invented one reads as correct.**

- Decision (b) — **the identification docks show the DIGITS, and keep showing the words.** The
  transcript is the evidence and is never rewritten (rule #1). Beside it now sits a derived reading
  produced by the same `digitsFromSpeech()` that will produce the value, spaced out (`0 1 7 1 5`) so
  an elderly patient can check one digit at a time instead of parsing their own sentence back. It is
  display-only: nothing is stored, sent, or normalised differently because of it.

- Decision (c) — **a SPOKEN clinical answer is read back and must be accepted before it is stored; a
  TYPED one is not.** The read-back shows the words large and verbatim, speaks them back in the
  capture language (`bn-BD`, `verbatim: true` — reading back half an answer would be a rule #1
  defect), and offers a tick and a cross. Nothing reaches the server until the tick. A typed answer is
  exempt because the patient is already looking at their own text, and a confirmation there would be a
  tap that buys nothing (ADR-0048's "minimize clicks"). ⚠ This DOES cost one tap per spoken turn,
  which is a real regression against the zero-touch goal — so `VOICE_ANSWER_CONFIRM=false` restores
  the S25-era flow exactly, the ADR-0045 pattern of never deleting the previous behaviour. The default
  is ON: the target patient may not be able to read the chat bubble that was previously the only way
  to notice a mis-recognition.

- Decision (d) — **the gate lives at ONE place: the spoken branch of `stopListening()`.** Not inside
  `submitPatientTurn()`/`submitResumeAnswer()`, which the typed paths also call, and not as a second
  question/answer route. `acceptAnswer()` re-enters the SAME calls with the SAME `source`, so
  ADR-0048's one-pipeline rule is untouched and the resume dock inherits the whole thing for free.

- Decision (e) — **an unusable capture is asked again, never guessed at, and this is NOT switchable.**
  "Unusable" is decided locally and deterministically — no letter and no digit — because that is
  something the kiosk can be right about offline; anything richer would be a heuristic judging a
  patient's answer, which is the doctor's job (rule #2). Silence, or noise, re-asks the SAME question
  through `askAloud()` (which reopens the mic in auto mode). Before this, an empty spoken turn fell
  through `if (sendTurn && text)` and did nothing at all: the mic closed, no question repeated, and the
  patient waited for a kiosk that had silently given up. ⚠ **Overlap with Step S5, stated plainly:**
  S5's "empty-submit guard / no-speech re-prompt" covers the same ground. Only the part the human's
  Phase 2 required is built. S5's distinguishing content — the `no_speech_ms` watchdog, the
  `max_answer_ms` cap, and permission/visibility recovery — is untouched and remains deferred.

- Decision (f) — **the review screen can be HEARD, and it is the derived summary that is spoken.**
  Every filled card gets a speaker button (labelled, so "None" is never read out with no subject),
  plus a read-through of all of them. `verbatim: true` on both, so TTS-1's bilingual split cannot
  halve a value. This reads the DERIVED `summary_fields`, never the raw transcript — the review screen
  shows what the doctor will receive, and the read-aloud must not diverge from what is on the card.

- Decision (g) — **the review submits itself after 60 seconds, but only while it legitimately can.**
  The clock and the Confirm & Submit button share ONE verdict (`updateSubmitVisibility`), so it can
  never count down toward a button that is not there or a submit the server would refuse; any manual
  action cancels it; `startReviewTimer()` is idempotent so re-entering the screen cannot stack a second
  timer; and `confirmSubmit()` gained a `submitting` re-entry guard so a timeout racing a tap produces
  exactly one POST (verified live: timeout + two taps = 1 submit). `VOICE_REVIEW_TIMEOUT_MS=0` disables
  it for a clinic that wants the patient in full control.

- Decision (h) — **one reusable ticker, and the S4 endpointer is deliberately NOT folded into it.**
  `startTicker()` is extracted and the 5-second auto-logout countdown is moved onto it, which is the
  proof it is reusable rather than a wrapper written for one caller. The S4 silence endpointer looks
  like the same thing and is not: its deadline is RESTARTED by every recognition result, and that
  restart IS the anti-clipping guarantee. Rewriting a rule #1 safeguard to share code with a UI clock
  would trade a real guarantee for a smaller diff. Reuse where it is safe; leave the safety-critical
  countdown alone.

- Decision (i) — **the kiosk page is bounded to the viewport; the thread and the summary are the
  scrollers.** Measured, not assumed: `shared.css` gives `body` `min-height: 100vh` and no height, so a
  handful of chat bubbles grew the document to 1538px inside a 694px viewport, `.chat-thread`'s
  `flex: 1` was handed unbounded space and never scrolled, and the whole voice dock — mic, Done, and
  the new read-back — sat below the fold. Auto-scrolling a thread that is not the scroll container
  cannot help. Scoped to `kiosk.html` for the same reason ADR-0054 scoped the elderly sizing there:
  the staff dashboards are long documents and SHOULD scroll as pages.

- Rejected: (1) **a spoken yes/no confirmation** instead of two buttons — it needs a voice-driven
  control loop, which is Step S5 / Requirement 3 territory and would have been built here by the back
  door. (2) **Auto-accepting the read-back after a countdown** — it reintroduces exactly the silent
  storage of an unheard answer that this ADR exists to remove. (3) **Reading the RAW transcript aloud
  on the review screen** — the review shows the derived summary, and speaking something else would let
  the patient approve one thing while hearing another. (4) **Putting the clock in `shared.css`, or
  converting the S4 countdown to the shared ticker** — see (h)/(i).

- Rules preserved: **rule #1** — the read-back displays and speaks the patient's words verbatim,
  carries no `data-en`/`data-bn` so a language toggle cannot overwrite them, and a REJECTED capture was
  never stored, so rejecting it edits nothing. **Rule #2** — "unclear" is a presence-of-characters
  test, not a judgement about the answer's content. **Rule #4** — no new data leaves the device; the
  read-back is local TTS on the same seam as every other spoken line.
- Status: Accepted (code shipped, **547 tests pass, 2 skipped, 0 failures**; was 480). Alembic
  unchanged at **0012** — no schema change, no migration.
  NOT proven: anything involving a real microphone. Every voice result in this session comes from
  feeding the recogniser's own buffer in a browser engine, as in S33.

## ADR-0056 — 2026-08-12 — S35: confirmation is SPOKEN, on one vocabulary; one clock in the header; the question prompt is told what it already knows

- Context: a second round of manual-testing findings. Two of them are the same complaint from
  different ends of the flow — the patient still needs a mouse to confirm anything — and two are the
  same layout complaint: the countdown cannot be found. One correction first, because the brief was
  wrong about the code: **the phone read-back did NOT auto-accept after ten seconds.** It had no
  timer at all; ADR-0053 deliberately required a tap. Verified by inspection before anything changed.

- Decision (a) — **YES and NO are spoken, and there is ONE vocabulary for both places they are
  asked.** `parseConfirmation()` serves the per-answer read-back (ADR-0055) and the final review.
  ⚠ This **supersedes ADR-0055's "Rejected (1)"**, which turned a spoken yes/no down as Step-S5
  territory. That was wrong on the facts: S5 is timers and permission recovery, and a yes/no verdict
  needs neither. The human overruled it, and the reasoning holds — a review screen that can only be
  approved with a mouse is not voice-first.

- Decision (b) — **the matching is explicit, and ambiguity is a verdict-free outcome.** Two rules:
  an utterance is a confirmation only when EVERY word in it is one the vocabulary knows, and where a
  YES word and a negation both appear, NO wins. The first is the direct answer to "do not assume
  every sentence containing না means NO" — a patient who is TALKING gets asked again rather than
  decided for. The second is what makes `ঠিক নাই` and `ঠিক না` rejections rather than agreement.
  The risk here is ASYMMETRIC and that is what shapes it: a missed confirmation costs one repeat; an
  INVENTED one stores an answer the patient was correcting, or submits a record they never approved.

- Decision (c) — **a verdict is routed before the clinical branches and is never stored.** One more
  branch at the same single routing point in `stopListening()`, after identification and before
  `holdForConfirmation()`. Otherwise the word "হ্যাঁ" would be POSTed as the patient's symptom.
  ⚠ It also forced REMOVING S34's `hideAnswerConfirm()` from `toggleListening()`: "the patient is
  speaking again, so they mean say-it-again" was a fair inference while the only reply was a tap, and
  a defect once the reply is speech — it cleared the pending answer between the mic opening and the
  verdict arriving. The rule did not disappear; it became an explicit word (`আবার বলি`) instead of an
  inference from the act of speaking.

- Decision (d) — **rejecting the review re-opens the EXISTING resume dock, it does not start a new
  flow.** `setResumeMode(null, entry)` already serves "a question that is not an M7 row", and
  `submitResumeAnswer()` already stores such an answer, re-runs intake, re-renders the summary and
  re-evaluates the loop. So "NO" costs one more entry in that map and no new pipeline, and the
  patient never leaves the review screen. The correction question is deliberately OPEN ("what would
  you like to correct?") — naming a card would mean asking them to read the screen.

- Decision (e) — **the phone read-back gains a visible 10-second window; the presentation is
  untouched.** ADR-0053's reasoning — a wrong digit sends the OTP to a stranger — still stands, and
  nothing about how the number is shown or read back changes. What changes is the DEFAULT when the
  patient does nothing: an elderly patient who does not know a press is expected used to sit in front
  of a kiosk that had silently stopped. `VOICE_PHONE_CONFIRM_MS=0` restores the tap-required rule
  exactly (ADR-0045's pattern). The guard against a double send is the state itself — `confirmPhone()`
  returns early without `pendingPhone` — rather than a flag that could be left set.

- Decision (f) — **ONE countdown clock, and it lives in the portal header.** S34 put it inside the
  review layout, so it existed only on that screen and only while that screen was scrolled to the
  top. The header sits OUTSIDE `.screen` (the element that scrolls, since ADR-0055 (i)), so the
  clock is at the top right at ALL times, cannot be scrolled away from, and cannot overlap anything
  — it is a flex item and the row reserves its width. `position: fixed` was rejected: taking the
  element out of flow is exactly how a floating clock lands on a heading at some untested width.
  Both countdowns write it through one renderer, with a PER-COUNTDOWN label, because "10 সেকেন্ড
  বাকি" and "10s to send" are different sentences rather than one string translated.
  Measured consequence, and the answer to the review's "first render jumps": the clock appearing no
  longer moves the review heading, title or grid by a single pixel (0/0/0/0 at 1280).

- Decision (g) — **M7 is told what it already knows, and that is all.** `collected_context()` is the
  exact mirror of `missing_summary_fields()` — same keys, same `field_has_text` predicate — and the
  system prompt forbids re-asking anything in it or in PATIENT CONTEXT (age, sex, area), and asks for
  CLARIFICATION of THAT SAME item when something is vague. ⚠ Deliberately NOT a decision system: it
  restates collected values, ranks nothing, names no condition, and does not choose the next field —
  the M6 gap list and the server-named field (ADR-0052) still own that entirely. A test asserts the
  block contains no evaluative language at all.

- Decision (h) — **TTS naturalness is pacing plus a neural voice, and nothing is claimed beyond
  that.** The engine question was settled by ADR-0050. What was left is that the strings handed to it
  are not written for speech: `spokenHalf()` leaves a bare clause with no terminator, a summary value
  is a fragment, a transcript has no punctuation at all, and every engine reads those flat.
  `speech_text()` adds a sentence-final terminator (`।`/`.`) and turns the em dashes and ellipses
  this project already uses as pauses into commas. It runs ONCE, in the service, so the primary and
  the fallback read the identical line. ⚠ It may never change a WORD — the read-back sends the
  PATIENT's own captured words down this path (ADR-0055), and a rewrite there would read back
  something they did not say. Pitch and volume are exposed but NEUTRAL by default: they are for a
  noisy room or a hard-of-hearing patient, not a "make it human" dial. **Acoustic quality is not
  tested and is not claimed** — that is a human listening judgement.

- Rejected: (1) **auto-accepting the ANSWER read-back on a timer** — unchanged from ADR-0055; it
  reintroduces storing something the patient never approved. Only the PHONE number, which is
  re-enterable and self-correcting via the OTP, gets a window. (2) **A looser yes/no match** (e.g.
  "any sentence containing না is NO") — it is the one change that could silently store a rejected
  answer. (3) **`position: fixed` for the clock** — see (f). (4) **Teaching `renderSummary()` about
  breakpoints** instead of the narrow-screen `span 1 !important` — a renderer that knows about
  viewport widths is a worse coupling than one `!important`.

- Rules preserved: **rule #1** — a verdict is never stored, a rejected capture was never stored, the
  read-back is still verbatim and still untranslated, and `speech_text()` cannot touch a word.
  **Rule #2** — "ambiguous" and "unclear" are presence-of-token tests, not judgements about content;
  `collected_context()` adds no clinical reasoning. **Rule #4** — no new data leaves the device; the
  TTS boundary is unchanged.
- Status: Accepted (code shipped, **622 tests pass, 2 skipped, 0 failures**; was 547). Alembic
  unchanged at **0012** — no schema change, no migration, no new dependency.
  NOT proven: anything involving a real microphone — including what a `bn-BD` recogniser actually
  returns for a spoken "হ্যাঁ", which is now on the critical path — and the acoustic quality of the
  paced TTS. Both are live-run questions.
