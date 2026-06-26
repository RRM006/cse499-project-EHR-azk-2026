# session_protocol.md — How We Start and End Every Session

> This file is the "operating manual". It is not project content — it is the habit
> that makes the whole memory system actually work. Copy-paste the prompts below.
>
> (Session 7 note: no functional change. `update_system_flowchart.md` now also lives in
> `agent_docs/`; read it when working on the pipeline/flow. The rest is unchanged.)

---

## ▶️ START-OF-SESSION prompt (paste this first, every new session)

```
Start of session. Before doing anything else:
1. Read CLAUDE.md.
2. Read these files and give me a 5-line summary of where we are:
   - agent_docs/session_protocol.md
   - agent_docs/current_task.md
   - agent_docs/changelog.md (just the newest 2 entries)
   - agent_docs/milestone_log.md (just the status board + current phase)
3. Tell me the single next step from current_task.md.
4. Then STOP and wait for my "go". Do not write code or make changes yet.
Remember: do not assume anything, plan with me first, keep it cross-platform
(Windows + Linux), and never edit the patient's raw words.
```

Why: Claude Code auto-loads `CLAUDE.md`, but the living logs are not auto-loaded
(on purpose, to save context). This prompt makes Claude read the few files that
matter and orient in seconds — without you re-explaining the project.

---

## ⏹️ END-OF-SESSION prompt (paste this before you stop working)

```
End of session. Please update our memory files now:
1. changelog.md — add a new entry at the TOP using the template (Did / Decided /
   Broke / Deferred / Next).
2. current_task.md — OVERWRITE it so it describes exactly what to do next session
   and the precise next step.
3. milestone_log.md — update any module status / phase that changed.
4. decisions.md — if we made any real decision, add a new ADR entry.
5. test_log.md — if we tested anything, add the result (with numbers).
6. codebase_map.md — if we added or moved files, update the map.
Show me a short diff/summary of what you changed in each file before saving.
```

Why: This is what prevents "Claude forgot where we were". Two minutes at the end
saves you re-explaining everything next time.

---

## 🔁 DURING a session — small reminders

- If Claude starts coding without a plan, say:
  `Stop. Show me the plan and options first, then wait for my go.`
- For a quick side question that you don't want cluttering the work, you can ask
  it plainly; keep the main thread focused on the current task.
- If the context feels full or Claude seems to forget recent things, you can run
  `/clear` to reset — Claude Code reloads `CLAUDE.md` automatically afterward, then
  just paste the START-OF-SESSION prompt again.
- Use `/context` if you want to see how full the context window is.

---

## 🧠 One-time setup notes (do these once)

- Put this whole folder at your repo root so `CLAUDE.md` sits where Claude Code
  looks for it (the folder you open Claude Code in).
- Make a `.gitignore` that ignores `.env`, `.venv/`, downloaded models, and audio
  data. (Ask Claude Code to generate one when we start coding.)
- Optional: run `/init` once. Since `CLAUDE.md` already exists, Claude Code will
  *suggest improvements* rather than overwrite it — review before accepting.
- Optional: Claude Code also keeps its own "auto memory" per project. You can run
  `/memory` to see what it has saved. Our `agent_docs/` files are the source of
  truth that *you* control; auto memory is a helper on top.

---

## The habit in one line
**Start:** paste the start prompt → read → plan → go.
**End:** paste the end prompt → update changelog + current_task → stop.
