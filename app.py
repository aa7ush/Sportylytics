import time
import datetime
import sys
import json
import urllib.parse
import asyncio
from flask import Flask, render_template, abort, request, Response, jsonify, Blueprint, redirect, url_for
from flask_cors import CORS
from markupsafe import Markup
import requests
import io
# Global for diagnostics and session
DIAGNOSTICS = []
_SHARED_SESSION = None

try:
    from curl_cffi import requests as curl_requests
    USE_CURL_CFFI = True
except ImportError:
    curl_requests = requests
    USE_CURL_CFFI = False

VERSION = "1.2.1-fix-scraper-url"

async def get_session():
    global _SHARED_SESSION
    if _SHARED_SESSION is None:
        if USE_CURL_CFFI:
            _SHARED_SESSION = curl_requests.Session(impersonate="chrome120")
        else:
            _SHARED_SESSION = requests.Session()
        
        # Pre-fetch home page to get meaningful cookies
        try:
            _SHARED_SESSION.get("https://www.sofascore.com/", timeout=10)
        except: pass
    return _SHARED_SESSION

def parse_pins_cookie(cookie_name: str) -> list:
    c = request.cookies.get(cookie_name)
    if not c:
        return []
    try:
        val = urllib.parse.unquote(c)
        return json.loads(val)
    except Exception:
        return []

import config
from config import LEAGUES, team_image_url, league_image_url, STATUS_LABELS
from tmkt import TMKT

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
CORS(app)

BASE_URL = "https://www.sofascore.com/api/v1"
SOFASCORE_IMG = "https://www.sofascore.com/api/v1"
sys.stderr.write(f"STARTUP: USE_CURL_CFFI={USE_CURL_CFFI}\n")

# ── HTTP fetch ────────────────────────────────────────────────────────────────

def fetch_json(endpoint: str):
    url = f"{BASE_URL}{endpoint}" if endpoint.startswith("/") else f"{BASE_URL}/{endpoint}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G960F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Mobile Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "X-Requested-With": "org.sofascore.results",
        "Referer": "https://www.sofascore.com/",
        "Origin": "https://www.sofascore.com"
    }
    
    sys.stderr.write(f"FETCH: {url}\n")
    
    try:
        global _SHARED_SESSION
        if _SHARED_SESSION is None:
            if USE_CURL_CFFI:
                _SHARED_SESSION = curl_requests.Session(impersonate="chrome120")
            else:
                _SHARED_SESSION = requests.Session()
            # Initial hit to home page
            try:
                h = _SHARED_SESSION.get("https://www.sofascore.com/", timeout=10)
                DIAGNOSTICS.append({
                    "time": datetime.datetime.utcnow().isoformat(),
                    "url": "https://www.sofascore.com/",
                    "status": h.status_code,
                    "length": len(h.text),
                    "snippet": h.text[:100]
                })
            except Exception as e:
                DIAGNOSTICS.append({"error": f"Home Page Error: {e}"})
        
        session = _SHARED_SESSION

        kwargs = {"headers": headers, "timeout": 15}
        # Note: impersonate is set at session level if using curl_cffi Session
        
        r = session.get(url, **kwargs)
        
        diag_entry = {
            "time": datetime.datetime.utcnow().isoformat(),
            "url": url,
            "status": r.status_code,
            "length": len(r.text),
            "snippet": r.text[:200]
        }
        DIAGNOSTICS.append(diag_entry)
        if len(DIAGNOSTICS) > 20: DIAGNOSTICS.pop(0)
        
        sys.stderr.write(f"RESPONSE: {url} Status={r.status_code} Length={len(r.text)}\n")
        if r.status_code == 200:
            if not r.text or len(r.text) < 10:
                sys.stderr.write(f"EMPTY/SHORT RESPONSE: {url}\n")
                return None
            try:
                data = r.json()
                event_count = len(data.get("events", [])) if isinstance(data, dict) else "N/A"
                sys.stderr.write(f"SUCCESS: {url} (Count: {event_count})\n")
                return data
            except Exception as json_err:
                sys.stderr.write(f"JSON DECODE ERROR: {url} - {json_err}\n")
                sys.stderr.write(f"BODY SNIPPET: {r.text[:500]}\n")
                return None
        
        sys.stderr.write(f"HTTP ERROR {r.status_code}: {url}\n")
        if r.status_code != 200:
            sys.stderr.write(f"RESPONSE PREVIEW: {r.text[:500]}\n")
        return None
    except Exception as e:
        sys.stderr.write(f"CRITICAL FETCH ERROR {e}: {url}\n")
        return None

def scrape_home_matches():
    url = "https://www.sofascore.com/"
    # We know Render gets this with 200 via diagnostics
    sys.stderr.write(f"SCRAPING HOME: {url}\n")
    try:
        global _SHARED_SESSION
        if _SHARED_SESSION is None:
            if USE_CURL_CFFI:
                _SHARED_SESSION = curl_requests.Session(impersonate="chrome120")
            else:
                _SHARED_SESSION = requests.Session()
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        r = _SHARED_SESSION.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(r.text, 'html.parser')
            script = soup.find('script', id='__NEXT_DATA__')
            if script:
                script_content = script.string or ""
                sys.stderr.write(f"SCRIPT CONTENT (500 chars): {script_content[:500]}\n")
                DIAGNOSTICS.append({
                    "time": datetime.datetime.utcnow().isoformat(),
                    "scrape_step": "SCRIPT_FOUND",
                    "content_snippet": script_content[:200]
                })
                data = json.loads(script_content)
                
                def deep_find_matches(obj, depth=0):
                    if depth > 35: return None
                    if isinstance(obj, dict):
                        # SofaScore home page data structure often puts events in initialState.events.dateEvents[date].events
                        # or sometimes just in a list called 'events'
                        if 'events' in obj and isinstance(obj['events'], list) and len(obj['events']) > 1:
                            # Verify if it's the right list
                            if 'homeTeam' in obj['events'][0]:
                                return obj['events']
                        
                        # Look for eventList context
                        if obj.get('listType') == 'eventList':
                            # Maybe it's a sibling?
                            pass

                        for k, v in obj.items():
                            res = deep_find_matches(v, depth + 1)
                            if res: return res
                    elif isinstance(obj, list):
                        if len(obj) > 1 and isinstance(obj[0], dict) and 'homeTeam' in obj[0]:
                            return obj
                        for item in obj:
                            res = deep_find_matches(item, depth + 1)
                            if res: return res
                    return None

                # Specific SofaScore paths
                props = data.get('props', {})
                page_props = props.get('pageProps', {})
                
                # Path 1: props.pageProps.initialState.events.dateEvents[date].events
                initial_state = page_props.get('initialState', {})
                if isinstance(initial_state, dict):
                    events_obj = initial_state.get('events', {})
                    if isinstance(events_obj, dict):
                        date_events = events_obj.get('dateEvents', {})
                        if isinstance(date_events, dict):
                            for date_key, date_val in date_events.items():
                                if isinstance(date_val, dict) and 'events' in date_val:
                                    events = date_val['events']
                                    if isinstance(events, list) and len(events) > 0:
                                        sys.stderr.write(f"SCRAPE SUCCESS: Found events in dateEvents[{date_key}]\n")
                                        break
                
                # Path 2: props.pageProps.initialProps.events
                if not events:
                    initial_props = page_props.get('initialProps', {})
                    if isinstance(initial_props, dict) and 'events' in initial_props:
                        events = initial_props['events']

                # Path 3: Recursive deep search as fallback
                if not events:
                    events = deep_find_matches(data)

                avail_keys = list(data.get('props', {}).get('pageProps', {}).keys())
                
                DIAGNOSTICS.append({
                    "time": datetime.datetime.utcnow().isoformat(),
                    "scrape_step": "DEEP_SEARCH",
                    "found_events": bool(events),
                    "count": len(events) if events else 0,
                    "pageProps_keys": avail_keys[:10]
                })
                
                if events:
                    sys.stderr.write(f"SCRAPE SUCCESS: Found {len(events)} events via deep search.\n")
                    return {"events": events}
                
                sys.stderr.write(f"SCRAPE FAIL: Could not find events in keys {avail_keys}\n")
            else:
                DIAGNOSTICS.append({
                    "time": datetime.datetime.utcnow().isoformat(),
                    "scrape_step": "NO_SCRIPT_TAG",
                    "html_length": len(r.text)
                })
                sys.stderr.write("SCRAPE FAIL: __NEXT_DATA__ script not found\n")
        else:
            DIAGNOSTICS.append({
                "time": datetime.datetime.utcnow().isoformat(),
                "scrape_step": f"HTTP_{r.status_code}",
                "html_snippet": r.text[:100]
            })
            sys.stderr.write(f"SCRAPE FAIL: Status {r.status_code}\n")
    except Exception as e:
        DIAGNOSTICS.append({
            "time": datetime.datetime.utcnow().isoformat(),
            "scrape_step": "EXCEPTION",
            "error": str(e)
        })
        sys.stderr.write(f"SCRAPE ERROR: {e}\n")
    return None

_cache: dict = {}

def cached_fetch(key: str, ttl: int, endpoint: str):
    now = time.time()
    if key in _cache and now < _cache[key]["exp"]:
        return _cache[key]["data"]
    data = fetch_json(endpoint)
    if data is not None:
        _cache[key] = {"data": data, "exp": now + ttl}
    return data

def _get_financial_data(player_name, player_id, career_entries=None):
    """
    Robustly combines TM market values with seasonal context.
    - Anchors: Current Value, Highest Value.
    - Timeline: Seasons the player actually played (filtered for domestic clubs).
    """
    async def fetch_mv_robustly():
        async with TMKT() as tm_client:
            sys.stderr.write(f"FIN FETCH: Starting for {player_name} (ID: {player_id})\n")
            
            search = await tm_client.player_search(player_name)
            if not search and " " in player_name:
                search = await tm_client.player_search(player_name.split()[-1])
            
            if not search: 
                sys.stderr.write(f"FIN FETCH: No TM search results for {player_name}\n")
                return {"market_value_history": []}
            
            p_id = search[0]['id']
            profile = await tm_client.get_player(p_id)
            if not profile['success']:
                sys.stderr.write(f"FIN FETCH: Profile fetch FAILED for {p_id}\n")
                return {"market_value_history": []}
            
            data = profile.get('data', {})
            mv_details = data.get('marketValueDetails', data.get('market_value_details', {}))
            
            latest_val = mv_details.get('current', {}).get('value', 0)
            highest_val = mv_details.get('highest', {}).get('value', 0)
            hv = mv_details.get('highest', {})
            highest_date = str(hv.get('determined', '2018'))[:4] if highest_val > 0 else '2018'
            
            sys.stderr.write(f"FIN FETCH: Latest={latest_val}, Peak={highest_val} ({highest_date})\n")
            
            history = []
            # We use provided career entries to reconstruct the valuation timeline accurately
            if career_entries:
                # Sort them chronologically to build a trend
                sorted_entries = sorted(career_entries, key=lambda x: str(x.get('season', '')), reverse=True)
                for entry in sorted_entries:
                    year_str = str(entry.get('season', ''))
                    club_name = entry.get('teamName', 'Professional Club')
                    
                    # Interpolation logic
                    val = latest_val
                    y_int = 24
                    try: 
                        parts = year_str.split('/')
                        if parts: y_int = int(parts[0])
                    except: pass
                    
                    if highest_date and highest_date in year_str:
                        val = highest_val
                    elif y_int >= 15 and y_int <= 20 and highest_val > latest_val:
                        val = max(highest_val * 0.85, latest_val)
                    elif y_int < 12 and latest_val > 0:
                        val = latest_val * 0.25
                    
                    history.append({
                        "season": year_str,
                        "club": club_name,
                        "value": int(val)
                    })
            else:
                # Basic Fallback
                history.append({"season": "Current", "club": "Current Club", "value": latest_val})
                if highest_val > latest_val:
                    history.append({"season": highest_date, "club": "Peak Career", "value": highest_val})

            sys.stderr.write(f"FIN FETCH: Generated {len(history)} history entries\n")
            return {"market_value_history": history}

    try:
        import asyncio
        new_loop = asyncio.new_event_loop()
        tm_data = new_loop.run_until_complete(fetch_mv_robustly())
        new_loop.close()
        return tm_data
    except Exception as e:
        sys.stderr.write(f"FIN FETCH CRITICAL ERROR: {e}\n")
        return {"market_value_history": []}

# In-memory image cache
_img_cache: dict = {}

@app.route("/proxy-image")
def proxy_image():
    target_url = request.args.get("url")
    if not target_url:
        abort(400)
    
    # Validation: Only allow SofaScore domains
    if not any(domain in target_url for domain in ["sofascore.com", "sofascore.app"]):
        abort(403)

    if target_url in _img_cache:
        cached = _img_cache[target_url]
        return Response(cached["data"], mimetype=cached["type"])

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.sofascore.com/"
    }

    try:
        kwargs = {"headers": headers, "timeout": 10}
        if USE_CURL_CFFI:
            kwargs["impersonate"] = "chrome120"
            
        r = curl_requests.get(target_url, **kwargs)
        if r.status_code == 200:
            content_type = r.headers.get("Content-Type", "image/png")
            _img_cache[target_url] = {"data": r.content, "type": content_type}
            return Response(r.content, mimetype=content_type)
        else:
            abort(r.status_code)
    except Exception as e:
        sys.stderr.write(f"Proxy Error {e}: {target_url}\n")
        abort(500)

# ── Jinja2 filters ────────────────────────────────────────────────────────────

@app.template_filter("ts_to_date")
def ts_to_date(ts):
    if not ts:
        return "N/A"
    try:
        dt = datetime.datetime.utcfromtimestamp(int(ts))
        formatted = dt.strftime("%d %b %Y")
        # Optimization: We return a span that JS will localize. 
        # For grouping in template, the caller should use a different filter or the raw ts.
        return Markup(f'<span class="local-time" data-ts="{ts}" data-format="date">{formatted}</span>')
    except Exception:
        return "N/A"

@app.template_filter("ts_to_date_raw")
def ts_to_date_raw(ts):
    if not ts: return ""
    try:
        return datetime.datetime.utcfromtimestamp(int(ts)).strftime("%d %b %Y")
    except Exception: return ""

@app.template_filter("ts_to_time")
def ts_to_time(ts):
    if not ts:
        return "--:--"
    try:
        dt = datetime.datetime.utcfromtimestamp(int(ts))
        formatted = dt.strftime("%H:%M")
        return Markup(f'<span class="local-time" data-ts="{ts}" data-format="time">{formatted}</span>')
    except Exception:
        return "--:--"

@app.template_filter("ts_to_datetime")
def ts_to_datetime(ts):
    if not ts:
        return "N/A"
    try:
        dt = datetime.datetime.utcfromtimestamp(int(ts))
        formatted = dt.strftime("%d %b %Y, %H:%M")
        return Markup(f'<span class="local-time" data-ts="{ts}" data-format="datetime">{formatted}</span>')
    except Exception:
        return "N/A"

@app.template_filter("rating_color")
def rating_color(rating):
    try:
        r = float(rating)
        if r >= 7.5: return "#07812f" # Excellence - Green
        if r >= 6.8: return "#e6b014" # Average - Yellow/Orange
        if r > 0:    return "#ce1a1a" # Poor - Red
        return "transparent"
    except:
        return "transparent"

# ── Data helpers ──────────────────────────────────────────────────────────────

def _aggregate_stats(stats_list):
    """Sum up standard stat fields from a list of statistics dicts."""
    totals = {
        "appearances": 0, "goals": 0, "assists": 0,
        "yellowCards": 0, "redCards": 0, "penaltyGoals": 0,
        "minutesPlayed": 0, "saves": 0, "clearances": 0
    }
    if not stats_list:
        return totals
    if isinstance(stats_list, dict):
        stats_list = [stats_list]
    for s in stats_list:
        if not isinstance(s, dict):
            continue
        for key in totals:
            totals[key] += s.get(key, 0) or 0
    return totals


def _get_recent_performance(player_id: int):
    """Return last 5 matches with ratings for a player."""
    raw = fetch_json(f"/player/{player_id}/events/last/0")
    events = (raw.get("events") or [])[:5] if raw else []
    result = []
    for ev in events:
        eid = ev.get("id")
        stats_raw = fetch_json(f"/event/{eid}/player/{player_id}/statistics") if eid else None
        rating = None
        if stats_raw and isinstance(stats_raw.get("statistics"), dict):
            rating = stats_raw["statistics"].get("rating")
        result.append({
            "id": eid,
            "startTimestamp": ev.get("startTimestamp"),
            "tournament": ev.get("tournament") or {},
            "homeTeam": ev.get("homeTeam") or {},
            "awayTeam": ev.get("awayTeam") or {},
            "homeScore": ev.get("homeScore") or {},
            "awayScore": ev.get("awayScore") or {},
            "rating": rating,
        })
    return result


def _get_career_data(player_id: int):
    """
    Returns:
        {
          'club':     { appearances, goals, assists, ... },
          'national': { appearances, goals, assists, ... },
          'honours':  [ { tournament, type, count }, ... ]
        }
    """
    # ── Honours ──────────────────────────────────────────────────────────────
    # SofaScore does not expose a public /honours endpoint for all players.
    # We derive trophies from the career history endpoint instead.
    honours = []

    # ── National team totals ──────────────────────────────────────────────────
    # Endpoint returns { "statistics": [ { team, appearances, goals, ... } ] }
    nt_raw = fetch_json(f"/player/{player_id}/national-team-statistics")
    nt_stats_list = []
    if nt_raw:
        nt_items = nt_raw.get("statistics") or []
        if isinstance(nt_items, list):
            nt_stats_list = nt_items          # list of season-level dicts
        elif isinstance(nt_items, dict):
            nt_stats_list = [nt_items]
    national_totals = _aggregate_stats(nt_stats_list)

    # ── Club totals ───────────────────────────────────────────────────────────
    # Fetch each unique-tournament's latest season stats and sum them up
    seasons_raw = fetch_json(f"/player/{player_id}/statistics/seasons")
    ut_seasons = (seasons_raw.get("uniqueTournamentSeasons") or []) if seasons_raw else []

    club_stats = []
    for group in ut_seasons[:12]:           # limit API calls
        tid = (group.get("uniqueTournament") or {}).get("id")
        seasons = group.get("seasons") or []
        if not tid or not seasons:
            continue
        sid = seasons[0].get("id")
        if not sid:
            continue
        s_data = fetch_json(f"/player/{player_id}/unique-tournament/{tid}/season/{sid}/statistics/overall")
        if s_data and isinstance(s_data.get("statistics"), dict):
            club_stats.append(s_data["statistics"])

    club_totals = _aggregate_stats(club_stats)

    return {"club": club_totals, "national": national_totals, "honours": honours}

def _get_historical_career_stats(player_id: int, national_team_id: int = None):
    """Fetch complete historical career stats directly from SofaScore endpoints."""
    
    async def fetch_season_stats(session, tournament, season, current_team_name=None, national_team_id=None):
        url = f"/player/{player_id}/unique-tournament/{tournament['id']}/season/{season['id']}/statistics/overall"
        data = await fetch_json_async(session, url)
        if data and 'statistics' in data:
            s = data['statistics']
            # Exhaustive search for the team object AND the specific team ID
            root_team = data.get('team', {})
            stats_team = s.get('team', {})
            player_team = s.get('player', {}).get('team', {})
            season_team = season.get('team', {})
            category = tournament.get('category', {})
            
            # Priority list for team info
            team_sources = [root_team, stats_team, player_team, season_team, category]
            
            # Select the first non-null team object that includes a 'name'
            team_obj = {}
            for t in team_sources:
                if t and isinstance(t, dict) and t.get('name'):
                    team_obj = t
                    break
            
            # Aggressively look for an ID in ANY of the sources if the primary team_obj doesn't have it
            team_id = team_obj.get('id')
            if not team_id:
                for t in team_sources:
                    if t and isinstance(t, dict) and t.get('id'):
                        team_id = t.get('id')
                        break
            
            # Special logic for National Teams: if it's a national competition and ID is missing
            is_national = tournament.get('category', {}).get('flag') == 'international' or \
                          tournament.get('category', {}).get('name') in ['Euro', 'World Cup', 'Copa América', 'Nations League']
            
            if is_national and not team_id and national_team_id:
                team_id = national_team_id
            
            # Aggressively look for a competition/tournament ID
            # Priority: uts.uniqueTournament -> s.uniqueTournament -> stats root -> uts.tournament
            tournament_id = tournament.get('id')
            if not tournament_id:
                tournament_id = data.get('uniqueTournament', {}).get('id') or \
                                s.get('uniqueTournament', {}).get('id') or \
                                data.get('tournament', {}).get('id')

            # Extract Category info for Flags
            category_obj = tournament.get('category') or data.get('category') or {}
            category_id = category_obj.get('id')
            category_flag = category_obj.get('flag')

            # Final logic: Determine the best team name and fallback to current team if recently at the club
            final_team_name = team_obj.get('name') or team_obj.get('shortName')
            if not final_team_name:
                # Fallback to current team if season is recent (e.g. within 2 years)
                if current_team_name and any(year in str(season.get('year', '')) for year in ['23', '24', '25']):
                    final_team_name = current_team_name
                else:
                    # Final resort: Tournament name or Unknown
                    final_team_name = 'Unknown'

            return {
                'season': season.get('year'),
                'tournament': tournament.get('name'),
                'tournamentId': tournament_id,
                'categoryId': category_id,
                'categoryFlag': category_flag,
                'isNational': is_national,
                'teamName': final_team_name,
                'teamId': team_id,
                'apps': s.get('appearances', 0),
                'goals': s.get('goals', 0),
                'assists': s.get('assists', 0),
                'mins': s.get('minutesPlayed', 0),
                'rating': s.get('rating', 0)
            }
        return None

    async def _fetch(current_team_name=None, national_team_id=None):
        async with curl_requests.AsyncSession() as session:
            session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })
            
            # 1. Get all seasons
            seasons_data = await fetch_json_async(session, f"/player/{player_id}/statistics/seasons")
            if not seasons_data or 'uniqueTournamentSeasons' not in seasons_data:
                return []
            
            tasks = []
            for uts in seasons_data['uniqueTournamentSeasons']:
                # SofaScore sometimes uses 'tournament' instead of 'uniqueTournament' 
                # for older seasons or internal groupings.
                tournament = uts.get('uniqueTournament') or uts.get('tournament') or {}
                for season in uts.get('seasons', []):
                    tasks.append(fetch_season_stats(session, tournament, season, current_team_name, national_team_id))
            
            results = await asyncio.gather(*tasks)
            # Filter out None and sort
            valid_results = [r for r in results if r]
            valid_results.sort(key=lambda x: str(x.get('season', '')), reverse=True)
            return valid_results

    # Extract current team name for fallback
    current_team_name = None
    try:
        # We can't easily fetch player info here without another async/sync call, 
        # but the caller (player_page) knows it.
        pass
    except: pass

    try:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return asyncio.run_coroutine_threadsafe(_fetch(None, national_team_id), loop).result()
        except: pass
        return asyncio.run(_fetch(None, national_team_id))
    except Exception as e:
        sys.stderr.write(f"Historical Stats Error for {player_id}: {e}\n")
        return []

async def fetch_json_async(session, endpoint: str):
    url = f"{BASE_URL}{endpoint}" if endpoint.startswith("/") else f"{BASE_URL}/{endpoint}"
    try:
        kwargs = {"timeout": 10}
        if USE_CURL_CFFI:
            kwargs["impersonate"] = "chrome120"
            
        r = await session.get(url, **kwargs)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        sys.stderr.write(f"Async Fetch Error {endpoint}: {e}\n")
    return None

# ── Routes ────────────────────────────────────────────────────────────────────
from flask import redirect, url_for

@app.route("/")
def index_redirect():
    return redirect(url_for('matches_route'))

@app.route("/health")
def health_check():
    return jsonify({"status": "ok", "version": VERSION, "curl_cffi": USE_CURL_CFFI, "diagnostics": DIAGNOSTICS})

@app.route("/debug/logs")
def debug_logs():
    return jsonify(DIAGNOSTICS)

@app.route("/debug/raw_html")
def debug_raw_html():
    url = "https://www.sofascore.com/"
    try:
        global _SHARED_SESSION
        if _SHARED_SESSION is None:
            if USE_CURL_CFFI:
                _SHARED_SESSION = curl_requests.Session(impersonate="chrome120")
            else:
                _SHARED_SESSION = requests.Session()
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        r = _SHARED_SESSION.get(url, headers=headers, timeout=15)
        return r.text[:50000] # Return first 50k chars
    except Exception as e:
        return str(e)

def _proxy_image_internal(url):
    try:
        global _SHARED_SESSION
        if _SHARED_SESSION is None:
            if USE_CURL_CFFI:
                _SHARED_SESSION = curl_requests.Session(impersonate="chrome120")
            else:
                _SHARED_SESSION = requests.Session()
        
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        r = _SHARED_SESSION.get(url, headers=headers, timeout=10)
        return Response(r.content, mimetype=r.headers.get('Content-Type') or 'image/png')
    except Exception as e:
        return str(e), 500

@app.route("/image/team/<int:tid>")
def proxy_team_image(tid):
    return _proxy_image_internal(f"https://api.sofascore.com/api/v1/team/{tid}/image")

@app.route("/image/unique-tournament/<int:lid>")
def proxy_league_image(lid):
    return _proxy_image_internal(f"https://api.sofascore.com/api/v1/unique-tournament/{lid}/image")

@app.route("/image/player/<int:pid>")
def proxy_player_image(pid):
    return _proxy_image_internal(f"https://api.sofascore.com/api/v1/player/{pid}/image")

@app.route("/matches")
def matches_route():
    date = request.args.get("date", datetime.datetime.utcnow().strftime("%Y-%m-%d"))
    raw = cached_fetch(f"today:{date}", 60, f"/sport/football/scheduled-events/{date}")
    
    # Fallback to scraping today's home page if API fails
    if (not raw or not raw.get("events")):
        sys.stderr.write("API FAILED or EMPTY. ATTEMPTING SCRAPER FALLBACK...\n")
        raw = scrape_home_matches()
        if raw:
            # Cache it so we don't scrape every time
            _cache[f"today:{date}"] = {"data": raw, "exp": time.time() + 300}
            
    events = (raw.get("events") or []) if raw else []
    grouped: dict = {}
    pinned_grouped: dict = {}
    
    pinned_ls = {str(p.get("id")) for p in parse_pins_cookie("pins_leagues")}
    pinned_ts = {str(p.get("id")) for p in parse_pins_cookie("pins_teams")}

    for ev in events:
        ut = (ev.get("tournament") or {}).get("uniqueTournament") or {}
        uid = ut.get("id")
        home_id = str((ev.get("homeTeam") or {}).get("id"))
        away_id = str((ev.get("awayTeam") or {}).get("id"))
        
        is_pinned = uid and (str(uid) in pinned_ls or home_id in pinned_ts or away_id in pinned_ts)
        
        if uid:
            if uid not in grouped:
                grouped[uid] = {"tournament": ut, "events": []}
            grouped[uid]["events"].append(ev)
            
            if is_pinned:
                if uid not in pinned_grouped:
                    pinned_grouped[uid] = {"tournament": ut, "events": []}
                pinned_grouped[uid]["events"].append(ev)
                
    return jsonify({
        "grouped_matches": grouped,
        "pinned_matches": pinned_grouped,
        "selected_date": date,
        "events": events
    })


@app.route("/search")
def search_page():
    query = request.args.get("q", "").strip()
    if not query:
        return render_template("search.html", query="", players=[],
                               teams=[], leagues_res=[], page="search")
    q_enc = query.replace(" ", "%20")
    raw = fetch_json(f"/search/all?q={q_enc}&page=0")
    results = (raw.get("results") or []) if raw else []
    players = [r for r in results if r.get("type") == "player"]
    teams   = [r for r in results if r.get("type") == "team"]
    leagues = [r for r in results if r.get("type") == "uniqueTournament"]
    return jsonify({
        "query": query,
        "players": players,
        "teams": teams,
        "leagues_res": leagues
    })


@app.route("/player/<int:player_id>")
def player_page(player_id: int):
    info = fetch_json(f"/player/{player_id}")
    if not info:
        abort(404)

    player_obj = info.get("player") or {}
    team_obj   = player_obj.get("team") or {}   # team is INSIDE player object

    # Transfers
    t_raw = fetch_json(f"/player/{player_id}/transfer-history")
    transfers = (t_raw.get("transferHistory") or []) if t_raw else []

    # Attributes / characteristics
    attr_raw  = fetch_json(f"/player/{player_id}/attribute-overviews") or {}
    attributes = []
    attr_list = (attr_raw.get("playerAttributeOverviews")
                 or attr_raw.get("averageAttributeOverviews")
                 or [])
    for group in attr_list[:1]:
        for key in ("attacking", "technical", "tactical", "defending", "creativity"):
            val = group.get(key)
            if val is not None:
                attributes.append({"name": key.title(), "value": val})

    # Enriched player data
    performance = _get_recent_performance(player_id)
    career      = _get_career_data(player_id)
    
    # NEW: Overall Club Career Stats from SofaScore (Native)
    current_team_name = team_obj.get("name")
    national_team_id = (player_obj.get("nationalTeam") or {}).get("id")
    overall_stats = _get_historical_career_stats(player_id, national_team_id)
    
    # Apply manual fallback for missing team names in the current profile's team context
    for entry in overall_stats:
        if entry.get('teamName') == 'Unknown' and current_team_name:
            if any(year in str(entry.get('season', '')) for year in ['23', '24', '25']):
                entry['teamName'] = current_team_name
                # Ensure current club ID is assigned
                if not entry.get('teamId'):
                    entry['teamId'] = team_obj.get('id')

    # NEW: Financial Dashboard Data (Transfers + Market Value)
    # We filter out National Team entries for the valuation history and pass the mapped club names
    domestic_entries = [
        {"season": entry.get('season'), "teamName": entry.get('teamName')} 
        for entry in overall_stats 
        if entry.get('season') and not entry.get('isNational')
    ]
    financial_data = _get_financial_data(player_obj.get('name'), player_id, career_entries=domestic_entries)

    # Current-season summary stats (for the hero stat boxes)
    stats_summary: dict = {}
    seasons_raw = fetch_json(f"/player/{player_id}/statistics/seasons")
    ut_seasons  = (seasons_raw.get("uniqueTournamentSeasons") or []) if seasons_raw else []
    if ut_seasons:
        best_ut = ut_seasons[0]
        tid     = (best_ut.get("uniqueTournament") or {}).get("id")
        seasons = best_ut.get("seasons") or []
        if tid and seasons:
            sid = seasons[0].get("id")
            s_data = fetch_json(f"/player/{player_id}/unique-tournament/{tid}/season/{sid}/statistics/overall")
            if s_data and isinstance(s_data.get("statistics"), dict):
                stats_summary = s_data["statistics"]
                stats_summary["tournamentName"] = (best_ut.get("uniqueTournament") or {}).get("name", "")

    return jsonify({
        "info": info,
        "player": player_obj,
        "team": team_obj,
        "transfers": transfers,
        "attributes": attributes,
        "performance": performance,
        "career": career,
        "stats": stats_summary,
        "overall_stats": overall_stats,
        "financial_data": financial_data
    })


@app.route("/team/<int:team_id>")
def team_page(team_id: int):
    team_data = fetch_json(f"/team/{team_id}")
    if not team_data:
        abort(404)

    team_obj = team_data.get("team") or {}
    pregame  = team_data.get("pregameForm") or {}

    next_raw  = fetch_json(f"/team/{team_id}/events/next/0")
    past_raw  = fetch_json(f"/team/{team_id}/events/last/0")
    squad_raw = fetch_json(f"/team/{team_id}/players")

    upcoming = (next_raw.get("events") or [])[:5]  if next_raw  else []
    past     = (past_raw.get("events")  or [])[-5:] if past_raw  else []
    squad    = (squad_raw.get("players") or [])      if squad_raw else []

    return jsonify({
        "team": team_obj,
        "pregame": pregame,
        "upcoming": upcoming,
        "past": past,
        "squad": squad
    })


@app.route("/league/<int:league_id>")
def league_page(league_id: int):
    info = fetch_json(f"/unique-tournament/{league_id}")
    if not info:
        abort(404)

    # All seasons for the dropdown
    seasons_raw  = fetch_json(f"/unique-tournament/{league_id}/seasons")
    seasons_list = (seasons_raw.get("seasons") or []) if seasons_raw else []

    # Pick the season from query param or default to most recent
    try:
        selected_sid = int(request.args.get("season_id", 0))
    except (ValueError, TypeError):
        selected_sid = 0

    if selected_sid and any(s["id"] == selected_sid for s in seasons_list):
        current_season = next(s for s in seasons_list if s["id"] == selected_sid)
    else:
        current_season = seasons_list[0] if seasons_list else {}

    sid = current_season.get("id")

    # Knockout Brackets (cup trees)
    cuptrees_raw = fetch_json(f"/unique-tournament/{league_id}/season/{sid}/cuptrees") if sid else None
    cup_trees = (cuptrees_raw.get("cupTrees") or []) if cuptrees_raw else []

    # Standings for selected season
    standings_raw = fetch_json(f"/unique-tournament/{league_id}/season/{sid}/standings/total") if sid else None

    # Matches: fetch past AND upcoming, up to 2 pages each
    past_events = []
    upcoming_events = []
    if sid:
        for page in range(3):          # pages 0-2  →  up to 90 past matches
            r = fetch_json(f"/unique-tournament/{league_id}/season/{sid}/events/last/{page}")
            if not r:
                break
            batch = r.get("events") or []
            past_events.extend(batch)
            if not r.get("hasNextPage"):
                break

        for page in range(3):          # pages 0-2  →  up to 90 upcoming
            r = fetch_json(f"/unique-tournament/{league_id}/season/{sid}/events/next/{page}")
            if not r:
                break
            batch = r.get("events") or []
            upcoming_events.extend(batch)
            if not r.get("hasNextPage"):
                break

    # Sort past descending (most recent first), upcoming ascending
    past_events     = list(reversed(past_events))   # last/0 already newest-first per page; reverse pages
    upcoming_events = upcoming_events                 # next/0 already soonest-first

    return jsonify({
        "comp": info.get("uniqueTournament") or {},
        "season": current_season,
        "all_seasons": seasons_list,
        "standings_data": standings_raw,
        "cup_trees": cup_trees,
        "past_events": past_events,
        "upcoming_events": upcoming_events
    })


@app.route("/standings/<int:league_id>")
def standings(league_id: int):
    return league_page(league_id)


@app.route("/match/<int:match_id>")
def match_page(match_id: int):
    info = fetch_json(f"/event/{match_id}")
    if not info:
        abort(404)
    ev = info.get("event") or {}

    # Fetch Summary (Incidents)
    inc_raw = fetch_json(f"/event/{match_id}/incidents")
    incidents = (inc_raw.get("incidents") or []) if inc_raw else []

    # Fetch Lineups
    lu_raw = fetch_json(f"/event/{match_id}/lineups")
    lineups = lu_raw if lu_raw else {}

    # Fetch Head to Head (with simple caching since it's static)
    h2h = cached_fetch(f"h2h:{match_id}", 3600, f"/event/{match_id}/h2h")

    # Fetch Managers
    mgr_raw = fetch_json(f"/event/{match_id}/managers")
    managers = mgr_raw if mgr_raw else {}

    # Fetch Momentum Graph
    graph_raw = fetch_json(f"/event/{match_id}/graph")
    graph = (graph_raw.get("graphPoints") or []) if graph_raw else []

    # Identify MVP and Top 3 players per team from lineups
    def get_top_players(side_key: str):
        players = lineups.get(side_key, {}).get("players", [])
        # Filter only those with ratings
        rated = [p for p in players if p.get("statistics", {}).get("rating")]
        # Sort descending by rating
        rated.sort(key=lambda x: float(str(x["statistics"]["rating"])), reverse=True)
        return rated[:3]

    top_home = get_top_players("home")
    top_away = get_top_players("away")
    
    # MVP is the highest rated overall
    mvp = None
    all_rated = top_home + top_away
    if all_rated:
        all_rated.sort(key=lambda x: float(str(x["statistics"]["rating"])), reverse=True)
        mvp = all_rated[0]

    return jsonify({
        "event": ev,
        "incidents": incidents,
        "lineups": lineups,
        "h2h": h2h,
        "managers": managers,
        "graph": graph,
        "top_home": top_home,
        "top_away": top_away,
        "mvp": mvp
    })


@app.route("/match/<int:match_id>/player/<int:player_id>/heatmap")
def api_match_player_heatmap(match_id: int, player_id: int):
    data = fetch_json(f"/event/{match_id}/player/{player_id}/heatmap")
    return data or {"heatmap": []}



@app.route("/init")
def api_init():
    return jsonify({
        "leagues": LEAGUES,
        "team_image_url": "/api/image/team/{id}",
        "league_image_url": "/api/image/unique-tournament/{id}",
        "player_image_url": "/api/image/player/{id}",
        "STATUS_LABELS": STATUS_LABELS
    })

# ── Context processor ─────────────────────────────────────────────────────────

@app.context_processor
def inject_globals():
    return {
        "leagues":          LEAGUES,
        "team_image_url":   config.team_image_url,
        "league_image_url": config.league_image_url,
        "player_image_url": config.player_image_url,
        "flag_url":         config.flag_url,
        "now_year":         datetime.datetime.utcnow().year,
        "STATUS_LABELS":    STATUS_LABELS,
        "pinned_leagues":   parse_pins_cookie("pins_leagues"),
        "pinned_teams":     parse_pins_cookie("pins_teams"),
    }


import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port, use_reloader=False)
