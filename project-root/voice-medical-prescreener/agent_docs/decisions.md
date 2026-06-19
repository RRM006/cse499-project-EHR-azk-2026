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
