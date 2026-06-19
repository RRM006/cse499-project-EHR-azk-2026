"use strict";

// ---------- elements ----------
const providerSel = document.getElementById("provider");
const providerStatus = document.getElementById("providerStatus");
const startBtn = document.getElementById("startBtn");
const stopBtn = document.getElementById("stopBtn");
const recStatus = document.getElementById("recStatus");
const timerEl = document.getElementById("timer");
const remainingEl = document.getElementById("remaining");
const errorBanner = document.getElementById("errorBanner");

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

// ---------- state ----------
const MAX_SECONDS = 300; // 5-minute cap
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

// Map backend status codes -> friendly labels shown in the dropdown + badge.
const STATUS_LABELS = {
  available: "✅ Available",
  missing_api_key: "❌ Missing API Key",
  missing_package: "❌ Missing Python Package",
  missing_model: "❌ Missing Model",
  unsupported_platform: "❌ Unsupported Platform",
  error: "❌ Initialization Error",
};
const statusLabel = (s) => STATUS_LABELS[s] || s;

let providers = {};        // id -> info
let recording = false;
let timerId = null;
let startedAt = 0;

let committedRaw = "";      // browser-path final text, appended verbatim
let currentUtteranceId = null; // id of the raw row that Correct will correct

// server-path (MediaRecorder)
let mediaRecorder = null;
let mediaStream = null;
let audioChunks = [];

// browser-path (Web Speech API)
let recognition = null;

// ---------- helpers ----------
function showError(msg) {
  errorBanner.textContent = msg;
  errorBanner.hidden = !msg;
}
function clearError() { showError(""); }

function setRecStatus(state) {
  recStatus.textContent = state;
  recStatus.className = "status-pill " + state.toLowerCase();
}

function fmt(sec) {
  const m = String(Math.floor(sec / 60)).padStart(2, "0");
  const s = String(sec % 60).padStart(2, "0");
  return `${m}:${s}`;
}

function selectedProvider() {
  return providers[providerSel.value];
}

async function copyText(text) {
  if (!text) return;
  try { await navigator.clipboard.writeText(text); } catch (_) { /* ignore */ }
}

// ---------- provider dropdown ----------
async function loadProviders() {
  const resp = await fetch("/api/stt/providers");
  const list = await resp.json();
  providers = {};
  providerSel.innerHTML = "";
  for (const info of list) {
    // The browser provider also needs the API present in THIS browser.
    if (info.id === "browser_webspeech" && !SpeechRecognition) {
      info.status = "unsupported_platform";
      info.ready = false;
      info.detail = "This browser has no Web Speech API (use Chrome/Edge).";
    }
    providers[info.id] = info;
    const opt = document.createElement("option");
    opt.value = info.id;
    // Show the reason right in the dropdown so disabled options aren't a mystery.
    opt.textContent = info.status === "available"
      ? info.label
      : `${info.label} — ${statusLabel(info.status)}`;
    opt.disabled = info.status !== "available";
    opt.title = info.detail || "";
    providerSel.appendChild(opt);
  }
  // pick the first available option
  const firstAvail = list.find((i) => providers[i.id].status === "available");
  if (firstAvail) providerSel.value = firstAvail.id;
  onProviderChange();
}

function onProviderChange() {
  const info = selectedProvider();
  if (!info) return;
  providerStatus.textContent = statusLabel(info.status);
  providerStatus.className = "badge " + (info.status === "available" ? "available" : "unavailable");
  providerStatus.title = info.detail || "";
  startBtn.disabled = recording || info.status !== "available";
  // Surface the reason (and any error detail) when a provider can't be used.
  if (info.status !== "available") {
    showError(`${info.label}: ${statusLabel(info.status)}${info.detail ? " — " + info.detail : ""}`);
  } else {
    clearError();
  }
}

// ---------- recording lifecycle ----------
function startTimer() {
  startedAt = Date.now();
  timerEl.textContent = `00:00 / ${fmt(MAX_SECONDS)}`;
  remainingEl.textContent = `remaining ${fmt(MAX_SECONDS)}`;
  timerId = setInterval(() => {
    const elapsed = Math.floor((Date.now() - startedAt) / 1000);
    timerEl.textContent = `${fmt(elapsed)} / ${fmt(MAX_SECONDS)}`;
    remainingEl.textContent = `remaining ${fmt(Math.max(0, MAX_SECONDS - elapsed))}`;
    if (elapsed >= MAX_SECONDS) stopRecording(); // auto-stop at 5:00
  }, 250);
}
function stopTimer() {
  if (timerId) clearInterval(timerId);
  timerId = null;
}

async function startRecording() {
  const info = selectedProvider();
  if (!info || info.status !== "available") {
    showError(`Provider "${info ? info.label : "?"}" is not available.`);
    return;
  }
  clearError();
  committedRaw = "";
  rawTextEl.textContent = "";
  interimEl.textContent = "";
  currentUtteranceId = null;

  recording = true;
  startBtn.disabled = true;
  stopBtn.disabled = false;
  providerSel.disabled = true;
  setRecStatus("Recording");
  startTimer();

  if (info.kind === "browser") {
    startBrowserRecognition();
  } else {
    await startMediaRecorder(); // server provider
  }
}

async function stopRecording() {
  if (!recording) return;
  recording = false;
  stopBtn.disabled = true;
  stopTimer();

  const info = selectedProvider();
  if (info && info.kind === "browser") {
    if (recognition) recognition.stop(); // onend will finalize + persist
  } else if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop(); // onstop will upload
  }
}

function finishUI() {
  providerSel.disabled = false;
  onProviderChange(); // re-enable Start if provider still available
}

// ---------- browser path (Web Speech API) ----------
function startBrowserRecognition() {
  recognition = new SpeechRecognition();
  recognition.lang = "bn-BD";
  recognition.continuous = true;
  recognition.interimResults = true;

  recognition.onresult = (event) => {
    let interim = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const r = event.results[i];
      if (r.isFinal) committedRaw += r[0].transcript; // verbatim append
      else interim += r[0].transcript;
    }
    rawTextEl.textContent = committedRaw;
    interimEl.textContent = interim;
  };
  recognition.onerror = (e) => {
    if (e.error === "not-allowed" || e.error === "service-not-allowed") {
      showError("Microphone permission denied. Allow mic access and try again.");
    } else {
      showError("Speech recognition error: " + e.error);
    }
  };
  recognition.onend = async () => {
    interimEl.textContent = "";
    setRecStatus("Processing");
    await persistRaw(committedRaw, "browser_webspeech", "mic");
    setRecStatus("Idle");
    finishUI();
  };

  try {
    recognition.start();
  } catch (err) {
    showError("Could not start recognition: " + err);
    setRecStatus("Idle");
    recording = false;
    stopTimer();
    finishUI();
  }
}

// ---------- server path (MediaRecorder → /api/transcribe) ----------
async function startMediaRecorder() {
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (err) {
    showError("Microphone permission denied or unavailable.");
    recording = false;
    stopTimer();
    setRecStatus("Idle");
    finishUI();
    return;
  }
  audioChunks = [];
  mediaRecorder = new MediaRecorder(mediaStream);
  mediaRecorder.ondataavailable = (e) => { if (e.data.size) audioChunks.push(e.data); };
  mediaRecorder.onstop = async () => {
    mediaStream.getTracks().forEach((t) => t.stop());
    setRecStatus("Processing");
    const blob = new Blob(audioChunks, { type: mediaRecorder.mimeType || "audio/webm" });
    await transcribeBlob(blob);
    setRecStatus("Idle");
    finishUI();
  };
  mediaRecorder.start();
}

async function transcribeBlob(blob) {
  const form = new FormData();
  form.append("provider", providerSel.value);
  form.append("audio", blob, "recording.webm");
  try {
    const resp = await fetch("/api/transcribe", { method: "POST", body: form });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) { showError(`Transcription failed (${resp.status}): ${data.detail || ""}`); return; }
    committedRaw = data.raw_text;
    currentUtteranceId = data.id;
    rawTextEl.textContent = data.raw_text;
    loadRecent();
  } catch (err) {
    showError("Network error during transcription: " + err);
  }
}

// ---------- persist raw (browser/manual) ----------
async function persistRaw(rawText, provider, source) {
  if (!rawText.trim()) return;
  try {
    const resp = await fetch("/api/transcripts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ raw_text: rawText, stt_provider: provider, source }),
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) { showError(`Saving raw failed (${resp.status}): ${data.detail || ""}`); return; }
    currentUtteranceId = data.id;
    rawTextEl.textContent = data.raw_text;
    loadRecent();
  } catch (err) {
    showError("Network error saving raw: " + err);
  }
}

// ---------- correction ----------
async function correct() {
  if (currentUtteranceId == null) {
    showError("Nothing to correct yet — record or enter text first.");
    return;
  }
  correctedBox.innerHTML = '<span class="spinner"></span> Correcting…';
  correctMeta.textContent = "";
  try {
    const resp = await fetch("/api/correct", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ utterance_id: currentUtteranceId }),
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      correctedBox.innerHTML = `<span class="error">Error ${resp.status}: ${data.detail || "failed"}</span>`;
      return;
    }
    correctedBox.textContent = data.corrected_text != null ? data.corrected_text : "(no correction)";
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
providerSel.addEventListener("change", onProviderChange);
startBtn.addEventListener("click", startRecording);
stopBtn.addEventListener("click", stopRecording);
correctBtn.addEventListener("click", correct);
copyRawBtn.addEventListener("click", () => copyText(rawTextEl.textContent));
clearRawBtn.addEventListener("click", () => {
  // UI-only clear (does NOT delete stored data)
  committedRaw = "";
  rawTextEl.textContent = "";
  interimEl.textContent = "";
});
copyCorrectedBtn.addEventListener("click", () => copyText(correctedBox.textContent));
clearCorrectedBtn.addEventListener("click", () => {
  correctedBox.innerHTML = "<em>No correction yet.</em>";
  correctMeta.textContent = "";
});
manualBtn.addEventListener("click", () => persistRaw(manualText.value, "manual", "manual"));
refreshRecentBtn.addEventListener("click", loadRecent);

loadProviders();
loadRecent();
