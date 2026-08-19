# changelog.md — Session-by-Session History

> The running memory of the project. **Newest entry at the top.**
> One short entry per session. This is what a new session reads to remember
> "what happened recently and why", so we never re-explain or re-litigate.
>
> Template for each entry:
> ```
> ## Session N — YYYY-MM-DD — <short title>
> - Did: <what we actually built or changed>
> - Decided: <any decision; also add it to decisions.md>
> - Broke / problem: <anything that failed or is fragile>
> - Deferred: <what we chose NOT to do yet, and why>
> - Next: <the one thing to do next — also update current_task.md>
> ```

---

## Session 45 — 2026-08-19 — **"Clicking ✏️ Edit does nothing" was the CARD moving between mousedown and mouseup** — 1181 → 1196 tests
- Did: reproduced the reported medic-portal bug with **real mouse events** (the previous two sessions
  had only ever verified it programmatically, which is why it kept coming back), root-caused it,
  fixed it in **one CSS rule**, and pinned it with a regression test. ⚠ **No schema, migration,
  Alembic, dependency, route, service or JavaScript change of any kind** — head stays **0014, 18
  tables**. **No module changed status; M15 stays 🟨.** ⚠ **No new ADR** — this is a bug fix to a
  stylesheet, not an architectural decision (the rule it establishes is recorded in `motion.css`
  itself, in `CLAUDE.md`'s frontend section, and in the new test).
- ⚠ **THE PREVIOUS TWO SESSIONS DID NOT ACTUALLY TEST THIS.** S43 verified the editor with
  `element.click()` and with clicks aimed at the SAVE button; S41 verified a scroll. Neither ever
  drove a real mouse at the **Edit** button. The handler was always fine, the route was always fine,
  and every test passed — which is precisely why "the terminal says it works" kept being the wrong
  answer. Recorded plainly because the lesson is the finding: **a programmatic `.click()` cannot
  detect a hit-target defect, because it bypasses hit-testing entirely.**
- **ROOT CAUSE — MEASURED, with a capture-phase listener on the shipped page.** Aiming at the Edit
  button's own centre (from its own `getBoundingClientRect`):
  ```
  pointerdown @628,526 -> DIV
  mousedown   @628,526 -> DIV
  mouseup     @628,526 -> BUTTON#intake-toggle     <-- a DIFFERENT element
  click       @628,526 -> DIV
  ```
  `mousedown` and `mouseup` landed on **different elements**, and the browser's rule for that is to
  fire `click` on their nearest **common ancestor** — the wrapper `<div>`. So the button's own
  handler never ran: no request, no error, nothing on screen. Indistinguishable from a dead control.
- **WHY THE ELEMENT UNDER A STATIONARY POINTER CHANGED MID-CLICK.** `.fx-card` (the S37 depth layer)
  carried `transform-style: preserve-3d` + `will-change: transform` and moved in Z inside
  `.fx-scene { perspective: 1400px }` — `translate3d(0,-2px,12px)` on `:hover`, then
  `translate3d(0,0,2px)` on `:active`. Under a perspective, **changing Z rescales the element about
  the perspective origin**, so pressing the mouse shifted every child of the card by a few pixels.
  A control near the card's edge slides out from under the pointer between the two halves of one
  click. The shift is proportional to a child's distance from the origin, which is why it hit some
  buttons and not others and why it felt intermittent.
- ⚠ **A/B PROVED IN THE BROWSER, NOT ARGUED.** Re-injecting the old rule at runtime reproduced the
  split mousedown/mouseup and the editor stayed shut; removing it again delivered **all four events
  to `BUTTON#intake-toggle`** and the editor opened. Two earlier hypotheses were tested and
  **rejected on measurement** first: a `resize_window` coordinate-scaling artifact (1.75x — my own
  tooling, not the app) and `preserve-3d` alone in a settled state (hit fine).
- **THE FIX — one rule, nothing removed.** `.fx-card` no longer sets `transform`,
  `transform-style` or `will-change`, and transitions `box-shadow` only. The depth affordance S37
  wanted is kept and is carried by the **elevation shadow**, which is what the `--elev-*` tokens are
  for: hover, press and keyboard focus all still respond. No handler was rewired, no markup changed,
  no second listener added, no JavaScript touched.
- ⚠ **Deliberately NOT changed:** `.queue-item` keeps its 2-D `translateX` (a single click target
  with no nested controls, so it cannot separate a mousedown from a mouseup on a child);
  `.fx-lift` keeps its 1px button lift (it moves the button ITSELF, and the pointer stays inside a
  33px target); `.fx-scene` keeps its `perspective` (a card that never moves in Z is never
  re-projected, and removing it would have been wider than the defect called for).
- Decided: no ADR. The durable rule — **a container of interactive controls is never moved in 3D;
  depth is the shadow** — is stated at the rule itself in `motion.css`, added to `CLAUDE.md`'s
  frontend section, and enforced by the new test.
- Verified — **by real mouse, which is the only acceptance condition here.** Hover onto ✏️ Edit,
  click: all events reach `BUTTON#intake-toggle` and the editor opens. 🩸 Sugar reference: opens its
  chart (2031 chars). Blood sugar retyped to **5.8** with real keystrokes, Save clicked with the
  mouse: **exactly ONE `PATCH /api/patients/16/vitals`**, the card then reads
  `🩸 রক্তে সুগার: 5.8 mmol/L (104 mg/dL) · যেকোনো সময়`, the editor closed, the error banner stayed
  empty and the console produced **no messages at all**. Doctor portal re-checked: queue loads, case
  opens, EHR FHIR + PDF + Write Prescription + Accept & Write to EHR all present, clean console.
- Verified — tests: **1196 passed, 2 skipped, 0 failures** (was 1181/2). New file
  `test_card_click_target_s45.py` (**15**). **No existing test was modified, weakened or deleted.**
  The new assertions were proved non-vacuous against the pre-fix stylesheet, which carried three
  `transform` declarations on `.fx-card`, `preserve-3d`, `will-change: transform` and a
  transform transition.
- Broke / problem: nothing. ⚠ One honest note about method: my first reproduction attempt was
  confounded by my own `resize_window` call, which desynchronised the click coordinate frame by
  1.75x and made an unrelated queue row look broken. Caught by comparing the reported click position
  with the position the page actually received, and ruled out before any code was touched.
- Deferred: unchanged from S44 — pasting the nine API keys, a real-microphone pass, **Step S5**, the
  mid-turn word-loss rule #1 decision, formal **WER**, the Edge run, the six committed `.db.bak`
  files, and the two S44 data items (the accidentally forwarded visit and the synthetic vitals).
- Next: **paste the nine API keys into `backend/.env`**, restart uvicorn, run
  `python -m backend.scripts.check_api_keys`, then hard-reload the portals and do the
  real-microphone pass.

## Session 44 — 2026-08-19 — **Three API keys per provider: nine free quotas reachable through the one existing chain, and a per-key cooldown so one spent key no longer sleeps the other two** — 1150 → 1181 tests
- Did: extended the existing provider registry so **Gemini, Groq and OpenRouter each hold up to four
  credential slots**, tried in order before the chain moves to the next provider; added the nine
  slots to `backend/.env` and documented them in `.env.example`; taught `check_api_keys` to report
  per slot; and closed a `.gitignore` gap that this session itself exposed. **One new ADR: 0069,
  which SUPERSEDES ADR-0068 (g).** ⚠ **No schema, migration, Alembic or dependency change** — head
  stays **0014, 18 tables**. **No module changed status; M15 stays 🟨.** ⚠ **No frontend file was
  touched at all** — no kiosk, medic, doctor, voice, TTS or CSS change of any kind.
- ⚠ **ADR-0068 (g) was WRONG on its premise, and this reverses it.** S43 rejected multiple keys per
  provider because "three keys" was read as three PROVIDERS, which the six-bucket registry already
  covered. The real situation is three keys **for each** of three providers. A free tier is metered
  per ACCOUNT, so those are **nine independent daily quotas** the architecture had no way to reach —
  and on a day when Gemini's quota was measured spent, that is exactly the redundancy that was
  missing. The rejection is recorded as superseded rather than deleted.
- **NOT A SECOND ROUTER — the same chain, one level deeper.** A bucket already expanded into one
  attempt per model (S42); it now expands into one attempt per **(credential, model)**.
  `provider_chain_for_module` is unchanged in shape, `FALLBACK_ORDER` is unchanged, and
  **`llm_client.py` changed by exactly one log line**. The resulting order, verified against the
  real builder: `Gemini key1→key2→key3 → Groq key1→key2→key3 → Cerebras → OpenRouter key1→key2→key3`,
  with every model of one key tried before the next key.
- **KEY-MAJOR, and the nesting is the decision.** Trying every model of key 1 before moving to key 2
  is right for both failure modes this project has actually measured: an OpenRouter `:free` 429 comes
  from a **shared per-model queue**, where a sibling model on the SAME key is the thing likely to
  answer; a daily-quota 429 is **per account**, where only another key helps — and by then every
  model of the exhausted key has been ruled out anyway.
- ⚠ **THE CRUX: the cooldown key now includes the credential slot.** `cooldown_key` was
  `bucket|model`; it is now `bucket#slot|model`. Without that, three Gemini keys collapsed to ONE
  cooldown identity, so a 429 on key 1 would have put keys 2 and 3 to sleep on the evidence of a
  third — **proved against the pre-change formula: 3 attempts, 1 cooldown key.** Cooldowns stay
  time-based and in-process, so **no key is ever permanently disabled**; a key busy this minute is
  tried again later. No persistent key-health storage was added.
- **Naming follows the project's own convention and stays backward compatible.** Each bucket reads
  four slots — the bare `GEMINI_API_KEY` **then** `_1`, `_2`, `_3` — with blanks and duplicates
  dropped. An existing `.env` that sets only the bare name is a one-element list and behaves exactly
  as it always did (**verified against the real `.env`: the live chain is unchanged**). A fresh
  `.env` may leave the bare name empty and use the numbered slots alone, which is the layout asked
  for. The same key pasted twice counts **once** — it is one quota, not two, and counting it twice
  would make the slot report overstate the redundancy available.
- **`check_api_keys` now answers the question the human actually has.** It prints a slot inventory
  per provider ("key 1 configured / key 2 configured / …") **before spending a single request**,
  names the exact empty `.env` variables, and probes every (key, model) attempt. ⚠ A provider is
  reported as failed **only when EVERY one of its keys failed** — a missing or spent key 2 never
  condemns a working key 1. The env names it prints come from the registry (`KEY_ENV_NAMES`), so it
  can never send the operator to edit a variable nothing reads.
- ⚠ **Cerebras and Mistral keep ONE slot each**, stated out loud in `.env.example` because the
  asymmetry is otherwise a trap: they are optional extra BUCKETS, and `CEREBRAS_API_KEY_2` would do
  nothing.
- Decided: **ADR-0069** (a)–(g), superseding ADR-0068 (g).
- Broke / problem: ⚠ **I created a `.env` backup that was NOT gitignored — it held every real key.**
  `*.env` does not match `.env.20260819-132348.bak`. It never reached git (never staged, never
  committed — verified), and it was deleted the moment it was noticed, but `.gitignore` now carries
  `.env.*` / `*.env.*` with `!*.env.example` and `!.env.example` re-included, and both directions are
  tested. ⚠ **And I forwarded a case I did not mean to.** A smoke-test snippet used the selector
  `.btn-primary`, which on an already-logged-in medic page is the *forward to doctor* button, so
  visit `1bbe6d80…` (ইসরাত) moved to Dr. M. Rahman at 07:18:27 and the **medic queue is now empty**.
  Nothing was deleted, `audit_log` correctly records `visit.assign` by Medic Rahman, and the reversal
  is one UPDATE — but it is the human's data and their call (see current_task.md).
- Verified: **1181 passed, 2 skipped, 0 failures** (was 1150/2). New file:
  `test_multi_key_fallback_s44.py` (**31**), covering the brief's scenarios A–O plus 404
  fall-through, per-key cooldown isolation, dedup, whitespace, sparse configuration and the
  credential-safety properties. **Every provider is mocked — no network call, no real credential, no
  quota spent.** New assertions proved non-vacuous against HEAD: `provider_api_keys`, `KEY_ENV_NAMES`
  and `key_index` did not exist, and the old `cooldown_key` collapsed three keys into one.
  Browser: server starts clean with the nine slots and warns about nothing; medic Save measured
  **layout shift 0.00, scroll delta 0.00** while the BMI grew to 210 chars; doctor portal shows both
  EHR buttons and Accept & Write to EHR; kiosk `/api/config` 200 and `/api/tts` returns real
  `audio/mpeg`; clean consoles throughout.
- ⚠ **No existing test was weakened or changed** — the 1150 that passed before still pass unmodified.
- Deferred: the corrector seam (`/api/correct`) still uses **slot 1 only** and has no chain of its
  own — it is the legacy `/legacy/` demo's route and folding it into `call_module` needs its own
  decision; the six committed `.db.bak` files; **Step S5**; the mid-turn word-loss rule #1 decision;
  formal **WER**; the Edge run; rotating the existing keys.
- Next: **paste the nine keys into the empty slots in `backend/.env`**, restart uvicorn, and run
  `python -m backend.scripts.check_api_keys` — it should print "key 1/2/3 configured" for all three
  providers. Then a real-microphone pass.

## Session 43 — 2026-08-19 — **"Save does nothing" was a 30-pixel layout shift, the language toggle was quietly eating a medic's typing, and one provider route was still speaking the upstream provider's words** — 1087 → 1150 tests
- Did: root-caused and fixed **three measured defects** in the medic's Intake & Vitals card, closed
  the **one LLM route S42's disclosure fix missed**, made a silent provider-configuration error
  report itself, and completed `.env.example`. **One new ADR: 0068.** ⚠ **No schema, migration,
  Alembic or dependency change** — head stays **0014, 18 tables**. **No module changed status; M15
  stays 🟨.** ⚠ **No STT/TTS/voice code touched** — the kiosk's speech pipeline is byte-for-byte as
  S42 left it; the only kiosk-related change is a TEST that pins existing behaviour.
- **MEDIC BUG 1 — the Save click was landing on a `<div>`, and the button was never at fault.**
  MEASURED in a real browser at 1280x720 with an instrumented event listener: `#bmi-live` is
  **15.7px tall while empty and 45.6px once the `/api/reference/bmi` answer arrives**, and it sat
  directly ABOVE the Save/Cancel row — so **Save moved down 29.9px, which is 94% of its own 31.6px
  height**, roughly 250ms (the `liveBmi` debounce) plus one network round-trip after the medic
  stopped typing. That is exactly while their hand is travelling to the button. The trace read
  `click -> DIV`, no `PATCH` was sent, no error appeared and the form stayed open with the values
  still in it — indistinguishable from a dead button, which is how it was reported. Fixed by DOM
  ORDER: the readout now follows the action row, so nothing interactive can be displaced at any
  width in either language. ⚠ **Reserving space with a `min-height` was rejected on measurement** —
  the box is 3 lines at 800px in English and more in Bangla at a narrow width, so any fixed
  reservation is a guess that fails on the layout it was not measured on. Nothing was removed: the
  BMI, both band ladders and the rule #2 disclaimer all still render, 35px lower.
- **MEDIC BUG 2 — switching language silently CLOSED the 🩸 Sugar reference chart, in BOTH staff
  portals.** Measured: `display` went `block -> none` and 2186 characters went to 0. Both portals
  call `renderGlucosePanel()` on a language change *precisely* so the chart follows the toggle, and
  it returned immediately every time — because whether the panel was open had been inferred from
  `panel.style.display`, a property on an element the card's `innerHTML` rebuild had just destroyed
  and recreated from a template saying `display:none`. The state now lives in one `Set` in
  `frontend_shared/staff.js`, keyed by mount id, so **one fix covers the medic and the doctor** and
  neither can close the other's.
- **MEDIC BUG 3 — the language toggle silently DISCARDED unsaved vitals.** Measured: a weight of
  63.5 typed into the open editor read 62.5 again afterwards. `renderIntakeCard()` re-opens the
  editor from the STORED patient, so every unsaved keystroke was overwritten with no warning — and
  a medic who does not notice then saves the old numbers over their own reading.
- ⚠ **The first version of that third fix introduced a REAL regression, and S41's test caught it.**
  The editor deliberately stays open across a PATIENT SWITCH, so restoring a draft blindly would
  have put one patient's typed weight into another patient's form — the exact leak
  `test_medic_intake_editor_s41.py` exists to prevent. The draft is now **stamped with the patient
  id it was typed for** and discarded for anyone else. Verified in the browser all three ways: a
  language toggle keeps it, a foreign-stamped draft falls back to the stored record, a
  correctly-stamped one is restored.
- **THE LEAK S42 MISSED.** `POST /api/correct` (Module 2, reached through the `Corrector` seam
  rather than `call_module`, so it never raises `LLMCallError`) still answered
  `detail=f"Correction failed: {exc}"` — the same raw upstream body S42 removed from six other
  routes. S42's guard walks `routes_*.py` but only inspects files that mention `LLMCallError`, so
  it could never have caught this one. Now routed through a new sibling helper
  `_llm_errors.provider_unavailable()` (same message, same `Retry-After`), the technical text goes
  to the server log, and a companion test covers the gap in the original guard.
- **A SILENT CONFIGURATION ERROR THAT COULD DELETE THE UNIVERSAL FALLBACK.** `OPENROUTER_MODEL=` —
  one blank line, with a perfectly valid key beside it — makes `split_models` return `[]`, which
  makes `provider_variants` return nothing, which makes `provider_chain_for_module` **skip the
  bucket entirely**, with no error and no trace. `check_api_keys` made it worse by reporting that
  bucket as "not set", i.e. blaming the key. New `misconfigured_buckets()` names the case; the
  server warns about it **at startup**; the checker reports it as its own verdict and points at the
  `*_MODEL` line. A bucket with neither key nor model is still NOT reported — that is the normal
  state of every optional provider.
- **NO REDUNDANCY:** the Module-2 corrector kept a **private copy of Groq's and OpenRouter's base
  URLs**; it now resolves through the one registry (`llm_providers.provider_credentials()`), and a
  test fails if either URL is written down twice again. `backend/.envnew.example` — a second,
  partial env template that told the reader to copy it to `.env`, and would have produced one with
  no `DATABASE_URL`, no OTP channel, no TTS provider and no voice settings — was **removed**;
  a test now asserts there is exactly one env template.
- **.env.example completed:** `GEMINI_FLASH_MODEL`, `GEMINI_FLASH_LITE_MODEL`, `CEREBRAS_BASE_URL`,
  `CEREBRAS_MODEL`, `MISTRAL_BASE_URL` and `MISTRAL_MODEL` were undocumented; a test now fails if
  any provider setting exists in code but nowhere in the template. It also states plainly that
  **there is ONE key per bucket and none is needed for multiple keys per provider** — redundancy
  comes from having several BUCKETS and, within a bucket, several MODELS.
- Decided: **ADR-0068** (a)–(h). ⚠ **Explicitly REJECTED: building multi-key-per-provider support.**
  The brief allowed it "if genuinely necessary"; it is not. Six buckets exist, three of them map
  exactly onto the three keys available, every `*_MODEL` already accepts a comma-separated list, and
  a second credential-rotation mechanism would be the "second routing system" the brief forbids.
- Verified: **1150 passed, 2 skipped, 0 failures** (baseline this session: 1087/2). New files:
  `test_provider_config_s43.py` (29) and `test_medic_intake_editor_s43.py` (33);
  `test_medic_intake_editor_s41.py` gained 1. Every new assertion was **proved non-vacuous against
  the pre-fix HEAD blobs**. Browser (localhost:8001, 1280x720): the Save button's top measured at
  **627.01px before and after** the BMI lands (shift 0.00, was 29.9) and a real click now sends
  **exactly one** `PATCH /api/patients/16/vitals` per save; the chart survives a language toggle
  (2186 chars kept) in the medic portal and a card rebuild in the doctor portal, and still closes on
  a second click; the doctor portal shows EHR FHIR + PDF, Write Prescription, Override and Accept &
  Write to EHR with a clean console; logout returns to the portal directory with empty
  sessionStorage; the kiosk loads with `/api/config` 200, the phone screen up, the AI-retry panel
  present and hidden, and no console errors.
- ⚠ **Three pinned test literals were UPDATED, not weakened.** S41's "every field is re-seeded"
  test now asserts the property against the new one-loop shape AND gained a companion that the
  draft cannot cross patients (strictly stronger); S41's re-open literal gained the third argument;
  S39's glucose test moved from the prefill lines to the **save path**, which is the stronger claim.
- Broke / problem: the draft regression above, caught by an existing test and fixed before the
  suite went green. ⚠ **I entered synthetic vitals on the dev DB while verifying** — patient 16
  (ইসরাত, `+8801875637607`) now carries height 170cm, weight 70.5kg, BP 118/76 and blood sugar
  5.4 mmol/L random. All four fields were **empty** before, so nothing was overwritten, but the
  PATCH route has no way to clear a value (by design), so removing them needs a direct DB write —
  the human's call, on S41's precedent.
- Deferred: giving `/api/correct` a FALLBACK CHAIN (it is the legacy `/legacy/` demo's route, not on
  the kiosk path; folding it into `call_module` would change the M2 `Corrector` seam and needs its
  own decision); `routes_tts.py`'s `detail=str(exc)` (**inspected and it is not patient-reachable** —
  `tts.js` binds `audio.onerror` and never reads the body); the six committed `.db.bak` files;
  **Step S5**; the mid-turn word-loss rule #1 decision; formal **WER**; the Edge run. ⚠ **No
  real-microphone run** — this session changed no speech code.
- Next: **add `CEREBRAS_API_KEY`** (still the highest-value pre-demo action, unchanged from S42),
  then hard-reload all three portals and do a real-microphone pass.

## Session 42 — 2026-08-19 — **The demo-eve outage: Groq's model was decommissioned, OpenRouter's free model was rate-limited, and the raw provider error was being shown to the patient** — 1056 → 1087 tests
- Did: root-caused and fixed the reported `POST /api/visits/<uuid>/intake` **502**, hardened the
  provider layer so no single free model is a point of failure, closed the disclosure leak that put
  upstream provider text on a patient's screen, and gave a total AI outage a controlled, bilingual,
  **retryable** UI. **One new ADR: 0067.** ⚠ **No schema, migration, Alembic or dependency change** —
  head stays **0014, 18 tables**. **No module changed status; M15 stays 🟨.** ⚠ **No STT/TTS logic
  changed** — the speech pipeline was deliberately not touched.
- **ROOT CAUSE — three faults lined up, none of them the one that was reported.** (1) Groq's
  `llama-3.3-70b-versatile` is **GONE** from Groq's live model list — the call answers
  `404 model_not_found`. Groq is `FALLBACK_ORDER[0]`, so the *first* bucket every module falls back to
  had been dead. (2) OpenRouter's `google/gemma-4-31b-it:free` answered **429 from its SHARED upstream
  pool** — that is ADR-0026's *universal fallback*. (3) Which left **Gemini as the only working
  provider**, so its ordinary daily 429 took the whole system down. The reported symptom named only
  the last provider to fail, which is why it looked like an OpenRouter problem.
- ⚠ **THE PATIENT WAS BEING SHOWN THE UPSTREAM PROVIDER'S ERROR.** Six routes answered
  `HTTPException(502, detail=str(exc))`, and `str(exc)` ends in the raw provider body — measured as
  containing the model id, `'provider_name': 'Google AI Studio'` and a signup URL. The kiosk pipes
  `detail` straight into its banner. This is configuration disclosure from a system handling medical
  data, and it is fixed at ONE helper (`api/_llm_errors.py`) that every LLM route now uses; a test
  walks `routes_*.py` and fails if any of them skips it.
- **A BUCKET NOW NAMES SEVERAL MODELS.** `OPENROUTER_MODEL` is comma-separated and each entry is its
  own attempt with its **own cooldown**. Measured: the configured id and one sibling were 429 while
  three other siblings answered the identical request correctly **in the same minute** — a `:free` id
  is not a quota you own, it is a queue you share. S41 fixed this bucket by swapping one dead id for
  one live id; that could only hold until the new id got busy.
- **Models replaced with live-verified ones:** Groq → `openai/gpt-oss-120b` (valid JSON, the
  patient's name kept in Bangla script, ~2.8 s on the real M3 prompt). ⚠ **Rejected in the same
  measurement:** `qwen/qwen3.6-27b` emits a `<think>` block that breaks `_parse_json`, and
  `groq/compound*` carry **built-in web search** — sending patient speech to a search tool would
  breach rule #4.
- **ONE BOUNDED RETRY, AND A BOUND ON THE WHOLE CALL.** A 429/5xx/timeout gets one more pass after
  ~1.5 s (the provider's own body says "retry shortly" and means it); a 404 or 401 gets none.
  Separately, `CALL_DEADLINE_S = 90` bounds the ENTIRE call — five attempts x 45 s x a retry pass was
  **7.5 minutes** of spinner, and "stuck loading" is worse than an honest error because an error at
  least carries the retry button. 90 s is ~6x the slowest measured degraded success.
- **A TOTAL OUTAGE IS NOW A WAIT THE PATIENT CAN ACT ON.** An amber panel — deliberately not red; an
  upstream queue clearing in a moment is a WAIT, and danger-red tells an unwell patient something is
  wrong with *them* — says "The assistant is busy right now / Your answers are saved" in both
  languages and offers **Try again**. It does not auto-hide. ⚠ **The retry resumes from the step that
  FAILED and never re-posts the utterance** — re-posting would write the patient's sentence into
  their verbatim record twice (rule #1).
- **`check_api_keys` was accusing a VALID key.** Groq's 404 body reads `'type':
  'invalid_request_error'`, and the classifier tested `"invalid"` **before** `404`, so it reported
  "REJECTED — the key is wrong, revoked, or not yet active" and would have sent the human to rotate a
  perfectly good credential. Order fixed; it now also probes **every** model of every bucket.
- **A `visibilitychange` guard — and it is explicitly NOT Step S5.** Backgrounding the tab ends the
  recognition session, `r.onend` restarts it (correctly, per S31), and the kiosk sits showing the red
  "🎤 এখন কথা বলুন" banner while listening to nothing. The handler calls the **existing**
  `stopListening(false)`, so it takes **no new position** on the patient's half-captured words — the
  open rule #1 decision stays the human's. A test forbids it from touching `finalBuffer`, any submit
  path, or any S5 timing.
- Decided: **ADR-0067** (a)–(k).
- Verified — **live, not simulated.** ⚠ **The original failure condition is ACTIVE on this machine:**
  Gemini's free daily quota is genuinely exhausted (`...FreeTier`, limit 20/day). Under the old code
  that call *was* the reported 502; it now falls back to Groq in 825 ms and intake completes in 7.3 s.
  A second uvicorn was run with **deliberately invalid keys** (the human's `.env` untouched) to force
  a REAL total outage: the server answered 502 + `Retry-After: 30` with **zero** leaked terms, the
  kiosk showed its bilingual panel, **all four patient utterances were stored verbatim** through the
  outage, and clicking **Try again** after the provider returned completed the intake with **zero
  duplicate utterances**. Full patient flow then driven end to end (phone → OTP → 4 scripted turns →
  intake → follow-up loop → resume loop → 10/10 fields → submit), landing in the medic queue as HIGH.
  Medic **Edit → Save** measured at y=677 in a 720px viewport (S41's fix intact, was y=727). S41
  containment re-measured at 375/768/1280 px: nothing escapes, no horizontal page scroll.
- ⚠ **First appearance evidence this project has had** — the Browser pane composites frames now, so
  the panel is screenshotted in both languages. S41 could not claim this.
- Broke / problem: I converted 12 files from LF to CRLF by writing them with Python on Windows, which
  broke two tests that split on a bare newline. Caught and reverted; the diff is content-only. ⚠ Two tests were
  UPDATED, not weakened: the profile-render guard now **searches** for every function that renders a
  profile instead of naming one (stronger — it would catch a second unguarded render), and the S5
  pin now asserts the **boundary** (the visibility handler must not touch `finalBuffer`, submits or
  timings) instead of the absence of a string.
- Deferred: rotating the 3 keys (they authenticate; **Gemini's daily quota is spent** — see
  current_task.md); untracking the six committed `.bak` files (unchanged repo-content decision);
  **Step S5**; the mid-turn word-loss rule #1 decision; formal **WER**; the Edge run. ⚠ **No
  real-microphone run was performed** — the browser here reports `microphone: denied`. Everything
  above used the typed path, which is the SAME pipeline (`source: manual` vs `mic`, ADR-0048).
- Next: **add `CEREBRAS_API_KEY`** (free, ~1M tokens/day, sits ahead of OpenRouter in the chain) so
  the demo does not depend on two providers, then a real-microphone pass.

## Session 41 — 2026-08-15 — **The first real-microphone run's findings, fixed: the patient's words stay in their box, the microphone says it is open in words, and "Edit does nothing" turned out to be a scroll** — 1031 → 1056 tests
- Did: fixed the four defects the human's **real-microphone** run surfaced, deleted the synthetic
  test visit, and did the half of the API-key rotation a tool can safely do. **One new ADR: 0066.**
  **No schema, migration, route, service, FHIR, PDF, OTP or auth change** — the only backend edit is
  one configuration default. **Alembic stays 0014, 18 tables, no new dependency.** **No module
  changed status; M15 stays 🟨.** ⚠ **No voice/STT/TTS logic changed.**
- **THE PATIENT'S SPEECH ESCAPED ITS BOX — two causes, both fixed on the base rule.** Bangla and
  Banglish arrive from the recogniser as long runs with almost no break opportunities (a spoken phone
  number has none), so `overflow-wrap: anywhere` now applies to **all four docks** at once. The
  second cause was less obvious: the box is a **flex item**, and a flex item defaults to
  `min-width: auto`, which refuses to shrink below its content. It is also bounded now
  (`max-height: 30vh; overflow-y: auto`) and carries `flex: none`, because the default
  `flex-shrink: 1` was squeezing it back to its minimum the moment an answer got long — the patient
  saw two lines of their own sentence while the box had room for six.
- ⚠ **The box must NOT be flex-centred, and that is a rule #1 concern rather than a style one.** A
  flex container with `align-items: center` and overflowing content pushes the TOP of that content
  above the scroll origin, **where it cannot be scrolled back to** — the patient would silently lose
  the beginning of their own answer, invisible and unreachable. `display: block`, and the box scrolls
  its own newest line into view as they talk. That last scroll is the one thing that legitimately
  runs on every recognition result, and it is safe only because it moves nothing outside the element;
  a test pins that no PAGE scroll ever happens there.
- **ASSISTANT MESSAGES WERE BEING CUT.** `.chat-turn` had no wrapping rule and no `min-width: 0`, so
  in the narrower S40 left column a long Bangla question spilled out of its card. It now wraps, sizes
  to its content (`height: auto`), and a test forbids any `max-height`, `overflow: hidden` or
  `text-overflow: ellipsis` on a bubble — a capped bubble is exactly what hides the end of a
  question, and the THREAD is the thing that scrolls, not the bubble.
- **"THE MICROPHONE IS OPEN" IS NOW SAID IN WORDS.** "Listening..." describes the machine; a patient
  who has never used a computer needs to be told what THEY should do, in the first two words. The
  wording is now **"🎤 You can speak now — …" / "🎤 এখন কথা বলুন — …"**, changed in the ONE
  `LISTENING_HINT` constant every dock reads — one edit, four docks, no second implementation. It is
  a filled banner rather than merely larger red text (colour is never the only carrier), and SPEAKING
  and PROCESSING get a quieter, deliberately different treatment: "wait" must not look like "talk"
  across a room. ⚠ The claim is **retracted** the instant it stops being true — `stopListening()`
  rewrites the hint in the same call that clears the listening class, now pinned by a test, because
  the UI must communicate state and never fake it.
- **"CLICKING EDIT DOES NOT WORK" — the button always worked; the form opened where the medic could
  not see it.** MEASURED at 1280x720: the editor opened at y=461 and its **Save button landed at
  y=727**, below a 720px fold, inside a case workspace that scrolls independently and was sitting at
  `scrollTop: 0`. Nothing visible changed and there was no visible way to save — indistinguishable
  from a dead button. Also verified in the same pass, and all fine: the click is not intercepted,
  the save round-trips, a reading without its measurement context is still refused, and switching
  patients does **not** leak the previous patient's values.
- ⚠ **Smooth scrolling silently did nothing, so the helper now VERIFIES its own result.** Measured:
  `scrollIntoView({behavior:'smooth'})` left `scrollTop` at 0 even after 1.5 s on that container,
  while `behavior:'auto'` moved it by exactly the 55px needed. The workspace carries
  `perspective: 1400px` from the S37 depth layer and Chromium declines to smooth-scroll a scroller in
  a 3D rendering context. Removing the perspective would trade a real visual regression for an
  animation, so the animation gives way: attempt smooth, check `isFullyInView()`, finish instantly if
  it did not land. **`bringIntoView()` also MOVED from kiosk.js into shared.js** — the medic form
  needed identical behaviour, and a test now pins that exactly ONE definition exists front-end-wide.
- **THE SYNTHETIC VISIT IS GONE, after being proved deletable rather than assumed to be.** All 8
  referencing tables were enumerated (21 rows), the repo was searched for the phone number (it
  appeared only in `agent_docs/` prose), and every test was confirmed to build its own in-memory
  SQLite so none depends on the dev DB. Backup written first, identity guards re-asserted inside the
  transaction, `documents` and `prescriptions` counts verified unchanged after. ⚠ **The human's own
  real-microphone visit was explicitly checked still present** and untouched.
- **API KEYS — the rotation itself is still the human's**, but `backend/scripts/check_api_keys.py`
  (NEW) now proves each key authenticates and **never prints, logs or writes a key value**. It
  immediately found a real problem: `OPENROUTER_MODEL` was `meta-llama/llama-3.3-70b-instruct:free`,
  which OpenRouter has **RETIRED**. The key authenticated fine, so nothing looked wrong until a call
  returned 404 — and this is ADR-0026's **universal fallback**, the bucket every module drops to when
  its own quota is spent, i.e. a safety net that would only be found missing when it was needed. The
  Gemini bucket was sitting at its daily 429 that same day. Replaced with `google/gemma-4-31b-it:free`,
  picked from the live model list and verified by a real completion that came back correctly in
  Bengali ("জ্বর"). All three keys now authenticate.
- Decided: **ADR-0066** (a)–(m), with three rejections — no private copy of `bringIntoView` in the
  medic portal; not removing the S37 perspective to make smooth scrolling work; and not fabricating
  or auto-rotating API keys.
- Broke / problem: ⚠ **two `.gitignore` rules had NEVER worked.** An inline `#` is not a comment in
  `.gitignore` — it is part of the pattern — so `*.db.*.bak` and `!*.env.example` each matched
  nothing, and **six pre-migration database backups are tracked in git** as a result. The patterns
  are fixed and the new backup is correctly ignored, but `.gitignore` cannot untrack what is already
  tracked: removing those six from the index is a repo-content decision left to the human. **No
  secret is exposed** — `backend/.env` has never been committed and no provider key prefix appears in
  any tracked file or any commit in history, both verified. Also: one transient run showed 10
  `FileNotFoundError` errors in the documents tests; they did not reproduce in three subsequent full
  runs and pass in isolation — recorded, not explained.
- ⚠ **Four pinned test literals were UPDATED, not weakened** (the auto-mode hint wording, the
  listening banner's size/weight, and two references to the helper that moved). Every intent is
  preserved and re-stated in place, and the auto-mode test now asserts the PROPERTY directly — "the
  auto-mode sentence must not ask for a tap" — instead of matching one exact sentence, which is
  stronger than what it replaced.
- Verified: **1056 passed, 2 skipped, 0 failures** (was 1031/2). New files:
  `test_kiosk_containment_s41.py` (15) and `test_medic_intake_editor_s41.py` (8); the S40 file gained
  2. All new assertions were **proved non-vacuous against the pre-fix HEAD blobs**. Browser: the
  transcript tested with short/long-Bangla/long-English/Banglish/unbroken-Bangla/unbroken-Latin at
  1280, 768 and 375 px — **nothing escapes at any width and there is no horizontal page scroll**;
  assistant bubbles expand rather than clip; the medic Save button now lands in view; the synthetic
  phone now finds no patient; the doctor portal still shows both EHR buttons and the S39 name
  provenance. Clean consoles on fresh tabs for all three portals.
- ⚠ **Real-microphone status — the distinction matters and is kept:** the successful real-mic run is
  the **HUMAN's**, reported by them and **corroborated** by the dev DB, which holds mic-sourced
  Bengali utterances ("আমি ব্যথা পেয়েছি") timestamped 2026-08-14 18:08–18:11 on visit 23, a visit
  that reached `reviewed`. **This session did NOT and could not perform a real-mic verification** —
  the browser here reports `microphone: denied` with no audio input labels. Nothing above is claimed
  as agent-verified microphone testing.
- Deferred: rotating the 3 keys (human-only, and the checker is ready for it); untracking the six
  committed `.bak` files; **Step S5**; the mid-turn word-loss rule #1 decision; formal **WER**; the
  Edge run. Appearance remains unclaimed — still no screenshot, since the Browser pane composites no
  frames here.
- Next: **a human pass over the kiosk with a real microphone**, checking the one thing only a person
  can judge — whether the open-microphone banner, the bounded speech box and the three-step strip
  make the screen read as *simple* to someone who has never used a computer.

## Session 40 — 2026-08-14 — **A backtick in a comment had killed the whole Medic portal; the patient kiosk becomes TWO COLUMNS with one thing emphasised at a time** — 1005 → 1031 tests
- Did: root-caused and fixed the reported Medic-portal outage, gave the kiosk the clarity redesign
  (1A–1F), and closed the test gap that let the outage ship. **One new ADR: 0065.** **No backend file
  was touched** — no route, service, schema, migration, FHIR builder, PDF renderer, OTP path or auth
  code. **Alembic stays 0014, 18 tables, no new dependency.** **No module changed status; M15 stays 🟨.**
- **THE MEDIC BUG — one root cause, both reported symptoms, and it was never the backend.** S39 added
  a developer note inside `renderPostReferral()`'s **template literal**, written as an HTML comment,
  and the note named the `patients` table **in backticks**. A backtick inside a template literal ends
  it, so the browser parsed the next word as code: `Uncaught SyntaxError: Unexpected identifier
  'patients'`. A syntax error is not partial — the entire `<script>` block is discarded before one
  line runs, so **every function it declared was undefined**. `login()` did not exist, which is
  exactly why "ড্যাশবোর্ডে প্রবেশ করুন" did nothing at all; and `tickClock()` never ran, which is why
  the S38 clock sat on its "—" placeholder. **The reported "no time is shown" was not a second bug.**
  The `304 Not Modified` lines were a red herring: every asset was served correctly and one of them
  could not be parsed.
- **The fix is WHERE the note lives, not how it is escaped.** Escaping the backticks would have
  worked and left the trap armed. The paragraph moved into the existing `/* S39 */` comment above the
  function, which already explained the same removal. Verified in a real browser: the dashboard
  opens, `👤 Staff: Medic Rahman`, and the clock ticks (`১১:২৪:৩৯ PM`, `শুক্রবার, ১৪ আগস্ট, ২০২৬`) —
  clicked through in **Bangla**, on the exact button text that was reported.
- **⚠ Why 1005 passing tests could not see it, and what now can.** Every frontend test here is a
  static-source assertion (S28: no vitest, no jsdom), and the file still *contained* every string
  those tests search for — the source was intact, only its **executability** was gone. That is the
  gap S39 wrote down about itself ("no browser has rendered the new portal DOM"). Now closed in two
  layers: a dependency-free ban on the exact construct, and a `node --check` parse of every inline
  block and shared script that **skips with a reason** when node is not on PATH (one
  requirements.txt, Windows and Arch — no Node dependency was added). **Both layers were proved
  non-vacuous against the HEAD version of the file before it was fixed.**
- **KIOSK — the screen is now split by WHOSE side of the conversation it is.** Left = everything the
  machine does (robot, status, thread); right = everything the patient does (their live words, the
  read-back, the mic, the buttons, the mode switch). It had been one tall column, so "where the AI
  is" and "where I speak" were the same place, stacked, with the patient's own words in the middle of
  the pile. ⚠ **Done with grid PLACEMENT and no wrapper elements** — the DOM, every id, every
  `aria-live` relationship and the screen-reader reading order are unchanged, and one media query
  returns it to exactly the single column it was before.
- **The patient's own words are now the loudest thing on screen**: 1.3rem, upright (italic grey reads
  as "placeholder, not real yet"), in a box that turns red-edged while the mic is open — via a MORE
  SPECIFIC selector, never a second equal-specificity rule (the S33 dead-CSS trap). A caption labels
  it, because the box is **emptied between turns** and its own placeholder is gone after the first
  answer.
- **ONE emphasised thing at a time (the reported name-confirmation confusion).** While an answer
  waits to be checked, the mic row, the mode switch and the "tap the mic" hint step back and the
  read-back is the only lit thing. ⚠ **Dimmed, never disabled** — no `pointer-events: none`, no
  `display: none`, asserted per-rule by a test: a patient reaching for the mouse must still be able
  to use it. A three-step strip (1 I ask · 2 You speak · 3 You check) shows the order of the exchange
  without a sentence to read, and is lit **purely by CSS** from the two attributes the kiosk already
  publishes — it has no JS at all, so it can never claim the mic is open when it is not.
- **Automatic movement is `block: 'nearest'`, and that is the whole restraint.** An element already
  on screen does not move, so the helper is silent on a wide screen and acts only on a stacked or
  short one. Four call sites (mic opens, read-back opens, follow-up question opens, screen changes)
  and ⚠ **deliberately never per recognition result** — scrolling on every interim chunk is how a
  page becomes unusable while someone is talking. Honours `prefers-reduced-motion`.
- **REVIEW PAGE — the answers take column 1, what to DO about them takes column 2.** The three
  buttons had been a full-width bar at the very bottom, so the patient scrolled past every answer
  card to reach the one action the screen exists for. Assistant + still-missing notice + buttons are
  now one **sticky** rail beside the answers, "Confirm & Submit" first and full width. ⚠ Placed with
  **`order`, not `grid-column`** — an explicit column would create an implicit second track the
  moment any single-column rule applies, which is the exact bug S36 fixed here; auto-placement means
  one column really is one column, so `.no-float` and both media queries kept working untouched.
- Decided: **ADR-0065** (a)–(l), with four rejections — not escaping the backticks in place; not
  making node a hard test dependency; not banning HTML comments outright (it would have meant
  rewriting live markup that never broke); and no wrapper `<section>`s for the two columns.
- Broke / problem: nothing regressed, and one suspected bug turned out **not** to be one — a language
  toggle appeared to wipe the live transcript, but that was the test harness writing `textContent`
  directly; the real recogniser path already mirrors live text into **both** language slots (P1-2,
  rule #1). Verified in source rather than assumed, and now pinned by a test.
- ⚠ **Three pinned test literals were UPDATED, not weakened**, because the structure they describe
  genuinely changed: two `grid-template-columns` values on the review grid, and the assertion that
  the forced reflow precedes `scrollIntoView` — now asserted inside the shared helper the reflow
  moved into. Each test's stated intent is preserved and re-stated in place. No test was deleted or
  loosened.
- Verified: **1031 passed, 2 skipped, 0 failures** (was 1005/2). New files:
  `test_portal_inline_script_parses.py` (3) and `test_kiosk_s40_layout.py` (23) — 26 new.
  **Real-browser verification, which is what this session was missing:** medic login clicked in
  Bangla and the dashboard entered, clock ticking; doctor portal entered, **both ⬇ EHR record (FHIR)
  and (PDF) buttons present**, the S39 name-provenance line correctly reporting a name from an
  *earlier* visit; kiosk driven **end to end through a real session** (phone → OTP → conversation →
  10-card Bangla review) with a clean console on every page. Layout measured at **1280 / 900 / 375
  px** and in the `no-float` state: two columns at 1280 (774 + 400 conversation; 641 + 250 review,
  both columns top-aligned), one column at 900 and 375, **no horizontal scroll at any width**, mic
  and primary action in view without scrolling.
- Deferred: **pixel screenshots could not be taken** — the Browser pane was not displayed, so it
  composites no frames. Everything above is measured DOM geometry and computed styles, which is
  precise about position, size and state but says nothing about how it *looks*; a human still owns
  that judgement. Also unchanged and still open: **Step S5**, the mid-turn word-loss rule #1 decision
  (the human's), rotating the **3 API keys**, formal **WER**, and the Edge run.
- ⚠ Note for next session: driving the kiosk end to end left **one synthetic in-progress visit**
  (phone `1999000111`, synthetic Bangla answers) in the dev DB. It was never submitted, so it sits in
  the medic queue as a waiting case. Delete it or ignore it — it is test data, not a patient.
- Next: **a human pass over all three portals in a real browser** — the S38/S39 walkthrough still
  stands, plus this session's kiosk redesign, where the one question only a person can answer is
  whether it now reads as *simple* to someone who has never used a computer.

## Session 39 — 2026-08-14 — **The patient NAME learns where it came from, the medic can finally record BLOOD SUGAR (with the context that makes it mean anything), and the EHR record gains a human-readable PDF rendered from the same FHIR bundle** — 931 → 1005 tests
- Did: a continuous inspect → root-cause → implement → test → verify → fix loop over one reported
  bug and two requested features, plus a redundancy audit. **One new ADR: 0064** (a–o, with ten
  rejections). **Alembic 0013 → 0014** — two columns on `patients`, no new table, 18 tables
  unchanged. **Two new Python dependencies and one new binary asset** (see below — the first deps
  added since S30, and the reasons are recorded before the code). **No module changed status; M15
  stays 🟨.**
- **THE NAME BUG — the root cause was not invention, and that mattered for the fix.** `patients` is
  keyed by **phone number**, so `display_name` is patient-scoped and **permanent**: a name recorded
  in one visit is inherited by every later visit on the same number. Reproduced in the dev DB
  (read-only): `audit_log` #54, 2026-08-13 17:44, actor 1 — a **staff** edit wrote "মাশরাফি" onto
  patient 7 through the medic form; **visit 18 the next day** is a different visit by the same phone
  in which the patient never stated a name, and the portal showed it anyway. Keeping the name is
  right — a returning patient is the same person. Showing it as though it had been established
  *here* is not. So: the AI auto-fill now **writes an audit row** (it previously wrote nothing at
  all, so a model-written name was untraceable forever after — an accountability hole quite apart
  from this bug); `services/identity` **derives** provenance from `audit_log` with **no new column**;
  and both staff portals print the origin under the name. ⚠ A staff edit records no visit — but it
  records **when**, and a name written before this visit began **provably** did not come from it, so
  that case is reported as `from_this_visit: false` rather than left silent. An edit made *during*
  the visit stays `None`: it could have come from the patient in the room or a paper form, and "we
  cannot tell" is the honest answer. A name written before S39 has no audit row and reports
  `unknown`, never a guess.
- **Also removed: `display_name` on `POST /api/patients/lookup`.** It was the third writer of the
  field and the only unaudited one, and **no client ever sent it**. Identity now enters through
  exactly two paths and both are audited.
- **BLOOD SUGAR — what was actually missing was the FIELD.** S38 shipped the glucose reference
  *chart* and no place to write a *reading*, so "the medic cannot edit sugar" was literally true:
  there was nothing to edit. Editing before referral already worked (S37 moved vitals into the case
  workspace), so the requirement was met by adding the value, not by changing a permission — and a
  test now pins that a medic edits pre-referral, that the referral still works afterwards, and that
  an unauthorised actor still gets a 403. ⚠ **The reading and its measurement context are ONE fact
  and are refused apart**, server-side and before the write: a fasting 6.5 and a random 6.5 are
  different findings, and a number stored with no context cannot be read safely by anyone later.
  The context is constrained in the **database** as well as the schema. ⚠ **No band, class or
  interpretation is stored or computed anywhere** — the value is reported, the published chart is
  shown beside it, and a clinician reads one against the other (rule #2; ADR-0060's
  `glucose_reference()`-takes-no-argument rule, now that a value exists to be tempted with).
  ⚠ **HbA1c is deliberately not recordable**: a percentage, not mmol/L, and a lab result rather than
  a bedside reading — it stays a reference row so one column never holds two quantities.
- **EHR PDF — a second RENDERING, not a second record.** `services/ehr_pdf` **does not read the
  database**: it is a pure function of the dict `ehr_export.build_fhir_bundle()` already returns, and
  it typesets that bundle's own section narratives (a FHIR document Bundle is *defined* as a
  Composition carrying human-readable XHTML per section — the standard's own answer to "what should
  a person see"). So the PDF cannot hold a fact the JSON lacks or omit a section it has; a test
  forbids `db.query`/`db.get` anywhere in the module, and another asserts every Composition section
  appears in the rendered page. New kind `ehr_pdf` beside `ehr_bundle`, same route, same `documents`
  table, `application/pdf`. The doctor now has both buttons through **one** download function.
- **⚠ The dependency decision was made by BANGLA, not by PDF features.** Bengali needs conjunct
  formation and vowel-sign reordering; a library that lays out one glyph per codepoint prints the
  patient's own words wrongly, which is a **rule #1 defect in the one export a human actually
  reads**. ReportLab cannot shape Bengali; **fpdf2** delegates to **uharfbuzz**. Both ship wheels for
  Windows x64 and manylinux. The font — **Noto Sans Bengali (OFL-1.1, 463 KB, `assets/fonts/` with
  its licence)** — ships **in the repo** rather than being found on the machine: Windows' Nirmala is
  not redistributable and not on Arch, and a clean Arch box may have no Bengali font at all. The
  renderer **REFUSES** (raises `PdfFontUnavailable`) rather than emitting a document whose Bangla
  would be wrong.
- **The one feature added beyond the brief, and why it is not invention:** S39 put a blood-sugar
  VALUE on the doctor's case screen, and the reference chart existed only in the medic portal — a
  number with no chart on the very screen where it is interpreted. The chart **moved** to
  `frontend_shared/staff.js` and both portals mount the same one; nothing was copied. ⚠ The doctor's
  glucose row is **read-only**: intake is the medic's to own (`portal_roles` §5), and a second editor
  would be the duplicate-form defect this same session deleted.
- **Redundancy audit — one real duplicate found and removed.** The medic's post-referral screen had
  its own identity editor AND its own weight editor, writing the same `patients` row through the same
  PATCH as the Intake & Vitals form, but covering a **subset** of the fields (no height, no BP, no
  sugar). A leftover from before S37 moved editing ahead of the referral. Both are gone with their
  two save functions; the screen is now a read-only snapshot that says where editing happens. Also
  unified: four different "no name" placeholders became one `patientNameLabel()`.
- Decided: **ADR-0064** (a)–(o) with ten rejections — no `display_name_source` column; no re-asking
  returning patients; no heuristic "verification" of an AI-extracted name; no single glucose column
  without its context; no band/`is_diabetic` column; no `measured_at` column; no glucose entry in the
  handover check; no HTML-template or DB-driven PDF; not ReportLab and not an OS-resolved font; and
  no `"pdf": PdfWriter` in the utterance-grain writer registry.
- Broke / problem: **four real defects found, three of them by LOOKING AT THE OUTPUT rather than by a
  test.** (1) `kg/m²` printed as **`kg/m`** — a different unit — because the shipped font has no
  U+00B2 and **a missing glyph does not raise, it VANISHES**; the narrative now uses the UCUM `kg/m2`
  it already codes, and a test walks every character the renderer will draw against the font's cmap.
  (2) `<br/>` inside a table cell was dropped, so the English and Bangla of one field rendered as one
  run-on string. (3) The narrative parser treated `<b>` as a *prefix*, which is right for
  `<b>Patient said:</b> …` and silently **reversed** `Urgency tier: <b>low</b>` into "low Urgency
  tier:"; emphasis is no longer tracked and text is captured in document order. (4) `<li>` red flags
  ran together into one paragraph — rule #3 makes their legibility a safety property, so they are
  bullets now. ⚠ **Self-inflicted:** a failed `write_text` on a `unicode_escape`-mangled string
  **truncated `frontend_shared/staff.js` to zero bytes**; it was rebuilt from its HEAD blob plus this
  session's additions and verified as purely additive (`git diff --stat`: 196 insertions, **0
  deletions**), then `node --check`ed.
- ⚠ **Three existing S38 tests were MOVED, not weakened.**
  `test_the_glucose_panel_refuses_to_be_a_single_number`,
  `test_the_glucose_panel_never_reads_a_patient_value` and
  `test_glucose_bands_carry_both_unit_systems` now read `STAFF_JS` instead of `MEDIC` because the
  panel moved to shared code. **Every assertion is byte-identical.** No test was deleted, weakened,
  or changed to make a failure disappear.
- Verified: **1005 passed, 2 skipped, 0 failures** (was 931/2). New files:
  `test_patient_name_provenance.py` (10), `test_intake_vitals_glucose.py` (16),
  `test_migration_0014.py` (5), `test_ehr_pdf.py` (26), `test_staff_portal_s39.py` (17) — 74 new.
  Alembic upgrade AND downgrade exercised on throwaway SQLite files. A 34-check HTTP walkthrough ran
  against a real uvicorn on a **throwaway seeded DB** (rule #4 — the dev DB was read once, read-only,
  and never modified: mtime unchanged), covering all three name-provenance cases, pre-referral
  glucose editing, correction, the 400 on a context-less reading, the 403 on an unknown actor, the
  referral, the doctor receiving the value, and both exports. PDF text was read back out through the
  document's own ToUnicode CMap and the verbatim Bangla round-tripped exactly; the rendered page was
  **inspected visually in Chrome** and the Bengali conjuncts and vowel signs are correctly shaped.
- Deferred: the browser-pane pass over the two staff portals themselves (the pane restricts localhost
  to the launch.json port, which was occupied by a server this session did not start and did not
  stop) — the portal changes are covered by static-source tests and the HTTP walkthrough, but **no
  human or headless browser has rendered the new portal DOM**. Still open from earlier cycles:
  **Step S5**, the mid-turn word-loss rule #1 decision (the human's), rotating the **3 API keys**,
  formal **WER**, and the Edge run.
- Next: **a human pass over the two staff portals** — the S38 walkthrough in `current_task.md` still
  stands, plus the three S39 additions: the name-origin line under the patient name, the blood-sugar
  row in Intake & Vitals, and the doctor's ⬇ EHR record (PDF) button. And one judgement only a person
  can make: whether the PDF is the right shape for whatever this clinic would actually file or hand
  to a patient.

## Session 38 — 2026-08-14 — **Staff-portal UX + clinical workflow hardening: a real Dhaka clock and a real date policy, an editable intake form with derived BMI, a glucose REFERENCE (not a limit), the prescription inline at the bottom with searchable tests, a FHIR R4 EHR export, M16 widened to tests + case-context, and the four workflow features S37 deferred** — 767 → 931 tests
- Did: a nineteen-item brief worked continuously (inspect → plan → implement → test → verify →
  fix → document), across both staff portals and the backend behind them. **Four new ADRs: 0060**
  (the derived/stored boundary + the four workflow features), **0061** (the date policy), **0062**
  (the FHIR export), **0063** (the M16 widening). **Alembic 0012 → 0013** — the first schema change
  since S25, and deliberately small: **one column and one table**, with the reasons and the rejected
  alternatives recorded before either was written. **No new Python dependency.** **No module changed
  status; M15 stays 🟨.**
- **The rule that shaped the session: most of it added no storage at all.** The medic's referral
  history, the FHIR bundle, the completeness detail, the BMI and the whole reference layer are
  questions asked of rows that already exist. Where the brief asked for something with genuinely no
  home, it got exactly one: `patients.height_cm`, and a single `clinical_notes` table serving BOTH
  the recall and the back-channel because they are the same shape.
- **MEDIC — A1..A7.** "Triage" is now explained where the word is used (a one-click disclosure, not
  a tutorial: worst tier first, then longest wait, and why an unassessed case sits above Moderate).
  The **10/10 line became a control** — ten segments instead of one bar, verified drawn differently
  from merely filled, keyboard-reachable, and clicking it lists exactly which fields are still empty
  from the server's own `fields_empty`. **Intake & Vitals was rebuilt as a working form**: labelled
  fields instead of five bare placeholders, prefilled with what is already stored, a button that
  says *Edit* once anything has been recorded, and it survives a language toggle mid-edit. Height
  joins weight and BP, and **BMI computes live as they are typed** — from
  `GET /api/reference/bmi`, so the published cut-offs exist in one place, reported under BOTH the
  WHO international and the **WHO Asian action points** (a BMI of 24 is "normal" internationally and
  "increased risk" for this population).
- **The medic queue's auto-refresh was silently destroying work.** It already ran every 15 s, and
  `searchPhone()` renders into the same list — so a medic looking up a returning patient watched
  their result replaced by the full queue fifteen seconds later, for no visible reason. The timer is
  now shared (one copy, not one per portal), **holds while a search result or another list is on
  screen**, holds while the tab is hidden and refreshes once on return, says which of those states
  it is in, and **no longer re-runs the entrance stagger on a background refresh** — a healthy queue
  had been re-flashing every 15 seconds.
- **A6 — the human asked for "a diabetic limit"; there isn't one, and shipping one would have been
  the most dangerous thing in the session.** `glucose_reference()` takes **no argument at all**: it
  returns the published chart — fasting / 2-h OGTT / random / HbA1c — each with the sample conditions
  that make its numbers mean anything, both mmol/L and mg/dL, the **WHO/ADA disagreement at the
  lower fasting bound stated out loud** rather than silently resolved, and a source per row.
- **DOCTOR — B1..B7.** The prescription form **moved inline to the bottom of the case** instead of
  replacing it, so writing a prescription no longer means losing sight of the case it is for.
  Advice/Lifestyle and Required Tests became **two vertical cards** side by side, stacking with no
  breakpoint to maintain. **Required Tests became a token editor** over a ~50-entry bilingual
  vocabulary (a Python module, not a table): type to search, click to add, type anything not on the
  list, remove any chip — and **Enter always commits what was TYPED, never the highlighted
  suggestion**, because the doctor's own words must win. "Assigned (0)" no longer shows *"Select a
  patient from the queue"* over an empty queue: the workspace now says what its emptiness means, and
  the placeholder is restored when a case is closed (it never was before).
- **B1 — "Accept & Write to EHR" now actually produces an EHR record.** An **HL7 FHIR R4 document
  Bundle** (Composition, Patient, Encounter, Organization, Practitioner, LOINC-coded vital-sign
  Observations with UCUM units, RiskAssessment, and MedicationRequest/ServiceRequest/Condition once
  a prescription exists), downloadable as `application/fhir+json` through the existing `documents`
  table and route — no new subsystem, no dependency. ⚠ Claimed honestly as *structurally valid and
  semantically conservative*: not certified, not profiled, and a receiver must still map it.
  ⚠ **The AI's suggested condition is excluded from the bundle entirely** — its disclaimer does not
  survive ingestion by another system, so the data must not travel; the doctor's own typed diagnosis
  IS exported. ⚠ `critical` is not silently downgraded: it maps to `high` in the standard
  `risk-probability` set AND travels exactly in our own system, because the standard set has no
  "critical".
- **B5 — the date policy, by CATEGORY.** "Cannot use previous date anywhere" applied literally would
  rewrite the record, so: system/historical timestamps are **never touched**; the prescription date
  must be **today**; a follow-up or recall must **not be in the past**. Enforced server-side (a
  `min` attribute is a courtesy, not a control) and BEFORE the write, so a rejected date reaches
  neither the stored payload nor the .docx. ⚠ **A real bug fixed on the way:** the form stamped
  `toISOString()`, the **UTC** date — so a prescription written between midnight and 6 a.m. Dhaka
  was dated the previous day on the document the patient carries to a pharmacy.
- **A7/B5 — one clock, and it is Bangladesh's.** A live header clock in both portals (real date,
  running 12-hour time with AM/PM, ticking, bilingual), and every stored timestamp re-rendered
  12-hour. ⚠ Server-side "today" uses a **fixed UTC+06:00 offset, not `ZoneInfo`**: Windows ships no
  IANA tz database and `zoneinfo` raises on this project's own dev machine. Bangladesh has had no
  DST since 2010, so the fixed offset is exact rather than approximate, and identical on Windows and
  Arch with nothing installed.
- **B6 — M16 widened, with privacy enforced structurally.** One service, one seam, one round-trip,
  now covering medicines (uses, dosing ranges, age considerations, cautions, contraindications,
  adverse reactions), diagnostic tests (what/why/measures/preparation), and — on the doctor's
  **explicit opt-in** — which tests might suit this patient. ⚠ **The web search receives the typed
  question and nothing else, by signature**, so no future edit can send clinical data to a third
  party; the LLM's case context is de-identified (age, sex, area, vitals, the derived 10 fields) and
  carries **no name, no phone and no raw transcript**. Suggested tests come back as chips the doctor
  CLICKS to insert — nothing is ordered until a human generates the prescription. A **new** output
  guard catches patient-directed instructions; ⚠ it deliberately does NOT reuse M7's dosage rule,
  because here a dosage range is the correct answer. A flagged reply is **delivered with a stronger
  server-authored disclaimer**, not deleted.
- **C1–C4 — the four features S37 deferred, all built.** *Referral history:* derived from
  `audit_log.actor_id` (which S37 added), so no new storage — and it **reports what it cannot
  attribute** rather than inventing an owner for pre-S37 referrals. *Per-field verification:*
  `verified_by`/`verified_at` inside the existing `summary_fields` JSON, so a medic can record "I
  read this and it is correct" **without editing the field** — which was previously the only way,
  and put a false edit in a medical record. An empty field cannot be verified. *Recall* and
  *doctor→medic back-channel:* one `clinical_notes` table, addressed to a **role** not a person, no
  thread, no reply, no read receipts.
- Decided: ADR-0060 (a)–(i) with six rejections, ADR-0061 (a)–(f) with four, ADR-0062 (a)–(j) with
  five, ADR-0063 (a)–(h) with five.
- Broke / problem: **three defects found and fixed during the loop, plus three of my own.**
  (1) the auto-refresh eating a phone search (above); (2) the UTC prescription date (above); (3) the
  doctor workspace never restoring its placeholder after a case was opened, so switching to an empty
  scope left the previous patient's case on screen. Mine: the completeness meter's negative margin
  made it 139px wide inside a 131px wrapper (measured) and it scrolled inside itself; the header's
  right-hand group does not wrap, so adding a clock pushed the page 17px sideways at 375px; and the
  first draft of `renderWorkspaceState` was never reached because `renderQueue` returns early on the
  empty branch — which is *exactly* the case B7 reports. All three were caught in the browser, not
  by a test, and the third now has a test.
- ⚠ **Three existing tests were modified, and this is the honest account of why.** Two fixture date
  literals (`test_prescription_docx`, `test_doctor_history`) were made relative — no assertion in
  either file ever read them, and leaving them would have rotted into a 400 under the new date
  policy. One assertion in `test_assistant` checked the exact phrase *"drug-information assistant"*
  in M16's system prompt; the module legitimately widened past drugs, so it now asserts the property
  that mattered (M16's own prompt, and that it is INFORMATION-ONLY). **No test was weakened or
  deleted, and no test was changed to make a failure disappear.**
- Verified: **931 passed, 2 skipped, 0 failures** (was 767/2). New files:
  `test_clinical_reference.py` (30), `test_migration_0013.py` (6), `test_staff_portal_s38.py` (39),
  `test_date_policy.py` (11), `test_ehr_export.py` (28), `test_workflow_notes.py` (31), plus 15 in
  `test_assistant.py` and 4 in `test_medic_summary.py`. Live browser run against a real uvicorn and
  a **throwaway** SQLite DB seeded with 8 synthetic cases (rule #4 — the real dev DB was NOT
  touched this session): the clock, the refresh line, the triage explainer, the segmented meter and
  its detail panel, the rebuilt intake form saving height/weight/BP with live BMI, the glucose
  chart, the inline prescription with its pinned dates, test search → select → free-text → remove,
  the FHIR bundle generated and re-read (10 resources, Composition first, `application/fhir+json`),
  per-field verify (AI-Extracted → ✔ Checked with the value unchanged), a recall and a handover note
  round-tripping into the medic inbox, and the referral history attributing a live forward. Layout
  checked at 1280 / 768 / 375 in both languages with **no page-level horizontal scroll**.
- Deferred: the medic portal has no recall LIST of its own (recalls appear in the shared inbox
  filtered by `kind`, which is enough for one clinic and avoids a fourth sidebar tab); the FHIR
  bundle is not validated against a national implementation guide; the test vocabulary is
  Bangladesh-outpatient-shaped and not exhaustive. Still open from earlier cycles: **Step S5**, the
  mid-turn word-loss rule #1 decision (the human's), rotating the **3 API keys**, formal **WER**,
  and the Edge run.
- Next: **a human pass over both portals.** Everything above is test-pinned and was exercised in a
  browser, but three things only a person can settle: whether the glucose reference reads as
  *reference* rather than as guidance, whether the FHIR export is the right shape for whatever
  system this clinic would actually hand it to, and whether the doctor→medic note is a channel this
  clinic wants at all or a source of noise.

## Session 37 — 2026-08-13 — **The staff portals get their ROLES: a medic operations layer (triage order, wait, completeness, pre-handoff vitals, advisory handover check) and a doctor longitudinal layer (patient timeline, prescription history, completed-cases scope); plus a staff depth/motion layer** — 723 → 767 tests
- Did: a full audit-then-build cycle over `/medic/` and `/doctor/`, loop-engineered (read the real
  code → find the gap → smallest fix → targeted tests → browser measurement → regression → next).
  **ADR-0058** (features + data ownership) and **ADR-0059** (the motion layer). **Alembic stays
  0012 — `models.py` and `migrations/` are untouched, no migration, no new dependency.**
  **No module changed status.** M15 stays 🟨. New reference doc: `agent_docs/portal_roles.md`.
- **Phase 1 — the real-mic status was corrected across the docs.** The human confirmed at the start
  of this session that the real-microphone test of the S33–S36 voice changes **has now been done**.
  ⚠ Recorded exactly that far and no further: **no per-claim results were supplied and none are
  documented**, and **no defects were reported back into this session**. So the docs now say the
  run happened and that its detailed outcomes were not itemised — they do NOT claim a pass on the
  three specific S36 claims (the completion vocabulary, the eleven-digit phone stop, audibility).
  The S25 evidence, which IS itemised, is left exactly as it was.
- **Finding 1 — the medic queue was sorted by the wrong thing, and it is the role's whole job.**
  `list_visits` returns `started_at DESC`, so a Critical patient who submitted 40 minutes ago sorted
  BELOW a Low-risk patient who submitted seconds ago. Triage order is now worst tier first, then
  longest wait first. Measured live against the dev DB: `critical 447m · high 1554m · medium 2860m ·
  medium 1530m · medium 1498m · medium 1451m · medium 85m` — worst first, and strictly
  longest-waiting first inside the Medium band. ⚠ An UNASSESSED case deliberately sorts BETWEEN High
  and Medium, not last: "we do not know yet" is not "we know it is fine". `sort=recent` still selects
  the old ordering, and a phone search is never re-sorted (that list is a chronology).
- **Finding 2 — the medic could record vitals only AFTER handing the case over.** This is the
  clearest workflow defect of the session and it was invisible in the docs: the weight/BP/identity
  editor existed only inside `renderPostReferral()`, the screen shown after `POST /assign`. Every
  case therefore reached the doctor with no weight and no BP. The fix moves the MOMENT, not the data
  — same `patients` row, same `PATCH /patients/{id}/vitals`, same audit action, now in the case
  workspace before the referral. Exercised end to end in the browser: saving 68.5 kg / 130/85 made
  the `vitals_missing` advisory disappear on the same screen.
- **Finding 3 — `prescriptions` was a WRITE-ONLY table.** Rows were created by `POST /prescription`
  and nothing in the codebase ever read one back, so a repeat medication was undetectable from
  inside the doctor portal, and the doctor could see only the single visit in front of them.
  NEW `GET /patients/{id}/history` returns prior visits + prior prescriptions (from **every**
  doctor — a repeat is only detectable if the other doctor's prescription is visible too).
  ⚠ It carries **no transcript**: a prior visit is opened through the existing
  `GET /api/visits/{uuid}` and read from the one immutable copy (rule #1), and it ranks, trends and
  interprets **nothing** (rule #2).
- **Finding 4 — reviewing a case made it vanish.** `POST /review` ended by dropping the case from the
  workspace, and the doctor queue lists only `awaiting_doctor` — so a doctor who accepted a case and
  then wanted to write its prescription had no route back except a phone search, even though
  prescribing after accepting is the normal order. The case now stays open and changes state, the
  review controls are replaced by a statement of what happened (`POST /review` would 409), the
  prescription form stays available, and a **Completed** scope lists the doctor's finished
  consultations. Verified as a full round trip in the browser: review → controls hidden → the case
  appears under Completed and leaves the working queue → reopened → prescription written → it shows
  up in the history panel with a working `.docx` link.
- **Finding 5 — the handover was blind, and the fix is deliberately toothless.** NEW
  `GET /visits/{uuid}/handoff` reports what the doctor is about to be missing. ⚠ It is **advisory
  and can never block a forward**: a medic must be able to push a Critical patient to a doctor with
  incomplete paperwork rather than hold them for it. A red flag is `info`, never `warn` — it is the
  model's finding about the patient, not paperwork anyone can complete. Two tests pin the safety
  property (one behavioural, one static over the shipped `submitForward`).
- **Finding 6 — the referral was the one staff write with no actor.** `audit_log` recorded which
  doctor RECEIVED a case and never which medic sent it. `AssignRequest.editor_id` is optional
  (walk-in/dev callers never had one) and lands in the existing `audit_log.actor_id`; an unknown or
  non-staff editor is a 403, because a wrong actor is worse than no actor.
- **UI/UX — `frontend_shared/motion.css`, staff portals only (ADR-0059).** Depth on cards, a tier
  rail per queue row, staggered entry that follows the triage ranking, a pop on a changed stat, a
  pulse reserved for urgency alone, skeleton loading rows, and role identity that keeps the two
  portals from reading as one screen (medic = amber `TRIAGE` operations desk; doctor = indigo
  `CLINICAL` workspace with a timeline spine and a Queue/Completed control).
  ⚠ **Accessibility outranks the effect**: every `animation` and every `@keyframes` lives inside
  `@media (prefers-reduced-motion: no-preference)` — proven by two tests that parse the shipped
  stylesheet — and nothing is conveyed by movement alone.
- Decided: **ADR-0058** (a)-(h) with six explicit rejections, and **ADR-0059** (a)-(h) with three.
  The load-bearing one: **a new staff view is a different QUESTION asked of existing rows, never a
  new copy of them** — hence zero new tables and zero new columns.
- Broke / problem: **four real defects found and fixed during the loop, plus one measurement trap.**
  (1) The "Longest wait" tile printed raw minutes — a clinic that has been open a while produces
  `2861m`, which nobody parses; it now uses the same formatter as the rows, and `waitLabel` grew a
  days band after a dev row legitimately showed `536h 50m`. (2) The doctor timeline printed the raw
  schema code `awaiting_doctor` at a doctor — fixed with a `STATUS_LABELS` map (ADR-0030 f: codes on
  the wire, labels in the frontend). (3) At 375px the page scrolled sideways: inline pixel widths
  (a 280px search box, a 220px doctor picker) exceed the screen; relaxed in the staff layer.
  (4) **The tier rail was repainted teal the moment a medic SELECTED a case** — shared.css's
  `.queue-item.active { border-left: 4px solid var(--secondary-color) }` outranked the rail colour;
  measured #EF4444 → #0D9488 on click, now restored so the tier outlives selection.
  ⚠ **The measurement trap, recorded because it will recur:** the Browser pane was not displayed, so
  the page was not compositing and **CSS transitions freeze mid-flight** — `getComputedStyle`
  returned stale colours and made a correct stylesheet look inverted. Injecting
  `*{transition:none!important;animation:none!important}` before measuring is the fix; nothing was
  wrong with the CSS.
- One pre-existing layout fault was fixed while checking it: shared.css sets only
  `min-height: 100vh`, so a long case grew the whole page instead of the two panes scrolling
  independently — the queue sidebar had stretched to **3,399px** and scrolled out of reach while a
  doctor read a case, defeating the point of `overflow-y: auto` on both panes. The staff portals are
  now pinned to the viewport, released again under `@media print`.
- No existing test was weakened, changed or deleted. All 723 prior tests still pass unmodified.
- Verified: **767 passed, 2 skipped, 0 failures** (was 723). New files: `test_medic_triage.py` (18),
  `test_doctor_history.py` (10), `test_staff_portal_ui.py` (16). Live browser run against a real
  uvicorn + the real dev SQLite: triage order, the load strip, the wait/flag/meter chips, the
  pre-handoff vitals save, the advisory checks re-evaluating, the doctor timeline (6 prior visits),
  the review → Completed → reopen → prescribe → history round trip, empty/error/search-miss states,
  and layout at 1280 / 768 / 375 in both languages with **no page-level horizontal scroll and no
  overflowing element**. ⚠ Two synthetic dev-DB rows were changed by that run (one visit reviewed,
  one prescription created) — noted in `test_log.md`, synthetic data only (rule #4).
- Deferred: a per-field "verified" flag for the medic (needs new per-field state; `source == 'human'`
  already gives the weaker `fields_verified` signal), a medic completed-referrals list (nothing
  attributes a referral to an individual medic — refused with a 400 rather than guessed), doctor-side
  follow-up/recall scheduling, and a doctor→medic back-channel. All recorded with reasons in
  `portal_roles.md` §6. Also still open from earlier cycles: **Step S5**, the mid-turn word-loss
  rule #1 decision (human's), rotating the **3 API keys**, formal **WER**, and the Edge run.
- Next: **a human pass over the two staff portals** — walk the medic triage flow and the doctor
  timeline/prescription flow on a real screen and report anything that reads wrong. The code side of
  S37 is complete and test-pinned; what no test can settle is whether the triage ordering matches how
  this clinic actually wants to work, and whether the motion reads as "clinical" rather than "busy".

## Session 36 — 2026-08-13 — **The patient session becomes a real boundary (epoch + endSession); MCP evaluated and REJECTED; the phone number ends its own turn; "ঠিক আছে" finishes the review; the raw transcript downloads itself** — 622 → 723 tests
- Did: worked all seven post-S35 hardening items in one continuous pass, loop-engineered
  (reproduce → root cause → smallest fix → targeted tests → browser measurement → regression → next).
  **ADR-0057.** **Alembic stays 0012** — no schema change, no migration, **no new dependency**.
  **No module changed status.** M15 stays 🟨. ⛔ **Step S5 was NOT implemented** — see below.
- **Finding 1 — the "alignment breaks at the final question" was the GRID, not the dock.**
  Reproduced and measured in a browser before touching anything: `setResumeMode()` hides
  `#summary-float`, and a hidden grid item stops being PLACED while its TRACK stays exactly where it
  was. Auto-placement then dropped `.summary-grid` into the narrow FIRST column — **471px → 170px,
  with a 231px card still inside it**, so every card overflowed its own column and the whole review
  jumped 188px left. Fixed with ONE rule (`.summary-body.no-float`) keyed to the same condition that
  hides the float, at (0,2,0) so it outranks both responsive overrides without depending on source
  order. Verified reversible: closing the dock restores `170px 471px` exactly. A second, smaller
  defect found by the same probe: the text column between the avatar and the 🔊 was an inline
  `flex:1` with no `min-width: 0`, so one unbroken 76-char token pushed the 🔊 out of the row —
  now `.resume-q-body` with `min-width: 0` + `overflow-wrap: anywhere`.
- **Finding 2 — the privacy one, and the largest change.** `resetState()` LOOKED like a reset and
  was not: the recognition ENGINE was still running (`r.onend` restarts it, so the previous
  patient's voice was transcribed into the NEXT patient's phone dock), `finalBuffer` still held
  their words, the review read-through kept reading their answers aloud, the phone ticker was never
  cancelled, and their summary cards stayed in the DOM. ⚠ **The dangerous one was none of those:
  every in-flight `api()` promise wrote into the new session**, because `state` is a module-level
  variable resetState() REPLACES. Worst case `verifyOtp()` — a late response installed the previous
  patient's `visit.uuid` into the new patient's session, so the new patient's answers would have
  been POSTed onto the old patient's visit. Clearing variables cannot fix a promise that has already
  resolved, so the fix is an EPOCH (`sessionToken()`), the same shape as S3's `armToken`. NEW
  `endSession()` + `startNewSession()`; eight async paths now check `mine()` before writing.
- **Finding 3 — MCP was evaluated and REJECTED, with the reasons written down (ADR-0057 b).** There
  is no tool-calling loop to attach it to (`call_module()` is one-shot); the round-trips are the
  scarce resource (ADR-0026, and M7 is in the live loop); a second context path would rebuild the
  disagreement S35 removed; and session scoping here is STRUCTURAL (a function not given visit B
  cannot return visit B), which a transport would weaken. The three responsibilities are implemented
  as explicit in-process functions in NEW `services/question_tools.py`. **What the rejection did not
  excuse:** the conversation handed to M7 was the ENTIRE unbounded history (now bounded to the most
  recent 24 turns — a normal ~18-turn visit is never truncated), and the model's question was only
  ever ASKED not to prescribe — it is now CHECKED on the way out by `unsafe_question_reason()`, with
  a deterministic server-authored fallback so the patient never loses a turn to the guard firing.
- **Finding 4 — a complete phone number now ends its own turn.** It is the one answer whose
  completeness is knowable the instant it arrives, and waiting `countdown_ms` for silence after it
  was a defect: trailing speech joined the SAME utterance, so a repeated digit pushed the count past
  eleven and `phoneFromSpeech()` returned null for a number already said correctly. Measured: stops
  at chunk 11 with the trailing words and the two extra digits excluded; nine digits and a number
  starting 02 keep listening. ⚠ The read-back is NOT skipped (ADR-0053's reason stands, and S35
  already made it button-free). Added the re-entry guard `sendOtp()` never had — four callers, each
  sending a real SMS.
- **Finding 5 — "ঠিক আছে" / "all right" finishes the review.** Measured against the shipped parser
  first: `সব ঠিক আছে`, `সবকিছু ঠিক আছে`, `সব ঠিক`, `all right`, `alright` and the "that is all"
  family ALL returned null, so the most natural way to say "everything is fine" was read back as a
  symptom and STORED as a correction — a loop the patient could not leave by speaking. Reuses
  `parseConfirmation()` (no second system); `all`/`সব` are YES words rather than filler, which is
  what makes "that is all" resolve at all. Only YES finishes; a real correction and an ambiguous
  sentence both reach the existing pipeline untouched.
- **Finding 6 — the raw transcript downloads itself at completion**, exactly once, not awaited,
  silent on failure, and DROPPED if the kiosk was handed over mid-render. Filename is now
  `raw-transcript-visit-<8>-<date>.docx` — "transcript" is ambiguous once a corrected text exists —
  carrying no name and no phone number. The stored `kind` is unchanged.
- **Finding 7 — two gaps, after checking that the other eight ideas were already solved.** The
  completion was SILENT on a kiosk where every question is spoken; it now says what happened and
  what to do next, through plain `speak()` (never `askAloud()`, which would open the mic on a
  finished visit). And the conversation screen answered "how much longer?" with nothing; it now
  shows `Question N of 4` **during the scripted opening only**, because that is the only stretch
  whose length is a fact — the M7 loop ends on completeness, and an invented denominator would lie.
- Decided: **ADR-0057** (a)-(g) + four explicit rejections.
- Broke / problem: **four defects created and caught during the loop, plus one caught by an existing
  test.** (1) `patient_context()` lost its docstring terminator when the body was rewritten —
  caught by a syntax check before any test ran. (2) A JS block comment was pasted into a Python
  file; same check. (3) My own comments inside `CONFIRM_YES`/`CONFIRM_FILLER` contained apostrophes,
  and `shipped_set()` parses the vocabulary by matching quoted tokens — so the prose `['that', 's',
  'all']` was silently READ AS VOCABULARY. **Caught by the pre-existing
  `test_the_two_vocabularies_do_not_overlap`**, which is exactly what it was written for; the
  literals now carry a warning not to use apostrophes in their comments. (4) `startNewSession()` was
  initially incomplete — it cleared all patient DATA but left the screen on the previous patient's
  view, so a future caller would have handed over a half-reset kiosk; the avatar clear, input mode
  and screen moved into it so there is nothing left for a caller to forget.
- Four existing tests updated, none weakened, all for the same reason: they pinned the hand-written
  teardown inside `confirmSubmit()` line by line, and that list is what S36 replaced with one seam.
  Each now asserts the NEW mechanism and is stricter than before — the timer test checks all FOUR
  cancels rather than the three somebody remembered, including the phone ticker the old list had
  simply missed. A fifth (`updateSubmitVisibility`) was widened by one term for Finding 5.
- Verified: **723 passed, 2 skipped, 0 failures** (was 622). New files: `test_kiosk_resume_layout.py`
  (8), `test_kiosk_session_isolation.py` (16), `test_question_tools.py` (27),
  `test_kiosk_phone_early_stop.py` (13), `test_kiosk_review_completion.py` (11),
  `test_auto_raw_transcript.py` (12), `test_kiosk_patient_feedback.py` (13).
  **Live browser run (the shipped handlers driven with scripted recogniser results, S33's method —
  NO microphone; ⚠ note real-mic STT/TTS *is* proven for the S25-era flow, S25's run passed, but no
  mic has ever exercised the S33-S36 voice behaviour, and S33-S35's "no microphone has EVER been
  used" phrasing is wrong and is corrected in current_task.md):** the review grid 170→659px with the dock open and back to `170px 471px` on close, no
  side-scroll at 1280x800 / 730x694 / 375x812 in both languages, avatar 64px and 🔊 44px across four
  question lengths; patient A → reset → patient B leaving ZERO of A's text in thread/grid/dock/phone
  /answer panel with `finalBuffer` empty, `recognition` null and the stale token invalid; a REAL
  in-flight response resolving 250ms after the reset failing to leak in all three of followup/answer,
  verify-otp and the profile fetch, with a CONTROL run proving all three still work normally without
  a reset; the phone stopping at chunk 11 and reaching OTP with exactly 1 lookup under four
  different race conditions; all six completion phrases submitting exactly once while a real
  correction and an ambiguous sentence submit zero; 1 auto-download with the raw filename and 0 on
  repeat; and one spoken completion line.
- Deferred: **Step S5 — STILL NOT IMPLEMENTED** (`no_speech_ms` watchdog, `max_answer_ms` cap,
  permission/visibility recovery), verified absent by inspection and now pinned by a test so no
  later session can assume it landed here. The one S5 item Finding 7 touches — recovery when mic
  permission is interrupted mid-answer — was left deliberately: it cannot be built without deciding
  what happens to the half-captured answer in `finalBuffer`, and that is the open **rule #1
  decision reserved for the human**. Also still open: rotating the **3 API keys** (human-only),
  formal **WER**, the Edge run, and the acoustic judgement on the paced TTS.
- Next: **REAL MICROPHONE VALIDATION of the S36 voice changes.** Three new claims a real `bn-BD`
  recogniser can disprove, none of which any test can settle: what it returns for `সব ঠিক আছে` /
  `all right`, whether the eleven-digit early stop fires at the right moment on live speech, and
  whether the spoken completion is audible over a waiting room.

## Session 35 — 2026-08-12 — **Voice-first confirmation (yes/no by speech), the header clock, context-aware questions, TTS pacing** — 547 → 622 tests
- Did: worked all 8 findings of the second manual-testing round in one pass, loop-engineered
  (reproduce → root cause → smallest fix → targeted tests → browser measurement → next). **ADR-0056.**
  **Alembic stays 0012** — no schema change, no migration, no new dependency, **no module status changed**.
- **⚠ Finding 1 began with a correction to the brief.** It said the phone read-back "currently
  auto-accepts after approximately 10 seconds". **It did not** — there was no timer on that panel at
  all; ADR-0053 deliberately required a tap. Verified by inspection before touching anything. So the
  10-second window is NEW behaviour, built as asked: the number is still shown at the largest size on
  the screen and still read back digit by digit, only the DEFAULT when the patient does nothing has
  changed, and `VOICE_PHONE_CONFIRM_MS=0` restores ADR-0053's rule exactly.
- **Findings 1 + 8 — ONE clock, moved into the portal header.** S34's clock lived inside the review
  layout, so it existed only on that screen and only while it was scrolled to the top. The header
  sits OUTSIDE `.screen` (the element that scrolls since ADR-0055 i), so the clock is now top-right
  at all times, cannot be scrolled away from, and cannot overlap — it is a flex item and the row
  reserves its width. Both countdowns (phone 10 s, review 60 s) write it through one renderer with a
  PER-COUNTDOWN label. `position: fixed` was rejected on purpose.
- **Findings 2 + 7 — the patient confirms by SPEAKING, in both places.** One vocabulary
  (`CONFIRM_YES` / `CONFIRM_NO` / `CONFIRM_FILLER`) and one parser serve the per-answer read-back and
  the final review. Two rules make it safe: an utterance is a verdict only when EVERY word in it is
  known, and where a YES word and a negation both appear NO wins. So `ঠিক আছে`→yes, `ঠিক নাই`/`ঠিক
  না`/`আবার বলি`→no, and `আমার নাম রহিম না মানে রহিমা`→**ambiguous, ask again** — the direct answer
  to "do not assume every sentence containing না means NO". Buttons remain as the fallback.
  Review NO re-opens the EXISTING resume dock with an open correction question — no new pipeline.
- **Finding 3 — "is it listening?" answered without reading.** `applyAvatarState()` publishes the
  ONE derived state on `<body data-kiosk-state>`; CSS makes the mic pulse and the dock hint jump from
  13.12px to 16.8px and turn red while the mic is open. No second state machine, so these cues can
  never disagree with the robot's face or the microphone.
- **Finding 4 — M7 is told what it already knows.** NEW `collected_context()`, the exact mirror of
  `missing_summary_fields()` (same keys, same `field_has_text`), plus a system-prompt clause
  forbidding re-asking anything in it or in PATIENT CONTEXT (age/sex/area) and asking for
  CLARIFICATION of that same item when something is vague. Deliberately NOT a decision system: it
  ranks nothing, names no condition and does not choose the next field — a test asserts the block
  carries no evaluative language at all.
- **Finding 6 — TTS pacing, not a new TTS.** NEW `services/tts/prosody.py`: `speech_text()` adds a
  sentence-final `।`/`.` and turns the em dashes and ellipses this project already uses as pauses
  into commas. Applied ONCE in the service so the primary and the fallback read the identical line.
  ⚠ It may never change a WORD — the read-back sends the patient's own captured words down this path.
  `tts_edge_pitch`/`tts_edge_volume` added but NEUTRAL by default.
- Decided: **ADR-0056** (a)-(h). It **supersedes ADR-0055's "Rejected (1)"** (spoken yes/no was
  turned down there as Step-S5 territory — wrong on the facts: S5 is timers and permission recovery)
  and **amends ADR-0053** (the phone tap becomes a window, with the tap-required mode kept selectable).
- Broke / problem: **one real defect created and caught by reasoning through the wiring, plus one
  measured layout fault.** (1) S34's `hideAnswerConfirm()` inside `toggleListening()` — "speaking
  again means say-it-again" — would have cleared `state.pendingAnswer` between the mic opening for
  the verdict and the word "হ্যাঁ" arriving, storing the verdict as the patient's symptom. Removed,
  with the reason left in place so it is not re-added; its rule became an explicit word instead.
  (2) `setResumeMode()` called `updateSubmitVisibility()` BEFORE its own `cancelPendingMic()`, which
  cancelled the very microphone the new review approval had just armed — the prompt would have been
  spoken with nothing listening. The call moved to the end of the function.
  (3) At 375px the clock landed at the LEFT of the wrapped header row: the right-hand group exactly
  fills the line (320px of 319px available), so `margin-left:auto` had no free space. Fixed with
  `order: 1` in the narrow query — measured back at x 264–348 against a 348px content edge.
- Six existing tests updated, none weakened: two `/api/config` whole-contract key sets (a new knob
  must be declared in both, by design); `test_kiosk_answer_confirm.py`'s retraction test, which now
  pins the REMOVAL above and explains it; the tokenizer assertions in `test_voice_digits.py`,
  retargeted from `digitsFromSpeech` to the extracted `speechTokens()` that both vocabularies now
  share; and four review-clock assertions retargeted from the review-scoped element to the header one.
- Verified: **622 passed, 2 skipped, 0 failures** (was 547). New files: `test_question_context.py`
  (12), `test_tts_prosody.py` (29), `test_kiosk_voice_confirmation.py` (17), `test_kiosk_phone_timer.py`
  (17). **Live browser run (no microphone — the recogniser's own buffer, S33's method):** all 9 YES
  phrases → yes, all 8 NO phrases → no, all 8 ambiguous/unrelated → null; phone clock 10s→8s→7s in
  the header with a triple tap sending EXACTLY ONE lookup and the timeout sending exactly one; a
  spoken answer held with 0 turns stored, ambiguous reply decided nothing, `না ঠিক নাই` stored
  nothing and re-asked, `হ্যাঁ ঠিক আছে` stored the answer and advanced **with the verdict itself
  absent from the transcript**; review NO re-opened the correction question with 0 submits, review
  YES racing a manual tap produced **exactly 1 submit**; no overflow or overlap at 1280x720,
  1024x600 or 375x812, the clock still visible after scrolling the review to the bottom, and the
  clock appearing shifts the review heading/title/grid by **0 pixels**.
- Deferred: **Step S5 — NOT implemented** (`no_speech_ms` watchdog, `max_answer_ms` cap,
  permission/visibility recovery all untouched). Also still open: the **real-microphone run**,
  rotating the **3 API keys** (human-only), Chrome + Edge comparison, formal **WER**, the acoustic
  judgement on the paced TTS, and the mid-turn word-loss rule #1 decision.
- Next: **REAL MICROPHONE VALIDATION.** What a `bn-BD` recogniser returns for a spoken "হ্যাঁ" is now
  on the critical path — an unrecognised yes/no blocks every confirmation in the flow.

## Session 34 — 2026-08-12 — **S34 manual-testing cycle: spoken-answer read-back, English digit words in Bangla script, review read-aloud + floating assistant, auto-scroll, the 60 s review clock** — 480 → 547 tests
- Did: worked the human's manual-testing findings end to end in one pass (their explicit
  instruction: no per-phase stop). **ADR-0055.** No schema change — **Alembic stays 0012**, no
  migration, no new dependency, **no module changed status**.
- **Phase 1 — the phone number showed WORDS, not digits. Two separate causes, both fixed.**
  (1) The real defect: the kiosk listens at `lang='bn-BD'`, and a Bangla-language recogniser handed
  "one two three" does not return Latin text — it returns `ওয়ান টু থ্রি`. The ten ENGLISH keys in
  `SPOKEN_DIGITS` could therefore **never be hit by a patient speaking English digits aloud**; they
  only ever matched typed/pasted text. Ten transliterations added (`জিরো ওয়ান টু থ্রি ফোর ফাইভ
  সিক্স সেভেন এইট নাইন`). `ও` ("and"/"he/she") is deliberately NOT mapped, by the same rule every
  other key passes. (2) The UX half: the identification docks now show a live **digit preview**
  (`0 1 7 1 5`) derived by the same `digitsFromSpeech()` that produces the value — the transcript
  keeps showing the words, because that is the evidence and it is never rewritten (rule #1).
- **Phase 2 — a spoken answer is now READ BACK before anything is stored.** Between S4 and this
  session a captured answer went from the recogniser straight into the permanent record with no
  human confirmation anywhere; the only way to catch a mis-recognition was to READ a chat bubble,
  which the target patient may not be able to do. Now: the words appear large and verbatim, are
  SPOKEN back (`bn-BD`, `verbatim`), and wait for ✔/✖. **Nothing reaches the server until ✔**; ✖
  discards the capture (it was never stored, so nothing is edited) and re-asks the SAME question.
  The gate is at ONE place — the spoken branch of `stopListening()` — and `acceptAnswer()` re-enters
  the SAME `submitPatientTurn(text,'mic')` / `submitResumeAnswer(text,'mic')`, so ADR-0048's
  one-pipeline rule is untouched and typed answers are never gated. **An unusable capture (no letter,
  no digit) is never guessed at**: silence and noise both re-ask. Before this an empty spoken turn
  fell through `if (sendTurn && text)` and did *nothing at all* — mic closed, no repeat, patient left
  waiting.
- **Phase 3/4 — the review can be HEARD, and has a floating assistant.** Every filled card gets a
  labelled 🔊 plus a "Hear my answers" read-through (one shared queue token, so a card tap and a
  read-through can never talk over each other). The P1 robotic doctor gains a THIRD mount on the
  review screen — same derived state machine (ADR-0054), added to `AVATAR_IDS`, with a slow float on
  the CARD (never on `.doctor-avatar`, whose transform belongs to the speaking state). It steps aside
  when the KIOSK-7 resume dock opens, so exactly one assistant is ever on screen.
- **Phase 5 — auto-scroll.** `addBubble()` now smooth-scrolls the THREAD (never `scrollIntoView()`,
  which moves the whole document and yanks the mic/typing box away mid-interaction), honest under
  `prefers-reduced-motion`, with the `scrollTop` assignment kept as the always-correct fallback.
- **Phase 6/7 — the 60-second review clock on ONE reusable ticker.** Digital, blinking, `urgent`
  under 10 s, `60s left` / `৬০ সেকেন্ড বাকি`. It runs **only while Confirm & Submit is genuinely
  pressable** (same verdict as the button), is idempotent so re-entry cannot stack a second timer,
  and `confirmSubmit()` gained a `submitting` re-entry guard. `startTicker()` is extracted and the
  5-second auto-logout countdown moved onto it — the proof it is reusable. **The S4 endpointer is
  deliberately NOT converted**: its deadline is restarted by every recognition result, and that
  restart IS the anti-clipping guarantee (rule #1).
- Decided: **ADR-0055** (a)-(i) — transliterated digit words; derived digit preview; read-back gate
  on spoken answers only, switchable via `VOICE_ANSWER_CONFIRM`; the gate at one routing point;
  unclear-answer re-ask NOT switchable; review read-aloud reads the DERIVED summary; review
  auto-submit gated on the submit verdict; one shared ticker with the S4 endpointer excluded; the
  kiosk page bounded to the viewport.
- Two new public knobs on the existing `/api/config` seam (S1's pattern — a clinic tunes behaviour
  from `.env`, not from JavaScript): `answer_confirm` (default true) and `review_timeout_ms`
  (default 60000, clamped at 0, `0` = never auto-submit).
- Broke / problem: **three defects found by MEASURING the running page, none by any assertion.**
  (1) The confirm panel opened **below the fold** — the same class of defect as F5b's phone
  read-back; fixed with the same proven forced-reflow + `scrollIntoView` pair. (2) Root cause of
  that: **PRE-EXISTING** — `shared.css` gives `body` `min-height: 100vh` and no height, so a handful
  of chat bubbles grew the document to **1538px inside a 694px viewport**, `.chat-thread` was handed
  unbounded space by `flex: 1` and never scrolled, and the entire voice dock sat below the fold.
  Auto-scrolling a thread that is not the scroll container cannot help. Fixed with
  `html, body { height: 100% }` + `.screen { min-height: 0; overflow-y: auto }`, scoped to the kiosk.
  (3) **PRE-EXISTING** — `renderSummary()` sets `grid-column: span 2` INLINE on two cards; in the
  narrow single-column grid that creates an IMPLICIT second column, and the review scrolled sideways
  inside its own box at 375px (**497px of content in a 375px viewport**). Fixed with
  `span 1 !important` in the narrow query plus `minmax(0, 1fr)` tracks. Also fixed: the clock as an
  absolute overlay **covered the centred heading** at 730px (now a flex sibling), and `৫৯s বাকি` was
  half-translated (the unit moved to the label).
- Three existing tests updated, none weakened: `test_kiosk_config.py` / `test_tts_provider.py` (the
  exact `/api/config` key set — both are deliberate whole-contract assertions, so a new knob must be
  declared in them) and `test_kiosk_avatar.py`'s `AVATAR_IDS` literal, rewritten to parse the list
  and check every mount also exists in the markup — strictly stronger than the string it replaced.
- Verified: **547 passed, 2 skipped, 0 failures** (was 480). New files: `test_kiosk_answer_confirm.py`
  (23), `test_kiosk_review_timer.py` (17), `test_kiosk_review_screen.py` (19); `test_voice_digits.py`
  +6 and `test_kiosk_config.py` +2. **Live browser run (no microphone, S33's method — feeding the
  recogniser's own buffer):** spoken-English-digits-in-Bangla-script phone → live preview `0 1 7 1 5`
  → read-back `01715-984632`, nothing sent → confirm → spoken OTP → verified → interview; a spoken
  answer showed the panel with **zero turns stored**, ✔ stored it and advanced, ✖ stored nothing and
  re-asked, silence and punctuation-only both re-asked; the clock ran 60→57→53→52, froze on Speak
  Again, restarted at 60 on return, went urgent under 10 s, and **a timeout racing TWO manual
  confirmSubmit() calls produced exactly ONE POST**; the shared ticker gave 3,2,1,0 with `onEnd`
  fired once and suppressed entirely by an early cancel; no horizontal overflow at 730x694 or
  375x812; console clean apart from the pre-existing `/favicon.ico` 404.
- Deferred: **Step S5 — NOT implemented, by explicit instruction** (its `no_speech_ms` watchdog,
  `max_answer_ms` cap and permission/visibility recovery are untouched; only the narrow
  empty-capture re-ask that Phase 2 required was built, and ADR-0055 (e) records the overlap).
  Also still deferred: the **real-microphone run**, rotating the **3 API keys** (human-only), the
  Chrome + Edge live STT comparison, formal **WER**, and the mid-turn word-loss rule #1 decision —
  which now also covers a pending read-back discarded by "Done".
- Next: **REAL MICROPHONE VALIDATION** of the full flow — now including the spoken-answer read-back
  and the English-digit transliterations, which are the two things a real recogniser can still
  disprove.

## Session 33 — 2026-08-11 — **F5 voice identification + P1 robotic doctor + P2 elderly UI + P3 age validation** — 392 → 480 tests
- Did: finished every remaining in-scope faculty-demo item. **F5a/F5b** (voice phone number +
  voice OTP, ADR-0053), **P1** the robotic-doctor avatar, **P2** elderly-friendly/3D UI, and
  **P3** age-appropriate conversation validation. **Alembic stays 0012 — no schema change.**
- **F5a — one cross-language digit contract.** `to_ascii_digits()` in `db/repository_visits.py`
  (folds any Nd digit via `unicodedata.decimal`) replaces `re.sub(r"\D", ...)`, which was
  Unicode-aware and so KEPT `০১৭…` and then failed the ASCII checks below it -> 400. JS gained
  `unicodeDigit()`/`asciiDigits()`/`digitsFromSpeech()`/`phoneFromSpeech()`, and both OTP box
  handlers stopped using ASCII-only `\D`, which had been SILENTLY DELETING Bangla digits.
- **F5b — identification by voice on the ONE recognizer.** Two more `DOCKS` entries
  (`phone`, `otp`) + `state.identifyStep` + two branches at the single routing point in
  `stopListening()` — no second pipeline, the human's explicit regression rule. A spoken phone
  number is READ BACK (large, grouped, spoken digit-by-digit) and requires a confirmation tap;
  a spoken OTP fills the boxes and reuses F1's `maybeAutoVerify()` unchanged. Phone screen is
  tap-to-start (no user gesture exists at first paint); auto-listen resumes at the OTP screen.
- **P1 — the robotic doctor.** CSS-only 3D (no library, no WebGL, no asset — CPU-only hardware).
  Five states DERIVED from real signals in `currentAvatarState()`, never pushed: listening >
  speaking > processing > idle. Only `done`/`error` may be pushed, and `error` expires with its
  8 s banner. Present in BOTH the conversation and resume docks; bilingual; `aria-live`;
  `prefers-reduced-motion` keeps the meaning.
- **P2 — elderly-friendly UI**, scoped to `kiosk.html` so the medic/doctor dashboards are
  untouched: 52px buttons, 54px inputs, 60px OTP boxes, 1.12rem chat, visible focus rings, and
  two separate responsive axes (`max-height: 820px` for the fold, `max-width: 620px` for overflow).
- **P3 — age validation, honestly tiered.** New `test_age_appropriate_questions.py` proves
  Tier 1 (the age is computed, reaches M7 verbatim, is confined to PATIENT CONTEXT, is rejected
  when implausible, and changes nothing else) and Tier 2 (the prompt's age instructions are
  directional, not just the phrase). **Tier 3 — that the MODEL obeys — is NOT proven** and an
  opt-in `M7_LIVE=1` probe is provided instead of a fake assertion.
- Decided: **ADR-0053** (F5: a Unicode decimal digit is a digit; identification reuses the one
  recognizer; phone confirmed / OTP not; tap-to-start on first paint) and **ADR-0054** (P1/P2/P3:
  avatar state derived-not-pushed with its precedence rule; elderly sizing scoped to the kiosk,
  not shared.css; the three-tier validation split).
- Verified: **480 passed, 2 skipped, 0 failures** (was 392). New files: `test_voice_digits.py` (20),
  `test_kiosk_voice_identification.py` (26), `test_kiosk_avatar.py` (25),
  `test_age_appropriate_questions.py` (17 + 1 opt-in skip). The 2 skips are both opt-in network
  tests (`TTS_LIVE=1`, `M7_LIVE=1`).
- **Live browser run (no microphone).** Full flow driven by feeding the recognizer's own buffer:
  spoken Bangla-word phone -> read-back `01715-984632` (nothing sent) -> confirm -> OTP screen ->
  spoken Bangla-word code -> verified -> interview. The scripted opening ran area -> name -> age ->
  complaint; **"আমার বয়স আটাত্তর বছর" was extracted to birth_year 1948 = age 78**, name and sex
  captured. A **real M7 call** then returned *"ব্যথার তীব্রতা কত? (How severe is the pain?)"* —
  on-topic, bilingual, non-diagnostic. Summary showed **10 cards**, F3's gate hid Submit and named
  the outstanding items, and all 12 turns stayed byte-identical and in order.
- Broke / problem: **six defects found by EXECUTING the code, none by assertions** — every one
  fixed and test-pinned. (1) `[^\p{L}\p{N}]+` shredded Bangla words at their own vowel marks
  (category M), so an eleven-digit sentence returned **"118"**. (2) `ছয়`/`নয়` have two encodings
  that render identically (U+09DF vs ya+nukta) and are `!==` in JS — one spelling dropped a digit;
  fixed with an NFC fold. (3) **TDZ**: `DOCKS` referenced `IDENTIFY_HINTS` before its `const`
  initialised — a ReferenceError that killed the whole kiosk. (4) `scrollIntoView` was a no-op
  called in the same tick as `display='flex'`; `requestAnimationFrame` would have *looked* like a
  fix but never fires on a non-painting tab, so a forced `offsetHeight` reflow is used. (5) My own
  P2 block re-declared `.welcome-title`/`.welcome-sub`/`.summary-label` at equal specificity AFTER
  existing rules — **dead CSS that read as applied**; sizes raised in place and a regression test
  added. (6) The 🔊 replay button measured **30x20**, under the 44px touch minimum.
  Also: per-state rules on `.doctor-antenna::after` applied box-shadow but silently kept the base
  `background`, so the state lamp stayed grey in all six states — moved to custom properties.
- One existing test updated, not weakened: `test_kiosk_otp_entry.py` pinned the literal
  `if (!res) return;`, which F5b extended to `if (!res) { reAskOtp(); return; }`. It now asserts
  the guard returns before BOTH the screen change and the visit assignment.
- ⚠ Honest gaps: **NO MICROPHONE WAS USED — the Browser pane blocks capture.** Every voice claim
  rests on feeding the recognizer's buffer directly; what Chrome's `bn-BD` recogniser actually
  returns for spoken digits is still unproven and is the next session's whole job. Screenshots
  were unavailable (the pane stopped compositing), so P2 rests on measured geometry at 1280x900,
  1280x720, 1024x600 and 375x812 rather than on looking at it. Age-appropriateness Tier 3 remains
  one live observation, not a validation across ages.
- Deferred: **real-microphone validation of F5** (next session), rotating the 3 API keys
  (human-only), the combined Chrome + Edge live listen/STT run, the mid-turn word-loss rule #1
  decision, Step S5 of Requirement 3, and formal WER.
- Next: **REAL MICROPHONE VALIDATION OF F5** — spoken phone -> confirmation -> spoken OTP ->
  verification, in Bangla and English digits AND number words, including the re-ask paths.

## Session 32 — 2026-08-11 — **Faculty-demo cycle: F1–F4 + F6 shipped** (OTP entry, target_gap mismatch, required-info gate, area/name/age, conversation-preservation tests) — 324 → 392 tests
- Did: the human gave a 8-part faculty-demo feature list and approved a P0 plan **F1→F2→F3→F4→F5→F6**.
  **F1, F2, F3, F4 and F6 are DONE. F5 (voice phone number + voice OTP) is NOT STARTED**, and neither
  are the P1/P2 items (robotic-doctor avatar, review identity header, 3D/elderly UI polish).
- **F1 — OTP entry (BUG FIX + UX).** `frontend/kiosk.js` only. Three defects the human reported:
  Enter did nothing (there was NO Enter handler on the OTP boxes OR the phone field — `initTypedInputs`
  wired only the two conversation text boxes); a complete code still needed a button click; a rejected
  code left its digits on screen. Now: `OTP_LENGTH` + `otpDigits()` + `clearOtpInputs()` +
  `maybeAutoVerify()` (called from the typed AND pasted paths), Enter on both screens, and a rewritten
  `verifyOtp()` with a length gate, an `otpVerifying` re-entry guard (codes are SINGLE-USE per
  ADR-0045 — a double submit would burn the patient's own valid code), clear-and-re-ask on failure
  keeping the server's own reason, and `if (!res) return;` so a failure cannot fall through to
  `showScreen('screen-voice')`.
- **F2 — the question/answer mismatch (BUG FIX).** `services/followup.py`. The resume scope used to
  let M7 pick the field and then "repair" a non-matching `target_gap` to `remaining[0]` — filing the
  question against a DIFFERENT field, so the asked field stayed unasked (asked again) and an unasked
  field was marked answered (never revisited). The SERVER now names the field in the prompt
  (`FIELD_PROMPTS`, one description per canonical key) and records that same field, including on the
  JSON-salvage path. The MAIN loop is deliberately untouched (M6 free-text gaps, no key contract).
- **F3 — required info cannot be skipped.** NEW `services/requirements.py` = the ONE definition, with
  the two-kinds split (`MUST_HAVE_VALUE` vs `MUST_HAVE_BEEN_ASKED`) so "no allergies" can satisfy a
  requirement. NEW `GET /api/visits/{uuid}/readiness`; `POST .../submit?require_complete=true`;
  `followup_resume_max_questions = 8` giving the resume loop its own budget on top of the main 5.
  Kiosk: `updateSubmitVisibility()` hides Confirm & Submit on the server's verdict, a bilingual
  `#required-notice` names what is outstanding, and `confirmSubmit()` sends the flag and re-runs the
  loop on a 409.
- **F4 — area first, name + age collected, both fed to M7.** `INTAKE_SCRIPT` = area → name → age →
  free description, each an ORDINARY recorded turn through the SAME endpoint (no second pipeline).
  M3/M8 gained `problem_area`; `entities` is now MERGED rather than replaced (intake used to wipe
  `suggested_condition` and any found area). `patient_context()` hands M7 age + sex + area, and
  `_QUESTION_SYSTEM` demands AGE-APPROPRIATE questions. Identity is re-askable on the review screen
  via the resume dock, which is what makes requiring it safe.
- **F6 — conversation preservation (tests only, no code).** Inspection found requirement 8 ALREADY
  satisfied; `test_conversation_preserved.py` converts "true today" into "cannot silently stop being
  true": both speakers in order, summary/report ADD rows and delete none, raw byte-exact in the DB
  (incl. a trailing space), and the .docx renders the whole conversation.
- Decided: **ADR-0052** — identity outside the 10 fields; two kinds of requirement; server-side gate;
  `require_complete` opt-in; resume budget; server names the resume field.
- Verified: **392 pass, 1 skipped** (was 324). New files: `test_kiosk_otp_entry.py` (12),
  `test_followup_target_gap.py` (13), `test_required_info.py` (21), `test_intake_context.py` (16),
  `test_conversation_preserved.py` (6). **Live-verified in a real browser engine** (no mic needed):
  Enter advanced the phone screen; six digits auto-submitted with no button press; a wrong code
  cleared all six boxes, refocused box 1 and showed *"Invalid verification code. Please enter the code
  again."*; `000000` advanced to the voice screen; and the scripted opening sequenced
  area → name → age → description with every turn stored server-side in order.
- Broke / problem: **two existing tests needed updating, neither weakened.**
  `test_resume_loop.py::test_resume_respects_shared_question_cap` — its settings stub had to gain
  `followup_resume_max_questions` (a fake Settings must model the real one); renamed and both caps
  zeroed, same assertion. `test_kiosk_auto_listen.py::test_every_question_..._goes_through_askaloud` —
  `setResumeMode()` now speaks a local `text` covering BOTH an M7 row and a re-asked scripted
  requirement, so the literal `askAloud(question.question_text)` no longer exists; the assertion was
  retargeted to the function body and now also proves it never uses plain `speak()`.
- ⚠ Honest gaps: **F5 not started** — voice phone/OTP entry is the human's requirement 1 and 2, so the
  full demo flow they specified is NOT yet achievable. **No voice path was verified** (the Browser pane
  blocks mic capture); the age-appropriateness and area-context prompt changes are **prompt-level and
  unproven** — no live LLM call was made against them. `require_complete` is bypassable by omitting
  the flag (deliberate, ADR-0052 d). A resumed `in_progress` visit re-asks the script and appends to
  the earlier conversation (pre-existing `verify-otp` behaviour, now more visible).
- **Deferred (the human called STOP at this point — next session's work):**
  **F5 — voice phone-number entry** and **F5 — voice OTP** (their requirements 1 and 2; the design is
  agreed and written into `current_task.md`, but no code exists). **P1 — the robotic doctor/avatar**
  and the review-page identity header. **P1/P2 — elderly-friendly + selective-3D UI work.**
  **Real human Bangla voice-DIGIT validation** (never attempted — the Browser pane blocks mic capture).
  **Full voice-first faculty-demo validation.** Also still deferred from earlier cycles: the combined
  **Chrome + Edge live listen / STT run**, the **mid-turn word-loss** rule #1 decision, **Step S5** of
  Requirement 3, **rotating the 3 API keys** (human-only), and the stale
  `human_live_run_guide.md` / `CLAUDE.md` lines.
- Next: **F5 — implement and validate voice phone-number entry + voice OTP.** Re-read the docs and
  re-inspect the STT/listening state machine FIRST; reuse the existing seam (no second recognizer);
  normalize Bangla/English digits and number words; **never silently submit an uncertain phone
  number** — show it and require confirmation; then voice OTP on top of F1's `maybeAutoVerify()`.
  Only after F5 is stable, P1/P2.

## Session 31 — 2026-08-09 — **The Edge STT terminal-error dead end is FIXED and CLOSED** — 318 → 324 tests
- Did: implemented the one defect the S30 Edge verification found and deliberately left unfixed.
  **`frontend/kiosk.js` only — ONE handler, one file, no backend/schema/Alembic change.**
  `r.onerror` now looks up a **`TERMINAL_STT_ERRORS`** map instead of testing two codes by hand:
  ```js
  r.onerror = (e) => {
    const message = TERMINAL_STT_ERRORS[e.error];
    if (!message) return;   // transient (no-speech / aborted): onend restarts, as before
    showError(t(message.en, message.bn));
    stopListening(false);   // sets listening = false — this is what breaks the restart loop
    setInputMode('type');
  };
  ```
  Terminal set = `not-allowed`, `audio-capture`, **`network`**, **`service-not-allowed`**,
  **`language-not-supported`** (the last is exactly what Edge emits if its backend rejects `bn-BD`).
  Everything absent — above all `no-speech` and `aborted` — stays transient.
  **`r.onend` is untouched:** the fix works by flipping `listening`, NOT by teaching the restart about
  error codes, and a test now pins that so the two mechanisms cannot get tangled later.
- Decided: **no new ADR, on purpose.** This is not an architectural decision — it *implements* what
  **ADR-0048** already requires ("typing is ALWAYS available… a patient is never blocked by a failed
  mic"). The `onerror` handler simply never covered the cases that could strand one. Creating an ADR
  for a completed obligation would be documentation noise.
- Decided (a small, deliberate deviation from the plan in `current_task.md`, flagged to the human and
  **awaiting their word — they have not responded yet**): **three messages instead of one generic
  string.** A dead speech SERVICE is not a dead MIC. `language-not-supported` → *"This browser cannot
  recognise Bangla speech"*; `network` / `service-not-allowed` → *"Speech recognition is unavailable"*;
  the mic pair keeps the original wording. All three bilingual (`MIC_UNAVAILABLE` /
  `STT_SERVICE_UNAVAILABLE` / `STT_LANGUAGE_UNSUPPORTED`). Reason: at a faculty demo those need
  different responses, and telling a patient the microphone failed when Edge rejected the *language* is
  simply false. Reverting to one message is a 3-line change.
- Verified: **324 pass, 1 skipped** (was 318; the skip is still the opt-in `TTS_LIVE=1` network test).
  New `backend/tests/test_kiosk_stt_errors.py` (6). Following the S30 precedent it **extracts the
  shipped `TERMINAL_STT_ERRORS` literal out of the served `kiosk.js` and compares the key set**, rather
  than substring-matching a comment. **Two of the six exist only to guard the Chrome side** —
  `no-speech`/`aborted` must stay OUT of the map, and the early `return` must precede every side effect.
- **Then it was exercised in a REAL browser engine, with no mic and no permission prompt** (build a
  recognizer, call `onerror` directly): `no-speech` → `listening` **true** ✅ · `aborted` → **true** ✅ ·
  `bad-grammar` → **true** ✅ · `network` / `service-not-allowed` / `not-allowed` / `audio-capture` →
  **false**, loop broken ✅. After a terminal error `state.inputMode` flipped to `'type'` and
  `#error-banner` read *"Speech recognition is unavailable — you can type instead."* with
  `display=block`. Zero console errors on load; the map also proved to be **valid JS** (the Python
  tests only parse text).
- Broke / problem: **nothing regressed** — no existing test was touched, weakened or deleted. One false
  alarm chased down and dismissed: a probe read `#error-banner` as `display:none`, which looked like the
  message never showing. It was `showError`'s own **8-second auto-hide** (`shared.js:134`); the check
  had simply run two tool round-trips late. Not a defect.
- ⚠ **Found and DELIBERATELY NOT FIXED — needs the human's call.** `stopListening(false)`
  (`kiosk.js:576`) discards `finalBuffer`, so a terminal error landing **mid-turn** — a wifi blip giving
  `network` after the patient has already spoken — **throws their captured words away instead of
  submitting them.** Pre-existing (already true for `not-allowed`/`audio-capture`), but this change
  widens the set of codes that reach it, and `network` is far more plausible mid-sentence than a
  permission revocation. Left alone because deciding the fate of a half-spoken answer is the **rule #1
  call** `current_task.md` already classes as "not a drive-by change" — same family as the deferred
  repeat-while-listening item. Cheap fix if wanted: when `endingTurn` is true, submit instead of drop.
- Deferred: the **combined Chrome + Edge live listen / STT run** (still nobody has HEARD TTS-1 or TTS-2,
  and nobody has run STT in Edge). Steps **S5–S7** of Requirement 3. Rotating the 3 API keys. The stale
  `human_live_run_guide.md` (lines 19, 72) and `CLAUDE.md` (S28/234-tests paragraph, the "no server, no
  key" TTS line, Python 3.14 vs the venv's 3.13.3). Formal WER / the TextBee demo.
- ⚠ **Honest gap, unchanged in kind:** whether Edge actually emits `language-not-supported` for `bn-BD`
  is **still UNPROVEN**. This fix makes the failure **visible and recoverable**; it does not prove which
  failure occurs. That still needs a human at a real mic.
- Next: **the human's faculty-demo feature list.** They opened a feature-planning workflow (analyse and
  classify each request → prioritised P0/P1/P2 plan → wait for "GO" → implement) but **the message
  contained no features yet.** Nothing is to be assumed or built until they arrive.

## Session 30 — 2026-08-08 — **TTS-1 FIXED and CLOSED** (one question is now spoken in one language) — 277 → 297 tests
- Did: implemented **TTS-1**, the first item of the 3.0 cycle, after the human chose **option (a):
  speak only the half matching the active UI language.** Frontend only — **4 files, ~50 lines, no
  backend, schema, or M7-contract change.**
  - `frontend_shared/tts.js` — a `BILINGUAL_QUESTION` regex + `spokenHalf(text, short)`, applied
    **once** inside `speak()` (`const speech = verbatim ? text : spokenHalf(text, short);`). Putting
    it in `speak()` rather than `askAloud()` was deliberate: the call site would have missed the
    resume-question path and the assistant replay button.
  - **Both providers speak the split half** — `new SpeechSynthesisUtterance(speech)` **and**
    `encodeURIComponent(speech)`. This is the part that actually matters: on Windows the server path
    is the **only** Bangla route (ADR-0049), so splitting only the browser path would have left the
    defect fully alive on the exact machine where it was reported.
  - `frontend/kiosk.js` — one call site: the per-bubble 🔊 passes `verbatim: role === 'patient'`. An
    assistant bubble replays the half the patient already heard; a **patient** bubble is the patient's
    own captured words and is read back whole — reading back part of what someone said would be a
    rule #1 defect in spirit.
  - **Fails safe by construction:** the pattern matches only a Bangla-script head followed by a
    TRAILING parenthesised Latin-script tail. A monolingual parenthetical (`"fever (above 100F)"`), a
    Bangla parenthetical, nested parens, and a `(...)` not at the very end all fail to match and are
    spoken **whole**. The failure mode of a splitter is speaking LESS than the question, so when it is
    unsure it loses seconds, never words.
- Decided: **ADR-0051 — Accepted (code shipped).** Option (b) (both halves with a real pause) was
  rejected: ~1 s more per question, against ADR-0048's "minimize clicks, waiting and complexity"
  priority for an elderly/non-technical user. **`followup.py` was deliberately NOT touched** — making
  the server return two fields would change the M7 contract and what medic/doctor display.
- Verification: **297 pass, 0 skipped** (was 277). New `backend/tests/test_tts_bilingual_split.py`
  (20 tests) **extracts the shipped regex literal out of the served `tts.js` and runs it**, so the rule
  is exercised rather than asserted about — a step up from the pure static-source convention, without
  adding a JS test runner (which would have broken the one-`requirements.txt` rule). Three of its tests
  pin what must NOT change: the stored `raw_text`, the on-screen bilingual bubble (ADR-0028 fallback),
  and the M7 prompt. Also cross-checked in a **real JS engine**, since the split tests run the literal
  through Python's `re`: Chrome's `spokenHalf` agreed case-for-case on 8 inputs, and with `serverTts`
  on + the UI in Bangla, `/api/tts` received `lang=bn` / `text=আপনার জ্বর কত দিন ধরে?` — English half
  absent, no console errors.
- Broke / problem: **two pre-existing tests failed** on the first full run —
  `test_kiosk_auto_listen.py::test_replaying_an_old_bubble_does_not_open_the_microphone` and
  `test_kiosk_tts_fallback.py::test_the_server_is_only_used_when_it_can_actually_speak`. Both were
  static-source assertions on the exact strings I intentionally changed (`encodeURIComponent(text)`
  and the replay-button one-liner). Updated to the new wiring with their **original intent still
  asserted** (replay stays plain `speak()`, never `askAloud()`); neither was weakened or deleted.
  Nothing else regressed — all 85 tests across the S1–S4 + TTS-seam files pass.
- Deferred: **TTS-2 untouched, as instructed** (still ADR-0050 Proposed: provider and the rule #4
  privacy trade-off undecided). **S5–S7 of Requirement 3 still NOT built.** Rotating the 3 API keys,
  formal WER, and the TextBee demo all still open. Also noted, not acted on: `askAloud`'s safety-net
  timeout is still sized from the FULL bilingual text, so it now over-waits slightly — deliberate and
  test-pinned, because over-waiting is harmless while opening the mic early is a rule #1 defect.
- ⚠ **Honest gap: nobody has HEARD this yet.** The tests prove which string reaches each provider;
  only a live listen proves it sounds like one question. The human said they will test later.
- Next: the human's live listen of TTS-1, then **TTS-2** — which needs a provider choice **and** an
  explicit rule #4 privacy decision before any code.

### 🔊 TTS-2 — same session, after the human's "go": **the robotic voice is replaced (ADR-0050 ACCEPTED)** — 297 → 318 tests
> Recorded inside Session 30, not as a new session: this was one continuous session, and the S29
> precedent is that inventing a session number corrupts the numbering the memory system relies on.
- Did: **inspected first, as instructed — and the inspection overturned a documented "fact".** ADR-0050
  and the 3.0 tracker described edge-tts's cost as a *"binary `aiohttp` dep"* and never checked its
  licence. Verified from PyPI metadata: **edge-tts 7.2.8 is LGPL-3.0** — library use imposes no copyleft
  on our code and carries **no non-commercial clause**. Verified from the HF model card:
  **`facebook/mms-tts-ben` is CC-BY-NC-4.0**, i.e. non-commercial only, which bars a real clinic
  deployment. **On licensing the "safe local option" was the more restrictive one.** Also confirmed
  `requirements.txt` already ships a binary dep (`ddgs`→`primp`), so `aiohttp` broke no intact property.
  Found a third candidate en route (gTTS: MIT, pure-Python, but an unofficial endpoint and the same
  privacy cost for a less natural voice) and presented all three rather than assuming.
- Decided (**the human's two calls, both recorded in ADR-0050, now Accepted**):
  1. **Provider = `edge-tts`, now the DEFAULT**; espeak-ng **demoted, not deleted** (`TTS_PROVIDER=espeak`
     is the private/offline path and the automatic fallback).
  2. **On failure, fall back to espeak-ng rather than go silent** — a robotic question beats a silent
     kiosk. `TTS_LOCAL_FALLBACK=false` restores ADR-0049's bare-503 contract.
  ⚠ **The rule #4 cost was accepted explicitly, not slipped in:** M7 questions are derived from patient
  speech and this sends them to Microsoft. What tipped it — the system **already** sends the patient's
  *actual audio* to Google via the Web Speech API, so this adds a second processor of strictly less
  sensitive derived text. **It still limits what the thesis may claim about privacy.**
- **The seam held, which was the real test of ADR-0049.** One subclass (`services/tts/edge.py`) + one
  `PROVIDER_FACTORIES` entry + `.env` settings. **No route, frontend, schema or Alembic change.**
  Microsoft returns **MP3 not WAV** and even that needed nothing extra, because the ABC already carries
  `media_type` per provider and `<audio>` plays MP3 natively.
- Two small generalisations were genuinely needed: **`MAX_TEXT_CHARS` moved `espeak.py` → `base.py`**
  (the route imported the cap *from a specific engine*, which made a local binary's constant the API's
  limit by accident), and availability became **`TtsProvider.available()`** instead of a duck-typed
  `resolve_binary` probe — "is the engine installed?" is only answerable for a *local* engine.
  `available()` deliberately never touches the network: it runs on every kiosk page load.
- Verified: **318 pass, 1 skipped** (was 297). New `test_tts_edge_provider.py` (21) is **offline by
  default** — every network call monkeypatched, because a suite that needs wifi fails in a lab; the one
  real network test is opt-in via `TTS_LIVE=1` and passed. Live through the running server: `bn` and
  `en` both `audio/mpeg` in **~0.8 s**; playback completed at **3013 ms** with `ttsSpeaking()` **true
  throughout**, so **S3's echo guard still holds against the new provider's network latency (rule #1)**;
  and `<audio>` was observed requesting **only the Bangla half**, proving ADR-0051 and ADR-0050 compose.
- Broke / problem: **three espeak-specific tests would have silently changed meaning.**
  `test_bangla_renders_a_valid_non_empty_wav`, `test_english_renders_too…` and
  `test_the_endpoint_serves_playable_audio…` called the module-level `synthesize()` and relied on espeak
  being the *default*; with `edge` as default they would have gone to the network and asserted `RIFF`
  against MP3. Each now pins `TTS_PROVIDER=espeak` explicitly, which is what they were always testing.
  Also caught a false alarm during live verification: Bangla appeared to return WAV in 124 ms — that was
  the **browser cache** (`private, max-age=300`) from the earlier TTS-1 check, not a fallback; re-fetched
  with `cache: 'no-store'` it was `audio/mpeg` from edge.
- Deferred: TTS-1's and TTS-2's **live listen — the human will test BOTH together in one Chrome run.**
  S5–S7 of Requirement 3 still NOT built. Rotating the 3 API keys, formal WER, TextBee demo still open.
  Faculty Req 2 unchanged — `mms-tts-ben` remains its natural candidate and now drops into this same seam.
- ⚠ **Honest gap, unchanged in kind: naturalness is NOT proven.** Bytes, MIME type, latency and
  completed playback are measured. Whether the voice sounds human to a Bangladeshi patient is the
  human's ears, and no test in this repo can answer it.
- Next: **the combined TTS-1 + TTS-2 live listen** (procedure handed to the human at the end of S30).

### 🧭 EDGE COMPATIBILITY VERIFICATION — end of Session 30 (INSPECTION ONLY, **no code changed**)
> Still Session 30: one continuous session, and the S29 precedent is that inventing a session number
> corrupts the numbering the whole memory system relies on.
- Did: the human plans to demo in **Microsoft Edge**, so STT + TTS browser compatibility was verified
  **before** the live test. Claude's browser tools drive Electron/Chromium 148, **not Edge** — so
  **real Microsoft Edge 151.0.4129.72** was launched at a throwaway local probe page
  (`127.0.0.1:8799`, read-only) that reported its capabilities back. The probe deliberately did **NOT**
  call `recognition.start()` or `getUserMedia()`: either would pop a permission dialog on the human's
  desktop unprompted. It therefore covers everything **except audio**.
- **Verified TRUE in real Edge:** the STT is the browser's **native Web Speech API**
  (`kiosk.js:464`, `window.SpeechRecognition || window.webkitSpeechRecognition` — no library, no server
  STT); Edge 151 exposes **both** constructors; a recognizer **constructed** and **accepted**
  `lang='bn-BD'`, `continuous=true`, `interimResults=true`; microphone permission state is
  **`"prompt"`** (not blocked) and `isSecureContext` is true on localhost; `canPlayType('audio/mpeg')`
  is **`"probably"`**, so Edge can play TTS-2's output; and there are **no Chrome-only APIs** in the
  STT path.
- **⚠ THE DISTINCTION THAT MATTERS, and it must not be blurred: API surface verified ≠ actual Bangla
  STT service verified.** Edge accepting the string `'bn-BD'` proves only that the setter took it.
  Whether Edge's speech **backend transcribes Bangla** is **UNPROVEN** and needs a human at a real mic.
  **Nothing here claims Edge STT works end-to-end.**
- **Key finding — Edge has NO Bengali browser TTS voice:** 26 voices across 21 languages,
  **`bnVoices: []`**. This **disproves ADR-0050's option 3** ("Edge as the kiosk browser — Microsoft
  online `bn-BD`, zero code — *unverified*"). Microsoft's *browser* ships no Bengali voice even though
  Microsoft's *edge-tts service* has `bn-BD-NabanitaNeural` — same vendor, different surface.
  **Consequence, and it is good news:** in Edge `_pickVoice('bn')` returns null, so the chain falls to
  provider 2 and **the server-side TTS-2 `edge-tts` path stays the Bangla route in Edge, exactly as
  designed** — no Chrome-vs-Edge divergence for Bangla audio.
- Found / problem — **ONE REAL DEFECT, and it is NOT fixed:** `kiosk.js:499` handles only **2 of the 8**
  Web Speech API error codes (`not-allowed`, `audio-capture`). **`language-not-supported`** — exactly
  what Edge would emit if its backend rejects `bn-BD` — plus **`network`** and **`service-not-allowed`**
  fall through, leaving `listening === true`; `kiosk.js:491` then restarts the engine, producing an
  infinite **`start → error → end → start`** loop. The patient sees a live-looking mic with **no error,
  no switch to typing, and no countdown** (S4 arms only after real words), and **S5 — which would catch
  the silence — is not built**. On Edge a `bn-BD` rejection is a *silent dead end* that also spins CPU.
- **Proposed minimal fix — NOT IMPLEMENTED, awaiting the human's "go":** split terminal from transient
  errors — `TERMINAL_STT_ERRORS = ['not-allowed','audio-capture','network','service-not-allowed',
  'language-not-supported']` → show the existing bilingual message, `stopListening(false)`,
  `setInputMode('type')`. ⚠ **`no-speech` and `aborted` MUST keep restarting** — that restart is what
  keeps continuous listening alive in Chrome and is part of the S29 PASS, so a blanket "stop on any
  error" would **regress Chrome**. Scope: `frontend/kiosk.js` + ~4 static-source tests; no change to
  S1–S4, the echo guard, the countdown, TTS-1, TTS-2, storage or schema.
- **Recorded as UNVERIFIED, deliberately NOT as a bug:** `FLUSH_GRACE_MS = 600` (`kiosk.js:372`) is
  Chrome-calibrated — its own comment says *"how long to let **Chrome** flush its last final chunk"*.
  If Edge finalises more slowly the tail of a long answer could be dropped (a rule #1 defect), but
  **this has not been observed** and cannot be measured without real audio in Edge. Do not change the
  constant blindly.
- Also flagged, not acted on: **`human_live_run_guide.md` is now wrong in two places** — line 19 tells
  the human to use Chrome *"not Edge"*, and line 72 repeats the **now-disproven** claim that Edge may
  expose `bn-BD` voices. And a demo warning: the Web Speech API + mic need a **secure context**, so
  `http://localhost:8001` is fine but a LAN address (`http://192.168.x.x:8001`) **blocks both**.
- Deferred: **everything.** The human explicitly ended the session here — *"Do not implement the
  proposed Edge STT error fix yet"* — so **no production code was touched after TTS-2 shipped**. This
  entry and the other memory files are the only changes.
- ⚠ **The human end-to-end test has still NOT happened.** Nobody has heard TTS-1 or TTS-2, and nobody
  has run STT in Edge. Everything in S30 rests on tests plus non-audio browser probes.
- Next: **the Edge STT terminal-error fix** (recommended), then the combined Chrome + Edge live run.

## Session 29 — 2026-08-08 — **Step S4 SHIPPED + live-tested PASS**, then **Bangla TTS solved architecturally (ADR-0049)** — 234 → 274 tests
- Did (two separate pieces of work, each after its own "go"):
  - **Step S4 — silence detection + the visible 3-2-1 countdown + barge-in cancel.** `kiosk.html`
    gained a `.countdown` block in **both** docks (2.2rem digit + bilingual caption); `kiosk.js` gained
    the endpointer: `restartSilenceWindow()` / `renderCountdown()` / `endTurnOnSilence()` /
    `finishFlushedTurn()`, a deadline-driven window so a tuned `countdown_ms` displays honestly, and
    `r.onend` rewritten from the old "always restart" line into an arbiter. **Every `onresult` tick —
    interim OR final — restarts the window**, so a pause or a cough cannot clip an answer; the window
    **arms only after real words are captured**, leaving the silent-patient case to S5. **The human's
    live run PASSED.** → 234 → **247 tests**.
  - **The flush (the human's call).** `stopListening()` reads `finalBuffer` immediately, so at zero we
    now `recognition.stop()` FIRST and submit from `onend` (or a 600 ms grace, whichever wins, exactly
    once). Proven in-browser: the submitted buffer was `"আমার জ্বর — এবং গলা ব্যথাও আছে"`, i.e. it
    **included the tail the engine only released on stop()** — without this that tail was silently lost.
  - **Then: Bangla TTS.** Audited first, as instructed. **Verified root cause, not guessed:** Bengali is
    **absent from Microsoft's entire Windows TTS voice list** (no `bn-BD`, no `bn-IN`), and the dev box
    confirms it — only `David/Zira (en-US)`, no `bn` token in the classic OR `Speech_OneCore` hive, no
    Bengali language pack. **So `human_live_run_guide.md` PART 1 was instructing the human to do
    something impossible**, and ADR-0040's "Windows path is unchanged" rested on that false premise.
  - **Built the seam (ADR-0049):** `backend/app/services/tts/` (`base.py` ABC + `espeak.py` +
    `service.py` selector — deliberately mirroring the ADR-0045 OTP seam) and public
    **`GET /api/tts?text=&lang=`** → `audio/wav`. `tts.js` keeps its exact signature but now walks a
    chain: **browser voice → server → `false`**. Text goes to espeak-ng via **stdin** (never argv, so
    Bangla dodges Windows argv encoding), `shell=False`, length-capped because the endpoint is
    unauthenticated. **Zero new Python dependencies** — stdlib `subprocess`.
  - **Honest failure, which was the actual ask:** the old `speak()` returned `true` whenever
    `speechSynthesis` merely existed, so Bangla read by an en-US voice *looked* like success. Now Bangla
    demands a matching voice, a missing engine is a **503** (never a silent 200), `speak()` returns
    **false**, and `/api/config` gained **`server_tts: bool`** — a capability, never the provider name
    or path (the schema's own no-disclosure rule, re-asserted by a test).
- Decided: **ADR-0049 — Accepted.** espeak-ng over the alternatives on verified grounds: **Piper has no
  Bengali voice at all** (checked `VOICES.md`); **`facebook/mms-tts-ben`** is a real bn model but needs
  torch+transformers and is **CC-BY-NC-4.0**, so it is parked as the natural fit for **Requirement 2**
  and drops into this seam as one subclass; **edge-tts** has genuine bn-BD neural voices
  (`NabanitaNeural`/`PradeepNeural`) but pulls binary `aiohttp` and ships question text to Microsoft —
  kept as a documented future provider. espeak-ng wins because it is **already this project's accepted
  Bangla voice** (ADR-0040, Arch), keeps question text **on the machine** (M7 questions are derived from
  patient speech — rule #4), and adds no dependency.
- Broke / problem — **three real bugs found and fixed, two of them mine:**
  1. **A rule #1 trap I created.** Server audio plays through `<audio>`, and `speechSynthesis.speaking`
     is **false** the whole time — so S3's echo guard would have opened the mic while the AI was
     audible. Fixed with **`ttsSpeaking()`** (true for either provider **and while the request is still
     in flight**) swapped into `openMicWhenQuiet()`, plus `ttsCancel()` in `toggleListening()`. Measured:
     `ttsSpeaking()` is already true the instant the request is created.
  2. **I broke English TTS** by making the browser path conditional on finding a matching voice —
     `getVoices()` is empty during Chrome's async load, so English returned `false`. Caught in the
     browser, not by tests. Only **Bangla** now demands a matching voice.
  3. **Stale `shared.js` served from cache** silently sent every question down the wrong language path —
     this is what made bug 2 invisible for two rounds. Starlette's `StaticFiles` sends no
     `Cache-Control`, so Chrome applied heuristic freshness. Fixed with `RevalidatedStaticFiles`
     (`no-cache, must-revalidate`; the existing ETag keeps it a cheap 304), and `tts.js` now reads the
     language from the **`lang` localStorage key shared.js already owns** instead of a shared.js helper,
     removing the cross-file version skew entirely. On a clinic kiosk that staleness would have silently
     disabled Bangla audio after an update.
- **Then espeak-ng was installed (winget, with the human approving the UAC prompt) and the pipeline was
  verified end to end → 274 → 277 tests, 0 skipped:**
  - Engine has a **Bengali voice** (`bn`, `inc\bn`); a Bangla question renders **exit 0, 158,098 bytes,
    RIFF/WAVE, 22,050 Hz, 3.58 s**. Endpoint: **200, `audio/wav`, 157,438 bytes, 3.57 s**.
    `/api/config` → **`"server_tts": true"`**; the KIOSK-2 banner is now **hidden** while
    `banglaVoiceAvailable()` is still false — proving the fallback, not a browser voice, is speaking.
  - **Playback genuinely completes:** `onend` at **3877 ms** vs the measured **22 ms** error path.
  - **Rule #1 integration proof:** with `toggleListening` spied, the mic opened **exactly once at
    4110 ms**; `ttsSpeaking()` was true at 509/1525/2553/3583 ms and the mic stayed shut throughout.
    Without the predicate swap it would have opened at ~400 ms, mid-question.
  - Hardened en route: `resolve_binary()` now also checks the installers' well-known paths, because the
    Windows MSI updates the **machine** PATH and processes started earlier cannot see it — a clinic
    would otherwise see "not installed" forever.
- Deferred: **S5–S7 are still NOT built.** ⚠ And the honest remaining gap: **nobody has HEARD the
  Bangla.** Bytes, duration and completed playback are proven; espeak-ng Bangla is known to be robotic
  (ADR-0040), and whether it is *intelligible* to a Bangladeshi patient is the human's judgement.
  Voice quality must not be described as validated. Also noted, not acted on: **CLAUDE.md says Python
  3.14 but the venv is 3.13.3.**

### 🔊 LIVE RUN VERDICT — end of Session 29 (the human's real listen, in Chrome)
> Recorded as part of Session 29, not a new session: this was one continuous session, and inventing a
> "Session 30" would corrupt the numbering the whole memory system relies on.
- Did: the human ran the kiosk in Chrome with real audio and reported: **Bangla voice: Too robotic ·
  Mic timing: Pass · Countdown: Pass · Transcript clean: Yes · English: Pass**, plus *"there are no gap
  when tts Bangla and English hear . some time 2 question hear at a same time this is confusing"* and
  *"i want make it like human not too robotic"*. Verbatim wording preserved in
  `context fixed problem 3.0.md`. **I then root-caused the audio defect** to
  `services/followup.py:45`.
- Decided: **ADR-0050 (Proposed).** The ADR-0049 **seam is validated and stays**; only its **first
  provider is rejected**. espeak-ng is a formant synthesizer, so "too robotic" is **inherent, not
  tunable** — no `.env` value fixes it. Replacing the voice is **one subclass**, which is exactly what
  the seam was built for. espeak-ng is **demoted, not deleted** (offline, zero-dep, no-network fallback +
  the Arch path). **The replacement provider is deliberately NOT chosen** — edge-tts (natural `bn-BD`
  neural, but a binary dep + sends question text to Microsoft), `facebook/mms-tts-ben` (local, but torch
  + CC-BY-NC), or fold into faculty Requirement 2. That choice carries a **rule #4 privacy trade-off**
  that is the human's to make explicitly, not mine to assume.
- Broke / problem: **TTS-1 — one question is spoken as Bangla then English with no gap**, which sounds
  like two questions. **Root cause found, not guessed:** `services/followup.py:45` forces the M7 prompt
  to emit `"question": "<Bangla question> (<English question>)"` — every question is a SINGLE bilingual
  string, so TTS reads both halves in one breath. **It is not an overlap bug and not caused by
  ADR-0049**; it has existed since S25 and was merely exposed, because espeak `-v bn` also applies
  Bengali phonetics to the English half. The fix must be **TTS-only**: the stored `system` utterance and
  the on-screen text keep the full bilingual string (rule #1 + ADR-0028).
- Deferred: **everything.** The human explicitly asked to fix nothing this session — "i want fixed some
  bug and add some features in upcoming session for now i want you will remember". So **no code was
  written after the verdict**; TTS-1 and TTS-2 are filed as the first two items of the **3.0 cycle**
  (`context fixed problem 3.0.md`, now 🟢 OPEN after being empty since S24). Also still open: **Steps
  S5–S7** of Requirement 3, rotating the 3 API keys, formal WER, the TextBee demo, **CLAUDE.md claiming
  Python 3.14 when the venv is 3.13.3**, and a **stray second uvicorn on port 8000**.
- Next: **TTS-1 first** (functional before polish) — but it needs one human decision before any code:
  should the patient hear **only their UI language** (recommended: faster, less confusing) or **both
  halves with a real pause**? Then TTS-2's provider choice, then Step S5.

## Session 28 — 2026-08-08 — Requirement 3 EXPANDED to voice-first + typing-fallback; inspection, 7-step plan, and **Steps S1 + S2 + S3 SHIPPED** — 234 tests pass
- Did (inspection + docs FIRST as instructed, then Steps S1 → S2 → S3, each after its own separate
  "go" from the human — no code was written before the plan was approved):
  - **The human expanded faculty Requirement 3** from "remove the mic clicks" to **"every patient
    interaction after phone login must support BOTH voice and typing, switchable at will"**. Filed as
    **§3b** in `faculty_future_features.md`, with the original §3 text kept **byte-identical** above it
    (provenance: §3 was relayed S27; §3b is the human's own written expansion).
  - **Full code inspection first, as instructed** — `kiosk.js`, `kiosk.html`, `tts.js`, `shared.js`,
    `routes_followup.py`, `schemas/followup.py`, `core/config.py`, `backend/tests/`.
  - **Key finding #1: voice and typing ALREADY share one pipeline.** `AnswerRequest.source` is
    `Literal["mic","manual"]` and `sendTypedFallback()`/`sendResumeTyped()` already hit the **same**
    `/followup/answer` endpoint. 3b's "do not duplicate the question/answer logic" is already
    satisfied — what is actually wrong is the *framing*: typing hides behind a "Microphone issue?"
    link. Nothing needs un-duplicating.
  - **Key finding #2 — a GOVERNING-RULE CONFLICT, surfaced not silently resolved.** `CLAUDE.md`'s
    VOICE INTERACTION RULES and **ADR-0027** say *"Patient input is VOICE ONLY … the manual text box
    remains ONLY as a developer/accessibility fallback"* (narrowed by ADR-0030 to phone/OTP only).
    Requirement 3b supersedes that. Recorded as **ADR-0048**; the `CLAUDE.md` rule edit is left
    **pending the human's explicit GO**.
  - **Key finding #3: no JavaScript test infrastructure exists** (no `package.json`, no Node — all
    192 tests are pytest/backend). **The countdown, barge-in cancel and echo guard cannot be
    unit-tested as things stand.** Three options filed (static-source assertions per
    `test_routes_static.py` / vitest+jsdom / none); recommended (a); **not yet chosen**.
  - **Key finding #4: two traps the spec does not mention** — (i) if no Bangla voice is installed,
    `speak()` degrades silently and **`onend` may never fire**, freezing an auto-listen kiosk → needs a
    `max(3 s, len×80 ms)` fallback timer; (ii) the Web Speech API opens its **own** audio stream, so
    `echoCancellation` constraints **cannot** be passed — echo protection is structural gating only.
  - **Key finding #5:** `AnswerRequest.raw_text` has **no minimum length** — an empty answer is
    storable today, so "never silently submit an empty answer" needs a server-side guard too.
  - **Filed the full plan** in `faculty_future_features.md` §A–K: what already works, what must
    change, recommended UX (persistent `[🎤 Voice][⌨ Type]` control, countdown as a **confirmation
    window**), a 20-row real-life safeguards table, backend changes (**no schema change — Alembic stays
    at 0012**), frontend changes, tests, 7 risks, a **7-step GO-gated build order**, and the **12-point
    live Chrome checklist**.
- Decided: **ADR-0048 — Accepted** (proposed mid-session, accepted once the human answered its three
  open questions). Voice is the **primary/default** patient interaction and typing is the
  **always-available fallback**; this **supersedes ADR-0027's clinical-input voice-only rule**
  (ADR-0028's "text AND audio" is untouched), and `CLAUDE.md` was amended to match. The 3-second
  countdown **is** the silence window and is a **confirmation window, never a hard cutoff**. ONE
  answer pipeline (`source: mic|manual` unchanged). Timings served from `.env` via a new public
  `GET /api/config`. `raw_text` gains a non-blank minimum, enforced server-side. Frontend tests =
  static-source assertions only (no vitest/jsdom). ADR-0047 marked "scope EXTENDED by ADR-0048".
- Broke / problem: nothing broke — **zero regressions across all three steps** (192 → 211 → 222 →
  234, every existing test still green). Two real hazards were found and closed rather than
  discovered later: (i) **Chrome fires `onend` for an utterance that `cancel()` killed**, so a
  cancelled question's callback would have opened the mic *during the next question* — the AI's own
  voice into a `patient` utterance (rule #1). Closed with a generation token in `tts.js` and
  **disproven by measurement** (two questions 200 ms apart → exactly one mic-open, after the second).
  (ii) With no installed voice `onend` may never fire at all — closed with the
  `max(3 s, len×80 ms)` safety net, verified by deleting `speechSynthesis` (mic still opened at
  416 ms). ⚠ Standing honesty caveat: **no microphone was ever opened this session** — `toggleListening`
  was a spy — so echo is disproven only at the *scheduling* level, and the dev machine has **no
  Bangla voice installed**, leaving the Bangla TTS path unexercised.
- **Then the human answered all three and said GO for S1 only — so S28 also SHIPPED Step S1:**
  - **Answers:** (1) **the 3 s visible countdown IS the silence window** (speech stops → 3→2→1 →
    submit; any resumed speech cancels it instantly); (2) frontend tests = **(a) static-source
    assertions** via the existing `TestClient` pattern, **no vitest/jsdom** — real mic/TTS/countdown/
    barge-in behaviour is proven only by the live Chrome run; (3) **`CLAUDE.md`: YES, update it.**
  - **Priority recorded:** *voice is the main goal and primary UX, not an optional feature* — the
    portal guides patients toward speaking, automating voice wherever possible; typing exists so no
    patient is ever blocked. UX priority = minimize clicks, waiting and complexity for
    elderly/non-technical patients.
  - **Built (S1 — backend only, zero UX change, fully reversible):**
    `core/config.py` — `voice_loop` (`auto`|`manual`, default **auto**) + `voice_countdown_ms=3000`,
    `voice_tts_guard_ms=400`, `voice_no_speech_ms=10000`, `voice_max_answer_ms=120000`, plus a
    `resolved_voice_loop` property (case/space-insensitive; a `.env` typo falls back to `auto`
    instead of breaking startup — same spirit as `resolved_database_url`). **NEW public
    `GET /api/config`** (`api/routes_config.py` + `schemas/kiosk_config.py`) — no DB, no auth,
    built field-by-field so a future secret in `Settings` can never leak through it.
    `schemas/followup.py` — `raw_text` gains `min_length=1` + a non-blank validator that **returns
    the value COMPLETELY UNCHANGED** (`.strip()` tests emptiness only — rule #1); its docstring now
    states the one-pipeline contract for `mic`|`manual`. `backend/.env.example` documents all five
    knobs and the restart requirement. `main.py` registers the router.
  - **`CLAUDE.md` amended (approved):** the "VOICE INTERACTION RULES" block now reads **voice-first,
    typing always available**, with an explicit ⚠ that this **supersedes** the old "patient input is
    VOICE ONLY / keyboard is a mic-failure fallback only" rule (ADR-0027 as narrowed by ADR-0030) and
    a "do not re-apply the old rule" warning; plus the one-pipeline rule and the countdown-is-a-
    confirmation-window rule. Status paragraph notes S28/S1.
  - **Tests: 192 → 211 (+19), all passing** — `test_kiosk_config.py` (defaults, `.env` override,
    `manual` selectable, 4 normalization cases, and an **exact-key-set + no-secret-substring** guard)
    and `test_answer_raw_text_guard.py` (6 blank forms rejected, padding preserved byte-for-byte,
    1-char "না" accepted, voice/typing share one contract, unknown `source` rejected, `mic` is the
    default). **No schema change — Alembic stays at head 0012.**
- **Then the human said "go" again → S28 also SHIPPED Step S2 (kiosk UI, no turn-taking change):**
  - **`kiosk.html`** — a `.mode-switch` segmented control **`[🎤 Speak] [⌨ Type]`** in **both** docks
    (conversation + KIOSK-7 resume), active mode filled teal with `aria-pressed`, bilingual
    `data-en`/`data-bn`. **The old "Microphone issue? Type instead" reveal link is GONE** — typing is
    now a first-class choice, not failure recovery.
  - **`kiosk.js`** — `state.inputMode` ('voice' default), a `DOCKS` map replacing the inline
    `activeDock()` literals, `MODE_HINTS`, and `setInputMode()` which updates **both** docks at once
    (the patient picks once; the resume dock inherits it), hides the mic in Type mode so it cannot be
    tapped by accident, and **focuses the input**. `stopListening()` now restores a **mode-aware**
    hint. Mic `onerror` (`not-allowed`/`audio-capture`) and the unsupported-browser branch now
    **switch the patient to typing** instead of merely revealing a row. **Enter sends** a typed answer
    (UX priority: fewer taps). Post-logout reset returns to voice — every patient starts voice-first.
  - **Rule #1 / ADR-0048 honored:** switching Voice→Type calls `stopListening(false)`, which
    **discards** the un-submitted STT buffer rather than pre-filling the box — a typed edit on top of
    STT text would be stored as one utterance whose `source`/`stt_provider` provenance is false.
  - **Turn-taking is UNCHANGED** — the patient still taps the mic to start and to finish, exactly as
    in the passed S25 run. Auto-listen is S3; the countdown is S4.
  - **Tests: 211 → 222 (+11)** — `test_kiosk_input_modes.py`, static-source assertions per the human's
    decision (2), with a docstring stating plainly that they prove the controls EXIST and cannot prove
    browser behaviour.
  - **Browser-verified** (in-app Chrome preview, no mic needed): voice default → Speak filled, mic
    shown, typed row hidden; Type → mic hidden, input auto-focused, hint changes, **resume dock
    inherits the mode**; switch back restores voice; the EN/BN toggle re-renders both labels and the
    hint in Bangla. **Zero console errors, zero server errors.**
- Deferred: **Steps S3–S7 are NOT built** (auto-listen, countdown, safeguards, resume-dock re-verify,
  live run) — each needs its own "go". `/api/config` is built but **not yet read by the kiosk** (S3 is
  the first consumer). Still open from before: rotating the 3 API keys, formal WER, the TextBee demo,
  the empty 3.0 inbox.
- **Then the human said "go" again → S28 also SHIPPED Step S3 (auto-listen):**
  - **`tts.js`** — `speak()` now carries a **generation token**. Chrome fires `onend` for an utterance
    that `speechSynthesis.cancel()` killed, so without this a **cancelled** question's callback would
    open the mic while the **next** question is still being spoken — the AI's own voice straight into
    a `patient` utterance. Guarded at the single TTS entry point; `onerror` is bridged to the same
    handler (a failed utterance can never strand the caller) and the callback fires **at most once**.
  - **`kiosk.js`** — `VOICE_DEFAULTS` + `loadKioskConfig()` (the **first consumer of `/api/config`**;
    a failed fetch keeps the safe defaults — configuration must never be what stops a patient being
    screened). New `askAloud()` replaces `speak()` at the **three** question sites (`assistantSays`,
    `setResumeMode`, `repeatQuestion`); the per-bubble 🔊 replay stays plain `speak()` because
    reviewing an old turn must not open the mic. `openMicWhenQuiet()` is the **echo guard**: it polls
    until `speechSynthesis.speaking` is false, then waits `tts_guard_ms`, then calls the SAME
    `toggleListening()` a tap calls — one code path, so auto and manual can't diverge. A
    `max(3 s, len×80 ms)` **safety net** covers the case where `onend` never fires (no installed
    voice). `cancelPendingMic()` is wired into every deliberate action — a tap, a mode switch, Done,
    and the logout reset all beat a pending arm. Bilingual arming hint ("the microphone will start by
    itself").
  - **The patient still taps ONCE to finish** — auto-endpointing and the countdown are S4.
    `voice_loop=manual` reproduces the S25 behaviour exactly.
  - **Tests: 222 → 234 (+12)** — `test_kiosk_auto_listen.py`, static-source assertions.
  - **Browser-verified with an instrumented spy on `toggleListening` (no mic touched):** `/api/config`
    really is consumed; a normal question opens the mic **once at 926 ms** with TTS already silent
    (the 3680 ms safety net correctly did not double-fire); **two questions 200 ms apart produce
    exactly ONE open, at 1057 ms — after the second question** (the cancelled utterance's `onend` did
    not fire the mic: the rule #1 echo case, disproven at the scheduling level); a mode switch mid-
    question yields **zero** opens; `manual` yields **zero** opens with the original hint; and with
    `speechSynthesis` deleted entirely the mic still opens at **416 ms** (no freeze).
    **Zero console/server errors.**
  - **Known gap, deliberately deferred to S5 and documented in the code:** tapping "Repeat question"
    while the mic is already open plays TTS into a live recognizer. Closing it means deciding what
    happens to the half-spoken answer already in the buffer — discarding a patient's words is a
    rule #1 decision, not something to slip into this step. Pre-existing since S25.
- Next: **Step S4 on the human's "go"** — silence detection + the **visible 3-2-1 confirmation
  countdown** + barge-in cancel. This is the step where rule #1 is genuinely at risk (a clipped
  answer), and the first one whose core behaviour a spy **cannot** verify — it needs real speech.

## Session 27 — 2026-08-08 — Faculty Requirement 3 filed (fully voice-driven follow-up conversation) + doc cross-references synced (docs-only, no code)
- Did (no code, no tests — 6 markdown files):
  - **`faculty_future_features.md`: added Requirement 3 — "Fully Voice-Driven Interactive Follow-up
    Conversation"** (a later faculty clarification relayed by the human). Written in the same formal
    register as Reqs 1–2 (`Currently… / As a future faculty requirement…`), plus a full
    implementation-notes block: why it is future work, current vs. future workflow, reusable seams,
    research challenges, evaluation ideas, benefits, and an internal build order.
    **Reqs 1 & 2 left byte-identical** (the only deletion was the header's status block).
  - **Key finding — read from the code, not assumed: the server-side loop is ALREADY autonomous.**
    `POST /api/visits/{uuid}/followup/answer` runs M8 merge → M9 check → M7 next question and returns
    `next_question` in the SAME response (`AnswerOut`), and `kiosk.js submitPatientTurn()` already
    chains it into `assistantSays()`. **Faculty steps 4–8 work today**; only steps 2–3 are manual
    (the two taps in `toggleListening()`). So Req 3 = frontend turn-taking, **no backend change**
    needed for the basic loop.
  - **Seams recorded for the future build:** `tts.js speak(text, {onend})` — the callback already
    exists and is ignored at all 3 kiosk call sites (= "mic starts automatically");
    `interimResults = true` already supplies the silence-timer ticks for auto-endpointing, replacing
    `r.onend = () => { if (listening) r.start(); }`; `stopListening(true)` already submits the turn;
    `activeDock()` means the KIOSK-7 resume dock inherits the change; and the loop is already bounded
    server-side (`followup_max_questions = 5`, `min = 4`, `threshold = 0.7`) — so hands-free cannot
    run forever. That bound is the safety property that makes removing the taps acceptable.
  - **Provenance kept honest:** Reqs 1–2 are the faculty's own pasted text; Req 3 was **relayed as a
    spoken clarification**, so the header marks it "faithful, not literally verbatim".
  - **Cross-references synced (5 spots)** so nothing still reads "two faculty requirements":
    `CLAUDE.md` (status pointer + memory-file item 11), `current_task.md` (menu option 3),
    `session_protocol.md` (the standing start-of-session menu), `codebase_map.md` (tree entry), and
    `context fixed problem 3.0.md` — the last one also gained a **misfiling guard**: "the mic needs
    two taps" is a **Req 3 research item, NOT a 3.0 bug**.
  - **Deliberately NOT touched (history stays honest):** this changelog's S24b entry, **ADR-0042**,
    `context fixed problem 2.0.md`, and `codebase_map.md`'s S24b note all correctly said "two" when
    written. `milestone_log.md` line 42 was checked and left alone (its wording carries no count).
- Decided: **ADR-0047** — Requirement 3 is filed to the **research track** (explicitly NOT the 3.0 bug
  cycle) and scoped as a **client-side turn-taking change, independent of Reqs 1 & 2**, to ship behind
  a `voice_loop = manual | auto` config switch (ADR-0045 pattern: switch in `.env`, old path never
  deleted). Rule #1 framing recorded: an endpointer that clips an answer, or TTS echo captured into a
  `patient` utterance, is a **rule #1 defect — not a UX nit**.
- Broke / problem: none. **No code was touched**, so the 192-test suite is unchanged and was
  deliberately **NOT re-run** this session (there was nothing for it to prove) — the number is carried
  over from S24/S25, not re-verified today.
- Deferred: building any of it. Reqs 1–3 all stay ⬜ NOT STARTED (research track). Still open from
  before: rotating the 3 API keys (pre-demo), formal WER/precision-recall, the TextBee real-SMS demo,
  and the empty 3.0 inbox.
- Next: **HUMAN's choice from the menu** — now with 4 real candidates: (1) rotate the 3 API keys
  (recommended before any public demo), (2) paste manual-testing findings into the 3.0 inbox,
  (3) faculty Reqs 1–3 — **Req 3 step 1 (auto-listen via `speak()`'s existing `onend`) is the
  smallest and most visible starting point**, (4) formal WER / TextBee demo.

## Session 26 — 2026-07-12 — Standing start-of-session "options menu"; confirmed 3.0 tracker intentionally empty (docs-only, no code)
- Did (no code, no tests):
  - **Confirmed the 3.0 tracker is EMPTY by design, not by oversight.** Re-read
    `context fixed problem 3.0.md` — 📥 inbox still "(nothing yet)". In S25 the human reported 0 bugs
    and explicitly said "leave 3.0 empty for now", so there is correctly nothing to file.
  - **Established a standing start-of-session behavior (human's request):** the 5-line orientation
    summary must ALSO surface the open **menu of options** and stress that picking among them is the
    **human's choice** — never assume one. Menu = (1) rotate the 3 API keys (recommended pre-demo),
    (2) paste manual-testing bugs/UX findings → `context fixed problem 3.0.md`, (3) faculty future
    features (`faculty_future_features.md`), (4) formal WER / TextBee demo, (5) anything else.
  - Wired it in three places so it survives: **`current_task.md`** next-step is now that menu with
    the choice framing; **`session_protocol.md`** gained a standing note in its START section; a
    **feedback memory** (`session-start-options-menu`) captures the preference.
- Decided: no new ADR — this is a **session-workflow preference**, not an architecture/design choice
  (ADRs stay reserved for real technical decisions). Captured in session_protocol.md + current_task.md
  + memory instead.
- Broke / problem: none. **192 tests still pass** (no code touched; carried over, unverified this
  session).
- Deferred: the whole menu itself — key rotation, the 3.0 fix cycle, faculty future features, formal
  WER, TextBee demo — all remain the human's to pick from.
- Next: **HUMAN's choice from the menu** (recommended pre-demo default = rotate the 3 API keys,
  `human_live_run_guide.md` PART 3).

## Session 25 — 2026-07-12 — HUMAN LIVE REAL-MIC RUN PASSED (Windows 11); Modules 1–14 → ✅ (docs-only, no code)
- Did (no code, no new tests — recording the human's live-run result):
  - **The human ran the live real-mic test** (`human_live_run_guide.md` PART 2) on **Windows 11 +
    Chrome + real mic**, synthetic data, OTP via the `000000` dev bypass. **TC-V1/V2/V3/F2/R1 all
    PASS.** Observations: STT **very accurate**, latency **≈ 2 s**, TTS **spoke correctly**,
    follow-up questions **good**. **No bugs / UX issues found.**
  - **`test_log.md`**: added the S25 live-run entry (all 5 cases PASS + the qualitative numbers +
    the explicit caveat that this run was qualitative & Windows-only — formal WER/precision-recall
    still to be logged).
  - **`milestone_log.md`**: the human live-voice gate is CLEARED → **Modules 1–14 flipped 🟨 → ✅**
    (M5 stays ⛔ retired; **M15 stays 🟨** = future retrain/regression pipeline). Status board,
    "Last updated", and Phase-0 step-6 marker updated; added the S25 note.
  - **`CLAUDE.md`**: status paragraph → Session 25, live run PASSED, Modules 1–14 ✅.
  - **`current_task.md`**: overwritten — the live run is DONE; next real work = **rotate the 3 API
    keys** (still pending) + optional formal WER/precision-recall as thesis evidence; future issues
    → the 3.0 inbox.
- Decided: **ADR-0046** — on the passed live-voice gate, move the happy-path module board (1–14) to
  ✅ (M5 ⛔, M15 🟨), with a standing caveat that the run was qualitative + Windows-only so formal
  WER/precision-recall is still owed as evidence. The human chose this over the more conservative
  "flip M1 & M7 only" and "change nothing" options.
- Broke / problem: none. **192 tests still pass** (no code touched). Caveat recorded, not a bug: the
  live run was qualitative (no by-hand WER / precision-recall / labeled set) and Windows-only.
- Deferred: rotating the 3 API keys (human, before any public demo); formal WER/precision-recall on
  ~50 samples; the optional TextBee real-SMS demo; everything in `faculty_future_features.md`.
- Next: **rotate the 3 API keys** (`human_live_run_guide.md` PART 3) before showing anyone; then the
  project is demo-ready. Any manual-testing issues found later → `context fixed problem 3.0.md` inbox.

## Session 24b — 2026-07-11 — Docs-only addendum: CLAUDE.md refreshed, 2.0 tracker closed, 3.0 scaffold + faculty future-features file created
- Did (no code, no tests — documentation structure for what comes next):
  - **CLAUDE.md**: stale status paragraph (S14/156 tests/head 0010) → current (S24, both cycles
    complete, real OTP ADR-0045, M16, head 0012, **192 tests**); memory-file list gained items
    10–11 (the two new files below).
  - **`context fixed problem 2.0.md`**: P4-1 flipped to ✅ with the S24 summary; header now says
    the WHOLE 2.0 tracker is complete and points to 3.0 — the file is historical.
  - **NEW `agent_docs/faculty_future_features.md`**: the faculty's two future requirements
    (quantized Moshi medical-summary model; quantized on-device STT/TTS replacing the browser
    APIs) kept VERBATIM + implementation notes mapping each onto existing seams (Req 1 = local
    OpenAI-compatible server as one more provider in `llm_providers.py`, zero pipeline change;
    Req 2 = `stt_provider` setting + Phase-1 WebSocket slot for STT, `tts.js speak()` for TTS,
    latency gates, Banglish-output caveat) + a suggested order (summary → STT → TTS). Research
    track, ⬜ not started, needs the human's "go" + its own plan.
  - **NEW `agent_docs/context fixed problem 3.0.md`**: the next-cycle scaffold, 🕐 EMPTY/waiting —
    encodes the 2.0 workflow: human pastes RAW manual-testing findings into its 📥 inbox → Claude
    triages into a numbered checkable tracker (original words kept verbatim) → human approves the
    plan → ONE item per "go", functional before polish. Carries over the locked rules + the
    baseline (192 tests, head 0012).
  - Consistency touches: `codebase_map.md` agent_docs listing + `current_task.md` next-step now
    name both new files.
- Decided: nothing new — documentation organization only (no ADR; ADR-0045 from S24 stands).
- Broke / problem: none.
- Deferred: everything in `faculty_future_features.md` (explicitly future).
- Next: unchanged — the human live real-mic run; findings → the 3.0 inbox.

## Session 24 — 2026-07-11 — P4-1 real OTP (Alembic 0012, pluggable sender seam, TextBee) — **2.0 TRACKER COMPLETE**; 192 tests
- Did:
  - **OTP channel research (human asked for deep 2026 research first):** a truly FREE SMS-OTP to
    arbitrary BD numbers does not exist — Twilio BD $0.5962/SMS (trial = verified numbers only);
    WhatsApp auth templates ~$0.0113/msg + Meta Business verification; Firebase phone auth is
    Blaze-plan-only (billing card, per-SMS); local BTRC aggregators (sms.bd / Alpha / MiM) are the
    real production route at ~৳0.30–0.40/OTP; Telegram Gateway is $0.01/code but recipients must
    have Telegram; email (Brevo 300/day, Gmail SMTP) is free but verifies the wrong thing. The
    free-AND-real option: **TextBee.dev** (open-source Android-phone SMS gateway, own BD SIM) —
    demo-grade, chosen as the second sender.
  - **Built P4-1 (ADR-0045):** `otp_codes` table (**Alembic 0012**, applied — head 0011→0012) +
    `OtpCode` model; new package `backend/app/services/otp/` (base ABC + `DevLogSender` default +
    `TextBeeSender` via httpx + channel-independent `service.py`); config `OTP_CHANNEL=dev|textbee`,
    `OTP_DEV_BYPASS`, TTL/attempts/cooldown knobs + TextBee creds. Security: salted-SHA-256 hash
    only (plaintext never persisted/audited), 5-min expiry, single-use, constant-time compares,
    5-attempt lockout (429 even for the CORRECT code), 60 s resend throttle (`otp_sent=false` +
    `retry_after_seconds`), undelivered codes voided, random codes can't collide with `000000`.
    The `000000` bypass lives ONLY inside the `otp_channel=="dev"` branch — a test proves it is
    rejected under `textbee` even with `OTP_DEV_BYPASS=true`. `lookup` now really issues+audits
    (`otp_issued`); kiosk UX unchanged (zero frontend edits). `httpx==0.28.1` pinned (now direct).
  - **Fixed a PRE-EXISTING logging bug** found while verifying: `migrations/env.py` ran
    `fileConfig(alembic.ini)` at every startup with default `disable_existing_loggers=True`,
    silencing ALL `uvicorn.*` logs after migrations (entry-point banner, access logs — and the new
    dev-OTP line). Fix: `disable_existing_loggers=False`; DevLogSender logs via `uvicorn.error`
    (same channel as main.py's banner).
  - **Live-verified end to end** on the dev server: 0012 applied at startup → lookup printed
    `[OTP] verification code for +8801766666666: 130303` → wrong code 401 → real code 200 with an
    `in_progress` visit → `000000` still accepted on the dev channel.
- Decided: **ADR-0045** (OTP design: hashed single-use codes behind a pluggable sender seam;
  dev-log default; TextBee = free real-SMS demo channel; BTRC aggregator = future prod sender).
- Broke / problem: nothing in the suite (**192 pass**, was 177; +test_otp.py 13 + 
  test_migration_0012.py 2). The env.py logging bug above was pre-existing, now fixed.
- Deferred: activating `textbee` (human must install the TextBee app on an Android+BD-SIM phone
  and put API key + device id in `.env`); a BTRC-approved aggregator sender for real deployment
  (paid ~৳0.35/OTP — same seam, new subclass).
- Next: **the 2.0 tracker is COMPLETE (STRUCT+P1+P2+P3+P4 all ✅).** Next real work = the human
  live real-mic run (`human_live_run_guide.md`) + key rotation; optional: TextBee real-SMS demo.

## Session 23 — 2026-07-10 — 2.0 build: P2-3 + P3-1..P3-4 (P2 AND P3 CLOSED — Alembic 0011, M16 drug-info assistant); 177 tests
- Did: five tracker items, one per "go":
  - **P2-3 (closes P2):** the medic portal needed NO retint — `frontend_medic/index.html` is fully
    token-based (its one hex `#F4FAF8` is an approved teal tint) and `staff.js` has zero hexes.
    Two real polish fixes, both in `shared.css`: `.card` radius `12px` → `var(--radius)` (10px, the
    ADR-0043 lock — all three portals inherit) and `.verbatim-speaker` made `display:block` + 4px
    gap ("ASSISTANT ASKED" no longer runs into the Bangla question text). Full medic flow
    preview-verified with a stubbed `api` (login → queue → case → Submit & Forward → post-referral
    → EN↔BN), computed styles + screenshots, no console errors.
  - **P3-1 (Alembic 0011):** new nullable `Visit.submitted_at` — stamped in
    `repository_visits.set_visit_status()` on `in_progress → awaiting_review` (mirrors the
    `completed_at` pattern, so `submit_visit` needed no change and the stamp stays synchronous —
    unaffected by the P1-5 background job). Exposed via `VisitOut` (detail + submit response
    inherit) and `DashboardItemOut`/`_to_item`. Frontend: queue rows render
    `dhakaTime(submitted_at || started_at)` (fallback covers pre-0011 rows); the doctor
    patient-details card gains a "Submitted / জমার সময়" row via `dhakaDateTime()`. Migration
    0011 applied to the dev DB (head confirmed; data untouched). New `test_submitted_at.py` (3:
    stamped once + a 2nd submit can't move it · queue+detail expose it · assign/review never
    clobber) + `test_migration_0011.py` (2 DB gates, house style).
  - **P3-2 (verification, NO product-code change):** traced that every doctor-side read is fresh
    (`GET /visits/{uuid}` embeds the live Patient row; /profile + /risk re-query per open) →
    doctor always sees medic edits, including post-referral identity/weight edits. Locked it in
    with `test_doctor_sees_medic_edits.py` (1 end-to-end: field edit + C1 replacement + risk
    override + post-forward vitals/identity PATCH → all visible in the doctor's queue row, visit
    detail, profile [source=human, disclaimer survives], /risk [human tier]). Render side
    preview-verified (মানব-সম্পাদিত badges etc.).
  - **P3-3 (M16 drug-info assistant, ADR-0044):** new `services/assistant.py` (ddgs/DuckDuckGo
    search, top-5 snippets capped at 400 chars → ONE `call_module("M16")` on the Flash bucket),
    `routes_assistant.py` (`POST /api/visits/{uuid}/assistant/drug-info` — visit-scoped because
    `module_events.visit_id` is NOT NULL + audit linkage), `schemas/assistant.py` (disclaimer
    fields REQUIRED in the contract). Disclaimer "AI-generated information. Please verify before
    prescribing." (+Bangla) attached SERVER-side on every answer — never left to the model (rule
    #2); search gets only the doctor's typed question (rule #4). Search fail → sourceless answer;
    non-JSON reply → salvaged; chain dead → 502. Doctor UI: "💊 AI Drug Info" top-nav button +
    teal slide-in panel (always-visible disclaimer bar, Q/A bubbles via textContent ONLY, source
    links, per-answer disclaimer, EN↔BN, hidden in print CSS). Dep: `ddgs==9.14.4` (its `primp`
    ships Windows x64 + manylinux wheels; no separate httpx needed). New `test_assistant.py` (5).
  - **P3-4 (closes P3):** doctor portal was already token-clean (semantic amber/red kept; the
    JS-rendered prescription form has ZERO hex hardcodes — verified in the live DOM). One fix:
    `.safety-panel` radius `12px` → `var(--radius)` in `shared.css` (deferred from P2-3) — the
    LAST radius hardcode; every panel now derives from the ADR-0043 token. Preview-verified incl.
    prescription form (Diagnosis still empty on open — rule #2).
- Decided: **ADR-0044** (M16 assistant design: visit-scoped endpoint, Flash bucket, server-attached
  disclaimer, ddgs-only dep, best-effort search). Everything else implements already-locked ADRs.
- Broke / problem: none. Two preview quirks (not app bugs): the stub must match the prescription
  context path WITH its `?doctor_id=` query; `preview_eval` can mis-read a just-toggled class.
- Deferred: **P4-1 (real OTP) — the ONLY item left**, and it needs the human's CHANNEL decision
  before the sender is built (recommend: dev/log sender + `000000` bypass behind a pluggable seam,
  optionally ONE free reference channel: email-OTP or Telegram-for-opted-in).
- Next: **P4-1** — get the human's OTP channel choice, then build: `OtpCode` table (Alembic 0012),
  expiring code, `000000` universal bypass, pluggable sender seam.

## Session 22 — 2026-07-10 — 2.0 build: P1-6 (kiosk polish, P1 CLOSED) + P2-1 (Dhaka time fixed) + P2-2 (patient demographics); 166 tests
- Did: three tracker items, one per "go":
  - **P1-6 (frontend, closes P1):** retinted the 6 leftover clinical-blue hardcodes in
    `frontend/kiosk.html` inline CSS to Teal Medical (dock transcript, summary icons, highlight
    icon/pill, progress chip, card shadow); the P1-4 amber "needs info" + green complete-chip
    (semantic colors) kept untouched. Verified via computed styles + screenshot — **Priority 1
    (Patient Portal) is now fully CLOSED** (P1-1 through P1-6 all ✅).
  - **P2-1 (frontend, opens P2):** found the ROOT CAUSE of the "random" medic/doctor queue times —
    SQLite serializes timestamps **offset-less** (`2026-07-05T14:03:42.884654`, no `Z`), so the
    browser's bare `new Date()` read them as LOCAL time instead of UTC. New shared helpers in
    `frontend_shared/shared.js`: `parseUtc()` (pins offset-less strings to UTC) + `dhakaTime()` /
    `dhakaDateTime()` (always render `Asia/Dhaka`, bn-BD/en-GB by language) — pure browser `Intl`,
    no backend/tzdata dependency. `frontend_shared/staff.js` `renderQueue` now uses `dhakaTime()` —
    both medic AND doctor queues fixed at once (shared file). Verified with known UTC instants
    (offset-less 06:30→12:30, `18:00Z`→00:00, `+00:00`→06:00, Bangla digits, invalid→"—").
  - **P2-2 (backend + frontend, MEDIC-details spec item):** `Patient.sex`/`birth_year` existed in
    the model but were never written; `display_name` only came from phone-lookup. (a) Extended the
    M3/M8 extraction prompt (human-approved wording) with a `patient_demographics` key — same LLM
    call, zero extra quota. (b) New `apply_demographics()` in `services/intake.py` (called from
    intake AND the M8 answer-merge in `services/profile_update.py`) writes
    `display_name`/`sex`/`birth_year` **FILL-ONLY-WHEN-EMPTY** — a staff-entered value is never
    overwritten by the AI, no schema migration needed. (c) Extended `PATCH /patients/{id}/vitals`
    (`schemas/dashboard.py` + `routes_dashboard.py`) to accept `display_name`/`sex` (pattern-
    validated)/`age_years`; audit now logs only the fields actually sent (fixed a pre-existing test
    that asserted strict-equality on the audit detail dict). (d) Medic post-referral card gets a
    **Gender** row + an "Edit Details" identity editor (name/age/gender, prefilled, same pattern as
    the weight editor); the doctor portal reads the same `Patient` row so it benefits automatically.
    New `test_patient_demographics.py` (4 tests: autofill · never-overwrite-existing ·
    malformed/absent-ignored · staff-PATCH-is-final + 422/400 validation). **166 pass** (was 162).
- Decided: no new ADR — P1-6/P2-1 implement the already-locked ADR-0042/0043; P2-2's
  fill-only-when-empty pattern mirrors the existing `source=human` M8-merge guard, not a new rule.
- Broke / problem: one pre-existing test (`test_medic_summary.py::test_vitals_patch_updates_and_audits`)
  broke on the extended PATCH because the audit detail dict grew 3 always-present `None` keys —
  fixed by auditing only sent fields (better behavior, not a workaround). One dev-server hiccup
  mid-session: `preview_start` tried the Linux launch config (`.venv/bin/python ENOENT` on
  Windows) — resolved by explicitly starting `"backend (FastAPI + uvicorn)"`.
- Deferred: P2-3 (medic UI polish, closes P2), then P3 (doctor: submitted-at, patient-details
  verification, AI chatbot) → P4 (OTP, channel choice still needs the human).
- Next: **P2-3** — Medic Portal UI polish (closes P2): sweep `frontend_medic/index.html` for
  leftover blue hardcodes → teal equivalents; layouts/hooks untouched.

## Session 21 — 2026-07-10 — 2.0 build: P1-5 (Confirm & Submit = instant, assessment in background); 162 tests
- Did: **P1-5** (ADR-0042b, one "go"). `backend/app/api/routes_dashboard.py`:
  `submit_visit()` now keeps only the guards + `status→awaiting_review` + audit **synchronous**
  (the case is in the medic queue the moment the response returns); the up-to-3 LLM round-trips
  (M10 risk + M11 XAI + M10C suggestion) moved into a new **`_post_submit_assessment(engine,
  visit_id)`** FastAPI `BackgroundTasks` job with its OWN session. Seam detail that kept every
  existing test green: the job binds to **`db.get_bind()`** (the request's engine), so prod uses
  the real DB and the tests' overridden in-memory engine exercises the same path — zero fixture
  churn. Job is fire-and-forget (try/except + `logger.exception`); `assess_visit` /
  `suggest_condition` were already idempotent + best-effort. No frontend change needed (the tier
  fills into the staff queues on their 15s refresh; null tier renders "—").
  Tests: new `test_submit_background.py` (3): assessment+XAI+C1 land after submit · a background
  crash never blocks/undoes the submission · **red flag still forces Critical from the background
  with the model down (rule #3)**. **162 pass** (was 159), 6.1 s.
- Decided: no new ADR — this is the implementation of the already-locked ADR-0042(b).
- Broke / problem: none; all submit-dependent suites (staff routes, risk, report/review,
  suggested condition, risk override) passed unchanged thanks to the engine-binding seam.
- Deferred: P1-6 (kiosk polish — the leftover blue tints in kiosk.html inline CSS), then P2→P4.
  Live-run caveat: TestClient runs background tasks synchronously, so the "instant return" is
  proven by design/tests offline — the human live run will see the real wall-clock win.
- Next: **P1-6** — Patient Portal UI polish (closes P1): retint `#EFF6FF`/`#BFDBFE`/`#F1F5F9` in
  `frontend/kiosk.html` to teal equivalents + visual polish; layouts/hooks untouched.

## Session 20 — 2026-07-10 — 2.0 build: P1-3 (4–5 follow-up floor + deepening) + P1-4 (missing-field highlight); 159 tests
- Did: two tracker items, one per "go":
  - **P1-3 (backend — first of the cycle):** the main follow-up loop now always asks **4–5**
    history-grounded questions. (1) `config.py`: `followup_min_questions=4` (cap stays 5).
    (2) `routes_followup.py` `_loop_state()`: "complete" needs the 0.7 threshold **AND** ≥4
    questions asked; cap exit unchanged; `scope=fields` resume loop untouched. (3) M7
    (`services/followup.py`): human-approved broadened `_QUESTION_SYSTEM` — gap-filling first,
    then **DEEPENING** questions grounded in the conversation (severity 1–10, location/spread,
    triggers/relievers, progression, impact, past episodes, family history) when the gap list is
    exhausted (main loop only; fields scope still stops); fixed the `remaining[0]` salvage
    fallbacks that would crash on an empty list. Tests: new `test_followup_min_questions.py`
    (floor-via-deepening incl. non-JSON salvage · cap terminates when floor>cap · fields scope
    unaffected) + 2 existing tests updated to the new spec (`test_followup_loop.py` drives to the
    floor and asserts exactly 4; `test_resume_loop.py` asserts the main loop stays open at 0 asked,
    re-serving the open question). **159 pass** (was 156).
  - **P1-4 (frontend):** kiosk summary — empty REQUIRED fields (the `HIGHLIGHT_FIELDS` set) now get
    `.summary-item.missing` (amber warning border/tint) + a bilingual **"Needs info / তথ্য প্রয়োজন"**
    chip that follows the P1-2 language toggle; optional empties stay muted "Not mentioned".
    Preview-verified (classes, chip EN↔BN, screenshot; no console errors).
- Decided: no new ADR — the 4–5-question floor was already locked in ADR-0042(3); the human
  approved the exact M7 prompt wording in-session before it was coded.
- Broke / problem: none. Note for the live run: every visit now spends ~3 more Groq M7 calls +
  M8 merges than before (still tiny vs the ~1,000/day free tier).
- Deferred: P1-5 (background-assessed submit), P1-6 (kiosk polish — incl. retinting the leftover
  blue tints in kiosk.html inline CSS: #EFF6FF/#BFDBFE/#F1F5F9), then P2→P4.
- Next: **P1-5** — move the 3 blocking LLM calls in `submit_visit` (M10/M11/M10C) into FastAPI
  `BackgroundTasks` so Confirm & Submit returns instantly (status+audit stay synchronous).

## Session 19 — 2026-07-10 — 2.0 build: STRUCT-2/3 + P1-1/P1-2 (logout, teal theme, auto-stop, full i18n)
- Did: executed four tracker items, one per "go", each preview-verified with a stubbed `api`
  (no backend/LLM calls — rule #4):
  - **STRUCT-2 (logout):** shared `logout()` in `frontend_shared/shared.js` + a bilingual Logout
    button in ALL THREE portal headers (medic + doctor + kiosk) → returns to the Portal Directory
    `/`. Verified: button renders, "লগআউট" in Bangla, click lands on `/`, no console errors.
  - **STRUCT-3 (theme):** shared palette evolved to **"Teal Medical"** (ADR-0043) — `:root` tokens
    (primary `#0F766E`, secondary `#0D9488`, bg `#F0FBF8`, radius 10px, teal shadows) + retinted
    the ~10 hardcoded blue tints in `shared.css`; semantic risk-badge colors untouched; CLAUDE.md
    FRONTEND section updated. Human chose Option A (teal) over Option B (ocean blue) from LIVE
    in-browser previews of both on the real medic portal. Verified teal on `/`, kiosk, medic, doctor.
  - **P1-1 (Summary auto-stops mic):** `kiosk.js` — new `submitFinalTurn()` + reworked
    `finishConversation()`: clicking "Done — see summary" now stops the mic, flushes the captured
    words as the final turn (answer path posts `followup/answer` and IGNORES the next question;
    opening path posts the utterance + re-runs intake so the words are extracted), then summarizes.
    `state.finishing` reentry guard. Verified: both flush paths + empty-buffer + triple-click.
  - **P1-2 (full language toggle):** `kiosk.js`/`shared.js`/`kiosk.html` — bubble labels + bilingual
    bodies carry `data-en/bn` so shared `applyLanguage()` re-translates them; new `setBilingualText()`
    keeps JS-written text (OTP subtitle, mic hints) toggle-safe; live transcript mirrored into both
    language slots so a mid-recording toggle can't wipe it; 🔊 tooltips refresh in `onLanguageChange`;
    shared `applyLanguage()` gained `data-en/bn-placeholder` support (+ the 2 fallback inputs).
    **Patient bubbles carry NO dataset — verbatim forever (rule #1)**; server questions (EN+BN in one
    string) left as captured. Verified the exact spec bug ("সহকারী / আপনার সমস্যাটি…" → EN and back)
    plus OTP subtitle, hints, transcript, placeholders — full EN↔BN round-trip.
- Decided: **ADR-0043** — shared palette = "Teal Medical" (Option A, chosen from live previews;
  ADR-0029 structure + semantic risk colors kept).
- Broke / problem: none functional. The preview **screenshot** capturer wedged during P1-2 (tooling
  hiccup; page JS confirmed alive via eval) — used the accessibility snapshot as proof instead.
  **No pytest run this session** (changes were frontend HTML/CSS/JS only); P1-3 will add tests.
- Deferred: P1-3 → P4 (unchanged queue). Per-portal UI polish (P1-6/P2-3/P3-4) still pending on top
  of the shared teal base.
- Next: **P1-3** — force 4–5 intelligent, history-based follow-ups (backend: `followup_min_questions`
  gate in `config.py`/`routes_followup.py` + deepening-question generation in `services/followup.py`
  + a new test; keep the 156-test suite green).

## Session 18 — 2026-07-09 — "Context Fixed Problem 2.0" spec captured + planned; STRUCT-1 done
- Did: (1) Oriented from the session files. (2) The human delivered a NEW work spec —
  `agent_docs/context fixed problem 2.0.md` (UI/UX redesign + functional fixes across all three
  portals, real OTP, and a doctor-side AI drug-info chatbot) plus 3 healthcare reference
  screenshots and a stated priority order. (3) Explored the codebase (frontend portals, backend
  pipeline, OTP/auth) and turned the spec into a priority-sequenced, checkable plan (saved to the
  Claude plan file; the priority checklist is now mirrored in `current_task.md`). Plan APPROVED.
  (3b) Converted `agent_docs/context fixed problem 2.0.md` into a living, checkable **BUILD TRACKER**
  (plan IDs + status + the files each item touches, original requirements kept verbatim below it) so
  any future session sees exactly what's done/left — STRUCT-1 ✅, STRUCT-2 👉 next.
  (4) Implemented **STRUCT-1**: renamed the 4 user-facing "Patient Kiosk" strings → "Patient Portal"
  (EN + Bangla "রোগী পোর্টাল") in `frontend/index.html:41` + `frontend/kiosk.html:6,81,200`;
  file names/URLs (`/kiosk.html`, `/kiosk.js`) kept so routes don't break. No backend touched.
- Decided: **ADR-0042** — approach for the 2.0 build: (a) UI = *evolve the theme* (shift shared
  `:root` tokens toward the teal/modern reference look + polish; KEEP all existing layouts &
  wired features — no 1:1 screenshot copy, no layout rebuild); (b) Confirm & Submit = *assess in
  background* (M10/M11/M10C move to a FastAPI BackgroundTasks job so submit returns instantly);
  (c) execute priority-by-priority, functional fixes before polish, ONE item per "go". The faculty
  "Future Features" (quantized Moshi / quantized STT-TTS) are OUT of scope for this spec.
- Broke / problem: none (STRUCT-1 was a string-only change; not a code path, so no tests run).
- Deferred: everything from STRUCT-2 onward — logout buttons, theme tokens, and all of P1–P4.
  Two items still need a human choice at build time: the exact **OTP delivery channel** (P4 —
  free reliable OTP-to-any-phone is not feasible; recommend persisted-OTP seam + `000000` bypass +
  one free reference channel) and a **look at the teal palette** before it's applied broadly.
- Next: **STRUCT-2** — add a Logout button to the medic + doctor headers that returns to the
  Portal Directory (`/`), plus an optional shared `logout()` in `frontend_shared/shared.js`.

## Session 17 — 2026-07-07 — Quota audit + quota-aware free-provider switching (ADR-0041)
- Did: (1) **API quota audit**: counted all LLM usage from `module_events` (33 lifetime events;
  visit 7 = the clean 13-call Session-8c run; visit 8 on 07-06 = M4 failing) + one read-only
  OpenRouter `GET /api/v1/key` (free tier confirmed, $0 usage). Found the "voice transcribes but
  formatting fails" bug: **Gemini Flash 429s were invisible** (only the LAST provider in the chain
  was logged) and the only fallback was OpenRouter `:free`, which itself 429'd **10× in ~9s** with
  no backoff — while Groq (1,000 free req/day) was never tried. (2) **Fix built (ADR-0041)**:
  `llm_client.py` now logs EVERY attempt to `module_events` (error rows incl. provider + message),
  puts a provider on **cooldown after a 429/quota error** (60s RPM / 15min daily, fail-open when
  all cool down), and `llm_providers.py` gained a universal `FALLBACK_ORDER` = assigned → Groq →
  Cerebras → Mistral → OpenRouter (blank-key buckets auto-skipped; Gemini buckets deliberately not
  cross-fallbacks). New optional free buckets in `config.py`/`.env.example`: **Cerebras**
  (~1M tok/day) and **Mistral Experiment** (trains on inputs — rule #4 warning, off by default).
  New `tests/conftest.py` (autouse cooldown reset) + `test_llm_client.py` (6 tests). **156 pass.**
- Decided: ADR-0041 (quota-aware cooldown + extended free fallback chain). Web research logged:
  Gemini Flash free ≈ 10 RPM / 1,500 RPD (resets midnight PT), Groq ≈ 1,000 RPD, OpenRouter
  `:free` ≈ 50 RPD, Cerebras ≈ 1M tok/day, Mistral ≈ 1B tok/month but 2 RPM + trains on data.
- Broke / problem: none; `test_intake.py::test_fallback_is_used_and_logged` updated for the new
  per-attempt error rows. Root cause of WHY Gemini Flash 429'd on 07-06 still unconfirmed (the
  old code didn't log it) — the new logging will show it on the next live run.
- Deferred: optional Cerebras key signup (human); $10 OpenRouter top-up (optional); everything
  from S16 (live real-mic run, Windows Bangla voice, key rotation, bug/feature list).
- Next: unchanged from S16 — human's bug list + faculty features → numbered spec → plan step 1.

## Session 16 — 2026-07-07 — Arch Linux TTS: installed + VERIFIED working (🔊 + mic confirmed by human)
- Did: finished the Session-15 Arch TTS fix. The human ran `sudo pacman -S speech-dispatcher
  espeak-ng`; I then verified the whole chain. System layer PASS: `espeak-ng --voices` lists `bn`
  (Bengali, `inc/bn`), rendered `আমার মাথা ব্যথা করছে` → valid **81,202-byte WAV** (RIFF PCM 16-bit
  mono 22050 Hz), `spd-say` exit 0. Then debugged why Chromium's `speechSynthesis.getVoices()` was
  **empty `[]`** despite the working synth: (a) the running Chromium (PID 10193) had started
  **before** the packages existed and caches the voice list at process start; (b) the speech-
  dispatcher daemon wasn't up and Chromium's sandbox can't spawn it. Fix: started the daemon and
  **`systemctl --user start speech-dispatcher.socket`** (it was `enabled` but not active) so Chromium
  triggers the daemon via socket activation; then the human **fully quit Chromium** (`pkill chromium`,
  not just a reload — Wayland keeps the process alive) and relaunched with `chromium
  --enable-speech-dispatcher`. Result: **getVoices() non-empty, 🔊 speaks, and the mic works** on
  Arch → **TC-V2 audio PASS on Arch** (human-confirmed). No application code changed.
- Decided: **ADR-0040** — Linux TTS/STT dev setup: `speech-dispatcher` + `espeak-ng`, stay on
  Chromium (do NOT require Google Chrome), rely on the enabled `speech-dispatcher.socket` +
  `--enable-speech-dispatcher`, and a FULL Chromium restart after install.
- Broke / problem: none now. (Prior blocker — empty `getVoices()` — was a stale pre-install
  Chromium process + no running daemon; both resolved.) Voice is espeak-ng-robotic (expected).
- Deferred: the full human **live real-mic run** (TC-V1 WER/latency, TC-V3 voice-only loop, TC-F2,
  TC-R1, TC-A1) + Windows Bangla voice + key rotation — all still pending. **The human also flagged
  (a) some bugs to fix next and (b) possible new features per faculty requirements** — NOT yet
  enumerated; next session must collect that list first and plan it one step per "go".
- Next: get the human's bug list + faculty requirements, turn them into a numbered spec (like
  `context_fixed_problem.md`), and plan step 1.

## Session 15 — 2026-07-07 — Arch Linux TTS fix: diagnosed + documented (PART 1B)
- Did: chased down why the kiosk 🔊 button is **silent on the Arch laptop**. Read-only
  diagnostics confirmed it is **system-level, not a code bug**: `speech-dispatcher` and
  `espeak-ng` are **not installed** and the speechd service is inactive, so Linux Chromium's
  `speechSynthesis.getVoices()` is empty and `frontend_shared/tts.js` correctly degrades to
  text-only (ADR-0028). The existing `human_live_run_guide.md` only covered the **Windows**
  Bangla-voice install. Added a new **"🐧 PART 1B — Enable a Bangla voice on Arch Linux"**
  section right after the Windows PART 1: `sudo pacman -S speech-dispatcher espeak-ng`,
  `espeak-ng --voices | grep bn` + `spd-say` verification, "fully restart Chromium", the same
  `getVoices().filter(bn)` console check + "hint banner gone = ✅" success test, and a note that
  the espeak-ng Bengali voice is robotic (expected; text stays primary) and STT is unaffected.
  **No application code changed** — `_pickBanglaVoice()`/`banglaVoiceAvailable()` already match
  any `bn*` voice, so they start working once the packages exist.
- Decided: nothing at ADR level — this is a docs/system-setup step, not an architecture choice.
  Confirmed scope with the human: **TTS only** (their mic/STT works), and **stay on Chromium**
  (do NOT switch to Google Chrome).
- Broke / problem: the `pacman` install needs `sudo` and could not be run from the non-interactive
  agent shell, so the fix is **documented but NOT yet installed/verified** on the Arch box.
- Deferred: the human runs the one `pacman` line, then verify (espeak-ng bn voice + `spd-say`
  audible → Chromium `getVoices` non-empty → kiosk `#voice-hint` gone + 🔊 speaks = TC-V2 on Arch).
  Everything from S14 still pending too (the full live real-mic run + Windows Bangla voice + key rotation).
- Next: human installs `speech-dispatcher`+`espeak-ng`, then I verify the three checks above.

## Session 14 — 2026-07-07 — Step 20 of 20 (FINAL): test gate + status flips + doc sweep — BUILD COMPLETE
- Did: closed the 20-step fix/feature build. Re-ran the gate — `pytest backend/tests/` = **150
  passed**. Flipped all stale markers in `context_fixed_problem.md` to ✅ (its "Last updated" was
  2026-07-05, predating S11/S13): **KIOSK-4/5/6/7** (S11 steps 8–11; KIOSK-7 = ADR-0034),
  **MEDIC-1/2/5** (S11 step 12) + **MEDIC-3** (S11 step 13, ADR-0035), **DOCTOR-3** (S13 step 17),
  **DOCTOR-4/5** (S13 step 18, ADR-0038), **DOCTOR-6** (S13 step 19, ADR-0039), and **DOCTOR-7**
  🟨→✅ (S13 steps 17–19) — each with a one-line "Done" note; added a "BUILD COMPLETE" banner +
  refreshed the header date/ADR list. Every numbered spec item is now ✅ (no ⬜/🟨 left except the
  legend). Marked the 20-step build complete in `milestone_log.md` while **deliberately keeping the
  15-module status table 🟨** (those gate on the human live-voice run, not build completion).
  `test_log.md` got a one-line S14 gate entry. Also (same session): wrote a plain-language
  **`agent_docs/human_live_run_guide.md`** for the human — start-the-app, install a Bangla TTS
  voice on Windows, the live-test walkthrough (each step mapped to TC-V1/V2/V3/F2/R1), and
  key rotation (which key → which `.env` line → where to get a fresh one). Refreshed the stale
  **`CLAUDE.md`** status line (was "Session 8 / Alembic 0009 / 104 tests" → now Session 14 /
  Alembic 0010 / 150 tests / build complete, pointing at the new guide).
- Decided: nothing new — step 20 is a sweep, no ADR (ADR-0031–0039 already cover the build).
- Broke / problem: none. Docs-only; no application code, DB, or patient data touched.
- Deferred: NOT build work — the **human live real-mic run** (TC-V2/V3/F2/R1/A1, real keys already
  in `.env`) and installing a Bangla TTS voice on the Windows box (kiosk audio). Any polish the
  live run surfaces.
- Next: hand off to the human live run; there is no further coded step in the 20-step plan.

## Session 13 — 2026-07-06 — Steps 17–19 of 20: DOCTOR-3 patient-details · DOCTOR-4/5 prescription form · DOCTOR-6 prescription .docx + save
- Did (step 19, DOCTOR-6, ADR-0039): the prescription **Submit** now saves + downloads.
  New `render_prescription(payload)` in `services/documents/visit_docx.py` (LOCAL .docx:
  letterhead · patient · symptoms · **Diagnosis verbatim from payload** · medicines table ·
  advice/tests/follow-up · signature) and `generate_prescription_document()` in
  `services/documents/__init__.py` (render → store → `create_document(kind="prescription")` →
  persist a `prescriptions` row linked by `document_id`). New endpoint
  `POST /api/visits/{uuid}/prescription` (body `{doctor_id, payload}`; 404 visit/doctor, 400
  non-doctor; audit `prescription.created`; returns `{prescription_id, document}`). A **new**
  prescription + docx per Submit (append). Frontend: `submitPrescription()` POSTs, auto-downloads
  the .docx (anchor-click, like the medic), and shows a "✅ Saved & Downloaded" confirmation with a
  re-download link (the step-18 preview fn removed). The .docx writer reads ONLY the payload, so
  the Diagnosis is structurally un-AI-fillable (rule #2) — regression-tested. New
  `test_prescription_docx.py` (5). **150 tests pass** (145 + 5). Verified live: real POST created a
  prescription row + linked document, downloaded the .docx and confirmed it contains the diagnosis,
  medicine, clinic, patient; frontend Submit wiring checked with a stubbed POST (body/auto-download/
  confirmation), no console errors.
- Did (step 18, DOCTOR-4/5, ADR-0038): a **Prescription form** in the doctor portal.
  Backend (small, read-only): `GET /api/visits/{uuid}/prescription/context?doctor_id=`
  (new `routes_prescription.py` + `schemas/prescription.py`) returns **letterhead only**
  (clinic + doctor); 404 unknown visit/doctor, 400 non-doctor. Patient + the 10 symptoms
  are assembled client-side from the already-loaded case (no re-send). An idempotent
  `seed_demo_letterhead()` (new `backend/app/db/seed.py`, run in `lifespan`) fills the NULL
  letterhead columns on the demo clinic + doctors with sample values (never clobbers a real
  value). New `test_prescription_context.py` (6). **No prescription is persisted in step 18**
  — the DB row + .docx are created together at Submit in step 19 (DOCTOR-6). Frontend
  (`frontend_doctor/index.html`): "📝 Write Prescription" in the review bar opens a full-screen
  `#prescription-screen` form — letterhead (editable, prefilled) · Date · Patient
  (auto-filled) · Symptoms (auto-filled from `summary_fields`) · **Diagnosis EMPTY, doctor-
  authored, never AI-filled (rule #2)** · Medicines table with **add/remove rows** · Advice ·
  Tests · Follow-up · signature line. `rxDraft` state survives the EN↔বাংলা toggle;
  `collectPrescriptionPayload()` assembles the payload (empty medicine rows filtered);
  Submit shows an inline preview (the .docx/download replaces it in step 19). **145 tests
  pass** (139 + 6). Browser-verified (stubbed context): full autofill, empty Diagnosis,
  add/remove + language-toggle persistence, ≥1-row guard, payload correct, no console errors,
  screenshot of the rendered form.
- Did (step 17, DOCTOR-3, frontend-only, `frontend_doctor/index.html`): the doctor case
  view now shows — right after the safety panel — a **Patient Details card** (Name · Phone ·
  Age-from-`birth_year` · Gender · Weight · Blood Pressure) reading the patient embedded in
  `GET /visits/{uuid}` (`VisitDetailWithPatientOut`), with **inline weight + BP editing** that
  reuses `PATCH /patients/{id}/vitals` (already permits role=doctor — **zero backend change**);
  a mounted **`#condition-card`** so the shared `renderConditionCard()` surfaces the C1 AI
  suggestion + reasoning + "not a diagnosis" disclaimer (identical to the medic — closes part of
  DOCTOR-7); and the **C2 display band** (`tierBand()`) beside the risk tier badge in
  `renderSafety()`. New page functions: `onDoctorCaseLoaded()` (renders patient details then
  loads risk — replaces `loadRisk` as the `PORTAL.onCaseLoaded` hook), `renderPatientDetails()`,
  `saveVitals()` (weight range + ≥1-field validation), `genderLabel()`; `onLanguageChange()`
  re-renders the patient card. Bilingual throughout; raw verbatim + patient name are never
  translated (rule #1). **139 tests still pass** (no backend touched). Browser-verified with
  stubbed network: all 6 fields correct, band renders "HIGH 51–75%", condition card + disclaimer,
  EN↔বাংলা toggle, edit fires `PATCH /api/patients/42/vitals` body `{editor_id, weight_kg, bp}`
  and updates the card, empty/invalid-weight guards block the call, no console errors, screenshot
  confirms the layout order (safety → patient → condition).
- Decided: **ADR-0038** (step 18, form + read-only letterhead prefill; save deferred) +
  **ADR-0039** (step 19, dedicated `POST …/prescription` saves row + renders .docx; new
  prescription per Submit; Diagnosis structurally un-AI-fillable). Step 17 needed no ADR
  (reuses C1/ADR-0036, C2 band, ADR-0037).
- Broke / problem: none. The preview server stopped between edits twice (restarted cleanly);
  `preview_screenshot` worked this session. Note: the startup letterhead seed only runs on
  server (re)start.
- Deferred: Step 20 (final): full `pytest` sweep + doc sweep + flip the `context_fixed_problem`
  DOCTOR-3/4/5/6/7 (+ any still-open KIOSK/MEDIC/STRUCT) statuses to done; sanity-eyeball all
  three portals. The whole 20-step build then closes.
- Next: Step 20 — final test + doc sweep + `context_fixed_problem` status flips. See `current_task.md`.

## Session 12 — 2026-07-06 — Steps 14–16 of 20: C1 suggested condition (MEDIC-4) + post-referral summary & docx (MEDIC-6/7) + doctor toggle/polish (DOCTOR-1/2/7)
- Did: **Step 14 (MEDIC-4/C1, ADR-0036):** new module **M10C** (Flash bucket, deliberately a
  SEPARATE call from M10 so the risk prompt's no-disease-names rule is never contaminated)
  generates a bilingual "Possible Condition (AI Suggestion – Not a Diagnosis)" + reasoning at
  kiosk submit, best-effort (LLM down → no suggestion, submit never blocked). Stored at
  `case_profiles.entities["suggested_condition"]` (no migration) with 10-field-style provenance
  AND the "not a diagnosis" disclaimers embedded IN the object — every payload carrying the
  suggestion carries them. `PATCH /visits/{uuid}/profile/condition` staff edit (403 non-staff,
  all language slots untranslated, disclaimer re-attached server-side, audit `profile.condition_edit`).
  Shared `renderConditionCard()` in staff.js; medic mounts `#condition-card`; kiosk has no mount.
  New `test_suggested_condition.py` (5). **Step 15 (MEDIC-6/7):** "Submit & Forward" now lands on
  a bilingual post-referral summary (snapshot-as-referred): patient card (name/phone/age-from-
  birth-year/**weight inline-edit**/BP), risk tier + C2 band + flags + XAI, the disclaimered
  condition, all 10 Q&A rows, ⬇ Download Report (.docx) + Back to Queue. New
  `PATCH /patients/{id}/vitals` (staff-only, 0–500 kg validated, audit `patient.vitals_edit`);
  `GET /visits/{uuid}` now embeds the patient with vitals (`VisitDetailWithPatientOut`, defined in
  patient.py to avoid a schema import cycle). M12 report sections gain vitals +
  `suggested_condition`; the summary_report docx renders the C1 block with both disclaimers; and
  the docx is assembled from a **FRESH report at download time** — staleness after staff
  edits/overrides was the hidden "download doesn't really work" failure. New
  `test_medic_summary.py` (5, incl. the staleness regression). **Step 16 (DOCTOR-1/2/7):** doctor
  portal fully bilingual (EN/বাংলা toggle, data-en/bn on all chrome, safety panel re-renders from
  state via `renderSafety()`, placeholders switch); **↻ Queue removed** (auto-refresh + post-review
  reload already cover it; the medic's Refresh-Queue stays — it clears the phone filter);
  `@media print` block (case content prints, chrome doesn't); responsive flex-wrap.
  **139 tests pass** (129 + 5 + 5). All frontend steps browser-verified with stubbed network.
- Decided: ADR-0036 (C1 = separate M10C call; embedded disclaimer; staff-only; never the doctor's
  Diagnosis field); ADR-0037 (post-referral summary = snapshot + fresh-report-on-download +
  patient embedded in visit detail + patient-scoped vitals PATCH).
- Broke / problem: `preview_screenshot` worked early in the session then timed out again
  (S11 flakiness) — post-referral screen + doctor toggle proven via eval + a11y snapshot;
  worth a human eyeball of `/medic/` after a forward and `/doctor/` in বাংলা (Ctrl+F5 first).
- Deferred: Steps 17–20 (one per "go"): DOCTOR-3 patient-details card (17, mounts the shared
  condition card + vitals from the now-embedded patient) · prescription form (18, Diagnosis
  defaults EMPTY — rule #2, per ADR-0036) · prescription docx + save (19) · final sweep (20).
  DOCTOR-7 stays 🟨 until 17–19 land its remaining identification targets.
- Next: Step 17 — DOCTOR-3: patient-details card in the doctor portal. See `current_task.md`.

## Session 11 — 2026-07-06 — Steps 8–13 of 20: kiosk summary complete (KIOSK-4/5/6/7) + medic bilingual/polish/refresh (MEDIC-1/2/5) + risk override (MEDIC-3)
- Did: **Step 8 (KIOSK-4):** bilingual "Download Raw Transcript (.docx)" button on the kiosk
  summary screen (before Confirm & Submit), wired to the existing step-3 endpoint via a
  temporary-anchor click (kiosk page never navigates away); no backend change.
  **Step 9 (KIOSK-5):** summary redesigned — each of the 10 fields is its own card (18px
  radius, backdrop blur, soft shadow, icon chip 🩺⏱️📋🤒📖💊⚠️🔄🩹💬, bold primary-blue
  titles); clinically key fields (main problem, duration, symptom details, medicines,
  allergies) get a left accent border + value badge; empty = muted-italic "Not mentioned /
  উল্লেখ করা হয়নি"; clinical-blue tokens only. **Step 10 (KIOSK-6):** summary follows the
  language toggle end-to-end — `renderSummary()` reads via `fieldValue()`, profile kept as
  `state.lastProfile`, `onLanguageChange()` re-renders; legacy `{value}` rows display as-is.
  **Step 11 (KIOSK-7, ADR-0034):** resume loop live — `?scope=fields` on `followup/next`
  + `followup/answer` (no 0.7-threshold gate; missing = empty summary-field keys via new
  `missing_summary_fields()`; `target_gap` forced to a real field key so "নেই/জানি না"
  is never re-asked; SHARED per-visit question cap). Kiosk: progress chip ("৮/১০ তথ্য
  সম্পন্ন"), resume voice dock on the summary screen (one recognition engine serves both
  docks via `activeDock()`), Confirm & Submit hidden while a question is open, summary
  regenerates after every answer, FAIL-OPEN (cap/API-error → submit returns; never trap
  the patient). New `test_resume_loop.py` (5 tests). **Step 12 (MEDIC-1/2/5):** staff.js
  fully bilingual (labels+icons, badges, verbatim chrome via t(); values via fieldValue();
  new `staffLanguageRefresh()`), medic portal gets the EN/বাংলা toggle + data-en/bn on all
  static text; "↻ Queue" → "↻ Refresh Queue / তালিকা রিফ্রেশ" (clears the phone filter +
  reloads — its one clear job); field-card icon chips + queue hover in shared.css; doctor
  portal (shares staff.js) regression-checked. **Step 13 (MEDIC-3, ADR-0035):**
  `POST /api/visits/{uuid}/risk/override` — appends a `model_provider='human'`
  risk_assessments row (AI rows never edited), carries red_flags + rule_overrode forward,
  stores a reason (constitution), audit_logs from/to/reason; **red-flag Critical cannot be
  downgraded by staff (409)** — only the doctor decides at review. Medic risk panel: tier
  badge + C2 display band + AI/Human badge + red flags + XAI + override select (labels
  from TIER_LABELS, band per tier) + reason box. New `test_risk_override.py` (3 tests).
  **129 tests pass** (121 + 5 + 3). All frontend steps browser-verified with stubbed
  network (no live LLM spend).
- Decided: ADR-0034 (resume loop = `?scope=fields` on the existing endpoints; shared
  question cap; asked-once = answered); ADR-0035 (risk override = appended human row, no
  migration; red-flag-Critical downgrade blocked for staff).
- Broke / problem: `preview_screenshot` tool times out this session (page itself healthy —
  all assertions via eval/a11y snapshot); the step-9 visual is worth a human eyeball at
  /kiosk.html (Ctrl+F5 first).
- Deferred: Steps 14–20 (one per "go"): C1 suggested condition (14) · post-referral
  summary + docx (15) · doctor toggle+polish (16) · patient-details card (17) ·
  prescription form (18) · prescription docx + save (19) · final sweep (20). Real-M7
  resume-loop questions over Groq untested by design — covered by the next live-mic run.
- Next: Step 14 — MEDIC-4 / C1: "Possible Condition (AI Suggestion – Not a Diagnosis)"
  section (clearly labeled, disclaimer, editable; doctor's Diagnosis never AI-filled —
  needs its own ADR per the locked C1 note). See `current_task.md`.

## Session 10 — 2026-07-06 — Fix/feature build continues: steps 6–7 (KIOSK-1 OTP + KIOSK-2/3 TTS UX)
- Did: **Step 6 DONE (KIOSK-1):** `frontend/kiosk.js` gains `initOtpInputs()` — typing a
  digit auto-focuses the next `.otp-input` (repeated digits like 000000 flow smoothly),
  non-digits are stripped, Backspace on an empty box clears + focuses the previous one,
  and pasting fills the boxes from box 1 (junk stripped, e.g. "code: 04-73-92" → 047392;
  short pastes focus the next empty box). `kiosk.html` boxes gain `inputmode="numeric"`
  + `autocomplete="one-time-code"`. All 5 behaviors asserted live in Chrome + screenshot.
  **Step 7 DONE (KIOSK-2/3):** (a) ROOT CAUSE of "Repeat Question does nothing" found and
  CONFIRMED live: the button always fired — **this Windows machine has NO Bangla TTS voice**
  (`banglaVoiceAvailable() === false`), so speech was silently absent (TC-V2, recorded in
  test_log.md). Fix = make the state visible: a bilingual `#voice-hint` banner shows on the
  voice screen whenever no bn voice exists (chained onto tts.js's `onvoiceschanged`, not
  replacing it); on-screen text stays the fallback (ADR-0028). (b) `addBubble()` now puts a
  🔊 icon on EVERY chat bubble — assistant icon replays that question; patient icon reads
  back EXACTLY the words captured at bubble creation (rule #1, never re-fetched/rewritten).
  The Repeat-Question button is KEPT alongside the icons (KIOSK-2 and KIOSK-3 are separate
  spec items; the button is also the accessibility-friendly big target). Browser-verified
  via a `speak()` spy: both icons + the repeat button speak the exact right text; hint
  toggles correctly both ways. **121 tests pass** (frontend-only; no backend change).
- Decided: nothing new (no ADR — bug fix + spec'd UI; the keep-the-repeat-button call is
  recorded here).
- Broke / problem: Browser CACHE bit twice — a stale kiosk.js made the first verification
  round of step 6 report false failures. Rule for preview checks: `fetch(url,
  {cache:'reload'})` + reload BEFORE asserting. The human should Ctrl+F5 the kiosk once.
- Deferred: Steps 8–20 (one per "go"). Installing a Bangla TTS voice on the Windows box
  (Settings → Time & Language → Speech → Add voices → Bengali) so TC-V2 can PASS with
  audio — human action, worth doing before the re-run.
- Next: Step 8 — kiosk "Download Raw Transcript (.docx)" button wired to the step-3
  endpoint `POST /api/visits/{uuid}/documents/transcript` (KIOSK-4). See `current_task.md`.

## Session 9 — 2026-07-05 — Fix/feature build from the human's Part-2 test: steps 1–5 of 20
- Did: The human's real-mic Part-2 run surfaced bugs + feature gaps, written up as
  `agent_docs/context_fixed_problem.md` (stable IDs: STRUCT/KIOSK/MEDIC/DOCTOR). A 20-step
  sequenced plan was approved with all open decisions resolved: C1 = "Possible Condition
  (AI Suggestion – Not a Diagnosis)" allowed with disclaimer + editable, doctor's Diagnosis
  never AI-filled; C2 = display-only tier→band mapping, NO stored numeric risk scores;
  legacy → `/legacy/` + `/` landing page; prescriptions/reports DB-backed (documents.visit_id
  + kinds + prescriptions table, Alembic 0010); bilingual summary values generated once and
  stored (`value_bn`/`value_en`, back-compat with `{value}`); clinic/doctor letterhead in DB;
  KIOSK-7 = resume loop asking only missing fields, cap respected, "নেই/জানি না" accepted.
  **Step 1 DONE (STRUCT-1/2, ADR-0031):** legacy demo `git mv`-ed to `frontend_legacy/`
  (asset refs made relative), mounted at `/legacy/`; new clinical-blue landing page at `/`
  linking all four entry points; `ENTRY_POINTS` list logged at startup; new
  `test_routes_static.py` (5 tests). **Step 2 DONE (ADR-0032):** Alembic rev
  `0010_prescriptions_letterhead` written AND applied to the real DB (backup
  `prescreener.db.pre-0010.bak`): `documents.utterance_id` now nullable (visit-grain
  exports), `patients.weight_kg`+`bp`, users/clinics letterhead columns, new
  `prescriptions` table (payload JSON, document_id link). Discovery that shrank the step:
  `documents.visit_id` already existed since 0003 and `patients` already had
  `birth_year`/`sex` — no duplicates added. Models updated (+`Prescription`); new
  `test_migration_0010.py` (4 tests incl. rule-#1 raw-preservation across the rebuild).
  architecture.md gained §8 (rev-0010 deltas). **Step 3 DONE:** visit-grain docx seam —
  new `services/documents/visit_docx.py` (full-visit RAW transcript writer, verbatim
  role-labeled turns; staff summary-report writer rendering the stored M12 sections with
  bilingual field labels + red flags + disclaimer), `generate_visit_document()` orchestrator
  (documents row: `visit_id` set, `utterance_id` NULL), `create_document` repo + DocumentOut
  schema extended (both grains), new route `POST /api/visits/{uuid}/documents/{kind}`
  (`routes_visit_documents.py`; download reuses `/api/documents/{id}/download`). New
  `test_visit_documents.py` (3 tests: byte-exact raw turns, field labels/values/disclaimer,
  route guards). **Step 4 DONE:** `shared.js` gains `fieldValue(field)` (bilingual summary
  values: picks `value_bn`/`value_en` by the active language, falls back cross-language,
  then to the legacy `{value}` shape, then ''; display-only, never writes back) and the C2
  `TIER_BANDS` map + `tierBand(tier)` (fixed display-only percentage band per tier — no
  numeric score generated/stored/wired). Verified live in the browser preview (all shapes +
  fallbacks + bands correct, zero console errors). **Step 5 DONE (ADR-0033):** M3/M8 now
  emit BOTH `value_en` + `value_bn` per field in ONE extraction call ({"en","bn"} reply
  shape; plain-string replies salvaged as English); stored shape `{value, value_en,
  value_bn, source, ...}` with `value` mirroring `value_en` so every legacy consumer/row
  works; M9 `field_has_text()` counts any slot; staff PATCH edits write the typed text to
  ALL slots untranslated (authoritative, no quota); `visit_docx._field_value()` falls back
  across slots. Test fakes updated + new `test_bilingual_fields.py` (5 back-compat tests)
  + a staff-PATCH slot assertion. **121 tests pass** (104 + 5 + 4 + 3 + 5).
- Decided: ADR-0031 (legacy isolation + landing page + startup URL log); ADR-0032 (rev 0010:
  one documents table with two grains, DB letterhead, prescriptions payload as JSON,
  human-only Diagnosis per C1, no stored risk scores per C2); ADR-0033 (bilingual values:
  one extraction call fills en+bn, `value` mirrors value_en, staff edits fill all slots
  untranslated).
- Broke / problem: Nothing. Note: legacy `index.html` used absolute `/styles.css`+`/app.js` —
  would have 404'd under `/legacy/`; caught before shipping, made relative.
- Deferred: Steps 6–20 (kiosk fixes KIOSK-1..7, medic MEDIC-1..7, doctor DOCTOR-1..7,
  final doc sweep) — one approved step at a time. Note: values stored by OLD intake runs
  stay English-only until re-extracted; new runs are bilingual.
- Next: Step 6 — kiosk OTP auto-advance + Backspace + paste (KIOSK-1). See
  `current_task.md`.

## Session 8c — 2026-07-03 — Live-run Part 1 PASSED: full pipeline live with real keys, all three buckets verified
- Did: (A) Added the human-provided **GROQ_API_KEY + OPENROUTER_API_KEY** to `backend/.env`
  (Gemini untouched) — the Session-8b key gap is CLOSED. (B) Ran **live-run Part 1** end-to-end
  with SYNTHETIC typed Banglish (no mic): phone lookup → stub OTP → visit → 2 utterances →
  `/intake` → follow-up loop (2 real Bangla questions from Groq, loop exited at completeness
  0.7) → `/assess` (tier=medium, no red flags — correct for headache+mild fever) → `/report`.
  (C) Verified `module_events`: **13 rows, all status=ok, ZERO fallbacks** — M3/M8=
  gemini_flash_lite, M4/M10/M11=gemini_flash, M6/M7=groq, M12=local — exactly the ADR-0026
  bucket map, live. Latencies 484–8577 ms. (D) `pytest backend/tests/` still **104 passing**.
  Numbers in test_log.md.
- Decided: nothing new (this executes the existing plan; no ADR).
- Broke / problem: Only a cosmetic Windows console issue: printing Bangla from a driver script
  needs `PYTHONIOENCODING=utf-8` (cp1252 UnicodeEncodeError) — not a code bug, backend unaffected.
  Note: the keys were pasted in chat; `.env` is gitignored so the repo is safe, but rotate the
  keys before any public demo.
- Deferred: **Part 2 — the human real-mic kiosk run** (TC-V1/V2/V3/F2/R1 + a live TC-A1
  pull-a-key test) — inherently the human's job. Then `.docx` per-visit report export, optional
  PDF, Phase-1 faster-whisper. Still: ~50 samples + WER, real SMS OTP/auth, encryption at rest.
- Next: Human does Part 2 in Chrome (`/kiosk.html` → speak → follow-ups → submit → `/medic/` →
  forward → `/doctor/` → review) and records TC-V2/V3/F2/R1/A1 in test_log.md. See
  `current_task.md`.

## Session 8b — 2026-07-03 — ADR-0029 doc rewrite executed + FIRST live Gemini verification
- Did: (A) Executed the deferred **ADR-0029 design-system switch in the docs**: CLAUDE.md's
  frontend section now points at the clinical-blue system (`frontend_shared/shared.css`) as the
  source of truth (with the TIER_LABELS rule + Noto Sans Bengali + the read-only-raw rule) and its
  status/stack lines updated; `DESIGN-mintlify.md` got a **SUPERSEDED banner** at the top (ADR-0029)
  with a compact clinical-blue token summary, keeping the old Mintlify analysis only as historical
  reference. (B) Ran the **first-ever LIVE LLM call** in the project: one real Gemini correction on
  synthetic Banglish — see test_log.md.
- Decided: nothing new (ADR-0029/0030 already stand; this executes them).
- Broke / problem: **Live-run gap surfaced, not a code bug:** only `GEMINI_API_KEY` is set;
  `GROQ_API_KEY` and `OPENROUTER_API_KEY` are EMPTY. Since M6 (gaps) + M7 (follow-up) are assigned
  to the Groq bucket with OpenRouter as the only fallback, a FULL live intake/loop cannot complete
  until a Groq OR OpenRouter key is added. All of it passes offline (LLM faked) — purely a missing
  key, not a code issue.
- Deferred: The full live pipeline (blocked on a Groq/OpenRouter key) and the human mic test
  (I cannot operate a real microphone — the voice portion is inherently the human's part).
- Next: Add a Groq (or OpenRouter) key to `backend/.env`, then run a full live pipeline with
  synthetic typed text; separately, the human does the real-voice kiosk run in Chrome. Record
  TC-V2/V3/F2/R1/A1. See `current_task.md`.

## Session 8 — 2026-07-03 — Mockup reconciliation + FULL-STACK BUILD: DB 0003–0009, backend M3–M12 pipeline, three portals
- Did: The biggest build session so far. (A) **Reconciliation:** reconciled `mockups-redesign.html`
  against architecture.md → new `agent_docs/reconciliation.md` + architecture.md §7. Human decided:
  'medic' is a real role; OTP is a stub; the mockup's clinical-blue design system replaces Mintlify
  (ADR-0029). (B) **Database:** Alembic revs **0003–0009 all written AND applied** to the real DB
  (backup .bak per rev): clinics/users/patients/visits (+'medic' role, 'awaiting_doctor' status,
  `assigned_doctor_id` — ADR-0030), case_profiles, module_events, followup_questions,
  risk_assessments, xai_explanations, reports, doctor_reviews, feedback, audit_log. Legacy
  utterances backfilled onto synthetic closed visits; seeds: 1 clinic, 1 medic, 2 doctors, 1 admin.
  (C) **Backend:** visits API + phone lookup + stub OTP (`DEV_OTP`); LLM provider registry +
  fallback + module_events logging (ADR-0026 as data); intake M3→M4→M6 writing the enforced
  10-field `summary_fields` JSON; follow-up loop M7 (Groq, no repeats, question stored + spoken)
  → M8 (merge; human edits never overwritten) → M9 (LOCAL completeness, threshold/max-turn exit);
  **M10 risk with the LOCAL red-flag rule list (5 categories, Bangla/Banglish/English) that forces
  Critical and survives total LLM outage** + M11 XAI (deterministic fallback reason); local M12
  report (Red Flags section + no-diagnosis disclaimer); staff endpoints (submit→auto-assess,
  dashboard queues, field-edit PATCH, assign); doctor review (accept/override→'reviewed') +
  feedback; audit rows on every state change. (D) **Frontend:** `frontend_shared/` (clinical-blue
  CSS, TIER_LABELS, EN/BN helper, tts.js `speak()` — Step A1 shipped), patient kiosk at
  `/kiosk.html` (phone→OTP→voice chat with STT bn-BD + TTS→10-field summary→submit→auto-logout),
  medic portal `/medic/`, doctor portal `/doctor/`. Old Module-1 app at `/` untouched.
- Decided: ADR-0029 (mockup clinical-blue design system supersedes Mintlify) and ADR-0030
  (medic role, `assigned_doctor_id`, 'awaiting_doctor', stub OTP, 10-field JSON shape, tier
  display labels, OTP-typing clarification) — both written to decisions.md mid-session.
  Implementation choices: M12 report assembly is LOCAL (no quota); model failure in M10 degrades
  to 'medium', never 'low' (rule #3); each legacy utterance = its own closed visit.
- Broke / problem: (1) Found + FIXED a pre-existing crash: this Windows machine's DB was a
  MIXED-state legacy DB (had `stt_provider`, lacked `documents.kind`) — the old blind
  stamp-at-0001 died with 'duplicate column'; `database.py` now picks the stamp revision from the
  ACTUAL columns (regression-tested). (2) alembic wasn't installed in the Windows venv (S6 ran on
  Arch) — installed from requirements.txt. (3) Batch-mode FKs need explicit names (0003 fixed).
- Deferred: Real SMS OTP, real auth (still stubbed), PDF export, per-visit report .docx export,
  Postgres (G7 = config), Phase 1 faster-whisper. CLAUDE.md + DESIGN doc rewrite per ADR-0029
  (awaiting explicit go). LIVE end-to-end run with real Gemini/Groq calls — the human's manual
  check (quota). Still from S4–S6: live mic test + ~50 samples + WER/latency.
- Next: Human live test in Chrome (`/kiosk.html` → speak → follow-ups → submit → `/medic/` →
  forward → `/doctor/` → review), with real keys in backend/.env; record TC-V2/V3/F2/R1/A1
  results + Bangla-voice availability per OS in test_log.md. Then the ADR-0029 doc rewrite.
  See `current_task.md`.

## Session 7 — 2026-06-25 — Architect planning lock: flowchart + final stack + per-module API strategy + voice model
- Did: A planning-only session (NO code). Locked the FINAL project plan ahead of vibe-coding.
  (A) **Flowchart:** removed the standalone Emergency module from the Patient Journey diagram —
  deleted node `D1` ("Emergency Detected?"), node `AX` (escalation alert), the `M4→D1`, `D1→No→M6`,
  `D1→Yes→AX` and the dashed `AX→` continuation arrows; added a direct `M4→M6` arrow; dropped the
  now-unused `DECA`, `ALTB`, `RA` styles and the "Emergency" legend entry. Reconstructed the whole
  TikZ source into `update_system_flowchart.md` (the original file was NOT in the uploaded set —
  marked as a reconstruction to diff against the real one). (B) **Safety preserved:** folded a
  lightweight **rule-based red-flag check into Module 10 (Risk Assessment)** that forces the
  **Critical** tier for clearly life-threatening symptoms, with a **Red Flags** section in the M12
  report; revised constitution rule #3 from "emergency detection runs first" to "surface red flags;
  never reassure falsely". (C) **Stack:** CONFIRMED the existing stack (no rewrite) and **added
  browser TTS** for M7 + a deploy path. (D) **API strategy:** assigned each LLM module across three
  independent free quota buckets (Gemini Flash / Gemini Flash-Lite / Groq) with OpenRouter `:free`
  as universal fallback. (E) **Voice:** patient input is **voice-only**; M7 questions show as **text
  AND play as audio (TTS) simultaneously**; manual text box demoted to a mic-failure fallback.
  (F) Rewrote the tracking docs (CLAUDE.md, constitution.md, Context, decisions.md, changelog.md,
  current_task.md, milestone_log.md, test_log.md, codebase_map.md; session_protocol.md unchanged).
- Decided: ADR-0024 (retire Emergency module, fold red-flag check into M10, keep numbering with an
  M5 gap), ADR-0025 (confirm stack + add browser TTS + deploy path), ADR-0026 (per-module free-API
  assignment, refines ADR-0003), ADR-0027 (voice model: STT `bn-BD` + `SpeechSynthesis` TTS,
  voice-only patient replies, manual text = fallback), ADR-0028 (follow-up = on-screen text AND
  spoken audio simultaneously).
- Broke / problem: Nothing built, so nothing broke. **Open conflict flagged, not silently resolved:**
  removing the Emergency module contradicts the *original* non-negotiable rule #3 and the Module
  10/12 dependency columns — this is a SAFETY-relevant change for a medical tool, so it is recorded
  as Open Flag 1 (recommended default: keep the rule-based red-flag check in M10, which is how the
  files are now written). `update_system_flowchart.md` is a reconstruction — node positions / exact
  fill colours are best-effort and must be diffed against the real file before committing.
- Deferred: Building any of the new modules (M2–M15) — still Phase 0. The actual M7 TTS code, the
  per-module provider config wiring, and the OpenRouter $10 top-up decision. Still deferred from
  S4/S5/S6: the human live mic test + ~50 samples + WER/latency on real speech.
- Next: First coding task = **Phase A / Step A1** of the build plan — add browser **TTS** to the
  existing frontend (speak a test Bangla string via `speechSynthesis`, on-screen text stays as
  fallback), planned-then-approved per CLAUDE.md before any code. See `current_task.md`.

## Session 6 — 2026-06-21 — Two separate raw/corrected .docx + Alembic migration (fix stt_provider bug)
- Did: (A) FIXED the live `sqlite3.OperationalError: table utterances has no column named
  stt_provider` by adopting **Alembic**. New `backend/alembic.ini` + `backend/migrations/`
  (env.py reads the URL from app settings, `render_as_batch=True` for SQLite) with two
  revisions: `0001_baseline` (original schema) and `0002` (adds `utterances.stt_provider` +
  `documents.kind`). `init_db()` now runs `run_migrations()` — stamps the baseline on a
  legacy DB, then `upgrade head`; fresh DBs build from scratch; re-runs no-op. Verified on
  the REAL db (2 rows preserved) + a fresh db; backed up the pre-migration db to
  `backend/data/prescreener.db.pre-alembic.bak`. (B) Split document export into TWO separate,
  independently downloadable files: added `documents.kind` ("raw"|"corrected"; legacy
  "combined"); `DocumentWriter.render(utterance, *, kind)` → DocxWriter renders raw-only
  ("Transcript") or corrected-only ("Corrected Transcript"); `generate_session_document(kind=…)`;
  repo `create_document(kind=…)` + `get_latest_document`. New routes (kept `/api/*`):
  `GET /api/transcripts/{id}` (TranscriptDetailOut: raw+corrected text + both doc links),
  `POST /api/transcripts/{id}/documents/raw`, `…/documents/corrected`; `/api/correct` now
  best-effort generates the CORRECTED doc and returns the detail. (C) Frontend: raw is now
  saved + a raw .docx generated when recording STOPS (not only on Correct); added per-panel
  "Download Raw/Corrected .docx" buttons (enabled when each file exists), loading states
  (Saving…/Generating document…/Correcting text…), and the exact spec error strings.
  (D) Config: added `STT_PROVIDER` + `DOCUMENT_OUTPUT_PATH` (alias of DOCUMENTS_DIR) +
  documented `DATABASE_URL`; updated `.env.example` and `.env`. Added a `backend-linux`
  launch.json config (the existing one is Windows-only `.venv/Scripts/python.exe`).
- Decided: Alembic + auto-migrate-at-startup with legacy baseline-stamp (ADR-0022); raw and
  corrected exported as SEPARATE docs via a `documents.kind` column, dedicated documents
  table kept over flat path columns, `/api/*` prefix kept (ADR-0023, decided with the human).
- Broke / problem: One real issue surfaced at END of session — `preview_start` failed with
  `spawn .venv/Scripts/python.exe ENOENT`: the DEFAULT `.claude/launch.json` config uses the
  WINDOWS venv path, which doesn't exist on Arch. Workaround: launch the new `backend-linux`
  config (`.venv/bin/python`) explicitly — that starts cleanly (earlier this session the
  server ran fine that way). NOT yet OS-robust (no single launch.json default works on both
  machines; the preview panel picks the first config). Test gotchas fixed during dev:
  TestClient runs sync endpoints in a threadpool, so the route test needed `StaticPool` to
  share the in-memory SQLite across threads; the preview screenshot tool timed out (renderer),
  but functional verification via preview_eval was conclusive. A synthetic session #3 raw doc
  was created in the dev DB during verification (harmless; gitignored, like S5's session #5).
- Deferred: LIVE Gemini correction in-browser + opening both .docx in Word/LibreOffice to
  confirm Bangla renders (human's manual check — not auto-run to save free quota). PDF /
  Markdown writers (format seam ready), version-history UI, auth, cloud storage, Patient/Visit
  tables. Still deferred from S4/S5: the human live mic test + ~50 samples + WER/latency.
- Next: Human live test in Chrome — record → Stop (raw .docx auto-saves + downloads) →
  Correct (corrected .docx) → open both, confirm Bangla renders + RAW unchanged; collect
  samples. See `current_task.md`.

## Session 5 — 2026-06-21 — Auto-generate & store .docx per session + Saved Documents UI
- Did: Added automatic Word-document export for completed sessions (additive, nothing
  existing broken). New `Document` SQLAlchemy model (UUID PK, FK → Utterance, format,
  filename, rel_path, created_at) + repo `create_document`/`get_document`/
  `list_documents`. New `services/documents/` layer: `DocumentWriter` ABC, `DocxWriter`
  (python-docx; renders Raw verbatim + Corrected + metadata; Bengali font set on Latin
  AND complex-script slots), `storage.py` filesystem abstraction (S3-swappable), and a
  `build_writer()` seam + `generate_session_document()` orchestrator. New routes
  `GET /api/documents` (list) and `GET /api/documents/{id}/download` (FileResponse, Word
  media type). `/api/correct` now best-effort generates the .docx after a successful
  correction (a docx failure logs but never fails the correction). Added `documents_dir`
  config (env-overridable, default `backend/data/documents`, no hardcoded paths) and
  `python-docx==1.1.2` to requirements.txt. Frontend: "Saved documents (.docx)" panel
  (Mintlify-styled) listing docs with download links, auto-refreshed after correction.
- Decided: A `.docx` is a DERIVED export artifact; the DB stays the source of truth
  (regenerable, preserves rule #1, avoids Bangla round-trip loss). python-docx (pure
  Python, cross-platform). Filesystem storage now, behind a swappable interface.
  Document grain = one Utterance/session; NO Patient/Visit tables yet. DOCX now, PDF
  later (clean `format` seam). (ADR-0021.)
- Broke / problem: Nothing broke. Note: passing a multi-line python `-c` with Bangla
  string literals through PowerShell mangled the quotes — used a temp script file
  instead (deleted after). Port-8000 orphaned-socket workaround (port 8001) still stands.
- Deferred: PDF generation + in-browser preview; Patient/Visit data model; auth on the
  document routes; cloud (S3/MinIO) storage. All have seams left in place. Still
  deferred from S4: the human live mic test + ~50 samples + WER/latency.
- Next: Human live test — record/correct in Chrome, confirm a .docx auto-saves and
  downloads + opens correctly (Bangla renders), alongside the mic/sample collection.

## Session 4 — 2026-06-20 — Simplify to browser-only STT + Mintlify UI + scrollable panels
- Did: (A) REMOVED the multi-provider STT architecture per the human's new plan —
  deleted `backend/app/services/stt/`, `api/routes_stt.py`, `test_stt_registry.py`,
  the three `requirements-*.txt`, all STT config + the `.env` STT block,
  `python-multipart`, and the startup health log. Recreated the venv from
  requirements.txt (clean core: fastapi 0.115.6, starlette 0.41.3; torch/
  transformers/qwen gone). Module 1 STT is now ONLY the browser Web Speech API.
  Rewrote the frontend for continuous recording: no cap, append-only verbatim
  transcript, brief pauses keep going (restart on `onend`), auto-stop after ~10s
  of silence. (B) Restyled the whole frontend to `DESIGN-mintlify.md` (Inter font,
  black pill buttons, mint-green accent for Start + active, 12px cards, hairline
  borders) and made the 3 transcript panels (Raw/Corrected/Manual) fixed-height,
  scrollable, with stick-to-bottom auto-scroll. Added the Frontend/Transcript-UI
  rules to CLAUDE.md.
- Decided: Browser Web Speech API is the only Module 1 STT (others return later);
  keep a clean seam (the `stt_provider` column stays). Drop the banglaspeech2text
  package permanently. Frontend follows DESIGN-mintlify.md. (ADR-0019, ADR-0020.)
- Broke / problem: A previous session left an ORPHANED socket holding port 8000
  (process dead, leaked handle keeps it LISTENING; clears on reboot). Worked around
  by switching `.claude/launch.json` to **port 8001**.
- Deferred: Live mic test of the continuous-recording + 10s-silence behavior (the
  human's manual check in Chrome). Collecting ~50 samples + WER/latency. Switching
  launch.json back to 8000 after a reboot. Regenerating the (now-removed) Groq key
  is moot since Groq STT was removed.
- Next: Human does the live mic test (speak, pause briefly, then go silent ~10s to
  confirm auto-stop) and collects samples. See `current_task.md`.

## Session 3 — 2026-06-19 — Multi-provider STT (5 providers) + provider health + installs
- Did: Re-planned Phase 0 to support 5 swappable STT providers with frontend
  switching. Built `backend/app/services/stt/` (STTProvider ABC + ProviderInfo
  health + registry + audio.py decode + 5 providers: browser_webspeech,
  groq_whisper, local_whisper, banglaspeech2text, qwen_asr). Added endpoints
  `GET /api/stt/providers`, `POST /api/transcribe`, `POST /api/transcripts`;
  refactored `/api/correct` to correct by utterance_id; added `Utterance.stt_provider`.
  Rewrote the frontend (provider dropdown + status badges, Start/Stop, MM:SS timer
  with 5-min auto-stop, raw/corrected copy+clear, manual fallback, error banner).
  Added a startup STT health log. Then FIXED 5 issues the human reported: documented
  QWEN_ASR_MODEL_DIR (optional, auto-download); rich provider health
  (available/missing_api_key/missing_package/missing_model/unsupported_platform/error)
  shown in the UI; resolved the huggingface-hub dependency conflict; split installs
  into per-provider requirements files; wrote INSTALL.md. INSTALLED all engines and
  verified the local transcribe paths.
- Decided: Drop the unmaintained `banglaspeech2text` pip package (pins
  huggingface-hub==0.11.1) and run shhossain/whisper-*-bn via `transformers`
  instead. Per-provider optional requirements files. Server STT = record→upload→
  transcribe; browser stays live. (ADR-0015 to ADR-0018.)
- Broke / problem: `requirements-local.txt` had a real conflict (fixed by the split).
  `torch==2.5.1` pin had no Python-3.14 wheel → unpinned (got torch 2.12.1).
  `qwen-asr` is INVASIVE: it bumped fastapi 0.115→0.137, starlette→1.3, transformers
  5→4.57, huggingface_hub→0.36 and pulled gradio/flask. App still works (13 tests
  pass, server boots) but Qwen may warrant its own venv.
- Deferred: Live Groq STT test (would spend the human's free quota). Qwen live run
  (3.4 GB download + very slow on CPU) — installed/ready but unverified. WER/latency
  on real Bangla speech. Regenerating the exposed Groq key (human action).
- Next: Human runs the live mic test for each provider in Chrome, collects ~50
  samples, and records real latency/WER. See `current_task.md`.

## Session 2 — 2026-06-19 — Phase 0 Steps 3–5: correction service + API + frontend
- Did: Built the correction service (Step 3): `services/correction/base.py`
  (`Corrector` ABC) + `openai_compatible.py` (`OpenAICompatibleCorrector` +
  `build_corrector()` + strict prompt + manual `__main__` live check) and
  `test_corrector.py` (4 offline guards). Built the API (Step 4):
  `schemas/transcript.py`, `api/routes_transcripts.py` (`POST /api/correct`,
  `GET /api/transcripts`), and `main.py` (lifespan `init_db`, `/health`, serves
  frontend or a placeholder). Built the frontend (Step 5): `frontend/index.html`,
  `app.js` (Web Speech API bn-BD, interim grey / final verbatim), `styles.css`.
  Fixed `.claude/launch.json` to use the venv Python. Ran the server via the
  preview tool and verified the page renders with no console errors.
- Decided: `POST /api/correct` persists RAW *before* calling the LLM, so raw
  survives a correction failure (502 with raw kept); misconfig fails fast (500).
  Recorded as ADR-0013.
- Broke / problem: `launch.json` first used system `python` (no uvicorn) → fixed to
  `.venv/Scripts/python.exe` (Windows-specific; Arch needs `.venv/bin/python`).
- Deferred: Live Gemini call NOT auto-run (spends free-tier quota) — left as a
  manual check for the human. No automated test for `/api/correct` (would hit the
  network). Groq/OpenRouter still interface-only. Frontend = plain HTML/JS (React later).
- Next: Step 6 — human runs the end-to-end live mic test in Chrome on both
  machines and collects ~50 sample utterances. See `current_task.md`.

## Session 1 — 2026-06-19 — Phase 0 scaffolding + backend skeleton (Steps 1–2)
- Did: Approved the Phase 0 plan, then built the foundation (not a throwaway
  demo folder): `requirements.txt`, `.gitignore`, `backend/.env` + `.env.example`,
  and the backend skeleton — `backend/app/core/config.py` (pydantic-settings),
  `backend/app/db/` (database.py, models.py `Utterance`, repository.py), and
  `backend/tests/test_raw_immutable.py`. Installed deps in `.venv` and ran tests.
- Decided: Build the real `backend/` + `frontend/` structure now (foundation for
  the full app); SQLite via a repository layer; one FastAPI server serving the
  frontend; mic + manual-text fallback; correction via the OpenAI-compatible
  client pointed at Gemini (swappable). Recorded as ADR-0009 to ADR-0011.
- Broke / problem: Pinned `SQLAlchemy==2.0.36` crashed on Python 3.14.4
  (typing-union `__getitem__` bug). Fixed by upgrading to `2.0.51` and re-pinning.
- Deferred: Gemini code + the actual network call, API routes, frontend
  (Steps 3–5). Groq/OpenRouter fallback (interface only). The human still needs to
  REGENERATE the pasted Gemini key and put it in `backend/.env`.
- Next: Step 3 — correction service (`Corrector` ABC + `OpenAICompatibleCorrector`
  with the strict correct-only prompt). See `current_task.md`.

## Session 0 — 2026-06-18 — Project setup & memory system
- Did: Created the project memory system: `CLAUDE.md` plus `agent_docs/`
  (constitution, milestone_log, current_task, changelog, test_log, decisions,
  codebase_map, session_protocol). No code yet.
- Decided: Locked in the starting stack and key choices — recorded as
  ADR-0001 to ADR-0008 in `decisions.md`.
- Broke / problem: None (nothing built yet).
- Deferred: All actual coding. AMD-GPU acceleration deferred (CPU-only first).
  Real Bangla-fine-tuned model deferred to Phase 2.
- Next: Build the Phase 0 demo (browser Web Speech API live Bangla transcription
  + free-LLM correction). Plan it with the human before coding.
  See `current_task.md`.
