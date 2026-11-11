"""Step 3: home-ground advantage - for teams, and for each player at each team's home ground.

A. Team home advantage: home win rate vs away win rate for the 10 current franchises (neutral-venue seasons 2009, 2020, 2021, 2022 left out).
B. Ground factors: how much a ground raises or lowers runs per ball and wickets per ball compared with the league in the same season.
C. Player-at-ground fit: player's runs-above-average per 100 balls AT a ground minus the same player's rate everywhere else, both measured against
   that ground's own scoring level, then shrunk toward 0 in proportion to how little data there is (k balls of 'prior').
D. Out-of-sample check: does a fit built from earlier seasons predict the same player's performance at that ground in a later season?
   The slope of that check (how much of the fit is real) is what the final model multiplies the fit by.

Outputs: team_home_advantage.csv, ground_factors.csv, player_ground_fit.csv, home_fit_check.json
Run:  python -I scripts/model_home.py        (after model_impact.py)
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

P = Path(__file__).resolve().parents[1] / "data" / "processed"
HOME = {   # franchise -> home grounds (canonical names from build_dataset.py)
    "Chennai Super Kings": ["MA Chidambaram Stadium"],
    "Mumbai Indians": ["Wankhede Stadium"],
    "Kolkata Knight Riders": ["Eden Gardens"],
    "Royal Challengers Bengaluru": ["M Chinnaswamy Stadium"],
    "Delhi Capitals": ["Arun Jaitley Stadium (Feroz Shah Kotla)"],
    "Punjab Kings": ["PCA IS Bindra Stadium, Mohali", "Maharaja Yadavindra Singh Stadium, New Chandigarh (Mullanpur)", "Himachal Pradesh Cricket Association Stadium"],
    "Rajasthan Royals": ["Sawai Mansingh Stadium"],
    "Sunrisers Hyderabad": ["Rajiv Gandhi International Stadium"],
    "Gujarat Titans": ["Narendra Modi Stadium (Sardar Patel, Motera)"],
    "Lucknow Super Giants": ["Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium"],
}
NEUTRAL = {2009, 2020, 2021, 2022}


def fr(t):
    t = str(t)
    return ("Royal Challengers Bengaluru" if "Royal Challengers" in t else "Delhi Capitals" if "Delhi" in t else "Punjab Kings" if "Punjab" in t
            else "Rajasthan Royals" if "Rajasthan" in t else t)


m = pd.read_csv(P / "matches.csv", parse_dates=["date"])
bat = pd.read_csv(P / "batting_innings.csv")
bowl = pd.read_csv(P / "bowling_innings.csv")
bat["team"], bowl["team"] = bat["team"].map(fr), bowl["team"].map(fr)

# ---------------- A. team home advantage
rows = []
for team, grounds in HOME.items():
    mt = m[(m["team1"].map(fr) == team) | (m["team2"].map(fr) == team)].copy()
    mt = mt[~mt["season"].isin(NEUTRAL) & mt["winner"].notna()]
    mt["home"] = mt["venue"].isin(grounds)
    mt["won"] = mt["winner"].map(fr) == team
    h, a = mt[mt["home"]], mt[~mt["home"]]
    # runs per innings by this team at home vs away
    tb = bat[(bat["team"] == team) & bat["match_id"].isin(mt["match_id"])].merge(mt[["match_id", "home"]], on="match_id")
    inns = tb.groupby(["match_id", "home"])["runs"].sum().reset_index()
    rows.append({"team": team, "home_matches": len(h), "home_win_pct": 100 * h["won"].mean(), "away_matches": len(a), "away_win_pct": 100 * a["won"].mean(),
                 "home_edge_pct_points": 100 * (h["won"].mean() - a["won"].mean()),
                 "se_pct_points": 100 * np.sqrt(h["won"].mean() * (1 - h["won"].mean()) / len(h) + a["won"].mean() * (1 - a["won"].mean()) / len(a)),
                 "runs_per_innings_home": inns[inns["home"]]["runs"].mean(), "runs_per_innings_away": inns[~inns["home"]]["runs"].mean()})
tha = pd.DataFrame(rows).round(2)
tha.to_csv(P / "team_home_advantage.csv", index=False)
allh = pd.concat([m.assign(team=fr(t)) for t in []]) if False else None
print(tha.to_string(index=False))
tot_h = (tha["home_matches"] * tha["home_win_pct"]).sum() / tha["home_matches"].sum()
tot_a = (tha["away_matches"] * tha["away_win_pct"]).sum() / tha["away_matches"].sum()
print(f"all ten: home win {tot_h:.1f}% vs away win {tot_a:.1f}% -> league-wide home edge {tot_h - tot_a:+.1f} points")

# ---------------- B. ground factors (vs same-season league)
lg_b = bat.groupby("season").agg(r=("runs", "sum"), b=("balls", "sum"), o=("dismissed", "sum"))
bat["exp_runs_lg"] = bat["balls"] * bat["season"].map(lg_b["r"] / lg_b["b"])
bat["exp_outs_lg"] = bat["balls"] * bat["season"].map(lg_b["o"] / lg_b["b"])
g = bat.groupby("venue").agg(runs=("runs", "sum"), exp=("exp_runs_lg", "sum"), outs=("dismissed", "sum"), expo=("exp_outs_lg", "sum"), balls=("balls", "sum"))
K_V = 3000.0                                                         # balls of prior pulling a ground's factor toward 1
g["run_factor"] = 1 + (g["runs"] / g["exp"] - 1) * g["balls"] / (g["balls"] + K_V)
g["wicket_factor"] = 1 + (g["outs"] / g["expo"] - 1) * g["balls"] / (g["balls"] + K_V)
g["matches"] = m.groupby("venue").size()
g[["matches", "run_factor", "wicket_factor"]].round(3).sort_values("matches", ascending=False).to_csv(P / "ground_factors.csv")
VF_R, VF_W = g["run_factor"], g["wicket_factor"]
print("run factor of the ten home grounds:", {k[:18]: round(VF_R.get(v[0], np.nan), 3) for k, v in HOME.items()})

# ---------------- C. player-at-ground rates, adjusted for the ground's own level
lg_w = bowl.groupby("season").agg(r=("runs", "sum"), b=("legal_balls", "sum"), w=("wickets", "sum"))
W = json.load(open(P / "impact_constants.json"))["wicket_value_runs"]
bat["vf_r"], bat["vf_w"] = bat["venue"].map(VF_R).fillna(1.0), bat["venue"].map(VF_W).fillna(1.0)
bat["raa"] = (bat["runs"] - bat["exp_runs_lg"] * bat["vf_r"]) - W * (bat["dismissed"] - bat["exp_outs_lg"] * bat["vf_w"])
bowl["exp_r"] = bowl["legal_balls"] * bowl["season"].map(lg_w["r"] / lg_w["b"]) * bowl["venue"].map(VF_R).fillna(1.0)
bowl["exp_w"] = bowl["legal_balls"] * bowl["season"].map(lg_w["w"] / lg_w["b"]) * bowl["venue"].map(VF_W).fillna(1.0)
bowl["raa"] = (bowl["exp_r"] - bowl["runs"]) + W * (bowl["wickets"] - bowl["exp_w"])
K_BAT, K_BOWL = 200.0, 150.0                                         # balls of prior for player-level shrinkage (tuned by the check below)


def rates(df, balls_col, k):
    """Per player: shrunk (rate at ground - rate elsewhere) per 100 balls, for every ground with data."""
    tot = df.groupby("player").agg(raa=("raa", "sum"), n=(balls_col, "sum"))
    v = df.groupby(["player", "venue"]).agg(raa=("raa", "sum"), n=(balls_col, "sum")).reset_index()
    v = v.merge(tot, on="player", suffixes=("", "_all"))
    v["raa_else"], v["n_else"] = v["raa_all"] - v["raa"], v["n_all"] - v["n"]
    v["fit"] = (v["raa"] / v["n"].clip(lower=1) - v["raa_else"] / v["n_else"].clip(lower=1)) * 100
    v.loc[v["n_else"] < 30, "fit"] = 0.0
    v["fit_shrunk"] = v["fit"] * v["n"] / (v["n"] + k)
    return v[["player", "venue", "n", "fit", "fit_shrunk"]]


# ---------------- D. out-of-sample check: fit from seasons < T vs the same player-ground in season T
def check(df, balls_col, k):
    pts = []
    for T in range(2013, 2027):
        pre, now = df[df["season"] < T], df[df["season"] == T]
        f = rates(pre, balls_col, k)
        tot_now = now.groupby("player").agg(raa=("raa", "sum"), n=(balls_col, "sum"))
        vn = now.groupby(["player", "venue"]).agg(raa=("raa", "sum"), n=(balls_col, "sum")).reset_index().merge(tot_now, on="player", suffixes=("", "_all"))
        vn["n_else"] = vn["n_all"] - vn["n"]
        vn = vn[(vn["n"] >= 20) & (vn["n_else"] >= 60)]
        vn["actual"] = (vn["raa"] / vn["n"] - (vn["raa_all"] - vn["raa"]) / vn["n_else"]) * 100
        j = vn.merge(f, on=["player", "venue"])
        j = j[j["n_y"] >= 20] if "n_y" in j else j
        j["season"] = T
        pts.append(j[["player", "venue", "season", "fit_shrunk", "fit", "actual", "n_x"]].rename(columns={"n_x": "n_now"}))
    d = pd.concat(pts)
    w = np.sqrt(d["n_now"])
    slope = float(np.sum(w * d["fit_shrunk"] * d["actual"]) / np.sum(w * d["fit_shrunk"] ** 2))
    # slope uncertainty by resampling players
    rng = np.random.default_rng(0)
    plist = d["player"].unique()
    bs = []
    for _ in range(300):
        s = rng.choice(plist, len(plist))
        dd = pd.concat([d[d["player"] == p] for p in s[:400]])
        ww = np.sqrt(dd["n_now"])
        bs.append(np.sum(ww * dd["fit_shrunk"] * dd["actual"]) / np.sum(ww * dd["fit_shrunk"] ** 2))
    return d, slope, float(np.std(bs)), float(np.corrcoef(d["fit_shrunk"], d["actual"])[0, 1])


out = {}
for name, df, col, k in (("batting", bat, "balls", K_BAT), ("bowling", bowl, "legal_balls", K_BOWL)):
    d, slope, se, r = check(df, col, k)
    out[name] = {"pairs": int(len(d)), "slope": slope, "slope_se": se, "corr": r}
    print(f"{name}: {len(d)} player-ground cases; later performance at the ground moves {slope:.2f} (SE {se:.2f}) runs per 100 balls for each 1 of shrunk fit; correlation {r:.3f}")
json.dump(out, open(P / "home_fit_check.json", "w"), indent=1)

fb, fw = rates(bat, "balls", K_BAT).rename(columns={"n": "bat_balls", "fit": "bat_fit", "fit_shrunk": "bat_fit_shrunk"}), rates(bowl, "legal_balls", K_BOWL).rename(columns={"n": "bowl_balls", "fit": "bowl_fit", "fit_shrunk": "bowl_fit_shrunk"})
fit = fb.merge(fw, on=["player", "venue"], how="outer").fillna(0)
fit.to_csv(P / "player_ground_fit.csv", index=False)
print("player-ground fit rows:", len(fit))
