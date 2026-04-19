/**
 * render.js - Logic for rendering JSON data into the DOM.
 * Replaces the work previously done by Jinja2 templates.
 */

// ── Common Elements ─────────────────────────────────────────────────────────

function renderCommon(config) {
    // Render Sidebar
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
        sidebar.innerHTML = `
            <div class="sidebar-header">
                <div class="sidebar-logo"><img src="/static/img/logo.png" style="width:28px;"></div>
                <span class="sidebar-title">Sportylytics</span>
                <button class="sidebar-toggle" id="sidebar-toggle-btn">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>
                </button>
            </div>
            <nav class="sidebar-nav">
                <div class="nav-section-label">Main</div>
                <a href="/" class="nav-item ${window.location.pathname === '/' ? 'active' : ''}">
                    <span class="nav-icon">🏠</span><span class="nav-text">Home</span>
                </a>
                <a href="/search" class="nav-item ${window.location.pathname.includes('search') ? 'active' : ''}">
                    <span class="nav-icon">🔍</span><span class="nav-text">Search</span>
                </a>
                <div class="nav-section-label" style="margin-top:8px;">Competitions</div>
                ${Object.entries(config.leagues).map(([id, info]) => `
                    <a href="/league/${id}" class="nav-item comp-item" title="${info.name}">
                        <img src="${config.league_image_url.replace('{id}', id)}" style="width:18px;height:18px;object-fit:contain;">
                        <span class="nav-text comp-name">${info.name}</span>
                    </a>
                `).join('')}
            </nav>
        `;
    }

    // Render Top Header
    const header = document.getElementById('top-header');
    if (header) {
        header.innerHTML = `
            <div class="header-search">
                <form action="/search" method="GET">
                    <span class="search-icon">🔍</span>
                    <input type="text" name="q" placeholder="Search for players, teams, or competitions...">
                </form>
            </div>
            <div class="header-spacer"></div>
            <div class="live-badge" id="live-indicator" style="display:none;"><span class="live-dot"></span>LIVE</div>
            <span style="font-size:12px; color:var(--text-muted);" id="header-clock"></span>
        `;
    }

    // Render Footer
    const footer = document.getElementById('footer');
    if (footer) {
        footer.innerHTML = `
            <span style="font-size:12px; color:var(--text-muted); display:flex; align-items:center; gap:6px;">
                <img src="/static/img/logo.png" style="width:14px;"> Sportylytics &copy; ${new Date().getFullYear()} &mdash; Data sourced from Sofascore
            </span>
        `;
    }
}

// ── Index Page ──────────────────────────────────────────────────────────────

async function renderIndex(date) {
    const data = await fetchData(`/?date=${date}`);
    const container = document.getElementById('matches-container');
    if (!data || !container) return;

    let html = '';
    
    // Pinned matches
    if (data.pinned_matches && Object.keys(data.pinned_matches).length > 0) {
        html += `<div class="section-card-header" style="margin-bottom:16px;">📌 Pinned Matches</div>`;
        html += Object.entries(data.pinned_matches).map(([uid, group]) => renderGroup(uid, group, true)).join('');
        html += `<div class="section-card-header" style="margin-bottom:16px;">🌍 All Matches</div>`;
    }

    // Grouped matches
    if (data.grouped_matches && Object.keys(data.grouped_matches).length > 0) {
        html += Object.entries(data.grouped_matches).map(([uid, group]) => renderGroup(uid, group)).join('');
    } else {
        html += `
            <div class="empty-state">
                <div class="empty-state-icon">📅</div>
                <div class="empty-state-text">No matches found for this date</div>
            </div>
        `;
    }

    container.innerHTML = html;
    
    // Re-initialize nav if the script exists
    if (typeof initDateNav === 'function') initDateNav(date);
    if (typeof startLivePolling === 'function') startLivePolling(date);
}

function renderGroup(uid, group, isPinned = false) {
    const ut = group.tournament;
    const suffix = isPinned ? '-pinned' : '';
    const sectionId = `comp-section-${uid}${suffix}`;
    
    return `
        <div class="competition-section" id="${sectionId}">
            <div class="comp-header" onclick="toggleSection('${sectionId}')">
                <img class="comp-header-emblem" src="https://api.sofascore.app/api/v1/unique-tournament/${ut.id}/image" alt="${ut.name}">
                <span class="comp-header-name">${ut.name}</span>
                <span class="comp-header-country">&middot; ${ut.category ? ut.category.name : ''}</span>
                <a href="/standings/${ut.id}" class="badge badge-muted" style="margin-left:8px;" onclick="event.stopPropagation();">Table</a>
                <span class="comp-header-chevron">▼</span>
            </div>
            <div class="match-list">
                ${group.events.map(ev => renderMatchCard(ev, isPinned)).join('')}
            </div>
        </div>
    `;
}

function renderMatchCard(ev, isPinned) {
    const home = ev.homeTeam;
    const away = ev.awayTeam;
    const st = ev.status;
    const start = ev.startTimestamp;
    const suffix = isPinned ? '-pinned' : '';

    let statusHtml = '';
    if (st.type === 'inprogress') {
        statusHtml = `<div class="status-live"><span class="status-live-dot"></span>${st.description.toUpperCase()}</div>`;
    } else if (st.type === 'finished') {
        statusHtml = `<span class="status-ft">FT</span>`;
    } else {
        statusHtml = `<span class="status-time">${new Date(start * 1000).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>`;
    }

    return `
        <div class="match-card" id="match-${ev.id}${suffix}" onclick="window.location.href='/match/${ev.id}'">
            <div class="match-status">${statusHtml}</div>
            <div class="team-col home">
                <img class="team-crest" src="https://api.sofascore.app/api/v1/team/${home.id}/image">
                <span class="team-name">${home.shortName || home.name}</span>
            </div>
            <div class="score-col">
                ${st.type !== 'notstarted' ? `
                    <span class="score-display">${ev.homeScore.display ?? 0}</span>
                    <span class="score-dash"> – </span>
                    <span class="score-display">${ev.awayScore.display ?? 0}</span>
                ` : '<span class="score-display" style="font-size:13px; color:var(--text-muted);">vs</span>'}
            </div>
            <div class="team-col away">
                <img class="team-crest" src="https://api.sofascore.app/api/v1/team/${away.id}/image">
                <span class="team-name">${away.shortName || away.name}</span>
            </div>
        </div>
    `;
}

// ── Player Page ─────────────────────────────────────────────────────────────

async function renderPlayer(id) {
    const data = await fetchData(`/player/${id}`);
    const area = document.getElementById('content-area');
    if (!data || !area) return;

    const p = data.player;
    const team = data.team;
    const tc = team.teamColors || {};
    
    // Header Hero
    area.innerHTML = `
        <div class="page-content">
            <div class="player-hero">
                <div class="player-hero-bg" style="background: linear-gradient(135deg, ${tc.primary || '#2563eb'}22 0%, var(--bg-card) 100%);"></div>
                <div class="player-hero-content">
                    <div class="player-hero-portrait">
                        <img src="https://api.sofascore.app/api/v1/player/${p.id}/image" onerror="this.src='/static/img/player-placeholder.png';">
                    </div>
                    <div class="player-hero-info">
                        ${team.id ? `
                            <div class="player-hero-team-badge">
                                <img src="https://api.sofascore.app/api/v1/team/${team.id}/image">
                                <span>${team.name}</span>
                            </div>
                        ` : ''}
                        <h1 class="player-hero-name">${p.name}</h1>
                        <div class="player-hero-meta">
                            <div class="meta-item"><span class="meta-label">Position</span><div class="meta-value">${p.position}</div></div>
                            <div class="meta-item"><span class="meta-label">Date of Birth</span><div class="meta-value">${formatDate(p.dateOfBirthTimestamp)}</div></div>
                            <div class="meta-item"><span class="meta-label">Height</span><div class="meta-value">${p.height} cm</div></div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="tabs" style="margin-top:24px;">
                <button class="tab-btn active" onclick="switchTab('overview')" id="tab-overview-btn">Overview</button>
                <button class="tab-btn" onclick="switchTab('career')" id="tab-career-btn">Career</button>
                <button class="tab-btn" onclick="switchTab('transfers')" id="tab-transfers-btn">Transfers</button>
            </div>

            <div class="tab-content active" id="tab-overview">
                <div class="section-grid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(380px,1fr));gap:24px;">
                    <!-- Characteristics -->
                    <div class="section-card">
                        <div class="section-card-header">Characteristics</div>
                        <div class="section-card-body">
                            ${(data.attributes || []).map(a => `
                                <div class="attribute-item">
                                    <div class="attribute-label"><span>${a.name}</span><span>${a.value}</span></div>
                                    <div class="attribute-bar-bg"><div class="attribute-bar-fill" style="width:${a.value}%;"></div></div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    <!-- Performance -->
                    <div class="section-card">
                        <div class="section-card-header">Recent Performance</div>
                        <div class="section-card-body">
                            <table class="perf-table">
                                ${data.performance.map(m => `
                                    <tr>
                                        <td>${m.homeTeam.shortName} vs ${m.awayTeam.shortName}</td>
                                        <td style="text-align:center;">${m.homeScore.display ?? 0} - ${m.awayScore.display ?? 0}</td>
                                        <td style="text-align:right;">
                                            <span class="perf-rating" style="background:${getRatingColor(m.rating)}">${(m.rating || 0).toFixed(1)}</span>
                                        </td>
                                    </tr>
                                `).join('')}
                            </table>
                        </div>
                    </div>
                </div>
            </div>

            <div class="tab-content" id="tab-career">
                <div class="section-card">
                    <div class="section-card-header">Overall Career Stats</div>
                    <div class="section-card-body" style="padding:0;">
                        <table class="data-table">
                            <thead>
                                <tr><th>Season</th><th>Team</th><th>Tournament</th><th>Apps</th><th>Goals</th></tr>
                            </thead>
                            <tbody>
                                ${data.overall_stats.map(s => `
                                    <tr>
                                        <td>${s.season}</td>
                                        <td>${s.teamName}</td>
                                        <td>${s.tournament}</td>
                                        <td>${s.apps}</td>
                                        <td>${s.goals}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <div class="tab-content" id="tab-transfers">
                <div class="section-card">
                    <div class="section-card-header">Transfer History</div>
                    <div class="section-card-body" style="padding:0;">
                        <table class="data-table">
                            <thead>
                                <tr><th>Date</th><th>From</th><th>To</th><th>Fee</th></tr>
                            </thead>
                            <tbody>
                                ${data.transfers.map(t => `
                                    <tr>
                                        <td>${formatDate(t.transferDateTimestamp)}</td>
                                        <td>${t.transferFrom?.name || 'N/A'}</td>
                                        <td>${t.transferTo?.name || 'N/A'}</td>
                                        <td>${t.transferFeeDescription || 'N/A'}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function switchTab(tabId) {
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + tabId).classList.add('active');
  document.getElementById('tab-' + tabId + '-btn').classList.add('active');
}

// ── Team Page ───────────────────────────────────────────────────────────────

async function renderTeam(id) {
    const data = await fetchData(`/team/${id}`);
    const area = document.getElementById('content-area');
    if (!data || !area) return;

    const t = data.team;
    area.innerHTML = `
        <div class="page-content">
            <div class="section-card">
                <div class="section-card-header" style="display:flex;align-items:center;gap:16px;">
                    <img src="https://api.sofascore.app/api/v1/team/${t.id}/image" style="width:48px;height:48px;object-fit:contain;">
                    <h1 style="margin:0;">${t.name}</h1>
                </div>
                <div class="section-card-body">
                    <h3>Squad</h3>
                    <div class="stats-summary-grid">
                        ${data.squad.map(p => `
                            <div class="stat-box" onclick="window.location.href='/player/${p.player.id}'" style="cursor:pointer;">
                                <span class="stat-label">${p.player.position}</span>
                                <span class="stat-value" style="font-size:14px;">${p.player.name}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        </div>
    `;
}

// ── Competition Page ────────────────────────────────────────────────────────

async function renderCompetition(id, sid) {
    const endpoint = sid ? `/league/${id}?season_id=${sid}` : `/league/${id}`;
    const data = await fetchData(endpoint);
    const area = document.getElementById('content-area');
    if (!data || !area) return;

    const comp = data.comp;
    const standings = data.standings_data?.standings?.[0]?.rows || [];
    
    area.innerHTML = `
        <div class="page-content">
            <div class="section-card">
                <div class="section-card-header" style="display:flex;align-items:center;gap:16px;">
                    <img src="https://api.sofascore.app/api/v1/unique-tournament/${comp.id}/image" style="width:48px;height:48px;object-fit:contain;">
                    <h1 style="margin:0;">${comp.name}</h1>
                </div>
                <div class="section-card-body">
                    <h3>Standings</h3>
                    <table class="data-table">
                        <thead><tr><th>#</th><th>Team</th><th>PL</th><th>GD</th><th>PTS</th></tr></thead>
                        <tbody>
                            ${standings.map(r => `
                                <tr onclick="window.location.href='/team/${r.team.id}'" style="cursor:pointer;">
                                    <td>${r.position}</td>
                                    <td>${r.team.name}</td>
                                    <td>${r.matches}</td>
                                    <td>${r.goalsFor - r.goalsAgainst}</td>
                                    <td><b>${r.points}</b></td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;
}

// ── Match Page ──────────────────────────────────────────────────────────────

async function renderMatch(id) {
    const data = await fetchData(`/match/${id}`);
    const area = document.getElementById('content-area');
    if (!data || !area) return;

    const ev = data.event;
    area.innerHTML = `
        <div class="page-content">
            <div class="match-card-hero" style="text-align:center;padding:40px;background:var(--bg-card);border-radius:12px;border:1px solid var(--border);">
                <div style="display:flex;justify-content:center;align-items:center;gap:40px;">
                    <div>
                        <img src="https://api.sofascore.app/api/v1/team/${ev.homeTeam.id}/image" style="width:80px;height:80px;">
                        <h3>${ev.homeTeam.name}</h3>
                    </div>
                    <div style="font-size:48px;font-weight:800;">
                        ${ev.homeScore.display ?? 0} - ${ev.awayScore.display ?? 0}
                    </div>
                    <div>
                        <img src="https://api.sofascore.app/api/v1/team/${ev.awayTeam.id}/image" style="width:80px;height:80px;">
                        <h3>${ev.awayTeam.name}</h3>
                    </div>
                </div>
                <div style="margin-top:20px;color:var(--text-muted);">${ev.status.description}</div>
            </div>
        </div>
    `;
}

// ── Search Page ─────────────────────────────────────────────────────────────

async function renderSearch(query) {
    const data = await fetchData(`/search?q=${encodeURIComponent(query)}`);
    const resultsArea = document.getElementById('search-results');
    if (!data || !resultsArea) return;

    document.getElementById('search-title').textContent = `Results for "${query}"`;
    
    let html = '';
    
    if (data.players.length > 0) {
        html += `<h3>Players</h3><div class="stats-summary-grid">`;
        html += data.players.map(p => `
            <div class="stat-box" onclick="window.location.href='/player/${p.id}'" style="cursor:pointer;">
                <span class="stat-value" style="font-size:14px;">${p.name}</span>
            </div>
        `).join('');
        html += `</div>`;
    }

    if (data.teams.length > 0) {
        html += `<h3>Teams</h3><div class="stats-summary-grid">`;
        html += data.teams.map(t => `
            <div class="stat-box" onclick="window.location.href='/team/${t.id}'" style="cursor:pointer;">
                <span class="stat-value" style="font-size:14px;">${t.name}</span>
            </div>
        `).join('');
        html += `</div>`;
    }

    if (!html) html = '<div class="empty-state">No results found</div>';
    
    resultsArea.innerHTML = html;
}
