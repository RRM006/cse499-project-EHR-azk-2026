# Niramoy — Speaker Script (≈10 minutes)

> Natural, first-person, engineer-to-engineers. Say it in your own words — these are your talking points, not a teleprompter. Where you see **[pause]**, let the slide land. Times are approximate.

---

## Slide 1 — Title (≈40s)

"Hi, I'm [Your Name]. I'm going to walk you through **Niramoy** — a voice-first medical pre-screening system I designed and built for clinics in Bangladesh.

The one-line version: a patient speaks naturally, in their own language, **before** they see the doctor — and the doctor gets a clear, structured, safety-checked summary waiting for them.

I built this end to end, so I'm happy to go as deep as you want on any part. Let me start with the problem, because the whole design comes out of it." **[pause]**

---

## Slide 2 — The problem (≈45s)

"If you've been in a busy clinic in Bangladesh, you know the reality: doctors see huge volumes, and a consultation can be two or three minutes. History-taking gets compressed, and things get missed before the exam even starts.

The second problem is the patient. Elderly, low-literacy, or anxious patients can't organise their own history the way a form wants — symptoms, duration, severity, past conditions.

And third — language. Real patients speak **Bangla, Banglish, and regional dialects**. Most digital tools assume typing, or English. So the people who most need help are exactly the ones the tools leave out. That's the gap I wanted to close."

---

## Slide 3 — The core idea (≈40s)

"My core idea was simple: **let people just speak.**

Niramoy is voice-first and hands-free. The patient talks; the system listens, asks what's missing, and turns it into structure — all before the doctor walks in.

Voice is the default here, not a bonus feature. Typing is always available as a fallback, but speaking leads — because that's what works for an elderly patient who can't type Bangla medical terms. This is the real patient screen you're looking at."

---

## Slide 4 — What I built (≈45s)

"What I actually built is one system with three role-specific portals, all on a single FastAPI backend and one database.

The **patient portal** is the voice-first intake. The **medic desk** is a triage queue — the medic verifies what the AI extracted against the patient's own words, and records vitals. The **doctor portal** leads with safety — risk, red flags, the AI's reasoning — and then lets the doctor review and prescribe.

I gave each role its own portal deliberately, instead of one app pretending to serve everyone — because a triage nurse and a physician need very different things."

---

## Slide 5 — End-to-end flow (≈60s)

"Here's the whole pipeline, left to right. The patient speaks. That speech is stored as a **raw transcript that is never changed**. Then a separate stage cleans and extracts it into ten structured fields. A follow-up loop asks only about the gaps. Then risk assessment runs, with red-flag detection and an explanation. Finally the doctor gets a report and writes to the EHR.

The most important thing on this slide is the dark bar: **the patient's exact words are captured once and never edited.** Cleaning, correction, and AI interpretation all happen in separate, later stages, stored in separate fields. That's the first rule of the system, and I enforce it in code and in tests — because if the machine is ever unsure, the human still has the ground truth of what was said."

---

## Slide 6 — Voice-first interaction (≈60s)

"Let me be precise about the voice interaction, because it's the heart of the product.

The assistant asks a question — spoken and on screen. The mic then **opens itself**, with an echo guard so the AI's own voice never gets transcribed into the patient's record. The patient just talks. When they pause, a visible **three-two-one** window appears — and if they start speaking again, it cancels. A clipped answer would violate my raw-words rule, so that countdown is a *confirmation*, never a hard cut-off.

I'll be honest about the boundary: the happy-path hands-free loop is built. The final robustness — automatically re-prompting on total silence, recovering a dropped mic permission — is the next hardening step I've scoped but not finished. And typing is always one tap away, running through the exact same pipeline."

---

## Slide 7 — The Bangla challenge (≈50s)

"I'm not going to pretend Bangla speech recognition is solved — it isn't, for anyone. Code-switching between Bangla and English mid-sentence breaks most recognisers. Regional dialects like Sylheti and Chittagonian differ sharply from standard Bangla. Medical terms and drug names are out-of-vocabulary. And clinics are noisy.

That uncertainty is *exactly why* the architecture's first rule is that raw words are never altered. On the right is a real case — the patient's own Bangla words, stored verbatim, in front of the doctor. The doctor can always check the AI's interpretation against what was actually said."

---

## Slide 8 — The AI / LLM pipeline (≈55s)

"Under the hood, the AI is a pipeline, not one magic call. It corrects the text, extracts the clinical entities, finds the gaps, generates follow-ups, and summarises into ten doctor-ready fields.

The key engineering decision is that **every AI task goes through one swappable, OpenAI-compatible client.** That single seam is deliberate: the next requirement is to drop in a local, quantized model that runs on the clinic's own machine — and because of this design, that's a configuration change, not a rewrite. On the right is the real extracted profile the staff verify."

---

## Slide 9 — Safety & integrity (≈50s)

"Safety here is a design stance, not a feature I bolted on. Four decisions.

One: it **never diagnoses**. It narrows what's worth considering; the doctor decides. Two: red flags are a **rule** that runs *independently* of the AI — so if a patient says 'chest pain,' it forces a Critical tier even on a bad model day. Three: **no invented numeric score** — risk is a tier with reasons, not a false-precision percentage. Four: every risk carries a plain-language explanation.

The strip at the bottom is a real Critical case: the red-flag rule fired on chest pain, forced Critical, and the explanation says exactly why."

---

## Slide 10 — Resilience (≈55s)

"This is my favourite real-engineering story. Niramoy runs on free AI tiers — by necessity, because it's for low-resource clinics. But free tiers hit daily limits, and their models get retired without notice.

So the one LLM client fails over across three multiplying dimensions: **providers, then keys, then models.**

And it isn't theoretical. The night before a demo, my live chain went down — one model had been decommissioned upstream, another was rate-limited. That outage taught me the failure mode, and I re-architected the fallback into these three dimensions so a single dead provider can never again stop a patient mid-intake."

---

## Slide 11 — Demo (≈75s, play the video)

"Rather than describe it, let me show you one real run." **[play the walkthrough video]**

*(Let it play. If you narrate live, keep it light:)* "The patient speaks, hands-free… the medic sees it triaged by urgency and checks the AI's fields against the raw words… and the doctor sees the safety story first — Critical, the red flag, the reasoning — before writing a prescription where the diagnosis is theirs, never the AI's."

---

## Slide 12 — Current state (≈45s)

"Here's what actually works today, and I want to be honest about both halves.

Fourteen of fifteen modules are built. Around 1,196 automated tests pass. Eighteen database tables, fourteen migrations. Three working portals. Real OTP, and EHR export as Word, PDF — with correctly-shaped Bangla — and an HL7 FHIR bundle.

And the honest half: I have **not** measured formal word-error-rate yet. A live real-mic run passed and the transcription felt accurate, but I won't quote a number I haven't recorded. Live speech-to-text is still browser-based and cloud-dependent, and staff login is stubbed."

---

## Slide 13 — Limits → Future (≈55s)

"I pair every limit with where it goes. Today, cloud STT sends audio to Google; free-tier models mean I only use synthetic or consented data; auth is stubbed; it's single-node SQLite; and I haven't finished fully-automatic endpointing.

The headline of the roadmap is **on-device**: a local quantized speech model and a local summary model, so nothing leaves the machine. That turns my biggest privacy limitation into the biggest future strength — and it's exactly what that one swappable client was designed to allow. After that: finish the hands-free loop, add real auth and Postgres and encryption, and run a formal accuracy evaluation."

---

## Slide 14 — How I built it + close (≈45s)

"Last thing — how I built it, because I want to be straight with you.

I used AI coding assistance to move fast. And I made every decision that mattered. I chose the architecture, the stack, and the non-negotiable rules. I debugged the real defects myself — including a nasty one where a CSS transform was silently moving a button out from under the cursor, and a timezone bug that dated prescriptions to the wrong day. I curated the decision records and the test suite, and I ran the live tests. **I know where every part of this system lives, what it does, and why it's there.**

The one line I'd leave you with: Niramoy meets patients in their own language, by voice, hands-free — and hands the doctor structure, safely. And the next step is on-device, offline, and fully hands-free.

Thank you — I'd love to go deep on any part of it."

---

### Delivery notes
- **Pace:** ~130 words/min is calm and clear. Don't rush slides 5, 6, 9, 10 — they carry the engineering.
- **If time is short:** the safe cuts are slides 2→3 (merge the problem into one breath) and 13 (state one limit, one future). Never cut slides 5, 6, 9, 10, or the demo.
- **Confidence line to remember:** when asked how much you built vs. AI — "I directed the build and I own the system. Ask me anything about it." Then answer specifically.
- **Honesty is a feature:** the WER caveat and the "S5 not finished" admission make everything else you say more credible. Lead with them, don't hide them.
