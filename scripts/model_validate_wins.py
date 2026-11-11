"""Does the impact measure relate to winning? Team-season impact (sum of each player's per-match impact over the games he played for the team)
versus the team's win rate, all seasons. Gives the conversion used in the report: win-% points (and wins per 14 games) per run of impact.
Note: this is a same-season, descriptive check (impact is built from the same matches), so it shows the measure captures winning, not that it predicts it.
Output: data/processed/impact_vs_wins.json.   Run: python -I scripts/model_validate_wins.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import pearsonr

P = Path(__file__).resolve().parents[1] / "data" / "processed"
imp = pd.read_csv(P / "player_season_impact.csv")
m = pd.read_csv(P / "matches.csv")
xi = pd.read_csv(P / "playing_xi.csv").merge(m[["match_id", "season"]], on="match_id")


def fr(t):
    t = str(t)
    return "RCB" if "Royal Challengers" in t else "DC" if "Delhi" in t else "PBKS" if "Punjab" in t else t


xi["team"] = xi["team"].map(fr)
pm = imp.set_index(["player", "season"])
ipm = (pm["impact"] / pm["matches"].clip(lower=1)).to_dict()
xi["ipm"] = [ipm.get((p, s), 0.0) for p, s in zip(xi["player"], xi["season"])]
ts = xi.groupby(["season", "team"])["ipm"].sum().rename("impact").reset_index()
m["w"] = m["winner"].map(fr)
played = pd.concat([m.assign(team=m["team1"].map(fr)), m.assign(team=m["team2"].map(fr))]).dropna(subset=["winner"]).groupby(["season", "team"]).size().rename("played").reset_index()
wins = m.dropna(subset=["winner"]).groupby(["season", "w"]).size().rename("wins").reset_index().rename(columns={"w": "team"})
d = ts.merge(played, on=["season", "team"]).merge(wins, on=["season", "team"], how="left").fillna({"wins": 0})
d = d[d["played"] >= 10]
d["win_pct"] = d["wins"] / d["played"] * 100
r, p = pearsonr(d["impact"], d["win_pct"])
slope = float(np.polyfit(d["impact"], d["win_pct"], 1)[0])
out = {"team_seasons": int(len(d)), "correlation": float(r), "win_pct_points_per_run": slope, "wins_per_14_games_per_100_runs": slope * 100 / 100 * 14}
json.dump(out, open(P / "impact_vs_wins.json", "w"), indent=1)
print(out)
