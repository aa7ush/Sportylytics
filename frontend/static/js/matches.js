/**
 * Sportylytics – matches.js
 * Live score polling and dynamic match card updates (Sofascore schema)
 * Data shape: { events: [ { id, homeScore: { display }, awayScore: { display }, status: { type, description } } ] }
 */

const POLL_INTERVAL_MS = 60_000; // 60 seconds

/**
 * Start polling today's matches for live score updates.
 * Only activates if there are live matches visible on the page.
 */
function startLivePolling(currentDate) {
  const hasLive = document.querySelectorAll('.status-live').length > 0;
  if (!hasLive) return;

  setInterval(() => {
    const date = currentDate || new Date().toISOString().slice(0, 10);
    fetch(`/api/matches?date=${date}`)
      .then(r => r.json())
      .then(data => {
        const events = data.events || [];
        events.forEach(ev => updateMatchCard(ev));
      })
      .catch(() => {/* silently ignore */});
  }, POLL_INTERVAL_MS);
}

/**
 * Update a single match card based on a Sofascore event object.
 */
function updateMatchCard(ev) {
  const card = document.getElementById(`match-${ev.id}`);
  if (!card) return;

  const hs  = ev.homeScore || {};
  const as_ = ev.awayScore || {};
  const st  = ev.status   || {};

  // ── Score display ──────────────────────────────────────────
  const homeScoreEl = card.querySelector(`#score-${ev.id}-h`);
  const awayScoreEl = card.querySelector(`#score-${ev.id}-a`);

  if (homeScoreEl && hs.display != null) {
    const newH = String(hs.display);
    if (homeScoreEl.textContent !== newH) {
      flashScore(homeScoreEl, newH);
    }
  }
  if (awayScoreEl && as_.display != null) {
    const newA = String(as_.display);
    if (awayScoreEl.textContent !== newA) {
      flashScore(awayScoreEl, newA);
    }
  }

  // ── Status display ─────────────────────────────────────────
  const statusEl = card.querySelector('.match-status');
  if (!statusEl) return;

  if (st.type === 'inprogress') {
    const desc = (st.description || 'LIVE')
      .replace('half', 'H').replace(' ', '').toUpperCase();
    statusEl.innerHTML = `<div class="status-live"><span class="status-live-dot"></span>${desc}</div>`;
    const indicator = document.getElementById('live-indicator');
    if (indicator) indicator.style.display = 'inline-flex';
  } else if (st.type === 'finished') {
    statusEl.innerHTML = '<span class="status-ft">FT</span>';
  }
}

function flashScore(el, newVal) {
  el.textContent = newVal;
  el.style.transition = 'color 0.3s';
  el.style.color = 'var(--green)';
  setTimeout(() => { el.style.color = ''; }, 1500);
}

// Expose globally
window.startLivePolling = startLivePolling;
