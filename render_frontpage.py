#!/usr/bin/env python3
"""
Render a static, self-contained "front page" standings HTML for the
Knights Table Super League tracker. No live fetch, no dependencies beyond
one Google Fonts link — values are baked in at generation time. Regenerated
weekly alongside the workbook and dropped into the Dropbox folder.
 
FPL-branded look (purple / green / cyan) with three tabs (Overall, First
Half, Second Half) and a prize-pot reference section at the bottom.
 
Usage as a library: render_frontpage_html(entrants, generated_at_label="")
entrants: same shape used by build.py's build(entrants=...) param:
    [{"manager_name": "...", "team_name": "...", "entry_id": 123,
      "scores": {1: 62, 2: 55, ...}}, ...]   # scores keyed by GW number, 1-38
"""
 
H1_END = 19
H2_START = 20
N_GW = 38
 
 
def fmt_money(n):
    s = f"{n:.2f}"
    if s.endswith(".00"):
        s = s[:-3]
    return "£" + s
 
 
def _rank_badge(rank):
    if rank <= 3:
        return f'<span class="fplst-rankbadge fplst-rank-{rank}">{rank}</span>'
    return f'<span class="fplst-rankbadge">{rank}</span>'
 
 
def _standings_rows(sorted_list, score_key, gw_col_label="GW"):
    rows = ""
    for i, e in enumerate(sorted_list):
        rank = i + 1
        gw_display = e.get("_gw_display", "—")
        rows += (f'<tr><td>{_rank_badge(rank)}</td><td>{e["manager_name"]}</td>'
                 f'<td class="fplst-team">{e["team_name"]}</td><td>{gw_display}</td>'
                 f'<td>{e[score_key]}</td></tr>')
    return rows
 
 
def _half_stats(entrants, gw_start, gw_end):
    """Compute half-season standings + the sub-prize winners.
 
    NOTE (2026-08-21): the "closest to average" sub-prize used to compare
    each entrant's score IN THE HALF'S WORST GAMEWEEK to that gameweek's
    average. Per Ryan's rule change it now compares each entrant's
    HALF-SEASON TOTAL to the average half-season total across all entrants
    instead - a season-total comparison, not a single-gameweek one. The
    "best score in the half's worst gameweek" sub-prize is unchanged and
    still uses the worst-gameweek lookup below.
    """
    played_gws = sorted({g for e in entrants for g in e.get("scores", {}) if gw_start <= g <= gw_end})
    for e in entrants:
        e["_half_total"] = sum(v for g, v in e.get("scores", {}).items() if gw_start <= g <= gw_end)
        in_range = {g: v for g, v in e.get("scores", {}).items() if gw_start <= g <= gw_end}
        e["_half_rowmax"] = max(in_range.values()) if in_range else None
 
    if not played_gws:
        return None
 
    totals = {e["manager_name"]: e["_half_total"] for e in entrants}
    max_total = max(totals.values())
    leaders = [n for n, v in totals.items() if v == max_total]
    strictly_lower = [v for v in totals.values() if v < max_total]
    runner_total = max(strictly_lower) if strictly_lower else None
    runners = [n for n, v in totals.items() if runner_total is not None and v == runner_total]
 
    row_maxes = [e["_half_rowmax"] for e in entrants if e["_half_rowmax"] is not None]
    best_single = max(row_maxes) if row_maxes else None
    best_single_winners = [e["manager_name"] for e in entrants if e["_half_rowmax"] == best_single]
 
    averages = {}
    for g in played_gws:
        vals = [e["scores"][g] for e in entrants if g in e.get("scores", {})]
        if vals:
            averages[g] = sum(vals) / len(vals)
    worst_gw = min(averages, key=averages.get)
    worst_avg = averages[worst_gw]
    scores_in_worst = {e["manager_name"]: e["scores"][worst_gw] for e in entrants if worst_gw in e.get("scores", {})}
    best_in_worst = max(scores_in_worst.values())
    best_in_worst_winners = [n for n, v in scores_in_worst.items() if v == best_in_worst]
 
    # "Closest to Half-Season Average" - compares each entrant's half TOTAL
    # to the average half TOTAL across all entrants (not a single gameweek).
    half_avg_total = sum(totals.values()) / len(totals)
    closest_diff = min(abs(v - half_avg_total) for v in totals.values())
    closest_winners = [n for n, v in totals.items() if abs(v - half_avg_total) == closest_diff]
 
    return {
        "leaders": leaders, "max_total": max_total,
        "runners": runners, "runner_total": runner_total,
        "best_single": best_single, "best_single_winners": best_single_winners,
        "worst_gw": worst_gw, "worst_avg": worst_avg,
        "best_in_worst": best_in_worst, "best_in_worst_winners": best_in_worst_winners,
        "half_avg_total": half_avg_total,
        "closest_winners": closest_winners, "closest_diff": closest_diff,
    }
 
 
def _half_tab_html(tab_id, label, gw_range_label, entrants, gw_start, gw_end, fund_per_player=5):
    n = len(entrants)
    fund = fund_per_player * n
    stats = _half_stats(entrants, gw_start, gw_end)
 
    played_in_half = sorted({g for e in entrants for g in e.get("scores", {}) if gw_start <= g <= gw_end})
    latest_in_half = played_in_half[-1] if played_in_half else None
    for e in entrants:
        e["_gw_display"] = e.get("scores", {}).get(latest_in_half, "—") if latest_in_half else "—"
    sorted_list = sorted(entrants, key=lambda e: e["_half_total"], reverse=True)
    rows_html = _standings_rows(sorted_list, "_half_total")
 
    if stats is None:
        callouts = f'<div class="fplst-callout">⚽ {label} hasn\'t started yet.</div>'
    else:
        callouts = (
            f'<div class="fplst-callout">👑 <b>Leading:</b> {", ".join(stats["leaders"])} — {stats["max_total"]} pts '
            f'({fmt_money(0.60 * fund / len(stats["leaders"]))} each if it finishes here)</div>'
        )
        if stats["runners"]:
            callouts += (
                f'<div class="fplst-callout">🥈 <b>Runner-up spot:</b> {", ".join(stats["runners"])} — {stats["runner_total"]} pts '
                f'({fmt_money(0.30 * fund / len(stats["runners"]))} each if it finishes here)</div>'
            )
        callouts += (
            f'<div class="fplst-callout">🔥 <b>Best single GW this half:</b> {", ".join(stats["best_single_winners"])} — '
            f'{stats["best_single"]} pts</div>'
        )
        callouts += (
            f'<div class="fplst-callout">📉 <b>Worst GW so far:</b> GW{stats["worst_gw"]} '
            f'(league averaged {stats["worst_avg"]:.1f} pts) — best score there: {", ".join(stats["best_in_worst_winners"])} '
            f'({stats["best_in_worst"]} pts)</div>'
        )
        callouts += (
            f'<div class="fplst-callout">🎯 <b>Closest to the half-season average:</b> {", ".join(stats["closest_winners"])} '
            f'(league average so far: {stats["half_avg_total"]:.1f} pts)</div>'
        )
 
    return f"""
  <div class="fplst-tabpanel" id="fplst-panel-{tab_id}" role="tabpanel">
    <div class="fplst-panelhead">
      <div class="fplst-panellabel">{label}</div>
      <div class="fplst-panelrange">{gw_range_label}</div>
    </div>
    <div class="fplst-callouts">{callouts}</div>
    <div class="fplst-tablewrap">
      <table class="fplst-table">
        <thead><tr><th class="fplst-th-rank">#</th><th>Manager</th><th>Team</th><th class="fplst-th-num">GW</th><th class="fplst-th-num">Half Total</th></tr></thead>
        <tbody>{rows_html}</tbody>
      </table>
    </div>
  </div>"""
 
 
def _prize_pot_html(entrants):
    n = len(entrants)
    weekly_pot = 1 * n
    half_fund = 5 * n
    cup_fund = 2 * n
    return f"""
  <div class="fplst-prizepot">
    <div class="fplst-prizepot-title">💰 Prize Pot — What You Need To Do</div>
    <div class="fplst-prizepot-sub">{n} entrants paid in so far — every amount below scales automatically as more people join.</div>
 
    <div class="fplst-prizegroup">
      <div class="fplst-prizegroup-head">Every Gameweek <span class="fplst-fundchip">Pot: {fmt_money(weekly_pot)}</span></div>
      <div class="fplst-prizerow"><span class="fplst-prizewhat">🥇 Highest score in the gameweek</span><span class="fplst-prizeamt">{fmt_money(0.8*weekly_pot)} <small>(80%, split if tied)</small></span></div>
      <div class="fplst-prizerow"><span class="fplst-prizewhat">🍽️ 3rd-from-bottom score in the gameweek</span><span class="fplst-prizeamt">{fmt_money(0.2*weekly_pot)} <small>(20%, split if tied)</small></span></div>
    </div>
 
    <div class="fplst-prizegroup">
      <div class="fplst-prizegroup-head">First Half — GW1 to GW19 <span class="fplst-fundchip">Fund: {fmt_money(half_fund)}</span></div>
      <div class="fplst-prizerow"><span class="fplst-prizewhat">🏆 Most points across the half</span><span class="fplst-prizeamt">{fmt_money(0.60*half_fund)} <small>(60%)</small></span></div>
      <div class="fplst-prizerow"><span class="fplst-prizewhat">🥈 2nd most points across the half</span><span class="fplst-prizeamt">{fmt_money(0.30*half_fund)} <small>(30%)</small></span></div>
      <div class="fplst-prizerow"><span class="fplst-prizewhat">🔥 Highest score in any single gameweek</span><span class="fplst-prizeamt">{fmt_money(0.02*half_fund)} <small>(2%)</small></span></div>
      <div class="fplst-prizerow"><span class="fplst-prizewhat">💪 Best score in the half's worst gameweek</span><span class="fplst-prizeamt">{fmt_money(0.02*half_fund)} <small>(2%)</small></span></div>
      <div class="fplst-prizerow"><span class="fplst-prizewhat">🎯 Closest to the half-season average total</span><span class="fplst-prizeamt">{fmt_money(0.06*half_fund)} <small>(6%)</small></span></div>
    </div>
 
    <div class="fplst-prizegroup">
      <div class="fplst-prizegroup-head">Second Half — GW20 to GW38 <span class="fplst-fundchip">Fund: {fmt_money(half_fund)}</span></div>
      <div class="fplst-prizerow"><span class="fplst-prizewhat">Same five prizes as the First Half, fund resets to £0 at GW20</span><span class="fplst-prizeamt"></span></div>
    </div>
 
    <div class="fplst-prizegroup">
      <div class="fplst-prizegroup-head">Mini League Cup — GW33 knockout <span class="fplst-fundchip">Fund: {fmt_money(cup_fund)}</span></div>
      <div class="fplst-prizerow"><span class="fplst-prizewhat">🏅 Cup winner</span><span class="fplst-prizeamt">{fmt_money((2/3)*cup_fund)} <small>(2/3)</small></span></div>
      <div class="fplst-prizerow"><span class="fplst-prizewhat">🥈 Cup runner-up</span><span class="fplst-prizeamt">{fmt_money((1/3)*cup_fund)} <small>(1/3)</small></span></div>
    </div>
 
    <div class="fplst-prizenote">No 3rd-place prize in any category. Ties split the prize evenly between everyone tied. "Closest to the half-season average total" compares each entrant's half-season points total to the league's average half-season total (not a single gameweek). Full rules and a live running ledger of who's owed what are in the tracker spreadsheet.</div>
  </div>"""
 
 
def render_frontpage_html(entrants, generated_at_label=""):
    n = len(entrants)
    all_gws = sorted({g for e in entrants for g in e.get("scores", {})})
    latest_gw = all_gws[-1] if all_gws else None
 
    for e in entrants:
        e["_season_total"] = sum(e.get("scores", {}).values())
        e["_gw_score"] = e.get("scores", {}).get(latest_gw) if latest_gw else None
        e["_gw_display"] = e["_gw_score"] if e["_gw_score"] is not None else "—"
 
    sorted_overall = sorted(entrants, key=lambda e: e["_season_total"], reverse=True)
    overall_rows = _standings_rows(sorted_overall, "_season_total")
 
    if latest_gw is not None:
        gw_scores = [e["_gw_score"] for e in entrants if e["_gw_score"] is not None]
        weekly_pot = 1 * n
        top_score = max(gw_scores) if gw_scores else None
        ascending = sorted(gw_scores)
        third_bottom_score = ascending[2] if len(ascending) >= 3 else None
        top_winners = [e for e in entrants if e["_gw_score"] == top_score]
        bottom_winners = ([e for e in entrants if e["_gw_score"] == third_bottom_score]
                           if third_bottom_score is not None else [])
        top_each = (0.8 * weekly_pot) / len(top_winners) if top_winners else 0
        bottom_each = (0.2 * weekly_pot) / len(bottom_winners) if bottom_winners else 0
        overall_callouts = (f'<div class="fplst-callout">🥇 <b>Top score this GW:</b> '
                             f'{", ".join(e["manager_name"] for e in top_winners)} — {top_score} pts '
                             f'({fmt_money(top_each)} each)</div>')
        if bottom_winners:
            overall_callouts += (f'<div class="fplst-callout">🍽️ <b>3rd-from-bottom:</b> '
                                  f'{", ".join(e["manager_name"] for e in bottom_winners)} — {third_bottom_score} pts '
                                  f'({fmt_money(bottom_each)} each)</div>')
        gw_badge = f"GW{latest_gw}"
    else:
        gw_badge = "Pre-season"
        overall_callouts = ('<div class="fplst-callout">⚽ Season hasn\'t kicked off yet — '
                             'check back after Gameweek 1!</div>')
 
    overall_panel = f"""
  <div class="fplst-tabpanel fplst-active" id="fplst-panel-overall" role="tabpanel">
    <div class="fplst-panelhead">
      <div class="fplst-panellabel">Overall Season</div>
      <div class="fplst-panelrange">GW1 – GW38 (no reset)</div>
    </div>
    <div class="fplst-callouts">{overall_callouts}</div>
    <div class="fplst-tablewrap">
      <table class="fplst-table">
        <thead><tr><th class="fplst-th-rank">#</th><th>Manager</th><th>Team</th><th class="fplst-th-num">GW</th><th class="fplst-th-num">Total</th></tr></thead>
        <tbody>{overall_rows}</tbody>
      </table>
    </div>
  </div>"""
 
    half1_panel = _half_tab_html("half1", "First Half", "GW1 – GW19", entrants, 1, H1_END)
    half2_panel = _half_tab_html("half2", "Second Half", "GW20 – GW38", entrants, H2_START, N_GW)
    prize_pot = _prize_pot_html(entrants)
 
    footer = f"{n} entrants"
    if generated_at_label:
        footer += f" — updated {generated_at_label}"
 
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Knights Table Super League — Standings</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@600;700;800;900&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root {{
    --fpl-purple: #37003c;
    --fpl-purple-light: #5c1465;
    --fpl-green: #00ff87;
    --fpl-cyan: #04f5ff;
    --surface: #f4f1f5;
    --card: #ffffff;
    --text-primary: #16001a;
    --text-secondary: #5c4a60;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; padding: 20px 12px 40px; background: var(--surface); font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
  .fplst-root {{ max-width: 680px; margin: 0 auto; color: var(--text-primary); }}
  .fplst-header {{
    background: linear-gradient(135deg, var(--fpl-purple) 0%, var(--fpl-purple-light) 100%);
    border-radius: 16px 16px 0 0;
    padding: 22px 20px;
    display: flex; align-items: center; justify-content: space-between; gap: 12px;
    position: relative; overflow: hidden;
  }}
  .fplst-header::after {{
    content: ""; position: absolute; right: -40px; top: -40px; width: 160px; height: 160px;
    background: var(--fpl-cyan); opacity: 0.15; border-radius: 50%;
  }}
  .fplst-title {{ font-family: 'Montserrat', sans-serif; font-weight: 900; font-size: 21px; color: #fff; line-height: 1.2; letter-spacing: -0.01em; }}
  .fplst-sub {{ font-size: 13px; color: var(--fpl-green); font-weight: 600; margin-top: 3px; }}
  .fplst-badge {{
    background: var(--fpl-green); color: var(--fpl-purple); font-family: 'Montserrat', sans-serif;
    font-weight: 800; font-size: 13px; padding: 7px 14px; border-radius: 999px; white-space: nowrap; z-index: 1;
  }}
  .fplst-tabs {{ display: flex; background: var(--fpl-purple); padding: 0 12px; gap: 4px; }}
  .fplst-tab {{
    flex: 1; text-align: center; padding: 12px 6px; font-family: 'Montserrat', sans-serif; font-weight: 700;
    font-size: 13px; color: #cbb0d1; cursor: pointer; border-radius: 8px 8px 0 0; border: none; background: transparent;
    transition: background 0.15s, color 0.15s;
  }}
  .fplst-tab.fplst-tabactive {{ background: var(--card); color: var(--fpl-purple); }}
  .fplst-body {{ background: var(--card); border-radius: 0 0 16px 16px; padding: 20px; box-shadow: 0 2px 10px rgba(55,0,60,0.12); }}
  .fplst-tabpanel {{ display: none; }}
  .fplst-tabpanel.fplst-active {{ display: block; }}
  .fplst-panelhead {{ display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 12px; }}
  .fplst-panellabel {{ font-family: 'Montserrat', sans-serif; font-weight: 800; font-size: 16px; color: var(--fpl-purple); }}
  .fplst-panelrange {{ font-size: 12px; color: var(--text-secondary); font-weight: 600; }}
  .fplst-callouts {{ display: flex; flex-direction: column; gap: 8px; margin-bottom: 16px; }}
  .fplst-callout {{ background: #f4edf6; border: 1px solid #e3d3e8; border-radius: 10px; padding: 10px 12px; font-size: 13.5px; line-height: 1.45; color: var(--text-primary); }}
  .fplst-callout b {{ color: var(--fpl-purple); }}
  .fplst-tablewrap {{ overflow-x: auto; }}
  .fplst-table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
  .fplst-table th {{ text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-secondary); padding: 8px 6px; border-bottom: 2px solid #e5dee7; font-weight: 700; }}
  .fplst-table td {{ padding: 9px 6px; border-bottom: 1px solid #f0ebf1; }}
  .fplst-team {{ color: var(--text-secondary); }}
  .fplst-th-rank, .fplst-th-num {{ text-align: center !important; }}
  .fplst-table td:first-child, .fplst-table td:nth-child(4), .fplst-table td:nth-child(5) {{ text-align: center; }}
  .fplst-table td:last-child {{ font-weight: 800; color: var(--fpl-purple); }}
  .fplst-rankbadge {{ display: inline-flex; align-items: center; justify-content: center; width: 24px; height: 24px; border-radius: 999px; font-weight: 800; font-size: 12px; background: #ece4ee; color: var(--text-secondary); }}
  .fplst-rank-1 {{ background: var(--fpl-green); color: var(--fpl-purple); }}
  .fplst-rank-2 {{ background: #d9d9d9; color: #3a3a3a; }}
  .fplst-rank-3 {{ background: #e8b98a; color: #5a3300; }}
  .fplst-footer {{ margin-top: 14px; font-size: 12px; color: var(--text-secondary); text-align: right; }}
 
  .fplst-prizepot {{ margin-top: 20px; background: var(--card); border-radius: 16px; padding: 20px; box-shadow: 0 2px 10px rgba(55,0,60,0.12); }}
  .fplst-prizepot-title {{ font-family: 'Montserrat', sans-serif; font-weight: 900; font-size: 17px; color: var(--fpl-purple); }}
  .fplst-prizepot-sub {{ font-size: 12.5px; color: var(--text-secondary); margin-top: 3px; margin-bottom: 16px; }}
  .fplst-prizegroup {{ margin-bottom: 16px; }}
  .fplst-prizegroup:last-of-type {{ margin-bottom: 0; }}
  .fplst-prizegroup-head {{
    font-family: 'Montserrat', sans-serif; font-weight: 800; font-size: 13.5px; color: #fff; background: var(--fpl-purple);
    padding: 8px 12px; border-radius: 8px; display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 6px;
  }}
  .fplst-fundchip {{ background: var(--fpl-green); color: var(--fpl-purple); font-size: 11px; padding: 3px 9px; border-radius: 999px; white-space: nowrap; }}
  .fplst-prizerow {{ display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 7px 4px; border-bottom: 1px solid #f0ebf1; font-size: 13.5px; }}
  .fplst-prizerow:last-child {{ border-bottom: none; }}
  .fplst-prizewhat {{ color: var(--text-primary); }}
  .fplst-prizeamt {{ font-weight: 800; color: var(--fpl-purple); white-space: nowrap; }}
  .fplst-prizeamt small {{ font-weight: 500; color: var(--text-secondary); }}
  .fplst-prizenote {{ margin-top: 12px; font-size: 11.5px; color: var(--text-secondary); line-height: 1.5; }}
 
  @media (prefers-color-scheme: dark) {{
    :root {{ --surface: #120014; --card: #1f0224; --text-primary: #ffffff; --text-secondary: #c9b7cc; }}
    .fplst-table th {{ border-bottom-color: #3a1f3e; }}
    .fplst-table td {{ border-bottom-color: #2c1530; }}
    .fplst-callout {{ background: #2a0e30; border-color: #4a2350; }}
    .fplst-prizerow {{ border-bottom-color: #2c1530; }}
    .fplst-rankbadge {{ background: #3a1f3e; color: #c9b7cc; }}
    body {{ background: var(--surface); }}
  }}
</style>
</head>
<body>
<div class="fplst-root">
  <div class="fplst-header">
    <div>
      <div class="fplst-title">🏆 Knights Table Super League</div>
      <div class="fplst-sub">2026/27 Season</div>
    </div>
    <div class="fplst-badge">{gw_badge}</div>
  </div>
  <div class="fplst-tabs" role="tablist">
    <button class="fplst-tab fplst-tabactive" data-tab="overall" role="tab">Overall</button>
    <button class="fplst-tab" data-tab="half1" role="tab">1st Half</button>
    <button class="fplst-tab" data-tab="half2" role="tab">2nd Half</button>
  </div>
  <div class="fplst-body">
    {overall_panel}
    {half1_panel}
    {half2_panel}
    <div class="fplst-footer">{footer}</div>
  </div>
  {prize_pot}
</div>
<script>
  document.querySelectorAll('.fplst-tab').forEach(function (btn) {{
    btn.addEventListener('click', function () {{
      document.querySelectorAll('.fplst-tab').forEach(function (b) {{ b.classList.remove('fplst-tabactive'); }});
      document.querySelectorAll('.fplst-tabpanel').forEach(function (p) {{ p.classList.remove('fplst-active'); }});
      btn.classList.add('fplst-tabactive');
      document.getElementById('fplst-panel-' + btn.dataset.tab).classList.add('fplst-active');
    }});
  }});
</script>
</body>
</html>
"""
 
 
if __name__ == "__main__":
    import sys
    entrants = [
        {"manager_name": "Ryan Maudsley", "team_name": "Awob Abob Bobb", "entry_id": 3798630, "scores": {}},
        {"manager_name": "Paul Maudsley", "team_name": "Stach my Klich up", "entry_id": 6208141, "scores": {}},
    ]
    out_path = sys.argv[1] if len(sys.argv) > 1 else "frontpage.html"
    label = sys.argv[2] if len(sys.argv) > 2 else ""
    html = render_frontpage_html(entrants, generated_at_label=label)
    with open(out_path, "w") as f:
        f.write(html)
    print("wrote", out_path)
 
