# MILESTONE LOG

> Big-picture status of all 15 modules. Update the relevant row whenever a
> module changes status. Keep "Definition of Done" specific and testable —
> not "works well" but "WER < X% on Y test set" / "extracts all 6 entity
> types with >Y% F1 on Z sample size."

**Status legend:** 🔲 Not started · 🟡 In progress · 🟢 Done · 🔴 Blocked

---

| # | Module | Status | Definition of Done | Date Done | Notes |
|---|---|---|---|---|---|
| 1 | Speech-to-Text | 🔲 | TBD | — | |
| 2 | Text Processing & Normalization | 🔲 | TBD | — | |
| 3 | Information Extraction | 🔲 | TBD | — | |
| 4 | Initial Clinical Summary | 🔲 | TBD | — | |
| 5 | Emergency Detection | 🔲 | TBD | — | |
| 6 | Missing Information Analysis | 🔲 | TBD | — | |
| 7 | Follow-up Question Generation | 🔲 | TBD | — | |
| 8 | Response Processing & Profile Update | 🔲 | TBD | — | |
| 9 | Case Completion Check | 🔲 | TBD | — | |
| 10 | Risk Assessment Engine | 🔲 | TBD | — | |
| 11 | Explainable AI (XAI) | 🔲 | TBD | — | |
| 12 | Structured Clinical Report | 🔲 | TBD | — | |
| 13 | EHR Database | 🔲 | TBD | — | |
| 14 | Doctor Dashboard | 🔲 | TBD | — | |
| 15 | Feedback & Continuous Learning | 🔲 | TBD | — | |

---

## Phase grouping (suggested build order)

Since modules 13/14 are infrastructure most other modules depend on, and
9/6/7/8 form a loop that's easiest to test once 1-3 are stable, a reasonable
phase order is:

**Phase 0 — Skeleton:** minimal Module 13 (DB schema) + Module 14 (dashboard
shell) so later modules have somewhere to write to / display from.

**Phase 1 — Core pipeline (linear):** Modules 1 → 2 → 3 → 4.

**Phase 2 — Safety-critical:** Module 5 (emergency detection) — get this
solid early, not last.

**Phase 3 — Gap-filling loop:** Modules 6 → 7 → 8 → 9.

**Phase 4 — Assessment & reporting:** Modules 10 → 11 → 12.

**Phase 5 — Integration:** Wire everything into 13/14 properly.

**Phase 6 — Feedback loop:** Module 15.

*(Edit this if your supervisor or timeline dictates a different order —
e.g. many capstones front-load Module 1 STT since it's the most
research-heavy / riskiest part to get working on Bangla.)*

---

## Overall project status snapshot

**Last updated:** _(fill in date)_
**Current phase:** Planning / Phase 0
**Blockers:** none yet
**Next milestone target:** _(fill in)_
