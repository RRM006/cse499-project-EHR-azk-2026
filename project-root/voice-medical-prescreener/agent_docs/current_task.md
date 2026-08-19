# current_task.md — What We Are Doing RIGHT NOW

> This is a small, throwaway snapshot. It gets **overwritten** every session.
> It is NOT a history log (that is `changelog.md`). It answers only:
> "If I open a brand-new Claude Code session, what do I need to know to continue?"

---

**Date:** 2026-08-19 (end of Session 45) — **fourth hardening session of the same day.**
**Phase:** The medic's **"clicking ✏️ Edit does nothing" bug is FIXED and verified by a real mouse
click** — it was the card moving between `mousedown` and `mouseup`, not the handler and not the API.
Test suite: **1196 passed, 2 skipped, 0 failures** (was 1181).
Alembic head: **0014 — unchanged. 18 tables. No new dependency. No schema or migration change.**
**No new ADR** (a stylesheet bug fix). **No module changed status. M15 stays 🟨.**
⚠ **S45 changed exactly one CSS rule and added one test file — no JavaScript, no route, no service.**

**There is no outstanding coding task.** Everything below is demo validation only.

---

## 🚦 NEXT SESSION — do these in order

### 1. Paste the nine API keys (5 minutes) — the only blocking item

`backend/.env` has nine **empty** slots waiting. One key per line, no quotes, no spaces around `=`:

```
GEMINI_API_KEY_1=      GROQ_API_KEY_1=      OPENROUTER_API_KEY_1=
GEMINI_API_KEY_2=      GROQ_API_KEY_2=      OPENROUTER_API_KEY_2=
GEMINI_API_KEY_3=      GROQ_API_KEY_3=      OPENROUTER_API_KEY_3=
```

- The **bare** `GEMINI_API_KEY` / `GROQ_API_KEY` / `OPENROUTER_API_KEY` lines are still read and are
  **slot 1** — your existing keys are in them and still work. The same key in two slots counts once.
- Blank slots are skipped; sparse is legal (key 1 + key 3 = two working keys).
- Keys are read **at startup**, so restart uvicorn, then verify (never prints a key):
  ```
  .venv\\Scripts\\python.exe -m backend.scripts.check_api_keys
  ```
  Expect `key 1 configured / key 2 configured / key 3 configured` under each of `gemini_flash`,
  `groq` and `openrouter`, then a PASS/FAIL per (key, model).
- ⚠ `CEREBRAS_API_KEY` has **one** slot only. ⚠ Do **not** set `MISTRAL_API_KEY` (trains on inputs,
  rule #4).

Resulting chain: `Gemini k1→k2→k3 → Groq k1→k2→k3 → Cerebras → OpenRouter k1→k2→k3`, every model of
one key before the next key (ADR-0069).

### 2. Hard-reload every portal

`Ctrl-F5` on `/kiosk.html`, `/medic/` and `/doctor/`. **S45 changed `frontend_shared/motion.css`**,
which both staff portals load and browsers cache aggressively — without a hard reload the Edit
button will still be broken on your machine.

### 3. The real-microphone pass — the last thing only you can do

**No microphone run has happened since S41**, and S42/S43/S44/S45 changed no speech code at all.
Speaking normally, check:
- normal Bangla, then Banglish; one short answer and one long one
- the words stay inside the box and the newest line is visible (S41)
- the red **"🎤 এখন কথা বলুন — বলা শেষ হলে থেমে যান"** banner appears while the mic is open and
  disappears the moment it closes
- while the mic is open, switch to another browser tab and come back: the kiosk must stop listening
  and say *"পেজটি ছেড়ে যাওয়ায় রেকর্ডিং থেমে গেছে…"* (S42)

### 4. Two data items from S44 that are yours to accept or undo

**(a) A case I forwarded by accident.** Visit `1bbe6d80-48cd-42aa-a819-214be28eeb07` (ইসরাত,
patient 16) went to Dr. M. Rahman, so **the medic queue is empty**. Nothing was deleted and
`audit_log` records it correctly. To put it back:

```sql
UPDATE visits SET status='awaiting_review', assigned_doctor_id=NULL
WHERE uuid='1bbe6d80-48cd-42aa-a819-214be28eeb07';
```

⚠ Leave the `audit_log` row alone — it is a true record.

**(b) Synthetic vitals on that same patient:** height 170cm, weight 70.5kg, BP 118/76, blood sugar
**5.8 mmol/L random** (S45's verification re-saved it). All four fields were empty before, so
nothing of yours was overwritten. Clearing them needs a direct DB write.
The three S42 synthetic visits (`+8801955000321/322/323`) are also still there.

---

## ✅ What Session 45 shipped (settled — do not redo or re-derive)

**The bug was the card moving between the two halves of one click.** Measured on the shipped page
with real mouse events and a capture-phase listener, aiming at the Edit button's own centre:

```
mousedown @628,526 -> DIV
mouseup   @628,526 -> BUTTON#intake-toggle    <-- a DIFFERENT element
click     @628,526 -> DIV                     <-- their common ancestor
```

`.fx-card` carried `transform-style: preserve-3d` + `will-change: transform` and moved in Z inside
`.fx-scene { perspective: 1400px }` — `translate3d(0,-2px,12px)` on hover, `translate3d(0,0,2px)` on
press. Under a perspective, changing Z **rescales** the card, so pressing the mouse shifted every
child by a few pixels and the button slid out from under a stationary pointer.

**Fixed** by carrying the depth in the **elevation shadow**: `.fx-card` sets no transform at all and
transitions `box-shadow` only. Hover, press and keyboard focus all still respond; nothing removed.
⚠ **A/B proved in the live page** — re-injecting the old rule reproduced the split
mousedown/mouseup and the editor stayed shut.

⚠ **THE LESSON, which is why this survived two "verified" sessions:** S41 and S43 checked this area
with `element.click()` and with clicks aimed at the SAVE button. **A programmatic `.click()` cannot
detect a hit-target defect — it invokes the handler and skips hit-testing entirely.** Anything about
whether a control can be *pressed* must be driven with a real mouse.

## ⚠ Open gaps / honest caveats (carry these forward)

- **Real API-key failover is mock-tested only** — the nine slots are empty (item 1 above).
- **No real-microphone run** since S41; nothing since has touched speech code.
- **No screenshots.** The Browser pane composites no frames here, so every visual claim in S43-S45
  is a measurement — event traces, `getBoundingClientRect`, computed styles, request logs. The
  *appearance* of S45's shadow-only hover is unclaimed; its behaviour is measured.
- **The corrector seam (`/api/correct`) uses key slot 1 only** and has no chain (ADR-0069 g).
- **Still not done:** Step S5, the mid-turn word-loss rule #1 decision, formal WER, the Edge run,
  rotating the older keys, the six committed `.db.bak` files.

## Locked decisions — do NOT re-open

- **S45 (no ADR, recorded in `motion.css` and `CLAUDE.md`):** a container of interactive controls is
  **never moved** — no `transform`, `translate3d`/`translateZ`, `preserve-3d` or
  `will-change: transform` on `.fx-card` or any card holding controls; depth is the `--elev-*`
  shadow. Moving the control ITSELF stays fine (`.fx-lift`, `.queue-item`) because the pointer
  stays inside it. `.fx-scene` keeps its perspective — a card that never moves in Z is never
  re-projected.
- **ADR-0069 (S44):** three keys per provider through the SAME chain, never a second router;
  key-major ordering; the cooldown includes the credential slot; four slots per bucket with blanks
  and duplicates dropped; a provider is "failed" only when every one of its keys failed.
  **Supersedes ADR-0068 (g).**
- **ADR-0068 (S43)** — all but (g) stands: an asynchronously-filled element never sits above an
  interactive control; disclosure state lives outside the DOM node that gets rebuilt; an unsaved
  draft is stamped with its patient; every provider-reaching route answers through `_llm_errors`;
  a key with no model is a REPORTED configuration error; one env template.
- **ADR-0067 (S42), ADR-0066 (S41), ADR-0065 (S40), ADR-0064 (S39), ADR-0060–0063 (S38),
  ADR-0058/0059 (S37)** and earlier — see `decisions.md`. All still stand.
- **S31's terminal/transient STT split** — `no-speech`, `aborted`, `bad-grammar` stay OUT of
  `TERMINAL_STT_ERRORS` or Chrome's continuous listening regresses. `r.onend` stays untouched.
- **⚠ No apostrophes in comments inside the `CONFIRM_*` literals** in `kiosk.js`.
- **⚠ Match each file's existing line endings.** S42 broke two tests by converting LF to CRLF.
- **⚠ Never use a bare `.btn-primary` selector in a browser smoke test** — it is how S44 forwarded a
  case by accident. Address elements by id.
- **⚠ `resize_window` in the Browser pane desynchronises the click coordinate frame** (measured:
  1.75x). Verify at the native viewport, or compare the reported click position with the position
  the page actually receives before believing a reproduction.

## ⛔ Step S5 is NOT implemented

S5 (`faculty_future_features.md` §J) is: **no-speech re-prompt, empty-submit guard, 120 s answer cap,
and permission/visibility recovery.** `no_speech_ms` and `max_answer_ms` are still served by
`/api/config` and **read by nothing** — pinned by a test. S42's `handleVisibilityChange()` is not S5,
and S43/S44/S45 added no kiosk code at all.
⚠ **The mid-turn word-loss rule #1 decision is still YOURS and still blocks the second half of S5.**

## Reminders (the four non-negotiables)

- **Rule #1:** raw words are never edited. S45 touched no transcript storage and no JavaScript.
- **Rule #2:** never diagnoses. S45 added no clinical content of any kind.
- **Rule #3:** red flags ADD-only. Untouched.
- **Rule #4:** synthetic/consented data only. No real provider call was made this session.
- Run (Windows): `.venv\\Scripts\\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Tests: `pytest backend/tests/` (**1196 passing, 2 skipped**). Windows: `PYTHONIOENCODING=utf-8`.
- Keys: `.venv\\Scripts\\python.exe -m backend.scripts.check_api_keys` (never prints a key).
