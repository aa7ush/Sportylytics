/**
 * Sportylytics – main.js
 * Core UI behaviours: sidebar toggle, date navigation, live indicator clock
 */

// ── Sidebar ──────────────────────────────────────────────────────────────────
const sidebar      = document.getElementById('sidebar');
const mainContent  = document.getElementById('main-content');
const toggleBtn    = document.getElementById('sidebar-toggle-btn');

let sidebarCollapsed = localStorage.getItem('sidebar-collapsed') === 'true';

function applySidebarState() {
  if (sidebarCollapsed) {
    sidebar.classList.add('collapsed');
    mainContent.classList.add('sidebar-collapsed');
    toggleBtn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>`;
  } else {
    sidebar.classList.remove('collapsed');
    mainContent.classList.remove('sidebar-collapsed');
    toggleBtn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>`;
  }
}

if (toggleBtn) {
  toggleBtn.addEventListener('click', () => {
    sidebarCollapsed = !sidebarCollapsed;
    localStorage.setItem('sidebar-collapsed', sidebarCollapsed);
    applySidebarState();
  });
}

// Apply on load
applySidebarState();

// ── Collapsible competition sections ─────────────────────────────────────────
function toggleSection(sectionId) {
  const section = document.getElementById(sectionId);
  if (!section) return;
  const header   = section.querySelector('.comp-header');
  const matchList = section.querySelector('.match-list');
  if (!matchList) return;

  const isCollapsed = matchList.style.display === 'none';
  matchList.style.display = isCollapsed ? 'flex' : 'none';
  if (header) header.classList.toggle('collapsed', !isCollapsed);
}

// ── Tab switching ─────────────────────────────────────────────────────────────
function switchTab(name) {
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

  const activeBtn = document.getElementById(`tab-${name}-btn`);
  const activeContent = document.getElementById(`tab-${name}`);
  if (activeBtn) activeBtn.classList.add('active');
  if (activeContent) activeContent.classList.add('active');
}

// ── Date Navigation ───────────────────────────────────────────────────────────
function initDateNav(selectedDate) {
  const nav = document.getElementById('date-nav');
  if (!nav) return;

  const dates = [];
  const today = new Date();

  // Generate -3 days to +3 days
  for (let i = -3; i <= 3; i++) {
    const d = new Date(today);
    d.setDate(today.getDate() + i);
    dates.push(d);
  }

  nav.innerHTML = '';

  dates.forEach(d => {
    const iso = d.toISOString().slice(0, 10);
    const label = formatDateLabel(d);
    const btn = document.createElement('a');
    btn.href = `/?date=${iso}`;
    btn.className = `date-btn${iso === selectedDate ? ' active' : ''}`;
    btn.textContent = label;
    btn.id = `date-btn-${iso}`;
    nav.appendChild(btn);
  });
}

function formatDateLabel(d) {
  const today = new Date();
  const yesterday = new Date(today); yesterday.setDate(today.getDate() - 1);
  const tomorrow  = new Date(today); tomorrow.setDate(today.getDate() + 1);

  const iso = d.toISOString().slice(0, 10);
  const todayIso     = today.toISOString().slice(0, 10);
  const yesterdayIso = yesterday.toISOString().slice(0, 10);
  const tomorrowIso  = tomorrow.toISOString().slice(0, 10);

  if (iso === todayIso)     return 'Today';
  if (iso === yesterdayIso) return 'Yesterday';
  if (iso === tomorrowIso)  return 'Tomorrow';

  return d.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' });
}

// ── Live Match Indicator ──────────────────────────────────────────────────────
function checkLiveMatches() {
  const indicator = document.getElementById('live-indicator');
  if (!indicator) return;

  // Check if any live-dot elements exist on the page
  const liveDots = document.querySelectorAll('.status-live');
  if (liveDots.length > 0) {
    indicator.style.display = 'inline-flex';
  }
}

// ── Real-time Clock ───────────────────────────────────────────────────────────
const clockEl = document.getElementById('header-clock');
function updateClock() {
  if (!clockEl) return;
  const now = new Date();
  clockEl.textContent = now.toLocaleTimeString('en-GB', {
    hour: '2-digit', minute: '2-digit', second: '2-digit'
  });
}

updateClock();
setInterval(updateClock, 1000);

// ── Time Localization ────────────────────────────────────────────────────────
function localizeAllTimes() {
  document.querySelectorAll('.local-time').forEach(el => {
    const ts = parseInt(el.getAttribute('data-ts'));
    const format = el.getAttribute('data-format');
    if (!ts) return;
    const date = new Date(ts * 1000);
    if (format === 'time') {
      el.textContent = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
    } else if (format === 'datetime') {
      el.textContent = date.toLocaleString([], { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false });
    } else {
      el.textContent = date.toLocaleDateString([], { day: 'numeric', month: 'short', year: 'numeric' });
    }
  });
}

// ── Smooth image load ─────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  localizeAllTimes();
  document.querySelectorAll('img').forEach(img => {
    img.style.opacity = '0';
    img.style.transition = 'opacity 0.3s';
    if (img.complete) {
      img.style.opacity = '1';
    } else {
      img.addEventListener('load',  () => { img.style.opacity = '1'; });
      img.addEventListener('error', () => { img.style.opacity = '1'; });
    }
  });
});

// ── Pin Logic ─────────────────────────────────────────────────────────────────
function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return null;
}

function parsePinsCookie(cookieName) {
  const raw = getCookie(cookieName);
  if (!raw) return [];
  try {
    return JSON.parse(decodeURIComponent(raw));
  } catch (e) {
    return [];
  }
}

function togglePin(type, id, name) {
  const cookieName = `pins_${type}`;
  let pins = parsePinsCookie(cookieName);
  const exists = pins.find(p => p.id == id);
  
  if (exists) {
    pins = pins.filter(p => p.id != id);
  } else {
    pins.push({ id: id, name: name });
  }
  
  const encoded = encodeURIComponent(JSON.stringify(pins));
  document.cookie = `${cookieName}=${encoded};path=/;max-age=31536000`;
  window.location.reload();
}

// Automatically highlight pinned icons natively
document.addEventListener('DOMContentLoaded', () => {
  ['teams', 'leagues'].forEach(type => {
    const pins = parsePinsCookie(`pins_${type}`);
    pins.forEach(p => {
      const icon = document.getElementById(`pin-icon-${type}-${p.id}`);
      if (icon) icon.textContent = '★';
    });
  });
});
