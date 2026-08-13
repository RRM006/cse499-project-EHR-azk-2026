/* Shared staff-portal logic (FE-2/FE-3): queue rendering, phone lookup, the
   immutable verbatim panel, and the 10 collapsible field cards with edit support.
   Each portal supplies PORTAL = { role, userId, canEdit, onCaseLoaded }.
   MEDIC-1/DOCTOR-2: everything rendered here is bilingual — static text via t(),
   extracted values via fieldValue(); the raw verbatim panel is NEVER translated
   or altered (rule #1). Portals call staffLanguageRefresh() on toggle. */

const STAFF_FIELD_LABELS = {
  main_problem:             { icon: '🩺', en: '1. Main Problem / Chief Complaint', bn: '১. প্রধান সমস্যা' },
  onset_duration:           { icon: '⏱️', en: '2. When Started & Duration', bn: '২. শুরুর সময় ও স্থায়িত্ব' },
  symptom_details:          { icon: '📋', en: '3. Symptom Details (Location, Character, Worse, Better)', bn: '৩. উপসর্গের বিস্তারিত (স্থান, ধরন, কীসে বাড়ে/কমে)' },
  associated_symptoms:      { icon: '🤒', en: '4. Associated Symptoms', bn: '৪. আনুষঙ্গিক উপসর্গ' },
  medical_history:          { icon: '📖', en: '5. Relevant Medical History', bn: '৫. প্রাসঙ্গিক চিকিৎসা ইতিহাস' },
  current_medicines:        { icon: '💊', en: '6. Medicines Currently Taking', bn: '৬. চলমান ওষুধসমূহ' },
  allergies:                { icon: '⚠️', en: '7. Allergies', bn: '৭. অ্যালার্জি' },
  recent_changes_exposures: { icon: '🔄', en: '8. Recent Changes / Exposures', bn: '৮. সাম্প্রতিক পরিবর্তন' },
  treatments_tried:         { icon: '🩹', en: '9. Treatments Tried', bn: '৯. গৃহীত ব্যবস্থা' },
  current_concern:          { icon: '💬', en: '10. Current Concern / Question', bn: '১০. মূল উদ্বেগ / প্রশ্ন' },
};

let currentCase = null;   // { uuid, detail, profile }
let lastQueueItems = [];  // kept so the queue re-renders on language toggle
let queueLoadedOnce = false;  // S37: skeletons only before the FIRST paint

/* S37 — which list the sidebar is showing. 'queue' is the working list; 'recent' is
   the doctor's own completed consultations (ADR-0058). The medic has no 'recent'
   (nothing attributes a referral to an individual medic) and the server refuses it,
   so this only ever leaves 'queue' in the doctor portal. */
let queueScope = 'queue';

function setQueueScope(scope) {
  queueScope = scope;
  queueLoadedOnce = false;   // a scope change is a new list, so show its skeleton
  loadQueue();
}

async function loadQueue() {
  const params = new URLSearchParams({ role: PORTAL.role, scope: queueScope });
  if (PORTAL.role === 'doctor' && PORTAL.userId) params.set('doctor_id', PORTAL.userId);
  if (!queueLoadedOnce) renderQueueSkeleton();
  try {
    const items = await api('GET', `/api/dashboard?${params}`);
    queueIsSearchResult = false;
    renderQueue(items);
  } catch (e) {
    // Handled here rather than re-thrown: loadQueue runs on a 15s timer and from
    // several callers, and an unhandled rejection in a timer is invisible to staff.
    // The failure is shown IN the sidebar, where the missing list actually is.
    queueLoadedOnce = true;
    renderQueueMessage(t('Could not load the queue.', 'তালিকা লোড করা যায়নি।'), e.message);
    return;
  }
  if (typeof onQueueLoaded === 'function') onQueueLoaded(lastQueueItems);
}

/* S37 — a processing state that says "fetching", not "empty". Without it the first
   paint of a slow queue is indistinguishable from a clinic with no patients. */
function renderQueueSkeleton() {
  const box = document.getElementById('queue-list');
  if (!box) return;
  box.innerHTML = Array.from({ length: 4 }, () =>
    `<div class="skeleton-row">
       <div class="skeleton skeleton-line" style="width:42%;"></div>
       <div class="skeleton skeleton-line" style="width:70%;"></div>
       <div class="skeleton skeleton-line" style="width:55%; margin-bottom:0;"></div>
     </div>`).join('');
}

function renderQueueMessage(title, detail, glyphChar) {
  const box = document.getElementById('queue-list');
  if (!box) return;
  box.innerHTML = '';
  const wrap = document.createElement('div');
  wrap.className = 'empty-state';
  const glyph = document.createElement('div');
  glyph.className = 'glyph';
  glyph.textContent = glyphChar || (detail ? '⚠️' : '✅');
  const head = document.createElement('div');
  head.style.cssText = 'font-weight:600; font-size:.86rem;';
  head.textContent = title;
  wrap.appendChild(glyph);
  wrap.appendChild(head);
  if (detail) {
    const sub = document.createElement('div');
    sub.style.cssText = 'font-size:.78rem;';
    sub.textContent = detail;      // server text — textContent only
    wrap.appendChild(sub);
  }
  box.appendChild(wrap);
}

/* S37 — minutes -> a short, tabular label. Bands are clinical judgement, not
   animation: >=15 min amber, >=30 min red (the tier still outranks both). */
function waitLabel(minutes) {
  if (minutes === null || minutes === undefined) return null;
  const band = minutes >= 30 ? 'late' : (minutes >= 15 ? 'warn' : '');
  if (minutes < 60) return { text: `${minutes}${t('m', 'মি')}`, band };
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h < 48) {
    return { text: m ? `${h}${t('h', 'ঘ')} ${m}${t('m', 'মি')}` : `${h}${t('h', 'ঘ')}`, band };
  }
  // Beyond two days, hours stop being readable: a demo/dev row can legitimately
  // show "536h 50m", which no one parses. Days + hours is the same fact, legibly.
  const d = Math.floor(h / 24);
  const rh = h % 24;
  return { text: rh ? `${d}${t('d', 'দি')} ${rh}${t('h', 'ঘ')}` : `${d}${t('d', 'দি')}`, band };
}

/* S37: which question the current list answers. A phone search that finds nothing
   is a search miss, not an empty clinic — saying "no cases in the queue" there told
   staff the wrong thing about their own workload. */
let queueIsSearchResult = false;

async function searchPhone() {
  const phone = document.getElementById('phone-search').value.trim();
  if (!phone) return loadQueue();
  try {
    const items = await api('GET', `/api/dashboard?phone=${encodeURIComponent(phone)}`);
    queueIsSearchResult = true;
    renderQueue(items);
  } catch (e) { showError(e.message); }
}

function renderQueue(items) {
  lastQueueItems = items;
  queueLoadedOnce = true;
  const box = document.getElementById('queue-list');
  box.innerHTML = '';
  document.getElementById('queue-count').textContent = items.length;
  if (!items.length) {
    renderQueueMessage(
      queueIsSearchResult
        ? t('No patient found for that number.', 'ঐ নম্বরে কোনো রোগী পাওয়া যায়নি।')
        : (queueScope === 'recent'
            ? t('No completed consultations yet.', 'এখনো কোনো সম্পন্ন পরামর্শ নেই।')
            : t('No cases in the queue.', 'তালিকায় কোনো কেস নেই।')),
      null,
      queueIsSearchResult ? '🔍' : '✅');
    return;
  }
  items.forEach((item, idx) => {
    const div = document.createElement('div');
    // S37: the tier is on the row itself (a colour rail) as well as in the badge,
    // so the ranking is legible while scrolling, not only when reading each row.
    div.className = 'queue-item fx-queue tier-' + (item.tier || 'none')
      + (currentCase && currentCase.uuid === item.visit_uuid ? ' active' : '');
    div.style.setProperty('--i', idx);
    div.tabIndex = 0;   // the queue is keyboard-reachable, like every other control
    // P2-1: always Bangladesh time (shared.js dhakaTime pins offset-less UTC
    // strings to UTC first — the old bare new Date() read them as local time).
    // P3-1: a queue row's time is the patient's SUBMISSION moment; started_at
    // only remains as the fallback for pre-0011 rows that carry no submitted_at.
    const when = dhakaTime(item.submitted_at || item.started_at);
    div.innerHTML =
      `<div class="queue-item-meta"><span>${when}</span>${tierBadge(item.tier)}</div>` +
      `<div class="queue-item-name"></div><div class="queue-item-problem"></div>` +
      `<div class="queue-chips"></div>`;
    div.querySelector('.queue-item-name').textContent =
      item.patient_name || item.patient_phone
      || `${t('Visit', 'ভিজিট')} ${item.visit_uuid.slice(0, 8)}`;
    div.querySelector('.queue-item-problem').textContent = item.main_problem || item.summary || '—';
    renderQueueChips(div.querySelector('.queue-chips'), item);
    div.onclick = () => openCase(item.visit_uuid);
    div.onkeydown = (e) => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openCase(item.visit_uuid); }
    };
    box.appendChild(div);
  });
}

/* S37 — the three operational facts a staff member needs BEFORE opening a case:
   how long this patient has waited, whether a red flag fired, and how much of the
   intake is actually filled in. All three are server-derived (ADR-0058); nothing
   here recomputes them, so a row can never disagree with the case it opens. */
function renderQueueChips(box, item) {
  if (!box) return;
  box.innerHTML = '';

  const wait = waitLabel(item.waiting_minutes);
  if (wait) {
    const chip = document.createElement('span');
    chip.className = 'wait-chip' + (wait.band ? ' ' + wait.band : '');
    chip.textContent = `⏱ ${wait.text}`;
    chip.title = t('Waiting since the patient submitted', 'রোগী জমা দেওয়ার পর থেকে অপেক্ষা');
    box.appendChild(chip);
  }

  if (item.red_flags && item.red_flags.length) {
    const flag = document.createElement('span');
    // Pulses ONLY here: urgency is the one thing worth repeating motion for.
    flag.className = 'flag-chip pulse';
    flag.textContent = `▲ ${t('Red flag', 'বিপদ সংকেত')}`;
    flag.title = item.red_flags.join(', ');   // attribute, never innerHTML
    box.appendChild(flag);
  }

  const total = item.fields_total || 10;
  const filled = item.fields_filled || 0;
  const meter = document.createElement('span');
  meter.className = 'meter';
  meter.title = t('Pre-screening fields with an answer', 'উত্তরসহ প্রাক-পরীক্ষার ঘর');
  const track = document.createElement('span');
  track.className = 'meter-track';
  const fill = document.createElement('span');
  fill.className = 'meter-fill' + (filled >= total ? ' full' : (filled <= total / 2 ? ' low' : ''));
  fill.style.width = `${Math.round((filled / total) * 100)}%`;
  track.appendChild(fill);
  const num = document.createElement('span');
  num.className = 'meter-num';
  num.textContent = `${filled}/${total}`;
  meter.appendChild(track);
  meter.appendChild(num);
  box.appendChild(meter);
}

async function openCase(uuid) {
  try {
    const detail = await api('GET', `/api/visits/${uuid}`);
    let profile = null;
    try { profile = await api('GET', `/api/visits/${uuid}/profile`); } catch (_) {}
    currentCase = { uuid, detail, profile };
    document.getElementById('no-case').style.display = 'none';
    const panel = document.getElementById('case-detail');
    panel.style.display = 'flex';
    // S37: re-trigger the entrance so switching cases reads as a NEW case arriving
    // rather than the same panel silently swapping its text.
    panel.classList.remove('fx-in');
    void panel.offsetWidth;   // force reflow so the animation restarts
    panel.classList.add('fx-in');
    renderVerbatim(detail);
    renderConditionCard(profile);
    renderFields(profile);
    if (PORTAL.onCaseLoaded) await PORTAL.onCaseLoaded(currentCase);
    loadQueue(); // refresh active highlight
  } catch (e) { showError(e.message); }
}

/* Raw verbatim panel — read-only, immutable (rule #1). */
function renderVerbatim(detail) {
  const body = document.getElementById('verbatim-body');
  body.innerHTML = '';
  detail.utterances.forEach((u) => {
    const turn = document.createElement('div');
    turn.className = 'verbatim-turn ' + (u.role === 'system' ? 'ask' : 'said');
    const speaker = document.createElement('span');
    speaker.className = 'verbatim-speaker';
    speaker.textContent = u.role === 'system'
      ? t('Assistant asked', 'সহকারী জিজ্ঞেস করেছেন')
      : t('Patient said', 'রোগী বলেছেন');
    const text = document.createElement('span');
    text.className = 'verbatim-text';
    text.textContent = u.raw_text; // exact words, never edited
    turn.appendChild(speaker);
    turn.appendChild(text);
    body.appendChild(turn);
  });
  const note = document.createElement('div');
  note.style.cssText = 'font-size:.78rem;color:var(--text-muted);border-top:1px dashed var(--border-color);padding-top:10px;';
  note.textContent = t(
    'This is the exact speech captured, stored unchanged. The structured fields below are the AI’s interpretation — always verify against what the patient actually said.',
    'এটি রোগীর হুবহু কথা, অপরিবর্তিত অবস্থায় সংরক্ষিত। নিচের কাঠামোবদ্ধ তথ্য এআই-এর ব্যাখ্যা — রোগী আসলে কী বলেছেন তার সাথে সবসময় মিলিয়ে নিন।'
  );
  body.appendChild(note);
}

function renderFields(profile) {
  const box = document.getElementById('field-cards');
  box.innerHTML = '';
  const fields = ((profile && profile.entities) || {}).summary_fields || {};
  Object.keys(STAFF_FIELD_LABELS).forEach((key, idx) => {
    const f = fields[key] || { value: '', source: 'ai' };
    const label = STAFF_FIELD_LABELS[key];
    const card = document.createElement('div');
    card.className = 'field-card' + (idx === 0 ? ' open' : '');
    const badge = f.source === 'human'
      ? `<span class="source-badge source-human">${t('Human Edited', 'মানব-সম্পাদিত')}</span>`
      : `<span class="source-badge source-ai">${t('AI-Extracted', 'এআই-নির্ণীত')}</span>`;
    card.innerHTML =
      `<div class="field-card-header"><span><span class="field-card-icon">${label.icon}</span>${t(label.en, label.bn)}</span><span>▾</span></div>` +
      `<div class="field-card-content">${badge}
         <div style="flex:1;">
           <div class="field-value" style="font-size:.95rem;line-height:1.5;"></div>
           <div class="field-editor" style="display:none;gap:8px;margin-top:8px;">
             <input class="input-field field-input" type="text">
             <button class="btn btn-primary" style="padding:6px 14px;font-size:.8rem;">${t('Save', 'সংরক্ষণ')}</button>
             <button class="btn btn-secondary" style="padding:6px 14px;font-size:.8rem;">${t('Cancel', 'বাতিল')}</button>
           </div>
         </div>` +
      (PORTAL.canEdit ? `<button class="btn btn-secondary edit-btn" style="padding:6px 12px;font-size:.8rem;">✏️ ${t('Edit', 'সম্পাদনা')}</button>` : '') +
      `</div>`;
    card.querySelector('.field-card-header').onclick = () => card.classList.toggle('open');
    // Bilingual DERIVED value (display-only; the medic edits write ALL slots).
    card.querySelector('.field-value').textContent = fieldValue(f) || '—';
    if (PORTAL.canEdit) {
      const editor = card.querySelector('.field-editor');
      const input = card.querySelector('.field-input');
      card.querySelector('.edit-btn').onclick = () => {
        input.value = fieldValue(f) || '';
        editor.style.display = 'flex';
      };
      const [saveBtn, cancelBtn] = editor.querySelectorAll('button');
      cancelBtn.onclick = () => { editor.style.display = 'none'; };
      saveBtn.onclick = async () => {
        try {
          const profile = await api('PATCH',
            `/api/visits/${currentCase.uuid}/profile/fields/${key}`,
            { value: input.value, editor_id: PORTAL.userId });
          currentCase.profile = profile;
          renderFields(profile);
        } catch (e) { showError(e.message); }
      };
    }
    box.appendChild(card);
  });
}

/* C1 (MEDIC-4, ADR-0036): the AI suggested condition — a clearly labeled,
   disclaimered SUGGESTION, never a diagnosis (rule #2). Staff portals opt in by
   having a #condition-card mount in their page; the kiosk never has one. */
function suggestionText(s, enKey, bnKey) {
  const byLang = currentLanguage === 'bn' ? [s[bnKey], s[enKey]] : [s[enKey], s[bnKey]];
  for (const v of byLang) {
    const text = (v === undefined || v === null) ? '' : String(v).trim();
    if (text) return text;
  }
  return '';
}

function renderConditionCard(profile) {
  const card = document.getElementById('condition-card');
  if (!card) return;
  card.style.display = 'flex';
  const s = ((profile && profile.entities) || {}).suggested_condition || null;
  const badge = !s ? '' : (s.source === 'human'
    ? `<span class="source-badge source-human">${t('Human Edited', 'মানব-সম্পাদিত')}</span>`
    : `<span class="source-badge source-ai">${t('AI Suggested', 'এআই-পরামর্শকৃত')}</span>`);
  card.innerHTML =
    `<div style="display:flex; justify-content:space-between; align-items:flex-start; gap:14px; flex-wrap:wrap;">
       <h3 style="font-size:1.05rem; color:var(--primary-color);">🔎 ${t('Possible Condition', 'সম্ভাব্য অবস্থা')}
         <span style="font-weight:600; font-size:.78rem; color:var(--text-muted);">(${t('AI Suggestion – Not a Diagnosis', 'এআই পরামর্শ – রোগনির্ণয় নয়')})</span></h3>
       <div style="display:flex; gap:8px; align-items:center;">${badge}` +
       (PORTAL.canEdit ? `<button class="btn btn-secondary condition-edit-btn" style="padding:6px 12px;font-size:.8rem;">✏️ ${t('Edit', 'সম্পাদনা')}</button>` : '') +
    `  </div>
     </div>
     <div class="condition-value" style="font-size:1rem; font-weight:700; color:var(--primary-color);"></div>
     <div class="condition-reasoning" style="display:none; font-size:.85rem; color:var(--text-main); background:var(--bg-main); padding:10px 14px; border-radius:6px; border-left:3px solid var(--secondary-color);"></div>
     <div class="condition-disclaimer" style="font-size:.78rem; font-weight:600; color:var(--warning-color);"></div>
     <div class="condition-editor" style="display:none; flex-direction:column; gap:8px;">
       <input class="input-field condition-input" type="text" placeholder="${t('Condition', 'অবস্থা')}">
       <textarea class="input-field condition-reasoning-input" rows="2" placeholder="${t('Reasoning (why)', 'যুক্তি (কেন)')}"></textarea>
       <div style="display:flex; gap:8px;">
         <button class="btn btn-primary condition-save" style="padding:6px 14px;font-size:.8rem;">${t('Save', 'সংরক্ষণ')}</button>
         <button class="btn btn-secondary condition-cancel" style="padding:6px 14px;font-size:.8rem;">${t('Cancel', 'বাতিল')}</button>
       </div>
     </div>`;
  const condition = s ? (suggestionText(s, 'condition_en', 'condition_bn') || s.condition || '') : '';
  const reasoning = s ? suggestionText(s, 'reasoning_en', 'reasoning_bn') : '';
  const valueBox = card.querySelector('.condition-value');
  if (s) {
    valueBox.textContent = condition || '—';
  } else {
    valueBox.style.cssText = 'font-size:.9rem; color:var(--text-muted); font-style:italic;';
    valueBox.textContent = t('No AI suggestion is available for this case.',
                             'এই কেসের জন্য কোনো এআই পরামর্শ পাওয়া যায়নি।');
  }
  if (reasoning) {
    const box = card.querySelector('.condition-reasoning');
    box.style.display = 'block';
    box.textContent = `🧠 ${t('Reasoning', 'যুক্তি')}: ${reasoning}`;
  }
  // The disclaimer is always visible with a suggestion — stored text preferred (rule #2).
  if (s) {
    card.querySelector('.condition-disclaimer').textContent = '⚠️ ' + (currentLanguage === 'bn'
      ? (s.disclaimer_bn || s.disclaimer || 'এটি শুধুমাত্র এআই পরামর্শ — রোগনির্ণয় নয়। সকল চিকিৎসা সিদ্ধান্ত ডাক্তার নেবেন।')
      : (s.disclaimer || 'AI suggestion only — NOT a diagnosis. The doctor makes all clinical decisions.'));
  }
  if (PORTAL.canEdit) {
    const editor = card.querySelector('.condition-editor');
    card.querySelector('.condition-edit-btn').onclick = () => {
      card.querySelector('.condition-input').value = condition;
      card.querySelector('.condition-reasoning-input').value = reasoning;
      editor.style.display = 'flex';
    };
    card.querySelector('.condition-cancel').onclick = () => { editor.style.display = 'none'; };
    card.querySelector('.condition-save').onclick = async () => {
      const value = card.querySelector('.condition-input').value.trim();
      if (!value) return showError(t('Condition cannot be empty.', 'অবস্থা খালি রাখা যাবে না।'));
      try {
        const updated = await api('PATCH', `/api/visits/${currentCase.uuid}/profile/condition`, {
          condition: value,
          reasoning: card.querySelector('.condition-reasoning-input').value.trim(),
          editor_id: PORTAL.userId,
        });
        currentCase.profile = updated;
        renderConditionCard(updated);
      } catch (e) { showError(e.message); }
    };
  }
}

function toggleVerbatim() {
  document.getElementById('verbatim-panel').classList.toggle('collapsed');
}

/* MEDIC-1/DOCTOR-2: rebuild everything staff.js rendered in the new language.
   Portals call this from their onLanguageChange(). Raw text is re-rendered but
   never translated (rule #1 — only the chrome around it switches). */
function staffLanguageRefresh() {
  renderQueue(lastQueueItems);
  if (currentCase) {
    renderVerbatim(currentCase.detail);
    renderConditionCard(currentCase.profile);
    renderFields(currentCase.profile);
  }
}
