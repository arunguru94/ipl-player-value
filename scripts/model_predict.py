"""Step 2: predict each player's NEXT-season impact (runs above average) and test it honestly.

Walk-forward test: for each season T from 2013 to 2025, train only on (season t -> season t+1) pairs with t+1 <= T-1... i.e. nothing from season T or later,
then predict season T from the features of season T-1 and score against what really happened. Baselines: last season's impact, the mean of the last 3
seasons, and a constant. A player who does not play in the target season has impact 0 (that is part of what is being predicted).

Outputs: data/processed/impact_forecast_2027.csv, forecast_backtest.csv, forecast_backtest_summary.json
Run:  python -I scripts/model_predict.py        (after model_impact.py and build_players.py)
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import RidgeCV

P = Path(__file__).resolve().parents[1] / "data" / "processed"
imp = pd.read_csv(P / "player_season_impact.csv")
FIRST = imp[imp["matches"] > 0].groupby("player")["season"].min()

wide = imp.pivot_table(index="player", columns="season", values="impact", fill_value=0.0)
mwide = imp.pivot_table(index="player", columns="season", values="matches", fill_value=0.0)
bat_w = imp.pivot_table(index="player", columns="season", values="bat_raa", fill_value=0.0)
bowl_w = imp.pivot_table(index="player", columns="season", values="bowl_raa", fill_value=0.0)
faced_w = imp.pivot_table(index="player", columns="season", values="balls", fill_value=0.0)
bowled_w = imp.pivot_table(index="player", columns="season", values="legal", fill_value=0.0)
SEASONS = sorted(wide.columns)
FEATS = ["imp1", "imp2", "imp3", "per_match1", "m1", "m2", "bat1", "bowl1", "bat_share_balls", "bowl_share_balls", "exp", "wmean3"]


def features(t):
    """Features of every player who played at least 3 matches in season t, using only seasons <= t."""
    idx = mwide.index[mwide[t] >= 3]
    g = lambda w, k: w.reindex(idx)[t - k] if (t - k) in w.columns else pd.Series(0.0, index=idx)
    X = pd.DataFrame(index=idx)
    X["imp1"], X["imp2"], X["imp3"] = g(wide, 0), g(wide, 1), g(wide, 2)
    X["m1"], X["m2"] = g(mwide, 0), g(mwide, 1)
    X["per_match1"] = X["imp1"] / X["m1"].clip(lower=1)
    X["bat1"], X["bowl1"] = g(bat_w, 0), g(bowl_w, 0)
    fb, bw = g(faced_w, 0), g(bowled_w, 0)
    X["bat_share_balls"], X["bowl_share_balls"] = fb / 400.0, bw / 300.0
    X["exp"] = t - FIRST.reindex(idx).values
    X["wmean3"] = (0.5 * X["imp1"] + 0.3 * X["imp2"] + 0.2 * X["imp3"])
    return X[FEATS]


def pairs(first_t, last_t):
    rows = []
    for t in range(first_t, last_t + 1):
        if t + 1 > SEASONS[-1]:
            break
        X = features(t)
        X["y"] = wide[t + 1].reindex(X.index).fillna(0.0).values
        X["season_t"] = t
        rows.append(X)
    return pd.concat(rows)


def fit(df):
    ridge = RidgeCV(alphas=np.logspace(-1, 3, 20)).fit(df[FEATS], df["y"])
    hgb = HistGradientBoostingRegressor(max_depth=3, learning_rate=0.05, max_iter=150, min_samples_leaf=30, l2_regularization=5.0, random_state=0).fit(df[FEATS], df["y"])
    return ridge, hgb


FIRST_TEST = 2013
res = []
for T in range(FIRST_TEST, SEASONS[-1] + 1):
    train = pairs(SEASONS[0] + 2, T - 2)                      # features from t <= T-2 so their targets (t+1 <= T-1) are known before season T
    test = features(T - 1)
    test["y"] = wide[T].reindex(test.index).fillna(0.0).values
    if len(train) < 150:
        continue
    ridge, hgb = fit(train)
    out = test[["y"]].copy()
    out["ridge"], out["hgb"] = ridge.predict(test[FEATS]), hgb.predict(test[FEATS])
    out["blend"] = (out["ridge"] + out["hgb"]) / 2
    out["last"], out["mean3"] = test["imp1"], test["wmean3"]
    out["season"] = T
    res.append(out.reset_index())
bt = pd.concat(res)
bt.to_csv(P / "forecast_backtest.csv", index=False)

rows = []
for name in ("blend", "ridge", "hgb", "last", "mean3"):
    per = bt.groupby("season").apply(lambda d: spearmanr(d[name], d["y"])[0], include_groups=False)
    mae = (bt[name] - bt["y"]).abs().mean()
    top = bt.groupby("season").apply(lambda d: len(set(d.nlargest(20, name).index) & set(d.nlargest(20, "y").index)) / 20, include_groups=False)
    corr = np.corrcoef(bt[name], bt["y"])[0, 1]
    rows.append({"model": name, "rank_corr_mean": per.mean(), "rank_corr_se": per.std() / np.sqrt(len(per)), "pearson": corr, "mae": mae, "top20_hit": top.mean(), "seasons": len(per)})
summary = pd.DataFrame(rows).set_index("model")
summary.loc["constant"] = {"rank_corr_mean": 0, "rank_corr_se": 0, "pearson": 0, "mae": (bt["y"] - bt["y"].mean()).abs().mean(), "top20_hit": 20 / bt.groupby("season").size().mean(), "seasons": len(per)}
print(summary.round(3).to_string())
# is the improvement over the 'last season' baseline real? paired by season
for a, b in (("blend", "last"), ("blend", "mean3")):
    d = bt.groupby("season").apply(lambda x: spearmanr(x[a], x["y"])[0] - spearmanr(x[b], x["y"])[0], include_groups=False)
    print(f"{a} minus {b}: mean rank-corr gain {d.mean():+.3f}  (SE {d.std() / np.sqrt(len(d)):.3f}, {int((d > 0).sum())}/{len(d)} seasons better)")
sd = float((bt["blend"] - bt["y"]).std())
print(f"residual SD of a forecast: {sd:.0f} runs of impact")

# ---- final model on every known pair, applied to season 2026 -> 2027
train = pairs(SEASONS[0] + 2, SEASONS[-1] - 1)
ridge, hgb = fit(train)
X26 = features(SEASONS[-1])
f = pd.DataFrame({"pred_impact_2027": (ridge.predict(X26[FEATS]) + hgb.predict(X26[FEATS])) / 2}, index=X26.index)
f["impact_2026"], f["impact_2025"], f["matches_2026"] = X26["imp1"], X26["imp2"], X26["m1"]
f["forecast_sd"] = sd
f.reset_index().rename(columns={"index": "ipl_name"}).to_csv(P / "impact_forecast_2027.csv", index=False)
summary.to_json(P / "forecast_backtest_summary.json", indent=1)
print(f"forecast for {len(f)} players who played 3+ matches in 2026; top 10:")
print(f.nlargest(10, "pred_impact_2027").round(0).to_string())
