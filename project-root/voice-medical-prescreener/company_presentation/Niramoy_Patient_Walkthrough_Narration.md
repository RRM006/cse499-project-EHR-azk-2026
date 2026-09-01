# Niramoy — Patient-Focused Walkthrough: Narration Script

**Use:** this is the exact voice-over in the video (already recorded into the .mp4, with matching burned-in subtitles + a separate .srt). To present in your own voice, read these lines over the muted video — each block is timed to the on-screen action.

**Voice:** first person, calm, unhurried — you are the engineer showing your own system. The patient section is most of the video; let it breathe.

**Runtime:** ~2 min 47 sec.

---

## OPENING

**[0:00] (title card)**
> This is Niramoy — a voice-first medical pre-screening system I designed and built for clinics in Bangladesh. Most of this walkthrough is the part that matters most: what the patient actually experiences, in their own voice.

## PART 1 — THE PATIENT (the main story)

**[0:14] (phone sign-in screen)**
> The patient starts here. No app to download, and no account to create — they just enter their phone number to begin.

**[0:21] (one-time code screen)**
> They get a one-time code and enter it once. And like everything else here, if they prefer, they can simply speak the digits out loud.

**[0:29] (assistant asks aloud, mic open (hands-free))**
> Now the heart of the system. The assistant asks its first question out loud, shows it on screen, and the microphone opens by itself — nothing to tap. This is what voice-first means: the system comes to the patient. Many of these patients are elderly, cannot read comfortably, or have never used an app.

**[0:47] (patient answer — Banglish)**
> The patient answers naturally — in Bangla, in Banglish, or a regional dialect, however they really speak. Voice is the primary path; I am typing here only to demonstrate. Either way, their words are captured.

**[0:59] (read-back: exact words preserved)**
> The system reads the answer back and stores it exactly as spoken — never edited, never cleaned. That is the first rule I built the whole system around: the raw words are permanent. Any interpretation happens later, as a separate step.

**[1:13] (follow-up question + conversation thread)**
> Then it asks follow-up questions — spoken and on screen — to cover what a doctor would want to know. The patient answers each one by voice, and the conversation builds up one question at a time.

**[1:24] (structured summary review)**
> When they are done, everything they said is organized into a clear, structured summary — and read back to them, so even a patient who cannot read the screen can still review their own pre-screening before it is sent.

**[1:37] (Submitted — Thank You)**
> They confirm, and submit. Behind the scenes the system assesses risk and checks for red flags — but the patient is never shown a diagnosis or a frightening label. That safety result is prepared for the doctor. For the patient, the visit is simply done.

## AFTER THE PATIENT (brief)

**[1:51] (transition card)**
> That is the patient's entire experience. Here, briefly, is what happens with what they submitted.

**[1:58] (medic verifies vs raw words)**
> It reaches a medic first, who checks the AI's structured summary against the patient's exact words — a person always confirms what the machine understood — and records vitals.

**[2:09] (doctor safety panel — red flag)**
> Then the doctor, who leads with safety: the risk level, a red flag on chest pain, and a plain-language reason. That red-flag rule runs independently of the AI, so a real emergency cannot be missed even if the model is wrong.

**[2:24] (Accept & Write to EHR (FHIR))**
> The doctor makes the decision and accepts the case into the record as a structured E-H-R document — an HL7 FHIR bundle. The diagnosis and the prescription are always the doctor's own; the system never diagnoses.

## CLOSING

**[2:37] (closing card)**
> That is Niramoy. The patient speaks, in their own language, hands-free; the system structures and safety-checks; and the doctor decides. Built around the patient's voice.

---

### One-line summary
**Patient speaks naturally → AI structures → Medic verifies → Doctor decides → structured EHR output.** The patient side is the heart of the video; the rest is deliberately brief.