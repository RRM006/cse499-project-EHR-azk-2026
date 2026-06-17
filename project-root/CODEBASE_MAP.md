# CODEBASE MAP

> A living description of the repo's folder/file structure, so a new
> session doesn't have to re-explore everything from scratch. Update this
> when structure changes meaningfully (new module folder, new service,
> restructuring) — not on every single file edit.

---

## Current structure

```
project-root/
├── PROJECT_CONTEXT.md      # Stable architecture/rules reference
├── SESSION_PROTOCOL.md     # Start/end-of-session checklist
├── MILESTONE_LOG.md        # Status of all 15 modules
├── CURRENT_TASK.md         # What we're doing right now
├── CHATLOG.md              # Session-by-session history
├── TEST_LOG.md             # Test results per module
├── DECISIONS.md            # Architecture decision records
├── CODEBASE_MAP.md         # This file
├── voice-medical-prescreener/ # Main project source code directory
└── docs/
    └── full_spec.md        # Original full project brief (verbatim)
```

*(No source code yet — project is in planning stage. This will fill in as
modules are scaffolded. Suggested future shape below — adjust once real
stack decisions are logged in DECISIONS.md.)*

---

## Suggested future shape (not yet built — for reference only)

```
project-root/
├── modules/
│   ├── 01_speech_to_text/
│   ├── 02_text_normalization/
│   ├── 03_information_extraction/
│   ├── 04_clinical_summary/
│   ├── 05_emergency_detection/
│   ├── 06_missing_info_analysis/
│   ├── 07_followup_questions/
│   ├── 08_response_processing/
│   ├── 09_completion_check/
│   ├── 10_risk_assessment/
│   ├── 11_xai/
│   ├── 12_report_generation/
│   ├── 13_ehr_database/
│   ├── 14_dashboard/
│   └── 15_feedback_loop/
├── tests/              # mirrors modules/ structure
├── data/               # eval sets, sample audio, etc. (gitignore raw patient data!)
└── docs/
```

Each module folder, once started, should get its own short `README.md`
stating: inputs, outputs, and the contract it expects from upstream/
downstream modules (e.g. "Module 3 outputs a JSON object with these exact
keys, which Module 4 and Module 5 both consume").
