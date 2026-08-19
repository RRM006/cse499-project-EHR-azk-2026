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

/* S38 (A2) — the auto-refresh, made VISIBLE and made SAFE.

   It already existed as a bare `setInterval(loadQueue, 15000)` in each portal, with
   two problems that only show up in use:

   1. **It destroyed the medic's own work.** `searchPhone()` renders a patient's
      history into the same list; fifteen seconds later the timer fired `loadQueue()`
      and silently replaced it with the full queue. A medic looking up a returning
      patient watched their result vanish for no visible reason. The brief is explicit:
      *"Do NOT refresh in a way that destroys the user's current interaction/input."*
   2. **It was invisible and unconditional.** Nothing on screen said the list was live,
      so a stale-looking queue was indistinguishable from a broken one — and it kept
      polling at full rate against a backgrounded tab all night.

   The fix keeps ONE timer, owned here rather than duplicated per portal:
     * it holds while a phone search is on screen, and resumes when the search clears;
     * it holds while the tab is hidden, and refreshes ONCE immediately on return, so
       a medic coming back to the tab sees current data without waiting out the period;
     * it publishes `lastQueueRefreshAt` and calls `onQueueRefreshState()`, which is
       what lets the portals draw a live "updated 3:42:07 PM" line instead of nothing;
     * a refresh never re-runs the entrance animation (see `queueAnimateNext`), because
       a queue that re-flashes every 15 seconds reads as an error, not as freshness. */
const QUEUE_REFRESH_MS = 15000;
let queueTimer = null;
let lastQueueRefreshAt = null;   // Date of the last SUCCESSFUL queue render
let queueRefreshPaused = false;  // why the timer is holding, for the status line
let queueAnimateNext = true;     // stagger the rows on this render only

function startQueueAutoRefresh() {
  if (queueTimer !== null) return;      // idempotent: re-login must not stack timers
  queueTimer = setInterval(autoRefreshQueue, QUEUE_REFRESH_MS);
  document.addEventListener('visibilitychange', () => {
    // Coming back to the tab is the one moment a medic MOST needs current data, and
    // the one moment the timer is most likely to have just fired into a hidden tab.
    if (!document.hidden) autoRefreshQueue();
    renderQueueRefreshState();
  });
}

function autoRefreshQueue() {
  // A search result is the medic's own question; the timer does not get to answer a
  // different one. Cleared the moment they clear the box (refreshQueue / loadQueue).
  // `PORTAL.autoRefreshPaused` extends the same rule to any other list a portal has
  // put in the sidebar (S38: the medic's referral history and inbox) — those are
  // things a person went looking for, and overwriting them would be exactly the
  // defect A2 exists to fix.
  if (typeof PORTAL === 'object' && PORTAL.autoRefreshPaused && PORTAL.autoRefreshPaused()) {
    queueRefreshPaused = true;
    renderQueueRefreshState();
    return;
  }
  if (queueIsSearchResult || document.hidden) {
    queueRefreshPaused = true;
    renderQueueRefreshState();
    return;
  }
  queueRefreshPaused = false;
  queueAnimateNext = false;   // a background refresh must not re-animate the list
  loadQueue();
}

/* Portals opt in by defining onQueueRefreshState(); the shared code never assumes
   a particular element exists. */
function renderQueueRefreshState() {
  if (typeof onQueueRefreshState === 'function') {
    onQueueRefreshState({
      lastRefreshAt: lastQueueRefreshAt,
      paused: queueRefreshPaused || document.hidden,
      intervalMs: QUEUE_REFRESH_MS,
      searching: queueIsSearchResult,
    });
  }
}

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
    lastQueueRefreshAt = new Date();
    queueRefreshPaused = false;
  } catch (e) {
    // Handled here rather than re-thrown: loadQueue runs on a 15s timer and from
    // several callers, and an unhandled rejection in a timer is invisible to staff.
    // The failure is shown IN the sidebar, where the missing list actually is.
    queueLoadedOnce = true;
    renderQueueMessage(t('Could not load the queue.', 'তালিকা লোড করা যায়নি।'), e.message);
    renderQueueRefreshState();
    return;
  }
  renderQueueRefreshState();
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
    queueAnimateNext = true;   // a search result IS a new list; it may animate in
    renderQueue(items);
    // S38: the auto-refresh holds from here until the search is cleared, so the timer
    // can never overwrite the answer the medic just asked for.
    renderQueueRefreshState();
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
    // ⚠ The empty branch is EXACTLY the case B7 reports, so the workspace has to be
    // told here too. Returning before this is how the right-hand panel kept saying
    // "Select a patient from the queue" while the queue beside it said there was none.
    queueAnimateNext = false;
    renderWorkspaceState();
    return;
  }
  items.forEach((item, idx) => {
    const div = document.createElement('div');
    // S37: the tier is on the row itself (a colour rail) as well as in the badge,
    // so the ranking is legible while scrolling, not only when reading each row.
    // S38: `fx-queue` is applied only when this render is a NEW list (first paint,
    // scope change, search, explicit refresh). A 15-second background refresh
    // rebuilds the same rows, and re-running the stagger every 15 seconds made a
    // healthy queue look like it was constantly reloading.
    div.className = 'queue-item tier-' + (item.tier || 'none')
      + (queueAnimateNext ? ' fx-queue' : '')
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
  // One render = one entrance. The next render re-earns it (search / scope / refresh).
  queueAnimateNext = false;
  renderWorkspaceState();
}

/* S38 (B7) — the RIGHT-hand panel must also answer "why is there nothing here?".

   The sidebar has had an empty state since S37; the workspace never did. So selecting
   "Assigned (0)" left the medic or doctor looking at a panel that said "Select Patient
   — click a patient to scan risk alerts", pointing at a list with no patients in it.
   Worse, once a case had been opened `#no-case` was hidden and nothing ever restored
   it, so switching to an empty scope left the PREVIOUS patient's case on screen as if
   it were still in the queue.

   This is deliberately shared rather than per-portal: the failure was identical in
   both, and a second copy would fix it in one and not the other. Portals customise the
   wording through `PORTAL.emptyWorkspace`. */
let placeholderDefaults = null;   // the markup's own "select a patient" copy

function renderWorkspaceState() {
  const placeholder = document.getElementById('no-case');
  const detail = document.getElementById('case-detail');
  if (!placeholder || !detail) return;
  const glyph = placeholder.querySelector('div');
  const heading = placeholder.querySelector('h3');
  const body = placeholder.querySelector('p');
  if (!glyph || !heading || !body) return;

  // Captured once, before anything overwrites it, so the default copy can be put back
  // when the queue refills. The bilingual pairs are taken from the markup's own
  // data-en/data-bn rather than re-typed here — one source for that text.
  if (placeholderDefaults === null) {
    placeholderDefaults = {
      glyph: glyph.textContent,
      title: { en: heading.dataset.en, bn: heading.dataset.bn },
      detail: { en: body.dataset.en, bn: body.dataset.bn },
    };
  }

  // A case that is open stays open — a doctor reading a completed case must not have
  // it snatched away because the working queue emptied underneath them. Likewise a
  // portal showing another full-width screen (the medic's post-referral confirmation)
  // owns the workspace, and the placeholder must not appear underneath it.
  if (currentCase) return;
  if (typeof PORTAL === 'object' && PORTAL.workspaceBusy && PORTAL.workspaceBusy()) return;

  detail.style.display = 'none';
  placeholder.style.display = 'block';

  const copy = (lastQueueItems.length || !(typeof PORTAL === 'object' && PORTAL.emptyWorkspace))
    ? { glyph: placeholderDefaults.glyph,
        title: t(placeholderDefaults.title.en, placeholderDefaults.title.bn),
        detail: t(placeholderDefaults.detail.en, placeholderDefaults.detail.bn) }
    : PORTAL.emptyWorkspace({ scope: queueScope, searching: queueIsSearchResult });

  glyph.textContent = copy.glyph;
  heading.textContent = copy.title;
  body.textContent = copy.detail;
  // These carry data-en/data-bn from the markup; leaving them would let
  // applyLanguage() put "Select Patient" back over the empty-state sentence on the
  // next language toggle. This function re-renders both languages itself instead.
  [heading, body].forEach((el) => { delete el.dataset.en; delete el.dataset.bn; });
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

  box.appendChild(buildCompletenessMeter(item));
}

/* S38 (A3) — the completeness indicator, from a line into a control.

   It used to be a 62px bar and the text "7/10", which told a medic a number without
   telling them anything they could act on: seven of WHICH ten, and had a human looked
   at any of them? Three changes, all of them from data the row already carries:

     * **Ten segments, one per field.** A continuous bar is a percentage; ten ticks are
       ten questions, which is what the medic is actually about to work through. Each
       segment says which field it is, so hovering the third tick names the third field.
     * **Verified is drawn differently from merely filled.** `fields_verified` counts
       the fields a human has confirmed (C2). "Filled" means the model wrote something;
       "verified" means a person agreed. Those are not the same fact and were being
       shown as one.
     * **It opens.** Click or press Enter and the row expands a plain list of exactly
       which fields are still empty — `fields_empty` from the server, so the panel can
       never disagree with the meter above it.

   ⚠ Clicking the meter must NOT open the case: the medic is asking a question about
   the row, not choosing it. Every handler stops propagation. Keyboard reaches it via
   its own tabindex, and `aria-label` carries the same sentence the tooltip does, so
   the information is not conveyed by the bar alone (ADR-0059's rule). */
function buildCompletenessMeter(item) {
  const total = item.fields_total || 10;
  const filled = item.fields_filled || 0;
  const verified = item.fields_verified || 0;
  const empty = item.fields_empty || [];
  const complete = filled >= total;

  const wrap = document.createElement('span');
  wrap.className = 'meter-wrap';

  const meter = document.createElement('span');
  meter.className = 'meter meter-interactive' + (complete ? ' complete' : '');
  meter.tabIndex = 0;
  meter.setAttribute('role', 'button');
  const summary = complete
    ? t(`All ${total} pre-screening questions answered`,
         `সবগুলো (${total}) প্রাক-পরীক্ষার প্রশ্নের উত্তর আছে`)
    : t(`${filled} of ${total} pre-screening questions answered, ${verified} verified by a person`,
         `${total}টির মধ্যে ${filled}টি প্রশ্নের উত্তর আছে, ${verified}টি যাচাই করা`);
  meter.title = summary + ' — ' + t('click for detail', 'বিস্তারিত দেখতে ক্লিক করুন');
  meter.setAttribute('aria-label', summary);

  const track = document.createElement('span');
  track.className = 'meter-track segmented';
  const keys = Object.keys(STAFF_FIELD_LABELS);
  keys.forEach((key, i) => {
    const seg = document.createElement('span');
    const isEmpty = empty.includes(key);
    // Verified segments are counted from the left; the row does not carry WHICH ones
    // are verified (only how many), so this shades a count, not specific fields —
    // and the tooltip says exactly that rather than implying per-field knowledge.
    const isVerified = !isEmpty && i < verified;
    seg.className = 'seg-tick' + (isEmpty ? ' empty' : (isVerified ? ' verified' : ' filled'));
    seg.title = `${i + 1}. ${t(STAFF_FIELD_LABELS[key].en, STAFF_FIELD_LABELS[key].bn)
      .replace(/^\d+\.\s*/, '')} — ${isEmpty ? t('empty', 'খালি') : t('answered', 'উত্তর আছে')}`;
    track.appendChild(seg);
  });

  const num = document.createElement('span');
  num.className = 'meter-num' + (complete ? ' full' : (filled <= total / 2 ? ' low' : ''));
  num.textContent = complete ? `✓ ${filled}/${total}` : `${filled}/${total}`;

  meter.appendChild(track);
  meter.appendChild(num);
  if (verified > 0) {
    const badge = document.createElement('span');
    badge.className = 'meter-verified';
    badge.textContent = `✔${verified}`;
    badge.title = t('Fields a person has confirmed', 'যেসব ঘর একজন মানুষ নিশ্চিত করেছেন');
    meter.appendChild(badge);
  }

  const detail = document.createElement('span');
  detail.className = 'meter-detail';
  detail.style.display = 'none';

  const toggle = (e) => {
    e.stopPropagation();          // the meter is a question about the row, not a click on it
    e.preventDefault();
    const open = detail.style.display === 'none';
    detail.style.display = open ? 'block' : 'none';
    if (open) fillMeterDetail(detail, { total, filled, verified, empty });
  };
  meter.onclick = toggle;
  meter.onkeydown = (e) => { if (e.key === 'Enter' || e.key === ' ') toggle(e); };

  wrap.appendChild(meter);
  wrap.appendChild(detail);
  return wrap;
}

function fillMeterDetail(box, { total, filled, verified, empty }) {
  box.innerHTML = '';
  const head = document.createElement('div');
  head.className = 'meter-detail-head';
  head.textContent = `${filled}/${total} ${t('answered', 'উত্তর আছে')} · ${verified} ${t('verified', 'যাচাইকৃত')}`;
  box.appendChild(head);
  if (!empty.length) {
    const done = document.createElement('div');
    done.textContent = '✓ ' + t('Nothing left to collect.', 'সংগ্রহের আর কিছু বাকি নেই।');
    box.appendChild(done);
    return;
  }
  const label = document.createElement('div');
  label.className = 'meter-detail-head';
  label.textContent = t('Still empty:', 'এখনো খালি:');
  box.appendChild(label);
  empty.forEach((key) => {
    const entry = STAFF_FIELD_LABELS[key];
    const row = document.createElement('div');
    row.textContent = '• ' + (entry ? t(entry.en, entry.bn) : key);
    box.appendChild(row);
  });
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
    /* S38 (C2): THREE states now, not two, because "the model wrote this", "a person
       corrected it" and "a person read it and agreed" are three different facts. The
       third had no way to be recorded before — a medic could only signal it by
       EDITING the field, i.e. retyping the model's own words, which put a false edit
       in a medical record. */
    const verified = !!f.verified_by;
    const badge = f.source === 'human'
      ? `<span class="source-badge source-human">${t('Human Edited', 'মানব-সম্পাদিত')}</span>`
      : (verified
          ? `<span class="source-badge source-verified">✔ ${t('Checked', 'যাচাইকৃত')}</span>`
          : `<span class="source-badge source-ai">${t('AI-Extracted', 'এআই-নির্ণীত')}</span>`);
    const hasText = !!fieldValue(f);
    card.innerHTML =
      `<div class="field-card-header"><span><span class="field-card-icon">${label.icon}</span>${t(label.en, label.bn)}</span><span>▾</span></div>` +
      `<div class="field-card-content">${badge}
         <div style="flex:1;">
           <div class="field-value" style="font-size:.95rem;line-height:1.5;"></div>
           <div class="field-verified-note" style="display:none;font-size:.7rem;color:var(--accent-color);font-weight:600;margin-top:3px;"></div>
           <div class="field-editor" style="display:none;gap:8px;margin-top:8px;">
             <input class="input-field field-input" type="text">
             <button class="btn btn-primary" style="padding:6px 14px;font-size:.8rem;">${t('Save', 'সংরক্ষণ')}</button>
             <button class="btn btn-secondary" style="padding:6px 14px;font-size:.8rem;">${t('Cancel', 'বাতিল')}</button>
           </div>
         </div>` +
      // Only offered where there is something to vouch FOR: "I checked this blank" is
      // not a claim anyone can make, and the server refuses it too.
      (PORTAL.canEdit && hasText && f.source !== 'human'
        ? `<button class="btn ${verified ? 'btn-secondary' : 'btn-accent'} verify-btn" style="padding:6px 12px;font-size:.8rem;">`
          + (verified ? `↺ ${t('Undo check', 'যাচাই বাতিল')}` : `✔ ${t('Looks right', 'ঠিক আছে')}`)
          + `</button>`
        : '') +
      (PORTAL.canEdit ? `<button class="btn btn-secondary edit-btn" style="padding:6px 12px;font-size:.8rem;">✏️ ${t('Edit', 'সম্পাদনা')}</button>` : '') +
      `</div>`;
    card.querySelector('.field-card-header').onclick = () => card.classList.toggle('open');
    // Bilingual DERIVED value (display-only; the medic edits write ALL slots).
    card.querySelector('.field-value').textContent = fieldValue(f) || '—';
    if (verified) {
      const note = card.querySelector('.field-verified-note');
      note.style.display = 'block';
      note.textContent = '✔ ' + t('Checked by a staff member', 'একজন কর্মী যাচাই করেছেন')
        + (f.verified_at ? ` · ${dhakaDateTime(f.verified_at)}` : '');
    }
    const verifyBtn = card.querySelector('.verify-btn');
    if (verifyBtn) {
      verifyBtn.onclick = async () => {
        verifyBtn.disabled = true;
        try {
          const updated = await api('POST',
            `/api/visits/${currentCase.uuid}/profile/fields/${key}/verify`,
            { editor_id: PORTAL.userId, verified: !verified });
          currentCase.profile = updated;
          renderFields(updated);
          loadQueue();   // the queue's verified count follows
        } catch (e) { showError(e.message); verifyBtn.disabled = false; }
      };
    }
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

/* ---- S38 (A5): BMI, shared by both staff portals ----

   Both roles legitimately record vitals on the same `patients` row at different
   moments (ADR-0058: one source of truth used twice, not duplication), so both need
   to render a BMI — which makes this shared code rather than a second copy.

   ⚠ The arithmetic and the band cut-offs are the SERVER's
   (services/clinical_reference, GET /api/reference/bmi). Recomputing them here would
   put published clinical constants in two places, which is the defect class this
   codebase keeps removing. The cost is one small local request per change; the
   benefit is that the portal cannot drift from the reference module.

   ⚠ BMI is never sent to any write endpoint. It is derived from height and weight
   every time it is displayed, so a corrected weight can never leave a stale BMI
   behind (ADR-0060). */

const BMI_BANDS = {
  underweight:    { en: 'Underweight',    bn: 'কম ওজন' },
  normal:         { en: 'Normal',         bn: 'স্বাভাবিক' },
  overweight:     { en: 'Overweight',     bn: 'অতিরিক্ত ওজন' },
  obese:          { en: 'Obese',          bn: 'স্থূল' },
  increased_risk: { en: 'Increased risk', bn: 'ঝুঁকি বেড়েছে' },
  high_risk:      { en: 'High risk',      bn: 'উচ্চ ঝুঁকি' },
};

function bmiBandLabel(code) {
  const entry = BMI_BANDS[code];
  return entry ? t(entry.en, entry.bn) : (code || '—');
}

/* --- S39 (ADR-0064): the medic's blood-sugar reading ------------------------------

   Codes on the wire, labels here — the same split TIER_LABELS and BMI_BANDS follow
   (ADR-0030 item e). What is NOT here is any threshold: the numbers that decide what
   a reading means live in ONE place, `services/clinical_reference`, and are shown as
   the published chart beside the value. This map is only how to say "fasting" twice.

   ⚠ The context is never optional in the UI, because it is never optional in the
   record: the server refuses a value without one. A fasting 6.5 and a random 6.5 are
   different facts, and a number stored without saying which it was cannot be read
   safely by anyone afterwards. */
const GLUCOSE_CONTEXTS = {
  fasting: { en: 'Fasting (8h+ no food)', bn: 'খালি পেটে (৮ ঘণ্টা+)' },
  ogtt_2h: { en: '2 hours after 75g OGTT', bn: '৭৫ গ্রাম OGTT-এর ২ ঘণ্টা পর' },
  random:  { en: 'Random / any time', bn: 'যেকোনো সময়' },
};

function glucoseContextLabel(code) {
  const entry = GLUCOSE_CONTEXTS[code];
  return entry ? t(entry.en, entry.bn) : (code || '—');
}

/* mg/dL per mmol/L, for DISPLAY only. Both unit systems are in daily use in
   Bangladeshi labs and converting at the bedside invites errors — the same reason the
   reference chart prints both. Only the stored mmol/L value is ever sent anywhere.

   ⚠ This MUST equal `clinical_reference.MMOL_TO_MGDL`. It is the one number in this
   file that also exists on the server, so a drift would print a reading in mg/dL that
   disagreed with the chart directly beneath it. A test asserts the two agree. */
const MMOL_TO_MGDL = 18.0;

/** "6.5 mmol/L (117 mg/dL) · Fasting (8h+ no food)" — value and context, never a band. */
function glucoseText(value, context) {
  if (value === null || value === undefined || value === '') return '';
  const num = Number(value);
  if (!isFinite(num)) return '';
  const mgdl = Math.round(num * MMOL_TO_MGDL);
  return `${num} mmol/L (${mgdl} mg/dL) · ${glucoseContextLabel(context)}`;
}

async function showBmi(targetId, weight, height) {
  const box = document.getElementById(targetId);
  if (!box) return;
  const wNum = Number(String(weight === null || weight === undefined ? '' : weight).trim());
  const hNum = Number(String(height === null || height === undefined ? '' : height).trim());
  // Nothing typed yet is not an error — it is simply nothing to show.
  if (!weight || !height || !isFinite(wNum) || !isFinite(hNum)) { box.textContent = ''; return; }
  let res;
  try {
    res = await api('GET', `/api/reference/bmi?weight_kg=${wNum}&height_cm=${hNum}`);
  } catch (_) { box.textContent = ''; return; }   // a missing BMI is harmless; a wrong one is not
  box.innerHTML = '';
  if (res.bmi === null) {
    // The server REFUSED to compute rather than returning something misleading — say
    // so, because a silently blank readout looks like a broken page.
    box.style.color = 'var(--warning-color)';
    box.textContent = '⚠ ' + t(
      'BMI not shown — check the height (cm) and weight (kg) are plausible.',
      'বিএমআই দেখানো হচ্ছে না — উচ্চতা (সেমি) ও ওজন (কেজি) যাচাই করুন।');
    return;
  }
  box.style.color = '';
  const head = document.createElement('span');
  head.style.cssText = 'font-weight:800; color:var(--primary-color);';
  head.textContent = `BMI ${res.bmi} kg/m²`;
  const bands = document.createElement('span');
  bands.style.cssText = 'color:var(--text-muted); margin-left:8px;';
  // Both ladders, both labelled. The Asian action points matter for this population:
  // a BMI of 24 is "normal" internationally and "increased risk" here.
  bands.textContent = `· WHO: ${bmiBandLabel(res.who)}`
    + `  · ${t('WHO Asian cut-offs', 'WHO এশীয় সীমা')}: ${bmiBandLabel(res.asia)}`;
  const note = document.createElement('div');
  note.style.cssText = 'font-size:.72rem; color:var(--warning-color); font-weight:600;';
  note.textContent = '⚠️ ' + (currentLanguage === 'bn' ? res.disclaimer_bn : res.disclaimer);
  box.appendChild(head);
  box.appendChild(bands);
  box.appendChild(note);
}

/* --- S39 (ADR-0064): where the patient's NAME came from -------------------------

   The reported defect: a medic opened a case for a patient who had said nothing
   about a name, and the portal showed one. It was not invented — the patients row is
   keyed by phone number, so a name typed by a colleague during an EARLIER visit is
   attached to the person, not to the visit, and every later case inherits it.

   That inheritance is correct (a returning patient is the same person). Presenting it
   as though it had been established in the case on screen is not. So the name is now
   always rendered WITH its origin, from the server's derived `name_provenance` —
   never re-derived here, and never guessed: `unknown` is displayed as unknown.

   Renders into `targetId` and returns nothing. An absent block is not an error: a
   record with no name says so through patientNameLabel() and needs no second line. */
function renderNameProvenance(targetId, prov) {
  const box = document.getElementById(targetId);
  if (!box) return;
  box.textContent = '';
  box.style.color = '';
  if (!prov || !prov.has_name) return;

  const when = prov.recorded_at ? dhakaDateTime(prov.recorded_at) : null;
  let text;
  if (prov.source === 'staff') {
    text = prov.actor_name
      ? t(`Name entered by ${prov.actor_name}`, `নাম লিখেছেন ${prov.actor_name}`)
      : t('Name entered by clinic staff', 'নাম লিখেছেন ক্লিনিক কর্মী');
  } else if (prov.source === 'ai') {
    text = t('Name taken by the AI from what the patient said',
             'রোগীর কথা থেকে এআই নামটি নিয়েছে');
  } else {
    // Written before S39, or through the kiosk lookup, which was never audited.
    // Saying "we do not know" is the honest answer and the whole reason this exists.
    box.style.color = 'var(--warning-color)';
    box.textContent = 'ⓘ ' + t('Origin of this name is not recorded — please confirm it with the patient.',
                               'এই নামটি কোথা থেকে এসেছে তা লেখা নেই — রোগীর সঙ্গে মিলিয়ে নিন।');
    return;
  }
  if (when) text += t(` on ${when}`, ` — ${when}`);
  /* The line the bug was really about. `from_this_visit` is null when the origin
     visit is unknown, and a null must NOT print "an earlier visit" — that would be
     the same kind of confident guess this whole change removes. */
  if (prov.from_this_visit === false) {
    box.style.color = 'var(--warning-color)';
    text = '⚠ ' + text + t(' — during an EARLIER visit, not this one.',
                           ' — এটি আগের একটি ভিজিটে, এই ভিজিটে নয়।');
  } else {
    box.style.color = 'var(--text-muted)';
    text = 'ⓘ ' + text;
  }
  box.textContent = text;
}


/* --- S39 (ADR-0064): the glucose reference chart, shared by BOTH staff portals ----

   Moved here from frontend_medic/index.html. The medic records the reading; the
   DOCTOR is the one who interprets it, and before S39 the chart existed only on the
   medic's screen. Rather than a second copy of published clinical thresholds in a
   second portal — the exact drift this codebase keeps removing — there is one panel
   and each portal mounts it.

   A6's rules are unchanged, and they are why this is a CHART and not an answer:
   `glucose_reference()` takes no patient value, this function never reads one, and
   the panel says out loud that there is no single "diabetic limit" because which
   numbers apply depends entirely on how the sample was taken (rule #2).

   `mountId` names the element to render into; the call toggles it open and closed.
   The chart is fetched once per portal session and cached. */

let glucoseRef = null;

/* ⚠ S43 — WHICH MOUNTS ARE DISCLOSED, held here rather than read back off the DOM.

   MEASURED defect, present in BOTH staff portals: with the chart open, switching
   language closed it — display went block -> none and its 2186 characters went to 0,
   silently. The cause is that whether the panel is open was inferred from
   `panel.style.display`, and the element carrying that style is destroyed on every
   re-render: `renderIntakeCard()` / `renderPatientDetails()` rebuild their card's
   innerHTML, which recreates the mount from the template's `display:none`. Both
   portals then call renderGlucosePanel() precisely so the chart follows the language —
   and it returned immediately, because the brand-new element said it was closed.

   So the panel's state is no longer stored in the thing that gets thrown away. One
   Set, shared by both portals, keyed by mount id — the doctor and the medic disclose
   independently and neither can close the other's. */
const glucoseOpenMounts = new Set();

async function toggleGlucosePanel(mountId) {
  const panel = document.getElementById(mountId);
  if (!panel) return;
  const opening = !glucoseOpenMounts.has(mountId);
  if (opening) glucoseOpenMounts.add(mountId); else glucoseOpenMounts.delete(mountId);
  panel.style.display = opening ? 'block' : 'none';
  if (!opening) return;
  if (!glucoseRef) {
    panel.textContent = t('Loading reference…', 'রেফারেন্স আসছে…');
    try { glucoseRef = await api('GET', '/api/reference/glucose'); }
    catch (e) { panel.textContent = e.message; return; }
  }
  renderGlucosePanel(mountId);
}

/* One band -> "< 6.0 mmol/L (108 mg/dL)" etc. BOTH unit systems, because both are in
   daily use in Bangladeshi labs and converting at the bedside invites errors. */
function bandRange(band) {
  if (band.low_percent != null || band.high_percent != null) {
    if (band.low_percent == null) return `< ${band.high_percent + 0.1}%`;
    if (band.high_percent == null) return `≥ ${band.low_percent}%`;
    return `${band.low_percent}–${band.high_percent}%`;
  }
  const pair = (mmol, mg) => `${mmol} mmol/L (${mg} mg/dL)`;
  if (band.low_mmol_l == null) return `≤ ${pair(band.high_mmol_l, band.high_mg_dl)}`;
  if (band.high_mmol_l == null) return `≥ ${pair(band.low_mmol_l, band.low_mg_dl)}`;
  return `${band.low_mmol_l}–${pair(band.high_mmol_l, band.high_mg_dl)}`;
}

function renderGlucosePanel(mountId) {
  const panel = document.getElementById(mountId);
  if (!panel || !glucoseRef || !glucoseOpenMounts.has(mountId)) return;
  // The mount may be a fresh element a re-render just created from a template that
  // says display:none, so the disclosure is re-asserted rather than assumed.
  panel.style.display = 'block';
  panel.innerHTML = '';
  const head = document.createElement('div');
  head.style.cssText = 'font-weight:800; color:var(--primary-color); margin-bottom:4px;';
  head.textContent = '🩸 ' + t('Blood glucose — reference values',
                               'রক্তে গ্লুকোজ — রেফারেন্স মান');
  panel.appendChild(head);

  const lead = document.createElement('div');
  lead.style.cssText = 'margin-bottom:8px;';
  lead.textContent = t(
    'There is no single "diabetic limit". Which numbers apply depends entirely on how the sample was taken.',
    'একটিমাত্র "ডায়াবেটিসের সীমা" বলে কিছু নেই। কোন মান প্রযোজ্য তা পুরোপুরি নির্ভর করে নমুনা কীভাবে নেওয়া হয়েছে তার উপর।');
  panel.appendChild(lead);

  glucoseRef.contexts.forEach((ctx) => {
    const block = document.createElement('div');
    block.style.cssText = 'margin-bottom:9px; padding-left:9px; border-left:2px solid var(--border-color);';
    const name = document.createElement('div');
    name.style.cssText = 'font-weight:700;';
    name.textContent = t(ctx.name_en, ctx.name_bn);
    block.appendChild(name);
    const req = document.createElement('div');
    req.style.cssText = 'font-size:.7rem; color:var(--text-muted); margin-bottom:3px;';
    req.textContent = t(ctx.requires_context_en, ctx.requires_context_bn);
    block.appendChild(req);
    ctx.bands.forEach((band) => {
      const row = document.createElement('div');
      row.style.fontSize = '.72rem';
      row.textContent = `• ${t(band.label_en, band.label_bn)}: ${bandRange(band)}`;
      block.appendChild(row);
    });
    const note = t(ctx.note_en, ctx.note_bn);
    if (note) {
      const n = document.createElement('div');
      n.style.cssText = 'font-size:.7rem; color:var(--warning-color); margin-top:2px;';
      n.textContent = '⚠ ' + note;
      block.appendChild(n);
    }
    const src = document.createElement('div');
    src.style.cssText = 'font-size:.66rem; color:var(--text-muted); margin-top:2px;';
    src.textContent = ctx.source;
    block.appendChild(src);
    panel.appendChild(block);
  });

  const disc = document.createElement('div');
  disc.style.cssText = 'font-size:.72rem; font-weight:600; color:var(--warning-color); border-top:1px dashed var(--border-color); padding-top:6px;';
  disc.textContent = '⚠️ ' + (currentLanguage === 'bn'
    ? glucoseRef.disclaimer_bn : glucoseRef.disclaimer);
  panel.appendChild(disc);
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
