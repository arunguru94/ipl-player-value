"""Step 1 of the player-value model: season-by-season player impact in 'runs above average' (RAA), ball by ball.

Every ball a player faces or bowls is compared with what an average player does in the SAME season, the SAME phase of the innings (powerplay overs 1-6,
middle 7-15, death 16-20) and at the SAME ground:
  bat RAA  = sum(runs - balls * expected runs/ball)            - W * sum(outs    - balls * expected out rate)
  bowl RAA = sum(balls * expected runs/ball - runs given)      + W * sum(wickets - balls * expected wicket rate)
  W        = runs a wicket is worth, estimated from the data (regression of innings total on balls and wickets lost)
Expected rates = league rate for (season, phase) x ground factor (how much the ground inflates scoring, shrunk toward 1 with 3,000 balls of prior).
This stops death-over bowlers (Bumrah types) being punished for the hard overs they bowl, openers being credited for the easy ones, and a team's own
ground from inflating or deflating its players. 'impact_raw' is the plain league-average version, kept for comparison.
Fielding and wicket-keeping are not measured.

Output: data/processed/player_season_impact.csv, impact_constants.json, ground_factors.csv
Run:  python -I scripts/model_impact.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

P = Path(__file__).resolve().parents[1] / "data" / "processed"
cols = ["match_id", "season", "venue", "innings", "striker", "bowler", "runs_off_bat", "is_wide", "legal", "bowler_runs", "is_wicket", "bowler_wicket",
        "player_dismissed", "over", "is_four", "is_six"]
bl = pd.read_csv(P / "balls.csv", usecols=lambda c: c in cols or c == "start_date")
bl["season"] = pd.to_datetime(bl["start_date"]).dt.year
bl = bl[bl["innings"] <= 2].copy()
bl["phase"] = np.where(bl["over"] <= 5, "PP", np.where(bl["over"] <= 14, "MID", "DEATH"))
for c in ("is_wide", "legal", "is_wicket", "bowler_wicket", "is_four", "is_six"):
    bl[c] = bl[c].astype(bool)

# ---- what is a wicket worth in runs? first-innings totals vs balls and wickets lost
inn = bl[bl["innings"] == 1].groupby("match_id").agg(runs=("bowler_runs", "sum"), outs=("is_wicket", "sum"), balls=("legal", "sum"))
coef = np.linalg.lstsq(np.c_[np.ones(len(inn)), inn["balls"], inn["outs"]], inn["runs"].values, rcond=None)[0]
W_EST = float(-coef[2] + coef[1] * 6)
W = float(np.clip(W_EST, 12, 30))
print(f"wicket worth {W_EST:.1f} runs (regression); using {W:.1f}")

# ---- batting side: balls faced (not wides), runs off the bat; outs belong to the dismissed batter
faced = bl[~bl["is_wide"]]
bat_b = faced.groupby(["striker", "season", "phase", "venue"]).agg(runs=("runs_off_bat", "sum"), balls=("runs_off_bat", "size"), fours=("is_four", "sum"), sixes=("is_six", "sum")).reset_index().rename(columns={"striker": "player"})
outs = bl[bl["is_wicket"] & bl["player_dismissed"].notna()].groupby(["player_dismissed", "season", "phase", "venue"]).size().rename("outs").reset_index().rename(columns={"player_dismissed": "player"})
bat_b = bat_b.merge(outs, on=["player", "season", "phase", "venue"], how="outer").fillna(0)
lg_bat = bat_b.groupby(["season", "phase"]).agg(r=("runs", "sum"), b=("balls", "sum"), o=("outs", "sum"))
lg_bat["rpb"], lg_bat["outr"] = lg_bat["r"] / lg_bat["b"], lg_bat["o"] / lg_bat["b"]
bat_b = bat_b.join(lg_bat[["rpb", "outr"]], on=["season", "phase"])
bat_b["er"], bat_b["eo"] = bat_b["balls"] * bat_b["rpb"], bat_b["balls"] * bat_b["outr"]

# ground factors (batting view, applied to bowling too: the same ground inflates both)
gv = bat_b.groupby("venue").agg(r=("runs", "sum"), e=("er", "sum"), o=("outs", "sum"), eo=("eo", "sum"), n=("balls", "sum"))
VF_R = 1 + (gv["r"] / gv["e"] - 1) * gv["n"] / (gv["n"] + 3000.0)
VF_W = 1 + (gv["o"] / gv["eo"] - 1) * gv["n"] / (gv["n"] + 3000.0)
mcount = pd.read_csv(P / "matches.csv").groupby("venue").size()
pd.DataFrame({"matches": mcount, "run_factor": VF_R.round(3), "wicket_factor": VF_W.round(3)}).dropna().sort_values("matches", ascending=False).to_csv(P / "ground_factors.csv")
bat_b["vr"], bat_b["vw"] = bat_b["venue"].map(VF_R).fillna(1.0), bat_b["venue"].map(VF_W).fillna(1.0)

# ---- bowling side
bow_b = bl.groupby(["bowler", "season", "phase", "venue"]).agg(legal=("legal", "sum"), conceded=("bowler_runs", "sum"), wkts=("bowler_wicket", "sum")).reset_index().rename(columns={"bowler": "player"})
lg_bow = bow_b.groupby(["season", "phase"]).agg(r=("conceded", "sum"), b=("legal", "sum"), w=("wkts", "sum"))
lg_bow["rpb"], lg_bow["wr"] = lg_bow["r"] / lg_bow["b"], lg_bow["w"] / lg_bow["b"]
bow_b = bow_b.join(lg_bow[["rpb", "wr"]], on=["season", "phase"])
bow_b["vr"], bow_b["vw"] = bow_b["venue"].map(VF_R).fillna(1.0), bow_b["venue"].map(VF_W).fillna(1.0)
bow_b["er"], bow_b["ew"] = bow_b["legal"] * bow_b["rpb"], bow_b["legal"] * bow_b["wr"]


def build(w_value):
    b = bat_b.assign(raa=(bat_b["runs"] - bat_b["er"] * bat_b["vr"]) - w_value * (bat_b["outs"] - bat_b["eo"] * bat_b["vw"]))
    bs = b.groupby(["player", "season"]).agg(runs=("runs", "sum"), balls=("balls", "sum"), outs=("outs", "sum"), fours=("fours", "sum"), sixes=("sixes", "sum"), bat_raa=("raa", "sum")).reset_index()
    o = bow_b.assign(raa=(bow_b["er"] * bow_b["vr"] - bow_b["conceded"]) + w_value * (bow_b["wkts"] - bow_b["ew"] * bow_b["vw"]))
    os_ = o.groupby(["player", "season"]).agg(legal=("legal", "sum"), conceded=("conceded", "sum"), wkts=("wkts", "sum"), bowl_raa=("raa", "sum")).reset_index()
    t = bs.merge(os_, on=["player", "season"], how="outer").fillna(0)
    t["impact"] = t["bat_raa"] + t["bowl_raa"]
    return t


t = build(W)
# plain version (league average per season only) for comparison
sb = bat_b.groupby(["player", "season"]).agg(runs=("runs", "sum"), balls=("balls", "sum"), outs=("outs", "sum")).reset_index()
lsb = sb.groupby("season").agg(r=("runs", "sum"), b=("balls", "sum"), o=("outs", "sum"))
sb["raw_bat"] = (sb["runs"] - sb["balls"] * sb["season"].map(lsb["r"] / lsb["b"])) - W * (sb["outs"] - sb["balls"] * sb["season"].map(lsb["o"] / lsb["b"]))
so = bow_b.groupby(["player", "season"]).agg(legal=("legal", "sum"), conceded=("conceded", "sum"), wkts=("wkts", "sum")).reset_index()
lso = so.groupby("season").agg(r=("conceded", "sum"), b=("legal", "sum"), w=("wkts", "sum"))
so["raw_bowl"] = (so["legal"] * so["season"].map(lso["r"] / lso["b"]) - so["conceded"]) + W * (so["wkts"] - so["legal"] * so["season"].map(lso["w"] / lso["b"]))
t = t.merge(sb[["player", "season", "raw_bat"]], on=["player", "season"], how="left").merge(so[["player", "season", "raw_bowl"]], on=["player", "season"], how="left").fillna(0)
t["impact_raw"] = t["raw_bat"] + t["raw_bowl"]
t = t.drop(columns=["raw_bat", "raw_bowl"])
xi = pd.read_csv(P / "playing_xi.csv").merge(pd.read_csv(P / "matches.csv", usecols=["match_id", "season"]), on="match_id")
m = xi.groupby(["player", "season"]).size().rename("matches").reset_index()
bi = pd.read_csv(P / "batting_innings.csv").groupby(["player", "season"]).size().rename("bat_inn").reset_index()
bo = pd.read_csv(P / "bowling_innings.csv").groupby(["player", "season"]).size().rename("bowl_inn").reset_index()
t = m.merge(t, on=["player", "season"], how="left").merge(bi, on=["player", "season"], how="left").merge(bo, on=["player", "season"], how="left").fillna(0)
t["impact_per_match"] = t["impact"] / t["matches"]
t.to_csv(P / "player_season_impact.csv", index=False)
json.dump({"wicket_value_runs": W, "wicket_value_estimated": W_EST}, open(P / "impact_constants.json", "w"))

base = t[t["season"] == 2026].set_index("player")["impact"]
for w2 in (15, 25):
    alt = build(w2).query("season == 2026").set_index("player")["impact"]
    print(f"2026 impact rank correlation, wicket={W:.0f} vs {w2}: {pd.concat([base, alt], axis=1, join='inner').corr(method='spearman').iloc[0, 1]:.3f}")
print("max |season total of impact| (near 0 if the baselines are right):", round(t.groupby("season")["impact"].sum().abs().max(), 1))
print("2026 top 10:"); print(t[t.season == 2026].nlargest(10, "impact")[["player", "matches", "runs", "wkts", "bat_raa", "bowl_raa", "impact", "impact_raw"]].round(0).to_string(index=False))
chk = t[t.season >= 2023].groupby("player").agg(adj=("impact", "sum"), raw=("impact_raw", "sum"), m=("matches", "sum")).query("m >= 40")
chk["diff"] = chk["adj"] - chk["raw"]
print("2023-26, change from adjusting for phase and ground (biggest drops, then gains):")
print(chk.sort_values("diff").iloc[list(range(5)) + list(range(-5, 0))].round(0).to_string())
for n in ("JJ Bumrah", "Arshdeep Singh", "TA Boult", "Rashid Khan", "V Kohli", "AD Russell"):
    r = t[(t.player == n) & (t.season == 2026)]
    if len(r):
        print(n, "2026 impact", round(float(r["impact"].iloc[0])), "vs raw", round(float(r["impact_raw"].iloc[0])), "matches", int(r["matches"].iloc[0]))
