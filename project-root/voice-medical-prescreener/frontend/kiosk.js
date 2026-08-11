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
    readiness: null,        // F3: the SERVER's verdict on "may this patient submit yet?"
    scriptIndex: -1,        // F4: position in INTAKE_SCRIPT; -1 = the script is done
    resumeScripted: null,   // F4: a scripted question re-asked on the summary screen
    inputMode: 'voice',     // S2 (ADR-0048): 'voice' (primary/default) | 'type' (always available)
    identifyStep: 'phone',  // F5b: 'phone' | 'otp' | null — which identification dock owns the mic
    pendingPhone: null,     // F5b: a spoken number awaiting the patient's confirmation
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
};

/** Pull the digit sequence out of one spoken (or typed) utterance.
 *
 *  Words are matched WHOLE, never as substrings — `তিনি` ("he/she") contains `তিন`
 *  ("three"), and substring matching would read a three out of a pronoun. Anything
 *  unrecognised contributes nothing, so filler ("আমার নম্বর হলো…") is ignored rather
 *  than being an error, and a token that is itself digits contributes those digits —
 *  which is what makes a mixed "শূন্য এক ৭১৫" work.
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
function digitsFromSpeech(text) {
  let out = '';
  const cleaned = String(text || '').normalize('NFC').replace(/[\u200C\u200D]/g, '');
  for (const token of cleaned.toLowerCase().split(/[^\p{L}\p{N}\p{M}]+/u)) {
    if (!token) continue;
    const word = SPOKEN_DIGITS[token];
    if (word !== undefined) { out += word; continue; }
    out += asciiDigits(token);
  }
  return out;
}

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

async function sendOtp() {
  const phone = document.getElementById('phone-input').value.trim();
  if (!phone) return showError(t('Enter your mobile number.', 'মোবাইল নম্বর লিখুন।'));
  try {
    await api('POST', '/api/patients/lookup', { phone });
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
  } catch (e) { showError(e.message); }
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
}

function hidePhoneConfirm() {
  if (state) state.pendingPhone = null;
  const el = document.getElementById('phone-confirm');
  if (el) el.style.display = 'none';
}

/** The patient agreed with what we heard — only now does the number leave the device. */
function confirmPhone() {
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

/* F4: ask INTAKE_SCRIPT[index]. Goes through assistantSays(), so the question is
   shown, spoken, recorded as a system utterance, and (in auto mode) opens the mic —
   identical handling to an M7 question. */
async function askScriptedQuestion(index) {
  state.scriptIndex = index;
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
  },
  resume: {
    transcript: 'resume-transcript', mic: 'resume-mic-btn', hint: 'resume-hint',
    fallback: 'resume-fallback-row', input: 'resume-fallback-input',
    voiceBtn: 'resume-mode-voice-btn', typeBtn: 'resume-mode-type-btn',
    countdown: 'resume-countdown', countdownDigit: 'resume-countdown-digit',
  },
  phone: {
    transcript: 'phone-transcript', mic: 'phone-mic-btn', hint: 'phone-hint',
    input: 'phone-input', hints: IDENTIFY_HINTS,
    voiceBtn: 'phone-mode-voice-btn', typeBtn: 'phone-mode-type-btn',
    countdown: 'phone-countdown', countdownDigit: 'phone-countdown-digit',
  },
  otp: {
    transcript: 'otp-transcript', mic: 'otp-mic-btn', hint: 'otp-hint',
    input: 'otp-input-1', hints: IDENTIFY_HINTS,
    voiceBtn: 'otp-mode-voice-btn', typeBtn: 'otp-mode-type-btn',
    countdown: 'otp-countdown', countdownDigit: 'otp-countdown-digit',
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
  setBilingualText(activeDock().hint, modeHint(activeDock()).en, modeHint(activeDock()).bn);   // S2: mode-aware
  if (recognition) try { recognition.stop(); } catch (_) {}
  const text = finalBuffer.trim();
  setBilingualText(activeDock().transcript, '', '');   // P1-2: clear dataset too
  if (sendTurn && text) {
    /* F5b: identification first — see activeDock(). These two branches never touch a
       visit; they read digits out of the utterance and drive the screen the patient is
       actually on. Everything below them is the clinical path, unchanged. */
    if (state.identifyStep === 'phone') applySpokenPhone(text);
    else if (state.identifyStep === 'otp') applySpokenOtp(text);
    else if (state.resumeActive) submitResumeAnswer(text, 'mic');
    else submitPatientTurn(text, 'mic');
  }
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
const AVATAR_IDS = ['doctor-avatar', 'resume-avatar'];
const AVATAR_STATUS_IDS = ['doctor-status'];

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
  setBilingualText('doctor-substatus', entry.sub.en, entry.sub.bn);
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
    } else if (inScriptedOpening()) {
      /* F4: a scripted answer that is NOT the last one. Store it verbatim and move to
         the next scripted question — intake deliberately waits until the whole
         opening is in, so M3 extracts area, name, age and the complaint from one
         complete conversation instead of re-running per turn. */
      await api('POST', `/api/visits/${state.visitUuid}/utterances`, {
        raw_text: rawText, role: 'patient', source,
        stt_provider: source === 'mic' ? 'browser_webspeech' : 'manual',
      });
      await askScriptedQuestion(state.scriptIndex + 1);
    } else {
      // Free opening turn(s): store, then run intake and start the loop.
      state.scriptIndex = -1;   // F4: the scripted opening is finished
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
  try {
    state.readiness = await api('GET', `/api/visits/${state.visitUuid}/readiness`);
  } catch (e) {
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
  updateSubmitVisibility();   // F3: readiness decides, not just "is a question open"
  if (state.resumeActive) {
    document.getElementById('resume-question').textContent = text;
    askAloud(text);   // ADR-0028 + S3: spoken, then the mic arms itself
  } else {
    cancelPendingMic();   // loop finished — nothing should open the mic behind the summary
  }
}

async function refreshResumeLoop(profile) {
  const filled = renderProgress(profile);
  // F3: readiness is checked FIRST and always — a 10/10 grid is no longer proof that
  // the required items were covered, and an incomplete one is no longer a reason to
  // keep asking once the server is satisfied.
  const readiness = await loadReadiness();
  if (filled >= 10 && (!readiness || readiness.complete)) { setResumeMode(null); return; }
  // F4: identity first — a missing name/age/area is re-asked with its own scripted
  // question, because no M7 question can cover it.
  const scripted = pendingScriptedRequirement();
  if (scripted) { setResumeMode(null, scripted); return; }
  try {
    const res = await api('POST', `/api/visits/${state.visitUuid}/followup/next?scope=fields`);
    setResumeMode(res.complete ? null : res.question);
  } catch (e) {
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
    const profile = await api('GET', `/api/visits/${state.visitUuid}/profile`);
    renderSummary(profile);          // spec: the summary regenerates automatically
    /* Re-evaluate from scratch: refreshResumeLoop re-reads readiness and picks the
       next thing to ask, so both branches converge on ONE decision point instead of
       each guessing what should come next. */
    await refreshResumeLoop(profile);
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
    /* F3: require_complete=true is what makes "cannot skip required information" a
       SERVER rule rather than a hidden button. If the server refuses, re-run the
       resume loop so the outstanding question appears instead of a dead end. */
    await api('POST', `/api/visits/${state.visitUuid}/submit?require_complete=true`);
  } catch (e) {
    showError(e.message);
    if (state.lastProfile) await refreshResumeLoop(state.lastProfile);
    return;
  }
  setAvatarOverride('done');   // P1: the one state no live variable can express
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
      setAvatarOverride(null);    // P1: the next patient must not inherit "All done"
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
