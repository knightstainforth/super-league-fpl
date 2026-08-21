#!/usr/bin/env python3
"""
Knights Table Super League — standings page generator.

Pulls the league roster and every manager's gameweek history straight from the
public Fantasy Premier League API, then renders the static standings page to
index.html.

Runs on GitHub Actions (see .github/workflows/refresh.yml). No API key, no
login, no secrets needed — the FPL endpoints used here are all public, and
server-side requests are not subject to the browser CORS restriction that
blocks doing this from a visitor's browser.

Usage:
    python3 fetch_and_render.py [output_path]
"""

import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

from render_frontpage import render_frontpage_html

LEAGUE_ID = 1369159
BASE = "https://fantasy.premierleague.com/api"
UA = "Mozilla/5.0 (compatible; KnightsTableSuperLeague/1.0; +https://github.com/)"
OUT = sys.argv[1] if len(sys.argv) > 1 else "index.html"


def get_json(url, attempts=4):
    """GET a URL and parse JSON, with a simple backoff retry."""
    last = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            last = e
            if i < attempts - 1:
                time.sleep(2 ** i)
    raise SystemExit(f"FATAL: could not fetch {url} after {attempts} attempts: {last}")


def london_label(now=None):
    """'Tuesday 25 Aug 2026' in UK local time.

    UK is UTC+1 from the last Sunday in March to the last Sunday in October,
    otherwise UTC. Computed without external tz libraries so the runner needs
    no extra dependencies.
    """
    now = now or datetime.now(timezone.utc)

    def last_sunday(year, month):
        d = datetime(year, month, 31, 1, 0, tzinfo=timezone.utc)
        while d.month != month:
            d -= timedelta(days=1)
        while d.weekday() != 6:  # Sunday
            d -= timedelta(days=1)
        return d

    bst_start = last_sunday(now.year, 3)
    bst_end = last_sunday(now.year, 10)
    local = now + timedelta(hours=1) if bst_start <= now < bst_end else now
    return local.strftime("%A %-d %b %Y") if sys.platform != "win32" else local.strftime("%A %d %b %Y")


def build_entrants():
    """Return (entrants, notes). entrants is the shape render_frontpage_html wants."""
    notes = []
    standings = get_json(f"{BASE}/leagues-classic/{LEAGUE_ID}/standings/")
    league_name = standings.get("league", {}).get("name", "?")
    print(f"league: {league_name} (id {LEAGUE_ID})")

    roster = []
    page = standings
    while True:
        results = page.get("standings", {}).get("results", []) or []
        for r in results:
            roster.append({
                "manager_name": (r.get("player_name") or "").strip(),
                "team_name": (r.get("entry_name") or "").strip(),
                "entry_id": r["entry"],
                "standings_total": r.get("total"),
            })
        if not page.get("standings", {}).get("has_next"):
            break
        nxt = page["standings"].get("page", 1) + 1
        page = get_json(f"{BASE}/leagues-classic/{LEAGUE_ID}/standings/?page_standings={nxt}")

    if roster:
        print(f"roster from standings: {len(roster)} entrants")
    else:
        # Pre-season: nobody has a score yet, so standings.results is empty and
        # the only place the roster appears is new_entries.
        print("standings empty (pre-season) - falling back to new_entries")
        page = standings
        while True:
            for r in page.get("new_entries", {}).get("results", []) or []:
                first = (r.get("player_first_name") or "").strip()
                lastn = (r.get("player_last_name") or "").strip()
                roster.append({
                    "manager_name": f"{first} {lastn}".strip(),
                    "team_name": (r.get("entry_name") or "").strip(),
                    "entry_id": r["entry"],
                    "standings_total": None,
                })
            if not page.get("new_entries", {}).get("has_next"):
                break
            nxt = page["new_entries"].get("page", 1) + 1
            page = get_json(f"{BASE}/leagues-classic/{LEAGUE_ID}/standings/?page_new_entries={nxt}")
        notes.append(f"pre-season: roster taken from new_entries ({len(roster)} entrants)")

    if not roster:
        raise SystemExit("FATAL: no entrants found in either standings or new_entries - aborting "
                         "rather than publishing an empty page.")

    # Tidy obviously-lowercase names (the API stores whatever the user typed).
    for e in roster:
        if e["manager_name"] and e["manager_name"] == e["manager_name"].lower():
            e["manager_name"] = e["manager_name"].title()

    # Per-manager gameweek history
    for e in roster:
        hist = get_json(f"{BASE}/entry/{e['entry_id']}/history/")
        current = hist.get("current", []) or []
        scores = {}
        for row in current:
            ev, pts = row.get("event"), row.get("points")
            if isinstance(ev, int) and isinstance(pts, int) and 1 <= ev <= 38:
                scores[ev] = pts
        e["scores"] = scores

        # Cross-check: our summed per-GW points vs the API's own totals.
        summed = sum(scores.values())
        api_total = current[-1].get("total_points") if current else 0
        if current and summed != api_total:
            notes.append(f"MISMATCH {e['manager_name']}: summed GW points {summed} != "
                         f"history total_points {api_total}")
        if e["standings_total"] is not None and summed != e["standings_total"]:
            notes.append(f"MISMATCH {e['manager_name']}: summed GW points {summed} != "
                         f"standings total {e['standings_total']}")
        print(f"  {e['manager_name']:<22} {len(scores):>2} GWs, {summed} pts")
        time.sleep(0.3)  # be polite to the API

    for e in roster:
        e.pop("standings_total", None)
    return roster, notes


def main():
    entrants, notes = build_entrants()
    label = london_label()
    html = render_frontpage_html(entrants, generated_at_label=label)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\nwrote {OUT} ({len(html)} bytes), {len(entrants)} entrants, label '{label}'")
    if notes:
        print("\nNOTES / WARNINGS:")
        for n in notes:
            print(f"  - {n}")


if __name__ == "__main__":
    main()
