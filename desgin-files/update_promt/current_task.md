# current_task.md — What We Are Doing RIGHT NOW

> This is a small, throwaway snapshot. It gets **overwritten** every session.
> It is NOT a history log (that is `changelog.md`). It answers only:
> "If I open a brand-new Claude Code session, what do I need to know to continue?"

---

**Date:** 2026-06-18
**Phase:** Phase 0 — Quick working demo
**Module:** Module 1 — Speech-to-Text (+ the correction step)

## Where we are right now
The project folder and all memory files (`CLAUDE.md` + `agent_docs/`) have been
created. **No code exists yet.** Nothing has been installed yet.

## The one thing we are doing next
Build the **Phase 0 demo**: a single web page that
1. uses the browser's Web Speech API (Chrome, `lang="bn-BD"`) to transcribe live
   microphone speech into Bangla text and show it on screen as the person speaks,
2. keeps that raw text **unchanged** in its own box,
3. sends the raw text to one free LLM API (start with Google Gemini Flash) to get
   a corrected version, and shows the corrected text in a *second* box beside it.

## Exact next step for Claude Code
**Before writing any code, make a short plan with me** covering:
- the folder/file layout for this tiny demo (frontend page + minimal backend, or
  frontend-only first?),
- how the free LLM key will be stored safely (env file, not committed),
- how we keep "raw" and "corrected" clearly separate in the UI and in storage.
Then wait for my "go" before coding.

## Open questions for me (the human) to answer
- Do I already have a Google Gemini (AI Studio) free API key? If not, that is step 1.
- Which folder name for the demo? (suggestion: `phase0_webspeech_demo/`)

## Reminders
- Raw words are never edited (constitution rule #1).
- Plan first, code second. Do not assume. (CLAUDE.md)
- Must stay cross-platform (Windows + Linux).
