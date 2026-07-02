# AI-Powered Voice Pre-Screening System — UI/UX Design

A four-portal clinical pre-screening product for Bangladeshi clinics. This document is **Part A — Design Specifications**. The clickable mockups for the priority screens are delivered separately as **Part B**.

> **Scope discipline:** Every design decision below is traceable to the background context in the brief. Where the brief left a choice open, the chosen interpretation is stated and tied to the relevant instruction. No additional roles, screens, data fields, or features have been invented.

---

## Shared design system

All four views share one visual language. Per-screen specs below state each screen's specific usage; this section defines the common tokens so the specs don't repeat them.

**Color**

| Token | Hex | Use |
|---|---|---|
| Primary blue | `#0B5CAD` | Buttons, active states, primary actions |
| Bright blue | `#2E86DE` | Listening/active voice state, focus rings, links |
| Blue tint surface | `#EAF2FB` | Selected rows, info surfaces, mic-orb halo |
| Page background | `#F6F9FC` | App background (clinician/admin views) |
| Card white | `#FFFFFF` | Cards, panels, kiosk background |
| Ink | `#1B2733` | Primary text (softer than pure black) |
| Muted ink | `#5A6B7B` | Secondary text, captions, labels |
| Hairline | `#E1E8EF` | Borders, dividers |

**Risk-tier colors** (semantic, deliberately high-contrast — used wherever risk is surfaced to a clinician):

| Tier | Text/badge | Tint background |
|---|---|---|
| Critical | `#D32F2F` | `#FDECEC` |
| High | `#E8710A` | `#FDF0E3` |
| Moderate | `#B07A00` | `#FBF4DE` |
| Low / Routine | `#2E7D52` | `#E7F4ED` |

**Provenance indicators** (used only in Medic + Doctor views; never shown to patients):

- **AI-extracted** — a small violet pill labelled `AI` (`#6D5BD0` on `#EFEBFB`). Means the value was auto-filled from the patient's voice and not yet touched by a human.
- **Human-edited** — a slate "edited" tag with a check (`#5A6B7B`), e.g. `Edited · Dr. Rahman`. Means a clinician changed or confirmed the value.

**Typography**

- **English UI:** Inter. Scale: Display 32/28, H1 24, H2 20, Body 16, Caption 13. Weights 400/500/600/700.
- **Bangla UI:** Hind Siliguri (fallback Noto Sans Bengali). Bangla glyphs run ~10–20% wider and taller, so every component below reserves vertical and horizontal slack and avoids fixed-height single-line containers for translatable strings.
- **Data / monitoring (Admin only):** IBM Plex Mono for IDs, counts, latencies and log rows — visually separates the operational view from clinical views.

**Bilingual toggle — global pattern**

A persistent segmented control `বাংলা | English` lives in the top-right of the header on **every** screen of all four portals. Tapping it re-renders all labels, instructions, and (on the Patient voice screen) the spoken question audio, with no layout shift. State persists for the session. The Patient login additionally surfaces the same toggle before sign-in so the patient picks their language first. (Brief: Rule 3, Rule 11; tone: "bilingual throughout.")

**Terminology rule (applies everywhere):** No `M1/M2`, no "ASR", "NER", "STT", "pipeline", or module numbers appear in any visible string. Stages are named by what they do in plain language. (Brief: Rule 9, terminology constraint.)

---

# Part A — Design Specifications

Organized by view: **Patient → Medic → Doctor → Admin**. Each view covers (a) login, (b) dashboard/home, (c) core task screen(s), (d) the Medical Problem Summary for that audience, (e) logout/session-end.

---

## 1. Patient View

Kiosk/tablet, public shared device, single session, voice-first. Calm and reassuring; large touch targets for anxious or elderly patients. Phone-number + OTP login. Auto-logout on completion so the next patient can start. (Brief: system_roles §1, authentication_flows, tone.)

> **OTP assumption (stated once):** The 6-digit code is delivered by a free-tier phone-verification service (e.g. Firebase phone-auth or Twilio Verify trial credits). The OTP screen is designed generically — phone entry → 6-digit entry → resend/timeout — and the verification provider sits behind an interface, swappable for production. (Brief: authentication_flows, Rule 10.)

### 1a. Patient — Phone & OTP Login

```
Screen: Patient — Phone & OTP Login
Audience: Patient
Language handling: Both. Toggle shown top-right AND offered prominently before sign-in so the
  patient sets their language first; choice carries into the whole session.
Layout: Tablet full-screen. Single centered card on a calm white field. Clinic name/logo placeholder
  top-center. Generous spacing, oversized inputs and buttons (min 56px touch height).
  Two sub-states on one screen:
    Step 1 — Phone entry: fixed "+880" prefix, one large numeric field, primary "Send code" button.
    Step 2 — Code entry: echoes "Code sent to +880 1712-•••678", six large segmented code boxes,
      a resend control with countdown ("Resend in 0:42"), primary "Verify" button, a "Change number" link.
Key components: Numeric keypad-friendly inputs, six-box OTP group with auto-advance, countdown timer,
  resend (disabled until timer ends), inline error line ("That code didn't match — try again"),
  language toggle.
Primary colors: White background, primary blue buttons, bright-blue focus ring on the active code box,
  muted-ink helper text. No red unless an input error is shown.
Typography: H1 question ("Enter your phone number" / Bangla) is the largest element; helper text caption-size.
Notes: Errors are instructive, never scolding (frontend voice). On successful verify → Patient dashboard.
  Single session begins here; no "remember me" on a shared device.
```

### 1b. Patient — Dashboard / Home

```
Screen: Patient — Dashboard / Home
Audience: Patient
Language handling: Both; persistent header toggle.
Layout: Tablet full-screen, single column, centered. A short reassuring welcome ("We'll ask a few
  questions about how you're feeling. You can speak normally — in Bangla, English, or mixed.") and
  one large primary action card: "Start" with a microphone glyph. Optional secondary line showing the
  patient's name/phone for confirmation.
Key components: One dominant "Start" button (full-width, tall), welcome text, language toggle,
  small privacy reassurance line ("Your answers are kept private and shared only with your doctor").
Primary colors: White, single primary-blue Start button, muted supporting text.
Typography: Welcome H1 large; reassurance caption-size.
Notes: Intentionally near-empty — one obvious next step. No menus or settings clutter on a kiosk.
  Tapping Start opens the Voice Interaction screen.
```

### 1c. Patient — Voice Interaction (core task)

```
Screen: Patient — Voice Interaction
Audience: Patient
Language handling: Both; persistent toggle top-right. The toggle also switches the language of the
  spoken question audio, not just on-screen labels.
Layout: Full-screen, single centered column, large touch-safe spacing. Vertical order, top to bottom:
  (1) progress indicator "Question 3 of about 6"; (2) the current question in the largest type on screen;
  (3) a central microphone orb that visibly changes by state; (4) a live/processed transcript area showing
  what the patient is saying; (5) a small, low-emphasis "Having trouble? Type instead" affordance.
Key components:
  - Mic orb with three explicit states: Listening (bright-blue, gentle pulsing rings), Processing
    (calm spinner / settling animation), Idle (neutral gray, before the patient starts).
  - Current question text (large), kept short and plain.
  - Live transcript area that fills in as the person speaks, then settles to the cleaned text.
  - Progress indicator (approximate count, "~6", because follow-ups are adaptive).
  - Fallback text input, revealed only after tapping "Having trouble? Type instead".
Primary colors: White background; primary/bright blue for the active listening orb and progress fill;
  neutral gray for the idle orb; ink for question and transcript text.
Typography: Question text is the single largest element. Transcript is secondary size and lighter weight.
Notes: No "Next" button while listening — the screen advances automatically when the patient finishes
  speaking. The fallback text box exists only for mic failure and stays hidden behind the "having trouble?"
  tap. State labels read in plain language ("Listening…", "One moment…"), never as engineering terms.
  (Brief: Rule 4, terminology constraint, Example 2.)
```

### 1d. Patient — Pre-Screening Summary (patient-formatted)

```
Screen: Patient — Pre-Screening Summary
Audience: Patient
Language handling: Both; persistent toggle. Fields render fully in the chosen language.
Layout: Tablet full-screen, single column, comfortable line length. Heading "Your pre-screening summary",
  one reassuring line ("Here's what we'll share with your doctor. Please check it's correct."), then the
  complete Medical Problem Summary — all 10 sections — in plain, friendly language with soft section icons.
  A calm "next step" banner sits at the top (see Notes). Two actions at the bottom: primary "This looks
  correct" and secondary "Something's wrong".
Key components: Read-only field cards (no edit controls, no provenance tags), a simple visual severity
  scale ("Pain level: 7 out of 10" as a labelled bar), a non-alarming next-step banner, confirm/decline
  actions. "Something's wrong" routes the patient to flag a problem to staff rather than free-editing
  clinical data on a public device.
Primary colors: White, primary-blue confirm button, muted supporting text. The next-step banner uses a
  calm blue (not red), regardless of internal risk tier.
Typography: Section labels H2; values body-size; reassurance text muted.
Notes — risk presentation: The patient sees their summary and a gentle, supportive next-step message
  tuned to urgency — e.g. for a high-urgency case: "Please stay here. A member of our care team will see
  you very soon." It does NOT show the red-flag list, the risk-tier label, or the AI reasoning, and it
  never states or implies a diagnosis. This follows two explicit constraints: tone ("never alarming even
  when displaying their own risk result — informative, not frightening") and the core principle "the AI
  never diagnoses." The full risk tier, red flags, and reasoning are surfaced to the Medic and Doctor
  instead. All 10 summary fields remain present and unaltered in content — only the styling is softened.
  (Brief: Rule 4, Rule 12, tone, risk_and_safety_design_note.)
```

The 10 sections, all present here in plain language: 1) Main problem · 2) When it started (start time + duration) · 3) Symptoms (main symptom, severity, location, character, what makes it worse, what makes it better) · 4) Associated symptoms · 5) Relevant medical history (existing diseases, recent procedures/tests, previous similar problem) · 6) Medicines currently taking · 7) Allergies · 8) Recent changes/exposures · 9) What has already been done · 10) Current concern/question.

### 1e. Patient — Session end / Auto-logout

```
Screen: Patient — Session End (auto-logout confirmation)
Audience: Patient
Language handling: Both; matches the language in use.
Layout: After the patient taps "This looks correct", a full-screen confirmation replaces the summary:
  a reassuring "Thank you" message, a one-line "Your information has been sent to the care team", and a
  visible auto-logout notice with a short countdown: "This session will close in 5 seconds so the next
  patient can begin." A single "Finish now" button lets the patient close immediately.
Key components: Confirmation message, auto-logout countdown, "Finish now" button.
Primary colors: White, calm blue, muted text. No alarming color.
Notes: On countdown end OR "Finish now", the session is destroyed and the device returns to the Patient
  phone-login screen, ready for the next patient. Single-session, public-device hygiene: nothing from the
  prior patient remains on screen. (Brief: system_roles §1, Rule 4.)
```

---

## 2. Pre-Screening / Medic View

Clinic staff who monitor completed pre-screenings and assign a doctor. Standard credentialed login (not OTP). Dense-but-organized and scannable. Two equal-priority access paths: a live queue **and** a manual phone-number lookup. Inline editing of any field with AI-vs-human indicators. (Brief: system_roles §2, authentication_flows, Rule 5, Rule 6.)

### 2a. Medic — Login

```
Screen: Medic — Staff Login
Audience: Clinic staff (Medic)
Language handling: Both; toggle top-right.
Layout: Desktop, centered card. Staff ID / email field, password field, "Sign in" button, "Forgot
  password" link. Explicitly the credentialed flow — no phone/OTP. Designed for fast repeat sign-in
  across a shift (autofocus on ID, Enter submits).
Key components: ID/email input, password input with show/hide, sign-in button, error line, language toggle.
Primary colors: White card on page-background, primary-blue sign-in button.
Typography: H1 "Staff sign in"; fields body-size.
Notes: Low-friction professional login; these users sign in repeatedly per shift. (Brief: Rule 10, authentication_flows.)
```

### 2b. Medic — Dashboard / Queue (core task) + Phone lookup

```
Screen: Medic — Dashboard / Queue
Audience: Medic
Language handling: Both; persistent header toggle.
Layout: Desktop. Left sidebar (Queue, Find patient, Assigned, Sign out). Header contains the global
  toggle, staff name, and — given equal-priority access — a always-visible phone-number lookup field
  ("Find patient by phone") sitting prominently in the header, not buried in a submenu. Main area is the
  live queue of patients who have completed pre-screening.
  A persistent Critical banner spans the top of the main area whenever any Critical-tier case is waiting.
Key components:
  - Persistent Critical banner (red) with count and quick jump, shown only when Critical cases exist.
  - Queue rows/cards: risk-tier badge (color at a glance), patient name + masked phone, one-line chief
    complaint, time completed, wait time, and an "Assign doctor" action. Critical rows pinned to top.
  - Header phone-lookup field (equal-priority path to the queue).
  - Sort/filter by risk and wait time.
Primary colors: Page-background app; white cards; risk-tier colors on badges; red persistent banner.
Typography: Chief complaint readable at a glance; metadata caption-size; risk badge bold.
Notes — two access paths: (1) the queue for triage of recent/pending cases, and (2) the header
  phone-lookup to pull any specific patient directly. Both are first-class and always reachable from this
  screen; entering a phone number jumps straight to that patient's detail view, the same destination a
  queue row opens. (Brief: Rule 5, risk_and_safety_design_note — Critical visible via persistent banner.)
```

### 2c / 2d. Medic — Patient Detail & Medical Problem Summary (medic-formatted)

```
Screen: Medic — Patient Detail (Medical Problem Summary + assign)
Audience: Medic
Language handling: Both; persistent toggle. Per-field language follows the global setting.
Layout: Desktop, two-region. Left/main: the complete Medical Problem Summary as independently
  expandable/collapsible sections (clickable accordions) — never one long static page. Right rail: a
  compact risk panel (tier badge + red-flag list) and the "Assign to doctor" panel (doctor dropdown +
  "Assign" button), which is the medic's core action. Header shows patient identity, masked phone, and the
  phone-lookup field to jump to another patient.
Key components:
  - Collapsible section cards for all 10 summary areas, each header showing the section name and a
    summary preview; expanding reveals the fields.
  - Per field: value + a provenance indicator — violet "AI" pill for auto-extracted, slate "Edited · [name]"
    for human-edited — plus a pencil edit icon enabling inline correction. Saving an edit flips that field's
    indicator to human-edited.
  - Right rail: risk-tier badge, red-flag list, and the assign-to-doctor control.
Primary colors: White cards; violet AI pills; slate edited tags; risk-tier colors in the right rail.
Typography: Section headers H2; field labels muted; values body. Clinical-shorthand-friendly density.
Notes: Every field from the summary is present and editable; only presentation is denser than the
  patient's. Collapsing/expanding lets staff scan fast and open only what they need. (Brief: Rule 6,
  Rule 12, data_model.)
```

### 2e. Medic — Logout / session

```
Screen: Medic — Sign out
Audience: Medic
Language handling: Both.
Layout: Standard "Sign out" in the sidebar; confirms then returns to the Medic login. Unlike the patient
  kiosk, no auto-logout-on-task — staff stay signed in across their shift until they sign out (or an
  inactivity timeout for a shared workstation).
Notes: Persistent professional session, in contrast to the single-session patient kiosk. (Brief: authentication_flows.)
```

---

## 3. Doctor View

Registered/verified doctors only. Credentialed login. Must be the fastest view to scan under time pressure — clickable/expandable sections, not a wall of text. Same summary format, plus a prominent, glanceable Risk + Red Flags + Explainable-AI panel. Same phone-lookup equal-priority path. Can validate, override, or annotate any field. (Brief: system_roles §3, Rule 5, Rule 6, Rule 7.)

### 3a. Doctor — Login

```
Screen: Doctor — Sign in
Audience: Verified doctor
Language handling: Both; toggle top-right.
Layout: Desktop centered card. Credentialed login (ID/email + password) — explicitly not OTP. Same
  low-friction repeat-sign-in pattern as the medic. Visually shares the staff-login design system.
Key components: ID/email, password with show/hide, sign-in button, error line, toggle.
Primary colors: White card, primary-blue sign-in.
Notes: For registered/verified doctors only; access control is upstream of this screen. (Brief: Rule 10.)
```

### 3b. Doctor — Dashboard / Queue (core task) + Phone lookup

```
Screen: Doctor — Dashboard / Queue
Audience: Doctor
Language handling: Both; persistent header toggle.
Layout: Desktop, tuned for the fastest possible scan. Left sidebar (My patients, Find patient, Sign out).
  Header has the toggle, doctor name, and the always-visible "Find patient by phone" field. Main area:
  the doctor's assigned cases as compact cards sorted by risk tier, then wait time. Persistent Critical
  banner across the top whenever a Critical case is assigned/waiting.
Key components:
  - Persistent Critical banner (red) with count and jump.
  - Compact case cards: large risk-tier badge, chief complaint, age/sex, wait time, and the single most
    important red flag previewed on the card; "Open" expands to the detail view.
  - Header phone-lookup (equal-priority path).
Primary colors: Page-background; white cards; risk-tier colors leading each card; red banner.
Typography: Risk badge and chief complaint largest on each card; metadata caption-size. Optimized for
  comprehension speed.
Notes: Same two access paths as the medic — assigned queue and direct phone-lookup, both first-class.
  Density favors glanceability over decoration. (Brief: Rule 5, Rule 7.)
```

### 3c / 3d. Doctor — Patient Detail with Risk / Red-Flag / XAI panel (doctor-formatted)

```
Screen: Doctor — Patient Detail (Risk + Red Flags + Explainable-AI, then full summary)
Audience: Doctor
Language handling: Both; persistent toggle; per-field follows global setting.
Layout: Desktop. The screen LEADS with a single prominent, glanceable panel pinned at the top —
  the most time-critical information, never buried:
    [ Risk tier badge ]  [ Red flags list ]  [ Why: plain-language explainable-AI reasoning ]
  Directly below, the complete Medical Problem Summary as independently expandable/collapsible cards
  (clickable), each field carrying its AI/human provenance indicator and inline controls to validate,
  override, or annotate. Header shows patient identity, masked phone, and the phone-lookup field.
Key components:
  - Top Risk/Red-Flag/XAI panel: bold risk-tier badge (e.g. Critical in red), an itemized red-flag list,
    and a short "why this tier" explanation in plain clinical language. A reference links a contributing
    value (e.g. a severe symptom) back to the red flag it triggered.
  - Collapsible summary cards for all 10 sections.
  - Per field: AI pill / human-edited tag + actions to Validate (confirm), Override (edit), or Annotate
    (add a note). Validating or overriding flips the field to human-edited and records the doctor.
Primary colors: White; the top panel uses the relevant risk-tier color prominently (red border/header
  for Critical); violet AI pills; slate edited tags.
Typography: The risk tier is among the largest elements on the screen; red-flag items bold; reasoning
  body-size and skimmable; summary fields clinical-dense.
Notes — risk model: This panel surfaces a Critical/red-flag case prominently for a human to act on; the
  system does not autonomously alert or escalate. The red-flag check is rule-based and folded into risk
  assessment — reflected here as a clearly itemized list with reasoning, not an "alarm". All 10 summary
  fields remain present and unaltered; the doctor can act on any of them. (Brief: Rule 6, Rule 7, Rule 12,
  risk_and_safety_design_note.)
```

### 3e. Doctor — Logout / session

```
Screen: Doctor — Sign out
Audience: Doctor
Language handling: Both.
Layout: Sidebar "Sign out" → confirm → Doctor login. Persistent professional session across the shift,
  with optional inactivity timeout on shared workstations. Not the patient auto-logout pattern.
Notes: Mirrors the medic session model. (Brief: authentication_flows.)
```

---

## 4. Admin / Management View

Backend/operations monitoring only. Confirms the system, data flow, and Patient → Medic → Doctor handoffs are running correctly. **Not** a clinical-decision interface — no patient clinical content. Standard authenticated login with elevated permissions. Neutral, operational dashboard tone. (Brief: system_roles §4, authentication_flows, Rule 8.)

### 4a. Admin — Login

```
Screen: Admin — Sign in
Audience: Operations / management
Language handling: Both; toggle top-right.
Layout: Desktop centered card, credentialed login with elevated permissions. Visually consistent with the
  staff-login system but distinct enough to signal management access (e.g. an "Operations" label).
Key components: ID/email, password with show/hide, sign-in, error line, toggle.
Primary colors: White card, primary-blue sign-in.
Notes: Elevated/management permissions; otherwise the standard credentialed pattern. (Brief: authentication_flows.)
```

### 4b / 4c. Admin — Monitoring Dashboard (core task)

```
Screen: Admin — System Monitoring Dashboard
Audience: Operations / management
Language handling: Both; persistent header toggle. (Stage names below are plain-language, never module
  terms.)
Layout: Desktop. Left sidebar (Overview, Handoffs, Errors, Users, Sign out). Header: toggle, admin name,
  overall system-status pill (Operational / Degraded / Down). Main area, top to bottom:
    (1) Status tiles: System status, Active sessions now, Average processing time, Failed voice captures
        today, Cases completed today, Queue throughput (per hour).
    (2) Handoff health: a left-to-right view of the journey — "Check-in & voice capture" →
        "Summary preparation" → "Staff review" → "Doctor handoff" — each stage showing a healthy/degraded
        status and a current count, so a stuck stage is obvious.
    (3) Error / failure log table: timestamp, area, short message, status (mono font).
    (4) Active users / accounts summary with a link to user management.
Key components: Metric tiles, a horizontal handoff-status strip, an error-log table, a users summary.
  Status uses semantic colors: green Operational, amber Degraded, red Down/failed.
Primary colors: Page-background; white tiles; semantic status colors; IBM Plex Mono for numbers, IDs,
  latencies, and log rows to distinguish the operational view from clinical views.
Typography: Metric numbers large and monospaced; labels caption-size; log rows mono.
Notes — strictly operational: System health, throughput, failed transcriptions, active users, error logs
  only. No clinical decision content, no patient summaries, no risk tiers for decision-making. Stage names
  are plain operational language with no module numbering or engineering pipeline terms. (Brief: Rule 8,
  Rule 9.)
```

### 4d. Admin — (no clinical summary)

The Medical Problem Summary intentionally does **not** appear in the Admin view. Admin is monitoring-only; surfacing patient clinical content here would contradict its stated purpose. (Brief: system_roles §4, Rule 8.) This omission is deliberate, not an oversight.

### 4e. Admin — Logout / session

```
Screen: Admin — Sign out
Audience: Operations / management
Layout: Sidebar "Sign out" → confirm → Admin login. Persistent professional session with inactivity
  timeout appropriate to elevated permissions.
Notes: Standard credentialed session model. (Brief: authentication_flows.)
```

---

## Coverage check

| View | Login | Dashboard | Core task | Summary (audience-formatted) | Logout |
|---|---|---|---|---|---|
| Patient | 1a | 1b | 1c voice | 1d (plain, no provenance, calm risk) | 1e auto-logout |
| Medic | 2a | 2b + lookup | 2b assign / 2c edit | 2c/2d (dense, editable, AI/human tags) | 2e |
| Doctor | 3a | 3b + lookup | 3c review | 3c/3d (expandable, XAI panel, editable) | 3e |
| Admin | 4a | 4b | 4b monitoring | — intentionally none (4d) | 4e |

All 10 Medical Problem Summary fields are preserved in every place the summary appears (Patient 1d, Medic 2c/2d, Doctor 3c/3d) — only presentation density and styling change per audience. No internal module numbering or engineering/pipeline terminology appears in any user-facing string. (Brief: Repeat Critical Instruction, Rule 9, Rule 12.)
