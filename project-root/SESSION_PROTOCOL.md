# SESSION PROTOCOL — paste this at the start of every Claude Code session

> Copy-paste the block below as your first message to Claude Code each time
> you sit down to work. It costs one message and saves hours of drift.

---

## Start-of-session prompt (copy this)

```
Before doing anything else:
1. Read PROJECT_CONTEXT.md fully.
2. Read CURRENT_TASK.md — this is what we're doing right now.
3. Read the last 2 entries in CHATLOG.md for recent history/decisions.
4. Skim CODEBASE_MAP.md if you need to know where things live.
5. Check DECISIONS.md if you're about to make a choice that might already
   be settled (framework, model, library, schema, etc.) — don't relitigate
   a closed decision without telling me first.

Then summarize back to me in 3-5 bullets: what we're picking up, and what
you think the next concrete step is. Wait for my go-ahead before writing
code.
```

---

## During the session

- If you (the human) make a real decision — picked a library, rejected an
  approach, changed a schema — say "log that as a decision" or just note it
  yourself in `DECISIONS.md` before you forget why.
- If something breaks or gets deferred, don't just abandon it silently —
  it should end up in `CHATLOG.md` under "Deferred / Known Issues" so it
  doesn't quietly vanish.
- If you run a real test (accuracy check, WER, extraction precision, unit
  tests, manual QA) — log it in `TEST_LOG.md` even if it fails. Failed
  tests are information too.

---

## End-of-session prompt (copy this)

```
We're wrapping up this session. Please:
1. Update CHATLOG.md with a new dated entry: what we did, what we decided,
   what broke or is deferred, and what the logical next step is.
2. Update CURRENT_TASK.md to reflect the new current/next task.
3. If a module's status changed, update MILESTONE_LOG.md.
4. If any architecture/library/design decision was made today, add it to
   DECISIONS.md (if not already logged).
5. If the file/folder structure changed meaningfully, update
   CODEBASE_MAP.md.
Keep all updates concise — bullet points, not prose essays.
```

---

## Why this matters for this specific project

This is a 15-module system with real interdependencies (e.g. Module 5
emergency detection has to interact correctly with whatever Module 3
extraction outputs; Module 9's completion loop depends on Module 6/7
contracts being stable). The expensive failure mode in a project like this
isn't "Claude writes bad code" — it's "Claude (or you) forgets a contract
or constraint from three weeks ago and quietly breaks an interface between
two modules." The files in this repo exist specifically to prevent that.
