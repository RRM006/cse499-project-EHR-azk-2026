# TEST LOG

> Tracks what was tested, how, and the result — for every module. For an
> ML/NLP pipeline, "it runs without crashing" is not a passing test. Define
> a real metric per module before you start, then log every run against it
> here, including failed/bad runs. Failed runs are useful history — don't
> delete them, mark them and move on.

---

## Suggested metric per module (fill in / adjust as you go)

| Module | Suggested metric | Target (set your own) |
|---|---|---|
| 1. STT | Word Error Rate (WER) on Bangla/Banglish test set | TBD |
| 2. Text Normalization | % of known errors correctly normalized (manual spot check) | TBD |
| 3. Information Extraction | Entity-level Precision/Recall/F1 (symptoms, duration, etc.) | TBD |
| 4. Clinical Summary | Human rubric score (clarity, completeness) — qualitative | TBD |
| 5. Emergency Detection | Recall on red-flag cases (false negatives are the dangerous failure) | Target: very high recall, accept lower precision |
| 6. Missing Info Analysis | % of known gaps correctly flagged | TBD |
| 7. Follow-up Question Gen | Human rubric (relevance, non-redundancy) | TBD |
| 8. Response Processing | Conflict-resolution correctness on test cases | TBD |
| 9. Completion Check | Loop terminates correctly within max-turn limit | Pass/Fail |
| 10. Risk Assessment | Accuracy vs. clinician-labeled validation cases | TBD |
| 11. XAI | Human rubric: does explanation match actual contributing factors | TBD |
| 12. Report Generation | Schema validation + completeness check | Pass/Fail |
| 13. EHR Database | Data integrity, encryption verification, retrieval correctness | Pass/Fail |
| 14. Dashboard | Functional/UI test pass rate | TBD |
| 15. Feedback Loop | Retraining pipeline runs end-to-end without manual intervention | Pass/Fail |

---

## Test entries

> Append new entries at the top.

```
## YYYY-MM-DD — Module #, [what was tested]
**Test type:** (unit / integration / manual eval / accuracy benchmark)
**Setup:** (test set used, sample size, conditions)
**Result:** (the actual number/outcome)
**Pass/Fail vs. target:** 
**Notes:** (anything surprising, edge cases that broke it)
```

*(No entries yet — log will populate once Module 1 prototyping begins.)*
