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

async function loadQueue() {
  const params = new URLSearchParams({ role: PORTAL.role });
  if (PORTAL.role === 'doctor' && PORTAL.userId) params.set('doctor_id', PORTAL.userId);
  const items = await api('GET', `/api/dashboard?${params}`);
  renderQueue(items);
}

async function searchPhone() {
  const phone = document.getElementById('phone-search').value.trim();
  if (!phone) return loadQueue();
  try {
    renderQueue(await api('GET', `/api/dashboard?phone=${encodeURIComponent(phone)}`));
  } catch (e) { showError(e.message); }
}

function renderQueue(items) {
  lastQueueItems = items;
  const box = document.getElementById('queue-list');
  box.innerHTML = '';
  document.getElementById('queue-count').textContent = items.length;
  if (!items.length) {
    box.innerHTML = `<div style="padding:20px; color:var(--text-muted); font-size:.85rem;">${t('No cases in the queue.', 'তালিকায় কোনো কেস নেই।')}</div>`;
    return;
  }
  items.forEach((item) => {
    const div = document.createElement('div');
    div.className = 'queue-item' + (currentCase && currentCase.uuid === item.visit_uuid ? ' active' : '');
    const when = new Date(item.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    div.innerHTML =
      `<div class="queue-item-meta"><span>${when}</span>${tierBadge(item.tier)}</div>` +
      `<div class="queue-item-name"></div><div class="queue-item-problem"></div>`;
    div.querySelector('.queue-item-name').textContent =
      item.patient_name || item.patient_phone
      || `${t('Visit', 'ভিজিট')} ${item.visit_uuid.slice(0, 8)}`;
    div.querySelector('.queue-item-problem').textContent = item.main_problem || item.summary || '—';
    div.onclick = () => openCase(item.visit_uuid);
    box.appendChild(div);
  });
}

async function openCase(uuid) {
  try {
    const detail = await api('GET', `/api/visits/${uuid}`);
    let profile = null;
    try { profile = await api('GET', `/api/visits/${uuid}/profile`); } catch (_) {}
    currentCase = { uuid, detail, profile };
    document.getElementById('no-case').style.display = 'none';
    document.getElementById('case-detail').style.display = 'flex';
    renderVerbatim(detail);
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
    renderFields(currentCase.profile);
  }
}
