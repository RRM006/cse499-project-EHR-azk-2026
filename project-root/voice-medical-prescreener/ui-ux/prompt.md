# AI Prompt — UI/UX Design for AI-Powered Medical Pre-Screening System

---

## 1. ROLE & TASK DESCRIPTION

You are a senior Product/UX Designer specializing in clinical and healthcare software for emerging markets. Your task is to design the complete UI/UX for a four-portal AI-powered voice-based medical pre-screening system used in Bangladesh — first producing detailed design specifications for each screen, then producing text/HTML mockups of the key screens based on those specs.

---

## 2. BACKGROUND CONTEXT

<context>
<project_summary>
This is a clinical pre-screening system used in Bangladeshi clinics. Before seeing a doctor, a patient sits at a kiosk/tablet and speaks naturally in Bangla, Banglish, or a regional dialect to describe symptoms and history. The system transcribes the speech, extracts clinical information, asks spoken+on-screen follow-up questions to fill gaps (patient replies by voice only), assesses risk, and produces a structured pre-screening report before the doctor enters the room. All data is stored in an encrypted EHR-integrated database. Doctor feedback is used to improve the system over time. The AI never diagnoses — it narrows the search space; the doctor decides.
</project_summary>

<system_roles>
There are four distinct portals, each with its own login:

1. **Patient View** (kiosk/tablet, public/shared device, single-session)
   - Login: phone number only → OTP verification → dashboard opens.
   - Bangla/English language toggle required throughout.
   - Voice-only interaction for describing symptoms and answering follow-up questions (a manual text box exists only as a fallback for mic failure).
   - After the patient confirms the pre-screening summary is complete and correct, the session auto-logs-out so the next patient can use the same device.
   - Patient can view their own completed Medical Problem Summary at the end.

2. **Pre-Screening / Medic View** (clinic staff who monitor incoming cases and assign a doctor)
   - Login: standard staff login (credentials), separate from patient login.
   - Bangla/English toggle.
   - Sees a dashboard/queue of patients who have completed pre-screening, with risk level visible at a glance.
   - Can open a patient's full Medical Problem Summary, review/edit auto-filled fields, and assign the case to a specific doctor.
   - Equal-priority access pattern: (a) a live dashboard list of recent/pending cases, and (b) a manual phone-number lookup to pull up any specific patient's profile directly.

3. **Doctor View** (registered/verified doctors only)
   - Login: standard credentialed login (not OTP), separate from patient login.
   - Bangla/English toggle.
   - Must be the easiest, fastest view to scan under time pressure — clickable/expandable sections, not a wall of text.
   - Sees the same Medical Problem Summary format, plus Risk Level, Explainable-AI reasoning, and Red Flags prominently surfaced.
   - Can also look up a patient directly by phone number (same equal-priority pattern as Medic).
   - Can validate, override, or annotate any auto-filled field.

4. **Admin / Management View** (backend/operations)
   - Purely a monitoring view — confirms the system, data pipeline, and handoffs between Patient → Medic → Doctor are running correctly and smoothly.
   - Not a clinical-decision interface. Think system health, queue throughput, error/failure monitoring, user/account management.

All four views are part of one coherent product and should share a visual design system, but each has a distinct information priority and interaction pattern as described above.
</system_roles>

<data_model>
Every completed patient pre-screening produces a structured "Medical Problem Summary" with these fields (must support full Bangla and English, both as a UI toggle and potentially per-field):

1. Main problem (one-sentence chief complaint)
2. When it started — Start date/time, Duration (hours/days/weeks/months)
3. Symptoms — Main symptom, Severity (mild/moderate/severe or 1–10), Location, Character (sharp/dull/burning/pressure-like/throbbing), What makes it worse, What makes it better
4. Associated symptoms (fever, vomiting, shortness of breath, weakness, vision change, dizziness, swelling, bleeding, cough, etc.)
5. Relevant medical history — Existing diseases, Recent procedures/tests, Previous similar problem (yes/no + details)
6. Medicines currently taking (with dose if known)
7. Allergies (drug/food, or "No known allergy")
8. Recent changes/exposures (new medicine, infection, travel, injury, unusual food, chemical exposure, sick contact, heavy exercise)
9. What has already been done (medicines tried, doctor visit, test results, home treatment, response)
10. Current concern/question (what the patient wants the doctor to decide: diagnosis, urgent care, medicine change, test, follow-up advice)

Fields are auto-filled by the AI pipeline from the patient's voice answers. Medic and Doctor views must allow inline editing/correction of any field, with a clear visual indicator distinguishing "AI-extracted" vs "human-edited" values. This same summary (plus Risk Level + Red Flags + XAI explanation) is what Patient, Medic, and Doctor all view after pre-screening is complete — same underlying data, three different presentation layers suited to each audience.
</data_model>

<risk_and_safety_design_note>
There is no standalone "Emergency Detection" step in the flow. Red-flag/life-threatening symptom detection is a rule-based check folded into the Risk Assessment stage, which can force a case into a "Critical" tier. The system does not perform autonomous emergency escalation — it only surfaces Critical-tier cases prominently to the Medic and Doctor views so a human acts on them. Design should reflect this: Critical/Red Flag indicators must be highly visible (color, placement, persistent banner) on Medic and Doctor dashboards, but the system itself does not "alert" or "escalate" autonomously.
</risk_and_safety_design_note>

<authentication_flows>
- Patient: enters phone number → receives OTP via a free-tier OTP service (e.g., Firebase Authentication phone-auth free tier, or Twilio Verify trial credits) → enters OTP → dashboard. Design should describe this as the assumed OTP method for the prototype/demo stage, with a note that it is swappable behind an interface for production. Single-session, auto-logout on completion, device immediately ready for the next patient.
- Medic / Doctor: standard authenticated login (e.g., email/ID + password, or staff credential system) — explicitly NOT the OTP flow. Should be designed as a fast, low-friction professional login since these users log in repeatedly per shift.
- Admin: standard authenticated login with elevated/management permissions.
</authentication_flows>

<terminology_constraint>
Do not use internal module labels such as "M1," "M2," "Speech-to-Text (ASR)," "NER," or similar engineering/pipeline terminology anywhere in the UI design, copy, or screen labels. All user-facing language must read as professional, modern clinical product language (e.g., "Tell us how you're feeling," "Reviewing your answers," "Pre-Screening Summary," not pipeline/module names).
</terminology_constraint>
</context>

---

## 3. TONE & STYLE

<tone>
- Overall product tone: **professional, modern, clinical, trustworthy** — comparable to clean clinical health apps (e.g., Mayo Clinic-style apps): predominantly white space, blue accent palette, clear typographic hierarchy, minimal visual clutter.
- Patient-facing screens: calm, reassuring, plain-language, large touch targets (kiosk/tablet use, possibly by anxious or elderly patients), never alarming even when displaying their own risk result — informative, not frightening.
- Medic/Doctor-facing screens: dense-but-organized, scannable, clinical-shorthand-friendly, optimized for speed of comprehension under time pressure. Clickable/expandable sections rather than long scrolling text blocks.
- Admin view: neutral, operational, dashboard/monitoring tone — status indicators, not clinical content.
- Bilingual throughout: every patient-facing and clinician-facing screen must support a Bangla/English toggle without breaking layout (Bangla text strings are often longer — design must accommodate text-length variance).
- Avoid: playful/casual tone, gamification visuals, dark/edgy styling, dense jargon walls, any pipeline/engineering terminology in visible copy.
</tone>

---

## 4. DETAILED INSTRUCTIONS & RULES

<rules>
1. Produce the output in two clearly separated parts, in this order: **(A) Design Specifications** for every screen/state listed below, then **(B) Mockups** (text-based wireframe layout or HTML/CSS mockup, your choice of format, clearly labeled per screen) for the most important screens only (do not mock up every single state — prioritize: Patient OTP login, Patient voice-interaction screen, Patient final summary screen, Medic dashboard/queue, Medic patient detail view, Doctor dashboard, Doctor patient detail view with Risk/Red-Flag/XAI panel, Admin monitoring dashboard).
2. For each of the four views, explicitly design and describe: (a) login/authentication screen, (b) primary dashboard/home screen, (c) core task screen(s) specific to that role, (d) the Medical Problem Summary view formatted for that role's audience, (e) logout/session-end behavior.
3. Every screen must specify: layout structure, primary color usage, typography hierarchy, key components/widgets used, and how the Bangla/English toggle is presented and behaves.
4. For the Patient view: explicitly describe the voice-interaction screen (how listening/recording state, the question being asked, and the live or processed transcript are shown), and the auto-logout confirmation step after the patient confirms their summary.
5. For the Medic and Doctor views: explicitly describe both access paths — the dashboard/queue list AND the manual phone-number lookup — and how a user moves between them.
6. For the Medic and Doctor Medical Problem Summary screens: visually distinguish AI-auto-filled fields from human-edited fields (e.g., icon, color tag, or label), and make every section independently expandable/collapsible ("clickable") rather than one long static page.
7. For the Doctor view specifically: design the Risk Level, Red Flags, and Explainable-AI reasoning as a single prominent, glanceable panel — this is the most time-critical information on the screen and must not be buried.
8. For the Admin view: focus only on system health/monitoring concerns (e.g., pipeline status, queue throughput, failed transcriptions, active users, error logs) — do not include clinical decision-making content here.
9. Do not use any internal module numbering or engineering pipeline terms (no "M1," "M2," "ASR," "NER," etc.) anywhere in screen copy, labels, or component names. Use plain clinical-product language instead.
10. Treat the OTP step for the Patient login as using a free-tier phone-verification service (e.g., Firebase Authentication phone-auth or Twilio Verify trial) — mention this assumption once in the specs, and design the OTP screen generically (phone entry → 6-digit code entry → resend/timeout state) without hard-coding a specific vendor's UI.
11. Make explicit, for every screen, which language (Bangla, English, or both) is shown and how switching is triggered (e.g., persistent toggle in header vs. a settings choice at login).
12. Keep the full Medical Problem Summary field list (Section 2/background context) intact and complete in every place it appears (Patient summary, Medic detail view, Doctor detail view) — do not drop or rename fields, only change presentation density/style per audience.
</rules>

---

## 5. EXAMPLES

<examples>
**Example 1 — Input → Output behavior for a single field across audiences**

Input data: `Severity: 7/10`, `auto-extracted from voice answer, not edited`

- Patient-facing summary screen output: a simple visual scale (e.g., "Pain level: 7 out of 10" shown as a labeled slider/bar, no edit controls, plain reassuring language).
- Medic detail view output: the value shown inline in a compact summary row, with a small "AI" tag/icon indicating it was auto-extracted, and a pencil/edit icon allowing correction.
- Doctor detail view output: same value, shown inside an expandable "Symptoms" card, with the AI tag, edit icon, and — if this severity contributed to a Critical risk tier — a visual link/reference into the Red Flags panel.

**Example 2 — Screen spec format (use this structure for every screen in Part A)**

```
Screen: Patient — Voice Interaction Screen
Audience: Patient
Language handling: Persistent toggle (top-right), affects all labels and TTS question audio
Layout: Full-screen, centered single-column, large touch-safe spacing
Key components: Mic state indicator (listening/processing/idle), current question text (large type), 
  live/processed transcript area, progress indicator ("Question 3 of ~6"), fallback text-input icon
Primary colors: White background, primary blue for active/listening state, neutral gray for idle
Typography: Question text largest element on screen; transcript text secondary size
Notes: No "Next" button while listening — advances automatically when patient finishes speaking; 
  fallback text box appears only after a tap on a small "having trouble?" affordance
```
</examples>

---

## 6. HALLUCINATION PREVENTION

If you are not sure about any detail, say "I don't know" rather than inventing it. Only state design decisions you are confident are consistent with the background context provided above. If you need to reference a specific instruction from the background context to justify a design choice, identify the relevant instruction first, then base your design decision on it. Do not invent additional system roles, screens, data fields, or product features beyond what is described in the Background Context above.

---

## 7. OUTPUT FORMAT

<output_format>
Structure the full response as:

**Part A — Design Specifications**
- Organized by view (Patient → Medic → Doctor → Admin)
- Within each view, one spec block per screen using the format shown in Example 2 above
- Use headings (##/###) per view and per screen, not a single unbroken paragraph

**Part B — Mockups**
- One mockup per prioritized screen (see Rule 1 for the list)
- Each mockup clearly labeled with the screen name and audience
- Use either a structured text/ASCII wireframe layout or a minimal HTML/CSS block per screen — pick one format and use it consistently across all mockups
- Bangla and English label examples should be shown side-by-side or toggled where relevant, not omitted

Do not output JSON. Do not omit any of the four views. Do not collapse Part A and Part B together — keep them as two clearly separated sections.
</output_format>

---

## 8. REPEAT CRITICAL INSTRUCTION

**The single most important rule: every screen and every field from the Medical Problem Summary must remain complete and unaltered in content across all three audiences (Patient, Medic, Doctor) — only presentation density and styling may change per audience — and no internal module numbering or engineering/pipeline terminology (M1, M2, ASR, NER, etc.) may appear anywhere in user-facing copy.**
