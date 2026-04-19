"""
config.py – Football Dashboard configuration
Uses sofascore-wrapper (no API key required).
League IDs are Sofascore's uniqueTournament IDs.
"""

# ── Sofascore uniqueTournament IDs ─────────────────────────────────────────
# These are the IDs used by https://www.sofascore.com/api/v1/unique-tournament/<id>
LEAGUES = {
    17:   {"name": "Premier League",        "country": "England",       "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿"},
    8:    {"name": "La Liga",               "country": "Spain",         "flag": "🇪🇸"},
    23:   {"name": "Serie A",               "country": "Italy",         "flag": "🇮🇹"},
    35:   {"name": "Bundesliga",            "country": "Germany",       "flag": "🇩🇪"},
    34:   {"name": "Ligue 1",               "country": "France",        "flag": "🇫🇷"},
    7:    {"name": "UEFA Champions League", "country": "Europe",        "flag": "⭐"},
    679:  {"name": "UEFA Europa League",    "country": "Europe",        "flag": "🟠"},
    37:   {"name": "Eredivisie",            "country": "Netherlands",   "flag": "🇳🇱"},
    238:  {"name": "Primeira Liga",         "country": "Portugal",      "flag": "🇵🇹"},
    18:   {"name": "FA Cup",                "country": "England",       "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿"},
    29:   {"name": "Copa del Rey",          "country": "Spain",         "flag": "🇪🇸"},
    132:  {"name": "MLS",                   "country": "USA",           "flag": "🇺🇸"},
}

# Image helpers – Sofascore CDN (no auth required)
SOFASCORE_IMG = "https://api.sofascore.app/api/v1"

def team_image_url(team_id: int) -> str:
    return f"{SOFASCORE_IMG}/team/{team_id}/image"

def league_image_url(league_id: int) -> str:
    return f"{SOFASCORE_IMG}/unique-tournament/{league_id}/image"

def player_image_url(player_id: int) -> str:
    return f"{SOFASCORE_IMG}/player/{player_id}/image"

def flag_url(alpha2: str) -> str:
    if not alpha2:
        return ""
    return f"/static/img/flags/{alpha2.lower()}.svg"

# ── Status code helpers ─────────────────────────────────────────────────────
# Sofascore status.type values
STATUS_LIVE      = {"inprogress"}
STATUS_FINISHED  = {"finished"}
STATUS_SCHEDULED = {"notstarted"}

STATUS_LABELS = {
    "notstarted":  "NS",
    "inprogress":  "LIVE",
    "finished":    "FT",
    "postponed":   "PPD",
    "canceled":    "CANC",
    "interrupted": "INT",
    "suspended":   "SUSP",
    "awarded":     "AWD",
}

# ── Cache TTLs (seconds) ────────────────────────────────────────────────────
CACHE_TTL_LIVE   = 30
CACHE_TTL_TODAY  = 60
CACHE_TTL_STATIC = 300

# ── Flask config ────────────────────────────────────────────────────────────
SECRET_KEY = "dev-secret-key-change-in-production"
DEBUG      = True
