/* Shared helpers for all three portals (FE-0).
   - TIER_LABELS: the ONE place risk tier codes map to display labels (ADR-0030 e —
     the schema/API always speak 'low|medium|high|critical'; "Moderate" etc. live here).
   - TIER_BANDS: display-only tier→percentage-band map (decision C2, Session 9).
   - fieldValue(): bilingual summary-field values (value_bn/value_en, {value} legacy).
   - Bilingual EN/BN via data-en / data-bn attributes (mockup pattern).
   - api(): thin fetch wrapper that surfaces backend error details. */

const TIER_LABELS = {
  low:      { en: 'Low',      bn: 'স্বাভাবিক' },
  medium:   { en: 'Moderate', bn: 'মাঝারি' },
  high:     { en: 'High',     bn: 'উচ্চ' },
  critical: { en: 'Critical', bn: 'ঝুঁকিপূর্ণ' },
};

/* Decision C2 (Session 9): the "risk score %" the staff UIs show is a FIXED band per
   tier, purely presentational. No numeric score is generated, stored, or sent on the
   wire — inventing per-case percentages would fake precision the model doesn't have. */
const TIER_BANDS = {
  low:      '0–25%',
  medium:   '26–50%',
  high:     '51–75%',
  critical: '76–100%',
};

let currentLanguage = localStorage.getItem('lang') || 'en';

function tierLabel(tier) {
  const entry = TIER_LABELS[tier];
  return entry ? entry[currentLanguage] : (tier || '—');
}

function tierBand(tier) {
  return TIER_BANDS[tier] || '—';
}

function tierBadge(tier) {
  if (!tier) return '<span class="risk-badge">—</span>';
  return `<span class="risk-badge risk-${tier}">${tierLabel(tier)}</span>`;
}

/* One summary field ({value_bn, value_en, source, ...}) -> the display string for the
   CURRENT language. Falls back across languages, then to the legacy {value} shape
   (pre-Session-9 rows), then to ''. Callers supply their own empty placeholder.
   Display-only: never writes back — the stored field is untouched. */
function fieldValue(field) {
  if (!field || typeof field !== 'object') return '';
  const byLang = currentLanguage === 'bn'
    ? [field.value_bn, field.value, field.value_en]
    : [field.value_en, field.value, field.value_bn];
  for (const v of byLang) {
    const s = (v === undefined || v === null) ? '' : String(v).trim();
    if (s) return s;
  }
  return '';
}

/* Re-render every element carrying data-en/data-bn in the chosen language. */
function applyLanguage() {
  document.querySelectorAll('[data-en]').forEach((el) => {
    const text = el.dataset[currentLanguage];
    if (text !== undefined) el.textContent = text;
  });
  // P1-2: bilingual input placeholders via data-en-placeholder / data-bn-placeholder.
  document.querySelectorAll('[data-en-placeholder]').forEach((el) => {
    const p = el.dataset[currentLanguage + 'Placeholder'];
    if (p !== undefined) el.placeholder = p;
  });
  document.querySelectorAll('.lang-btn').forEach((b) => {
    b.classList.toggle('active', b.dataset.lang === currentLanguage);
  });
}

function setLanguage(lang) {
  currentLanguage = lang;
  localStorage.setItem('lang', lang);
  applyLanguage();
  if (typeof onLanguageChange === 'function') onLanguageChange();
}

function t(en, bn) { return currentLanguage === 'bn' ? bn : en; }

/* S38 — a NUMBER in the active language's digits. Bangla renders ১৫, not 15, and a
   sentence that is Bangla everywhere except its numerals reads as half-translated.
   The queue's own counts already come out of toLocaleString via the date helpers;
   this is for numbers built into interpolated strings. */
function localeNum(n) {
  return Number(n).toLocaleString(currentLanguage === 'bn' ? 'bn-BD' : 'en-GB');
}

/* S39 (ADR-0064) — the ONE representation of "this record carries no name".

   Before this there were four: the medic's intake line said "(no name)", the
   post-referral summary and the doctor's details card both said "—", and the .docx
   said "—" as well. A dash is what this project prints for a value that was not
   recorded, which is right — but it is also what it prints for a dozen other empty
   things, so the one field a patient is identified by said nothing about itself.
   Naming the absence is the point: a medic must be able to tell "nobody asked" from
   "the screen is still loading".

   ⚠ It is a LABEL, never a value: it is not stored, not sent, and never appears in an
   export. `services/ehr_export` still omits the FHIR `name` element entirely when
   there is no name, which is the correct machine-readable way to say "absent". */
function patientNameLabel(name) {
  const text = (name === undefined || name === null) ? '' : String(name).trim();
  return text || t('Name not provided', 'নাম দেওয়া হয়নি');
}

/* STRUCT-2: every portal header offers Logout back to the Portal Directory at "/".
   Auth is stubbed (no server session to clear), so logout = leave the page; each
   portal's in-memory state is discarded by the navigation itself. */
function logout() { window.location.href = '/'; }

/* P2-1: timestamps are stored/serialized as UTC, but SQLite rows come back
   OFFSET-LESS (e.g. "2026-07-05T14:03:42.884654") — new Date() would read that as
   LOCAL time, which is exactly the "random queue time" bug. parseUtc() pins
   offset-less strings to UTC; the dhaka*() formatters then always display
   Bangladesh time (Asia/Dhaka) regardless of the viewing PC's zone. */
function parseUtc(value) {
  if (value instanceof Date) return value;
  const s = String(value || '').trim();
  const hasZone = /([Zz]|[+-]\d{2}:?\d{2})$/.test(s);
  return new Date(hasZone ? s : s + 'Z');
}

/* S38 (A7): every clock in the staff portals is a 12-hour clock with AM/PM.
   The 24-hour `en-GB` default was a developer's clock, not a clinic's — Bangladeshi
   staff write and read "3:40 PM", and a queue row saying "15:40" is one extra
   translation step for the exact user this project is built for (elderly and
   non-technical). `hour: 'numeric'` rather than '2-digit' so it reads "3:40 PM",
   not "03:40 PM". The Bangla locale renders both the digits and the day-period in
   Bangla script. */
const DHAKA = 'Asia/Dhaka';
function _locale() { return currentLanguage === 'bn' ? 'bn-BD' : 'en-GB'; }

function dhakaTime(value) {
  const d = parseUtc(value);
  if (isNaN(d)) return '—';
  return d.toLocaleTimeString(_locale(),
    { timeZone: DHAKA, hour: 'numeric', minute: '2-digit', hour12: true });
}

function dhakaDateTime(value) {
  const d = parseUtc(value);
  if (isNaN(d)) return '—';
  return d.toLocaleString(_locale(),
    { timeZone: DHAKA, day: '2-digit', month: 'short', year: 'numeric',
      hour: 'numeric', minute: '2-digit', hour12: true });
}

/* A7 — the LIVE clock: what the actual date and time are RIGHT NOW in Dhaka.
   Distinct from the two formatters above, which render a STORED moment. Nothing is
   hard-coded and nothing is passed in: it reads the system clock every call, so a
   caller ticking it on an interval shows a running clock.
   ⚠ `timeZone: 'Asia/Dhaka'` is safe in the browser (every modern engine ships the
   full IANA database); the SERVER cannot rely on that — Windows has no tz database —
   which is why backend/app/services/clinical_dates.py uses a fixed +06:00 offset
   instead. The two agree because Bangladesh has had no DST since 2010. */
function dhakaNowParts() {
  const now = new Date();
  return {
    date: now.toLocaleDateString(_locale(),
      { timeZone: DHAKA, weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }),
    time: now.toLocaleTimeString(_locale(),
      { timeZone: DHAKA, hour: 'numeric', minute: '2-digit', second: '2-digit', hour12: true }),
  };
}

/* A7 / B5 — today's Dhaka calendar date as YYYY-MM-DD, for defaulting and for the
   `min`/`max` of a date input. `toISOString()` would give the UTC date, which is
   YESTERDAY for the first six hours of every Dhaka day — that is exactly the bug the
   prescription form shipped with. `en-CA` is used because it formats as ISO. */
function dhakaTodayIso() {
  return new Date().toLocaleDateString('en-CA', { timeZone: DHAKA });
}

/* fetch wrapper: throws Error with the backend's detail message on failure. */
async function api(method, path, body) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body !== undefined) opts.body = JSON.stringify(body);
  const res = await fetch(path, opts);
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try { detail = (await res.json()).detail || detail; } catch (_) { /* keep default */ }
    const err = new Error(detail);
    /* S42: carry the STATUS, not just the message. The kiosk has to distinguish "the
       AI provider chain is down" (502 — temporary, worth a retry button) from a real
       client error like 409 "question already answered" (retrying only fails again).
       Deciding that by matching words in `detail` would break the moment the wording
       changed — and the whole point of S42 is that the wording no longer carries
       provider text. `retryAfter` is the server's own hint, when it sends one. */
    err.status = res.status;
    const retryAfter = res.headers.get('Retry-After');
    if (retryAfter) err.retryAfter = Number(retryAfter) || null;
    throw err;
  }
  return res.json();
}

/* S41 — bring the thing the user must act on into view, and NOTHING else.

   Introduced in S40 inside kiosk.js; MOVED here in S41 because the medic portal needed
   exactly the same behaviour and a second copy is how two answers to one question start
   disagreeing. shared.js is loaded by all three portals, so there is one implementation.

   `block: 'nearest'` is the whole restraint: an element already fully on screen does not
   move at all, and one that is partly below the fold is scrolled just far enough to
   reveal it. That is what makes this safe to call on every state change — it is silent
   unless it is needed.

   `void offsetHeight` first: in the same tick an element is un-hidden the layout is
   still stale and scrollIntoView() is a silent no-op. That is a MEASURED defect, twice
   over — the kiosk read-back panel (S34) and the medic intake form (S41). */
function bringIntoView(target, { block = 'nearest' } = {}) {
  const el = typeof target === 'string' ? document.getElementById(target) : target;
  if (!el || !el.scrollIntoView) return;
  void el.offsetHeight;
  const reduced = window.matchMedia
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const scroll = (behavior) => {
    try { el.scrollIntoView({ block, inline: 'nearest', behavior }); }
    catch (_) { el.scrollIntoView(); }   // older engine: no options object
  };
  if (reduced) { scroll('auto'); return; }
  scroll('smooth');
  /* ⚠ Smooth scrolling is a NICETY; landing in view is the REQUIREMENT, so the result
     is verified rather than assumed. MEASURED on the medic case workspace: a smooth
     `scrollIntoView` left `scrollTop` at 0 even after 1.5 s, while the identical call
     with `behavior: 'auto'` moved it by exactly the 55px needed. That container carries
     `perspective: 1400px` from the S37 depth layer, and Chromium silently declines to
     smooth-scroll a scroller in a 3D rendering context. Removing the perspective would
     trade a real visual regression for an animation, so the animation is what gives way.
     If the smooth attempt has not landed, finish the job instantly. */
  setTimeout(() => { if (!isFullyInView(el)) scroll('auto'); }, 320);
}

/* Is every edge of `el` inside the window AND inside each scrollable ancestor?

   The window test alone is not enough: an element scrolled out of a short scroller that
   itself sits mid-page still reports a rect inside the window, so it would look visible
   while being clipped. Each scrollable ancestor is therefore checked too. */
function isFullyInView(el) {
  const rect = el.getBoundingClientRect();
  const viewH = window.innerHeight || document.documentElement.clientHeight;
  const viewW = window.innerWidth || document.documentElement.clientWidth;
  if (rect.top < 0 || rect.bottom > viewH || rect.left < 0 || rect.right > viewW) return false;
  for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) {
    const style = window.getComputedStyle(p);
    const scrolls = /(auto|scroll|overlay)/.test(style.overflowY + style.overflowX);
    if (!scrolls) continue;
    const box = p.getBoundingClientRect();
    if (rect.top < box.top || rect.bottom > box.bottom) return false;
  }
  return true;
}

function showError(msg) {
  const banner = document.getElementById('error-banner');
  if (!banner) { alert(msg); return; }
  banner.textContent = msg;
  banner.style.display = 'block';
  clearTimeout(showError._t);
  showError._t = setTimeout(() => { banner.style.display = 'none'; }, 8000);
}

document.addEventListener('DOMContentLoaded', applyLanguage);
