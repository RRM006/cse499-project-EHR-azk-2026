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

/* F4: the scripted opening — AREA first, then name, then age, then the free
   description. These three are REQUIRED (F3) but the M7 loop cannot be relied on to
   ask for them: M7 targets clinical gaps in the 10 fields, not identity, and area is
   deliberately not one of those fields (the human's decision: the 10-field contract
   stays byte-identical).

   Each is an ORDINARY turn — the question is stored as a `system` utterance and the
   answer as a `patient` utterance — so the chronological conversation and the raw
   transcript stay complete (requirement 8), and M3 sees them exactly like any other
   speech. No second pipeline (ADR-0048).

   Area comes FIRST because every later question is better for knowing it: it is the
   context M7 keeps questions inside instead of wandering. */
const INTAKE_SCRIPT = [
  {
    key: 'problem_area',
    en: 'Which health problem would you like to talk about today? For example: stomach, chest, head, or skin.',
    bn: 'আজ আপনি কোন সমস্যার বিষয়ে কথা বলতে চান? যেমন: পেট, বুক, মাথা বা ত্বক।',
  },
  {
    key: 'patient_name',
    en: 'What is your name?',
    bn: 'আপনার নাম কী?',
  },
  {
    key: 'patient_age',
    en: 'How old are you?',
    bn: 'আপনার বয়স কত?',
  },
  // Last: the free description. Answering THIS is what triggers intake + the M7 loop.
  { key: 'main_problem', en: OPENING_QUESTION.en, bn: OPENING_QUESTION.bn },
];

function scriptEntry(key) { return INTAKE_SCRIPT.find((q) => q.key === key) || null; }

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
  countdown_ms: 3000,      // S4: the visible confirmation window before a turn is sent
  tts_guard_ms: 400,       // silence after TTS before the mic may open (echo guard)
  no_speech_ms: 10000,     // S5 (not used yet)
  max_answer_ms: 120000,   // S5 (not used yet)
  server_tts: false,       // ADR-0049: is GET /api/tts able to speak? assume not
  answer_confirm: true,    // S34 (ADR-0055): read a spoken answer back before storing it
  review_timeout_ms: 60000, // S34 (ADR-0055): review screen auto-submit; 0 = never
  phone_confirm_ms: 10000, // S35 (ADR-0056): phone read-back auto-accept; 0 = tap required
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
  applyCountdownCaption();
}

/* S34: with the read-back on (the default), the countdown no longer ends in a submit —
   it ends in "here is what I heard". The markup carries the honest caption for the
   answer_confirm=false deployment; this rewrites it for the confirming one, so the
   screen can never promise the wrong next step. */
function applyCountdownCaption() {
  if (!voiceConfig.answer_confirm) return;
  ['dock-countdown-caption', 'resume-countdown-caption'].forEach((id) =>
    setBilingualText(id,
      'Finishing your answer — keep speaking to continue',
      'আপনার উত্তর শেষ হচ্ছে — বলা চালিয়ে গেলে থেমে যাবে'));
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
    readiness: null,        // F3: the SERVER's verdict on "may this patient submit yet?"
    scriptIndex: -1,        // F4: position in INTAKE_SCRIPT; -1 = the script is done
    resumeScripted: null,   // F4: a scripted question re-asked on the summary screen
    inputMode: 'voice',     // S2 (ADR-0048): 'voice' (primary/default) | 'type' (always available)
    identifyStep: 'phone',  // F5b: 'phone' | 'otp' | null — which identification dock owns the mic
    pendingPhone: null,     // F5b: a spoken number awaiting the patient's confirmation
    pendingAnswer: null,    // S34: {text, scope} — a spoken answer awaiting the read-back OK
    reviewConfirm: false,   // S35: the review screen is waiting for a spoken yes/no
  };
  document.getElementById('chat-thread').innerHTML = '';
  document.getElementById('phone-input').value = '';
  document.querySelectorAll('.otp-input').forEach((i) => { i.value = ''; });
  document.getElementById('fallback-row').style.display = 'none';
  document.getElementById('resume-dock').style.display = 'none';
  document.getElementById('resume-fallback-row').style.display = 'none';
  document.getElementById('resume-fallback-input').value = '';
  document.getElementById('summary-progress').style.display = 'none';
  document.getElementById('required-notice').style.display = 'none';   // F3
  document.getElementById('confirm-submit-btn').style.display = '';
  document.getElementById('phone-confirm').style.display = 'none';     // F5b
  /* S34: the read-back panels and the review clock, by ID rather than through DOCKS —
     resetState() runs at module load, where `const DOCKS` is still in its temporal dead
     zone. (The same trap that killed the whole kiosk once in S33.) */
  document.getElementById('dock-answer-confirm').style.display = 'none';
  document.getElementById('resume-answer-confirm').style.display = 'none';
  document.getElementById('kiosk-clock').style.display = 'none';
}
resetState();

/* --- S36 (ADR-0057): THE PATIENT SESSION BOUNDARY --------------------------------

   The defect this closes is a PRIVACY one, and it was not hypothetical. The kiosk is
   one long-lived page that serves patient after patient, and almost nothing belonging
   to the previous patient actually stopped when their visit was submitted.

   `resetState()` builds a fresh `state` object and empties the chat thread, which LOOKS
   like a reset. It is not one — everything living outside `state` survived it:

     * **The recognition engine, still running.** `r.onend` restarts it while
       `listening` is true, and `r.onresult` writes into `activeDock()`. So a patient
       who was still talking when the kiosk reset had their voice transcribed straight
       into the NEXT patient's phone dock.
     * **`finalBuffer`**, still holding the previous patient's captured words.
     * **Every in-flight `api()` promise.** `state` is a module-level variable that
       resetState() REPLACES, so a response arriving after the reset does not write into
       a dead object — it writes into the LIVE one. The worst is `verifyOtp()`: it would
       install the previous patient's `visit.uuid` into the new patient's session, and
       every answer the new patient gave would be POSTed onto the old patient's visit.
       `submitResumeAnswer()` and `finishConversation()` would likewise `renderSummary()`
       the previous patient's profile onto the new patient's review screen.
     * **The review read-through**, still reading the previous patient's answers aloud.
     * **The phone countdown**, and the previous patient's rendered summary cards.

   The fix is an EPOCH — the same shape as S3's `armToken` and S34's read-aloud queue
   token, both of which already solve "a callback that outlived what asked for it".
   `sessionToken()` captures the session on screen; the predicate it returns answers
   "is my session still the live one?", and every `await` on a patient-facing path is
   followed by that check BEFORE it writes anything.

   ⚠ Why an epoch and not just "clear the variables": clearing cannot help a promise
   that has ALREADY resolved and is about to run. The only way to stop a continuation
   is for it to identify itself as stale, which is what the counter is for.

   ⚠ `endSession()` is deliberately NOT called from `resetState()`. resetState() also
   runs at MODULE LOAD, where `recognition`, `finalBuffer`, `phoneTicker` and `DOCKS`
   are all still in their temporal dead zone — the trap that killed the whole kiosk once
   in S33. `startNewSession()` sequences the two instead. */

let sessionEpoch = 0;

/** Capture the session that is on screen NOW. The returned predicate is false from the
 *  moment endSession() runs, which is exactly the question every `await` on a
 *  patient-facing path must ask before it touches `state` or the DOM. */
function sessionToken() {
  const epoch = sessionEpoch;
  return () => epoch === sessionEpoch;
}

/** Tear down everything belonging to the patient who just finished — for real, not
 *  visually. Ordered so the epoch bump happens FIRST: if anything below throws, the
 *  in-flight responses are already invalidated, which is the half that protects data. */
function endSession() {
  sessionEpoch += 1;

  /* 1. The microphone. Detaching the handlers BEFORE abort() is what stops `onend`
        from restarting the engine, and abort() rather than stop() DISCARDS what was
        captured instead of delivering it into the next patient's dock. A fresh engine
        is built for the next patient rather than reusing this one. */
  listening = false;
  endingTurn = false;
  if (recognition) {
    try {
      recognition.onresult = null;
      recognition.onend = null;
      recognition.onerror = null;
      recognition.abort();
    } catch (_) { /* an engine that never started throws; there is nothing to undo */ }
  }
  recognition = null;
  finalBuffer = '';
  heardSpeech = false;

  // 2. Audio in both directions — ADR-0049: ttsCancel() also stops the server <audio>.
  readAloudQueue = null;   // the review read-through must not follow the patient out
  ttsCancel();

  // 3. Every timer that could still fire into the next patient's screening.
  cancelPendingMic();
  cancelCountdown();
  cancelPhoneTimer();
  cancelReviewTimer();
  clearTimeout(flushTimer);
  flushTimer = null;

  // 4. The re-entry guards, so the next patient is never locked out by a flag the
  //    previous one left set (a stuck `otpVerifying` makes the kiosk refuse every code).
  otpSending = false;
  otpVerifying = false;
  submitting = false;
  autoTranscriptDownloaded = false;   // S36 Finding 6: the NEXT patient gets their own

  // 5. The previous patient's WORDS, wherever they are still rendered. Hiding a panel
  //    is not enough — the text itself goes, so there is nothing left to re-read.
  hideAnswerConfirm();
  hidePhoneConfirm();
  clearDigitPreview();
  Object.values(DOCKS).forEach((dock) => {
    setBilingualText(dock.transcript, '', '');
    const box = dock.confirmText ? document.getElementById(dock.confirmText) : null;
    if (box) box.textContent = '';
  });
  const grid = document.getElementById('summary-grid');
  if (grid) grid.innerHTML = '';
  const resumeQ = document.getElementById('resume-question');
  if (resumeQ) resumeQ.textContent = '';
  hideConvoProgress();   // S36 Finding 7: the next patient starts at no question, not at 4
  setReadAloudLabel(false);
}

/** The ONE way a new patient begins: end the previous session, THEN build clean state,
 *  THEN put the kiosk back where a new patient starts.
 *
 *  All three, always, in this order. The order is the contract — a reset without an
 *  endSession() is the bug this whole section exists to fix — and so is the
 *  COMPLETENESS: a caller that had to remember to also clear the avatar, restore voice
 *  mode and show the phone screen is the same "maintained by remembering" teardown that
 *  confirmSubmit() used to carry, one function further along. There is nothing left for
 *  a caller to forget. */
function startNewSession() {
  endSession();
  resetState();
  setAvatarOverride(null);   // P1: the next patient must not inherit "All done"
  setInputMode('voice', { focus: false });   // S2/ADR-0048: voice-first at every reset
  showScreen('screen-phone');
}

function showScreen(id) {
  document.querySelectorAll('.screen').forEach((s) => s.classList.toggle('active', s.id === id));
  /* S40 (1C): a screen the patient has just arrived at starts at ITS top. `.screen` is
     the scroll container (S34), and it keeps its scroll position across an
     activate/deactivate cycle — so returning to the review after a follow-up question
     used to drop the patient wherever they had scrolled to last time. Instant, not
     smooth: this is a page change, and animating it would just look like a glitch. */
  const shown = document.getElementById(id);
  if (shown) shown.scrollTop = 0;
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
     the language its text is currently displayed in.
     TTS-1: an ASSISTANT bubble is a bilingual M7 question, so replay speaks the half
     matching the UI language — the same thing the patient heard the first time. A
     PATIENT bubble is `verbatim`: those are the patient's own captured words, and
     "hear your own words again" must read back all of them. */
  const replayLang = role === 'patient' ? 'bn-BD' : null;
  speakBtn.onclick = () =>
    speak(body.textContent, { lang: replayLang, verbatim: role === 'patient' });
  div.appendChild(meta);
  div.appendChild(body);
  thread.appendChild(div);
  scrollThreadToEnd(thread);
}

/* S34 — the conversation follows itself down the screen.
   Scrolls the THREAD, never the page: scrollIntoView() on the bubble would move the
   whole document, which yanks the typed-answer box and the mic out from under a patient
   who is mid-interaction — and does it again on every keystroke-triggered re-render.
   Smooth by default because the movement is the cue that something new arrived; honest
   under prefers-reduced-motion, where an instant jump is what the patient asked for.
   The scrollTop assignment stays as the fallback: it is correct everywhere, including
   engines with no smooth-scroll support. */
function scrollThreadToEnd(thread) {
  if (!thread) return;
  const reduced = window.matchMedia
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (!reduced && thread.scrollTo) {
    try {
      thread.scrollTo({ top: thread.scrollHeight, behavior: 'smooth' });
      return;
    } catch (_) { /* older engine — fall through to the instant path */ }
  }
  thread.scrollTop = thread.scrollHeight;
}

/* S41 — the transcript box follows the patient's own words down.

   The box is bounded (`max-height: 30vh`) and scrolls internally, so on a long answer
   the newest words would otherwise sit below its bottom edge while the patient is still
   talking — they would be watching a box that had stopped updating.

   ⚠ Scrolls the BOX, never the page. This is the one thing that legitimately runs on
   every recognition result, and it is safe precisely because it moves nothing outside
   this element. `scrollTop` rather than smooth scrolling: this fires several times a
   second, and an animation queue at that rate lags behind the text it is chasing. */
function scrollTranscriptToEnd(el) {
  if (!el) return;
  if (el.scrollHeight > el.clientHeight) el.scrollTop = el.scrollHeight;
}

/* S40 (1C) — automatic movement is `bringIntoView()`, which lives in shared.js since
   S41 (the medic intake form needed the identical behaviour, and two copies of "scroll
   this into view" is how two answers to one question start disagreeing). shared.js is
   loaded by kiosk.html before this file.

   Why `block: 'nearest'` matters here specifically: an element already on screen does
   not move at all, so on the S40 two-column layout — where the assistant and the
   patient panel are both visible — this is silent, and it only acts on a stacked or
   short screen, which is where it was needed.

   ⚠ Deliberately NOT called per recognition result. Scrolling the PAGE on every interim
   chunk is how a page becomes unusable while someone is talking. The transcript BOX
   scrolls its own newest line into view instead — see scrollTranscriptToEnd(). */

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

/* --- F5a (ADR-0053): reading digits out of Bangla or English, spoken or typed ---

   The contract, matched by `to_ascii_digits()` in db/repository_visits.py: a decimal
   digit is a digit whatever script it is written in. JS is the half that had it wrong
   in the OTHER direction from Python — JS `\d` is ASCII-only, so `replace(/\D/g,'')`
   SILENTLY DELETED a Bangla digit typed into an OTP box, while Python's Unicode-aware
   `\D` kept it and then failed the ASCII checks downstream. Both are fixed to the same
   rule so the two languages can no longer disagree.

   These are PURE functions on purpose: no DOM, no state, no network. F5b wires them to
   the microphone; here they are only the vocabulary, which is also what makes them
   verifiable in a browser without a mic. */

const BN_ZERO = 0x09E6;   // '০' — Bangla-Bengali digits are one contiguous block

/** One character -> its ASCII digit, or null. ASCII and Bangla only: those are the two
 *  scripts this kiosk can actually receive. The SERVER is deliberately more permissive
 *  (any Nd character), because it must never be the thing that rejects a valid number. */
function unicodeDigit(ch) {
  const code = ch.codePointAt(0);
  if (code >= 0x30 && code <= 0x39) return String(code - 0x30);
  if (code >= BN_ZERO && code <= BN_ZERO + 9) return String(code - BN_ZERO);
  return null;
}

/** Every digit in a string, folded to ASCII, in order. Non-digits are dropped. */
function asciiDigits(text) {
  let out = '';
  for (const ch of String(text || '')) {
    const d = unicodeDigit(ch);
    if (d !== null) out += d;
  }
  return out;
}

/* Spoken digit words. Bangla first (the kiosk listens at lang='bn-BD'), then the
   English words a Banglish speaker mixes in, then the spelling variants the recognizer
   actually returns — `শুন্য` with the short u instead of the long uu, and `পাচ` without
   the chandrabindu, are common STT output, not typos.

   ⚠ Deliberately ABSENT: English homophones (`to`/`too`, `for`, `won`, `ate`). They are
   ordinary words, and mapping them would invent digits out of a sentence like "for the
   number". Bangla compound numbers (এগারো, তেইশ) are absent for the same reason — a
   patient reading a phone number says the digits one at a time. What the map misses,
   the F5b confirmation step catches; what a homophone ADDS would look correct. */
const SPOKEN_DIGITS = {
  'শূন্য': '0', 'শুন্য': '0', 'এক': '1', 'দুই': '2', 'তিন': '3', 'চার': '4',
  'পাঁচ': '5', 'পাচ': '5', 'ছয়': '6', 'সাত': '7', 'আট': '8', 'নয়': '9',
  'zero': '0', 'oh': '0', 'o': '0', 'nought': '0',
  'one': '1', 'two': '2', 'three': '3', 'four': '4',
  'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9',
  /* S34: the ENGLISH digit words as the bn-BD recogniser actually writes them.
     The kiosk listens at lang='bn-BD' (it must — the clinical answers are Bangla),
     and a Bangla-language recogniser handed "one two three" does not return Latin
     script: it returns the Bangla TRANSLITERATION. So the Latin keys above could
     never be hit by a patient who says English digits out loud, and the whole number
     came back as zero digits. These are the missing half of that vocabulary.

     Safe by the same test as every other key here: none of the ten is an ordinary
     Bangla word, so none can be produced by ordinary speech. `ও` (a very common word
     — "and", "he/she") is deliberately NOT mapped to zero for exactly that reason,
     even though an English speaker's "oh" is transliterated that way. A missed digit
     is caught by the read-back; an invented one reads as correct. */
  'জিরো': '0', 'ওয়ান': '1', 'টু': '2', 'থ্রি': '3', 'ফোর': '4',
  'ফাইভ': '5', 'সিক্স': '6', 'সেভেন': '7', 'এইট': '8', 'নাইন': '9',
};

/** One spoken (or typed) utterance -> its whole words, lowercased and NFC-folded.
 *
 *  The ONE tokenizer for every vocabulary the kiosk matches against speech: the
 *  spoken digits (F5a) and, since S35, the spoken yes/no confirmation. Words are
 *  matched WHOLE, never as substrings — `তিনি` ("he/she") contains `তিন` ("three"),
 *  and substring matching would read a three out of a pronoun.
 *
 *  ⚠ `.normalize('NFC')` is load-bearing, not defensive tidying. `ছয়` (6) and `নয়` (9)
 *  each have TWO encodings that render identically: precomposed U+09DF, or য U+09AF +
 *  nukta U+09BC. They are `!==` in JS, so a recogniser returning the other spelling
 *  would miss the map and silently drop a digit. NFC is the fold, and note it resolves
 *  toward the DECOMPOSED pair (U+09DF is a Unicode composition exclusion) — which is
 *  the form the keys above are written in.
 *
 *  ⚠ `\p{M}` in the split class is equally load-bearing, and its absence was a REAL
 *  defect caught only by running this in a browser: Bangla vowel signs and the nukta
 *  (ূ ি া ্ ় ঁ) are category MARK, not Letter or Number. Without `\p{M}` the split
 *  treated a word's own vowel marks as separators and shredded it — `শূন্য এক সাত এক
 *  পাঁচ নয় আট চার ছয় তিন দুই` returned "118" instead of the eleven digits, because
 *  `এক` and `আট` are the only two digit words with no combining mark and `এক` is said
 *  twice. ZWJ/ZWNJ are stripped for the same reason: invisible, and they would
 *  silently break an otherwise exact match.
 */
function speechTokens(text) {
  const cleaned = String(text || '').normalize('NFC').replace(/[\u200C\u200D]/g, '');
  return cleaned.toLowerCase().split(/[^\p{L}\p{N}\p{M}]+/u).filter(Boolean);
}

/** Pull the digit sequence out of one spoken (or typed) utterance.
 *
 *  Anything unrecognised contributes nothing, so filler ("আমার নম্বর হলো…") is ignored
 *  rather than being an error, and a token that is itself digits contributes those
 *  digits — which is what makes a mixed "শূন্য এক ৭১৫" work. */
function digitsFromSpeech(text) {
  let out = '';
  for (const token of speechTokens(text)) {
    const word = SPOKEN_DIGITS[token];
    if (word !== undefined) { out += word; continue; }
    out += asciiDigits(token);
  }
  return out;
}

/* --- S35 (ADR-0056): saying YES or NO out loud ------------------------------------

   The ONE yes/no vocabulary in the kiosk. Both places a patient is asked to confirm
   something — the answer read-back (ADR-0055) and the final review — parse speech
   through `parseConfirmation()`, so there is a single definition of what "yes" means
   and a single place a missing word gets added.

   The matching is EXPLICIT and CONSERVATIVE, and the reason is asymmetric risk: a
   confirmation that is missed costs the patient one repeat, while a confirmation
   INVENTED out of ordinary speech silently stores an answer they were trying to
   correct. So an utterance is only a confirmation when EVERY word in it is one this
   map knows — see parseConfirmation() for what that rules out. */

/* Yes. `ঠিক` ("correct") carries "ঠিক আছে" and "ঠিক" alone; the negated forms are
   handled by NO winning outright, below. */
const CONFIRM_YES = new Set([
  'হ্যাঁ', 'হ্যা', 'হা', 'জি', 'জ্বি', 'জী', 'ঠিক', 'ইয়েস',
  'yes', 'yeah', 'yep', 'ok', 'okay', 'right', 'correct', 'fine', 'good',
  /* S36 (ADR-0057), Finding 5: the words a patient actually uses to mean "nothing more
     to change". Measured against the shipped parser BEFORE this session, every one of
     these returned null — so the most natural way to say "everything is fine" was heard
     as ordinary speech and stored as though it were a correction:
        সব ঠিক আছে · সবকিছু ঠিক আছে · সব ঠিক · all right · alright · that is all

     `all` and `সব` are YES words rather than filler, and that distinction is the whole
     reason the "that is all" family works: a filler-only utterance carries no YES token,
     so parseConfirmation() would still return null for it. They stay safe under the same
     rule as every other entry — an utterance is a verdict only when EVERY word in it is
     known — so "all my body hurts" and "সব সময় ব্যথা" remain ambiguous and are asked
     again, never treated as approval.

     ⚠ Keep apostrophes OUT of the comments inside this literal. test_kiosk_voice_
     confirmation.py parses the vocabulary straight out of the served file by matching
     quoted tokens, so an apostrophe in prose is read as a word and silently joins the
     set — which is exactly how the overlap test caught this comment on its first draft. */
  'alright', 'all', 'সব', 'সবকিছু',
]);

/* No. `নাই`/`নেই` are what "ঠিক নাই" is built from, and `আবার`/`বলি`/`বলব` cover
   "আবার বলি" ("let me say it again"), which is how a patient rejects without ever
   using the word "না". */
const CONFIRM_NO = new Set([
  'না', 'নাই', 'নেই', 'ভুল', 'আবার', 'বলি', 'বলব', 'বলবো', 'নো',
  'no', 'nope', 'wrong', 'incorrect', 'again', 'repeat',
]);

/* Words that may appear in a confirmation without being one. Kept SHORT on purpose:
   every entry widens what counts as a confirmation, and the whole safety of this
   scheme is that an unknown word makes the utterance ambiguous instead of a verdict. */
const CONFIRM_FILLER = new Set([
  'আছে', 'হয়েছে', 'একদম', 'জ্বী', 'হুম', 'আচ্ছা', 'মানে', 'এটা', 'এটাই', 'সেটাই',
  'that', 'is', 'it', 'thats', 'quite', 'very', 'uh', 'um', 'hmm', 'well',
  /* S36 (ADR-0057), Finding 5: speechTokens() splits on every non-letter, so a
     contraction leaves its tail behind as a separate token — the phrase "that is all"
     written with an apostrophe tokenises to three tokens, that / s / all, and the
     orphan s made the whole utterance ambiguous. It is a fragment rather than a word,
     so it can carry no meaning of its own and is safe here; `thats` above stays for the
     recognisers that write it unpunctuated.
     ⚠ No apostrophes in this comment — see the note in CONFIRM_YES. */
  's',
]);

/** 'yes' | 'no' | null (not a confirmation — ask again, never guess).
 *
 *  Two rules, both deliberate:
 *
 *  1. **An unknown word makes the whole utterance ambiguous.** This is what stops
 *     "আমার নাম রহিম, না মানে..." from being read as a rejection, and it is the direct
 *     answer to "do not assume every sentence containing না means NO". A patient who is
 *     talking rather than confirming gets asked again; nothing is decided for them.
 *  2. **Where both appear, NO wins.** `ঠিক নাই` and `ঠিক না` are built from a YES word
 *     plus a negation, and reading them as agreement would store an answer the patient
 *     just rejected. Erring toward "ask again" is the safe direction (rule #1).
 */
function parseConfirmation(text) {
  const tokens = speechTokens(text);
  if (!tokens.length) return null;
  let yes = false;
  let no = false;
  for (const token of tokens) {
    if (CONFIRM_NO.has(token)) { no = true; continue; }
    if (CONFIRM_YES.has(token)) { yes = true; continue; }
    if (CONFIRM_FILLER.has(token)) continue;
    return null;   // an ordinary word — this is speech, not an answer to a yes/no question
  }
  if (no) return 'no';
  return yes ? 'yes' : null;
}

/** A digit string spaced out for reading: '01715' -> '0 1 7 1 5'. Used for the LIVE
 *  preview and for the spoken read-back, which need the same thing for the same
 *  reason — eleven digits run together are checked by nobody. */
function spacedDigits(text) { return String(text || '').split('').join(' '); }

/** The 10-digit national part of a BD mobile ('1715984632'), or null.
 *
 *  Mirrors normalize_phone() in db/repository_visits.py step for step, and returns what
 *  #phone-input actually holds — the markup already shows the +880 prefix beside it.
 *  The server stays the authority; this exists so the kiosk can SHOW the patient the
 *  number it heard before anything is sent (F5b), which needs an answer locally. */
function phoneFromSpeech(text) {
  let d = digitsFromSpeech(text);
  if (d.startsWith('880')) d = d.slice(3);
  if (d.startsWith('0')) d = d.replace(/^0+/, '');
  if (d.length !== 10 || !d.startsWith('1')) return null;
  return d;
}

/* How many digits the code has. The markup ships exactly this many .otp-input boxes;
   keeping it as one constant is what lets "the code is complete" be a single check. */
const OTP_LENGTH = 6;

function otpBoxes() {
  return Array.from(document.querySelectorAll('#otp-row .otp-input'));
}

function otpDigits() {
  return otpBoxes().map((b) => b.value).join('');
}

/* F1: reset the boxes so a retry always starts from a clean, empty code. Leaving the
   rejected digits on screen is exactly what made "wrong OTP" confusing — the patient
   had to work out that they must clear six boxes themselves before trying again. */
function clearOtpInputs({ focus = true } = {}) {
  const boxes = otpBoxes();
  boxes.forEach((b) => { b.value = ''; });
  if (focus && boxes[0]) boxes[0].focus();
}

/* F1: a complete code IS the submit gesture — no button hunt, no extra tap (ADR-0048's
   "minimize clicks" priority). verifyOtp() owns the re-entry guard, so the typed path,
   the pasted path, Enter and the button can never submit the same code twice. */
function maybeAutoVerify() {
  if (otpDigits().length === OTP_LENGTH) verifyOtp();
}

/* KIOSK-1: OTP boxes auto-advance on digit entry, Backspace walks back, and pasting
   a full 6-digit code fills every box. F1 adds Enter-to-submit (there was NO Enter
   handler here at all — pressing Enter did nothing) and auto-verify on completion.
   Wired once at load. */
function initOtpInputs() {
  const boxes = otpBoxes();
  boxes.forEach((box, i) => {
    box.addEventListener('input', () => {
      // F5a: asciiDigits(), not replace(/\D/g,'') — JS `\d` is ASCII-only, so a Bangla
      // digit typed here used to vanish as the patient typed it.
      const digits = asciiDigits(box.value);
      box.value = digits.slice(-1); // keep only the last typed digit
      if (box.value && i < boxes.length - 1) boxes[i + 1].focus();
      maybeAutoVerify();
    });
    box.addEventListener('keydown', (e) => {
      if (e.key === 'Backspace' && !box.value && i > 0) {
        e.preventDefault();
        boxes[i - 1].value = '';
        boxes[i - 1].focus();
        return;
      }
      // F1: Enter submits from any box — the keyboard path a patient expects.
      if (e.key === 'Enter') { e.preventDefault(); verifyOtp(); }
    });
    box.addEventListener('paste', (e) => {
      e.preventDefault();
      const digits = asciiDigits((e.clipboardData || window.clipboardData).getData('text'))
        .slice(0, boxes.length);   // F5a: a pasted Bangla-digit code now survives too
      if (!digits) return;
      boxes.forEach((b, j) => { b.value = digits[j] || ''; });
      boxes[Math.min(digits.length, boxes.length - 1)].focus();
      maybeAutoVerify();
    });
  });
}
initOtpInputs();

/* S36 (ADR-0057), Finding 4: the re-entry guard the lookup never had. FOUR things can
   now reach sendOtp() — the Continue button, Enter in the field, the read-back's ✔, and
   the phone countdown accepting itself — and every one of them sends a real SMS. The
   read-back path was already single-shot (confirmPhone() clears `pendingPhone` first),
   but the typed path was not: two quick Enters were two codes to the patient's handset,
   and because each new code invalidates the last (ADR-0045, single-use), the patient
   would then be reading out a code the server had already replaced. */
let otpSending = false;

async function sendOtp() {
  if (otpSending) return;
  const phone = document.getElementById('phone-input').value.trim();
  if (!phone) return showError(t('Enter your mobile number.', 'মোবাইল নম্বর লিখুন।'));
  otpSending = true;
  const mine = sessionToken();   // S36: this lookup belongs to the patient who asked for it
  try {
    await api('POST', '/api/patients/lookup', { phone });
    if (!mine()) return;   // the kiosk reset while we waited — this number is not the new patient's
    state.phone = phone;
    setBilingualText('otp-sub',
      `A 6-digit code has been sent to +880 ${phone}`,
      `একটি ৬-সংখ্যার কোড +880 ${phone} নম্বরে পাঠানো হয়েছে`);
    /* F5b: from here the mic may open itself — reaching this line always took a
       deliberate tap (the mic, Enter, or the button), so the gesture Chrome requires
       for audio and for the permission prompt has already happened. */
    state.identifyStep = 'otp';
    showScreen('screen-otp');
    document.querySelector('.otp-input').focus();
    askAloud(t(OTP_PROMPT.en, OTP_PROMPT.bn));
  } catch (e) {
    if (mine()) showError(e.message);
  } finally {
    /* Released, not latched: the guard exists to collapse the near-simultaneous calls
       (two Enters, a tap racing the countdown) into one SMS. A later, deliberate retry
       after a failed lookup is a different request and must still work. */
    otpSending = false;
  }
}

/* F1: re-entry guard. Auto-verify, Enter and the button all land here, and the code is
   SINGLE-USE server-side (ADR-0045) — a double submit would burn the patient's own valid
   code and reject them with "Invalid verification code". */
let otpVerifying = false;

async function verifyOtp() {
  if (otpVerifying) return;
  const otp = otpDigits();
  if (otp.length !== OTP_LENGTH) {
    showError(t(`Enter all ${OTP_LENGTH} digits of the code.`,
      `কোডের ${bnDigits(OTP_LENGTH)}টি সংখ্যাই লিখুন।`));
    return;
  }
  otpVerifying = true;
  /* S36 (ADR-0057): the single most dangerous stale write in the kiosk. Without this
     token, a verify-otp response that arrives after the kiosk has reset installs the
     PREVIOUS patient's visit.uuid into the NEW patient's session — and every answer the
     new patient then gives is POSTed onto the old patient's visit. */
  const mine = sessionToken();
  let res = null;
  try {
    res = await api('POST', '/api/patients/verify-otp', { phone: state.phone, otp });
  } catch (e) {
    /* Wrong, expired or locked out: clear the boxes and say what to do next. The
       server's own detail is kept first — "Too many wrong attempts" and "Invalid
       verification code" need different reactions from the patient. */
    clearOtpInputs();
    showError(`${e.message} ${t('Please enter the code again.',
      'অনুগ্রহ করে কোডটি আবার লিখুন।')}`);
  } finally {
    otpVerifying = false;
  }
  if (!mine()) return;   // S36: a verified code from a finished session opens nothing
  // Failed above — the patient stays on the OTP screen. F5b: in voice mode, say the
  // prompt again and reopen the mic, so retrying is speaking rather than hunting.
  if (!res) { reAskOtp(); return; }
  state.visitUuid = res.visit.uuid;
  state.identifyStep = null;   // F5b: identification over — the docks hand back to the conversation
  showScreen('screen-voice');
  await askScriptedQuestion(0);   // F4: area → name → age → free description
}

/* --- F5b (ADR-0053): identification BY VOICE, on the same engine as everything else ---

   The two screens differ in exactly one way, and it is not architectural:
     * PHONE — a spoken number is read back and must be CONFIRMED before anything is
       sent. Getting a digit wrong here does not annoy the patient, it sends their
       verification code to a stranger's handset.
     * OTP   — recognised digits are filled into the six boxes and F1's existing
       maybeAutoVerify() takes over. A wrong code is self-correcting (the server
       rejects it, F1 clears and re-asks), so a confirmation step here would be one
       more thing to do for no safety gained — ADR-0048's "minimize clicks". */

const PHONE_PROMPT = {
  en: 'Please say your mobile number, one digit at a time.',
  bn: 'অনুগ্রহ করে আপনার মোবাইল নম্বরটি একটি একটি করে বলুন।',
};
const OTP_PROMPT = {
  en: 'Please say the 6-digit code, one digit at a time.',
  bn: 'অনুগ্রহ করে ৬-সংখ্যার কোডটি একটি একটি করে বলুন।',
};

/* Say a digit string as DIGITS. The spaces are the whole point: handed "01715984632"
   whole, a synthesizer reads "one billion, seven hundred fifteen million…", which is
   useless for checking a phone number. Bangla UI hears Bangla numerals. */
function speakDigits(ascii) {
  const shown = t(ascii, bnDigits(ascii));
  speak(shown.split('').join(' '), { verbatim: true });
}

/* S34 — the LIVE digit preview on the two identification docks.
   The dock transcript shows what the recogniser HEARD, which for a spoken number is
   words ("সাত এক পাঁচ", "one two three"). That is correct and stays: it is the
   evidence. But it is not what the patient needs to check, and reading "one two
   three…" back off the screen while trying to verify a phone number is exactly the
   confusion this fixes. So the digits are shown too, DERIVED from the same utterance
   by digitsFromSpeech() — the identical function that will produce the value — and
   spaced out so they can be read one by one.
   Nothing here is stored or sent; it is display only, and the recogniser's own text is
   never rewritten. */
function renderDigitPreview(live) {
  const dock = activeDock();
  const box = dock.digitPreview ? document.getElementById(dock.digitPreview) : null;
  if (!box) return;
  const digits = digitsFromSpeech(live);
  // P1-2: both slots, so a mid-utterance language toggle cannot blank it.
  box.dataset.en = spacedDigits(digits);
  box.dataset.bn = spacedDigits(bnDigits(digits));
  box.textContent = t(box.dataset.en, box.dataset.bn);
  box.style.display = digits ? 'block' : 'none';
}

function clearDigitPreview() {
  Object.values(DOCKS).forEach((dock) => {
    const box = dock.digitPreview ? document.getElementById(dock.digitPreview) : null;
    if (!box) return;
    box.dataset.en = '';
    box.dataset.bn = '';
    box.textContent = '';
    box.style.display = 'none';
  });
}

/* The number as a Bangladeshi patient knows it: 11 digits starting 0, grouped. The
   stored/canonical form is still +8801XXXXXXXXX — that is the server's business, and
   showing it here would be asking an elderly patient to verify a format they never use. */
function renderPhoneReadback() {
  const el = document.getElementById('phone-readback');
  if (!el || !state || !state.pendingPhone) return;
  const local = '0' + state.pendingPhone;
  const grouped = `${local.slice(0, 5)}-${local.slice(5)}`;
  el.dataset.en = grouped;              // P1-2: data-* so the EN/BN toggle re-renders it
  el.dataset.bn = bnDigits(grouped);
  el.textContent = t(grouped, bnDigits(grouped));
}

function showPhoneConfirm(national) {
  state.pendingPhone = national;
  renderPhoneReadback();
  const panel = document.getElementById('phone-confirm');
  panel.style.display = 'flex';
  /* Adding this panel makes the phone screen taller than a 720px viewport, so on a short
     screen it opens BELOW THE FOLD: the patient hears their number read back and sees no
     buttons. The page scrolls, but an elderly patient should not have to discover that.
     ⚠ The offsetHeight read is required, not superstition: called in the same tick as
     `display = 'flex'` the layout is still stale and scrollIntoView does nothing at all
     (measured — scrollY stayed 0 with both buttons off-screen). Reading offsetHeight
     forces layout to be current, synchronously. requestAnimationFrame would also fix it
     ON A PAINTING TAB, but it never runs on one that is not, which is exactly the
     unverifiable-in-CI failure mode this avoids. */
  void panel.offsetHeight;
  panel.scrollIntoView({ block: 'nearest' });
  speakDigits('0' + national);   // plain speak(): the next action is a tap, not an answer
  startPhoneTimer();             // S35: …or no action at all — see below
}

function hidePhoneConfirm() {
  if (state) state.pendingPhone = null;
  cancelPhoneTimer();   // S35: the clock belongs to the panel and dies with it
  const el = document.getElementById('phone-confirm');
  if (el) el.style.display = 'none';
}

/* --- S35 (ADR-0056), Finding 1: the phone read-back accepts itself after 10 seconds ---

   ⚠ This CHANGES ADR-0053, so it is worth being exact about what and why. ADR-0053
   said a spoken phone number "must be CONFIRMED before anything is sent", because a
   wrong digit does not annoy the patient — it sends their verification code to a
   stranger's handset. That reasoning still stands, and nothing here weakens the
   PRESENTATION: the number is still shown at the largest size on the screen and still
   read back digit by digit. What changes is the DEFAULT when the patient does nothing:
   an elderly patient who does not know they are expected to press something used to sit
   in front of a kiosk that had silently stopped. Ten visible, audible, cancellable
   seconds is a confirmation window, not a bypass — and `VOICE_PHONE_CONFIRM_MS=0`
   restores ADR-0053's tap-required behaviour exactly (the ADR-0045 pattern).

   It reuses `startTicker()` and the ONE header clock. No second timer implementation. */
let phoneTicker = null;

function phoneConfirmMs() {
  return Math.max(0, Number(voiceConfig.phone_confirm_ms) || 0);
}

function startPhoneTimer() {
  if (phoneTicker) return;   // idempotent: re-showing the panel never stacks a second
  const total = phoneConfirmMs();
  if (!total) { hideClock(); return; }   // 0 = the clinic requires the tap (ADR-0053)
  phoneTicker = startTicker(total, {
    onTick: (secondsLeft) => renderClock(secondsLeft, CLOCK_LABELS.phone),
    onEnd: () => {
      phoneTicker = null;
      hideClock();
      confirmPhone();   // its own guard makes this exactly one send
    },
  });
}

function cancelPhoneTimer() {
  if (phoneTicker) phoneTicker.cancel();
  phoneTicker = null;
  hideClock();
}

/** The patient agreed with what we heard — only now does the number leave the device.
 *  Re-entrant by construction: hidePhoneConfirm() clears `pendingPhone`, so the timeout
 *  and a simultaneous tap can never both reach sendOtp(). */
function confirmPhone() {
  if (!state || !state.pendingPhone) return;
  hidePhoneConfirm();
  sendOtp();
}

/** "No, say it again": clear it and reopen the mic in the same gesture, so correcting a
    misheard number costs ONE tap rather than tap-clear-tap. */
function rejectPhone() {
  hidePhoneConfirm();
  document.getElementById('phone-input').value = '';
  setBilingualText(DOCKS.phone.transcript, '', '');
  if (state.inputMode === 'voice' && !listening) toggleListening();
}

/* --- S36 (ADR-0057), Finding 4: a complete phone number ends its own turn ----------

   The phone number is the ONE answer in this kiosk whose completeness is knowable the
   instant it arrives: eleven digits, starting 01, and there is nothing more to say.
   Every other answer is prose, where only silence can suggest the patient has finished
   — which is why the S4 endpointer waits `countdown_ms` before ending a turn.

   Applying that same wait here was a defect, not a design. After the last digit the mic
   stayed open for the whole confirmation window, and whatever arrived in it was appended
   to the SAME utterance: "…নয় দুই, এটাই আমার নম্বর" adds no digits and is merely untidy,
   but a patient who repeats themselves ("…দুই — দুই?") pushes the count past eleven and
   `phoneFromSpeech()` then returns null for a number that was already correct. The
   patient is told their number was not understood and asked to say it all again.

   ⚠ This deliberately does NOT skip the read-back. ADR-0053's reason still holds — a
   wrong digit here does not annoy the patient, it sends their verification code to a
   stranger's handset — and S35 already made that step require no button: it accepts
   itself after `phone_confirm_ms`. So the patient still hears their number and still
   reaches OTP without touching anything; they simply stop waiting for a silence timer
   that had nothing left to wait for.

   ⚠ It reads `live` (finals PLUS the current interim), because the eleventh digit is
   usually still interim when it arrives — waiting for the recogniser to finalise it is
   the very delay this removes. The captured text is committed to `finalBuffer` first, so
   `stopListening(true)` submits exactly the words that were on screen and the ordinary
   path (applySpokenPhone -> read-back) runs unchanged. One route in, one route out. */
function maybeCompletePhone(live) {
  // Only on the phone dock, only while a turn is genuinely open, and never twice: after
  // stopListening() `listening` is false, which is what makes a late final chunk from
  // the engine harmless.
  if (!state || state.identifyStep !== 'phone' || state.pendingPhone) return false;
  if (!listening || endingTurn) return false;
  if (!phoneFromSpeech(live)) return false;   // not eleven valid digits yet — keep listening
  cancelCountdown();      // S4: the confirmation window has nothing left to confirm
  finalBuffer = live;     // the evidence is the utterance that was actually shown
  stopListening(true);    // the SAME exit a tap takes — applySpokenPhone() takes it from here
  return true;
}

function applySpokenPhone(rawText) {
  const heard = digitsFromSpeech(rawText);
  const national = phoneFromSpeech(rawText);
  const input = document.getElementById('phone-input');
  if (!national) {
    /* Keep whatever WAS heard in the field rather than discarding it: nine correct
       digits are a head start for the typed repair, and the patient can see exactly
       where the recognition went wrong. Nothing is sent. */
    input.value = heard;
    hidePhoneConfirm();
    showError(t(
      `I heard ${heard.length} digits. Please say the whole 11-digit number again, or type it.`,
      `আমি ${bnDigits(heard.length)}টি সংখ্যা শুনেছি। সম্পূর্ণ ১১-সংখ্যার নম্বরটি আবার বলুন, অথবা টাইপ করুন।`));
    reAskPhone();
    return;
  }
  input.value = national;
  showPhoneConfirm(national);
}

function applySpokenOtp(rawText) {
  const digits = digitsFromSpeech(rawText);
  if (digits.length !== OTP_LENGTH) {
    clearOtpInputs({ focus: false });   // no focus: it would fight the mic on a kiosk
    showError(t(
      `I heard ${digits.length} digits — the code has ${OTP_LENGTH}. Please say it again.`,
      `আমি ${bnDigits(digits.length)}টি সংখ্যা শুনেছি — কোডে ${bnDigits(OTP_LENGTH)}টি আছে। আবার বলুন।`));
    reAskOtp();
    return;
  }
  otpBoxes().forEach((box, i) => { box.value = digits[i]; });
  maybeAutoVerify();   // F1 owns everything from here — single-use guard, clear-and-re-ask
}

/* Re-ask, and in auto mode reopen the mic, so a misheard answer does not strand the
   patient waiting for a prompt that already happened. Typing patients are left alone:
   the error banner has already told them what to fix. */
function reAskPhone() {
  if (state.identifyStep !== 'phone' || state.inputMode !== 'voice') return;
  askAloud(t(PHONE_PROMPT.en, PHONE_PROMPT.bn));
}

function reAskOtp() {
  if (state.identifyStep !== 'otp' || state.inputMode !== 'voice') return;
  askAloud(t(OTP_PROMPT.en, OTP_PROMPT.bn));
}

/* --- S36 (ADR-0057), Finding 7: "how much longer?" -------------------------------

   The conversation screen answered that question with nothing at all, and for the
   patient this kiosk is built for — elderly, often anxious, frequently at a computer
   for the first time — an interview of unknown length is its own reason to give up.

   ⚠ It is shown ONLY during the scripted opening, and that restriction is the honest
   part. INTAKE_SCRIPT has a known length, so "প্রশ্ন ২ / ৪" is a FACT. The M7 loop that
   follows ends on completeness and the turn cap, not on a count nobody knows in
   advance — so rather than invent a denominator that would drift ("Question 6 of 10"
   while the loop stops at 7), the chip simply goes away. A progress bar that lies is
   worse than no progress bar, and this project does not get to be approximate about
   what it knows. */
function renderConvoProgress() {
  const chip = document.getElementById('convo-progress');
  if (!chip) return;
  if (!inScriptedOpening() && state.scriptIndex < 0) { chip.style.display = 'none'; return; }
  const step = Math.min(state.scriptIndex + 1, INTAKE_SCRIPT.length);
  if (step < 1) { chip.style.display = 'none'; return; }
  const total = INTAKE_SCRIPT.length;
  chip.dataset.en = `Question ${step} of ${total}`;
  chip.dataset.bn = `প্রশ্ন ${bnDigits(step)} / ${bnDigits(total)}`;
  chip.textContent = t(chip.dataset.en, chip.dataset.bn);
  chip.style.display = 'inline-block';
}

function hideConvoProgress() {
  const chip = document.getElementById('convo-progress');
  if (!chip) return;
  chip.style.display = 'none';
  /* Cleared, not just hidden — the same rule endSession() follows for the previous
     patient's words. A hidden element still holding "Question 2 of 4" is one language
     toggle or one stray render away from being visible again on the wrong screen. */
  chip.textContent = '';
  chip.dataset.en = '';
  chip.dataset.bn = '';
}

/* F4: ask INTAKE_SCRIPT[index]. Goes through assistantSays(), so the question is
   shown, spoken, recorded as a system utterance, and (in auto mode) opens the mic —
   identical handling to an M7 question. */
async function askScriptedQuestion(index) {
  state.scriptIndex = index;
  renderConvoProgress();   // S36: the step count follows the script, not a guess
  const q = INTAKE_SCRIPT[index];
  await assistantSays({ en: q.en, bn: q.bn });   // P1-2: pair → follows the toggle
}

function inScriptedOpening() {
  return state.scriptIndex >= 0 && state.scriptIndex < INTAKE_SCRIPT.length - 1;
}

/* --- screen 3: the voice conversation --- */

let recognition = null;
let listening = false;
let finalBuffer = '';

/* KIOSK-7 + F5b: the ONE recognition engine serves FOUR docks — the two
   identification screens, the conversation screen, and the summary-screen resume dock.
   This picks the active one's elements.
   ⚠ Identification is checked FIRST and deliberately: it runs BEFORE state.visitUuid
   exists, so a spoken phone number reaching the conversation branch would be POSTed as
   a clinical turn to a visit that has not been created yet. */
function activeDock() {
  if (state.identifyStep) return DOCKS[state.identifyStep];
  return state.resumeActive ? DOCKS.resume : DOCKS.conversation;
}

/* F5b: the identification docks override the typing hint, because there is no Send
   button on those screens and nothing there is an "answer" — telling a patient to press
   a control that does not exist is how a kiosk reads as broken. A dock with no `hints`
   key keeps MODE_HINTS exactly as before. */
const IDENTIFY_HINTS = {
  voice: { en: 'Tap the mic and say the digits', bn: 'মাইকে চাপ দিয়ে সংখ্যাগুলো বলুন' },
  type: { en: 'Type the digits, then press Enter', bn: 'সংখ্যাগুলো টাইপ করে এন্টার চাপুন' },
};

/* S2 (ADR-0048): every dock, so an input-mode switch applies everywhere at once — the
   patient picks Speak-or-Type ONCE, on whatever screen they happen to be on, and it
   holds all the way from their phone number to the last follow-up question.
   F5b: `phone` and `otp` deliberately declare NO `fallback` row. The number field and
   the OTP boxes are the typed path AND the display of what was heard, so they must stay
   visible in voice mode; setInputMode() guards every lookup, so omitting the key is the
   way to say "this dock has nothing to show and hide". `input` is still given, because
   that is only used to place the cursor when the patient switches to typing. */
const DOCKS = {
  conversation: {
    transcript: 'dock-transcript', mic: 'mic-btn', hint: 'listening-hint',
    fallback: 'fallback-row', input: 'fallback-input',
    voiceBtn: 'mode-voice-btn', typeBtn: 'mode-type-btn',
    countdown: 'dock-countdown', countdownDigit: 'dock-countdown-digit',
    // S34: the read-back panel for a captured spoken answer (ADR-0055).
    confirmPanel: 'dock-answer-confirm', confirmText: 'dock-answer-text',
  },
  resume: {
    transcript: 'resume-transcript', mic: 'resume-mic-btn', hint: 'resume-hint',
    fallback: 'resume-fallback-row', input: 'resume-fallback-input',
    voiceBtn: 'resume-mode-voice-btn', typeBtn: 'resume-mode-type-btn',
    countdown: 'resume-countdown', countdownDigit: 'resume-countdown-digit',
    confirmPanel: 'resume-answer-confirm', confirmText: 'resume-answer-text',
  },
  phone: {
    transcript: 'phone-transcript', mic: 'phone-mic-btn', hint: 'phone-hint',
    input: 'phone-input', hints: IDENTIFY_HINTS,
    voiceBtn: 'phone-mode-voice-btn', typeBtn: 'phone-mode-type-btn',
    countdown: 'phone-countdown', countdownDigit: 'phone-countdown-digit',
    // S34: the live "digits so far" line — see renderDigitPreview().
    digitPreview: 'phone-digit-preview',
  },
  otp: {
    transcript: 'otp-transcript', mic: 'otp-mic-btn', hint: 'otp-hint',
    input: 'otp-input-1', hints: IDENTIFY_HINTS,
    voiceBtn: 'otp-mode-voice-btn', typeBtn: 'otp-mode-type-btn',
    countdown: 'otp-countdown', countdownDigit: 'otp-countdown-digit',
    digitPreview: 'otp-digit-preview',
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
/* S41 — the sentence now LEADS with the fact, not with the machine's status.
   "Listening..." describes what the kiosk is doing; a patient who has never used a
   computer needs to be told what THEY should do, and told it in the first two words.
   The instruction that follows is unchanged, because it is still true and still the
   only thing they need after that.
   ⚠ Written HERE, in the one constant every dock reads through listeningHint(), so the
   phone screen, the OTP screen, the conversation and the resume dock all say the same
   thing without a second implementation and without four copies of the wording. */
const LISTENING_HINT = {
  auto: { en: '🎤 You can speak now — stop when you are finished',
          bn: '🎤 এখন কথা বলুন — বলা শেষ হলে থেমে যান' },
  manual: { en: '🎤 You can speak now — tap again when done',
            bn: '🎤 এখন কথা বলুন — বলা শেষে আবার চাপুন' },
};

function modeHint(dock) {
  const hints = (dock && dock.hints) || MODE_HINTS;
  return hints[(state && state.inputMode) || 'voice'];
}

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
  // S34: same rule for a spoken answer still awaiting its read-back OK — a patient who
  // switches to typing has chosen to answer again, in writing.
  if (typing) hideAnswerConfirm();
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
    setBilingualText(dock.hint, modeHint(dock).en, modeHint(dock).bn);
  });
  if (typing && focus) {
    const input = document.getElementById(activeDock().input);
    if (input) input.focus();
  }
}

/* The Web Speech API has 8 error codes and only SOME are fatal. This map is the
   TERMINAL set: the engine will never produce text on its own, so the patient must be
   told and moved to typing. Everything absent from it — above all `no-speech` and
   `aborted` — is TRANSIENT and MUST fall through to `onend`, because that restart IS
   what keeps continuous listening alive in Chrome (part of the passed S29 live run).
   ⚠ Do not "simplify" this into stopping on every error: that would regress Chrome.

   Before this map, only `not-allowed` and `audio-capture` were handled, so
   `language-not-supported` (exactly what Edge emits if its backend rejects `bn-BD`),
   `network` and `service-not-allowed` left `listening === true` and `onend` restarted
   forever — start → error → end → start, with no message, no typing fallback and no
   countdown (the countdown arms only after real words arrive). A silent dead end.

   The wording separates a dead MIC from a dead SPEECH SERVICE: at a demo those need
   different responses, and telling a patient the microphone failed when the recognizer
   rejected the language is simply false. */
const MIC_UNAVAILABLE = {
  en: 'Microphone unavailable — you can type instead.',
  bn: 'মাইক্রোফোন পাওয়া যায়নি — টাইপ করতে পারেন।',
};
const STT_SERVICE_UNAVAILABLE = {
  en: 'Speech recognition is unavailable — you can type instead.',
  bn: 'স্পিচ রিকগনিশন কাজ করছে না — টাইপ করতে পারেন।',
};
const STT_LANGUAGE_UNSUPPORTED = {
  en: 'This browser cannot recognise Bangla speech — you can type instead.',
  bn: 'এই ব্রাউজারে বাংলা স্পিচ রিকগনিশন কাজ করছে না — টাইপ করতে পারেন।',
};
const TERMINAL_STT_ERRORS = {
  'not-allowed': MIC_UNAVAILABLE,
  'audio-capture': MIC_UNAVAILABLE,
  'network': STT_SERVICE_UNAVAILABLE,
  'service-not-allowed': STT_SERVICE_UNAVAILABLE,
  'language-not-supported': STT_LANGUAGE_UNSUPPORTED,
};

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
    scrollTranscriptToEnd(el);   // S41: the newest words stay visible inside the box
    // S34: on the identification docks, show the DIGITS this utterance means so far.
    renderDigitPreview(live);
    /* S36 (ADR-0057), Finding 4: eleven valid digits ARE the end of this turn. Checked
       before the endpointer below, because the whole point is not to start a silence
       window the number has already made unnecessary — and because everything after
       this point belongs to a turn that no longer exists. */
    if (maybeCompletePhone(live)) return;
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
    const message = TERMINAL_STT_ERRORS[e.error];
    if (!message) return;   // transient (no-speech / aborted): onend restarts, as before
    showError(t(message.en, message.bn));
    stopListening(false);   // sets listening = false — this is what breaks the restart loop
    setInputMode('type');   // S2: never leave the patient stranded on a dead mic
    // P1: the face says so too, and expires with the banner (both 8 s) so the two can
    // never disagree about whether the kiosk is currently broken.
    setAvatarOverride('error', { clearAfterMs: 8000 });
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
  /* ⚠ S35 (ADR-0056) REMOVED an old `hideAnswerConfirm()` from here. S34 read "the
     patient is speaking again, so they mean 'say it again'" — a heuristic that was
     reasonable when the only way to answer the read-back was a tap. Now the read-back
     IS answered by speaking, and this line would have cleared `state.pendingAnswer`
     between the mic opening and the word "হ্যাঁ" arriving — so the patient's verdict
     would have been stored as their symptom. All speech while a read-back is open is a
     verdict; parseConfirmation() decides, and an ordinary sentence is ambiguous. */
  document.getElementById(activeDock().mic).classList.add('listening');
  setBilingualText(activeDock().hint, listeningHint().en, listeningHint().bn);   // S4: mode-aware
  ttsCancel();   // ADR-0049: silences server audio too, not just speechSynthesis
  try { recognition.start(); } catch (_) {}   // already-started engine throws InvalidStateError
  /* S40 (1C): the microphone is open, so the place the patient speaks into must be on
     screen. ONE call site for both paths — a tap and the S3 auto-open both arrive here,
     which is the same "one code path, not two" this function already relies on. */
  bringIntoView(activeDock().mic);
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
  setBilingualText(activeDock().hint, modeHint(activeDock()).en, modeHint(activeDock()).bn);   // S2: mode-aware
  if (recognition) try { recognition.stop(); } catch (_) {}
  const text = finalBuffer.trim();
  setBilingualText(activeDock().transcript, '', '');   // P1-2: clear dataset too
  clearDigitPreview();                                 // S34: and the derived digits
  if (sendTurn && text) {
    /* F5b: identification first — see activeDock(). These two branches never touch a
       visit; they read digits out of the utterance and drive the screen the patient is
       actually on. Everything below them is the clinical path, unchanged. */
    if (state.identifyStep === 'phone') applySpokenPhone(text);
    else if (state.identifyStep === 'otp') applySpokenOtp(text);
    /* S35 (ADR-0056): a read-back is open, so this utterance is the patient's VERDICT
       on it — "হ্যাঁ" or "না" — and never a new answer. It must be checked before the
       clinical branches below or the word "হ্যাঁ" would be stored as their symptom. */
    else if (state.pendingAnswer) applySpokenConfirmation(text);
    /* S35 (ADR-0056), Finding 7: the review screen is waiting for the patient to approve
       the whole pre-screening. Same parser, same rules — a verdict, never an answer. */
    else if (state.reviewConfirm) applyReviewConfirmation(text);
    /* S36 (ADR-0057), Finding 5: the correction question is open and the patient has
       said there is nothing to correct ("ঠিক আছে", "all right"). Checked BEFORE the
       read-back gate below, or the kiosk would read "ঠিক আছে" back as though it were a
       symptom and then store it as one. */
    else if (maybeFinishReview(text)) { /* the review is finished — see maybeFinishReview */ }
    /* S34 (ADR-0055): a CLINICAL spoken answer is read back to the patient before it is
       stored. holdForConfirmation() returns true when it has taken ownership of this
       turn — either because the capture was unusable (re-ask, never guess) or because
       the read-back panel is now waiting for the patient. The two submit calls below are
       then made by acceptAnswer(), with the identical arguments: one pipeline, one
       `source`, no second path (ADR-0048). */
    else if (holdForConfirmation(text)) { /* waiting for the patient — see acceptAnswer */ }
    else if (state.resumeActive) submitResumeAnswer(text, 'mic');
    else submitPatientTurn(text, 'mic');
  } else if (sendTurn && !state.identifyStep) {
    // Nothing usable was captured. Silence is NOT an answer: ask the same question
    // again rather than storing an empty turn or inventing one (rule #1 / rule #2).
    reAskUnclearAnswer();
  }
}

/* --- S34 (ADR-0055): "this is what I heard" — the spoken-answer read-back ---------

   The gap this closes: between S4 and now, a spoken answer went straight from the
   recogniser into the patient's permanent record. The patient never heard what the
   machine understood, and the only way to discover a mis-recognition was to read it
   off a chat bubble — which the target patient (elderly, possibly not literate, quite
   possibly not wearing their glasses) cannot be assumed to do.

   So a captured answer is now SHOWN large, SPOKEN back in the patient's own words, and
   held until they accept it. Three rules shape it:
     * it is the PATIENT's words, verbatim, never a cleaned-up paraphrase (rule #1);
     * nothing is stored until they accept — a rejected capture was never an utterance,
       so rejecting it edits nothing;
     * an unusable capture is NEVER guessed at. The same question is asked again.

   The read-back is deliberately NOT a question the mic should answer, so it uses plain
   speak() and cancels any pending auto-open — the same rule the per-bubble 🔊 follows. */

/* S35: the prompt now TELLS the patient the two words that work, because a question
   the patient can answer but does not know they may answer aloud is a question they
   will look for a button for. */
const ANSWER_CONFIRM_PROMPT = {
  en: 'Is this correct? Say yes, or say no.',
  bn: 'এটা কি ঠিক আছে? হ্যাঁ বলুন অথবা না বলুন।',
};

const CONFIRM_NOT_UNDERSTOOD = {
  en: 'Sorry — please say yes, or say no.',
  bn: 'দুঃখিত — অনুগ্রহ করে "হ্যাঁ" বলুন অথবা "না" বলুন।',
};

const UNCLEAR_ANSWER = {
  en: 'Sorry, I did not catch that — let me ask again.',
  bn: 'দুঃখিত, আমি বুঝতে পারিনি — প্রশ্নটি আবার করছি।',
};

/** Is there anything here a human would call an answer? Deterministic and local: at
 *  least one letter or digit. No model, no confidence threshold, no guessing — pure
 *  punctuation or an empty capture is not an answer, and EVERYTHING else is the
 *  patient's to accept or reject rather than ours to judge. Erring toward "let them
 *  decide" is the safe direction; silently discarding real words is not. */
function isUnclearAnswer(text) {
  return !/[\p{L}\p{N}]/u.test(String(text || ''));
}

/** The question the patient is answering RIGHT NOW, whichever dock owns the turn. */
function currentQuestionText() {
  if (state.resumeActive) {
    if (state.resumeQuestion) return state.resumeQuestion.question_text;
    if (state.resumeScripted) return t(state.resumeScripted.en, state.resumeScripted.bn);
  }
  return state.lastQuestionText;
}

/** Ask the SAME question again. Used when the capture was unusable and when the patient
 *  rejects the read-back — in both cases the previous question is still unanswered, and
 *  moving on would mean answering it with something the patient never said. askAloud()
 *  re-opens the mic in auto mode, so correcting costs no extra tap. */
function reAskUnclearAnswer() {
  if (state.identifyStep || state.inputMode !== 'voice') return;
  const question = currentQuestionText();
  if (!question) return;
  showError(t(UNCLEAR_ANSWER.en, UNCLEAR_ANSWER.bn));
  askAloud(question);
}

/** The single gate on the spoken-answer path. Returns TRUE when it has taken ownership
 *  of this turn, which is the caller's signal not to submit. */
function holdForConfirmation(text) {
  if (isUnclearAnswer(text)) { reAskUnclearAnswer(); return true; }
  if (!voiceConfig.answer_confirm) return false;   // clinic opted out — S25-era flow
  offerSpokenAnswer(text, state.resumeActive ? 'resume' : 'conversation');
  return true;
}

function offerSpokenAnswer(text, scope) {
  state.pendingAnswer = { text, scope };
  showAnswerConfirm(text);
  speakAnswerBack(text);
}

/* Both clinical docks are written together, exactly like showCountdown() — one of the
   two screens is visible at a time, and keeping them in step means the patient can
   never see a stale panel after a screen change. */
function showAnswerConfirm(text) {
  Object.values(DOCKS).forEach((dock) => {
    const panel = dock.confirmPanel ? document.getElementById(dock.confirmPanel) : null;
    if (panel) panel.style.display = 'flex';
    const box = dock.confirmText ? document.getElementById(dock.confirmText) : null;
    // No data-en/data-bn: these are the patient's own words and are never translated
    // or re-rendered by the language toggle (rule #1, same as a patient bubble).
    if (box) box.textContent = text;
  });
  /* Measured, not assumed: opening this panel makes the dock taller than the viewport,
     so on a laptop screen the two buttons land BELOW THE FOLD — the patient hears their
     answer read back and sees nothing to press. Same defect, same proven fix as
     showPhoneConfirm(): force layout to be current (in this tick it is still stale and
     scrollIntoView is a silent no-op), then bring the panel up.
     ⚠ S40: both halves now live in bringIntoView(), which every "bring this into view"
     call site shares — the forced reflow did not go away, it moved. */
  /* S40 (1D): publish "an answer is waiting to be checked" so the CSS can make the
     read-back the ONLY emphasised thing on screen. Set in exactly the two functions
     that open and close this gate, so it cannot drift: it is not a second state
     machine, it is this one gate reporting itself, the same way `data-kiosk-state` is
     the derived avatar state reporting itself. */
  document.body.dataset.kioskStage = 'confirming';
  const active = activeDock();
  const panel = active.confirmPanel ? document.getElementById(active.confirmPanel) : null;
  if (!panel) return;
  bringIntoView(panel);   // S40: the shared helper — same 'nearest', now reduced-motion aware
}

function hideAnswerConfirm() {
  if (state) state.pendingAnswer = null;
  // S40 (1D): the gate is closed - the rest of the dock comes back to full strength.
  delete document.body.dataset.kioskStage;
  Object.values(DOCKS).forEach((dock) => {
    const panel = dock.confirmPanel ? document.getElementById(dock.confirmPanel) : null;
    if (panel) panel.style.display = 'none';
  });
}

/* Two utterances in sequence, each in the voice it needs: the patient's own words were
   captured at lang='bn-BD' and are read back VERBATIM (the TTS-1 bilingual split must
   not touch them — half of an answer is not an answer), then the confirmation question
   follows in the UI language. speak() cancels whatever is playing, so chaining on
   `onend` is what stops the two from cutting each other off. */
function speakAnswerBack(text) {
  cancelPendingMic();   // nothing may open the mic while the read-back is still playing
  speak(text, {
    lang: 'bn-BD',
    verbatim: true,
    // Guarded: if the patient has already decided, the prompt is moot and would talk
    // over whatever comes next.
    onend: () => { if (state && state.pendingAnswer) askConfirmationAloud(); },
  });
}

/* S35 (ADR-0056): the confirmation question goes through askAloud(), so the mic opens
   itself once it has been spoken — the patient answers "হ্যাঁ" or "না" without touching
   anything. This is the ONLY difference from S34's read-back, and it is deliberately
   the same seam the interview questions use: no second turn-taking path exists. */
function askConfirmationAloud() {
  askAloud(t(ANSWER_CONFIRM_PROMPT.en, ANSWER_CONFIRM_PROMPT.bn));
}

/** A spoken turn that arrived while a read-back was waiting. It is a VERDICT, never an
 *  answer: routing it anywhere else would store "হ্যাঁ" as the patient's symptom. */
function applySpokenConfirmation(rawText) {
  const verdict = parseConfirmation(rawText);
  if (verdict === 'yes') { acceptAnswer(); return; }
  if (verdict === 'no') { rejectAnswer(); return; }
  /* Neither. Never guess — ask the SAME confirmation again, with the answer still on
     screen and still unsent. The read-back is not repeated: the patient has already
     heard their own words, and repeating them every time the recogniser mishears a
     "yes" would be its own kind of trap. */
  showError(t(CONFIRM_NOT_UNDERSTOOD.en, CONFIRM_NOT_UNDERSTOOD.bn));
  if (state.inputMode === 'voice') askConfirmationAloud();
}

/** "Yes, that is what I said." Only now does the answer enter the pipeline — and it
 *  enters through exactly the same call the un-gated path used, with the same `source`,
 *  so there is still ONE question/answer path (ADR-0048). */
function acceptAnswer() {
  const pending = state && state.pendingAnswer;
  if (!pending) return;
  const text = pending.text;
  const scope = pending.scope;
  hideAnswerConfirm();
  ttsCancel();   // the patient has decided; the read-back has nothing left to say
  if (scope === 'resume') submitResumeAnswer(text, 'mic');
  else submitPatientTurn(text, 'mic');
}

/** "No — say it again." The capture is dropped (it was never stored, so nothing is
 *  edited) and the SAME question is put again. */
function rejectAnswer() {
  if (!state || !state.pendingAnswer) return;
  hideAnswerConfirm();
  ttsCancel();
  const question = currentQuestionText();
  if (question) askAloud(question);
  else if (state.inputMode === 'voice' && !listening) toggleListening();
}

/* --- P1: the robotic doctor's state machine -------------------------------------

   The avatar exists to answer ONE question without words: "is it my turn?" That only
   works if it can never be wrong, so every state is DERIVED from the same variables
   the rest of the kiosk already acts on. There is no setAvatarState('speaking') call
   sprinkled at call sites that could drift out of sync with reality — there is one
   reader, and it reads the truth.

   ⚠ Order is the contract, not a style choice:
     * LISTENING outranks everything. The mic being open is the one state a patient
       must never be wrong about (rule #1 — a patient who thinks it is not listening
       stops talking mid-answer).
     * SPEAKING outranks PROCESSING because `state.busy` stays TRUE across
       assistantSays() — the assistant starts talking while the turn is still "busy",
       so testing busy first would show "please wait" over a talking doctor.
     * PROCESSING is last, which makes it the honest meaning of busy: work with no
       audible output.
   Anything else is idle. */
/* S34: a THIRD mount — the floating assistant on the review screen. Same component,
   same derived state, no second state machine: the review page is where the patient is
   asked to approve their own record, so the "is it my turn / is it talking to me" cue
   matters there at least as much as during the interview. */
const AVATAR_IDS = ['doctor-avatar', 'resume-avatar', 'summary-avatar'];
const AVATAR_STATUS_IDS = ['doctor-status', 'summary-status'];
const AVATAR_SUBSTATUS_IDS = ['doctor-substatus', 'summary-substatus'];

const AVATAR_STATES = {
  idle: {
    en: 'Ready when you are', bn: 'আপনি প্রস্তুত হলেই শুরু করুন',
    sub: { en: 'Your AI health assistant', bn: 'আপনার এআই স্বাস্থ্য সহকারী' },
  },
  speaking: {
    en: 'I am speaking — please listen', bn: 'আমি বলছি — শুনুন',
    sub: { en: 'The question is also written below', bn: 'প্রশ্নটি নিচে লেখাও আছে' },
  },
  listening: {
    en: 'Listening — please speak now', bn: 'শুনছি — এখন বলুন',
    sub: { en: 'Take your time', bn: 'তাড়াহুড়োর দরকার নেই' },
  },
  processing: {
    en: 'Please wait a moment', bn: 'একটু অপেক্ষা করুন',
    sub: { en: 'I am reading your answer', bn: 'আপনার উত্তরটি পড়ছি' },
  },
  done: {
    en: 'All done — thank you', bn: 'সব শেষ — ধন্যবাদ',
    sub: { en: 'Your answers are with the doctor', bn: 'আপনার উত্তর ডাক্তারের কাছে গেছে' },
  },
  error: {
    en: 'Something went wrong', bn: 'কিছু একটা সমস্যা হয়েছে',
    sub: { en: 'You can type your answer instead', bn: 'আপনি টাইপ করেও উত্তর দিতে পারেন' },
  },
};

let avatarState = null;       // last APPLIED state — the DOM is only touched on a change
let avatarOverride = null;    // 'done' | 'error': terminal states real state cannot express

function currentAvatarState() {
  if (avatarOverride) return avatarOverride;
  if (!state) return 'idle';
  if (listening) return 'listening';
  // ADR-0049: ttsSpeaking(), never speechSynthesis.speaking — the latter is false while
  // the SERVER-TTS <audio> is playing, which is the whole Bangla path on Windows.
  if (typeof ttsSpeaking === 'function' && ttsSpeaking()) return 'speaking';
  if (state.busy || state.finishing) return 'processing';
  return 'idle';
}

function applyAvatarState(name) {
  const entry = AVATAR_STATES[name] || AVATAR_STATES.idle;
  AVATAR_IDS.forEach((id) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.dataset.avatarState = name;
    el.setAttribute('aria-label', t(entry.en, entry.bn));
  });
  AVATAR_STATUS_IDS.forEach((id) => setBilingualText(id, entry.en, entry.bn));
  AVATAR_SUBSTATUS_IDS.forEach((id) => setBilingualText(id, entry.sub.en, entry.sub.bn));
  /* S35 / Finding 3: publish the SAME derived state on <body>, so the whole page can
     answer "is it listening?" without a second state machine and without any call site
     being able to disagree with the avatar. The CSS uses it to make the microphone
     pulse and the dock hint loud while listening — cues a patient who cannot read the
     status line, or is not looking at the robot, still cannot miss. */
  document.body.dataset.kioskState = name;
}

function refreshAvatar() {
  const next = currentAvatarState();
  if (next === avatarState) return;   // no DOM write, so animations are never restarted
  avatarState = next;
  applyAvatarState(next);
}

/* 'done' and 'error' are the two states NO live variable can express: the work is over,
   or it failed. They are the only states allowed to be pushed rather than derived, which
   is why they carry an expiry — an error face left up after the patient has recovered
   would be exactly the lie the derived states exist to prevent. Pass null to clear.
   ⚠ Never called from resetState(): that runs at module load, where `avatarOverride`
   is still in its temporal dead zone. */
function setAvatarOverride(name, { clearAfterMs = 0 } = {}) {
  avatarOverride = name;
  clearTimeout(setAvatarOverride._t);
  if (clearAfterMs) {
    setAvatarOverride._t = setTimeout(() => { avatarOverride = null; refreshAvatar(); }, clearAfterMs);
  }
  refreshAvatar();
}

/* Polled rather than event-driven, deliberately: speech has no "still speaking" event
   on EITHER path — speechSynthesis fires only start/end, and the server-TTS fallback is
   an <audio> element whose request latency is part of "speaking" (ADR-0049). Polling the
   same predicate the echo guard uses is what keeps the avatar and the microphone
   agreeing. 200 ms is under the ~250 ms at which a turn change starts to feel laggy, and
   refreshAvatar() writes nothing when the state has not changed. */
const AVATAR_POLL_MS = 200;
setInterval(refreshAvatar, AVATAR_POLL_MS);

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
  /* S36 (ADR-0057): every write below this line happens AFTER an await, so each one
     must first prove it still belongs to the patient on screen. Without it, a followup
     answer that resolves late spoke the previous patient's next question into the new
     patient's thread and set it as their `activeQuestion`. */
  const mine = sessionToken();
  addBubble('patient', rawText, { en: 'Your words', bn: 'আপনার কথা' });
  try {
    if (state.activeQuestion) {
      // Answer to an M7 question -> M8 merge + M9 check + next question, one call.
      const res = await api('POST', `/api/visits/${state.visitUuid}/followup/answer`, {
        question_id: state.activeQuestion.id, raw_text: rawText,
        source, stt_provider: source === 'mic' ? 'browser_webspeech' : 'manual',
      });
      if (!mine()) return;
      state.activeQuestion = res.next_question || null;
      if (res.complete) await finishConversation();
      else await assistantSays(res.next_question.question_text, { record: false });
    } else if (inScriptedOpening()) {
      /* F4: a scripted answer that is NOT the last one. Store it verbatim and move to
         the next scripted question — intake deliberately waits until the whole
         opening is in, so M3 extracts area, name, age and the complaint from one
         complete conversation instead of re-running per turn. */
      await api('POST', `/api/visits/${state.visitUuid}/utterances`, {
        raw_text: rawText, role: 'patient', source,
        stt_provider: source === 'mic' ? 'browser_webspeech' : 'manual',
      });
      if (!mine()) return;
      await askScriptedQuestion(state.scriptIndex + 1);
    } else {
      // Free opening turn(s): store, then run intake and start the loop.
      state.scriptIndex = -1;   // F4: the scripted opening is finished
      hideConvoProgress();      // S36: past here the remaining count is genuinely unknown
      await api('POST', `/api/visits/${state.visitUuid}/utterances`, {
        raw_text: rawText, role: 'patient', source,
        stt_provider: source === 'mic' ? 'browser_webspeech' : 'manual',
      });
      await api('POST', `/api/visits/${state.visitUuid}/intake`);
      if (!mine()) return;
      state.intakeDone = true;
      const res = await api('POST', `/api/visits/${state.visitUuid}/followup/next`);
      if (!mine()) return;
      if (res.complete) await finishConversation();
      else {
        state.activeQuestion = res.question;
        await assistantSays(res.question.question_text, { record: false });
      }
    }
  } catch (e) {
    if (!mine()) return;   // an error from a finished session is not this patient's problem
    showError(e.message);
  }
  if (!mine()) return;     // …and neither is clearing their busy flag
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
  const mine = sessionToken();   // S36: nothing below may land on the next patient's screen
  cancelPendingMic();   // S3: "Done" ends the conversation — no mic may open behind it
  /* S34: a read-back still waiting for an answer belongs to the question the patient
     has just walked away from. Retract it so it cannot follow them onto the summary.
     ⚠ The captured words are dropped, exactly like the mid-turn `stopListening(false)`
     discard below — the SAME open rule #1 decision recorded in current_task.md, not a
     new one taken here. */
  hideAnswerConfirm();
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
      if (!mine()) return;
      state.intakeDone = true;
    }
    const profile = await api('GET', `/api/visits/${state.visitUuid}/profile`);
    /* S36: the previous patient's summary must never be drawn onto — nor navigated to
       on — the new patient's screen. This is the last await before both happen. */
    if (!mine()) return;
    renderSummary(profile);
    showScreen('screen-summary');
    await refreshResumeLoop(profile);   // KIOSK-7: fill remaining fields before submit
  } catch (e) {
    if (!mine()) return;
    showError(e.message);
  }
  if (!mine()) return;
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
    /* S34 — "what did I say?" on the review screen. Everything above this line asks the
       patient to CHECK the summary, and until now checking it meant reading it. A
       patient who cannot read the screen — no glasses, low literacy, a language they
       speak but do not read — had no way to review their own pre-screening at the one
       moment they are asked to approve it. Every filled card can now be heard. */
    if (text) {
      const hear = document.createElement('button');
      hear.className = 'bubble-speak';
      hear.type = 'button';
      hear.textContent = '🔊';
      hear.dataset.titleEn = 'Hear this answer';
      hear.dataset.titleBn = 'এই উত্তরটি শুনুন';
      hear.title = t(hear.dataset.titleEn, hear.dataset.titleBn);
      hear.onclick = () => speakSummaryField(key, text);
      head.appendChild(hear);
    }
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

/* --- S34: hearing the review, not just reading it --------------------------------

   The summary values are DERIVED (M3's extraction of what the patient said), never the
   raw transcript — so this reads back the same text the card displays, in the same
   language the card is displaying it in. `verbatim: true` opts out of the TTS-1
   bilingual split: a summary value is not an M7 "<Bangla> (<English>)" question, and
   letting that regex near it could cut a real answer in half.

   The per-card 🔊 and the read-through share one queue token so they can never talk over
   each other — speak() cancels the previous utterance, and without the token the killed
   utterance's onend would keep walking the list underneath the new one. */
let readAloudQueue = null;

function summaryRowText(key) {
  const fields = ((state.lastProfile || {}).entities || {}).summary_fields || {};
  return fieldValue(fields[key]);
}

function speakSummaryField(key, text) {
  readAloudQueue = null;   // one card wins over a running read-through
  const label = t(FIELD_LABELS[key].en, FIELD_LABELS[key].bn);
  speak(`${label}. ${text || summaryRowText(key)}`, { verbatim: true });
}

function summaryReadAloudActive() { return readAloudQueue !== null; }

function setReadAloudLabel(active) {
  setBilingualText('read-summary-btn',
    active ? '⏹ Stop' : '🔊 Hear my answers',
    active ? '⏹ থামান' : '🔊 আমার উত্তরগুলো শুনুন');
}

/** Read every filled card aloud, one after another. A second tap stops it — an elderly
 *  patient who started a two-minute read-through must be able to end it without hunting
 *  for a different control. */
function toggleSummaryReadAloud() {
  if (summaryReadAloudActive()) {
    readAloudQueue = null;
    ttsCancel();
    setReadAloudLabel(false);
    return;
  }
  const rows = Object.keys(FIELD_LABELS)
    .map((key) => ({ key, text: summaryRowText(key) }))
    .filter((row) => row.text);
  if (!rows.length) {
    speak(t('Nothing has been recorded yet.', 'এখনো কিছু রেকর্ড করা হয়নি।'), { verbatim: true });
    return;
  }
  const queue = rows.slice();
  readAloudQueue = queue;
  setReadAloudLabel(true);
  const next = () => {
    if (readAloudQueue !== queue) return;   // superseded by a newer request — stop here
    const row = queue.shift();
    if (!row) { readAloudQueue = null; setReadAloudLabel(false); return; }
    const label = t(FIELD_LABELS[row.key].en, FIELD_LABELS[row.key].bn);
    speak(`${label}. ${row.text}`, { verbatim: true, onend: next });
  };
  next();
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

/* --- S34 (ADR-0055): ONE countdown ticker, reused by every timed countdown --------

   The kiosk already had two hand-rolled countdowns before this — the S4 endpointer and
   the 5-second auto-logout — and the review clock would have been a third. So the
   generic half is extracted ONCE here and the logout countdown is moved onto it, which
   is also the proof that it is genuinely reusable rather than a wrapper written for one
   caller.

   ⚠ The S4 endpointer is deliberately NOT converted. It looks like the same thing and
   is not: its deadline is RESTARTED by every recognition result (that restart is the
   whole anti-clipping guarantee — rule #1), it renders in the middle of a live
   recognition turn, and it is pinned line-by-line by test_kiosk_countdown.py. Rewriting
   a rule #1 safeguard to share code with a UI clock would be trading a real guarantee
   for tidiness. Reuse where it is safe; leave the safety-critical one alone.

   The handle fires `onEnd` AT MOST ONCE — `done` is set before the callback so an
   onEnd that itself submits, navigates or starts another ticker cannot re-enter. */
function startTicker(totalMs, { onTick = null, onEnd = null, tickMs = 250 } = {}) {
  const deadline = Date.now() + Math.max(0, Number(totalMs) || 0);
  const handle = { timer: null, done: false };
  handle.cancel = () => {
    handle.done = true;
    clearInterval(handle.timer);
    handle.timer = null;
  };
  const tick = () => {
    if (handle.done) return;
    const remaining = Math.max(0, deadline - Date.now());
    if (onTick) onTick(Math.ceil(remaining / 1000), remaining);
    if (remaining > 0) return;
    handle.cancel();          // BEFORE onEnd, so onEnd can never be reached twice
    if (onEnd) onEnd();
  };
  tick();                     // paint the starting value now, not one tick late
  if (!handle.done) handle.timer = setInterval(tick, tickMs);
  return handle;
}

/* --- S34: the 60-second review clock ---------------------------------------------

   A finished pre-screening sitting unattended on the review screen helps nobody: the
   doctor never receives it and the kiosk is occupied. So the review submits itself.

   Three things make that safe rather than reckless:
     * it runs ONLY while Confirm & Submit is actually pressable — the same verdict the
       button uses (updateSubmitVisibility), so it can never fire into a case the server
       would refuse, and it can never submit while a required question is still open;
     * any manual action cancels it — pressing the button, going back to Speak Again,
       the post-submit reset;
     * one timeout = one submit. The ticker fires once and confirmSubmit() carries its
       own re-entry guard, so the timeout and a simultaneous tap cannot both send. */
let reviewTicker = null;

/* S35 (ADR-0056) — ONE clock renderer for every countdown the patient can see.
   The element lives in the header (see kiosk.html), which sits outside the scrolling
   `.screen`, so it is always at the top right and can never be scrolled away from or
   overlapped. `label` is the {en,bn} pair for the unit, because "10 সেকেন্ড বাকি" and
   "10s to confirm" are different sentences, not the same one translated. */
const CLOCK_LABELS = {
  review: { en: 'left', bn: 'সেকেন্ড বাকি' },
  phone: { en: 'to send', bn: 'সেকেন্ড পরে যাবে' },
};

function renderClock(secondsLeft, label) {
  const box = document.getElementById('kiosk-clock');
  if (!box) return;
  box.style.display = 'flex';
  // Urgency is carried by a CLASS, not by rewriting the markup: the blink/pulse is CSS
  // and must not be restarted on every tick.
  box.classList.toggle('urgent', secondsLeft <= 10);
  /* The unit lives with the LABEL, not with the number: "৫৯s বাকি" is half-translated
     (measured on the live page) — Bangla wants "৫৯ সেকেন্ড বাকি", English wants
     "59s left". Same digits, two honest sentences. */
  setBilingualText('kiosk-clock-value', `${secondsLeft}s`, bnDigits(secondsLeft));
  setBilingualText('kiosk-clock-label', label.en, label.bn);
}

function hideClock() {
  const box = document.getElementById('kiosk-clock');
  if (!box) return;
  box.style.display = 'none';
  box.classList.remove('urgent');
}

function reviewTimeoutMs() {
  return Math.max(0, Number(voiceConfig.review_timeout_ms) || 0);
}

function startReviewTimer() {
  if (reviewTicker) return;            // idempotent: re-entering the screen never stacks
  const total = reviewTimeoutMs();
  if (!total) { hideClock(); return; }   // 0 = the clinic turned auto-submit off
  reviewTicker = startTicker(total, {
    onTick: (secondsLeft) => renderClock(secondsLeft, CLOCK_LABELS.review),
    onEnd: () => {
      reviewTicker = null;
      hideClock();
      confirmSubmit();                 // its own guard makes this exactly one submit
    },
  });
}

function cancelReviewTimer() {
  if (reviewTicker) reviewTicker.cancel();
  reviewTicker = null;
  hideClock();
}

/** "Speak Again" — back to the conversation. The clock must not keep running behind
 *  the screen the patient just left, or it would submit a review they walked away from. */
function reviewSpeakAgain() {
  cancelReviewTimer();
  stopReviewConfirmation();
  ttsCancel();
  showScreen('screen-voice');
}

/* --- S35 (ADR-0056), Finding 7: approving the whole review BY VOICE ----------------

   The last screen was also the last place a mouse was still required. It is now the
   same interaction as the per-answer read-back — the identical `parseConfirmation()`
   vocabulary and the identical "never guess" rule — differing only in what YES and NO
   mean here:

     YES -> submit (through confirmSubmit(), so the timeout and the tap and the spoken
            approval all pass the one re-entry guard and the visit is sent once);
     NO  -> re-open the KIOSK-7 resume dock with a correction question. That is not a
            new pipeline: `setResumeMode(null, entry)` already serves "a question that
            is not an M7 row", and `submitResumeAnswer()` already stores such an answer
            as an ordinary utterance, re-runs intake, re-renders the summary and
            re-evaluates the loop. The patient never leaves the review screen.

   It is armed by the SAME verdict that shows the submit button and starts the clock,
   so the kiosk can never be waiting for approval of a review the server would refuse. */

const REVIEW_CONFIRM_PROMPT = {
  en: 'Your answers are on the screen. Is everything correct? Say yes, or say no.',
  bn: 'আপনার দেওয়া তথ্য পর্দায় আছে। সবকিছু কি ঠিক আছে? হ্যাঁ বলুন অথবা না বলুন।',
};

/* The correction turn. Open on purpose — the patient says what is wrong in their own
   words, and M3 re-extracts it exactly as it would any other answer. Naming a specific
   card would mean asking them to read the screen, which is what voice-first exists to
   avoid. */
const REVIEW_CORRECTION = {
  key: 'review_correction',
  en: 'What would you like to correct? Please tell me in your own words.',
  bn: 'কোন তথ্যটি ঠিক করতে চান? নিজের ভাষায় বলুন।',
};

function startReviewConfirmation() {
  if (!state || state.reviewConfirm) return;   // idempotent — never ask twice over
  state.reviewConfirm = true;
  askAloud(t(REVIEW_CONFIRM_PROMPT.en, REVIEW_CONFIRM_PROMPT.bn));
}

function stopReviewConfirmation() {
  if (state) state.reviewConfirm = false;
}

function applyReviewConfirmation(rawText) {
  const verdict = parseConfirmation(rawText);
  if (verdict === 'yes') { stopReviewConfirmation(); confirmSubmit(); return; }
  if (verdict === 'no') { rejectReview(); return; }
  showError(t(CONFIRM_NOT_UNDERSTOOD.en, CONFIRM_NOT_UNDERSTOOD.bn));
  if (state.inputMode === 'voice') {
    askAloud(t(REVIEW_CONFIRM_PROMPT.en, REVIEW_CONFIRM_PROMPT.bn));
  }
}

/** "No — something is wrong." Nothing is submitted; the resume dock re-opens with a
 *  correction question and the clock stops, because the patient is now editing. */
function rejectReview() {
  stopReviewConfirmation();
  cancelReviewTimer();
  setResumeMode(null, REVIEW_CORRECTION);
}

/* --- S36 (ADR-0057), Finding 5: "ঠিক আছে" is an answer to the correction question ---

   Once rejectReview() has opened "কোন তথ্যটি ঠিক করতে চান?", the patient has one more
   thing they may reasonably want to say, and it is not a correction: that there is
   nothing to correct after all. They looked, or listened, and it is fine.

   Before this, that sentence had nowhere to go. "ঠিক আছে" fell through to the ordinary
   clinical path, was read back as though it were a symptom, and on ✔ was STORED as the
   patient's answer to `review_correction` — and the same question was asked again. The
   patient could not get out of the correction loop by speaking, which on a voice-first
   kiosk means they could not get out at all.

   It reuses `parseConfirmation()` — the same vocabulary, the same "every word must be
   known" rule — so there is no second confirmation system and a phrase added for one
   place works in the other. Only a YES ends the review:

     * an ordinary sentence is `null` and is therefore a real correction, which is the
       common case and reaches the existing pipeline completely unchanged;
     * `no` is left to that same pipeline too. On THIS question it is genuinely unclear
       ("no, nothing" or the start of a correction), and ending a patient's screening on
       an unclear signal is the one direction that cannot be undone.

   Submission goes through confirmSubmit(), so the spoken finish, the tap and the review
   clock all pass the ONE re-entry guard and the visit is sent exactly once — and if the
   server refuses for missing required information, its catch re-opens the outstanding
   question instead of stranding the patient (F3's rule, unchanged). */

function reviewCorrectionOpen() {
  return !!(state && state.resumeActive && state.resumeScripted
            && state.resumeScripted.key === REVIEW_CORRECTION.key);
}

/** Returns TRUE when it has taken ownership of this turn — the caller must not submit. */
function maybeFinishReview(text) {
  if (!reviewCorrectionOpen()) return false;
  if (parseConfirmation(text) !== 'yes') return false;   // a correction, or unclear: not ours
  ttsCancel();
  cancelPendingMic();   // the screening is over — nothing may re-open the mic behind it
  /* confirmSubmit() first: it sets `submitting` synchronously, before its first await,
     and updateSubmitVisibility() reads that flag — so closing the dock on the next line
     cannot re-arm the very approval question this answer just settled. */
  confirmSubmit();
  setResumeMode(null);   // dock closes; Finding 1's full-width grid and the float return
  return true;
}

/* --- F3: the patient cannot reach the doctor with required information missing. ---

   The SERVER owns the verdict (GET /readiness), so the screen and the submit guard
   can never disagree about what "complete" means. This function only renders it.

   ⚠ A FAILED readiness fetch must NOT hide the button. `state.readiness` stays null,
   which reads here as "unknown" and leaves submit reachable — otherwise one flaky
   request would trap the patient on the review screen with no way forward. Nothing is
   lost by that: confirmSubmit() sends ?require_complete=true, so an incomplete case
   is still refused by the server. The UI guides; the server enforces. */
function updateSubmitVisibility() {
  const blocked = state.resumeActive || (state.readiness && !state.readiness.complete);
  document.getElementById('confirm-submit-btn').style.display = blocked ? 'none' : '';
  renderRequiredNotice();
  /* S34: the review clock and the submit button share ONE verdict. A countdown toward a
     button that is not there — or toward a submit the server would refuse — would be a
     kiosk counting down to nothing.
     S35: the spoken approval is armed by that same verdict, for the same reason — the
     kiosk must never ask "is this correct?" about a review it could not submit. */
  /* S36 (ADR-0057): `submitting` joins the same verdict. A visit that is already being
     sent must not be asked about — re-arming the approval here would speak "is
     everything correct?" over the submit that answer had just triggered (Finding 5's
     spoken finish closes the dock, which lands exactly here). */
  if (blocked || submitting) { cancelReviewTimer(); stopReviewConfirmation(); }
  else { startReviewTimer(); startReviewConfirmation(); }
}

/* Name what is still needed, in the patient's language, using the SAME numbered
   labels as the cards above so "৭. অ্যালার্জি" on the notice and on the card are
   visibly the same thing. */
function renderRequiredNotice() {
  const notice = document.getElementById('required-notice');
  if (!notice) return;
  const missing = (state.readiness && !state.readiness.complete)
    ? (state.readiness.missing || []) : [];
  if (!missing.length) { notice.style.display = 'none'; notice.textContent = ''; return; }
  const names = missing
    .map((key) => (FIELD_LABELS[key] ? t(FIELD_LABELS[key].en, FIELD_LABELS[key].bn) : key))
    .join(', ');
  notice.textContent = t(
    `A few required details are still needed: ${names}`,
    `আরও কিছু প্রয়োজনীয় তথ্য বাকি আছে: ${names}`);
  notice.style.display = 'block';
}

/* F3: ask the server whether the patient may submit. Never throws — an unreachable
   server leaves the verdict `null` ("unknown"), which updateSubmitVisibility()
   deliberately treats as not-blocking. */
async function loadReadiness() {
  const mine = sessionToken();   // S36: one visit's verdict may never gate another's submit
  try {
    const verdict = await api('GET', `/api/visits/${state.visitUuid}/readiness`);
    if (!mine()) return null;
    state.readiness = verdict;
  } catch (e) {
    if (!mine()) return null;
    state.readiness = null;
  }
  return state.readiness;
}

/* F4: identity items (name, age, area) are required but are NOT among the 10 fields,
   so the M7 resume loop cannot ask for them. If extraction missed one — the patient
   answered "সবাই আমাকে চাচি ডাকে", or the age never parsed — this finds the ORIGINAL
   scripted question to re-ask. It is what stops requiring identity from ever trapping
   a patient on the review screen. */
function pendingScriptedRequirement() {
  const missing = (state.readiness && !state.readiness.complete)
    ? (state.readiness.missing || []) : [];
  for (const key of missing) {
    const entry = scriptEntry(key);
    if (entry) return entry;
  }
  return null;
}

/* One resume dock, two kinds of question: an M7 `question` row, or a re-asked
   scripted requirement. Everything downstream (dock visibility, TTS, auto-listen,
   the submit gate) is identical — only where the answer is POSTed differs. */
function setResumeMode(question, scripted = null) {
  state.resumeQuestion = question || null;
  state.resumeScripted = question ? null : scripted;
  state.resumeActive = !!(question || state.resumeScripted);
  const text = question
    ? question.question_text
    : (state.resumeScripted ? t(state.resumeScripted.en, state.resumeScripted.bn) : '');
  document.getElementById('resume-dock').style.display = state.resumeActive ? 'flex' : 'none';
  /* S34: exactly ONE assistant on screen at a time. The resume dock carries its own
     avatar (P1), so the floating one steps aside while a question is open rather than
     leaving the patient with two robots and no idea which one is talking to them. */
  const float = document.getElementById('summary-float');
  if (float) float.style.display = state.resumeActive ? 'none' : '';
  /* S36 (ADR-0057), Finding 1: hiding the float is only HALF of removing it. Its grid
     TRACK survives, and auto-placement then drops the summary cards into that narrow
     column (measured: 471px -> 170px, with a 231px card overflowing it) — the reported
     alignment break at the final question. These two lines are ONE decision and must
     always be written from the same expression; a test pins the pairing so they cannot
     drift apart. */
  const layout = document.querySelector('.summary-body');
  if (layout) layout.classList.toggle('no-float', state.resumeActive);
  if (state.resumeActive) {
    document.getElementById('resume-question').textContent = text;
    bringIntoView('resume-dock');   // S40 (1C): a new question must not open below the fold
    state.lastQuestionText = text;   // S34: so a rejected read-back re-asks THIS question
    askAloud(text);   // ADR-0028 + S3: spoken, then the mic arms itself
  } else {
    cancelPendingMic();   // this question is over — nothing it armed may still fire
  }
  /* F3: readiness decides, not just "is a question open".
     ⚠ S35: this MUST run after the branch above, not before it. It is what arms the
     spoken review approval, and the `cancelPendingMic()` on the else path would
     otherwise cancel the very microphone that approval needs — the prompt would be
     spoken and then nothing would listen for the answer. */
  updateSubmitVisibility();
}

async function refreshResumeLoop(profile) {
  const mine = sessionToken();   // S36
  const filled = renderProgress(profile);
  // F3: readiness is checked FIRST and always — a 10/10 grid is no longer proof that
  // the required items were covered, and an incomplete one is no longer a reason to
  // keep asking once the server is satisfied.
  const readiness = await loadReadiness();
  if (!mine()) return;   // S36: no question from a finished visit may open on this screen
  if (filled >= 10 && (!readiness || readiness.complete)) { setResumeMode(null); return; }
  // F4: identity first — a missing name/age/area is re-asked with its own scripted
  // question, because no M7 question can cover it.
  const scripted = pendingScriptedRequirement();
  if (scripted) { setResumeMode(null, scripted); return; }
  try {
    const res = await api('POST', `/api/visits/${state.visitUuid}/followup/next?scope=fields`);
    if (!mine()) return;   // S36: a question generated for the previous patient is never asked
    setResumeMode(res.complete ? null : res.question);
  } catch (e) {
    if (!mine()) return;
    showError(e.message);
    // Fail-open on the LOOP only: an API hiccup must not trap the patient behind a
    // question that never arrived. Submission itself is still gated by readiness
    // above and re-checked server-side by confirmSubmit().
    setResumeMode(null);
  }
}

function repeatResumeQuestion() {
  if (state.resumeQuestion) speak(state.resumeQuestion.question_text);
  else if (state.resumeScripted) speak(t(state.resumeScripted.en, state.resumeScripted.bn));
}

function sendResumeTyped() {
  const input = document.getElementById('resume-fallback-input');
  const text = input.value.trim();
  if (!text) return;
  input.value = '';
  submitResumeAnswer(text, 'manual');
}

async function submitResumeAnswer(rawText, source) {
  if (state.busy || !(state.resumeQuestion || state.resumeScripted)) return;
  state.busy = true;
  /* S36 (ADR-0057): without this, a late resume answer called renderSummary() with the
     PREVIOUS patient's profile — their ten answer cards drawn onto the new patient's
     review screen. This is the exact "old patient's information appears in the new
     patient's session" report. */
  const mine = sessionToken();
  const sttProvider = source === 'mic' ? 'browser_webspeech' : 'manual';
  try {
    if (state.resumeScripted) {
      /* F4: a re-asked identity requirement. Stored as an ORDINARY patient turn
         (same endpoint, same verbatim rules) and then intake re-runs, so M3 harvests
         the name/age/area from it exactly as it would from the scripted opening. */
      await api('POST', `/api/visits/${state.visitUuid}/utterances`, {
        raw_text: rawText, role: 'patient', source, stt_provider: sttProvider,
      });
      await api('POST', `/api/visits/${state.visitUuid}/intake`);
    } else {
      await api('POST',
        `/api/visits/${state.visitUuid}/followup/answer?scope=fields`, {
          question_id: state.resumeQuestion.id, raw_text: rawText,
          source, stt_provider: sttProvider,
        });
    }
    if (!mine()) return;
    const profile = await api('GET', `/api/visits/${state.visitUuid}/profile`);
    if (!mine()) return;   // a profile fetched for a finished visit is never drawn
    renderSummary(profile);          // spec: the summary regenerates automatically
    /* Re-evaluate from scratch: refreshResumeLoop re-reads readiness and picks the
       next thing to ask, so both branches converge on ONE decision point instead of
       each guessing what should come next. */
    await refreshResumeLoop(profile);
  } catch (e) {
    if (!mine()) return;
    showError(e.message);
  }
  if (!mine()) return;
  state.busy = false;
}

/* KIOSK-4: export the RAW conversation as .docx BEFORE any AI summarization is
   accepted. Backend writer is verbatim (rule #1); no new backend code — reuses the
   step-3 endpoint. The anchor click (not location.href) keeps the kiosk page put.

   S36 (ADR-0057), Finding 6: the same export now also runs BY ITSELF the moment a
   screening is submitted, so the patient leaves with their own unedited record without
   being asked to find a button. The `auto` flag is the only difference between the two
   callers, and it controls exactly two things — the once-per-visit guard, and silence:
   an automatic download that fails must not throw an error banner over the "all done"
   screen, because the patient has nothing to do about it and their visit was submitted
   either way. The button stays for a deliberate re-download. */
let autoTranscriptDownloaded = false;

async function downloadRawTranscript({ auto = false } = {}) {
  // "Repeated finish events do not create multiple downloads": the submit guard already
  // makes confirmSubmit() single-shot, and this makes the download single-shot even if a
  // future caller is added. endSession() clears it for the next patient.
  if (auto && autoTranscriptDownloaded) return;
  if (auto) autoTranscriptDownloaded = true;
  const mine = sessionToken();
  const btn = document.getElementById('download-transcript-btn');
  if (btn) btn.disabled = true;
  try {
    const doc = await api('POST', `/api/visits/${state.visitUuid}/documents/transcript`);
    /* S36: if the kiosk was handed to the next patient while this was being rendered,
       DROP it. Saving one patient's transcript into the browser of the person now
       standing at the kiosk is the exact leak Finding 2 exists to prevent, and a missed
       download is the cheaper failure — the manual button and the staff portals can
       still produce it. */
    if (!mine()) return;
    const a = document.createElement('a');
    a.href = doc.download_url;
    a.download = doc.filename || '';
    document.body.appendChild(a);
    a.click();
    a.remove();
  } catch (e) {
    if (!auto && mine()) showError(e.message);
  }
  if (btn) btn.disabled = false;
}

/* S36 (ADR-0057), Finding 7: the spoken completion. Deliberately says what HAPPENED and
   what to do next — "sent to the doctor" and "please wait to be called" — because "thank
   you" alone leaves a patient standing at a kiosk wondering whether they may leave. */
const SUBMITTED_ALOUD = {
  en: 'Thank you. Your information has been sent to the doctor. Please wait to be called.',
  bn: 'ধন্যবাদ। আপনার তথ্য ডাক্তারের কাছে পাঠানো হয়েছে। আপনাকে ডাকা হবে, অনুগ্রহ করে অপেক্ষা করুন।',
};

/* S34: the re-entry guard. Two things can now ask for a submit — the patient's tap and
   the 60-second review clock — and the visit must be sent EXACTLY ONCE whichever
   arrives first (a double POST would submit the same visit twice). Never reset on the
   success path: after a submit there is nothing left to submit until resetState(). */
let submitting = false;

async function confirmSubmit() {
  if (submitting) return;
  submitting = true;
  const mine = sessionToken();   // S36
  cancelReviewTimer();        // whoever got here first, the clock's job is over
  stopReviewConfirmation();   // …and so is the question it was asking
  try {
    /* F3: require_complete=true is what makes "cannot skip required information" a
       SERVER rule rather than a hidden button. If the server refuses, re-run the
       resume loop so the outstanding question appears instead of a dead end. */
    await api('POST', `/api/visits/${state.visitUuid}/submit?require_complete=true`);
  } catch (e) {
    if (!mine()) return;   // S36: a refusal for a finished visit must not unblock this one
    showError(e.message);
    submitting = false;   // it did NOT submit — the patient must be able to try again
    if (state.lastProfile) await refreshResumeLoop(state.lastProfile);
    return;
  }
  if (!mine()) return;   // S36: the "all done" screen belongs to the visit that submitted
  setAvatarOverride('done');   // P1: the one state no live variable can express
  /* S36 (ADR-0057), Finding 7: say it out loud. Every question in this kiosk is SPOKEN
     (ADR-0028), and then the single most important moment in the whole visit — "your
     information reached the doctor" — was text on a screen and nothing else. A patient
     who cannot read that screen is exactly the patient this project is built for, and
     they were being left to guess whether it had worked.

     ⚠ Plain speak(), never askAloud(): this is an announcement, not a question, and
     askAloud() would open the microphone on a finished visit. */
  speak(t(SUBMITTED_ALOUD.en, SUBMITTED_ALOUD.bn));
  /* S36 (ADR-0057), Finding 6: the patient leaves with their own RAW record, verbatim.
     Deliberately NOT awaited — the "all done" screen and its 5-second countdown must not
     wait on a .docx render, and the download failing must not hold up a visit that has
     already been submitted. */
  downloadRawTranscript({ auto: true });
  const modal = document.getElementById('logout-modal');
  modal.style.display = 'flex';
  // S34: the same ticker the review clock uses — one countdown implementation.
  startTicker(5000, {
    onTick: (secondsLeft) => {
      document.getElementById('logout-timer').textContent =
        t(String(secondsLeft), bnDigits(secondsLeft));
    },
    onEnd: () => {
      modal.style.display = 'none';
      /* S36 (ADR-0057): ONE call replaces the hand-written teardown that used to live
         here. That list was the bug: it was assembled by remembering, session after
         session, which globals to clear — so it cancelled three timers but not the
         phone one, cleared `state` but never the recognition ENGINE or `finalBuffer`,
         and could do nothing at all about a response still in flight. endSession() is
         the single place that answers "what belongs to the finished patient?", and it
         runs BEFORE resetState() builds the new one. */
      startNewSession();
    },
  });
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
    renderRequiredNotice();   // F3: it names fields, so it must follow the toggle too
  }
  document.querySelectorAll('.bubble-speak[data-title-en]').forEach((b) => {
    b.title = t(b.dataset.titleEn, b.dataset.titleBn);
  });
  // S2: the dock hint is written by JS, so re-render it in the new language too.
  Object.values(DOCKS).forEach((dock) => setBilingualText(dock.hint, modeHint(dock).en, modeHint(dock).bn));
  // P1: the avatar's status line and aria-label are written by JS, so they must follow
  // the toggle too — an English "Listening" over a Bangla UI is the kind of half-
  // translated screen this project's bilingual rule exists to prevent.
  if (avatarState) applyAvatarState(avatarState);
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
  // F1: the phone screen had no Enter handler either — typing a number and pressing
  // Enter simply did nothing, which reads as a broken kiosk.
  wire('phone-input', sendOtp);
  /* F5b: editing the field by hand retracts a pending read-back. Leaving it up would
     let the patient change the number, tap "Yes", and send the OLD one — the read-back
     must never outlive the value it is vouching for. */
  const phoneInput = document.getElementById('phone-input');
  if (phoneInput) phoneInput.addEventListener('input', hidePhoneConfirm);
}
initTypedInputs();
setInputMode('voice', { focus: false });
loadKioskConfig();   // S1/S3: voice_loop + timings from backend/.env; defaults if it fails
