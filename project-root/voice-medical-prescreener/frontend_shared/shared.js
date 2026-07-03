/* Shared helpers for all three portals (FE-0).
   - TIER_LABELS: the ONE place risk tier codes map to display labels (ADR-0030 e —
     the schema/API always speak 'low|medium|high|critical'; "Moderate" etc. live here).
   - Bilingual EN/BN via data-en / data-bn attributes (mockup pattern).
   - api(): thin fetch wrapper that surfaces backend error details. */

const TIER_LABELS = {
  low:      { en: 'Low',      bn: 'স্বাভাবিক' },
  medium:   { en: 'Moderate', bn: 'মাঝারি' },
  high:     { en: 'High',     bn: 'উচ্চ' },
  critical: { en: 'Critical', bn: 'ঝুঁকিপূর্ণ' },
};

let currentLanguage = localStorage.getItem('lang') || 'en';

function tierLabel(tier) {
  const entry = TIER_LABELS[tier];
  return entry ? entry[currentLanguage] : (tier || '—');
}

function tierBadge(tier) {
  if (!tier) return '<span class="risk-badge">—</span>';
  return `<span class="risk-badge risk-${tier}">${tierLabel(tier)}</span>`;
}

/* Re-render every element carrying data-en/data-bn in the chosen language. */
function applyLanguage() {
  document.querySelectorAll('[data-en]').forEach((el) => {
    const text = el.dataset[currentLanguage];
    if (text !== undefined) el.textContent = text;
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

/* fetch wrapper: throws Error with the backend's detail message on failure. */
async function api(method, path, body) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body !== undefined) opts.body = JSON.stringify(body);
  const res = await fetch(path, opts);
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try { detail = (await res.json()).detail || detail; } catch (_) { /* keep default */ }
    throw new Error(detail);
  }
  return res.json();
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
