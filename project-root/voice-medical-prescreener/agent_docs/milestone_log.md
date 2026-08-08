# milestone_log.md — Big-Picture Status Board

> This answers one question: **"Where are we in the whole project right now?"**
> Update the status when a module's state changes. Keep the "Done means" line
> honest and testable — not "works well", but a real, checkable definition.

**Status keys:** ⬜ Not started · 🟨 In progress · 🟦 Blocked · ✅ Done · ⛔ Retired

**Last updated:** 2026-08-08 (**Session 30, closed after an EDGE COMPATIBILITY VERIFICATION —
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
| 13 | EHR Database | ✅ | Transcripts, profiles, reports, and audit logs are stored and retrievable by patient ID/date; data encrypted. **Built** (all 15 tables, Alembic head `0009`; retrieval by phone + status; `audit_log` on every state change). Encryption-at-rest still pending. |
| 14 | Doctor Dashboard | ✅ | Web UI shows report, risk, flags, XAI; doctor can override/annotate; high/critical cases alerted. **Built** (`frontend_doctor/`: queue, risk/red-flags/XAI panel, field edit, Override/Accept; S12: fully bilingual, ↻ Queue removed, print CSS. Medic side: C1 condition card + post-referral summary + .docx download, S12). |
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
