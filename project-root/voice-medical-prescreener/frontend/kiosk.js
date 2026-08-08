/* Patient kiosk (FE-1). VOICE-FIRST clinical input with typing always available
   (ADR-0048, which supersedes ADR-0027's voice-only rule — do not re-apply it): STT =
   Web Speech API bn-BD; every follow-up question is SHOWN and SPOKEN together
   (ADR-0028). Both modes feed ONE pipeline, differing only in `source` (mic|manual).
   RAW text goes to the backend verbatim (rule #1).

   Flow: phone -> stub OTP -> open conversation (intake after first answer, then the
   M7-M9 loop) -> 10-field summary -> Confirm & Submit -> auto-logout reset. */

const OPENING_QUESTION = {
  bn: 'আপনার সমস্যাটি নিজের ভাষায় খুলে বলুন তো।',
  en: 'Please tell me, in your own words, what problem you are facing.',
};

const FIELD_LABELS = {
  main_problem:             { en: '1. Main Problem', bn: '১. প্রধান সমস্যা' },
  onset_duration:           { en: '2. When Started & Duration', bn: '২. শুরুর সময় ও স্থায়িত্ব' },
  symptom_details:          { en: '3. Symptom Details', bn: '৩. উপসর্গের বিস্তারিত' },
  associated_symptoms:      { en: '4. Associated Symptoms', bn: '৪. আনুষঙ্গিক উপসর্গ' },
  medical_history:          { en: '5. Medical History', bn: '৫. চিকিৎসা ইতিহাস' },
  current_medicines:        { en: '6. Current Medicines', bn: '৬. চলমান ওষুধসমূহ' },
  allergies:                { en: '7. Allergies', bn: '৭. অ্যালার্জি' },
  recent_changes_exposures: { en: '8. Recent Changes / Exposures', bn: '৮. সাম্প্রতিক পরিবর্তন' },
  treatments_tried:         { en: '9. Treatments Tried', bn: '৯. গৃহীত ব্যবস্থা' },
  current_concern:          { en: '10. Current Concern / Question', bn: '১০. মূল উদ্বেগ / প্রশ্ন' },
};

/* S1/S3 (ADR-0048): the kiosk's voice-loop behaviour is served by GET /api/config so a
   clinic can tune it from backend/.env without editing this file. These defaults mirror
   core/config.py and are used verbatim if the fetch fails — configuration must never be
   what stops a patient from being screened. */
const VOICE_DEFAULTS = {
  voice_loop: 'auto',      // 'auto' = the mic opens itself after TTS; 'manual' = tap-to-talk
  countdown_ms: 3000,      // S4 (not used yet)
  tts_guard_ms: 400,       // silence after TTS before the mic may open (echo guard)
  no_speech_ms: 10000,     // S5 (not used yet)
  max_answer_ms: 120000,   // S5 (not used yet)
  server_tts: false,       // ADR-0049: is GET /api/tts able to speak? assume not
};
let voiceConfig = { ...VOICE_DEFAULTS };

async function loadKioskConfig() {
  try {
    voiceConfig = { ...VOICE_DEFAULTS, ...(await api('GET', '/api/config')) };
  } catch (e) {
    voiceConfig = { ...VOICE_DEFAULTS };  // server unreachable -> safe voice-first defaults
  }
  // ADR-0049: hand the TTS helper its provider chain, then re-evaluate the banner —
  // the server fallback may have just made Bangla audible after all.
  configureTts({ serverTts: voiceConfig.server_tts });
  updateVoiceHint();
}

let state = null;

function resetState() {
  state = {
    phone: null,
    visitUuid: null,
    intakeDone: false,
    activeQuestion: null,   // followup_questions row currently awaiting an answer
    lastQuestionText: OPENING_QUESTION.bn,
    openingAnswered: false,
    busy: false,
    finishing: false,       // P1-1: reentry guard for finishConversation
    lastProfile: null,      // KIOSK-6: kept so the summary re-renders on language toggle
    resumeQuestion: null,   // KIOSK-7: open resume-loop question on the summary screen
    resumeActive: false,
    inputMode: 'voice',     // S2 (ADR-0048): 'voice' (primary/default) | 'type' (always available)
  };
  document.getElementById('chat-thread').innerHTML = '';
  document.getElementById('phone-input').value = '';
  document.querySelectorAll('.otp-input').forEach((i) => { i.value = ''; });
  document.getElementById('fallback-row').style.display = 'none';
  document.getElementById('resume-dock').style.display = 'none';
  document.getElementById('resume-fallback-row').style.display = 'none';
  document.getElementById('resume-fallback-input').value = '';
  document.getElementById('summary-progress').style.display = 'none';
  document.getElementById('confirm-submit-btn').style.display = '';
}
resetState();

function showScreen(id) {
  document.querySelectorAll('.screen').forEach((s) => s.classList.toggle('active', s.id === id));
}

/* P1-2: bubble labels (and assistant text that HAS a bilingual source) carry
   data-en/data-bn so the shared applyLanguage() re-translates them on toggle.
   Patient bodies get NO dataset — verbatim forever (rule #1). `label` is {en,bn};
   `textPair` is an optional {en,bn} for the body (opening prompt only, today). */
function addBubble(role, text, label, textPair = null) {
  const thread = document.getElementById('chat-thread');
  const div = document.createElement('div');
  div.className = `chat-turn ${role}`;
  const meta = document.createElement('div');
  meta.className = 'chat-meta';
  const labelSpan = document.createElement('span');
  labelSpan.dataset.en = label.en;
  labelSpan.dataset.bn = label.bn;
  labelSpan.textContent = t(label.en, label.bn);
  // KIOSK-3: every message gets a speaker icon. Assistant = replay the question;
  // patient = read back EXACTLY the captured words (rule #1 — the text captured at
  // bubble creation, never re-fetched or rewritten).
  const speakBtn = document.createElement('button');
  speakBtn.className = 'bubble-speak';
  speakBtn.type = 'button';
  speakBtn.textContent = '🔊';
  const titleEn = role === 'patient' ? 'Hear your own words again' : 'Hear this question again';
  const titleBn = role === 'patient' ? 'আপনার নিজের কথা আবার শুনুন' : 'এই প্রশ্নটি আবার শুনুন';
  speakBtn.dataset.titleEn = titleEn;
  speakBtn.dataset.titleBn = titleBn;
  speakBtn.title = t(titleEn, titleBn);
  meta.appendChild(labelSpan);
  meta.appendChild(speakBtn);
  const body = document.createElement('span');
  if (textPair) {
    body.dataset.en = textPair.en;   // bilingual assistant text follows the toggle
    body.dataset.bn = textPair.bn;
    body.textContent = t(textPair.en, textPair.bn);
  } else {
    body.textContent = text; // verbatim — never rewritten
  }
  /* Replay what is displayed NOW. Plain speak() — reviewing an old turn must never
     open the mic (S3). ADR-0049: a PATIENT bubble is pinned to Bangla because STT
     captured it at lang='bn-BD'; an assistant bubble follows the UI language, which is
     the language its text is currently displayed in. */
  const replayLang = role === 'patient' ? 'bn-BD' : null;
  speakBtn.onclick = () => speak(body.textContent, { lang: replayLang });
  div.appendChild(meta);
  div.appendChild(body);
  thread.appendChild(div);
  thread.scrollTop = thread.scrollHeight;
}

/* P1-2: JS-written UI text must survive the EN/BN toggle — writing through here keeps
   the element's data-en/data-bn in sync so applyLanguage() re-renders it correctly. */
function setBilingualText(id, en, bn) {
  const el = document.getElementById(id);
  if (!el) return;
  el.dataset.en = en;
  el.dataset.bn = bn;
  el.textContent = t(en, bn);
}

/* KIOSK-2: the Repeat button was "doing nothing" when the OS has no Bangla TTS voice
   (speech is silently skipped/degraded). Make that state VISIBLE: show the hint banner
   whenever no bn voice is available — the on-screen text stays the fallback (ADR-0028). */
function updateVoiceHint() {
  const hint = document.getElementById('voice-hint');
  if (!hint) return;
  /* ADR-0049: the question is now "can the patient hear Bangla by ANY route?" — an
     installed bn voice OR the server espeak-ng fallback. Windows has no Bengali voice
     at all, so before the fallback existed this banner was permanent there. */
  hint.style.display = banglaAudioAvailable() ? 'none' : 'block';
}
if (window.speechSynthesis) {
  // Chrome loads voices asynchronously; tts.js already listens — chain, don't replace.
  const prevHandler = window.speechSynthesis.onvoiceschanged;
  window.speechSynthesis.onvoiceschanged = () => {
    if (prevHandler) prevHandler();
    updateVoiceHint();
  };
}
updateVoiceHint();

/* Show AND speak an assistant turn (ADR-0028), and record it server-side.
   P1-2: accepts either a plain string (server questions already embed EN+BN in one
   string — left as captured) or an {en,bn} pair (re-translates on toggle). */
async function assistantSays(msg, { record = true } = {}) {
  const pair = (msg && typeof msg === 'object') ? msg : null;
  const text = pair ? t(pair.en, pair.bn) : msg;
  state.lastQuestionText = text;
  addBubble('ai', text, { en: 'Assistant', bn: 'সহকারী' }, pair);
  askAloud(text);   // S3: shown as text AND spoken (ADR-0028); in auto mode the mic follows
  if (record && state.visitUuid) {
    try {
      await api('POST', `/api/visits/${state.visitUuid}/utterances`,
        { raw_text: text, role: 'system', source: 'tts', stt_provider: null });
    } catch (e) { /* recording the system turn is best-effort */ }
  }
}

/* S3: repeating re-arms the mic too, so a patient who missed the question is not left
   waiting for a tap they were never told to make.
   ⚠ Known gap, deliberately left for S5: tapping Repeat while the mic is ALREADY open
   plays TTS into a live recognizer. Closing it means deciding what happens to the
   half-spoken answer in the buffer, and discarding a patient's words is a rule #1
   decision — not something to slip into this step. Pre-existing since S25. */
function repeatQuestion() { askAloud(state.lastQuestionText); }

/* --- screens 1-2: identification --- */

/* KIOSK-1: OTP boxes auto-advance on digit entry, Backspace walks back, and pasting
   a full 6-digit code fills every box. Wired once at load. */
function initOtpInputs() {
  const boxes = Array.from(document.querySelectorAll('#otp-row .otp-input'));
  boxes.forEach((box, i) => {
    box.addEventListener('input', () => {
      const digits = box.value.replace(/\D/g, '');
      box.value = digits.slice(-1); // keep only the last typed digit
      if (box.value && i < boxes.length - 1) boxes[i + 1].focus();
    });
    box.addEventListener('keydown', (e) => {
      if (e.key === 'Backspace' && !box.value && i > 0) {
        e.preventDefault();
        boxes[i - 1].value = '';
        boxes[i - 1].focus();
      }
    });
    box.addEventListener('paste', (e) => {
      e.preventDefault();
      const digits = (e.clipboardData || window.clipboardData)
        .getData('text').replace(/\D/g, '').slice(0, boxes.length);
      if (!digits) return;
      boxes.forEach((b, j) => { b.value = digits[j] || ''; });
      boxes[Math.min(digits.length, boxes.length - 1)].focus();
    });
  });
}
initOtpInputs();

async function sendOtp() {
  const phone = document.getElementById('phone-input').value.trim();
  if (!phone) return showError(t('Enter your mobile number.', 'মোবাইল নম্বর লিখুন।'));
  try {
    await api('POST', '/api/patients/lookup', { phone });
    state.phone = phone;
    setBilingualText('otp-sub',
      `A 6-digit code has been sent to +880 ${phone}`,
      `একটি ৬-সংখ্যার কোড +880 ${phone} নম্বরে পাঠানো হয়েছে`);
    showScreen('screen-otp');
    document.querySelector('.otp-input').focus();
  } catch (e) { showError(e.message); }
}

async function verifyOtp() {
  const otp = Array.from(document.querySelectorAll('.otp-input')).map((i) => i.value).join('');
  try {
    const res = await api('POST', '/api/patients/verify-otp', { phone: state.phone, otp });
    state.visitUuid = res.visit.uuid;
    showScreen('screen-voice');
    await assistantSays(OPENING_QUESTION);   // P1-2: bilingual pair → follows the toggle
  } catch (e) { showError(e.message); }
}

/* --- screen 3: the voice conversation --- */

let recognition = null;
let listening = false;
let finalBuffer = '';

/* KIOSK-7: the ONE recognition engine serves two docks — the conversation screen
   and the summary-screen resume dock. This picks the active one's elements. */
function activeDock() {
  return state.resumeActive ? DOCKS.resume : DOCKS.conversation;
}

/* S2 (ADR-0048): both docks, so an input-mode switch applies to the conversation
   screen AND the KIOSK-7 resume dock at once — the patient picks once, not twice. */
const DOCKS = {
  conversation: {
    transcript: 'dock-transcript', mic: 'mic-btn', hint: 'listening-hint',
    fallback: 'fallback-row', input: 'fallback-input',
    voiceBtn: 'mode-voice-btn', typeBtn: 'mode-type-btn',
    countdown: 'dock-countdown', countdownDigit: 'dock-countdown-digit',
  },
  resume: {
    transcript: 'resume-transcript', mic: 'resume-mic-btn', hint: 'resume-hint',
    fallback: 'resume-fallback-row', input: 'resume-fallback-input',
    voiceBtn: 'resume-mode-voice-btn', typeBtn: 'resume-mode-type-btn',
    countdown: 'resume-countdown', countdownDigit: 'resume-countdown-digit',
  },
};

/* Mode-aware dock hint. Voice wording still says "tap" — S2 changes WHO can answer
   how, not the turn-taking; auto-listen arrives in S3. */
const MODE_HINTS = {
  voice: { en: 'Tap the mic when you are ready to speak', bn: 'বলতে প্রস্তুত হলে মাইকে চাপ দিন' },
  type: { en: 'Type your answer, then press Send', bn: 'উত্তর টাইপ করে "পাঠান" চাপুন' },
};

/* S3: in auto mode the patient is not asked to tap to START, so the hint must say so. */
const ARMING_HINT = {
  en: 'Please wait — the microphone will start by itself',
  bn: 'একটু অপেক্ষা করুন — মাইক নিজেই চালু হবে',
};

/* S4: in auto mode the patient is not asked to tap to FINISH either — the turn ends on
   silence. The tap still works (it submits immediately), it is just no longer required,
   so telling an elderly patient to "tap again" would be asking for a needless action. */
const LISTENING_HINT = {
  auto: { en: 'Listening... just stop speaking when you are finished',
          bn: 'শুনছি... বলা শেষ হলে থেমে যান' },
  manual: { en: 'Listening... tap again when done', bn: 'শুনছি... বলা শেষে আবার চাপুন' },
};

function modeHint() { return MODE_HINTS[(state && state.inputMode) || 'voice']; }

function listeningHint() { return LISTENING_HINT[autoVoiceMode() ? 'auto' : 'manual']; }

/* --- S3 (ADR-0048): auto-listen. The AI finishes speaking -> the mic opens itself.
   The patient still taps ONCE to finish an answer; auto-endpointing is S4. --- */

let armToken = 0;      // invalidates a pending arm (new question, mode switch, manual tap)
let armTimer = null;

/** Auto-listen applies only when the deployment asked for it AND the patient is in
 *  voice mode. In 'manual' the kiosk behaves exactly as it did in the passed S25 run. */
function autoVoiceMode() {
  return voiceConfig.voice_loop === 'auto' && state && state.inputMode === 'voice';
}

function cancelPendingMic() {
  clearTimeout(armTimer);
  armTimer = null;
  armToken += 1;   // anything already scheduled now belongs to a stale token
}

/* Speak a question and, in auto mode, arm the microphone to open when it ends.
   Used for every question the patient is expected to ANSWER. The per-bubble 🔊 replay
   button deliberately still calls plain speak() — reviewing an old turn must not open
   the mic. */
function askAloud(text) {
  cancelPendingMic();
  const token = armToken;
  if (!autoVoiceMode()) { speak(text); return; }
  setBilingualText(activeDock().hint, ARMING_HINT.en, ARMING_HINT.bn);
  const spoken = speak(text, { onend: () => openMicWhenQuiet(token) });
  /* Safety net. With no installed voice (or a silently degraded engine) `onend` may
     NEVER fire — the kiosk would then sit forever with the mic shut. Give TTS a
     generous window based on the question length, then open the mic regardless. If
     speechSynthesis is missing entirely, there is nothing to wait for. */
  armTimer = setTimeout(
    () => openMicWhenQuiet(token),
    spoken ? Math.max(3000, text.length * 80) : 0,
  );
}

/* The echo guard (rule #1). The mic must never open while the AI is still audible,
   or the browser transcribes the AI's own question into the patient's verbatim
   record. Poll until ALL TTS is silent, then wait tts_guard_ms more.
   ⚠ ADR-0049: this MUST ask ttsSpeaking(), not speechSynthesis.speaking —
   `speechSynthesis.speaking` is false while the server-TTS <audio> element plays (and
   while its request is still in flight), which would reopen exactly this echo hole. */
function openMicWhenQuiet(token) {
  if (token !== armToken) return;   // superseded — a newer question or a manual action won
  clearTimeout(armTimer);
  if (ttsSpeaking()) {
    armTimer = setTimeout(() => openMicWhenQuiet(token), 120);
    return;
  }
  armTimer = setTimeout(() => {
    if (token !== armToken) return;
    armToken += 1;   // consume: `onend` and the safety net can never both open the mic
    if (!autoVoiceMode() || listening || state.busy) return;
    toggleListening();   // the SAME path a tap takes — one code path, not two
  }, voiceConfig.tts_guard_ms);
}

/* --- S4 (ADR-0048): the endpointer. A turn now ends on SILENCE instead of on a tap.
   The 3-2-1 window is a CONFIRMATION window, never a hard cutoff: EVERY recognition
   result — interim or final — restarts it, so a mid-sentence pause, a cough or "উম্…"
   can never clip an answer. A clipped answer is a rule #1 defect, not a UX nit. --- */

/* How long to let Chrome flush its last final chunk after we stop the engine. Not a
   tunable: it is an engine-latency allowance, not a clinical preference. */
const FLUSH_GRACE_MS = 600;

let countdownTicker = null;
let countdownDeadline = 0;
let heardSpeech = false;   // the window arms only AFTER real words have been captured
let endingTurn = false;    // flush in progress — waiting for Chrome's last final chunk
let flushTimer = null;

/* Both docks are updated together, exactly like setInputMode() — the patient may be in
   the conversation dock or the KIOSK-7 resume dock, and one endpointer serves both. */
function showCountdown(show, secondsLeft) {
  Object.values(DOCKS).forEach((dock) => {
    const box = document.getElementById(dock.countdown);
    if (box) box.style.display = show ? 'flex' : 'none';
    const digit = document.getElementById(dock.countdownDigit);
    if (digit) digit.textContent = show ? t(String(secondsLeft), bnDigits(secondsLeft)) : '';
  });
}

function cancelCountdown() {
  clearInterval(countdownTicker);
  countdownTicker = null;
  countdownDeadline = 0;
  showCountdown(false);
}

/* Called on EVERY recognition result. Restarting on interim results IS the safeguard —
   it keeps the patient, not the timer, in control of when their turn ends. */
function restartSilenceWindow() {
  cancelCountdown();
  if (!autoVoiceMode() || !listening || !heardSpeech || endingTurn) return;
  countdownDeadline = Date.now() + voiceConfig.countdown_ms;
  renderCountdown();
  // Tick well under 1 s so the digit is never visibly stale, and so a clinic that tunes
  // countdown_ms to a non-round value still gets an honest count instead of a fake 3-2-1.
  countdownTicker = setInterval(renderCountdown, 200);
}

function renderCountdown() {
  const remaining = countdownDeadline - Date.now();
  if (remaining <= 0) { endTurnOnSilence(); return; }
  showCountdown(true, Math.ceil(remaining / 1000));
}

/* Zero. Stop the engine FIRST so Chrome finalizes whatever it has not yet marked
   `isFinal`, and only then submit — reading finalBuffer immediately would silently drop
   the tail of the answer (rule #1). Whoever reports back first wins: the engine's own
   `onend`, or the grace timer if it never does. The submit happens exactly ONCE. */
function endTurnOnSilence() {
  cancelCountdown();
  if (endingTurn) return;
  endingTurn = true;
  if (recognition) try { recognition.stop(); } catch (_) {}
  flushTimer = setTimeout(finishFlushedTurn, FLUSH_GRACE_MS);
}

function finishFlushedTurn() {
  if (!endingTurn) return;   // a tap or an error already submitted this turn
  stopListening(true);       // clears the flush state; the SAME path a tap takes
}

/* S2: switch the patient between speaking and typing.
   - VOICE is the primary path and the default at every reset (ADR-0048).
   - TYPING is always reachable — a failed mic, a noisy room, poor recognition or
     simple preference must never block a patient.
   - Both modes feed the SAME endpoints; only `source` ('mic' | 'manual') differs.
   - Switching to typing DISCARDS any un-submitted speech buffer instead of
     pre-filling the box: a typed edit on top of STT text would be stored as one
     utterance whose source/stt_provider provenance is false (ADR-0048, rule #1). */
function setInputMode(mode, { focus = true } = {}) {
  const typing = mode === 'type';
  cancelPendingMic();   // S3: choosing a mode cancels any mic the AI was about to open
  if (typing && listening) stopListening(false);   // mic off, buffer dropped, nothing sent
  state.inputMode = typing ? 'type' : 'voice';
  Object.values(DOCKS).forEach((dock) => {
    const mic = document.getElementById(dock.mic);
    if (mic) mic.style.display = typing ? 'none' : '';   // hidden so it cannot be tapped by accident
    const row = document.getElementById(dock.fallback);
    if (row) row.style.display = typing ? 'flex' : 'none';
    const voiceBtn = document.getElementById(dock.voiceBtn);
    const typeBtn = document.getElementById(dock.typeBtn);
    if (voiceBtn) voiceBtn.setAttribute('aria-pressed', String(!typing));
    if (typeBtn) typeBtn.setAttribute('aria-pressed', String(typing));
    setBilingualText(dock.hint, modeHint().en, modeHint().bn);
  });
  if (typing && focus) {
    const input = document.getElementById(activeDock().input);
    if (input) input.focus();
  }
}

function initRecognition() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return null;
  const r = new SR();
  r.lang = 'bn-BD';
  r.continuous = true;
  r.interimResults = true;
  r.onresult = (event) => {
    let interim = '';
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const chunk = event.results[i][0].transcript;
      if (event.results[i].isFinal) finalBuffer += chunk;
      else interim += chunk;
    }
    // P1-2: mirror the live verbatim text into BOTH language slots so a language
    // toggle mid-recording can never wipe/replace the patient's words (rule #1).
    const el = document.getElementById(activeDock().transcript);
    const live = finalBuffer + interim;
    el.dataset.en = live;
    el.dataset.bn = live;
    el.textContent = live;
    /* S4: the patient is still talking, so the confirmation window restarts from zero.
       Coughs and filler sounds arrive here too — deliberately, since erring toward NOT
       cutting the patient off is the safe direction (rule #1). A blank/noise-only tick
       cancels a running countdown but can never arm one. */
    if (live.trim()) heardSpeech = true;
    restartSilenceWindow();
  };
  r.onend = () => {
    // S4: arbitrate between "we are ending this turn" and "Chrome stopped on its own".
    if (endingTurn) { finishFlushedTurn(); return; }   // the flush completed -> submit
    // Brief pauses keep going. Restart even mid-countdown, so resumed speech is still
    // heard and can still cancel it; `listening` is false after a submit, which is what
    // stops the engine coming back afterwards.
    if (listening) try { r.start(); } catch (_) {}
  };
  r.onerror = (e) => {
    if (e.error === 'not-allowed' || e.error === 'audio-capture') {
      showError(t('Microphone unavailable — you can type instead.', 'মাইক্রোফোন পাওয়া যায়নি — টাইপ করতে পারেন।'));
      stopListening(false);
      setInputMode('type');   // S2: never leave the patient stranded on a dead mic
    }
  };
  return r;
}

function toggleListening() {
  cancelPendingMic();   // S3: a deliberate tap always beats a pending auto-open
  if (listening) { stopListening(true); return; }
  recognition = recognition || initRecognition();
  if (!recognition) {
    showError(t('Speech recognition needs Chrome/Edge — use the typed fallback.', 'স্পিচ রিকগনিশনের জন্য Chrome/Edge দরকার — টাইপ করুন।'));
    setInputMode('type');   // S2: an unsupported browser switches the patient over, not out
    return;
  }
  finalBuffer = '';
  listening = true;
  heardSpeech = false;   // S4: a fresh turn has captured nothing yet, so nothing to confirm
  document.getElementById(activeDock().mic).classList.add('listening');
  setBilingualText(activeDock().hint, listeningHint().en, listeningHint().bn);   // S4: mode-aware
  ttsCancel();   // ADR-0049: silences server audio too, not just speechSynthesis
  try { recognition.start(); } catch (_) {}   // already-started engine throws InvalidStateError
}

function stopListening(sendTurn) {
  /* S4: this is the single exit of a listening turn, so it is where the endpointer is
     torn down — no countdown may outlive its turn, and no pending flush may fire a
     second submit behind a tap that already sent the answer. */
  cancelCountdown();
  endingTurn = false;
  clearTimeout(flushTimer);
  flushTimer = null;
  heardSpeech = false;
  listening = false;
  document.getElementById(activeDock().mic).classList.remove('listening');
  setBilingualText(activeDock().hint, modeHint().en, modeHint().bn);   // S2: mode-aware
  if (recognition) try { recognition.stop(); } catch (_) {}
  const text = finalBuffer.trim();
  setBilingualText(activeDock().transcript, '', '');   // P1-2: clear dataset too
  if (sendTurn && text) {
    if (state.resumeActive) submitResumeAnswer(text, 'mic');
    else submitPatientTurn(text, 'mic');
  }
}

function sendTypedFallback() {
  const input = document.getElementById('fallback-input');
  const text = input.value.trim();
  if (!text) return;
  input.value = '';
  submitPatientTurn(text, 'manual');
}

async function submitPatientTurn(rawText, source) {
  if (state.busy) return;
  state.busy = true;
  addBubble('patient', rawText, { en: 'Your words', bn: 'আপনার কথা' });
  try {
    if (state.activeQuestion) {
      // Answer to an M7 question -> M8 merge + M9 check + next question, one call.
      const res = await api('POST', `/api/visits/${state.visitUuid}/followup/answer`, {
        question_id: state.activeQuestion.id, raw_text: rawText,
        source, stt_provider: source === 'mic' ? 'browser_webspeech' : 'manual',
      });
      state.activeQuestion = res.next_question || null;
      if (res.complete) await finishConversation();
      else await assistantSays(res.next_question.question_text, { record: false });
    } else {
      // Free opening turn(s): store, then run intake and start the loop.
      await api('POST', `/api/visits/${state.visitUuid}/utterances`, {
        raw_text: rawText, role: 'patient', source,
        stt_provider: source === 'mic' ? 'browser_webspeech' : 'manual',
      });
      await api('POST', `/api/visits/${state.visitUuid}/intake`);
      state.intakeDone = true;
      const res = await api('POST', `/api/visits/${state.visitUuid}/followup/next`);
      if (res.complete) await finishConversation();
      else {
        state.activeQuestion = res.question;
        await assistantSays(res.question.question_text, { record: false });
      }
    }
  } catch (e) { showError(e.message); }
  state.busy = false;
}

/* --- screen 4: summary + submit --- */

/* P1-1 helper: record the flushed last turn WITHOUT continuing the question loop —
   the patient chose "Done", so no next question is spoken here; the summary-screen
   resume loop (KIOSK-7) covers anything still missing. Verbatim (rule #1). */
async function submitFinalTurn(rawText) {
  addBubble('patient', rawText, { en: 'Your words', bn: 'আপনার কথা' });
  if (state.activeQuestion) {
    // Answer the open M7 question (stores the utterance + M8 merge); ignore next_question.
    await api('POST', `/api/visits/${state.visitUuid}/followup/answer`, {
      question_id: state.activeQuestion.id, raw_text: rawText,
      source: 'mic', stt_provider: 'browser_webspeech',
    });
    state.activeQuestion = null;
  } else {
    await api('POST', `/api/visits/${state.visitUuid}/utterances`, {
      raw_text: rawText, role: 'patient', source: 'mic', stt_provider: 'browser_webspeech',
    });
    state.intakeDone = false;   // re-run intake below so this turn is extracted too
  }
}

async function finishConversation() {
  if (state.finishing) return;  // P1-1: ignore double-clicks while finishing
  state.finishing = true;
  cancelPendingMic();   // S3: "Done" ends the conversation — no mic may open behind it
  try {
    /* P1-1: clicking "Done — see summary" while the mic was live used to abandon the
       in-progress speech and require a second mic tap. Now: stop the mic, submit the
       already-captured words as the final turn, THEN build the summary. */
    if (listening && !state.resumeActive) {
      stopListening(false);            // mic off + UI reset; finalBuffer is kept
      const text = finalBuffer.trim();
      finalBuffer = '';
      if (text) await submitFinalTurn(text);
    }
    if (!state.intakeDone) {
      await api('POST', `/api/visits/${state.visitUuid}/intake`);
      state.intakeDone = true;
    }
    const profile = await api('GET', `/api/visits/${state.visitUuid}/profile`);
    renderSummary(profile);
    showScreen('screen-summary');
    await refreshResumeLoop(profile);   // KIOSK-7: fill remaining fields before submit
  } catch (e) { showError(e.message); }
  state.finishing = false;
}

/* KIOSK-5: per-field icon + which fields get the accent highlight (symptoms,
   duration, medications per spec — allergies added as clinically critical). */
const FIELD_ICONS = {
  main_problem: '🩺', onset_duration: '⏱️', symptom_details: '📋',
  associated_symptoms: '🤒', medical_history: '📖', current_medicines: '💊',
  allergies: '⚠️', recent_changes_exposures: '🔄', treatments_tried: '🩹',
  current_concern: '💬',
};
const HIGHLIGHT_FIELDS = ['main_problem', 'onset_duration', 'symptom_details',
  'current_medicines', 'allergies'];

function renderSummary(profile) {
  state.lastProfile = profile;
  const fields = ((profile.entities || {}).summary_fields) || {};
  const grid = document.getElementById('summary-grid');
  grid.innerHTML = '';
  Object.keys(FIELD_LABELS).forEach((key) => {
    // KIOSK-6: bilingual DERIVED value for the active language (shared.js fieldValue,
    // display-only with cross-language + legacy {value} fallback). Raw is untouched.
    const text = fieldValue(fields[key]);
    // P1-4: a REQUIRED field (the HIGHLIGHT set) with no text gets the warning
    // "needs info" treatment so the patient can see exactly what to fill next.
    const requiredMissing = HIGHLIGHT_FIELDS.includes(key) && !text;
    const cell = document.createElement('div');
    cell.className = 'summary-item'
      + (HIGHLIGHT_FIELDS.includes(key) ? ' highlight' : '')
      + (requiredMissing ? ' missing' : '');
    if (key === 'symptom_details' || key === 'current_concern') cell.style.gridColumn = 'span 2';
    const head = document.createElement('div');
    head.className = 'summary-item-head';
    const icon = document.createElement('span');
    icon.className = 'summary-icon';
    icon.textContent = FIELD_ICONS[key] || '📄';
    const label = document.createElement('div');
    label.className = 'summary-label';
    label.textContent = t(FIELD_LABELS[key].en, FIELD_LABELS[key].bn);
    head.appendChild(icon);
    head.appendChild(label);
    if (requiredMissing) {
      const chip = document.createElement('span');
      chip.className = 'missing-chip';
      chip.dataset.en = 'Needs info';        // P1-2: follows the language toggle
      chip.dataset.bn = 'তথ্য প্রয়োজন';
      chip.textContent = t('Needs info', 'তথ্য প্রয়োজন');
      head.appendChild(chip);
    }
    const val = document.createElement('div');
    val.className = 'summary-val' + (text ? '' : ' empty');
    val.textContent = text || t('Not mentioned', 'উল্লেখ করা হয়নি');
    cell.appendChild(head);
    cell.appendChild(val);
    grid.appendChild(cell);
  });
}

/* --- KIOSK-7: resume loop — ask ONLY still-missing fields, one at a time, on the
   summary screen. Confirm & Submit is hidden while a question is open; the server
   owns the rules (no threshold gate, shared question cap, "নেই/জানি না" never
   re-asked). If the loop cannot run (cap reached, API down) the patient is NEVER
   trapped: submit comes back. --- */

function bnDigits(n) { return String(n).replace(/\d/g, (d) => '০১২৩৪৫৬৭৮৯'[d]); }

function summaryFilledCount(profile) {
  // JS mirror of backend field_has_text: text in ANY language slot counts.
  const fields = ((profile.entities || {}).summary_fields) || {};
  return Object.keys(FIELD_LABELS).filter((key) => {
    const f = fields[key] || {};
    return ['value', 'value_en', 'value_bn'].some((s) => String(f[s] || '').trim());
  }).length;
}

function renderProgress(profile) {
  const n = summaryFilledCount(profile);
  const chip = document.getElementById('summary-progress');
  chip.style.display = 'inline-block';
  chip.textContent = t(`${n}/10 items completed`, `${bnDigits(n)}/১০ তথ্য সম্পন্ন`);
  chip.classList.toggle('complete', n >= 10);
  return n;
}

function setResumeMode(question) {
  state.resumeActive = !!question;
  state.resumeQuestion = question || null;
  document.getElementById('resume-dock').style.display = question ? 'flex' : 'none';
  document.getElementById('confirm-submit-btn').style.display = question ? 'none' : '';
  if (question) {
    document.getElementById('resume-question').textContent = question.question_text;
    askAloud(question.question_text);   // ADR-0028 + S3: spoken, then the mic arms itself
  } else {
    cancelPendingMic();   // loop finished — nothing should open the mic behind the summary
  }
}

async function refreshResumeLoop(profile) {
  if (renderProgress(profile) >= 10) { setResumeMode(null); return; }
  try {
    const res = await api('POST', `/api/visits/${state.visitUuid}/followup/next?scope=fields`);
    setResumeMode(res.complete ? null : res.question);
  } catch (e) {
    showError(e.message);
    setResumeMode(null);   // fail-open: an API hiccup must never block submission
  }
}

function repeatResumeQuestion() {
  if (state.resumeQuestion) speak(state.resumeQuestion.question_text);
}

function sendResumeTyped() {
  const input = document.getElementById('resume-fallback-input');
  const text = input.value.trim();
  if (!text) return;
  input.value = '';
  submitResumeAnswer(text, 'manual');
}

async function submitResumeAnswer(rawText, source) {
  if (state.busy || !state.resumeQuestion) return;
  state.busy = true;
  try {
    const res = await api('POST',
      `/api/visits/${state.visitUuid}/followup/answer?scope=fields`, {
        question_id: state.resumeQuestion.id, raw_text: rawText,
        source, stt_provider: source === 'mic' ? 'browser_webspeech' : 'manual',
      });
    const profile = await api('GET', `/api/visits/${state.visitUuid}/profile`);
    renderSummary(profile);          // spec: the summary regenerates automatically
    renderProgress(profile);
    setResumeMode(res.complete ? null : res.next_question);
  } catch (e) { showError(e.message); }
  state.busy = false;
}

/* KIOSK-4: export the RAW conversation as .docx BEFORE any AI summarization is
   accepted. Backend writer is verbatim (rule #1); no new backend code — reuses the
   step-3 endpoint. The anchor click (not location.href) keeps the kiosk page put. */
async function downloadRawTranscript() {
  const btn = document.getElementById('download-transcript-btn');
  if (btn) btn.disabled = true;
  try {
    const doc = await api('POST', `/api/visits/${state.visitUuid}/documents/transcript`);
    const a = document.createElement('a');
    a.href = doc.download_url;
    a.download = doc.filename || '';
    document.body.appendChild(a);
    a.click();
    a.remove();
  } catch (e) { showError(e.message); }
  if (btn) btn.disabled = false;
}

async function confirmSubmit() {
  try {
    await api('POST', `/api/visits/${state.visitUuid}/submit`);
  } catch (e) { return showError(e.message); }
  const modal = document.getElementById('logout-modal');
  modal.style.display = 'flex';
  let count = 5;
  document.getElementById('logout-timer').textContent = count;
  const timer = setInterval(() => {
    count -= 1;
    document.getElementById('logout-timer').textContent = count;
    if (count <= 0) {
      clearInterval(timer);
      modal.style.display = 'none';
      resetState();               // kiosk reset is purely frontend state (ADR-0030 d)
      cancelPendingMic();         // S3: nothing from this visit may open the next patient's mic
      cancelCountdown();          // S4: nor may a stale countdown submit into the next visit
      setInputMode('voice', { focus: false });  // S2: the next patient starts voice-first
      showScreen('screen-phone');
    }
  }, 1000);
}

/* KIOSK-6: static labels re-render via applyLanguage(); the summary grid and the
   KIOSK-7 progress chip are built in JS, so rebuild them from the kept profile so
   labels AND extracted values follow the toggle together.
   P1-2: chat-bubble labels/bilingual bodies re-render via applyLanguage (they carry
   data-en/bn); only the 🔊 tooltips need a manual refresh here. */
function onLanguageChange() {
  if (state && state.lastProfile) {
    renderSummary(state.lastProfile);
    renderProgress(state.lastProfile);
  }
  document.querySelectorAll('.bubble-speak[data-title-en]').forEach((b) => {
    b.title = t(b.dataset.titleEn, b.dataset.titleBn);
  });
  // S2: the dock hint is written by JS, so re-render it in the new language too.
  Object.values(DOCKS).forEach((dock) => setBilingualText(dock.hint, modeHint().en, modeHint().bn));
}

/* S2 init — runs LAST, after `listening` is declared, so setInputMode may inspect it.
   Enter sends a typed answer (UX priority: fewer taps), and the kiosk always opens in
   VOICE mode because voice is the primary interaction, not an option (ADR-0048). */
function initTypedInputs() {
  const wire = (inputId, send) => {
    const input = document.getElementById(inputId);
    if (!input) return;
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); send(); }
    });
  };
  wire(DOCKS.conversation.input, sendTypedFallback);
  wire(DOCKS.resume.input, sendResumeTyped);
}
initTypedInputs();
setInputMode('voice', { focus: false });
loadKioskConfig();   // S1/S3: voice_loop + timings from backend/.env; defaults if it fails
