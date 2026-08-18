# milestone_log.md — Big-Picture Status Board

> This answers one question: **"Where are we in the whole project right now?"**
> Update the status when a module's state changes. Keep the "Done means" line
> honest and testable — not "works well", but a real, checkable definition.

**Status keys:** ⬜ Not started · 🟨 In progress · 🟦 Blocked · ✅ Done · ⛔ Retired

**Last updated:** 2026-08-19 (**Session 42 — DEMO-HARDENING. The reported Patient-Portal 502 root-caused
and fixed, the provider chain given real redundancy, and the raw upstream provider error stopped from
reaching the patient's screen. 1056 → 1087 tests pass, 2 skipped, 0 failures.** New ADR **0067**.
⚠ **No schema, migration, Alembic, dependency, FHIR, PDF, OTP or auth change. Head stays 0014, 18 tables.**
⚠ **NO MODULE CHANGED STATUS.** **M15 stays 🟨.**
⚠ **No STT/TTS logic changed** — the speech pipeline is exactly as S41 left it.

**THE ROOT CAUSE WAS THREE FAULTS, AND THE REPORTED ONE WAS THE LEAST IMPORTANT.** (1) Groq's
`llama-3.3-70b-versatile` is **DECOMMISSIONED** — no Llama chat model remains in Groq's live model
list and the call answers `404 model_not_found`. Groq is `FALLBACK_ORDER[0]`, so the *first* bucket
every module falls back to had been silently dead. (2) OpenRouter's `google/gemma-4-31b-it:free`
answered **429 from its SHARED upstream pool** — and that bucket is ADR-0026's *universal fallback*.
(3) Which left **Gemini as the only working provider**, so its ordinary free daily 429 took the whole
system down and `POST /visits/<uuid>/intake` returned 502. The error text named only the last
provider to fail, which is why it presented as an OpenRouter problem.

⚠ **AND THE PATIENT WAS BEING SHOWN THE UPSTREAM PROVIDER'S ERROR BODY.** Six routes answered
`HTTPException(502, detail=str(exc))`; `str(exc)` ends in the raw provider reply, measured as carrying
the model id, `'provider_name': 'Google AI Studio'` and a signup URL — and the kiosk pipes `detail`
straight into its banner. That is configuration disclosure from a system handling medical data. It is
now converted at ONE helper (`api/_llm_errors.py`) that every LLM route uses, and a test walks
`routes_*.py` and fails if any file handling `LLMCallError` skips it.

**A PROVIDER BUCKET NOW NAMES SEVERAL MODELS.** `OPENROUTER_MODEL` is comma-separated and each entry
becomes its own attempt with its **own cooldown** — keyed on `bucket|model`, because the provider's
429 names a MODEL, not a bucket, so cooling the whole bucket skipped healthy siblings.
⚠ Measured during the outage: the configured id and one sibling were 429 while **three other `:free`
siblings answered the identical request correctly in the same minute**. A `:free` id is not a quota
you own, it is a queue you SHARE — so pinning the universal fallback to one id is a single point of
failure by construction, and S41's one-id-for-one-id fix could only hold until that id got busy.

**MODELS REPLACED WITH LIVE-VERIFIED ONES.** Groq → `openai/gpt-oss-120b`, checked against this
project's real M3 extraction prompt: valid JSON, the patient's name preserved in Bangla script
("রফিক"), ~2.8 s. ⚠ **Rejected in the same measurement:** `qwen/qwen3.6-27b` emits a `<think>` block
that breaks `_parse_json`, and `groq/compound*` are agentic models with **built-in web search** —
sending patient speech to a search tool would breach rule #4.

**ONE BOUNDED RETRY, PLUS A BOUND ON THE WHOLE CALL.** Transient failures (429/5xx/timeout) get
exactly one more pass after ~1.5 s; a 404 model_not_found or a 401 gets none. Separately
`CALL_DEADLINE_S = 90` bounds the ENTIRE call — unbounded it was five attempts x 45 s x a retry pass
= **7.5 minutes** of spinner, and "stuck loading" is worse than an honest error because an error at
least carries the retry button.

**A TOTAL OUTAGE IS NOW A WAIT THE PATIENT CAN ACT ON.** An amber panel — deliberately **not red**,
because an upstream queue clearing in a moment is a WAIT and danger-red tells an unwell patient
something is wrong with *them* — says "The assistant is busy right now / Your answers are saved" in
both languages and offers **Try again**. It does not auto-hide.
⚠ **The retry resumes from the step that FAILED and never re-posts the utterance** — re-posting would
write the patient's sentence into their verbatim record twice (rule #1).

⚠ **VERIFIED LIVE, NOT SIMULATED — and the original failure condition is ACTIVE.** Gemini's free daily
quota is genuinely exhausted on this machine (limit 20/day); under the old code that call *was* the
reported 502, and it now falls back to Groq in 825 ms with intake completing in 7.3 s. A second
uvicorn was run with deliberately invalid keys (the human's `.env` untouched) to force a REAL total
outage: 502 + `Retry-After: 30`, **zero** leaked terms, the bilingual panel shown, **all four patient
utterances stored verbatim through the outage**, and **Try again** completing the intake with **zero
duplicates**. The full patient flow then ran end to end into the medic queue as HIGH, and the medic
**Edit → Save** button measured at y=677 in a 720px viewport (S41's fix intact).
⚠ **NO REAL-MICROPHONE RUN** — the browser here reports `microphone: denied`. Everything used the
typed path, which is the SAME pipeline (ADR-0048). S42 changed no STT code.

**Last updated:** 2026-08-15 (**Session 41 — the four defects the human's REAL-MICROPHONE run
surfaced are fixed, the synthetic test visit is deleted, and the API keys are now checkable.
1031 → 1056 tests pass, 2 skipped, 0 failures.** New ADR **0066**.
⚠ **No schema, migration, route, service, FHIR, PDF, OTP or auth change** — the only backend edit is
ONE configuration default. **Alembic stays 0014. 18 tables. No new dependency.**
⚠ **NO MODULE CHANGED STATUS.** **M15 stays 🟨.**
⚠ **No voice/STT/TTS logic changed** — kiosk.js gained one scroll helper and one changed constant.

**THE PATIENT'S OWN WORDS STAY IN THEIR BOX.** Bangla and Banglish arrive from the recogniser as long
runs with almost no break opportunities (a spoken phone number has none at all), and the transcript
card had no wrapping rule — so the patient's speech ran straight out of it. Fixed on the BASE rule so
all four docks are covered at once, plus `min-width: 0`, which is the less obvious half: the box is a
flex item and a flex item defaults to `min-width: auto`, refusing to shrink below its content. The
box is now bounded (`max-height: 30vh`) and scrolls itself, with `flex: none` so it stops being
squeezed back to its minimum the moment an answer gets long.
⚠ **And it must NOT be flex-centred** — that is a rule #1 concern, not a style one: a flex container
with `align-items: center` and overflowing content pushes the TOP of that content above the scroll
origin, **where it cannot be scrolled back to**, so a patient would silently lose the beginning of
their own answer. It is `display: block`, and it scrolls its newest line into view as they talk —
inside the box only, never the page.

**"THE MICROPHONE IS OPEN" IS NOW SAID IN WORDS.** "Listening..." describes the machine; a patient who
has never used a computer needs to be told what THEY should do, in the first two words. The wording is
now **"🎤 You can speak now" / "🎤 এখন কথা বলুন"**, changed in the ONE `LISTENING_HINT` constant every
dock reads through `listeningHint()` — one edit, four docks, no second implementation. It is a filled
banner rather than merely larger red text, because colour is never the only carrier of a state a
patient must not get wrong, and SPEAKING/PROCESSING get a deliberately quieter, different treatment:
"wait" must not look like "talk" across a room.
⚠ The claim is **retracted the instant it stops being true** — `stopListening()` rewrites the hint in
the same call that clears the listening class. Now pinned by a test: the UI communicates state, it
never fakes it.

**"CLICKING EDIT DOES NOT WORK" (MEDIC) WAS A SCROLL, NOT A REWIRE.** The button always worked.
Measured at 1280x720: the form opened at y=461 and its **Save button landed at y=727**, below a 720px
fold, inside a case workspace that scrolls independently and was sitting at `scrollTop: 0` — nothing
the medic could see changed and there was no visible way to save. Everything else in that flow was
verified healthy in the same pass: the click is not intercepted, the save round-trips, a reading
without its measurement context is still refused, and switching patients does not leak the previous
patient's values.
⚠ **The first fix silently did nothing, and the reason is recorded because it will recur:** smooth
`scrollIntoView` left `scrollTop` at 0 even after 1.5 s on that container, while `behavior: 'auto'`
moved it by exactly the 55px needed — the workspace carries `perspective: 1400px` from the S37 depth
layer, and Chromium declines to smooth-scroll a scroller inside a 3D rendering context. Removing the
perspective would trade a real visual regression for an animation, so the animation gives way:
`bringIntoView()` now attempts smooth, checks `isFullyInView()`, and finishes instantly if it did not
land. It also **moved from kiosk.js into shared.js** — one definition, front-end-wide, pinned.

**THE SYNTHETIC TEST VISIT IS GONE, after being proved deletable rather than assumed to be.** All 8
referencing tables enumerated first (21 rows), the repo searched for the phone number, every test
confirmed to build its own in-memory SQLite, a timestamped backup written, identity guards
re-asserted inside the transaction, and `documents`/`prescriptions` counts verified unchanged
afterwards. ⚠ The human's own real-microphone visit was explicitly checked still present.

**API KEYS — checked, not rotated.** Rotation needs provider logins and stays the human's. What is new
is `backend/scripts/check_api_keys.py`, which proves each key authenticates and **never prints, logs
or writes a key value**. It immediately found a dead safety net: `OPENROUTER_MODEL` pointed at a model
OpenRouter has **RETIRED**, so ADR-0026's **universal fallback** — the bucket every module drops to
when its own quota is spent — was returning 404, on a day when the Gemini bucket was already sitting
at its daily 429. Replaced and verified by a real completion that came back correctly in Bengali.

⚠ **REAL-MICROPHONE STATUS — the distinction is kept deliberately.** The successful real-mic run is
the **HUMAN's**, reported by them and **corroborated** by the dev DB, which holds `source='mic'`
Bengali utterances on visit 23 (2026-08-14 18:08–18:11) for a visit that reached `reviewed`. **This
session did not and could not perform one** — the browser here reports `microphone: denied` with no
readable audio-input labels. Nothing is claimed as agent-performed microphone testing.
⚠ **What was NOT verified: APPEARANCE.** Still no screenshot (the Browser pane composites no frames
here). Everything is measured DOM geometry and computed style across 1280/768/375 px, plus clean
consoles on fresh tabs for all three portals.

**Last updated:** 2026-08-14 (**Session 40 — the reported Medic-portal outage root-caused and fixed,
the patient kiosk given its clarity redesign, and the test gap that let the outage ship closed.
1005 → 1031 tests pass, 2 skipped, 0 failures.** New ADR **0065**.
⚠ **NO BACKEND FILE WAS TOUCHED** — no route, service, schema, migration, FHIR builder, PDF renderer,
OTP path or auth code. **Alembic stays 0014. 18 tables. No new dependency.**
⚠ **NO MODULE CHANGED STATUS.** The work is entirely in the three front ends. **M15 stays 🟨.**
⚠ **S40 changed NO voice/STT/TTS logic**, so the real-mic status is unchanged.

**THE MEDIC-PORTAL OUTAGE — one root cause, BOTH reported symptoms, and it was never the backend.**
Reported as two things: `ড্যাশবোর্ডে প্রবেশ করুন` did not enter the dashboard, and the portal showed
no time. They were the same defect. S39 had added a developer note inside `renderPostReferral()`'s
**template literal**, written as an HTML comment, and the note named the `patients` table **in
backticks** — and a backtick inside a template literal *ends it*, so the browser parsed the next word
as code and threw `SyntaxError: Unexpected identifier 'patients'`.
A syntax error is not partial: **the entire `<script>` block is discarded before one line of it
runs**, so every function it declared was undefined. `login()` did not exist, and `tickClock()` never
ran — which is why the S38 clock sat on its "—" placeholder. The `304 Not Modified` lines in the log
were a red herring; every asset was served correctly and one of them could not be parsed.
The fix is **where the note lives, not how it is escaped**: escaping the backticks would have worked
and left the trap armed, so the paragraph moved into the existing `/* S39 */` JS comment above the
function. Verified in a real browser, clicking the Bangla button that was reported.

⚠ **WHY 1005 PASSING TESTS COULD NOT SEE IT.** Every frontend test in this project is a
static-source assertion (the S28 decision — no vitest, no jsdom). The file still *contained* every
string those tests search for; the source was intact and only its **executability** was gone. This is
exactly the gap S39 recorded about itself ("no browser has rendered the new portal DOM"). It is now
closed in two layers that add **no runtime dependency**: a dependency-free ban on the precise
construct, and a `node --check` parse of every inline block and shared script which **skips with a
reason** when node is not on PATH. Both layers were **proved non-vacuous** against the pre-fix blob.

**THE KIOSK — split by WHOSE side of the conversation it is.** The reported problem was not that it
was ugly but that it was *not understandable* for a child, an elderly patient, or someone who has
never used a computer. It had been one tall column — robot, then the whole conversation, then a dock
holding the transcript, the read-back, the countdown, three buttons, a hint, a mode switch and a text
box — so "where the AI is" and "where I speak" were the same place, stacked, with the patient's own
words in the middle of the pile. Now: **machine on the left, patient on the right**, their live words
large and upright in a box that turns red-edged while the mic is open, a 92px microphone, and a
three-step strip (1 I ask · 2 You speak · 3 You check) that shows the order of the exchange without a
sentence to read.
⚠ Built with grid **PLACEMENT and no wrapper elements** — the DOM, every id, every `aria-live`
relationship and the screen-reader reading order are unchanged, and one media query returns the page
to exactly the single column it was before.
⚠ **The step strip has NO JavaScript** and `data-kiosk-stage` is set only by the function that opens
the read-back gate and cleared by the one that closes it — the gate reporting itself, never a second
state machine that could tell a patient the mic is open when it is not (ADR-0054's rule).
⚠ While an answer waits to be checked, everything else is **dimmed, NEVER disabled** — no
`pointer-events: none`, no `display: none`, asserted per CSS rule by a test: a patient reaching for
the mouse must still be able to use it, and hiding controls mid-turn is how a kiosk traps someone.
⚠ Automatic movement is **`block: 'nearest'`** and nothing else, so an element already on screen does
not move at all — and it is **never** called per recognition result, because scrolling on every
interim chunk is how a page becomes unusable while someone is talking.

**THE REVIEW PAGE — the answers take column 1, what to DO about them takes column 2.** The three
buttons had been a full-width bar at the very bottom, so the patient scrolled past every answer card
to reach the one action the screen exists for. The assistant, the still-missing notice and the
buttons are now one **sticky** rail beside the answers, "✔ Confirm & Submit" first and full width.
⚠ Placed with **`order`, not `grid-column`**: an explicit column would create an implicit second
track the moment any single-column rule applies, which is the exact bug S36 fixed on this grid — so
`.no-float` and both media queries kept working untouched.

⚠ **What was NOT verified this session: APPEARANCE.** No screenshot could be taken (the Browser pane
was not displayed, so it composites no frames). Everything claimed above is **measured DOM geometry
and computed style** in a real browser — two columns at 1280px, one at 900 and 375, no horizontal
scroll at any width, both review columns top-aligned, dimmed-but-clickable confirmed — plus a real
end-to-end kiosk session (phone → OTP → conversation → 10-card Bangla review) with a clean console.
That is precise about position and state and **silent about how it looks**; a human still owns that.

**Last updated:** 2026-08-14 (**Session 39 — one reported BUG root-caused and fixed, two requested
features built, one duplicate form removed. 931 → 1005 tests pass, 2 skipped, 0 failures.** New ADR
**0064** (a–o, ten rejections). **Alembic 0013 → 0014** — TWO columns on `patients`, no new table,
still **18 tables**. ⚠ **Two new Python dependencies (fpdf2, uharfbuzz) and one new binary asset**
(an OFL Bengali+Latin font), the first deps since S30 — the reason is recorded below and it is
Bangla, not PDF features.
⚠ **NO MODULE CHANGED STATUS.** The work lands inside **M13 (EHR Database)** and **M14 (Doctor
Dashboard)** plus the medic side of the same staff layer, all already ✅. **M15 stays 🟨.**
⚠ **S39 touched NO voice code and no kiosk file**, so the real-mic status is unchanged.

**THE REPORTED BUG — a patient name appeared for a visit in which none was given.** The root cause
was **not invention**, and that changed the whole shape of the fix: `patients` is keyed by **phone
number**, so `display_name` is patient-scoped and **permanent**, and a name recorded during one visit
is inherited by every later visit on that number. Reproduced from the dev DB read-only: a **staff**
edit on 2026-08-13 wrote the name; the visit the next day, in which the patient said nothing about a
name, displayed it. Keeping the name is right — a returning patient is the same person. Presenting it
as though it had been established *in the case on screen* is not.
So the name now carries its **origin**, derived from `audit_log` with **no new column**
(`services/identity`), and the AI auto-fill — which previously wrote a name into a permanent medical
record and **left no trace at all** — now writes its own audit row with `actor_id = NULL`.
⚠ A staff edit records no visit, but it records **when**, and a name written **before this visit
began provably did not come from it**; that case is reported rather than left silent. One made
*during* the visit stays "we cannot tell", because it could have come from the patient in the room.
A name written before S39 has no audit row and reports **`unknown`**, never a guess.
`display_name` was also **removed from `POST /api/patients/lookup`** — the third writer of the field,
the only unaudited one, and no client ever sent it.

**BLOOD SUGAR — what was missing was the FIELD, not a permission.** S38 shipped the glucose reference
*chart* and nowhere to write a *reading*, so "the medic cannot edit sugar" was literally true.
Editing before referral already worked (S37 moved vitals into the case workspace), so the requirement
was met by adding the value — and tests now pin that a medic edits pre-referral, that the referral
still works afterwards, and that an unauthorised actor still gets a 403.
⚠ **The reading and its measurement context are ONE fact and are refused apart**, server-side and
before the write: a fasting 6.5 and a random 6.5 are different findings. The context is constrained
in the **database** as well as the schema.
⚠ **No band, class or interpretation is stored or computed anywhere** — the value is reported, the
published chart is shown beside it, and a clinician reads one against the other. This is ADR-0060's
`glucose_reference()`-takes-no-argument rule, now that a value exists to be tempted with.
⚠ **HbA1c is deliberately not recordable**: a percentage, not mmol/L, and a laboratory result rather
than a bedside reading, so one column never holds two quantities.

**THE EHR PDF — a second RENDERING, not a second record.** `services/ehr_pdf` **does not read the
database**: it is a pure function of the dict `ehr_export.build_fhir_bundle()` already returns, and
it typesets that bundle's own section narratives — which is what a FHIR document Bundle *is*. The PDF
therefore cannot hold a fact the JSON lacks or omit a section it has; a test forbids `db.query` and
`db.get` anywhere in the module.
⚠ **The dependency choice was made by BANGLA.** Bengali needs conjunct formation and vowel-sign
reordering; a library that lays out one glyph per codepoint prints the patient's own words wrongly,
which is a **rule #1 defect in the one export a human actually reads**. ReportLab cannot shape
Bengali; fpdf2 delegates to HarfBuzz. The font ships **in the repo** (OFL-1.1) because Windows'
Nirmala is not redistributable and a clean Arch box may have no Bengali font at all. The renderer
**REFUSES** rather than emitting a document whose Bangla would be wrong.
⚠ And the trap that cost a real defect: **a missing glyph does not raise — it VANISHES.** `kg/m²`
printed as `kg/m`, a different unit. A test now walks every character the renderer will draw against
the font's cmap.

**SHARED, NOT COPIED.** S39 put a blood-sugar value on the doctor's screen and the reference chart
existed only in the medic portal — a number with no chart where it is interpreted. The chart **moved**
to `frontend_shared/staff.js`; both portals mount the same one, nothing was duplicated. ⚠ The
doctor's row is **read-only**: intake is the medic's to own (`portal_roles` §5).

**REDUNDANCY AUDIT — one real duplicate removed.** The medic's post-referral screen had its own
identity editor AND weight editor, writing the same `patients` row through the same PATCH as the
Intake & Vitals form but covering **fewer fields** — a leftover from before S37 moved editing ahead
of the referral. Both are gone; the screen is a read-only snapshot that says where editing happens.

⚠ **What was NOT verified this session:** no browser rendered the new portal DOM (the Browser pane
restricts localhost to the `launch.json` port, which was occupied by a server this session did not
start and did not stop). The portal changes are covered by static-source assertions and by a 34-check
HTTP walkthrough against a real server on a throwaway seeded DB; **how they look is unclaimed.** The
PDF itself *was* inspected visually in Chrome and its Bengali shaping is correct.

**Last updated:** 2026-08-14 (**Session 38 — the staff-portal UX + clinical-workflow brief is
COMPLETE: all nineteen requested items (A1-A7, B1-B7, C1-C4). 767 → 931 tests pass, 2 skipped, 0
failures.** New ADRs **0060** (the derived/stored boundary + the four workflow features), **0061**
(the date policy), **0062** (the FHIR EHR export) and **0063** (the M16 widening).
**Alembic 0012 → 0013** — the first schema change since S25, and deliberately minimal: **ONE column
(`patients.height_cm`) and ONE table (`clinical_notes`)**, each with its rejected alternatives
recorded before it was written. **18 tables. No new Python dependency.**
⚠ **NO MODULE CHANGED STATUS.** The work lands inside **M14 (Doctor Dashboard)**, the medic side of
the same staff layer (both already ✅) and **M16** (the doctor-side assistant). **M15 stays 🟨.**

**The governing rule of the session: most of it added no storage at all.** The medic's referral
history, the FHIR bundle, the queue's completeness detail, the BMI and the entire clinical-reference
layer are all DERIVED — different QUESTIONS asked of rows that already exist, exactly as in S37.

**MEDIC (A1-A7).** "Triage" is explained where the word is used (a one-click disclosure, not a
tutorial). The **10/10 line became a control**: ten segments instead of one bar, verified drawn
differently from merely filled, keyboard-reachable, and clicking it names which fields are still
empty from the server's own `fields_empty`. **Intake & Vitals was rebuilt into a working form** —
labelled fields, prefilled with what is stored, a button that says *Edit* once anything exists, and
it survives a language toggle mid-edit; height joins weight and BP and **BMI computes live**, under
BOTH the WHO international and the WHO **Asian** action points (a BMI of 24 is "normal"
internationally and "increased risk" for this population).
⚠ **A real defect found: the queue's auto-refresh was destroying the medic's own work.** It ran
every 15 s and `searchPhone()` renders into the same list, so a phone lookup was silently replaced
by the full queue fifteen seconds later. The timer is now shared, **holds** while a search result or
another list is on screen, holds while the tab is hidden, refreshes once on return, says which state
it is in, and no longer re-runs the entrance stagger on a background refresh.
⚠ **A6 — the human asked for "a diabetic limit"; there isn't one.** `glucose_reference()` takes **no
argument at all**: it returns the published chart (fasting / 2-h OGTT / random / HbA1c), each row
with the sample conditions that make its numbers mean anything, both mmol/L and mg/dL, the WHO-vs-ADA
disagreement stated out loud, and a source per row. A function that mapped a reading to a band is one
refactor from printing a finding beside a patient's name (rule #2).

**DOCTOR (B1-B7).** The prescription form **moved inline to the bottom of the case** instead of
replacing it. Advice/Lifestyle and Required Tests became **two vertical cards**. **Required Tests is
now a token editor** over a ~50-entry bilingual vocabulary (a Python module, not a table): search,
click to add, type anything not listed, remove any chip — and **Enter always commits what was
TYPED**, never the highlighted suggestion. "Assigned (0)" no longer shows "Select a patient" over an
empty queue.
**B1 — "Accept & Write to EHR" now produces an actual EHR record:** an **HL7 FHIR R4 document
Bundle** (Composition first, Patient, Encounter, Organization, Practitioner, LOINC-coded vital-sign
Observations with UCUM units, RiskAssessment, and MedicationRequest/ServiceRequest/Condition once a
prescription exists), served as `application/fhir+json` through the EXISTING `documents` table and
route. ⚠ Claimed honestly: **structurally valid and semantically conservative — not certified, not
profiled**, and a receiver must still map it. ⚠ **The AI suggested condition is excluded entirely**
(its disclaimer does not survive ingestion elsewhere); the doctor's own typed diagnosis IS exported.
⚠ `critical` is never silently downgraded.
**B5 — the date policy, by CATEGORY:** historical timestamps are **never touched**, a prescription
must be dated **today**, a follow-up/recall must **not be in the past** — enforced server-side and
BEFORE the write. ⚠ It fixed a real bug: the form stamped `toISOString()`, the **UTC** date, so a
prescription written between midnight and 6 a.m. Dhaka was dated the previous day.

**A7 — one clock, and it is Bangladesh's.** A live 12-hour header clock in both portals, and every
stored timestamp re-rendered 12-hour. ⚠ Server-side "today" uses a **fixed UTC+06:00 offset, not
`ZoneInfo`**: Windows ships no IANA tz database. Bangladesh has had no DST since 2010, so the fixed
offset is exact rather than approximate.

**B6 — M16 widened, with privacy enforced structurally.** One service, one seam, one round-trip, now
covering medicines, diagnostic tests, and — on **explicit opt-in** — which tests might suit this
patient. ⚠ **The web search receives the doctor's typed question and nothing else, by signature**;
the LLM's case context is de-identified and carries **no name, no phone and no raw transcript**.
Suggested tests are chips the doctor **clicks** to insert — nothing is ordered until a human
generates the prescription. A **new** output guard catches patient-directed instructions and
deliberately does **not** reuse M7's dosage rule, because here a dosage range is the correct answer.

**C1-C4 — the four features S37 deferred, all built.** Referral history **derived from
`audit_log.actor_id`** (which S37 added), and it **reports what it cannot attribute** rather than
inventing an owner. Per-field verification inside the existing `summary_fields` JSON, so a medic can
record "I read this and it is correct" **without editing the field** — previously the only way, and
it put a false edit in a medical record. Recall + doctor→medic back-channel on **one**
`clinical_notes` table, addressed to a **role** not a person, with no thread, reply or read receipts.

⚠ **Real-microphone status is UNCHANGED by S38** — it touched no voice code. The S37 record stands:
the human confirmed the S33-S36 real-mic run **was carried out**, **no per-claim results were
supplied and none are documented**, and no defects came back. S25's itemised evidence stands.
⚠ **S38's frontend tests are static-source assertions** (the S28 no-JS-runner decision): they prove
wiring and containment, not appearance. Everything visual was checked by hand in a browser this
session against a **throwaway** seeded DB (rule #4 — the dev DB was not modified).

Prior: 2026-08-13 (**Session 37 — the two STAFF portals were audited as ROLES; 723 → 767 tests, ADRs 0058/0059, Alembic stayed 0012.**)
Prior: 2026-08-13 (**Session 36 — the post-S35 hardening cycle is CLOSED; all seven items
shipped in one pass. 622 → 723 tests pass, 2 skipped, 0 failures.** New ADR **0057**. **Alembic stays
0012 — no schema change, no migration, no new dependency.**
⚠ **NO MODULE CHANGED STATUS.** Refinements inside modules already ✅ (M1 speech input, M7 follow-up,
M12 report export, M13 storage, M14 presentation) plus four bug fixes. **M15 stays 🟨.**
**The reported "alignment breaks at the final question" was the GRID, not the dock (Finding 1).**
Reproduced and MEASURED before anything was touched: `setResumeMode()` hides `#summary-float`, and a
hidden grid item stops being PLACED while its TRACK stays exactly where it was — auto-placement then
dropped the summary cards into the narrow first column, **471px → 170px with a 231px card inside
it**, so every card overflowed its own column and the review jumped 188px left. One CSS rule
(`.summary-body.no-float`) keyed to the same condition that hides the float, at (0,2,0) so it beats
both responsive overrides regardless of source order. Verified reversible.
**The patient SESSION is now a real boundary (Finding 2) — this is the largest change and it is a
privacy one.** `resetState()` looked like a reset and was not: the recognition ENGINE was still
running (`r.onend` restarts it, so a patient still talking had their voice transcribed into the NEXT
patient's phone dock), `finalBuffer` still held their words, the review read-through kept reading
their answers aloud, the phone ticker was never cancelled, and their summary cards stayed in the DOM.
⚠ **The dangerous one was none of those: every in-flight `api()` promise wrote into the new
session**, because `state` is a module-level variable resetState() REPLACES. Worst case `verifyOtp()`
— a late response installed the previous patient's `visit.uuid` into the new patient's session, so
the new patient's answers would have been POSTed onto the old patient's visit. Clearing variables
cannot stop a promise that has already resolved, so the fix is an EPOCH (`sessionToken()`), the same
shape as S3's `armToken`. NEW `endSession()` / `startNewSession()`; eight async paths check before
writing.
**MCP was evaluated and REJECTED, with the reasons recorded (Finding 3, ADR-0057 b).** No
tool-calling loop exists to attach it to (`call_module()` is one-shot); the round-trips are the
scarce resource (ADR-0026, and M7 sits in the LIVE loop); a second context path would rebuild the
disagreement S35 removed; and session scoping here is STRUCTURAL — a function not given visit B
cannot return visit B — which a transport would weaken. The three responsibilities are in-process
functions in NEW `services/question_tools.py`. **Two real gaps found while evaluating were closed:**
the conversation handed to M7 was the ENTIRE unbounded history (now the most recent 24 turns; a
normal ~18-turn visit is never truncated), and M7's question was only ever ASKED not to prescribe —
it is now CHECKED on the way out, with a deterministic server-authored fallback.
⚠ **That output guard is HIGH-PRECISION / LOW-RECALL and is NOT a medical-safety classifier.** It
catches dosage amounts and explicit prescribing/diagnosing phrases and deliberately does NOT ban
"ওষুধ" / "medicine" / "diagnosis" — asking ABOUT those is M7's job. Rule #2 rests on the whole
design, not on that function.
**A complete phone number now ends its own turn (Finding 4)** — eleven digits are knowable the
instant they arrive, and waiting for silence let trailing speech join the same utterance, so a
repeated digit pushed the count past eleven and a correct number came back as "not understood".
⚠ The read-back is NOT skipped (ADR-0053 stands; S35 already made it button-free).
**"ঠিক আছে" / "all right" now finishes the review (Finding 5).** Measured first: `সব ঠিক আছে`,
`সবকিছু ঠিক আছে`, `সব ঠিক`, `all right`, `alright` and the "that is all" family ALL returned null,
so the most natural way to say "everything is fine" was read back as a symptom and stored as a
correction — a loop the patient could not leave by speaking. Reuses `parseConfirmation()`.
**The raw transcript downloads itself at completion (Finding 6)**, once, unawaited, silent on
failure, and DROPPED if the kiosk was handed over mid-render; filename now
`raw-transcript-visit-<8>-<date>.docx`, carrying no name and no phone number.
**Two usability gaps closed (Finding 7)** after confirming the other eight ideas were already
solved: the completion is now SPOKEN (it was text-only on a kiosk where every question is spoken),
and the conversation screen shows `Question N of 4` **during the scripted opening only** — the M7
loop ends on completeness, and an invented denominator would lie.
**Four defects created and caught during the loop, plus one caught by an existing test:** a
docstring terminator lost in a rewrite and a JS comment pasted into Python (both caught by a syntax
check before any test ran); apostrophes in my own comments inside the `CONFIRM_*` literals, which
`shipped_set()` parses as vocabulary — **caught by the pre-existing
`test_the_two_vocabularies_do_not_overlap`**, exactly what it exists for; and an incomplete
`startNewSession()` that cleared all patient DATA but left the previous patient's screen showing.
⛔ **Step S5 was NOT implemented** — `no_speech_ms` watchdog, `max_answer_ms` cap and
permission/visibility recovery are all still untouched, verified by inspection and now pinned by a
test. Its permission/visibility half is **BLOCKED**, not merely pending: it cannot be built without
deciding what happens to a half-captured answer in `finalBuffer`, which is the open rule #1 decision
reserved for the human.
⚠ **On the microphone, corrected because S33-S35 overstated it:** real-mic STT/TTS **is proven** for
the S25-era flow (S25's human live run passed on Windows 11 + Chrome + a real mic). What no
microphone has ever exercised is the voice behaviour added since — **S33-S36**. Do not repeat "no
microphone has ever been used"; it is false. Do not call the new behaviour validated either.
Prior: 2026-08-12 (**Session 35 — the SECOND manual-testing cycle is closed; all 8
findings shipped in one pass. 547 → 622 tests pass, 2 skipped, 0 failures.** New ADR **0056**
(supersedes ADR-0055's "Rejected (1)", amends ADR-0053). **Alembic stays 0012 — no schema change,
no migration, no new dependency.**
⚠ **NO MODULE CHANGED STATUS.** Refinements inside modules already ✅ (M1 speech input, M7 follow-up,
M13 storage, M14 presentation) plus three bug fixes. **M15 stays 🟨.**
**⚠ One correction to the brief, recorded because it matters:** the finding said the phone read-back
"currently auto-accepts after ~10 seconds". **It did not** — there was no timer on that panel at
all; ADR-0053 deliberately required a tap. Verified by inspection before anything changed. The
10-second window is therefore NEW behaviour, and the safety property ADR-0053 actually protected —
that the patient can SEE and HEAR the number before it goes — is untouched.
**Confirmation is now SPOKEN, everywhere (Findings 2 + 7).** ONE vocabulary and ONE parser serve the
per-answer read-back and the final review. Two rules make it safe: an utterance is a verdict only
when EVERY word in it is known, and where a YES word and a negation both appear NO wins — so
`ঠিক আছে`→yes, `ঠিক নাই`/`আবার বলি`→no, and `আমার নাম রহিম না মানে রহিমা`→**ambiguous, ask again**.
A verdict is routed before the clinical branches and is NEVER stored. Rejecting the review re-opens
the EXISTING KIOSK-7 resume dock with an open correction question — no second pipeline. Buttons
remain as the accessibility fallback.
**ONE clock, in the portal header (Findings 1 + 8).** S34's clock lived inside the review layout, so
it existed only on that screen and only while it was scrolled to the top. The header sits OUTSIDE
`.screen` (the element that scrolls since ADR-0055 i), so it is top-right at all times, cannot be
scrolled away from, and cannot overlap — it is a flex item and the row reserves its width. Both
countdowns write it through one renderer with a per-countdown label. Measured consequence, and the
answer to Finding 5's "first render jumps": **the clock appearing now shifts the review heading,
title and grid by 0 pixels.**
**Questions follow what is already collected (Finding 4).** `collected_context()` is the exact mirror
of `missing_summary_fields()` (same keys, same `field_has_text`), plus prompt clauses forbidding
re-asking anything in it or in PATIENT CONTEXT and asking for CLARIFICATION when something is vague.
⚠ Deliberately NOT a decision system: it ranks nothing, names no condition, and does not choose the
next field — the M6 gap list and the server-named field (ADR-0052) still own that. **Whether the
model OBEYS is Tier 3 and is NOT claimed** (the ADR-0054 f rule).
**TTS pacing, not a new TTS (Finding 6).** NEW `services/tts/prosody.py`: a sentence-final `।`/`.`
and real commas where the text already implies a pause, applied ONCE in the service so the primary
and the fallback read the identical line. ⚠ It may never change a WORD — the read-back sends the
patient's own captured words down this path. Pitch/volume exposed but NEUTRAL.
⚠ **ACOUSTIC QUALITY IS NOT TESTED AND NOT CLAIMED** — whether it sounds more natural is a human
listening judgement.
**Three defects found on the way, two by reasoning through the wiring and one by measurement:**
S34's `hideAnswerConfirm()` in `toggleListening()` would have cleared the pending answer between the
mic opening for the verdict and the word "হ্যাঁ" arriving (storing the verdict as the symptom);
`setResumeMode()` cancelled the very microphone the new review approval had just armed; and at 375px
the clock landed at the LEFT of the wrapped header row because the right-hand group exactly fills the
line (320px of 319px available), so `margin-left:auto` had no free space.
⚠ **STILL NO MICROPHONE, in any session** — and the stakes rose: **every answer and the final submit
now pass through a spoken yes/no**, so what a real `bn-BD` recogniser returns for "হ্যাঁ" is the
single most load-bearing unproven claim in the build.
⛔ **Step S5 was NOT implemented** — `no_speech_ms` watchdog, `max_answer_ms` cap and
permission/visibility recovery are all untouched. ADR-0056 also corrects ADR-0055 in passing: a
spoken yes/no is **not** S5 content.
Prior: 2026-08-12 (**Session 34 — the manual-testing cycle the human reported is
CLOSED; all twelve phases shipped in one pass. 480 → 547 tests pass, 2 skipped, 0 failures.**
New ADR **0055**. **Alembic stays 0012 — no schema change, no migration, no new dependency.**
⚠ **NO MODULE CHANGED STATUS.** Everything here is a refinement inside modules already ✅
(M1 speech input, M7 follow-up, M13 storage, M14 presentation) plus three bug fixes — not new
modules. **M15 stays 🟨.**
**Phase 1 (the reported "one two…" defect):** the kiosk listens at `lang='bn-BD'`, and a
Bangla-language recogniser handed spoken English digits returns the TRANSLITERATION
(`ওয়ান টু থ্রি`), not Latin text — so the ten English keys in `SPOKEN_DIGITS` could never be hit
by a patient SPEAKING English digits. Ten transliterations added (`ও` deliberately excluded: it is
one of the commonest words in Bangla and would invent zeros out of ordinary speech). Plus a live
**digit preview** (`0 1 7 1 5`) beside the transcript, derived by the same `digitsFromSpeech()`
that produces the value — the transcript keeps showing the words, because that is the evidence and
it is never rewritten (rule #1).
**Phase 2 (the real gap):** between S4 and this session a spoken answer went from the recogniser
straight into the permanent record with **no human confirmation anywhere in the path**. Now every
SPOKEN clinical answer is shown large and verbatim, SPOKEN back (`bn-BD`, `verbatim`), and held
until the patient taps ✔ — nothing reaches the server before that, and ✖ discards a capture that
was never stored and re-asks the SAME question. ONE gate, in `stopListening()`'s spoken branch;
`acceptAnswer()` re-enters the SAME `submitPatientTurn`/`submitResumeAnswer` calls, so ADR-0048's
one-pipeline rule is intact and TYPED answers are never gated. An unusable capture (no letter, no
digit) is **never guessed at** — silence and noise both re-ask. Switchable off via
`VOICE_ANSWER_CONFIRM=false`; the re-ask half is not.
**Phases 3-5 (review + motion):** every filled summary card can be HEARD (labelled 🔊, plus a
"Hear my answers" read-through on one queue token); the P1 robotic doctor gains a THIRD mount as a
floating assistant on the review screen — same DERIVED state machine (ADR-0054), stepping aside
when the resume dock's own avatar opens; and the conversation auto-scrolls the THREAD (never
`scrollIntoView()`, which moves the whole document out from under the patient).
**Phases 6-7 (the clock):** a 60-second digital countdown top-right of the review heading, blinking,
`urgent` under 10 s, bilingual (`60s left` / `৬০ সেকেন্ড বাকি`). It runs ONLY while Confirm &
Submit is genuinely pressable, is idempotent against re-entry, and `confirmSubmit()` gained a
`submitting` guard — **verified live: the timeout racing two manual taps produced exactly ONE
POST.** `startTicker()` is extracted and the auto-logout countdown moved onto it; **the S4
endpointer is deliberately NOT converted** — its deadline restart is the rule #1 anti-clipping
guarantee, not a UI detail.
**Three defects found by MEASURING the running page, not by any assertion:** the confirm panel
opened below the fold; underneath it, a **PRE-EXISTING** unbounded page (`body` had `min-height:
100vh` and no height → 1538px of document in a 694px viewport, `.chat-thread` never scrolling, the
whole voice dock under the fold); and a **PRE-EXISTING** sideways overflow at 375px from an inline
`grid-column: span 2` creating an implicit second column (497px of content in a 375px viewport).
All three fixed, scoped to `kiosk.html`.
⚠ **STILL NO MICROPHONE, in any session.** Every voice result on record comes from feeding the
recogniser's own buffer in a browser engine. **The Bangla transliterations are REASONED, NOT
OBSERVED** — what Chrome's `bn-BD` recogniser really returns for spoken English digits remains the
single most disprovable claim in the build.
⛔ **Step S5 was NOT implemented** (by explicit instruction): its `no_speech_ms` watchdog,
`max_answer_ms` cap and permission/visibility recovery are untouched. Only the narrow empty-capture
re-ask required by Phase 2 was built — ADR-0055 (e) records the overlap.
Prior: 2026-08-11 (**Session 33 — ALL IN-SCOPE FACULTY-DEMO DEVELOPMENT IS COMPLETE.**
Shipped **F5** (voice phone number + voice OTP), **P1** the robotic doctor/avatar, **P2** the
elderly-friendly / selective-3D UI, and **P3** age-appropriate conversation validation.
**392 → 480 tests pass, 2 skipped, 0 failures.** New ADRs **0053** (F5) and **0054** (P1/P2/P3).
**Alembic stays 0012 — no schema change.**
⚠ **NO MODULE CHANGED STATUS.** These are refinements inside modules already ✅ (M1 STT input,
M7 follow-up, M13 storage, M14 presentation) plus bug fixes — not new modules. **M15 stays 🟨.**
**F5:** ONE cross-language digit contract (`to_ascii_digits()` server-side; `digitsFromSpeech()` /
`phoneFromSpeech()` kiosk-side) — Python's Unicode-aware `\D` had KEPT Bangla digits and then failed
the ASCII checks (400), while JS's ASCII-only `\D` had SILENTLY DELETED them. Identification reuses
the ONE recognizer as two more `DOCKS` entries + `state.identifyStep` + two branches at the single
routing point in `stopListening()` — **no second pipeline**, the human's explicit regression rule.
A spoken phone number is READ BACK and requires a confirmation tap; a spoken OTP reuses F1's
`maybeAutoVerify()` untouched. Phone screen is tap-to-start (no user gesture exists at first paint);
auto-listen resumes from the OTP screen on.
**P1 (robotic doctor):** CSS-only 3D, no library/WebGL/asset (CPU-only hardware, offline kiosk).
Five states **DERIVED** from real signals — never pushed — with the precedence
**listening > speaking > processing > idle**; only `done`/`error` may be pushed and `error` expires
with its banner. Present in BOTH the conversation and resume docks, bilingual, `aria-live`, and
`prefers-reduced-motion` keeps the meaning.
**P2 (elderly / 3D UI):** scoped to `kiosk.html` so the medic and doctor dashboards are untouched —
52px buttons, 54px inputs, 60px OTP boxes, 1.12rem chat, visible focus rings, and two SEPARATE
responsive axes (`max-height: 820px` for the fold, `max-width: 620px` for overflow). Measured at
1280x900 / 1280x720 / 1024x600 / 375x812: no horizontal overflow, primary action always visible,
**zero controls under the 44px touch minimum**.
**P3 (age validation):** proven in **three explicit tiers** — Tier 1 deterministic code (age
computed, reaching M7 verbatim, confined to PATIENT CONTEXT, implausible ages rejected, the 10-field
shape and the requirements gate identical for a 19- and a 78-year-old) and Tier 2 prompt content
(directional age instructions, no diagnosis, no reciting the age back). ⚠ **Tier 3 — that the MODEL
obeys — is explicitly NOT claimed**; an opt-in `M7_LIVE=1` probe replaces a fake green test.
⚠ **NO MICROPHONE WAS USED ANYWHERE IN THIS SESSION** — the Browser pane blocks capture, so all
voice results come from feeding the recogniser's own buffer. **What Chrome's `bn-BD` recogniser
returns for spoken digits is still UNPROVEN and is the entire next session.** Screenshots were also
unavailable (pane not compositing), so the UI evidence is measured geometry, not visual inspection.
✅ **One live end-to-end run did happen (no mic):** spoken Bangla-word phone → read-back → confirm →
spoken Bangla-word OTP → verified → area/name/age/complaint → a REAL M7 question
(*"ব্যথার তীব্রতা কত? (How severe is the pain?)"*, on-topic and non-diagnostic) for an extracted
**age 78** → 10-card summary with F3's gate correctly withholding Submit → all 12 turns byte-exact
and in order.
Prior: 2026-08-11 (**Session 32 — the FACULTY-DEMO feature cycle opened; F1–F4 + F6 shipped,
F5 NOT started.** The human gave an 8-part feature list and approved a P0 plan **F1→F2→F3→F4→F5→F6**.
**⚠ NO MODULE CHANGED STATUS and the faculty-demo voice flow is NOT complete** — these are refinements
inside modules already ✅ (M7 follow-up, M9 completion, M13 storage) plus one bug fix, not new modules.
Shipped: **F1** OTP entry (`frontend/kiosk.js` — Enter on the OTP boxes AND the phone field, which had
**no Enter handler at all**; auto-verify at 6 digits from both the typed and pasted paths; a rejected
code now clears and re-asks; an `otpVerifying` guard because ADR-0045 codes are SINGLE-USE and a double
submit would burn the patient's own valid code). **F2** the question/answer mismatch (`followup.py` —
the resume scope used to "repair" M7's `target_gap` to `remaining[0]`, filing a question against a
DIFFERENT field, so the asked field stayed unasked and an unasked field was marked answered; the SERVER
now names the field and records that same field, salvage path included; **the MAIN loop is deliberately
unchanged**). **F3** required-info enforcement (NEW `services/requirements.py` = the ONE definition,
with the two-kinds split MUST_HAVE_VALUE vs MUST_HAVE_BEEN_ASKED so "no allergies" can satisfy a
requirement; NEW `GET /api/visits/{uuid}/readiness`; `submit?require_complete=true`; and
`followup_resume_max_questions = 8` giving the resume loop its OWN budget — it shared the main cap of 5,
which the main loop spent entirely, and THAT is why review pages arrived with empty required fields).
**F4** area → name → age → description as an `INTAKE_SCRIPT` of ORDINARY recorded turns through the SAME
endpoint (no second pipeline); `problem_area` added to M3/M8 and `entities` now MERGED instead of
replaced (it was silently wiping `suggested_condition`); `patient_context()` hands M7 age + sex + area
and `_QUESTION_SYSTEM` demands AGE-APPROPRIATE questions. **F6** conversation-preservation regression
tests — **tests only, no production code**: requirement 8 was ALREADY satisfied, so this converts "true
today" into "cannot silently stop being true". **324 → 392 tests pass, 1 skipped.** New ADR **0052**
(identity stays OUTSIDE the 10 fields; two kinds of requirement; server-side gate; `require_complete`
opt-in; resume budget; server names the resume field). **Alembic stays 0012 — no schema change.**
⚠ **NOT DONE and explicitly deferred by the human:** **F5 voice phone-number entry and voice OTP**
(their requirements 1 and 2 — so the specified demo flow is NOT yet achievable), **P1 robotic
doctor/avatar**, **P1/P2 elderly-friendly + 3D UI**, **real human Bangla voice-DIGIT validation**, and
**full voice-first faculty-demo validation**. ⚠ **NO VOICE PATH WAS VERIFIED this session** — the
Browser pane blocks mic capture, so every voice claim still rests on the human's live run; what WAS
live-verified needs no mic (the OTP keyboard/auto-submit/clear cycle, and the scripted opening
sequencing area → name → age → description with every turn stored in order). ⚠ **The F4 prompt changes
are UNPROVEN** — tests prove the age/area context REACHES M7, not that the model obeys it.
Prior: 2026-08-09 (**Session 31 — the ONE real defect S30 found is now FIXED and CLOSED.**
`frontend/kiosk.js` only, ONE handler: `r.onerror` looks up a **`TERMINAL_STT_ERRORS`** map
(`not-allowed`, `audio-capture`, `network`, `service-not-allowed`, **`language-not-supported`**) →
message + `stopListening(false)` + `setInputMode('type')`. That flips `listening` to false, which is what
ends the **`start → error → end → start`** loop. ⚠ **`no-speech`, `aborted` and `bad-grammar` are
deliberately ABSENT and must stay absent** — their restart via `onend` IS what keeps continuous listening
alive in Chrome (part of the passed S29 run), so a blanket "stop on any error" would regress Chrome and
clip patients mid-answer. **`r.onend` is untouched and test-pinned.** **318 → 324 tests pass, 1 skipped**
(new `test_kiosk_stt_errors.py`, which extracts the shipped map out of the served JS and compares the key
set; **no existing test touched or weakened**). **Live-verified in a real browser engine with no mic and
no permission prompt** — transient codes kept `listening` true, all four terminal codes broke the loop and
switched the patient to typing with the right bilingual banner. **No new ADR, on purpose:** this
*implements* ADR-0048's existing "a patient is never blocked by a failed mic" requirement rather than
deciding anything new. ⚠ **Still UNPROVEN and unchanged:** whether Edge's backend actually transcribes
`bn-BD`. This makes a rejection **visible and recoverable**; it does not prove which failure occurs.
🔴 **One rule #1 decision now WAITS FOR THE HUMAN:** `stopListening(false)` (`kiosk.js:576`) discards
`finalBuffer`, so a terminal error landing **mid-turn** (a wifi blip → `network`) throws away words the
patient already spoke. Pre-existing, but S31 widened the set of codes that reach it; deciding the fate of
a half-spoken answer is not a drive-by change. **The human end-to-end test STILL has not happened** —
nobody has heard TTS-1/TTS-2 or run STT in Edge. **No module status and no phase changed; Alembic stays
0012; S5–S7 still NOT built.** The tree is now entering a **faculty-demo feature cycle**: the human
opened a feature-planning workflow but **has not yet given the features** — nothing is to be assumed.
Prior: **Session 30, closed after an EDGE COMPATIBILITY VERIFICATION —
INSPECTION ONLY, no code changed.** The human will demo in **Microsoft Edge**, so browser support was
checked before the live test. **Real Edge 151.0.4129.72** was probed (Claude's own browser is
Electron/Chromium 148, so a separate read-only probe page was used; it never called `start()` or
`getUserMedia()`, so it covers everything **except audio**). **Verified TRUE:** the STT is the browser's
**native Web Speech API** (`kiosk.js:464`, no library/no server STT); Edge exposes **both**
`SpeechRecognition` and `webkitSpeechRecognition`; a recognizer **constructed** and **accepted**
`lang='bn-BD'`, `continuous`, `interimResults`; mic permission is **`"prompt"`**, not blocked;
`canPlayType('audio/mpeg')` = `"probably"`; **no Chrome-only APIs** in the STT path. ⚠ **API surface
verified ≠ actual Bangla STT service verified — nothing here claims Edge STT works end-to-end**; whether
Edge's backend transcribes `bn-BD` is **UNPROVEN** and needs a human at a real mic. **Key finding: Edge
has NO Bengali browser TTS voice** (26 voices, 21 languages, `bnVoices: []`), which **disproves
ADR-0050's option 3** and confirms the design — in Edge the chain falls to provider 2, so the
**server-side TTS-2 `edge-tts` path remains the Bangla route**, same as Chrome. **ONE REAL DEFECT FOUND
AND DELIBERATELY NOT FIXED:** `kiosk.js:499` handles only 2 of 8 Web Speech error codes, so
`language-not-supported` (exactly what Edge emits if it rejects `bn-BD`), `network` and
`service-not-allowed` leave `listening === true` and `kiosk.js:491` restarts forever —
**`start → error → end → start`**, with no error shown, no switch to typing and no countdown (S5, which
would catch it, is not built). The minimal fix (split terminal vs transient errors; `no-speech`/`aborted`
**must** keep restarting or Chrome regresses) is **PROPOSED, NOT IMPLEMENTED** — it is the recommended
next step. **`FLUSH_GRACE_MS = 600` on Edge is recorded as UNVERIFIED, not as a bug.** ⚠ **The human
end-to-end test has still NOT happened** — nobody has heard TTS-1 or TTS-2, and nobody has run STT in
Edge. **No module status and no phase changed; Alembic stays 0012; 318 tests / 1 skipped unchanged.**
Earlier the same session — **BOTH 3.0 items are now SHIPPED: TTS-1 (ADR-0051) and
TTS-2 (ADR-0050, moved Proposed → ACCEPTED).** TTS-2 replaced the robotic espeak-ng default with
**edge-tts**, Microsoft's neural `bn-BD` voice. **The ADR-0049 seam held exactly as designed** — one
`TtsProvider` subclass (`services/tts/edge.py`) + one registry entry + `.env` settings, with **no route,
frontend, schema or Alembic change**, and MP3-instead-of-WAV needed nothing extra because the ABC already
carries `media_type` per provider. **The inspection overturned a documented "fact":** edge-tts is
**LGPL-3.0** (no copyleft on our code, no non-commercial clause), while `facebook/mms-tts-ben` is
**CC-BY-NC-4.0** — so the option previously described as the safe local choice is the more restrictive
one on licensing. ⚠ **The rule #4 cost was accepted explicitly by the human:** M7 questions are derived
from patient speech and now go to Microsoft; what tipped it is that the Web Speech API already sends the
patient's *actual audio* to Google. **This limits what the thesis may claim about privacy**, and
`TTS_PROVIDER=espeak` remains the one-value private/offline escape hatch. On failure the chain falls back
to espeak-ng (a robotic question beats a silent kiosk) and still 503s — never a silent 200 — if both fail.
**297 → 318 tests pass, 1 skipped** (opt-in `TTS_LIVE=1` network test, which passed). Measured live:
`bn`/`en` both `audio/mpeg` in **~0.8 s**, playback complete at **3013 ms**, and **`ttsSpeaking()` true
throughout — S3's echo guard still holds against a NETWORK provider's latency (rule #1)**; `<audio>` was
seen requesting **only the Bangla half**, so TTS-1 and TTS-2 compose. ⚠ **Naturalness is NOT proven** —
that is the human's pending live listen, which will cover TTS-1 and TTS-2 together. **No module status
and no phase changed; Alembic stays 0012; S5–S7 still NOT built.** Prior in the same session:
**TTS-1 is FIXED and CLOSED (ADR-0051, Accepted)**, the
first item of the 3.0 cycle. The human chose **option (a): speak only the half matching the active UI
language**; option (b) — both halves with a pause — was rejected as ~1 s per question against ADR-0048's
"minimize waiting" priority. Frontend only: `spokenHalf()` + a conservative `BILINGUAL_QUESTION` regex
applied **once** inside `speak()`, and **both** providers get the split half (splitting only the browser
path would have left the defect alive on Windows, where the server route is the ONLY Bangla path —
ADR-0049). The patient's own 🔊 replay opts out via `verbatim`. **The stored `system` utterance, the
on-screen bilingual bubble and the M7 prompt are all unchanged and test-pinned** — this changed what is
SPOKEN, never what is stored or displayed. **277 → 297 tests pass, 0 skipped**; the new
`test_tts_bilingual_split.py` extracts the shipped regex literal from the served `tts.js` and RUNS it,
and Chrome's own engine was cross-checked case-for-case. Two pre-existing static assertions were updated
to the new strings with their intent kept. ⚠ **Not yet HEARD by a human** — tests prove which string
reaches each provider, not that it sounds right. **No module status and no phase changed; Alembic stays
at 0012. TTS-2 is untouched (ADR-0050 still Proposed — provider and the rule #4 privacy trade-off
undecided) and S5–S7 are still NOT built.** Prior: Session 29 — **Step S4 of 7 is DONE and its live run PASSED**:
silence detection, the visible 3-2-1 confirmation countdown in both docks, barge-in cancel on every
`onresult` tick, and a flush-before-submit so the tail Chrome had not yet finalized is not dropped
(rule #1). Then **Bangla TTS was solved architecturally — ADR-0049**: a server-side TTS provider seam
(`services/tts/`, mirroring the ADR-0045 OTP seam) + public `GET /api/tts` with **espeak-ng**, chosen
because it is already this project's accepted Bangla voice (ADR-0040) and keeps patient-derived
question text on the machine; zero new Python dependencies. **Verified root cause: Windows has NO
Bengali TTS voice at all**, so `human_live_run_guide.md` PART 1 was documenting an impossible step —
now corrected. `speak()` no longer fakes success: Bangla demands a matching voice, a missing engine is
a **503**, and `/api/config` gained a `server_tts` capability flag. Three bugs were found and fixed en
route (an echo-guard hole from `<audio>` being invisible to `speechSynthesis.speaking`; English TTS
broken by the async `getVoices()` race; and stale cached `shared.js`, now `no-cache`). **espeak-ng
1.52.0 was then installed and the pipeline verified end to end: 234 → 277 tests pass, 0 skipped** —
`/api/tts` serves a valid 3.57 s Bangla WAV, `/api/config` reports `server_tts: true`, the KIOSK-2
banner is hidden while `banglaVoiceAvailable()` is still false (so the fallback is what speaks),
`onend` fires at 3877 ms vs a 22 ms error path (real playback), and with the mic spied it opens
**exactly once at 4110 ms** — never while `ttsSpeaking()` is true (rule #1).
**Then the HUMAN LIVE LISTEN closed the session: the seam PASSED, the voice FAILED.** Mic timing ✅ ·
countdown ✅ · **transcript clean ✅ = zero AI words in the patient's verbatim record, so rule #1 holds
end-to-end even with a server-side TTS provider (the cycle's biggest risk, now retired)** · English ✅ ·
**Bangla voice "Too robotic" ❌ → rejected on quality (ADR-0050, Proposed: keep the seam, replace the
provider — one subclass; provider and the rule #4 privacy trade-off deliberately UNDECIDED).** One new
defect **root-caused, not guessed**: `services/followup.py:45` forces every M7 question into ONE
bilingual string `"<Bangla> (<English>)"`, so TTS speaks both halves in a single breath — heard as "two
questions, no gap". **Pre-existing since S25**, only exposed by ADR-0049. ⚠ **No module status and no
phase changed; Alembic stays at 0012. S5–S7 are NOT built.** The **"Context Fixed Problem 3.0" cycle is
now 🟢 OPEN** (empty since S24) with its first two items, **TTS-1** and **TTS-2**; no code was written
after the verdict, at the human's explicit request. Prior: Session 28 — faculty **Requirement 3 EXPANDED to §3b: a VOICE-FIRST
Patient Portal with typing always available as the fallback** (**ADR-0048, Accepted**; supersedes
ADR-0027's voice-only rule, and `CLAUDE.md` was amended accordingly). Full 7-step GO-gated plan +
12-point live checklist in `faculty_future_features.md` §A–K. **Step S1 of 7 is DONE** — backend
only, zero UX change: `voice_loop` + 4 timings in `.env`, the new public `GET /api/config`, and a
server-side non-blank `raw_text` guard. **Step S2 of 7 is DONE too** — the `[🎤 Speak] [⌨ Type]`
switch in both kiosk docks, and **Step S3 is DONE** — auto-listen: the mic opens itself after the
question is spoken, behind an echo guard, with the patient still tapping once to finish
→ **234 tests pass** (was 192). **No module status and no phase changed; Alembic stays at head
0012.** S4–S7 not built. Prior: Session 27 — docs-only: **faculty Requirement 3 filed** (fully
voice-driven follow-up loop, **ADR-0047**) in `faculty_future_features.md`, plus 5 cross-reference
fixes. **No module status and no phase changed**; 192 tests unchanged and not re-run — no code was
touched. Prior: Session 25 — **the HUMAN LIVE REAL-MIC RUN PASSED on Windows 11**:
TC-V1/V2/V3/F2/R1 all ✅ (STT very accurate, ~2 s latency, TTS spoke, follow-ups good; OTP via the
`000000` dev bypass; no bugs found). On that cleared gate the human chose to move **Modules 1–14 →
✅** (M5 retired ⛔, **M15 stays 🟨** = future retrain/regression pipeline). Docs-only, no code —
**192 tests still pass**. Caveat: the live run was qualitative (no by-hand WER/precision-recall,
Windows-only) — formal metrics remain the recommended thesis-evidence follow-up. Prior: S24 P4-1
real OTP (Alembic 0012, ADR-0045); S24b 3.0 scaffold + `faculty_future_features.md`.)
**Current phase:** ✅ **Build complete.** The 20-step plan (spec: `context_fixed_problem.md`) is
fully implemented — **every numbered spec item (STRUCT/KIOSK/MEDIC/DOCTOR) is ✅** and 150 tests
pass. What remains for the project is NOT build work: **S25 — the human live real-mic run PASSED on
Windows (TC-V1/V2/V3/F2/R1 all ✅)**, so the only open item is **rotating the 3 API keys** before a
public demo (+ optional formal WER/precision-recall as thesis evidence). **Steps 1–20 DONE:** S9 = legacy
isolation ADR-0031 · Alembic 0010 ADR-0032 · visit-grain docx seam · `fieldValue()` +
`TIER_BANDS` · bilingual values ADR-0033. S10 = kiosk OTP KIOSK-1 · per-message 🔊 +
no-bn-voice hint KIOSK-2/3. S11 = kiosk summary complete KIOSK-4/5/6/7 (resume loop ADR-0034) ·
medic bilingual/polish MEDIC-1/2/5 · risk override MEDIC-3 (ADR-0035). S12 = **C1 suggested
condition MEDIC-4 (ADR-0036:** separate M10C call, embedded disclaimer, staff-only, never the
doctor's Diagnosis**)** · **post-referral summary + fresh .docx MEDIC-6/7 (ADR-0037:** vitals
PATCH, patient embedded in visit detail, report regenerated at download**)** · doctor
bilingual/polish/↻-removal DOCTOR-1/2 (+DOCTOR-7 base). S13 = **DOCTOR-3 patient-details card**
(frontend-only: identity + editable weight/BP via the existing `PATCH /patients/{id}/vitals`,
mounted `#condition-card` for the shared C1 suggestion, C2 band in the safety panel — no backend
change) + **DOCTOR-4/5 prescription form** (step 18, ADR-0038) + **DOCTOR-6 prescription .docx +
save** (step 19, ADR-0039: `POST …/prescription` saves a `prescriptions` row + a linked
`documents` row and renders the LOCAL .docx; new prescription per Submit; Diagnosis
structurally un-AI-fillable). **S14 = step 20 (final):** 150-test gate re-confirmed; all
`context_fixed_problem` markers flipped to ✅ (KIOSK-4/5/6/7 + MEDIC-1/2/3/5 from S11,
DOCTOR-3/4/5/6/7 from S13); doc sweep. **150 tests pass.**
**Module in focus (S30):** **M7 (follow-up question presentation)** — its audio half was the whole
session's work and is now **code-complete**: one question is spoken in one language (TTS-1) in a natural
neural voice (TTS-2). What remains is **not build work** — it is the human's combined live listen. Board
status unchanged (M7 stays ✅ — the loop itself always worked; these were audio-delivery defects tracked
in the 3.0 cycle, not module regressions). Prior note: the fix/feature build is closed AND the
human live-voice gate is now CLEARED. **Modules 1–14 are ✅** (as of S25, on the passed live run); **M15 stays 🟨** (future
retrain/regression pipeline). **Next real work = the HUMAN's choice** (S26 standing note) from an
open menu: (1) rotate the 3 API keys before any public demo (`human_live_run_guide.md` PART 3,
recommended); (2) paste manual-testing bugs/UX findings into `context fixed problem 3.0.md`;
(3) faculty future features (`faculty_future_features.md`); (4) formal WER/precision-recall or the
TextBee real-SMS demo; (5) anything else. No status/phase changed in S26 (docs-only).
**Session 28 (no status change — a NEW cycle is planned but NOT started):** inspection + planning
only, no code. The human **expanded faculty Requirement 3** from "remove the mic clicks" to **"every
patient interaction after phone login must support BOTH voice and typing, switchable at will"** —
filed as **§3b** in `faculty_future_features.md` with the full plan in §A–K (**ADR-0048, Proposed**).
Findings from reading the code: voice and typing **already share one pipeline** (`source: mic|manual`,
same endpoint) so nothing needs un-duplicating — typing is merely *framed* as a failure fallback;
**no JS test infrastructure exists** (all 192 tests are pytest) so the countdown/barge-in/echo guard
**cannot be unit-tested**; `speak()`'s `onend` **may never fire** with no installed voice (would freeze
an auto-listen kiosk); the Web Speech API opens its own stream so `echoCancellation` **cannot** be set;
and `raw_text` currently has **no minimum length**. ⚠ **Requirement 3b supersedes ADR-0027's
"patient input is VOICE ONLY" clinical-input rule** — recorded in ADR-0048, but `CLAUDE.md`'s rule text
**has now been edited** (the human approved): VOICE INTERACTION RULES = **voice-first + typing always
available**. The human also answered the three blocking questions — the **3 s visible countdown IS
the silence window** (cancelled by any resumed speech), frontend tests = **static-source assertions
only** (no vitest/jsdom), and yes to the `CLAUDE.md` amendment — and set the standing priority:
**voice is the main goal and primary UX, not an optional feature**; typing exists so no patient is
ever blocked. Build order = 7 GO-gated steps. **Step S1 SHIPPED** (backend only, zero UX change):
`voice_loop` + `voice_countdown_ms/tts_guard_ms/no_speech_ms/max_answer_ms` in `core/config.py` with
a `resolved_voice_loop` normalizer, the new public **`GET /api/config`**
(`routes_config.py` + `schemas/kiosk_config.py`, secret-free by construction), and a non-blank
`raw_text` guard on `AnswerRequest` that returns the value **unchanged** (rule #1).
**Step S2 SHIPPED too** (kiosk UI, turn-taking unchanged): a bilingual **`[🎤 Speak] [⌨ Type]`**
switch in **both** docks with one shared mode, the mic hidden in Type mode, Enter-to-send, and mic
failure / unsupported browser now switching the patient **to** typing; the old "Microphone issue?
Type instead" link is gone. Voice→Type **discards** the un-submitted STT buffer (false provenance
would otherwise be stored — rule #1). **Step S3 SHIPPED as well (auto-listen):** the mic now opens
itself after a question is spoken — `askAloud()` at the 3 question sites, an **echo guard** that waits
for `speechSynthesis.speaking` to clear plus `tts_guard_ms`, a **generation token in `tts.js`** so a
cancelled question's `onend` can never open the mic during the next one (the rule #1 echo case), a
`max(3 s, len×80 ms)` safety net for machines where `onend` never fires, and `cancelPendingMic()` on
every deliberate action. `/api/config` is now consumed. **The patient still taps once to finish**;
`voice_loop=manual` reproduces S25 exactly. **192 → 234 tests pass (+19 S1, +11 S2, +12 S3)**; S2 and
S3 were also browser-verified in Chrome (S3 with an instrumented spy: one mic-open per question at
926 ms with TTS already silent; **two questions 200 ms apart → exactly one open, after the second**;
zero opens in manual mode / after a mode switch; mic still opens with `speechSynthesis` removed).
**S4–S7 (countdown, safeguards, resume-dock re-verify, live run) are NOT built** — each needs its own
"go", and S4–S6 can only be proven by the human's real-Chrome run with a mic.
**Session 27 (no status change):** docs-only. The faculty's **third** future requirement — a fully
voice-driven follow-up conversation (AI speaks → mic auto-opens → answer auto-captured → next
question, no screen contact mid-conversation) — was filed as **Requirement 3** in
`faculty_future_features.md` (**ADR-0047**: research track, client-side turn-taking, independent of
Reqs 1 & 2, no backend change for the basic loop). Notable finding: the server loop is **already
autonomous** (`POST /followup/answer` returns the next question in the same response), so faculty
steps 4–8 work today and only the two mic taps are manual. Reqs 1–3 all stay ⬜ NOT STARTED. **No
module status, no phase change; 192 tests unchanged (no code touched, not re-run).**
**Session 25 (module board moved):** the HUMAN ran the live real-mic test on **Windows 11 + Chrome +
real mic** (synthetic data, OTP `000000` dev bypass) per `human_live_run_guide.md` PART 2 —
**TC-V1/V2/V3/F2/R1 all PASS**: STT "very accurate", latency **≈ 2 s**, TTS **spoke correctly**,
follow-up questions **good**, **no bugs / UX issues**. This is the gate the 15-module board had waited
on since S8 → the human chose to flip **Modules 1–14 to ✅** (over the more conservative "M1 & M7
only" / "no change" options); M5 stays retired ⛔, M15 stays 🟨. ⚠ The run was **qualitative**
(no by-hand WER / precision-recall / labeled set) and **Windows-only** (Arch was the S16 browser-level
TTS+mic pass) — formal metrics are the recommended follow-up but were not required for the board flip.
Docs-only session; **192 tests unchanged**. Remaining: API-key rotation (human, pre-demo).
**Session 15 (no status change):** diagnosed the silent kiosk 🔊 on the Arch laptop as a
system-setup gap (`speech-dispatcher`+`espeak-ng` not installed → empty Linux `speechSynthesis`;
`tts.js` degrades correctly per ADR-0028). Added guide **PART 1B** (Arch Bangla-voice install);
no app code. Pending: human runs `sudo pacman -S speech-dispatcher espeak-ng`, then verify 🔊
speaks (TC-V2 on Arch).
**Session 24 (no module-status change):** **P4-1 real OTP (ADR-0045) — the LAST 2.0 tracker item;
the cycle (STRUCT + P1 + P2 + P3 + P4) is now fully complete.** Research first (human-requested):
no truly free SMS-OTP to any BD number exists (Twilio BD ~$0.60/SMS; WhatsApp ~$0.0113/auth msg;
Firebase phone auth Blaze-only; Telegram Gateway $0.01/code but Telegram-only; BTRC aggregators
~৳0.30–0.40/OTP = the real production route) → free real-SMS demo channel = **TextBee.dev**
(open-source Android-SIM gateway). Built: `otp_codes` (**Alembic 0012**, head 0011→0012, applied),
pluggable sender seam `services/otp/` (`OTP_CHANNEL=dev|textbee`; dev = code in the server log),
hashed single-use codes, 5-min expiry, constant-time compare, 5-attempt lockout, 60 s resend
throttle; the `000000` bypass works ONLY on the dev channel (`OTP_DEV_BYPASS`) and is structurally
impossible under textbee (tested). Kiosk UX unchanged. Bonus: fixed a pre-existing bug where
`migrations/env.py`'s `fileConfig` silenced all uvicorn logs at startup. Live-verified end to end
(log code → 401 wrong → 200 real → bypass ok). +15 tests → **192 pass** (was 177). Module table
unchanged (still gates on the human live run — now the only remaining work).
**Session 23 (no module-status change):** five 2.0 cycle items — **P2 and P3 are both CLOSED**.
**P2-3** medic polish: portal already token-clean; real fixes in `shared.css` (`.card` radius →
`var(--radius)`, verbatim speaker labels on their own line). **P3-1**: `Visit.submitted_at` via
**Alembic 0011** (applied; head bumped 0010→0011), stamped on `awaiting_review` in
`set_visit_status()`; staff queues show the SUBMISSION moment in Dhaka time (started_at fallback
for pre-0011 rows); doctor details card gains a Submitted row. **P3-2**: verified the doctor
always reads the latest medic edits (all doctor-side reads are fresh) and locked it with an
end-to-end test. **P3-3 (ADR-0044)**: new module **M16** — doctor drug-info assistant:
ddgs/DuckDuckGo search → one Flash-bucket `call_module()`, visit-scoped endpoint, disclaimer
"AI-generated information. Please verify before prescribing." attached SERVER-side on every
answer (rule #2), teal slide-in panel with textContent-only rendering; dep `ddgs==9.14.4`.
**P3-4**: last radius hardcode (`.safety-panel`) → token; prescription form verified hex-free,
Diagnosis empty. +11 tests → **177 pass** (was 166). Module table unchanged (still gates on the
human live run). Remaining cycle work: **P4-1 only** (needs the human's OTP-channel decision).
**Session 22 (no module-status change):** three 2.0 cycle items. **P1-6** retinted the last
clinical-blue leftovers in the kiosk to Teal Medical — **Priority 1 (Patient Portal) is now fully
CLOSED**. **P2-1** found and fixed the real cause of "random" queue times: SQLite serializes
timestamps offset-less, so bare `new Date()` read them as local time instead of UTC; new shared
`parseUtc()`/`dhakaTime()`/`dhakaDateTime()` helpers fix BOTH the medic and doctor queues at once
(shared file). **P2-2** wired `Patient.sex`/`birth_year` (existed, never written): the M3/M8
extraction now also returns `patient_demographics`, and a new `apply_demographics()` writer fills
Name/Age/Gender **only when empty** so staff edits are always final; the vitals PATCH and medic UI
were extended to match; the doctor portal inherits the same Patient row. +4 tests →
**166 pass** (was 162). Module table unchanged (still gates on the human live run).
**Session 21 (no module-status change):** 2.0 cycle item **P1-5** (ADR-0042b): `submit_visit` now
returns instantly — status+audit synchronous, the M10/M11/M10C LLM work moved to a FastAPI
`BackgroundTasks` job (`_post_submit_assessment`, own session bound to the request's engine via
`db.get_bind()` so tests exercise the same path). New `test_submit_background.py` proves the
assessment lands, a background crash can't block/undo submission, and the **local red-flag rule
still forces Critical from the background with the model down (rule #3)** → **162 pass** (was 159).
P1 is now 5/6 done (P1-6 polish left). Module table unchanged (gates on the human live run).
**Session 20 (no module-status change):** 2.0 cycle items **P1-3 + P1-4**. P1-3 = the first backend
change of the cycle: the M7–M9 main loop now has a **question floor** (`followup_min_questions=4`,
cap 5 still wins) and M7 switches to history-grounded **deepening questions** when the M6 gap list
runs out (human-approved prompt); the KIOSK-7 `scope=fields` resume loop is unaffected. New
`test_followup_min_questions.py` + 2 tests updated to the new spec → **159 pass** (was 156). P1-4 =
kiosk summary highlights empty REQUIRED fields (amber `.missing` card + bilingual "Needs info"
chip). Module table unchanged (still gates on the human live run — note M7's loop behavior changed,
so the live run will see 4–5 questions per visit).
**Session 19 (no module-status change):** advanced the 2.0 cycle by 4 tracker items (one per "go"),
all frontend/CSS, all preview-verified with a stubbed `api` (no LLM calls): **STRUCT-2** logout→`/`
in all 3 headers; **STRUCT-3** shared "Teal Medical" palette (ADR-0043, human chose Option A from
live previews); **P1-1** kiosk "Done" auto-stops the mic + flushes the final turn before summarizing;
**P1-2** full EN↔BN toggle of the Patient Portal (bilingual bubbles + `setBilingualText()`, patient
words verbatim — rule #1). No pytest run (no backend logic changed); the 15-module table is unchanged
(still gates on the human live run). Next = **P1-3** (first backend change: force 4–5 follow-ups).
**Session 18 (no module-status change):** the human opened a NEW feature/fix cycle with the spec
`agent_docs/context fixed problem 2.0.md` (UI/UX evolve-the-theme redesign + functional fixes on
all three portals + real OTP + a doctor-side AI drug-info chatbot). Explored the code and approved
a priority-sequenced, checkable plan (mirrored in `current_task.md`); executing ONE item per "go",
functional fixes before polish. **STRUCT-1 done** (rename "Patient Kiosk" → "Patient Portal",
strings only). **ADR-0042** locks: UI = evolve the theme (keep layouts), Submit = assess in
background; faculty quantized-model "Future Features" are OUT of scope. Module table unchanged —
still gates on the human live-voice run; the 2.0 spec is UX/functional polish, not module state.
**Session 17 (no module-status change):** diagnosed why "voice transcribes but formatting fails":
Gemini Flash 429s were unlogged (only the last chain provider was recorded) and the sole fallback
(OpenRouter `:free`, ~50 req/day) 429'd 10× in 9s with no backoff while Groq sat unused. Fix =
**ADR-0041 quota-aware switching**: per-attempt `module_events` logging, 429/quota cooldown
(60s/15min, fail-open), fallback chain assigned→Groq→Cerebras→Mistral→OpenRouter (optional new
free buckets, blank-key skipped). +6 tests → **156 pass**. Module table unchanged (still gates on
the human live run).
**Session 16 (no module-status change):** Arch TTS **DONE + verified** — packages installed, the
enabled `speech-dispatcher.socket` started, and after a full Chromium restart with
`--enable-speech-dispatcher` the kiosk 🔊 speaks + mic works (**TC-V2 audio PASS on Arch**,
human-confirmed; ADR-0040). Module 7 stays 🟨 (still gates on the full live-voice run:
TC-V1/V3/F2/R1/A1 with real numbers). Human also flagged upcoming **bugs + faculty-requirement
features** — to be enumerated into a numbered spec next session and planned one step at a time.
**Progress:** Session 8 built the reconciled system end to end (see `changelog.md` S8 +
`reconciliation.md`). **DB:** all 15 architecture.md tables applied (Alembic head `0009_audit_log`).
**Backend:** kiosk phone + stub OTP → visit; intake (M3/M4/M6); follow-up loop (M7/M8/M9);
**M10 risk with a LOCAL red-flag rule that forces Critical even if every LLM is down** + M11 XAI;
M12 local report (Red Flags + no-diagnosis disclaimer); staff submit→auto-assess→queue→assign→
review→feedback; audit_log on every state change. **Frontend:** patient kiosk (`/kiosk.html`),
medic (`/medic/`), doctor (`/doctor/`) — clinical-blue design (ADR-0029), bilingual, TTS+STT.
**104 tests pass.** Everything below moves off ⬜; most modules are ✅-on-happy-path but stay
🟨 until the human live run records real numbers (TC-V2/V3/F2/R1/A1) with real API keys. Module 1
also still awaits the live mic test + ~50 samples + WER/latency.
**Session 8b:** the ADR-0029 design-system switch is now reflected in the docs (CLAUDE.md +
DESIGN-mintlify SUPERSEDED). **First live Gemini call verified** (M2 correction, correction-only).
**Live-run key gap:** only Gemini is keyed — Groq + OpenRouter empty, so M6/M7 can't run live until
a key is added (all still pass offline). No module status changed from Session 8.
**Session 8c:** key gap CLOSED (all three keys in `backend/.env`). **Live-run Part 1 PASSED** —
the full M3→M12 pipeline ran live with synthetic typed text; `module_events` shows every module
on its ADR-0026 bucket (M3/M8 flash-lite, M4/M10/M11 flash, M6/M7 groq, M12 local), 13/13 ok,
zero fallbacks, latencies 0.5–8.6 s. 104 tests still pass. Modules stay 🟨 (not ✅) because the
statuses gate on the HUMAN real-voice run (TC-V2/V3/F2/R1/A1) — that is now the only thing
between most modules and ✅-on-live-path. M1 also still awaits the mic test + ~50 samples + WER.
**Session 9:** the human RAN the Part-2 real-mic test; findings became the work spec
`context_fixed_problem.md` (STRUCT/KIOSK-1..7/MEDIC-1..7/DOCTOR-1..7) and a 20-step plan was
approved (decisions locked in `current_task.md`: C1 suggestion-not-diagnosis, C2 display-only
risk bands, DB-backed prescriptions/reports via Alembic 0010, stored bilingual values, DB
letterhead, KIOSK-7 resume loop). Step 1 DONE: legacy demo isolated at `/legacy/`, landing page
at `/`, startup entry-point log (ADR-0031). Step 2 DONE: Alembic **0010** applied (nullable
`documents.utterance_id` for visit-grain exports, patient vitals, letterhead columns,
`prescriptions` table — ADR-0032, architecture.md §8). **113 tests pass.** Module statuses
unchanged — the affected areas (M7 loop UX, M12 exports, M14 dashboards) move when their
steps land.
**Session 11:** steps 8–13 landed. Kiosk summary is feature-complete for this build
(KIOSK-4 raw .docx download · KIOSK-5 per-field cards · KIOSK-6 full language consistency ·
KIOSK-7 resume loop: `?scope=fields` on the M7–M9 endpoints, shared question cap, progress
chip, fail-open — ADR-0034). Medic portal: fully bilingual staff.js + EN/বাংলা toggle +
Refresh-Queue clarity (MEDIC-1/2/5) and the MEDIC-3 risk panel + override endpoint
(ADR-0035: appended `model_provider='human'` rows, audit_log from/to, staff cannot
downgrade a red-flag Critical — 409). **129 tests pass** (new: test_resume_loop 5,
test_risk_override 3). Module statuses still 🟨 — the gate remains the human live-voice
re-run; M7's loop UX and M10's override path are now built-and-offline-tested.
**Session 12:** steps 14–16 landed. The medic portal is feature-complete for this build:
**MEDIC-4** C1 suggested condition (ADR-0036 — new module `M10C` on the Flash bucket, its own
module_events code, generated best-effort at kiosk submit, stored in
`entities["suggested_condition"]` with embedded "not a diagnosis" disclaimers, staff edit via
`PATCH /profile/condition`, shared `renderConditionCard()`; the kiosk never shows it) and
**MEDIC-6/7** post-referral summary + working .docx (ADR-0037 — `PATCH /patients/{id}/vitals`
weight edit, patient embedded in `GET /visits/{uuid}`, the summary_report docx now carries the
C1 block + vitals and regenerates the M12 report FRESH at download so staff edits/overrides
always show). Doctor portal: **DOCTOR-1** ↻ Queue removed, **DOCTOR-2** fully bilingual
(safety panel re-renders from state), DOCTOR-7 base polish + print CSS (finishes with 17–19).
**139 tests pass** (new: test_suggested_condition 5, test_medic_summary 5). Statuses still 🟨 —
gate unchanged (human live-voice re-run); M12's export path and M14's medic side are
built-and-offline-tested.
**Session 13:** steps 17–18 landed. **Step 17 — DOCTOR-3** (frontend-only,
`frontend_doctor/index.html`): patient-details card in the doctor case view (Name · Phone · Age ·
Gender · Weight · BP from the patient embedded in `GET /visits/{uuid}`) with inline weight+BP edit
reusing the existing `PATCH /patients/{id}/vitals`; a mounted `#condition-card` so the shared
`renderConditionCard()` surfaces the C1 suggestion + disclaimer; and the **C2 band** (`tierBand()`)
beside the risk tier. **Step 18 — DOCTOR-4/5 prescription form (ADR-0038):** a read-only prefill
endpoint `GET /visits/{uuid}/prescription/context` (letterhead only), an idempotent
`seed_demo_letterhead()` (fills NULL letterhead columns at startup), and a full-screen bilingual
prescription form — editable letterhead + auto-filled patient/symptoms + add/remove medicine rows +
**empty doctor-authored Diagnosis (never AI, rule #2)**. **Step 19 — DOCTOR-6 prescription .docx +
save (ADR-0039):** `POST /api/visits/{uuid}/prescription` renders the LOCAL .docx
(`render_prescription`) + persists a `prescriptions` row linked to a `documents` row (kind
`prescription`); the form's Submit POSTs → auto-downloads → "✅ Saved & Downloaded". New
prescription per Submit; the .docx reads only the payload so Diagnosis can't be AI-filled
(regression-tested). New `test_prescription_context.py` (6) + `test_prescription_docx.py` (5).
**150 tests pass.** Statuses gate on the human live-voice re-run; the doctor portal's
DOCTOR-1..7 targets are now all built (final `context_fixed_problem` flips happen in step 20).

---

## The 15 modules

> **S25 update:** Modules 1–14 moved 🟨 → ✅ after the human live real-mic run PASSED on Windows 11
> (TC-V1/V2/V3/F2/R1 all ✅). That run was **qualitative** — **formal WER / precision-recall on a
> labeled set is still to be logged as thesis evidence** (see `test_log.md` "Metrics we care about"),
> and it was Windows-only this pass. M5 stays retired ⛔; **M15 stays 🟨** (future retrain pipeline).

| # | Module | Status | "Done" means (testable) |
|---|--------|:------:|--------------------------|
| 1 | Speech-to-Text | ✅ | Live mic audio is transcribed and the **raw** Bangla/Banglish text appears on screen within ~3s; raw text is stored unchanged; works on both Windows and Linux; manual text-input fallback exists. |
| 2 | Text Processing & Normalization | ✅ | Given raw text, a separate cleaned/normalized field is produced (spelling, fillers removed, sentence boundaries); raw is never modified; measured on a small test set. **Built** (existing `/api/correct` corrector, reused as M2); live accuracy on a test set still pending. |
| 3 | Information Extraction | ✅ | From normalized text, symptoms / body part / duration / severity / meds / history are extracted as structured fields; precision & recall recorded in test_log. **Built** (`services/intake.py`, M3 → 10-field `summary_fields` JSON); precision/recall on real data pending. |
| 4 | Initial Clinical Summary | ✅ | A 2–4 sentence chief-complaint summary is generated from extracted fields and shown to the doctor. **Built** (`services/intake.py`, M4). |
| 5 | ~~Emergency Detection~~ | ⛔ | **RETIRED (Session 7, ADR-0024).** The standalone module + its flowchart diamond/alert are removed. Its job is now a **rule-based red-flag check inside Module 10** (see M10). Number 5 is left as a permanent gap so M6–M15 keep their IDs. |
| 6 | Missing Information Analysis | ✅ | System outputs a checklist of present vs. missing data points for the case. Now fed **directly by M4** (M4→M6, no emergency branch). **Built** (`services/intake.py`, M6 → `case_profiles.gaps`). |
| 7 | Follow-up Question Generation | ✅ | System generates prioritized follow-up questions (Bangla/English) for the gaps, no repeats of answered items; each question is **shown as text AND spoken via TTS**, and the patient replies **by voice only** (ADR-0027/0028). **Built** (`services/followup.py` + kiosk STT/TTS; S10: per-message 🔊 + no-voice hint; S11: KIOSK-7 resume loop — `?scope=fields` targets the empty summary fields, shared cap, "নেই/জানি না" counts as answered, ADR-0034). TC-V2 partial: Windows dev box has NO bn TTS voice (text fallback + hint verified; audio needs a voice installed). Live voice loop pending (TC-V3/F2). |
| 8 | Response Processing & Profile Update | ✅ | Patient answers are re-processed and merged into the profile with conflict handling. **Built** (`services/profile_update.py`, M8; human-edited fields are never overwritten). |
| 9 | Case Completion Check | ✅ | A completeness score is computed; loops back to Module 7 until threshold or max turns reached. **Built** (`services/completion.py`, LOCAL; threshold + max-turn exit, both env-tunable). |
| 10 | Risk Assessment Engine | ✅ | Each case is classified Low/Medium/High/Critical from rules + model; **a rule-based red-flag check forces Critical for clearly life-threatening symptoms (chest pain, stroke signs, severe breathing difficulty, loss of consciousness) and surfaces them prominently**; accuracy + red-flag recall recorded on a labeled test set. **Built** (`services/risk.py` + `red_flags.py`; rule survives total LLM outage; red-flag recall enforced per-phrase in tests; S11: MEDIC-3 staff override appends a human row, audit-logged, red-flag-Critical downgrade blocked — ADR-0035). Accuracy on labeled real data pending. |
| 11 | Explainable AI (XAI) | ✅ | Every risk output has a plain-language reason listing the contributing factors. **Built** (`services/risk.py`, M11; deterministic fallback so no risk row is ever reason-less). |
| 12 | Structured Clinical Report | ✅ | A full report (all sections) is generated and exportable as PDF + dashboard view; contains **no diagnosis**; includes a **Red Flags** section sourced from M10. **Built** (`services/report.py`, LOCAL assembly + disclaimer; shown in doctor portal). Per-visit `.docx` export of the summary report + raw transcript SHIPPED (S9 step 3, `visit_docx.py`); S12: summary_report carries the C1 possible-condition block + vitals and regenerates FRESH at download (ADR-0037). PDF still pending. |
| 13 | EHR Database | ✅ | Transcripts, profiles, reports, and audit logs are stored and retrievable by patient ID/date; data encrypted. **Built** (all 15 tables, Alembic head `0009`; retrieval by phone + status; `audit_log` on every state change). Encryption-at-rest still pending. **S39 (ADR-0064) — Alembic 0014:** blood glucose is recordable at intake as a VALUE **plus its measurement context**, refused apart, with no band/interpretation column anywhere (rule #2); and the patient NAME now carries its provenance, **derived from `audit_log` with no new column** — the AI auto-fill, which used to write into a permanent medical record leaving no trace, is now audited. The record is exportable in two forms from ONE builder: the FHIR R4 Bundle (S38) and a human-readable **PDF that renders that same bundle** and never re-reads the DB. |
| 14 | Doctor Dashboard | ✅ | Web UI shows report, risk, flags, XAI; doctor can override/annotate; high/critical cases alerted. **Built** (`frontend_doctor/`: queue, risk/red-flags/XAI panel, field edit, Override/Accept; S12: fully bilingual, ↻ Queue removed, print CSS. Medic side: C1 condition card + post-referral summary + .docx download, S12). **S37 (ADR-0058/0059) — the two staff portals were audited as ROLES and given the layers each was missing:** medic = urgency-ordered queue + wait/red-flag/completeness on every row + floor-load strip + **vitals captured BEFORE the referral** (they had been recordable only after it) + an **advisory** handover check that can never block a forward + referral attribution in `audit_log`; doctor = **patient timeline + prescription history** (`prescriptions` had been a write-only table) + a **Completed** scope so a reviewed case stays reachable + review controls that hide once the case is reviewed. Plus `frontend_shared/motion.css` (depth/motion, staff-only, every animation behind `prefers-reduced-motion`). All views are **derived and read-only — no new table, no new column, Alembic still 0012**. Full role/ownership reference: `agent_docs/portal_roles.md`. **S39 (ADR-0064):** both portals show the patient name WITH its origin; the medic records blood sugar before the referral; the doctor sees it read-only beside the shared reference chart and can download the record as **PDF or FHIR**; and the post-referral screen's duplicate identity/weight editors were REMOVED — they wrote the same row through the same PATCH as the intake form with fewer fields. |
| 15 | Feedback & Continuous Learning | 🟨 | Doctor feedback is collected and usable to retrain/fine-tune; regression check before deploying updates. **Built** (feedback stored via `POST /api/visits/{uuid}/feedback`); retrain/regression pipeline still future. |

---

## Roadmap phases (how we get Module 1 right first)

These come from the build plan. Each phase has a clear "move on when" gate.

### Phase 0 — Quick working demo  ⬅️ WE ARE HERE (planning locked; starting Phase A next)
**Goal:** Prove the whole loop (live voice → raw text → corrected text → screen)
with zero ML setup, using the browser Web Speech API + one free LLM for correction.
**Move on when:** I can speak Bangla/Banglish into the browser, see the raw text
live, see a corrected version beside it, and the raw text is stored unchanged.
(Also: ~50 real sample utterances collected for later testing.)
**Build steps (6):** 1 scaffolding ✅ · 2 backend skeleton ✅ · 3 correction service ✅
· 4 API routes + static serving ✅ · 5 frontend (mic + boxes + fallback) ✅
· 6 end-to-end live test ✅ (S25 — human real-mic run PASSED on Windows) · collect ~50 samples ⬜
(still pending, for formal WER).

**Session 7 (architect lock):** flowchart updated (Emergency removed, M4→M6 direct); stack +
per-module API strategy + voice model locked; all tracking docs rewritten. No code. The full
sequential build plan (Phases A–I) now lives in the architect output / the build plan; the
**first coding step is Phase A / Step A1 — add browser TTS to the frontend.**

**Multi-provider STT (Session 3):** built — then REMOVED in Session 4 (scope
simplified to browser-only for Module 1; may return in a later module).

**Browser-only STT (Session 4):** continuous recording (no cap, append-only,
~10s-silence auto-stop) ✅ · Mintlify UI + scrollable stick-to-bottom panels ✅
· live mic test on real speech + ~50 samples ⬜ (next, human).

**Document export (Session 5):** every completed session auto-saves a `.docx`
(python-docx; derived artifact, DB is source of truth) ✅ · `GET /api/documents`
list + `/download` ✅ · Saved-documents frontend panel ✅. Early groundwork toward
Module 12 (Structured Clinical Report) and Module 13 (EHR storage) — those modules
stay ⬜ (no clinical content/extraction yet; this only exports raw + corrected).

**Two-file export + Alembic (Session 6):** RAW and CORRECTED exported as SEPARATE,
independently downloadable `.docx` (raw on Stop, corrected on Correct) via a
`documents.kind` column ✅ · routes `GET /api/transcripts/{id}`,
`POST /api/transcripts/{id}/documents/{raw,corrected}` ✅ · per-panel download buttons +
loading/error states ✅ · **Alembic** schema migrations, auto-run at startup, fixing the
`no column named stt_provider` bug in place (data preserved) ✅. 19 tests pass.

### Phase 1 — Robust local core
**Goal:** FastAPI + WebSocket backend streaming live mic audio to faster-whisper
(int8, CPU); store immutable raw + corrected text; verified working on both
Windows and Arch Linux from one requirements.txt.
**Move on when:** Live transcription runs locally on both machines with usable
latency, and raw/corrected are saved separately. Module 1 = ✅ at this point.

### Phase 2 — Bangla accuracy
**Goal:** Swap in a Bangla-fine-tuned Whisper model (e.g. tugstugi/whisper-medium
converted to CTranslate2); add Banglish→Bangla transliteration (IndicXlit) + LLM
normalization (Module 2); measure WER on our own samples.
**Move on when:** WER on our real samples is recorded and acceptable, and a
separate normalized field is produced. This begins Module 2.

### Phase 3 — Stretch / thesis contribution
**Goal:** Fine-tune on medical Bangla data, and/or harden the API for the future
mobile app. Optional speaker separation (doctor vs patient).

---

## Notes
- Nothing is "done" until its testable definition above is met **and** the result
  is written in `test_log.md`.
- If a later module is tempting to start early, check the dependency column in
  `constitution.md` first.
- **Emergency safety did not go away** — it moved into Module 10 as a rule-based red-flag
  check (ADR-0024). A medical pre-screening tool must never present a falsely reassuring
  picture (Open Flag 1 if the student wants to revisit this).
