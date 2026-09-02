# Niramoy — Walkthrough Video v2
## Narration script + scene-by-scene storyboard — FOR APPROVAL

**Status:** script only. Nothing has been rendered. No video will be produced until you approve this.

| | |
|---|---|
| **Target runtime** | **2:53** at a natural pace (hard ceiling 3:00 — 7 s of headroom) |
| **Narration** | 397 spoken words @ ~145 wpm, natural presenting pace, first person |
| **Scenes** | 15 |
| **Patient side** | **S2–S10 = 109 s = 63 % of the runtime** |
| **Medic + Doctor + EHR** | S11–S14 = 49 s = 29 % |
| **Title + close** | 14 s = 8 % |
| **Language** | English voice-over; the UI on screen switches EN/BN and shows real Bangla |

**The one sentence the video must land:**
A patient can communicate naturally by voice → Niramoy structures the information → a medic verifies it → a doctor makes the clinical decision → the information becomes a structured medical record.

---

## 1. What is different from the previous video

| Previous video | This script |
|---|---|
| Patient journey compressed to 7 beats | **11 patient beats** — every stage you listed, in order |
| No AI-extraction step shown | **S7** shows the 10-field extraction as its own beat |
| No confirmation/correction step | **S6** is built entirely around the read-back + yes/no correction |
| Risk/red-flag mentioned in one line at the doctor | **S10** (what runs at submit) **and S13** (what the doctor sees) |
| No explanation of *how* portals connect | **S11** is a dedicated handover beat: one record, one status, no copies |
| Portal hand-offs implied | Status transitions named on screen: `in_progress → awaiting_review → awaiting_doctor → reviewed` |
| Runtime 2:47, patient ≈ 66 % but shallow | Runtime 2:52, patient **63 % and complete** |

---

## 2. The narration, as one continuous read

> This is Niramoy — a voice-first medical pre-screening system built for clinics in Bangladesh.
>
> The patient journey starts here. No app, no account — just a mobile number, typed or spoken digit by digit. A six-digit code verifies them. It is hashed, expires in five minutes, and works only once.
>
> This is the heart of it. The assistant asks out loud and on screen, then the microphone opens by itself — nothing to tap. Not a touch kiosk.
>
> The patient answers in whatever they actually speak — Bangla, Banglish, or a regional dialect. Recognition runs in Bangla, and their words appear live as they talk.
>
> Then it reads the answer back — "I heard you say" — in the patient's exact words. They just say yes, or no. Nothing is stored until they confirm, and the raw text is never edited. Rule number one.
>
> From that speech the AI extracts structured clinical information into ten fields — main problem, onset, symptoms, history, medicines, allergies. The raw transcript stays untouched beside it.
>
> Then it finds the gaps and asks four to five follow-up questions, each spoken aloud and shown on screen. The patient answers by voice, and every answer updates the same case profile.
>
> Everything is compiled into a summary the patient reviews — and can hear read aloud, so a patient who cannot read still checks their own answers. Anything missing is asked for, one field at a time.
>
> They confirm and submit. In the background, risk is assessed and a rule-based red-flag check scans their own words — in Bangla, Banglish and English. The patient never sees a tier or a diagnosis.
>
> That single case now moves forward — one record, one status, no copies.
>
> A medic sees it first, in a queue ordered by urgency, not arrival. They check every AI field against the patient's verbatim words, correct what is wrong, record vitals, and forward to a named doctor.
>
> The doctor's case opens with safety: the risk tier, the red flags that triggered, and a plain-language explainable-AI reason. That rule is local and deterministic — it can force critical even if every model is offline.
>
> The doctor decides. They write the diagnosis themselves — the AI's suggestion never enters it — and accepting the case turns the encounter into an HL7 FHIR R4 document bundle, downloadable as data or PDF.
>
> The patient speaks. The system structures. A medic verifies. The doctor decides — and it becomes a medical record.

---

## 3. Scene-by-scene storyboard

### S1 · 0:00 – 0:06 · Title

- **On screen:** Title card on the teal brand ground. `Niramoy` · sub-line `Voice-first medical pre-screening · Bangla · Banglish · Regional speech`. Small footer: `CSE499 Capstone · North South University`.
- **Action:** Wordmark fades in; the four-stage chain `Patient → Medic → Doctor → EHR` draws in underneath, then dims back, leaving `Patient` lit.
- **Voice-over:** *This is Niramoy — a voice-first medical pre-screening system built for clinics in Bangladesh.*
- **Subtitle:** `Niramoy — a voice-first medical pre-screening system for clinics in Bangladesh.`
- **Feature:** Framing only. The chain that lights up is the map the rest of the video follows.

---

### S2 · 0:06 – 0:14 · Patient Portal — sign in

- **On screen:** `/kiosk.html`, phone screen. `Mobile Number` field, `🎤` mic button, the `[🎤 Speak] [⌨ Type]` switch, live `digit-preview` under the field, EN/BN toggle in the header.
- **Action:** The digit preview fills a number one digit at a time; the `🎤 Speak` half of the switch is highlighted to show voice is the default, not the fallback.
- **Voice-over:** *The patient journey starts here. No app, no account — just a mobile number, typed or spoken digit by digit.*
- **Subtitle:** `No app, no account — just a mobile number, typed or spoken.`
- **Feature:** Patient entry point; **voice available from the very first field**; bilingual UI. `frontend/kiosk.html` `#screen-phone`.

---

### S3 · 0:14 – 0:22 · One-time code

- **On screen:** `#screen-otp` — `Enter 6-Digit OTP`, mic button, digit preview.
- **Action:** Code appears digit by digit; verify; the screen advances. A small caption chip reads `hashed · single-use · 5-minute expiry`.
- **Voice-over:** *A six-digit code verifies them. It is hashed, expires in five minutes, and works only once.*
- **Subtitle:** `A one-time code — hashed, single-use, expires in five minutes.`
- **Feature:** Real OTP (ADR-0045): hashed, TTL 300 s, max 5 attempts, pluggable sender (`OTP_CHANNEL=dev|textbee`). **No code, key or `.env` value is ever on screen.**

---

### S4 · 0:22 – 0:33 · Voice-first, hands-free  ★ the anchor shot

- **On screen:** `#screen-voice`. Assistant avatar in its **speaking** state, the question in the chat thread in Bangla + English, the step strip `1 🔊 I ask → 2 🎤 You speak → 3 ✔ You check`, progress chip `প্রশ্ন ১ / ৪`.
- **Action:** Avatar speaks → a beat of silence (the echo guard) → the avatar flips to **listening** and the mic button turns active **on its own**. A callout points at the mic: `opened by itself — no tap`. The pointer stays visibly parked away from the controls for the whole shot.
- **Voice-over:** *This is the heart of it. The assistant asks out loud and on screen, then the microphone opens by itself — nothing to tap. Not a touch kiosk.*
- **Subtitle:** `The assistant asks aloud — then the mic opens by itself. Nothing to tap.`
- **Feature:** ADR-0048 voice-first loop, S1–S4: `voice_loop=auto`, `tts_guard_ms` echo guard, question **spoken and shown** together (ADR-0028), the 3-step strip lit from real kiosk state.

---

### S5 · 0:33 – 0:45 · The patient speaks

- **On screen:** Same screen. `🗣 What you are saying` panel filling with live interim text in Bangla script; avatar in **listening** state; the `[🎤 Speak]` mode still selected.
- **Action:** Interim words accumulate, then settle into the final line. A corner chip shows `webkitSpeechRecognition · lang = bn-BD · continuous · interim`.
- **Voice-over:** *The patient answers in whatever they actually speak — Bangla, Banglish, or a regional dialect. Recognition runs in Bangla, and their words appear live as they talk.*
- **Subtitle:** `Bangla, Banglish or regional speech — captured live, in their own words.`
- **Feature:** M1 live STT, Bangla-first. Extraction and follow-up prompts are written for **Bangla / Banglish / English** input (`services/intake.py`, `services/followup.py`); the red-flag matcher holds Bangla, Roman-Banglish and English phrases.

---

### S6 · 0:45 – 1:01 · Raw words preserved → confirm or correct  ★ rule #1

- **On screen:** The `I heard you say:` read-back card with the patient's verbatim line, `🎤 Just say "yes" or "no"`, then `✔ Yes — that is right` / `✖ No — say it again`, and the 3-2-1 countdown strip `Sending your answer — keep speaking to continue`.
- **Action:** Read-back appears → countdown ticks 3, 2 → a **split screen** slides in: left `RAW — stored verbatim, write-once`, right `CORRECTED — a separate field`, with an arrow showing raw never being touched. Cut back; the patient confirms; the turn is stored.
- **Voice-over:** *Then it reads the answer back — "I heard you say" — in the patient's exact words. They just say yes, or no. Nothing is stored until they confirm, and the raw text is never edited. Rule number one.*
- **Subtitle (2 cues):** `It reads the answer back in the patient's exact words — yes, or no.` / `Nothing is stored until they confirm. The raw text is never edited.`
- **Feature:** S34/S35 spoken read-back + **spoken** yes/no confirmation; S4 countdown as a *confirmation window, not a cutoff* — resumed speech cancels it. **Rule #1**: `utterances.raw_text` is write-once; `corrected_text` is a separate column.

---

### S7 · 1:01 – 1:12 · AI extraction

- **On screen:** The 10 summary-field cards being populated, each card showing its **English and Bangla** value; a left-hand strip keeps the verbatim transcript visible the whole time.
- **Action:** The transcript line highlights, an arrow travels to the card it filled; cards fill in sequence. Field titles readable: `1. Main Problem`, `2. When Started & Duration`, `3. Symptom Details`, `5. Medical History`, `6. Current Medicines`, `7. Allergies`.
- **Voice-over:** *From that speech the AI extracts structured clinical information into ten fields — main problem, onset, symptoms, history, medicines, allergies. The raw transcript stays untouched beside it.*
- **Subtitle:** `The AI extracts ten structured clinical fields — the raw transcript untouched.`
- **Feature:** M3 intake extraction (`POST /visits/{uuid}/intake`), the fixed 10-field contract, **bilingual `en` + `bn` values**, `source: ai` provenance on every field.

---

### S8 · 1:12 – 1:26 · Follow-up questions, answered by voice

- **On screen:** Back on the conversation screen; a follow-up question in **Bangla script followed by English**, spoken and shown; the chat thread grows; the mic re-opens after each question.
- **Action:** Question → mic opens itself → answer → thread grows → next question. A quiet counter shows `follow-up 2 of 4–5`; a completeness meter nudges upward as answers land.
- **Voice-over:** *Then it finds the gaps and asks four to five follow-up questions, each spoken aloud and shown on screen. The patient answers by voice, and every answer updates the same case profile.*
- **Subtitle:** `It asks four to five follow-ups — spoken and on screen — and answers update the case.`
- **Feature:** M6 gap detection → M7 question → M8 merge → M9 completeness. Real guardrails: `followup_min_questions=4`, `followup_max_questions=5`, `completeness_threshold=0.7`. Questions are generated **in Bangla with English alongside**.

---

### S9 · 1:26 – 1:41 · Structured summary — the patient reviews it

- **On screen:** `#screen-summary` — `Please Review Your Pre-Screening Summary` / `Compiled from your voice answers. It will be sent to the doctor.`, the card grid, the `🔊 Hear my answers` button, and the resume dock `A few more questions before we finish`.
- **Action:** Cards scroll; `🔊 Hear my answers` is pressed and the avatar reads the summary while a card highlights in time; then the resume dock asks for one still-empty field and the patient answers it by voice.
- **Voice-over:** *Everything is compiled into a summary the patient reviews — and can hear read aloud, so a patient who cannot read still checks their own answers. Anything missing is asked for, one field at a time.*
- **Subtitle (2 cues):** `A structured summary the patient reviews — and can hear read aloud.` / `Anything still missing is asked for, one field at a time.`
- **Feature:** KIOSK-6 review, summary read-aloud (accessibility for low-literacy patients), KIOSK-7 `scope=fields` resume loop, and the server-side readiness verdict that writes the "still required" notice.

---

### S10 · 1:41 – 1:55 · Submit → risk and red flags, in the background

- **On screen:** `✔ Confirm & Submit` pressed → `Submitted — Thank You!` modal with the 5-second reset. Then the screen splits: patient side stays on the thank-you; the other half shows a **background** panel — `M10 risk assessment` and `RULE-BASED RED-FLAG CHECK` scanning Bangla / Banglish / English phrases.
- **Action:** Submit → thank-you (with the spoken confirmation and the automatic raw-transcript `.docx`) → the background panel runs and a `CRITICAL` tier plus `chest pain` land **on the staff side only**. A lock badge over the patient half reads `patient is never shown a tier or a diagnosis`.
- **Voice-over:** *They confirm and submit. In the background, risk is assessed and a rule-based red-flag check scans their own words — in Bangla, Banglish and English. The patient never sees a tier or a diagnosis.*
- **Subtitle (2 cues):** `They submit — risk and red flags are assessed in the background.` / `A rule-based check reads Bangla, Banglish and English. The patient sees no tier.`
- **Feature:** Instant `in_progress → awaiting_review` (the patient never waits on an LLM), background M10/M11/C1 job, the **local deterministic** red-flag rule (rule #3), spoken "your information reached the doctor" + automatic raw-transcript download for the patient (S36). Rule #2: the kiosk never shows a tier, red flag or suggested condition.

---

### S11 · 1:55 – 2:01 · How the portals connect

- **On screen:** Clean diagram beat. The status machine, animating left to right:
  `in_progress ──patient submits──▶ awaiting_review ──medic forwards──▶ awaiting_doctor ──doctor reviews──▶ reviewed`
  with a single card icon travelling along it, and the label `ONE record · ONE status · no copies`.
- **Action:** The card moves; portal badges (Patient / Medic / Doctor / EHR) light as it passes.
- **Voice-over:** *That single case now moves forward — one record, one status, no copies.*
- **Subtitle:** `One record, one status — the case moves; nothing is copied.`
- **Feature:** The real hand-over chain. Medic and doctor read the **same** `case_profiles` row — there is no message and no second copy (`portal_roles.md` §4).

---

### S12 · 2:01 – 2:16 · Medic Portal — verify, vitals, forward

- **On screen:** `/medic/` — `Triage Queue` with `⚑ Urgency order`, the floor-load strip, then the case: `Patient's Own Words / Raw — unedited` beside `Patient Summary Case Verification`, `Intake & Vitals`, `Handover Check`, `Assign Doctor:` and `Submit & Forward`.
- **Action:** Queue → open the top (most urgent, longest-waiting) case → the raw panel and an AI field sit side by side → one field is corrected and its badge flips `ai → human` → weight/BP entered → doctor selected → forwarded, and the case leaves the queue.
- **Voice-over:** *A medic sees it first, in a queue ordered by urgency, not arrival. They check every AI field against the patient's verbatim words, correct what is wrong, record vitals, and forward to a named doctor.*
- **Subtitle (2 cues):** `A medic works a queue ordered by urgency, not arrival.` / `They check every AI field against the patient's own words, add vitals, and forward.`
- **Feature:** M-1 triage-ordered queue, M-2 row chips, M-3 floor load, **M-4 vitals captured before the referral**, M-5 advisory handover check (it can never block a forward), M-6 referral attribution. Raw stays read-only; only the derived field changes, and it is labelled `human`.

---

### S13 · 2:16 – 2:31 · Doctor Portal — safety first, and the explanation

- **On screen:** `/doctor/` — `My Assigned Patients`, then the case with the safety block at the top: `Risk Assessment` tier chip, `Red Flag` chip, and the box `🧠 Explainable-AI Reasoning: …`. `Patient's Own Words / Raw — unedited` below it; `Patient History` alongside.
- **Action:** The case opens and the eye is led top-down: tier → red flag → reason. A side annotation shows the safety ordering: `red-flag rule runs regardless of the model · a triggered flag forces critical`.
- **Voice-over:** *The doctor's case opens with safety: the risk tier, the red flags that triggered, and a plain-language explainable-AI reason. That rule is local and deterministic — it can force critical even if every model is offline.*
- **Subtitle (2 cues):** `The doctor's case opens with safety — tier, red flags, and a plain-language reason.` / `The red-flag rule is local and deterministic: it can force critical on its own.`
- **Feature:** DOCTOR-7 safety-first layout, M11 stored XAI reason (**never stored without a reason**), the local rule that the LLM can only ever escalate — never suppress. D-1 patient timeline.

---

### S14 · 2:31 – 2:45 · The doctor decides → the EHR record

- **On screen:** `📝 Write Prescription` inline at the bottom of the case — `Diagnosis` typed by the doctor, `Advice / Lifestyle`, `Required Tests` token editor — then `Accept & Write to EHR`, and the produced `⬇ EHR record (FHIR)` and `⬇ EHR record (PDF)`.
- **Action:** Diagnosis typed by hand; a callout marks the AI suggested-condition card `excluded from the export`. Accept → the FHIR document bundle appears, scrolling to show `Bundle · type: document` → `Composition`, and a section labelled as the patient's **verbatim** words, carried through to the record.
- **Voice-over:** *The doctor decides. They write the diagnosis themselves — the AI's suggestion never enters it — and accepting the case turns the encounter into an HL7 FHIR R4 document bundle, downloadable as data or PDF.*
- **Subtitle (2 cues):** `The doctor writes the diagnosis themselves — the AI's suggestion never enters it.` / `Accepting turns the encounter into an HL7 FHIR R4 document bundle.`
- **Feature:** DOCTOR-4/5/6 prescription, M14 review, B1 FHIR R4 document Bundle served as `application/fhir+json`, the FHIR-bundle-derived PDF, the AI suggestion excluded by design, the risk tier exported as a `RiskAssessment` (never a `Condition`), and the verbatim transcript reproduced in its own section.

---

### S15 · 2:45 – 2:53 · Close

- **On screen:** The four-stage chain from S1, now complete and all lit: `Patient (voice) → Medic (verify) → Doctor (decide) → EHR (FHIR)`. Wordmark under it.
- **Action:** Each stage lights on its clause in the narration; hold on the finished chain.
- **Voice-over:** *The patient speaks. The system structures. A medic verifies. The doctor decides — and it becomes a medical record.*
- **Subtitle:** `The patient speaks · the system structures · a medic verifies · the doctor decides.`
- **Feature:** The closing statement, matching the one sentence at the top of this document.

---

## 4. Two honesty notes about the ordering you gave me

1. **"Explanation" sits at S13, not on the patient side.** You listed *risk/red-flag handling → explanation* inside the patient journey. In the built system the kiosk deliberately **never** shows a tier, a red flag, or a suggested condition — that is rules #2 and #3, and it is one of the better design decisions in this project. So S10 shows the risk work *happening* at submit and says out loud that the patient is not shown it, and the **explainable-AI reason** is shown where it actually lives: in front of the doctor, at S13. Nothing is skipped; it is placed where it is real. Say the word if you would rather I move it and I will re-cut S10.

2. **The patient-facing "explanation" is the read-back and the read-aloud summary.** S6 and S9 carry it: the system tells the patient what it understood, in their own words, and reads the whole summary aloud before anything is sent. That is the patient's version of "explain what is happening", and it is real.

---

## 5. Rules this script keeps

- Only features that exist in the repo today. Every scene above names the module, ADR or file it comes from.
- **No invented numbers.** No accuracy, WER, latency or "percent correct" claim appears anywhere — there is no formal WER/precision-recall evidence yet, so the video claims none.
- No API key, no `.env`, no OTP value, no source code on screen.
- Synthetic/consented data only — the patient in the video is a seeded case, not a real person.
- Nothing implies autonomous diagnosis or emergency dispatch. The system narrows; the doctor decides.
- Voice is shown as the default path in every patient scene; the pointer never touches a control during S4.

---

## 6. Production notes (for after approval)

**Runtime check.** 397 spoken words at a natural 145 wpm = 164 s of speech + 9 s of scene pauses = **2:53**, leaving 7 s under your 3:00 ceiling. Delivery pace is the only thing that can break the ceiling: at a slow 130 wpm the same words run 3:12, so if the recorded read comes back slower than 140 wpm I trim S1, S3 and S11 (the three scenes carrying no product feature) before anything else — that alone buys 20 s.

**Subtitles.** Burned into the video *and* delivered as a separate `.srt`, cue-split exactly as marked above (long scenes carry 2 cues), max ~12 words per cue.

**Two decisions I need from you** — asked separately, right after this document:
1. **How the patient's voice scenes get captured** (this decides how strong the "hands-free" proof is).
2. **Whose voice narrates** (I cannot reach a natural neural TTS service from this session — the hosts are blocked by the sandbox's egress policy — so the natural-voice options run through your machine or your own recording).
