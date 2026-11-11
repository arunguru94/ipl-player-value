"""Current-squad table: every player in a 2026 IPL squad with price, how they were acquired, trade, age, role, team and IPL stats.

Inputs : data/raw/wikipedia/*.json  (Wikipedia pages saved 11 Nov 2026, see README for URLs)
         data/processed/player_career.csv, balls.csv   (built by build_dataset.py)
Output : data/processed/players_2026.csv (+ table players_2026 in ipl.db), data/processed/trades_2026.csv, auction_2026.csv

Run:  python -I scripts/build_players.py     (after build_dataset.py)
"""
import io
import json
import re
import sqlite3
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
WIKI = ROOT / "data" / "raw" / "wikipedia"
PROC = ROOT / "data" / "processed"
TODAY = date(2026, 11, 11)

TEAMS = {   # page slug -> team name (as used on the personnel-changes page)
    "Chennai_Super_Kings": "Chennai Super Kings", "Delhi_Capitals": "Delhi Capitals", "Gujarat_Titans": "Gujarat Titans",
    "Kolkata_Knight_Riders": "Kolkata Knight Riders", "Lucknow_Super_Giants": "Lucknow Super Giants", "Mumbai_Indians": "Mumbai Indians",
    "Punjab_Kings": "Punjab Kings", "Rajasthan_Royals": "Rajasthan Royals", "Royal_Challengers_Bengaluru": "Royal Challengers Bengaluru",
    "Sunrisers_Hyderabad": "Sunrisers Hyderabad"}
RETAINED_ORDER = ["Chennai Super Kings", "Delhi Capitals", "Gujarat Titans", "Kolkata Knight Riders", "Lucknow Super Giants",
                  "Mumbai Indians", "Punjab Kings", "Rajasthan Royals", "Royal Challengers Bengaluru", "Sunrisers Hyderabad"]


def norm(s):
    s = re.sub(r"\[.*?\]|[†*]", "", str(s))
    return re.sub(r"[^a-z ]", "", s.lower().replace(".", " ")).strip().replace("  ", " ")


ALIAS = {"aman khan": "aman hakim khan", "sahil parekh": "sahil parakh", "harnoor pannu": "harnoor singh"}   # same person, spelled differently on the two pages


def lakh(s):
    m = re.search(r"₹\s*([\d.]+)\s*(crore|lakh)", str(s))
    if not m:
        return np.nan
    v = float(m.group(1))
    return v * 100 if m.group(2) == "crore" else v


def tables(path):
    out = pd.read_html(io.StringIO(json.load(open(path))["parse"]["text"]))
    for t in out:                                                   # Wikipedia uses non-breaking spaces in headers and cells
        t.columns = [c.replace("\xa0", " ") if isinstance(c, str) else c for c in t.columns]
    return out


# ------------------------------------------------------------------ personnel-changes page
T = tables(WIKI / "personnel_changes_2026.json")
trades = next(t for t in T if list(t.columns)[:3] == ["Date", "Name", "Salary"]).drop(columns="Ref.")
trades["price_lakh"] = trades["Salary"].map(lakh)
trades = trades.rename(columns={"Date": "trade_date", "Name": "player", "From": "from_team", "To": "to_team"})[["trade_date", "player", "from_team", "to_team", "price_lakh"]]

ret_tabs = [t for t in T if list(t.columns) == ["No.", "Player", "Nationality", "Salary"]]
assert len(ret_tabs) == 10, len(ret_tabs)
retained = pd.concat([t.assign(team=n) for t, n in zip(ret_tabs, RETAINED_ORDER)])
retained["retention_price_lakh"] = retained["Salary"].map(lakh)
retained = retained.rename(columns={"Player": "player"})[["player", "team", "retention_price_lakh"]]

auc = [t for t in T if "Auctioned price (₹ lakhs)" in map(str, t.columns)]
auction = pd.concat(auc, ignore_index=True)
auction = auction.rename(columns={"Name": "player", "Country": "country", "Role": "role_wiki", "Base price (₹ lakhs)": "base_price_lakh",
                                  "2026 IPL team": "bought_by", "Auctioned price (₹ lakhs)": "auction_price_lakh", "2025 IPL team": "team_2025",
                                  "No. of IPL matches": "ipl_matches_before", "Category": "category"})
auction = auction.sort_values("role_wiki", na_position="last").drop_duplicates("player")
for c in ("base_price_lakh", "auction_price_lakh"):
    auction[c] = pd.to_numeric(auction[c], errors="coerce")
auction["team_2025"] = auction["team_2025"].replace("—N/a", np.nan)
auction = auction[["player", "country", "role_wiki", "category", "base_price_lakh", "auction_price_lakh", "bought_by", "team_2025", "ipl_matches_before"]]

# ------------------------------------------------------------------ squads
rows = []
for slug, team in TEAMS.items():
    sq = next(t for t in tables(WIKI / f"2026_{slug}_season.json") if "Birth date" in map(str, t.columns))
    sq = sq.copy()
    sq["withdrawn"] = sq["Name"].str.contains("†")
    sq["player"] = sq["Name"].str.replace(r"[†*]|\[.*?\]", "", regex=True).str.strip()
    sq["team"] = team
    rows.append(sq)
sq = pd.concat(rows, ignore_index=True)
sq["dob"] = pd.to_datetime(sq["Birth date"].str.extract(r"^(\d{1,2} \w+ \d{4})")[0], format="%d %B %Y", errors="coerce")
sq["age"] = sq["dob"].map(lambda d: TODAY.year - d.year - ((TODAY.month, TODAY.day) < (d.month, d.day)) if pd.notna(d) else np.nan)
sq["salary_lakh"] = sq["Salary"].map(lakh)
sq["notes"] = sq["Notes"].fillna("").str.replace(r"\[.*?\]", "", regex=True).str.strip()
sq["overseas"] = sq["notes"].str.contains("Overseas") | ~sq["Nationality"].eq("India")
sq["is_replacement"] = sq["notes"].str.contains("eplacement")
sq["is_captain"] = sq["notes"].str.contains("Captain")
sq = sq.rename(columns={"Nationality": "nationality", "Batting style": "batting_style", "Bowling style": "bowling_style", "S/N": "jersey_no"})
sq["bowling_style"] = sq["bowling_style"].replace("—N/a", np.nan)

# ------------------------------------------------------------------ acquisition: how each player joined and at what price
sq["_k"] = sq["player"].map(norm)
for d, c in ((trades, "player"), (retained, "player"), (auction, "player")):
    d["_k"] = d[c].map(norm).replace(ALIAS)
tr = trades.rename(columns={"from_team": "traded_from", "to_team": "traded_to", "trade_date": "trade_date", "price_lakh": "trade_price_lakh"}).drop(columns="player")
au = auction.drop(columns="player").rename(columns={"team_2025": "team_2025_auction"})
rt = retained.rename(columns={"team": "retained_by"}).drop(columns="player")
sq = sq.merge(tr, on="_k", how="left").merge(au, on="_k", how="left").merge(rt, on="_k", how="left")
sq["acquired_via"] = np.select(
    [sq["traded_to"].notna() & (sq["traded_to"] == sq["team"]),
     sq["bought_by"].notna() & (sq["bought_by"] == sq["team"]),
     sq["retained_by"].notna() & (sq["retained_by"] == sq["team"]),
     sq["is_replacement"]],
    ["Trade (Nov 2025)", "Auction (16 Dec 2025)", "Retained", "Replacement signing 2026"], default="Other / not matched")
sq["price_2026_lakh"] = sq["salary_lakh"]                      # the contract value that season
sq["price_2026_crore"] = (sq["price_2026_lakh"] / 100).round(2)
sq["auction_price_crore"] = (sq["auction_price_lakh"] / 100).round(2)
sq["base_price_crore"] = (sq["base_price_lakh"] / 100).round(2)
sq["team_2025"] = sq["team_2025_auction"]                       # previous team only known for auction buys; fill below from trade/retention
sq.loc[sq["team_2025"].isna() & sq["traded_from"].notna(), "team_2025"] = sq["traded_from"]
sq.loc[sq["team_2025"].isna() & (sq["acquired_via"] == "Retained"), "team_2025"] = sq["team"]
sq["traded_in_2025_window"] = sq["traded_to"].notna()

# ------------------------------------------------------------------ IPL history from Cricsheet -> stats + derived role
car = pd.read_csv(PROC / "player_career.csv")
balls = pd.read_csv(PROC / "balls.csv", usecols=["wicket_type", "fielder_1"])
stump = balls[balls["wicket_type"] == "stumped"].groupby("fielder_1").size().rename("stumpings")
car = car.merge(stump, left_on="player", right_index=True, how="left").fillna({"stumpings": 0})
car["_first"] = car["player"].str.split().str[0].str.upper()
car["_last"] = car["player"].str.split().str[-1].map(norm)
car["_ini"] = car["_first"].str[0]


FRANCHISE = lambda t: ("RCB" if "Royal Challengers" in t else "DC" if "Delhi" in t else "PBKS" if "Punjab" in t else t)
xi = pd.read_csv(PROC / "playing_xi.csv").merge(pd.read_csv(PROC / "matches.csv", usecols=["match_id", "season"]), on="match_id")
xi["fr"] = xi["team"].map(FRANCHISE)
appear = xi.groupby(["player", "fr"])["season"].agg(list).to_dict()          # (cricsheet name, franchise) -> seasons played
OVERRIDE = {"Varun Chakravarthy": "CV Varun"}                                  # Cricsheet spells a few names unlike Wikipedia


def find(row):
    name, team, team25 = row["player"], FRANCHISE(row["team"]), row["team_2025"]
    team25 = FRANCHISE(team25) if isinstance(team25, str) else None
    if name in OVERRIDE:
        return OVERRIDE[name], "ok (manual)"
    wt = norm(name).split()
    cand = []
    for cn in car["player"]:
        ct = norm(cn).split()
        if not ct or ct[-1] != wt[-1] and not (set(wt) <= set(ct)):
            continue
        first_raw = cn.split()[0]
        is_initials = first_raw.isupper()                              # "YBK", "RG": initials, not a first name
        if set(wt) <= set(ct):
            pass
        elif is_initials and ct[0][0] != wt[0][0]:
            continue
        elif not is_initials and ct[0] != wt[0]:                       # Cricsheet gives a full first name: it must agree
            continue
        cand.append(cn)
    ok = []
    for cn in cand:
        recent_now = [y for y in appear.get((cn, team), []) if y >= 2025]
        recent_prev = [y for y in appear.get((cn, team25), []) if y >= 2025] if team25 else []
        if recent_now or recent_prev:
            ok.append((cn, 2026 in appear.get((cn, team), []), len(recent_now) + len(recent_prev)))
    if not ok:
        return None, "no IPL appearance for this franchise in 2025-26"
    ok.sort(key=lambda t: (t[1], t[2]), reverse=True)
    return ok[0][0], "ok" if len(ok) == 1 else "ok (picked best of %d)" % len(ok)


m = sq.apply(find, axis=1)
sq["ipl_name"] = [x[0] for x in m]
sq["ipl_history_match"] = [x[1] for x in m]
# Cricsheet initials ("RK Singh") can fit two squad-mates; give the record to the higher-paid (more established) one and flag the other
dup = sq["ipl_name"].notna() & sq.duplicated(["ipl_name", "team"], keep=False) & (sq["ipl_history_match"] != "ok (manual)")
keep_idx = sq[dup].sort_values("salary_lakh", ascending=False).drop_duplicates(["ipl_name", "team"]).index
lose = sq[dup].index.difference(keep_idx)
sq.loc[lose, "ipl_name"] = None
sq.loc[lose, "ipl_history_match"] = "no IPL history (name clash with a team-mate)"
keep = ["player", "matches", "runs", "bat_avg", "bat_sr", "hundreds", "fifties", "wickets", "economy", "bowl_avg", "best_bowling", "legal_balls",
        "balls_faced", "bat_innings", "stumpings", "first_season", "player_of_match_awards"]
st = car[keep].rename(columns={"player": "ipl_name", "matches": "ipl_matches", "runs": "ipl_runs", "bat_avg": "ipl_bat_avg", "bat_sr": "ipl_bat_sr",
                               "hundreds": "ipl_100s", "fifties": "ipl_50s", "wickets": "ipl_wickets", "economy": "ipl_economy", "bowl_avg": "ipl_bowl_avg",
                               "best_bowling": "ipl_best_bowling", "first_season": "ipl_debut_season", "player_of_match_awards": "ipl_pom_awards",
                               "legal_balls": "_bowled", "balls_faced": "_faced", "bat_innings": "_inn", "stumpings": "_stump"})
sq = sq.merge(st, on="ipl_name", how="left")


INTRO = json.load(open(WIKI / "player_intros.json")) if (WIKI / "player_intros.json").exists() else {}


def wiki_role(name):
    """Role from the first sentence of the player's Wikipedia article (only if the page is about a cricketer)."""
    t = INTRO.get(name, {}).get("extract", "")
    if "cricket" not in t.lower():
        return None
    t = t.lower()
    if "wicket-keeper" in t or "wicketkeeper" in t:
        return "Wicket-keeper batter"
    if "all-rounder" in t or "allrounder" in t:
        return "All-rounder"
    pos = {k: min([t.find(w) for w in ws if w in t] or [10**6]) for k, ws in
           {"Batter": ("batter", "batsman", "opener", "top-order", "middle-order"),
            "Bowler": ("bowler", "spinner", "seamer", "pace", "fast", "spin")}.items()}
    k = min(pos, key=pos.get)
    return k if pos[k] < 10**6 else None


def derive(r):
    if isinstance(r["role_wiki"], str) and r["role_wiki"]:
        return r["role_wiki"], "Wikipedia auction list"
    w = wiki_role(r["player"])
    if w:
        return w, "Wikipedia article"
    if pd.isna(r["ipl_matches"]):
        return ("Batter", "no bowling style listed") if pd.isna(r["bowling_style"]) else ("Unknown", "no IPL history")
    bowled, faced, runs = (r["_bowled"] or 0), (r["_faced"] or 0), (r["ipl_runs"] or 0)
    if (r["_stump"] or 0) >= 5:
        return "Wicket-keeper batter", "IPL stumpings"
    if bowled >= 300 and runs >= 500 and (r["_inn"] or 0) >= 25:
        return "All-rounder", "derived from IPL record"
    if bowled >= 300 or (bowled >= 120 and faced < 300):
        return "Bowler", "derived from IPL record"
    if faced >= 150:
        return "Batter", "derived from IPL record"
    return "Unknown", "too little IPL data"


d = sq.apply(derive, axis=1)
sq["role"], sq["role_source"] = [x[0] for x in d], [x[1] for x in d]
sq["role"] = sq["role"].replace({"Batter": "Batter", "Wicket-keeper": "Wicket-keeper batter"})

cols = ["player", "team", "age", "dob", "role", "role_source", "nationality", "overseas", "is_captain", "batting_style", "bowling_style", "jersey_no",
        "price_2026_crore", "price_2026_lakh", "acquired_via", "auction_price_crore", "base_price_crore", "category", "team_2025",
        "traded_in_2025_window", "traded_from", "traded_to", "trade_date", "trade_price_lakh", "retained_by", "retention_price_lakh",
        "is_replacement", "withdrawn", "notes", "ipl_name", "ipl_history_match", "ipl_debut_season", "ipl_matches", "ipl_runs", "ipl_bat_avg", "ipl_bat_sr",
        "ipl_100s", "ipl_50s", "ipl_wickets", "ipl_economy", "ipl_bowl_avg", "ipl_best_bowling", "ipl_pom_awards"]
out = sq[cols].sort_values(["team", "price_2026_lakh"], ascending=[True, False])
out.to_csv(PROC / "players_2026.csv", index=False)
trades.drop(columns="_k").to_csv(PROC / "trades_2026.csv", index=False)
auction.drop(columns="_k").to_csv(PROC / "auction_2026.csv", index=False)
db = sqlite3.connect(PROC / "ipl.db")
out.to_sql("players_2026", db, if_exists="replace", index=False)
trades.drop(columns="_k").to_sql("trades_2026", db, if_exists="replace", index=False)
auction.drop(columns="_k").to_sql("auction_2026", db, if_exists="replace", index=False)
db.close()

# ------------------------------------------------------------------ checks
print(f"{len(out)} players in 10 squads;", out.groupby("team").size().to_dict())
print("acquired_via:", out["acquired_via"].value_counts().to_dict())
print("role:", out["role"].value_counts().to_dict(), "| role_source:", out["role_source"].value_counts().to_dict())
print("IPL history match:", out["ipl_history_match"].value_counts().to_dict())
print("missing age:", int(out["age"].isna().sum()), "| missing price:", int(out["price_2026_lakh"].isna().sum()))
print(f"auction rows {len(auction)}, auction buys found in squads: {int((out['acquired_via'] == 'Auction (16 Dec 2025)').sum())}; trades {len(trades)} found {int(out['traded_in_2025_window'].sum())}")
print("auction buys not in a squad:", sorted(set(auction['_k']) - set(sq['_k']))[:20])
print("retained not in a squad:", sorted(set(retained['_k']) - set(sq['_k'])))
