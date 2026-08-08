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

/* S3 (ADR-0048): every speak() call supersedes the previous one. Chrome fires
   `onend` for an utterance that speechSynthesis.cancel() killed, so without a
   generation token a CANCELLED question's callback would fire while the NEW question
   is still being spoken — and an auto-opening mic would then transcribe the AI's own
   voice into the patient's verbatim record. That is a rule #1 defect, so the stale
   callback is dropped here, at the single TTS entry point. */
let _speechGeneration = 0;

/** Speak `text` aloud (bn-BD). Returns true if TTS was attempted, false if the
 *  browser has no speechSynthesis at all (text on screen remains the fallback).
 *  `onend` fires at most ONCE, and never for a superseded utterance. It is also
 *  bridged from `onerror` so a failed/interrupted utterance can't strand a caller
 *  that is waiting to open the microphone. */
function speak(text, { lang = 'bn-BD', onend = null } = {}) {
  if (!window.speechSynthesis || !text) return false;
  const generation = (_speechGeneration += 1);
  window.speechSynthesis.cancel(); // never overlap questions
  const u = new SpeechSynthesisUtterance(text);
  u.lang = lang;
  const voice = _banglaVoice || _pickBanglaVoice();
  if (voice) u.voice = voice;
  if (onend) {
    let fired = false;
    const finish = () => {
      if (fired || generation !== _speechGeneration) return; // once, and not if superseded
      fired = true;
      onend();
    };
    u.onend = finish;
    u.onerror = finish;
  }
  window.speechSynthesis.speak(u);
  return true;
}

function banglaVoiceAvailable() {
  return Boolean(_banglaVoice || _pickBanglaVoice());
}
