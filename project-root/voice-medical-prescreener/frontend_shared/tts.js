/* Browser TTS helper (Module 7 groundwork — Phase A / Step A1, ADR-0027/0028).
   speak(text): plays the text aloud via window.speechSynthesis with lang bn-BD,
   preferring an installed Bangla voice, else the default voice. The on-screen text
   is ALWAYS the fallback — callers must display the text regardless (ADR-0028),
   so a missing Bangla voice degrades gracefully (Open Flag 4). No server, no key. */

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

/** Speak `text` aloud (bn-BD). Returns true if TTS was attempted, false if the
 *  browser has no speechSynthesis at all (text on screen remains the fallback). */
function speak(text, { lang = 'bn-BD', onend = null } = {}) {
  if (!window.speechSynthesis || !text) return false;
  window.speechSynthesis.cancel(); // never overlap questions
  const u = new SpeechSynthesisUtterance(text);
  u.lang = lang;
  const voice = _banglaVoice || _pickBanglaVoice();
  if (voice) u.voice = voice;
  if (onend) u.onend = onend;
  window.speechSynthesis.speak(u);
  return true;
}

function banglaVoiceAvailable() {
  return Boolean(_banglaVoice || _pickBanglaVoice());
}
