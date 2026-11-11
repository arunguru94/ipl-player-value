"""Write IPL_MODEL.md: the model results, validation, and a recommendation page for each team, all generated from data/processed.
Run:  python -I scripts/make_report.py        (after model_recommend.py and model_validate_wins.py)
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
keep = pd.read_csv(P / "team_keep_values.csv")
tg = pd.read_csv(P / "team_targets.csv")
summ = pd.read_csv(P / "team_summary.csv")
pv = pd.read_csv(P / "player_value.csv")
bt = pd.DataFrame(json.load(open(P / "forecast_backtest_summary.json")))      # rows = models
hf = json.load(open(P / "home_fit_check.json"))
wins = json.load(open(P / "impact_vs_wins.json"))
tha = pd.read_csv(P / "team_home_advantage.csv")
gf = pd.read_csv(P / "ground_factors.csv")
W = json.load(open(P / "impact_constants.json"))["wicket_value_runs"]


def table(df, cols, heads=None):
    heads = heads or cols
    lines = ["| " + " | ".join(heads) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            cells.append("" if (isinstance(v, float) and np.isnan(v)) else (f"{v:.1f}" if isinstance(v, float) and abs(v) < 1000 and c not in ("age",) else str(int(v)) if isinstance(v, float) else str(v)))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


L = []
a = L.append
a("# IPL player-value model: which players suit each team\n")
a("Built from 1,243 matches of ball-by-ball data (2008 to 2026) plus the 2026 squads, salaries, ages and trades up to 11 Nov 2026. "
  "Run order: `build_dataset.py`, `build_players.py`, `build_trades.py`, `model_impact.py`, `model_predict.py`, `model_home.py`, `model_recommend.py`, `model_validate_wins.py`, `make_report.py`.\n")
a("## The short version\n")
a(f"- **Value** is measured as *impact*: runs above an average player over a season, ball by ball, compared with the same phase of the innings and the same ground, "
  f"counting a wicket as {W:.0f} runs. Across {wins['team_seasons']} team-seasons, a team's total impact correlates **{wins['correlation']:.2f}** with its win rate; "
  f"**+100 runs of impact is worth about {wins['wins_per_14_games_per_100_runs']:.1f} extra wins in a 14-game season.** Even the best signing moves a season by well under one win.")
b = bt.loc["blend"]
a(f"- **Forecasting next season is weak.** The model's rank correlation with what really happened is **{b['rank_corr_mean']:.2f}** (SE {b['rank_corr_se']:.2f}) over {int(b['seasons'])} test seasons, "
  f"against {bt.loc['last', 'rank_corr_mean']:.2f} for 'same as last season' and {bt.loc['mean3', 'rank_corr_mean']:.2f} for a simple weighted 3-season average. "
  "It is no better than that simple average, and a typical forecast is off by about 66 runs of impact. Treat the forecasts as a ranking of broad tiers, not exact numbers.")
a(f"- **Home-ground advantage is real for teams but not for individual players.** Across the ten franchises the home side wins about **{(tha.home_matches * tha.home_win_pct).sum() / tha.home_matches.sum():.1f}%** of matches against "
  f"**{(tha.away_matches * tha.away_win_pct).sum() / tha.away_matches.sum():.1f}%** away, but differences between teams are within noise. A player's past record at a specific ground does **not** predict how he does there later "
  f"(batting slope {hf['batting']['slope']:.2f} ± {hf['batting']['slope_se']:.2f}, bowling {hf['bowling']['slope']:.2f} ± {hf['bowling']['slope_se']:.2f}; a real effect would be near 1). "
  "So the recommendations do not use player-ground fit. Grounds are used only to remove their own scoring bias from every player's numbers.")
a("- **Price is only loosely linked to value:** salary and forecast impact correlate about 0.4 across the 172 players with a forecast.\n")

a("## How the recommendations are made\n")
a("1. Each player's impact for every season is computed (`model_impact.py`).\n2. A ridge-plus-gradient-boosting blend forecasts 2027 impact from the last three seasons, matches played, balls faced and bowled, and experience (`model_predict.py`). Age is not in the model: dates of birth exist only for the current squads.\n"
  "3. For each team an optimiser picks the best squad and XI under the IPL rules, within the purse (`model_recommend.py`). Rules: squad of 18 to 25, at most 8 overseas in the squad and 4 in the XI, at least 2 keepers, 5 who bowl and 6 who bat in the XI, salaries within the purse. "
  "The purse defaults to ₹125 crore (the 2026 figure; 2027 is not confirmed: run `model_recommend.py 130` to change it). Cheap unproven fillers can always be signed at ₹0.30 crore.\n"
  "4. **Keep value** = team value with the player minus without him. **Fit gain** = team value if an outside player is added (others may be dropped to fit the purse) minus now, at his current salary. These differ by team because they depend on what the team already has.\n")
a("Targets are ideals, not predictions: several teams can want the same player, salaries in 2027 will differ, and who is available depends on the retention deadline (17 Nov), trades and the December auction.\n")

a("## Summary by team\n")
s = summ.rename(columns={"team": "Team", "current_squad": "Squad now", "current_payroll_crore": "Payroll (cr)", "best_xi_forecast": "Best XI forecast (runs)", "squad_cost_crore": "Best squad cost (cr)", "not_needed": "Players not needed"})
a(table(s, ["Team", "Squad now", "Payroll (cr)", "Best XI forecast (runs)", "Best squad cost (cr)", "Players not needed"]) + "\n")
a("The XI forecast is the sum of forecast impact of the best legal XI from the team's own players; higher is better.\n")

for team in summ["team"]:
    k = keep[keep.team == team]
    a(f"## {team}\n")
    xi = k[k.in_best_xi].sort_values("keep_value", ascending=False)
    a("**Best XI from the current squad** (by contribution):\n")
    a(table(xi, ["player", "role", "age", "price_crore", "forecast_impact_2027", "keep_value"], ["Player", "Role", "Age", "Salary (cr)", "Forecast impact", "Keep value"]) + "\n")
    surplus = k[(k.keep_value <= 0.5) & (k.price_crore >= 2)].sort_values("price_crore", ascending=False).head(6)
    if len(surplus):
        a("**Paid well but not needed by this model** (forecast below what a cheap replacement gives, or surplus to the best squad):\n")
        a(table(surplus, ["player", "role", "age", "price_crore", "forecast_impact_2027"], ["Player", "Role", "Age", "Salary (cr)", "Forecast impact"]) + "\n")
    t = tg[tg.team == team].head(5)
    a("**Best additions** (if available):\n")
    a(table(t, ["player", "from_team", "role", "age", "price_crore", "fit_gain", "squad_cost_change_crore"], ["Player", "Now at", "Role", "Age", "Salary (cr)", "Fit gain", "Extra cost (cr)"]) + "\n")

a("## League-wide\n")
a("**Highest forecast impact for 2027:**\n")
a(table(pv[pv.has_forecast].head(12), ["player", "team", "role", "age", "price_crore", "forecast_impact_2027"], ["Player", "Team", "Role", "Age", "Salary (cr)", "Forecast impact"]) + "\n")
vv = pv[(pv.forecast_impact_2027 > 25)].sort_values("value_per_crore", ascending=False).head(10)
a("**Best value for money** (forecast impact above 25, most impact per crore):\n")
a(table(vv, ["player", "team", "role", "age", "price_crore", "forecast_impact_2027", "value_per_crore"], ["Player", "Team", "Role", "Age", "Salary (cr)", "Forecast impact", "Impact per cr"]) + "\n")
op = pv[pv.has_forecast & (pv.price_crore >= 10)].sort_values("forecast_impact_2027").head(10)
a("**Highest-paid players with the weakest forecast.** Mostly one poor 2026 season pulling the forecast down; check the player's longer record before acting:\n")
a(table(op, ["player", "team", "role", "age", "price_crore", "forecast_impact_2027", "impact_2026"], ["Player", "Team", "Role", "Age", "Salary (cr)", "Forecast impact", "2026 impact"]) + "\n")

a("## What the model cannot see\n")
a("- Fielding, wicket-keeping quality, captaincy, injuries and fitness, and who bats where. Keepers and bowlers are valued only by their batting and bowling.\n"
  "- Age: older players (Kohli 38, Klaasen 35, Jadeja 37) are forecast like younger ones with the same record.\n"
  "- Match-ups, pitch type versus bowling style, and dew. Ground effects are measured only as an overall scoring level.\n"
  "- Auction rules for 2027 (purse, retention slabs, overseas fee cap, right to match) are not confirmed, and 2027 salaries will differ from 2026 contracts.\n"
  "- Role labels for about 40 players with almost no IPL record are guesses, and players with no 2026 usage are forecast at league average.\n"
  "- A sample of one season for most players: the forecast error (about 66 runs) is larger than the gap between most mid-ranked players.\n")
(ROOT / "IPL_MODEL.md").write_text("\n".join(L))
print("written IPL_MODEL.md,", len("\n".join(L).splitlines()), "lines")
