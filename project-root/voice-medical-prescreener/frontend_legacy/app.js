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
const downloadRawLink = document.getElementById("downloadRaw");

const correctBtn = document.getElementById("correctBtn");
const correctedBox = document.getElementById("correctedBox");
const correctMeta = document.getElementById("correctMeta");
const copyCorrectedBtn = document.getElementById("copyCorrected");
const clearCorrectedBtn = document.getElementById("clearCorrected");
const downloadCorrectedLink = document.getElementById("downloadCorrected");

const manualText = document.getElementById("manualText");
const manualBtn = document.getElementById("manualBtn");
const refreshRecentBtn = document.getElementById("refreshRecent");
const recentList = document.getElementById("recentList");
const refreshDocsBtn = document.getElementById("refreshDocs");
const docsList = document.getElementById("docsList");

// ---------- config / state ----------
const SILENCE_MS = 10000;          // auto-stop after ~10s of continuous silence
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

let recognition = null;
let recording = false;       // true between Start and Stop/auto-stop
let stopping = false;        // user Stop or silence auto-stop → don't auto-restart
let committedRaw = "";       // append-only final text; NEVER cleared mid-session
let currentUtteranceId = null; // id of the saved RAW utterance for this session
let startedAt = 0;
let timerId = null;
let lastResultAt = 0;        // timestamp of the most recent speech result
let silenceId = null;

// ---------- helpers ----------
function showError(msg) { errorBanner.textContent = msg; errorBanner.hidden = !msg; }
function clearError() { showError(""); }

// One place for every transient status the UI reports (spec loading states).
const STATUS = {
  idle: ["Idle", "idle"],
  recording: ["● Recording", "recording"],
  saving: ["Saving…", "processing"],
  generating: ["Generating document…", "processing"],
  correcting: ["Correcting text…", "processing"],
};
function setStatus(state) {
  const [text, cls] = STATUS[state] || STATUS.idle;
  recStatus.textContent = text;
  recStatus.className = "status-pill " + cls;
}

function enableDownload(link, doc) {
  if (!doc) return;
  link.href = doc.download_url || `/api/documents/${doc.id}/download`;
  link.classList.remove("is-disabled");
  link.title = doc.filename || "";
}
function disableDownload(link) {
  link.removeAttribute("href");
  link.classList.add("is-disabled");
  link.removeAttribute("title");
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

  // A fresh session: the next Stop saves a NEW raw utterance, and the download
  // buttons are off until that session's documents exist.
  currentUtteranceId = null;
  disableDownload(downloadRawLink);
  disableDownload(downloadCorrectedLink);

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
      showError("Speech recognition failed.");
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
  };

  recording = true;
  stopping = false;
  startBtn.disabled = true;
  stopBtn.disabled = false;
  setStatus("recording");
  startTimer();
  startSilenceWatch();
  try {
    recognition.start();
  } catch (err) {
    showError("Speech recognition failed.");
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
  setStatus("idle");
  if (reason === "silence") showError("Auto-stopped after ~10s of silence. Your transcript is kept below.");

  // On a real stop, persist the RAW transcript and auto-generate its .docx.
  if (reason === "user" || reason === "silence") finalizeRawSession();
}

// ---------- persistence helpers ----------
// Save the RAW transcript exactly as captured. Returns the new utterance id.
async function saveRaw(rawText, sttProvider, source) {
  const resp = await fetch("/api/transcripts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ raw_text: rawText, stt_provider: sttProvider, source }),
  });
  if (!resp.ok) throw new Error("save");
  const stored = await resp.json();
  return stored.id;
}

// Generate the RAW .docx for a saved utterance and enable its download button.
async function generateRawDoc(id) {
  const resp = await fetch(`/api/transcripts/${id}/documents/raw`, { method: "POST" });
  if (!resp.ok) throw new Error("doc");
  enableDownload(downloadRawLink, await resp.json());
}

// Stop → save raw → generate raw .docx. Errors surface with the spec messages.
async function finalizeRawSession() {
  if (!committedRaw.trim()) return; // nothing was recognized
  try {
    setStatus("saving");
    currentUtteranceId = await saveRaw(committedRaw, "browser_webspeech", "mic");
  } catch (_) {
    showError("Failed to save transcript.");
    setStatus("idle");
    return;
  }
  try {
    setStatus("generating");
    await generateRawDoc(currentUtteranceId);
  } catch (_) {
    showError("Failed to generate document.");
  } finally {
    setStatus("idle");
    loadRecent();
    loadDocuments();
  }
}

// ---------- correction (raw must already be saved; raw stays immutable) ----------
async function correct() {
  // If the user clicks Correct without a saved session (e.g. they never stopped, or
  // typed manually), save the raw first so correction has an id to attach to.
  if (currentUtteranceId == null) {
    const raw = committedRaw;
    if (!raw.trim()) { showError("Nothing to correct yet — record or type something first."); return; }
    try {
      setStatus("saving");
      currentUtteranceId = await saveRaw(raw, "browser_webspeech", "mic");
    } catch (_) { showError("Failed to save transcript."); setStatus("idle"); return; }
    try { setStatus("generating"); await generateRawDoc(currentUtteranceId); }
    catch (_) { showError("Failed to generate document."); }
  }
  await runCorrection(currentUtteranceId);
}

async function runCorrection(id) {
  clearError();
  correctedBox.innerHTML = '<span class="spinner"></span> Correcting text…';
  correctMeta.textContent = "";
  setStatus("correcting");
  try {
    const resp = await fetch("/api/correct", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ utterance_id: id }),
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      correctedBox.innerHTML = '<span class="error">Gemini correction failed.</span>';
      showError("Gemini correction failed.");
      return;
    }
    correctedBox.textContent = data.corrected_text != null ? data.corrected_text : "(no correction)";
    autoScroll(correctedBox);
    correctMeta.textContent = `#${data.id} · ${data.correction_provider}/${data.correction_model}`;
    enableDownload(downloadCorrectedLink, data.corrected_document); // corrected .docx
    loadRecent();
    loadDocuments();
  } catch (err) {
    correctedBox.innerHTML = '<span class="error">Gemini correction failed.</span>';
    showError("Gemini correction failed.");
  } finally {
    setStatus("idle");
  }
}

// ---------- manual fallback (type → save as RAW → export) ----------
async function useManualText() {
  const txt = manualText.value;
  if (!txt.trim()) return;
  clearError();
  // Mirror into the RAW display and treat it as the active session.
  committedRaw = txt;
  rawTextEl.textContent = txt;
  currentUtteranceId = null;
  disableDownload(downloadRawLink);
  disableDownload(downloadCorrectedLink);
  try {
    setStatus("saving");
    currentUtteranceId = await saveRaw(txt, "manual", "manual");
  } catch (_) { showError("Failed to save transcript."); setStatus("idle"); return; }
  try { setStatus("generating"); await generateRawDoc(currentUtteranceId); }
  catch (_) { showError("Failed to generate document."); }
  finally { setStatus("idle"); loadRecent(); loadDocuments(); }
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

// ---------- saved documents ----------
async function loadDocuments() {
  try {
    const resp = await fetch("/api/documents?limit=20");
    if (!resp.ok) return;
    const rows = await resp.json();
    docsList.innerHTML = "";
    if (rows.length === 0) {
      const li = document.createElement("li");
      li.className = "empty";
      li.textContent = "No documents yet — Stop a recording or Correct to generate one.";
      docsList.appendChild(li);
      return;
    }
    for (const d of rows) {
      const li = document.createElement("li");
      const meta = document.createElement("span");
      meta.className = "rid";
      const when = new Date(d.created_at).toLocaleString();
      meta.textContent = `session #${d.utterance_id} · ${d.kind} · ${d.format} · ${when} `;
      const link = document.createElement("a");
      link.className = "doc-link";
      link.href = d.download_url || `/api/documents/${d.id}/download`;
      link.textContent = `⬇ ${d.filename}`;
      li.append(meta, link);
      docsList.appendChild(li);
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
manualBtn.addEventListener("click", useManualText);
manualText.addEventListener("input", () => autoScroll(manualText));
refreshRecentBtn.addEventListener("click", loadRecent);
refreshDocsBtn.addEventListener("click", loadDocuments);

// enable stick-to-bottom auto-scroll on all three panels
trackStick(rawBox);
trackStick(correctedBox);
trackStick(manualText);

loadRecent();
loadDocuments();
