# current_task.md — What We Are Doing RIGHT NOW

> This is a small, throwaway snapshot. It gets **overwritten** every session.
> It is NOT a history log (that is `changelog.md`). It answers only:
> "If I open a brand-new Claude Code session, what do I need to know to continue?"

---

**Date:** 2026-07-03
**Phase:** Full-stack build — **backend + all three portals BUILT**; now verification + polish
**Module:** M1–M12 backend pipeline done (M13 store = the DB itself); M14 doctor UI done; M15 feedback stored

## Where we are right now
Session 8 built the whole reconciled system (see `changelog.md` Session 8 and
`agent_docs/reconciliation.md`):
- **DB:** Alembic head = `0009_audit_log`; all 15 tables from architecture.md exist and are
  applied to the real DB. Seeds: 1 clinic, 1 medic ("Medic Rahman"), 2 doctors, 1 admin.
- **Backend:** kiosk phone + stub OTP (`DEV_OTP=000000`) → visit; intake (M3/M4/M6, per-module
  free-API buckets + OpenRouter fallback, everything logged in `module_events`); follow-up loop
  (M7 Groq / M8 merge / M9 local); **M10 risk with the LOCAL red-flag rule that forces Critical
  even if every LLM is down**; M11 XAI (with deterministic fallback); M12 local report;
  submit→auto-assess→medic queue→assign→doctor queue→review('reviewed'); audit_log everywhere.
- **Frontend:** `/kiosk.html` (patient), `/medic/`, `/doctor/` — clinical-blue design (ADR-0029),
  bilingual EN/BN, TTS+STT wired. The OLD Module-1 transcript app at `/` is untouched.
- **Tests: 104 passing** (`pytest backend/tests/`). Red-flag recall is enforced per-phrase.

## Done since the main Session 8 build
- **ADR-0029 executed in docs:** CLAUDE.md frontend section now points at the clinical-blue
  system (`frontend_shared/shared.css`); `DESIGN-mintlify.md` marked SUPERSEDED. No longer pending.
- **First live Gemini call verified** (M2 correction on synthetic Banglish — correction-only,
  no translation/diagnosis; see test_log.md 2026-07-03 Session 8b).
- **⚠ Live-run key gap:** only `GEMINI_API_KEY` is set. **`GROQ_API_KEY` + `OPENROUTER_API_KEY`
  are EMPTY**, so M6 (gaps) and M7 (follow-up) — the Groq bucket — have NO provider and a full
  live intake/loop will 502 until a key is added. Everything passes offline (LLM faked).

## The one thing we are doing next
**Get a full live run working, in two independent parts:**

**Part 1 (either you or Claude, once a key exists):** add a **Groq** or **OpenRouter** key to
`backend/.env`, restart, then drive the pipeline with SYNTHETIC typed text (no mic needed):
create a visit → POST a couple of `/utterances` → `/intake` → `/followup/next` + `/answer` →
`/assess` → `/report`. Confirm real M3/M4/M6/M7/M10/M11 output + `module_events` provider rows.

**Part 2 (human only — needs a real microphone):** the voice kiosk run in Chrome
(spends a little quota — needs the keys above):
1. Start the server (port 8001), open `http://localhost:8001/kiosk.html`.
2. Phone → any BD mobile → OTP `000000` → speak a Bangla complaint → answer the follow-up
   questions by voice → check the 10-field summary → Confirm & Submit → watch the auto-logout.
3. Open `/medic/` → login → the case should be in the queue WITH a risk badge → edit a field →
   Assign Doctor → Submit & Forward.
4. Open `/doctor/` → login as that doctor → case in queue → check risk/red-flags/XAI panel →
   Accept & Write to EHR (or Override to Low-Risk).
5. Record in `test_log.md`: TC-V2 (was a bn-BD TTS voice available per OS?), TC-V3 (voice-only
   loop), TC-F2 (loop exits, no repeats), TC-R1 (say "বুকে ব্যথা" → tier must be Critical),
   TC-A1 (pull a key → fallback provider logged in `module_events`).

**After that:** per-visit report `.docx` export (M12 → the existing DocxWriter/documents seam),
then optional PDF, then Phase-1 faster-whisper. (The ADR-0029 doc rewrite is DONE.)

## Important environment notes
- Server: port 8001. Windows launch config is `backend (FastAPI + uvicorn)`; Arch is
  `backend-linux`. `.env` changes need a restart.
- **DEV_OTP=000000** (stub — no SMS). Patient phone lives in `patients.external_ref`.
- Alembic migrates at startup; NEVER delete the DB. Pre-migration backups:
  `backend/prescreener.db.pre-000{3,4,5,6,7}.bak` (gitignored).
- The Windows venv needed `pip install -r requirements.txt` this session (alembic was missing);
  if tests fail with ModuleNotFoundError, reinstall requirements.
- Tier codes on the wire are always low/medium/high/critical; labels (incl. "Moderate", Bangla)
  live ONLY in `frontend_shared/shared.js` TIER_LABELS.

## Reminders
- Raw words are never edited (rule #1) — staff edits touch only `summary_fields` (source
  becomes 'human'; M8 never overwrites human fields). The system never diagnoses (rule #2).
- Red flags: rule list in `backend/app/services/red_flags.py` — ADD phrases only, each with a
  matching TC-R1 test case; the rule must always be able to force Critical (rule #3).
- Never auto-run live LLM calls (quota + rule #4 synthetic-data-only). Tests fake the LLM layer.
- Plan first, one small step at a time (CLAUDE.md).
- Run (Windows): `.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Run (Arch):    `.venv/bin/python -m uvicorn backend.app.main:app --reload --port 8001`
- Tests: `pytest backend/tests/` (**104 passing**).
