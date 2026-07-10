/* Patient kiosk (FE-1). Voice-only clinical input (ADR-0027): STT = Web Speech API
   bn-BD; every follow-up question is SHOWN and SPOKEN together (ADR-0028); the typed
   box is a mic-failure fallback only. RAW text goes to the backend verbatim (rule #1).

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
  speakBtn.onclick = () => speak(body.textContent); // replay what is displayed NOW
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
  const noVoice = !window.speechSynthesis || !banglaVoiceAvailable();
  hint.style.display = noVoice ? 'block' : 'none';
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
  speak(text);
  if (record && state.visitUuid) {
    try {
      await api('POST', `/api/visits/${state.visitUuid}/utterances`,
        { raw_text: text, role: 'system', source: 'tts', stt_provider: null });
    } catch (e) { /* recording the system turn is best-effort */ }
  }
}

function repeatQuestion() { speak(state.lastQuestionText); }

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
  return state.resumeActive
    ? { transcript: 'resume-transcript', mic: 'resume-mic-btn', hint: 'resume-hint', fallback: 'resume-fallback-row' }
    : { transcript: 'dock-transcript', mic: 'mic-btn', hint: 'listening-hint', fallback: 'fallback-row' };
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
  };
  r.onend = () => { if (listening) r.start(); }; // brief pauses keep going
  r.onerror = (e) => {
    if (e.error === 'not-allowed' || e.error === 'audio-capture') {
      showError(t('Microphone unavailable — you can type instead.', 'মাইক্রোফোন পাওয়া যায়নি — টাইপ করতে পারেন।'));
      document.getElementById(activeDock().fallback).style.display = 'flex';
      stopListening(false);
    }
  };
  return r;
}

function toggleListening() {
  if (listening) { stopListening(true); return; }
  recognition = recognition || initRecognition();
  if (!recognition) {
    showError(t('Speech recognition needs Chrome/Edge — use the typed fallback.', 'স্পিচ রিকগনিশনের জন্য Chrome/Edge দরকার — টাইপ করুন।'));
    document.getElementById(activeDock().fallback).style.display = 'flex';
    return;
  }
  finalBuffer = '';
  listening = true;
  document.getElementById(activeDock().mic).classList.add('listening');
  setBilingualText(activeDock().hint, 'Listening... tap again when done', 'শুনছি... বলা শেষে আবার চাপুন');
  window.speechSynthesis && window.speechSynthesis.cancel();
  recognition.start();
}

function stopListening(sendTurn) {
  listening = false;
  document.getElementById(activeDock().mic).classList.remove('listening');
  setBilingualText(activeDock().hint, 'Tap the mic when you are ready to speak', 'বলতে প্রস্তুত হলে মাইকে চাপ দিন');
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
    const cell = document.createElement('div');
    cell.className = 'summary-item' + (HIGHLIGHT_FIELDS.includes(key) ? ' highlight' : '');
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
    speak(question.question_text);   // ADR-0028: shown as text AND spoken together
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
}
