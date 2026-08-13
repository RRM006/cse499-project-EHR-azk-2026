# current_task.md — What We Are Doing RIGHT NOW

> This is a small, throwaway snapshot. It gets **overwritten** every session.
> It is NOT a history log (that is `changelog.md`). It answers only:
> "If I open a brand-new Claude Code session, what do I need to know to continue?"

---

**Date:** 2026-08-13 (end of Session 37)
**Phase:** **The staff-portal role cycle is CLOSED.** Both `/medic/` and `/doctor/` were audited as
ROLES and given the layer each was missing, plus a shared depth/motion layer. Everything built is
**derived and read-only**.
Test suite: **767 passed, 2 skipped, 0 failures** (was 723).
Alembic head: **0012 — `db/models.py` and `migrations/` are UNTOUCHED. Do not create a migration.**
No new dependency. New ADRs: **0058** (features + data ownership) and **0059** (the motion layer).
**No module changed status** — the work lands inside M14 and the medic side of the same staff layer,
both already ✅. **M15 stays 🟨.**
**NEW reference doc: `agent_docs/portal_roles.md` — read it before touching either staff portal.**

**⚠ Step S5 is STILL NOT implemented and must not be assumed. See the bottom of this file.**

---

## 🚦 THE NEXT STEP — **a HUMAN pass over the two staff portals**

The code side of S37 is complete and test-pinned. What no test can settle is whether the new
behaviour matches how this clinic actually wants to work. Two things need a person:

1. **Does the triage ordering match your intent?** The medic queue is now **worst tier first, then
   longest wait first**, and an **unassessed** case sorts *between* High and Medium (on the
   reasoning that "we do not know yet" is not "we know it is fine"). If a real desk would rather
   see, say, strict FIFO with urgency only as a badge, that is a one-line change to
   `TIER_ORDER` / `triage_sort_key` in `backend/app/services/triage.py`, not a redesign.
2. **Does the motion read as "clinical" or as "busy"?** Depth on cards, a stagger on the queue, a
   pop on a changed stat, and a pulse on the red-flag chip only. Anything that distracts should be
   said plainly — every effect lives in one file (`frontend_shared/motion.css`) and each is
   removable on its own.

### Setup
- Run: `.venv\\Scripts\\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Open **http://127.0.0.1:8001/medic/** and **http://127.0.0.1:8001/doctor/** in Chrome.
- No microphone is involved in any of this — S37 touched no voice code.

### The exact flow to walk
1. **Medic:** log in. Read the load strip (waiting / critical / high / not assessed / longest wait).
   Confirm the top of the queue is who you would actually take next.
2. **Medic:** open a case. The **Intake & Vitals** card is now at the top and works BEFORE you
   forward — record a weight and a BP and watch the handover check drop `vitals_missing`.
3. **Medic:** read the **Handover Check**. Confirm it is *advice*, not a gate: the Submit & Forward
   button must stay usable even when the card says "You can still add more".
4. **Doctor:** open an assigned case. Expand **Patient History** — prior visits, and prior
   prescriptions from every doctor with a working `.docx` link.
5. **Doctor:** Accept & Write to EHR. The case must **stay on screen**, the accept/override controls
   must disappear, "Consultation completed" must show, and **Write Prescription must still work**.
6. **Doctor:** switch the sidebar to **Completed** and confirm the case you just reviewed is there.
7. **Both:** toggle বাংলা and confirm nothing overflows or falls back to English.

### ⚠ The rule for next session
**Only change code if the walkthrough reveals a REAL issue.** Everything through S37 is complete and
test-pinned.

---

## Also open (the human's choice, not a queue)

1. **Rotate the 3 API keys** — HUMAN-only, still pending since S25, recommended before any public demo.
2. **Formal WER / precision-recall** on a labelled set — the thesis-evidence gap. S25's live run was
   qualitative.
3. **The mid-turn word-loss rule #1 decision** — what happens to a half-captured answer in
   `finalBuffer` when the tab is backgrounded or mic permission is revoked mid-answer. **This is
   yours to decide, and it is what BLOCKS the second half of Step S5.**
4. **The Edge run** — every live run so far has been Chrome only.
5. **Faculty future requirements** (`faculty_future_features.md`): quantized summary model,
   quantized STT/TTS, the fully voice-driven follow-up loop.

---

## ✅ What Session 37 shipped (settled — do not redo or re-derive)

- **NEW `services/triage.py`** — `waiting_minutes()` (pins offset-less SQLite UTC BEFORE arithmetic),
  `TIER_ORDER`, `triage_sort_key()`, `empty_field_keys()`, `human_verified_count()`,
  `handoff_checks()`, `queue_stats()`. Writes nothing.
- **NEW `services/history.py`** — `patient_history()` + `_medicine_names()`. Writes nothing.
- **NEW `schemas/triage.py`, `schemas/history.py`, `api/routes_history.py`** (registered in `main.py`).
- **`routes_dashboard.py`** — `scope` (`queue`|`recent`) + `sort` (`triage`|`recent`),
  `_queue_visits()` as the ONE queue definition shared by the list and the stats,
  `GET /api/dashboard/stats`, `GET /api/visits/{uuid}/handoff`, and `assign` recording the
  forwarding medic in `audit_log.actor_id`.
- **`schemas/dashboard.py`** — `DashboardItemOut` += `waiting_minutes`, `fields_filled`,
  `fields_total`, `fields_verified`, `assigned_doctor_name`; `AssignRequest` += optional `editor_id`.
- **NEW `frontend_shared/motion.css`** — staff-only depth/motion + role identity + staff breakpoints.
- **`frontend_shared/staff.js`** — skeleton / empty / error / search-miss states, `waitLabel()`,
  queue chips + tier rails, `setQueueScope()`.
- **`frontend_medic/index.html`** — load strip, Intake & Vitals BEFORE the referral, handover check,
  attributed forward.
- **`frontend_doctor/index.html`** — patient timeline + prescription history, Queue/Completed scope,
  review-state bar, `STATUS_LABELS`.
- **NEW tests:** `test_medic_triage.py` (18), `test_doctor_history.py` (10),
  `test_staff_portal_ui.py` (16). **No existing test was modified, weakened or deleted.**

## ⚠ Open gaps / honest caveats (carry these forward)

- **🟡 Real-mic status.** The human confirmed at the start of S37 that the real-microphone run of the
  **S33–S36** voice changes **was carried out**. ⚠ Exactly that far: **no per-claim results were
  supplied and none are documented**, and no defects came back. So do NOT repeat "no microphone has
  exercised S33–S36" (false), and do NOT upgrade the three specific S36 claims (the completion
  vocabulary, the eleven-digit phone stop, audibility) to "verified" — there is no recorded evidence
  for them. S25's itemised evidence stands unchanged.
- **S37's static-source tests prove wiring and containment, not appearance.** That every animation
  sits behind `prefers-reduced-motion` is mechanically proven; that the portals *look* clinical
  rather than busy is a human judgement and is not claimed.
- **A medic still cannot record "I checked this field and it is correct" without editing it.**
  Deliberately deferred (ADR-0058, Rejected 2): it needs new per-field state. `fields_verified`
  (count of `source == 'human'`) is the weaker signal shipped instead.
- **Nothing attributes a referral to an individual medic *retroactively*.** S37 records it going
  forward; historical rows have none, which is why `scope=recent&role=medic` is a **400 with the
  reason**, not a guess.
- **⚠ A measurement trap, recorded because it will recur:** when the Browser pane is not displayed
  the page does not composite and **CSS transitions freeze mid-flight** — `getComputedStyle` returns
  stale colours and can make a correct stylesheet look inverted. Inject
  `*{transition:none!important;animation:none!important}` before measuring.
- **⚠ Two synthetic dev-DB rows changed during S37's browser verification** (one visit
  `awaiting_doctor` → `reviewed`, one prescription + document created). Synthetic data only (rule
  #4); noted so nobody reads them as real clinic activity.
- **Still not done from earlier cycles:** the 3 API keys, formal WER, the Edge run, Step S5.

## Locked decisions — do NOT re-open

- **ADR-0058 (S37):** a new staff view is a different QUESTION asked of existing rows, never a new
  copy — hence **no new table and no new column**; triage order is tier-then-wait and an unassessed
  case sorts between High and Medium; the handover check is **advisory and can never block a
  forward** (a Critical patient must reach a doctor with incomplete paperwork); a red flag is `info`,
  never `warn`; the patient history carries **no transcript** (rule #1) and interprets nothing
  (rule #2); `scope=recent` is doctor-only and requires `doctor_id`; medic and doctor writing the
  same `patients` row at two moments is **one source of truth used twice, not duplication**.
- **ADR-0059 (S37):** accessibility outranks the effect — every `animation`/`@keyframes` stays
  inside `@media (prefers-reduced-motion: no-preference)` and nothing is conveyed by movement alone;
  only composited properties animate; a looping animation is reserved for urgency; the two staff
  portals must never read as one screen; the kiosk never loads `motion.css`.
- **ADR-0057 (S36):** the session epoch and `endSession()`; **MCP is rejected**; a complete phone
  number ends its own turn but does not skip the read-back; the auto-download is dropped rather than
  handed to the next patient.
- **ADR-0056 / 0055 / 0054 / 0053 / 0052 / 0051 / 0050 / 0049 / 0048 / 0045 / 0040** — see
  `decisions.md`.
- **S31's terminal/transient STT split:** `no-speech`, `aborted`, `bad-grammar` must stay OUT of
  `TERMINAL_STT_ERRORS` or Chrome's continuous listening regresses. `r.onend` stays untouched.
- **⚠ No apostrophes in comments inside the `CONFIRM_*` literals** in `kiosk.js` — the vocabulary
  tests parse quoted tokens straight out of the served file, so prose with an apostrophe is read AS
  VOCABULARY. This actually happened in S36.

## ⛔ Step S5 is NOT implemented — do not assume it is

S5 (`faculty_future_features.md` §J) is: **no-speech re-prompt, empty-submit guard, 120 s answer
cap, and permission/visibility recovery.** S34 built only the narrow empty-capture re-ask its
Phase 2 required; S35, S36 and **S37 built nothing from S5 at all** (S37 touched no voice code).
Pinned by `test_step_s5_is_still_not_implemented`: `no_speech_ms` and `max_answer_ms` are still
marked `S5 (not used yet)` and read by nothing, and there is no `visibilitychange` handler and no
permission-recovery path anywhere in the kiosk.
⚠ **The permission/visibility half is BLOCKED, not merely pending** — see open item 3 above.

## Reminders (the four non-negotiables)

- **Rule #1:** raw words are never edited, and never RE-RENDERED elsewhere. S37's doctor timeline
  deliberately carries no transcript — a prior visit is opened through `GET /api/visits/{uuid}` and
  read from the one immutable copy. A test asserts it.
- **Rule #2:** never diagnoses. The patient history ranks nothing, trends nothing and names no
  condition; the C1 suggestion still never reaches the prescription Diagnosis.
- **Rule #3:** red flags ADD-only. In S37 a red flag is surfaced as `info` on the handover check and
  as a pulsing chip on the queue row — it can never make a case read as "not ready", and the local
  rule still forces Critical with every LLM down.
- **Rule #4:** synthetic/consented data only. Web Speech sends audio to Google; edge-tts sends the
  assistant's question text to Microsoft (ADR-0050) — state both in the thesis privacy section.
- Run (Windows): `.venv\\Scripts\\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Tests: `pytest backend/tests/` (**767 passing, 2 skipped**). Windows: `PYTHONIOENCODING=utf-8`.
