"use strict";

// ---------- elements ----------
const startBtn = document.getElementById("startBtn");
const stopBtn = document.getElementById("stopBtn");
const recStatus = document.getElementById("recStatus");
const timerEl = document.getElementById("timer");
const errorBanner = document.getElementById("errorBanner");
const browserWarn = document.getElementById("browserWarn");

const rawBox = document.getElementById("rawBox");
const rawTextEl = document.getElementById("rawText");
const interimEl = document.getElementById("interim");
const copyRawBtn = document.getElementById("copyRaw");
const clearRawBtn = document.getElementById("clearRaw");

const correctBtn = document.getElementById("correctBtn");
const correctedBox = document.getElementById("correctedBox");
const correctMeta = document.getElementById("correctMeta");
const copyCorrectedBtn = document.getElementById("copyCorrected");
const clearCorrectedBtn = document.getElementById("clearCorrected");

const manualText = document.getElementById("manualText");
const manualBtn = document.getElementById("manualBtn");
const refreshRecentBtn = document.getElementById("refreshRecent");
const recentList = document.getElementById("recentList");

// ---------- config / state ----------
const SILENCE_MS = 10000;          // auto-stop after ~10s of continuous silence
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

let recognition = null;
let recording = false;       // true between Start and Stop/auto-stop
let stopping = false;        // user Stop or silence auto-stop → don't auto-restart
let committedRaw = "";       // append-only final text; NEVER cleared mid-session
let startedAt = 0;
let timerId = null;
let lastResultAt = 0;        // timestamp of the most recent speech result
let silenceId = null;

// ---------- helpers ----------
function showError(msg) { errorBanner.textContent = msg; errorBanner.hidden = !msg; }
function clearError() { showError(""); }

function setRecStatus(state) {
  recStatus.textContent = state === "recording" ? "● Recording" : (state === "processing" ? "Processing" : "Idle");
  recStatus.className = "status-pill " + state;
}

function fmt(sec) {
  const m = String(Math.floor(sec / 60)).padStart(2, "0");
  const s = String(sec % 60).padStart(2, "0");
  return `${m}:${s}`;
}

async function copyText(text) {
  if (!text) return;
  try { await navigator.clipboard.writeText(text); } catch (_) { /* ignore */ }
}

// ---------- auto-scroll (shared by Raw / Corrected / Manual panels) ----------
// Each panel "sticks" to the bottom as new text arrives, UNLESS the user has
// scrolled up; it resumes sticking once they scroll back to the bottom.
function nearBottom(el) { return el.scrollHeight - el.scrollTop - el.clientHeight < 24; }
function trackStick(el) {
  el.dataset.stick = "true";
  el.addEventListener("scroll", () => { el.dataset.stick = nearBottom(el) ? "true" : "false"; });
}
function autoScroll(el) { if (el.dataset.stick !== "false") el.scrollTop = el.scrollHeight; }

// ---------- timers ----------
function startTimer() {
  startedAt = Date.now();
  timerEl.textContent = "00:00";
  timerId = setInterval(() => {
    timerEl.textContent = fmt(Math.floor((Date.now() - startedAt) / 1000)); // counts up, no cap
  }, 250);
}
function stopTimer() { if (timerId) clearInterval(timerId); timerId = null; }

function startSilenceWatch() {
  lastResultAt = Date.now();
  silenceId = setInterval(() => {
    if (recording && Date.now() - lastResultAt >= SILENCE_MS) {
      stopRecording("silence"); // ~10s of continuous silence
    }
  }, 500);
}
function stopSilenceWatch() { if (silenceId) clearInterval(silenceId); silenceId = null; }

// ---------- recording ----------
function startRecording() {
  if (!SpeechRecognition) { browserWarn.hidden = false; return; }
  clearError();

  recognition = new SpeechRecognition();
  recognition.lang = "bn-BD";
  recognition.continuous = true;
  recognition.interimResults = true;

  recognition.onresult = (event) => {
    lastResultAt = Date.now(); // any speech (interim or final) resets the silence clock
    let interim = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const r = event.results[i];
      if (r.isFinal) committedRaw += r[0].transcript; // append verbatim; never clear/replace
      else interim += r[0].transcript;
    }
    rawTextEl.textContent = committedRaw;
    interimEl.textContent = interim;
    autoScroll(rawBox); // keep newest line visible unless the user scrolled up
  };

  recognition.onerror = (e) => {
    if (e.error === "not-allowed" || e.error === "service-not-allowed") {
      showError("Microphone permission denied. Allow mic access and try again.");
      stopRecording("error");
    } else if (e.error === "no-speech") {
      // ignore — the silence watcher decides when to actually stop
    } else {
      showError("Speech recognition error: " + e.error);
    }
  };

  // Chrome ends recognition after short pauses. If the user hasn't stopped and we
  // haven't hit the 10s silence limit, restart so brief pauses don't end the session.
  recognition.onend = () => {
    if (recording && !stopping) {
      try { recognition.start(); } catch (_) { /* will retry on next tick if needed */ }
      return;
    }
    interimEl.textContent = "";
    setRecStatus("idle");
  };

  recording = true;
  stopping = false;
  startBtn.disabled = true;
  stopBtn.disabled = false;
  setRecStatus("recording");
  startTimer();
  startSilenceWatch();
  try {
    recognition.start();
  } catch (err) {
    showError("Could not start recording: " + err);
    stopRecording("error");
  }
}

function stopRecording(reason) {
  if (!recording) return;
  recording = false;
  stopping = true;
  stopBtn.disabled = true;
  startBtn.disabled = false;
  stopTimer();
  stopSilenceWatch();
  if (recognition) { try { recognition.stop(); } catch (_) { /* ignore */ } }
  setRecStatus("idle");
  if (reason === "silence") showError("Auto-stopped after ~10s of silence. Your transcript is kept below.");
}

// ---------- correction (store raw first, then correct) ----------
async function correct() {
  const raw = committedRaw.trim();
  if (!raw) { showError("Nothing to correct yet — record or type something first."); return; }
  await runCorrection(committedRaw, "browser_webspeech", "mic");
}

async function runCorrection(rawText, sttProvider, source) {
  correctedBox.innerHTML = '<span class="spinner"></span> Correcting…';
  correctMeta.textContent = "";
  try {
    // 1) store the RAW transcript first (immutable record)
    const storeResp = await fetch("/api/transcripts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ raw_text: rawText, stt_provider: sttProvider, source }),
    });
    const stored = await storeResp.json().catch(() => ({}));
    if (!storeResp.ok) {
      correctedBox.innerHTML = `<span class="error">Save failed (${storeResp.status}): ${stored.detail || ""}</span>`;
      return;
    }
    // 2) correct it by id (raw stays untouched)
    const resp = await fetch("/api/correct", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ utterance_id: stored.id }),
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      correctedBox.innerHTML = `<span class="error">Error ${resp.status}: ${data.detail || "failed"}</span>`;
      return;
    }
    correctedBox.textContent = data.corrected_text != null ? data.corrected_text : "(no correction)";
    autoScroll(correctedBox);
    correctMeta.textContent = `#${data.id} · ${data.correction_provider}/${data.correction_model}`;
    loadRecent();
  } catch (err) {
    correctedBox.innerHTML = `<span class="error">Network error: ${err}</span>`;
  }
}

// ---------- recent list ----------
async function loadRecent() {
  try {
    const resp = await fetch("/api/transcripts?limit=20");
    if (!resp.ok) return;
    const rows = await resp.json();
    recentList.innerHTML = "";
    for (const r of rows) {
      const li = document.createElement("li");
      const rid = document.createElement("span");
      rid.className = "rid";
      rid.textContent = `#${r.id} [${r.stt_provider || "?"}] `;
      const raw = document.createElement("span");
      raw.className = "raw";
      raw.textContent = "RAW: " + r.raw_text;
      const cor = document.createElement("span");
      cor.className = "cor";
      cor.textContent = r.corrected_text != null ? "  →  " + r.corrected_text : "";
      li.append(rid, raw, cor);
      recentList.appendChild(li);
    }
  } catch (_) { /* non-critical */ }
}

// ---------- wire up ----------
if (!SpeechRecognition) { browserWarn.hidden = false; startBtn.disabled = true; }

startBtn.addEventListener("click", startRecording);
stopBtn.addEventListener("click", () => stopRecording("user"));
correctBtn.addEventListener("click", correct);
copyRawBtn.addEventListener("click", () => copyText(rawTextEl.textContent));
clearRawBtn.addEventListener("click", () => {
  // UI-only clear (does not delete stored data); only when not recording
  if (recording) return;
  committedRaw = "";
  rawTextEl.textContent = "";
  interimEl.textContent = "";
});
copyCorrectedBtn.addEventListener("click", () => copyText(correctedBox.textContent));
clearCorrectedBtn.addEventListener("click", () => {
  correctedBox.innerHTML = "<em>No correction yet.</em>";
  correctMeta.textContent = "";
});
manualBtn.addEventListener("click", () => {
  if (manualText.value.trim()) runCorrection(manualText.value, "manual", "manual");
});
manualText.addEventListener("input", () => autoScroll(manualText));
refreshRecentBtn.addEventListener("click", loadRecent);

// enable stick-to-bottom auto-scroll on all three panels
trackStick(rawBox);
trackStick(correctedBox);
trackStick(manualText);

loadRecent();
