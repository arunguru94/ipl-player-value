"""Step 4: which players suit each team under the IPL rules and the purse.

Team value = what a team's best squad is worth, found by a mixed-integer optimiser:
    value = sum(forecast impact of the XI) + BENCH_WEIGHT * sum(forecast impact of the rest of the squad)
Impact = forecast runs above average next season, measured against the same grounds. Rules enforced (settings at the top; change them if 2027 differs):
    squad 18-25, at most 8 overseas, total salary within the purse; XI of 11 with at most 4 overseas, at least 1 keeper, 5 who bowl and 6 who bat;
    at least 2 keepers in the squad.
Every team can also sign FILLERS: unproven domestic players at the minimum salary with replacement-level forecast (so a missing keeper or bowler can be covered).

Two scores per team and player:
  KEEP VALUE  of a current player = team value with him - team value without him (others reshuffled, fillers allowed).
  FIT GAIN    of an outside player = team value if he is added (and the team may drop others to fit the purse) - team value now, at his current salary.
They are different for every team because they depend on what the team already has: its roles, overseas slots and payroll. Fit gain is an ideal, not a
prediction: several teams may want the same player, and who is available depends on the 2027 releases, trades and auction.

Inputs: players_2026.csv, impact_forecast_2027.csv, balls.csv.   Outputs: team_keep_values.csv, team_fit_matrix.csv, team_targets.csv, team_summary.csv, player_value.csv
Run:  python -I scripts/model_recommend.py [purse_crore]        (after model_predict.py and build_trades.py)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp

P = Path(__file__).resolve().parents[1] / "data" / "processed"
PURSE = float(sys.argv[1]) if len(sys.argv) > 1 else 125.0          # crore; the 2026 purse was 125, the 2027 purse is not confirmed
SQUAD_MIN, SQUAD_MAX, OVERSEAS_SQUAD, OVERSEAS_XI = 18, 25, 8, 4
BENCH_WEIGHT = 0.25                                                  # a bench player counts a quarter of an XI player (injuries, rotation)
MIN_PRICE = 0.30                                                     # lowest salary, crore

pl = pd.read_csv(P / "players_2026.csv")
fc = pd.read_csv(P / "impact_forecast_2027.csv").rename(columns={"player": "ipl_name"})
pl = pl.merge(fc[["ipl_name", "pred_impact_2027", "impact_2026"]], on="ipl_name", how="left")
pl["has_forecast"] = pl["pred_impact_2027"].notna()
pl["value"] = pl["pred_impact_2027"].fillna(0.0)
pl["price"] = pl["trade_2027_fee_crore"].fillna(pl["price_2026_crore"]).clip(lower=MIN_PRICE)
pl["team"] = pl["current_team"]
pl["overseas"] = pl["overseas"].astype(bool)

# wicket-keepers: Wikipedia role, or at least 2 stumpings in the IPL record (the role text is often missing from the article extract)
b = pd.read_csv(P / "balls.csv", usecols=["wicket_type", "fielder_1"])
stump = b[b["wicket_type"] == "stumped"].groupby("fielder_1").size()
pl["stumpings"] = pl["ipl_name"].map(stump).fillna(0)
role = pl["role"].replace({"Unknown": np.nan})
role = role.fillna(pl["bowling_style"].map(lambda s: "Bowler" if isinstance(s, str) else "Batter"))
pl["role_model"] = role
pl["keeper"] = role.eq("Wicket-keeper batter") | (pl["stumpings"] >= 2)
pl["bats"] = role.isin(["Batter", "Wicket-keeper batter", "All-rounder"]) | pl["keeper"]
pl["bowls"] = role.isin(["Bowler", "All-rounder"])
pl = pl.drop_duplicates("player").reset_index(drop=True)

# replacement level = average forecast of players on the minimum-ish salary who have a forecast
repl_val = float(pl[(pl["price"] <= 0.5) & pl["has_forecast"]]["value"].mean())
fill = []
for kind, n, kw in (("Batter", 3, dict(bats=True, bowls=False, keeper=False)), ("Keeper", 2, dict(bats=True, bowls=False, keeper=True)),
                    ("Bowler", 4, dict(bats=False, bowls=True, keeper=False)), ("All-rounder", 2, dict(bats=True, bowls=True, keeper=False))):
    for i in range(n):
        fill.append(dict(player=f"[filler {kind} {i + 1}]", team="free", value=repl_val, price=MIN_PRICE, overseas=False, filler=True, role_model=kind, **kw))
FILL = pd.DataFrame(fill)
pl["filler"] = False
print(f"replacement-level forecast (cheap players with a forecast): {repl_val:.1f} runs; purse {PURSE} crore")


def solve(pool, purse, force=None, exclude=None):
    """Return (objective, selected mask, xi mask) for the best legal squad from pool; force/exclude are pool positions."""
    n = len(pool)
    v, c = pool["value"].values, pool["price"].values
    obj = -np.r_[BENCH_WEIGHT * v, (1 - BENCH_WEIGHT) * v]            # x (squad) then y (XI)
    z, one = np.zeros(n), np.ones(n)
    A, lo, hi = [], [], []

    def add(xc, yc, l, h):
        A.append(np.r_[xc, yc]); lo.append(l); hi.append(h)

    ov, kp = pool["overseas"].values * 1.0, pool["keeper"].values * 1.0
    add(one, z, SQUAD_MIN, SQUAD_MAX); add(z, one, 11, 11)
    add(ov, z, 0, OVERSEAS_SQUAD); add(z, ov, 0, OVERSEAS_XI)
    add(c, z, 0, purse)
    add(z, kp, 1, 11); add(kp, z, 2, 25)
    add(z, pool["bowls"].values * 1.0, 5, 11); add(z, pool["bats"].values * 1.0, 6, 11)
    for i in range(n):
        r = np.zeros(2 * n); r[i] = -1; r[n + i] = 1
        A.append(r); lo.append(-np.inf); hi.append(0)
    lb, ub = np.zeros(2 * n), np.ones(2 * n)
    if force is not None:
        lb[force] = 1
    if exclude is not None:
        ub[exclude] = 0; ub[n + exclude] = 0
    res = milp(obj, constraints=LinearConstraint(np.array(A), lo, hi), integrality=np.ones(2 * n), bounds=Bounds(lb, ub), options={"time_limit": 30})
    if res.x is None:
        return None
    x, y = res.x[:n] > 0.5, res.x[n:] > 0.5
    return -res.fun, x, y


keep_rows, fit_rows, summ = [], [], []
for team in sorted(pl["team"].unique()):
    own = pl[pl["team"] == team]
    pool = pd.concat([own, FILL], ignore_index=True)
    base = solve(pool, PURSE)
    if base is None:
        print("no legal squad for", team); continue
    obj0, x0, y0 = base
    sel = pool[x0]
    # KEEP VALUE of every current player in the best squad: drop him and re-solve
    for i in np.where(x0 & ~pool["filler"].values)[0]:
        r = solve(pool, PURSE, exclude=i)
        keep_rows.append({"team": team, "player": pool.at[i, "player"], "role": pool.at[i, "role_model"], "overseas": bool(pool.at[i, "overseas"]), "age": pool.at[i, "age"],
                          "price_crore": round(pool.at[i, "price"], 2), "forecast_impact_2027": round(pool.at[i, "value"], 0), "has_forecast": bool(pool.at[i, "has_forecast"]),
                          "in_best_xi": bool(y0[i]), "keep_value": round(obj0 - (r[0] if r else np.nan), 1)})
    for _, r in own[~own["player"].isin(set(sel["player"]))].iterrows():
        keep_rows.append({"team": team, "player": r["player"], "role": r["role_model"], "overseas": bool(r["overseas"]), "age": r["age"], "price_crore": round(r["price"], 2),
                          "forecast_impact_2027": round(r["value"], 0), "has_forecast": bool(r["has_forecast"]), "in_best_xi": False, "keep_value": 0.0})
    # FIT GAIN of every outside player
    others = pl[pl["team"] != team]
    for _, o in others.iterrows():
        p2 = pd.concat([pool, o.to_frame().T.assign(filler=False)], ignore_index=True)
        for c in ("value", "price"):
            p2[c] = p2[c].astype(float)
        for c in ("overseas", "keeper", "bats", "bowls", "filler"):
            p2[c] = p2[c].astype(bool)
        r = solve(p2, PURSE, force=len(p2) - 1)
        fit_rows.append({"team": team, "player": o["player"], "from_team": o["team"], "role": o["role_model"], "overseas": bool(o["overseas"]), "age": o["age"],
                         "price_crore": round(float(o["price"]), 2), "forecast_impact_2027": round(float(o["value"]), 0), "has_forecast": bool(o["has_forecast"]),
                         "fit_gain": round(r[0] - obj0, 1) if r else np.nan, "in_best_xi_if_added": bool(r[2][-1]) if r else False,
                         "squad_cost_change_crore": round(float(p2[r[1]]["price"].sum()) - float(sel["price"].sum()), 1) if r else np.nan})
    summ.append({"team": team, "current_squad": len(own), "current_payroll_crore": round(own["price"].sum(), 1), "best_squad_value": round(obj0, 0),
                 "best_xi_forecast": round(pool[y0]["value"].sum(), 0), "squad_cost_crore": round(sel["price"].sum(), 1),
                 "fillers_needed": int(sel["filler"].sum()), "overseas_in_best_squad": int(sel["overseas"].sum()),
                 "not_needed": int((~own["player"].isin(set(sel["player"]))).sum())})
    print(team, "done", flush=True)

keep, fit, summary = pd.DataFrame(keep_rows), pd.DataFrame(fit_rows), pd.DataFrame(summ)
keep.to_csv(P / "team_keep_values.csv", index=False)
fit.to_csv(P / "team_fit_matrix.csv", index=False)
fit["gain_per_extra_crore"] = (fit["fit_gain"] / fit["squad_cost_change_crore"].where(fit["squad_cost_change_crore"] > 0.5)).round(1)
tg = fit.sort_values(["team", "fit_gain"], ascending=[True, False]).groupby("team").head(8)
tg.to_csv(P / "team_targets.csv", index=False)
summary.to_csv(P / "team_summary.csv", index=False)

pv = pl[["player", "team", "role_model", "overseas", "age", "price", "value", "has_forecast", "impact_2026"]].copy()
pv["value_per_crore"] = (pv["value"] / pv["price"]).round(1)
fm = pv[pv["has_forecast"]]
coef = np.polyfit(fm["value"], np.log(fm["price"]), 1)
pv["fair_price_crore"] = np.exp(np.polyval(coef, pv["value"])).round(2)
pv["paid_minus_fair"] = (pv["price"] - pv["fair_price_crore"]).round(2)
pv = pv.rename(columns={"price": "price_crore", "value": "forecast_impact_2027", "role_model": "role"}).sort_values("forecast_impact_2027", ascending=False)
pv.to_csv(P / "player_value.csv", index=False)
print(summary.to_string(index=False))
print("correlation of forecast impact with log salary:", round(np.corrcoef(fm["value"], np.log(fm["price"]))[0, 1], 2))
