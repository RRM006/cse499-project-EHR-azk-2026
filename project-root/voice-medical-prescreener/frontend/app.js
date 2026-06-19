"use strict";

// --- elements ---
const micToggle = document.getElementById("micToggle");
const clearRawBtn = document.getElementById("clearRaw");
const statusEl = document.getElementById("status");
const rawTextEl = document.getElementById("rawText");
const interimEl = document.getElementById("interim");
const correctMicBtn = document.getElementById("correctMic");
const manualTextEl = document.getElementById("manualText");
const correctManualBtn = document.getElementById("correctManual");
const correctedBox = document.getElementById("correctedBox");
const refreshRecentBtn = document.getElementById("refreshRecent");
const recentList = document.getElementById("recentList");
const browserWarn = document.getElementById("browserWarn");

// committedRaw holds ONLY finalized recognition output, appended verbatim.
// JS never edits these words — that is the whole point (constitution rule #1).
let committedRaw = "";
let recognizing = false;
let recognition = null;

// --- Web Speech API setup (Chrome/Edge) ---
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (!SpeechRecognition) {
  browserWarn.hidden = false;
  micToggle.disabled = true;
} else {
  recognition = new SpeechRecognition();
  recognition.lang = "bn-BD";
  recognition.continuous = true;
  recognition.interimResults = true;

  recognition.onresult = (event) => {
    let interim = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const result = event.results[i];
      if (result.isFinal) {
        committedRaw += result[0].transcript; // verbatim append, no trimming
      } else {
        interim += result[0].transcript;
      }
    }
    rawTextEl.textContent = committedRaw;
    interimEl.textContent = interim;
  };

  recognition.onerror = (e) => {
    statusEl.textContent = "Mic error: " + e.error + (e.error === "not-allowed" ? " (allow microphone access)" : "");
  };

  recognition.onend = () => {
    recognizing = false;
    micToggle.textContent = "🎤 Start mic";
    statusEl.textContent = "Stopped.";
    interimEl.textContent = "";
  };
}

micToggle.addEventListener("click", () => {
  if (!recognition) return;
  if (recognizing) {
    recognition.stop();
  } else {
    try {
      recognition.start();
      recognizing = true;
      micToggle.textContent = "⏹ Stop mic";
      statusEl.textContent = "Listening… speak Bangla / Banglish / Roman Bangla.";
    } catch (err) {
      statusEl.textContent = "Could not start mic: " + err;
    }
  }
});

clearRawBtn.addEventListener("click", () => {
  committedRaw = "";
  rawTextEl.textContent = "";
  interimEl.textContent = "";
});

// --- correction call ---
async function correct(rawText, source) {
  if (!rawText.trim()) {
    correctedBox.innerHTML = "<em>Nothing to correct.</em>";
    return;
  }
  correctedBox.textContent = "Correcting…";
  try {
    const resp = await fetch("/api/correct", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ raw_text: rawText, source: source }),
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      correctedBox.innerHTML =
        '<span class="error">Error ' + resp.status + ": " + (data.detail || "request failed") + "</span>";
      return;
    }
    renderCorrected(data);
    loadRecent();
  } catch (err) {
    correctedBox.innerHTML = '<span class="error">Network error: ' + err + "</span>";
  }
}

function renderCorrected(data) {
  correctedBox.innerHTML = "";
  const meta = document.createElement("div");
  meta.className = "meta";
  meta.textContent =
    "#" + data.id + " · source=" + data.source + " · " + data.correction_provider + "/" + data.correction_model;
  const text = document.createElement("div");
  text.className = "corrected-text";
  text.textContent = data.corrected_text != null ? data.corrected_text : "(no correction)";
  correctedBox.append(meta, text);
}

correctMicBtn.addEventListener("click", () => correct(committedRaw, "mic"));
correctManualBtn.addEventListener("click", () => correct(manualTextEl.value, "manual"));

// --- recent list (confirms raw + corrected are stored separately) ---
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
      rid.textContent = "#" + r.id + " ";
      const raw = document.createElement("span");
      raw.className = "raw";
      raw.textContent = "RAW: " + r.raw_text;
      const arrow = document.createTextNode(" → ");
      const cor = document.createElement("span");
      cor.className = "cor";
      cor.textContent = r.corrected_text != null ? r.corrected_text : "";
      li.append(rid, raw, arrow, cor);
      recentList.appendChild(li);
    }
  } catch (err) {
    /* non-critical */
  }
}

refreshRecentBtn.addEventListener("click", loadRecent);
loadRecent();
