/* Browser TTS helper (Module 7 — ADR-0027/0028, Bangla fallback per ADR-0049).

   speak(text): plays `text` aloud. The on-screen text is ALWAYS the fallback — callers
   must display it regardless (ADR-0028), so a missing voice degrades gracefully.

   PROVIDER CHAIN (first one that can actually speak wins):
     1. a real browser voice for the UI language  — free, offline, no server (ADR-0027)
     2. GET /api/tts                              — server espeak-ng, Bangla on Windows
     3. nothing                                   — return false; the caller must NOT
                                                    pretend audio played

   Why 2 exists: Windows ships NO Bengali voice at all, so on Windows step 1 can never
   speak Bangla. Step 2 is a fallback, never a replacement — an installed bn voice
   (e.g. Arch + espeak-ng via speech-dispatcher, ADR-0040) still wins.

   The caller (kiosk.js) must use ttsSpeaking() — NOT speechSynthesis.speaking — as its
   echo guard, because `speechSynthesis.speaking` is false while server audio plays and
   the mic would then transcribe the AI's own question into the patient's verbatim
   record (rule #1). */

let _banglaVoice = null;

function _pickBanglaVoice() {
  const voices = window.speechSynthesis ? window.speechSynthesis.getVoices() : [];
  _banglaVoice =
    voices.find((v) => v.lang === 'bn-BD') ||
    voices.find((v) => v.lang && v.lang.toLowerCase().startsWith('bn')) ||
    null;
  return _banglaVoice;
}

if (window.speechSynthesis) {
  // Voice list loads asynchronously in Chrome.
  window.speechSynthesis.onvoiceschanged = _pickBanglaVoice;
  _pickBanglaVoice();
}

/* S3 (ADR-0048): every speak() call supersedes the previous one. Chrome fires
   `onend` for an utterance that speechSynthesis.cancel() killed, so without a
   generation token a CANCELLED question's callback would fire while the NEW question
   is still being spoken — and an auto-opening mic would then transcribe the AI's own
   voice into the patient's verbatim record. That is a rule #1 defect, so the stale
   callback is dropped here, at the single TTS entry point. The token covers the
   server-audio path too. */
let _speechGeneration = 0;

/* The in-flight server-TTS element. Non-null from the moment the request is created
   until the audio ends or fails — so it also covers the window where the fetch is
   still in flight and nothing is audible YET. Treating that as "speaking" is what
   stops the mic opening into the start of the question. */
let _audio = null;
let _serverTts = false;

/** Tell the helper whether GET /api/tts can actually produce audio. Called by the
 *  kiosk once /api/config has been read; defaults to false so a page that never
 *  configures it behaves exactly as before. */
function configureTts({ serverTts = false } = {}) {
  _serverTts = Boolean(serverTts);
}

function serverTtsEnabled() { return _serverTts; }

/** True while ANY provider is producing (or about to produce) audio. This is the echo
 *  guard's only correct question — see the header note. */
function ttsSpeaking() {
  if (window.speechSynthesis && window.speechSynthesis.speaking) return true;
  return _audio !== null;
}

/** Stop all audio from every provider and invalidate pending callbacks. */
function ttsCancel() {
  _speechGeneration += 1;
  if (window.speechSynthesis) window.speechSynthesis.cancel();
  _releaseAudio();
}

function _releaseAudio() {
  if (!_audio) return;
  const audio = _audio;
  _audio = null;
  try { audio.pause(); } catch (_) { /* already stopped */ }
  audio.onended = null;
  audio.onerror = null;
  audio.src = '';   // drop the pending request so it cannot fire later
}

/* The ACTIVE UI language. tts.js must not hard-code 'bn-BD': when the patient reads the
   portal in English the question text IS English, and handing that to a Bengali voice
   produces nonsense.

   Read from localStorage rather than from a shared.js helper on purpose — shared.js
   already writes 'lang' on every setLanguage() and seeds itself from the same key, so
   this stays in sync with ZERO cross-file coupling. Depending on a shared.js function
   made the two files version-skew: a browser holding a cached shared.js silently sent
   every question down the wrong language path. */
function _uiLang() {
  try {
    return localStorage.getItem('lang') === 'bn' ? 'bn' : 'en';
  } catch (_) {
    return 'en';   // storage blocked (private mode / kiosk lockdown) — match the default
  }
}

function _pickVoice(short) {
  if (!window.speechSynthesis) return null;
  if (short === 'bn') return _banglaVoice || _pickBanglaVoice();
  const voices = window.speechSynthesis.getVoices();
  return voices.find((v) => v.lang && v.lang.toLowerCase().startsWith('en')) || null;
}

/** Speak `text` aloud. Returns true if some provider accepted it, false if NOTHING
 *  can speak (the caller must then rely on the on-screen text alone — ADR-0028).
 *  `onend` fires at most ONCE, never for a superseded utterance, and is bridged from
 *  every error path so a failed utterance can't strand a caller that is waiting to
 *  open the microphone.
 *  `lang` is normally omitted — it follows the UI language. */
function speak(text, { lang = null, onend = null } = {}) {
  if (!text) return false;
  const short = lang ? (String(lang).toLowerCase().startsWith('bn') ? 'bn' : 'en') : _uiLang();
  const generation = (_speechGeneration += 1);
  if (window.speechSynthesis) window.speechSynthesis.cancel(); // never overlap questions
  _releaseAudio();

  let fired = false;
  const finish = () => {
    if (fired || generation !== _speechGeneration) return; // once, and not if superseded
    fired = true;
    _releaseAudio();
    if (onend) onend();
  };

  // --- provider 1: the browser's own voice (preferred: free, offline, no server) ---
  if (window.speechSynthesis) {
    const voice = _pickVoice(short);
    /* Only BANGLA demands a matching voice. With no bn voice the browser reads Bangla
       text with an English voice — audible nonsense that LOOKS like success, which is
       exactly what this ADR removes. English is different: the default voice reads
       English correctly, and accepting it also keeps audio working during Chrome's
       asynchronous getVoices() load, when the list is still momentarily empty. */
    if (voice || short === 'en') {
      const u = new SpeechSynthesisUtterance(text);
      u.lang = short === 'bn' ? 'bn-BD' : 'en-US';
      if (voice) u.voice = voice;
      u.onend = finish;
      u.onerror = finish;
      window.speechSynthesis.speak(u);
      return true;
    }
  }

  // --- provider 2: server-side TTS (this is why Bangla is audible on Windows) ---
  if (_serverTts) {
    const url = `/api/tts?lang=${short}&text=${encodeURIComponent(text)}`;
    const audio = new Audio(url);
    _audio = audio;
    audio.onended = finish;
    // 503 (engine missing) or a decode failure must release the caller immediately,
    // exactly like onerror does for speechSynthesis.
    audio.onerror = finish;
    const started = audio.play();
    if (started && typeof started.catch === 'function') started.catch(finish);
    return true;
  }

  // --- nothing can speak. Say so honestly rather than faking it. ---
  return false;
}

function banglaVoiceAvailable() {
  return Boolean(_banglaVoice || _pickBanglaVoice());
}

/** True when the patient can hear Bangla by SOME route — a real bn voice or the
 *  server fallback. Drives the "no Bangla voice" banner so it stops warning about a
 *  problem that the server provider has already solved. */
function banglaAudioAvailable() {
  return banglaVoiceAvailable() || _serverTts;
}
