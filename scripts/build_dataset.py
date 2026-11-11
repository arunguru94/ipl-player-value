"""Build the IPL analysis tables from the Cricsheet ball-by-ball CSV2 download in data/raw/matches.

Run:  .venv-or-any-python -I scripts/build_dataset.py     (from the project root)
Outputs (data/processed): matches, balls, player_registry, batting_innings, bowling_innings, player_career,
player_season, player_venue, venues, team_season, plus one SQLite file ipl.db holding all of them.

Definitions (standard cricket conventions)
  balls faced      : every delivery faced except wides (no-balls count)
  bowler runs      : runs off the bat + wides + no-balls (byes and leg-byes are not charged to the bowler)
  bowler wickets   : all dismissals except run out, retired hurt/out, obstructing the field, timed out (not credited to the bowler)
  legal balls      : deliveries that are neither wides nor no-balls; overs = legal balls / 6
  economy          : runs conceded per over;  strike rate: runs per 100 balls;  average: runs / dismissals (batting), runs / wickets (bowling)
  best bowling     : most wickets in an innings, fewest runs as the tie-break (e.g. 6/12)
Super-over deliveries (innings > 2) are kept in balls.csv but excluded from every player statistic.
"""
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "matches"
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

NOT_BOWLER = {"run out", "retired hurt", "retired out", "obstructing the field", "timed out"}

# ---------------------------------------------------------------- matches + registry
info_rows, reg, squads = [], {}, []
for f in sorted(RAW.glob("*_info.csv")):
    mid = int(f.stem.split("_")[0])
    rec = {"match_id": mid}
    teams, umpires = [], []
    for line in pd.read_csv(f, header=None, names=range(8), dtype=str, keep_default_na=False).itertuples(index=False):
        kind, key = line[0], line[1]
        if kind != "info":
            continue
        if key == "registry":
            reg[line[3]] = line[4]
        elif key == "team":
            teams.append(line[2])
        elif key == "umpire":
            umpires.append(line[2])
        elif key == "player":
            squads.append((mid, line[2], line[3]))
        elif key in ("target_runs", "target_overs"):
            rec[key] = line[3]
        elif key in ("match_id",):
            continue
        else:
            rec.setdefault(key, line[2])
    rec["team1"], rec["team2"] = (teams + ["", ""])[:2]
    rec["umpires"] = "; ".join(umpires)
    info_rows.append(rec)
matches = pd.DataFrame(info_rows)
matches["date"] = pd.to_datetime(matches["date"].str.replace("/", "-"), errors="coerce")
for c in ("winner_runs", "winner_wickets", "target_runs", "target_overs", "match_number"):
    if c in matches:
        matches[c] = pd.to_numeric(matches[c], errors="coerce")
matches["season"] = matches["season"].astype(str).str.slice(0, 4).where(~matches["season"].astype(str).str.contains("/"), matches["season"].astype(str).str.slice(0, 4))
# Cricsheet writes some seasons as "2007/08", "2009/10", "2020/21": the calendar year of the first match is clearer
matches["season"] = matches["date"].dt.year.astype("Int64")
matches = matches.sort_values(["date", "match_id"]).reset_index(drop=True)

# One name per physical ground (Cricsheet spells and renames them over the years). Mullanpur/New Chandigarh is a different ground from Mohali.
GROUND = {   # substring of raw name -> (canonical name, city)
    "Chinnaswamy": ("M Chinnaswamy Stadium", "Bengaluru"),
    "Feroz Shah Kotla": ("Arun Jaitley Stadium (Feroz Shah Kotla)", "Delhi"),
    "Arun Jaitley": ("Arun Jaitley Stadium (Feroz Shah Kotla)", "Delhi"),
    "Sardar Patel": ("Narendra Modi Stadium (Sardar Patel, Motera)", "Ahmedabad"),
    "Narendra Modi": ("Narendra Modi Stadium (Sardar Patel, Motera)", "Ahmedabad"),
    "Maharaja Yadavindra": ("Maharaja Yadavindra Singh Stadium, New Chandigarh (Mullanpur)", "New Chandigarh"),
    "Punjab Cricket Association": ("PCA IS Bindra Stadium, Mohali", "Mohali"),
    "Maharashtra Cricket Association": ("MCA Stadium, Pune (Gahunje)", "Pune"),
    "Subrata Roy": ("MCA Stadium, Pune (Gahunje)", "Pune"),
    "Dr DY Patil": ("Dr DY Patil Sports Academy", "Navi Mumbai"),
    "Chidambaram": ("MA Chidambaram Stadium", "Chennai"),
    "Dubai International": ("Dubai International Cricket Stadium", "Dubai"),
    "Sharjah": ("Sharjah Cricket Stadium", "Sharjah"),
    "Rajiv Gandhi": ("Rajiv Gandhi International Stadium", "Hyderabad"),
    "Brabourne": ("Brabourne Stadium", "Mumbai"),
    "Wankhede": ("Wankhede Stadium", "Mumbai"),
    "Eden Gardens": ("Eden Gardens", "Kolkata"),
}


def ground(v):
    for k, (name, city) in GROUND.items():
        if k in str(v):
            return name, city
    return str(v).split(",")[0].strip(), None


g = matches["venue"].map(ground)
matches["venue_raw"] = matches["venue"]
matches["venue"] = g.map(lambda t: t[0])
matches["city"] = [t[1] or c for t, c in zip(g, matches["city"])]
matches["city"] = matches["city"].fillna(matches["venue"])
squad = pd.DataFrame(squads, columns=["match_id", "team", "player"]).drop_duplicates()
registry = pd.DataFrame(sorted(reg.items()), columns=["player", "player_id"])

# ---------------------------------------------------------------- balls
balls = pd.read_csv(RAW / "all_matches.csv", low_memory=False)
balls["start_date"] = pd.to_datetime(balls["start_date"])
balls["venue"] = balls["match_id"].map(matches.set_index("match_id")["venue"])      # canonical ground name from the match record
for c in ("runs_off_bat", "extras", "wides", "noballs", "byes", "legbyes", "penalty"):
    balls[c] = pd.to_numeric(balls[c], errors="coerce").fillna(0).astype(int)
balls["is_wide"] = balls["wides"] > 0
balls["is_noball"] = balls["noballs"] > 0
balls["legal"] = ~(balls["is_wide"] | balls["is_noball"])
balls["bowler_runs"] = balls["runs_off_bat"] + balls["wides"] + balls["noballs"]
balls["total_runs"] = balls["runs_off_bat"] + balls["extras"]
wt = balls["wicket_type"].fillna("")
balls["is_wicket"] = wt != ""
balls["bowler_wicket"] = balls["is_wicket"] & ~wt.isin(NOT_BOWLER)
balls["over"] = np.floor(pd.to_numeric(balls["ball"], errors="coerce")).astype("Int64")
balls["phase"] = pd.cut(balls["over"].astype(float), [-1, 5, 14, 99], labels=["powerplay", "middle", "death"])
balls["is_four"] = (balls["runs_off_bat"] == 4) & (balls["non_boundary"].fillna(0) == 0)
balls["is_six"] = balls["runs_off_bat"] == 6
balls["is_dot"] = balls["legal"] & (balls["total_runs"] == 0)
reg_map = dict(reg)
balls["striker_id"] = balls["striker"].map(reg_map)
balls["bowler_id"] = balls["bowler"].map(reg_map)

reg_inn = balls[balls["innings"] <= 2].copy()          # regulation innings only (super overs excluded from player stats)

# ---------------------------------------------------------------- batting innings
faced = reg_inn[~reg_inn["is_wide"]]
bat = faced.groupby(["match_id", "innings", "batting_team", "striker"]).agg(
    runs=("runs_off_bat", "sum"), balls=("striker", "size"), fours=("is_four", "sum"), sixes=("is_six", "sum"),
    dots=("is_dot", "sum")).reset_index().rename(columns={"striker": "player"})
# batters who only stood at the non-striker's end or were out without facing a legal ball
ns = reg_inn[["match_id", "innings", "batting_team", "non_striker"]].rename(columns={"non_striker": "player"}).drop_duplicates()
dis = reg_inn[reg_inn["is_wicket"] & reg_inn["player_dismissed"].notna()][["match_id", "innings", "player_dismissed", "wicket_type", "bowler", "fielder_1"]].rename(columns={"player_dismissed": "player"})
dis = dis.drop_duplicates(["match_id", "innings", "player"])
all_bat = pd.concat([bat[["match_id", "innings", "batting_team", "player"]], ns, dis.merge(
    reg_inn[["match_id", "innings", "batting_team"]].drop_duplicates(), on=["match_id", "innings"])[["match_id", "innings", "batting_team", "player"]]]).drop_duplicates(["match_id", "innings", "player"])
batting = all_bat.merge(bat, on=["match_id", "innings", "batting_team", "player"], how="left").merge(dis, on=["match_id", "innings", "player"], how="left")
for c in ("runs", "balls", "fours", "sixes", "dots"):
    batting[c] = batting[c].fillna(0).astype(int)
batting["dismissed"] = batting["wicket_type"].notna()
batting["strike_rate"] = np.where(batting["balls"] > 0, batting["runs"] / batting["balls"].replace(0, np.nan) * 100, np.nan).round(2)
batting = batting.merge(matches[["match_id", "season", "date", "venue", "city"]], on="match_id", how="left")
batting = batting.rename(columns={"batting_team": "team", "bowler": "dismissed_by_bowler", "fielder_1": "dismissed_fielder"})

# ---------------------------------------------------------------- bowling innings
bowl = reg_inn.groupby(["match_id", "innings", "bowling_team", "bowler"]).agg(
    legal_balls=("legal", "sum"), runs=("bowler_runs", "sum"), wickets=("bowler_wicket", "sum"), dots=("is_dot", "sum"),
    wides=("wides", "sum"), noballs=("noballs", "sum"), fours_conceded=("is_four", "sum"), sixes_conceded=("is_six", "sum")).reset_index()
bowl["overs"] = (bowl["legal_balls"] // 6) + (bowl["legal_balls"] % 6) / 10
bowl["economy"] = (bowl["runs"] / (bowl["legal_balls"] / 6)).round(2)
mo = reg_inn[reg_inn["legal"]].groupby(["match_id", "innings", "bowler", "over"])["total_runs"].sum().reset_index()
maidens = (mo.assign(m=(mo["total_runs"] == 0)).groupby(["match_id", "innings", "bowler"])["m"].sum().rename("maidens").reset_index())
bowl = bowl.merge(maidens, on=["match_id", "innings", "bowler"], how="left").fillna({"maidens": 0})
bowl = bowl.merge(matches[["match_id", "season", "date", "venue", "city"]], on="match_id", how="left").rename(columns={"bowling_team": "team", "bowler": "player"})
bowl["figures"] = bowl["wickets"].astype(int).astype(str) + "/" + bowl["runs"].astype(int).astype(str)


def best(g):                                       # most wickets, then fewest runs
    i = g.sort_values(["wickets", "runs"], ascending=[False, True]).iloc[0]
    return i["figures"]


# ---------------------------------------------------------------- career
def career(gb_bat, gb_bowl, keys):
    b = batting.groupby(keys)
    bt = b.agg(bat_innings=("match_id", "size"), runs=("runs", "sum"), balls_faced=("balls", "sum"), fours=("fours", "sum"), sixes=("sixes", "sum"),
               dismissals=("dismissed", "sum"), highest=("runs", "max"),
               fifties=("runs", lambda s: int(((s >= 50) & (s < 100)).sum())), hundreds=("runs", lambda s: int((s >= 100).sum())),
               ducks=("runs", lambda s: 0)).drop(columns="ducks")
    duck = batting[(batting["runs"] == 0) & batting["dismissed"]].groupby(keys).size().rename("ducks")
    bt = bt.join(duck).fillna({"ducks": 0})
    bt["bat_avg"] = (bt["runs"] / bt["dismissals"].replace(0, np.nan)).round(2)
    bt["bat_sr"] = (bt["runs"] / bt["balls_faced"].replace(0, np.nan) * 100).round(2)
    bw = bowl.groupby(keys)
    bo = bw.agg(bowl_innings=("match_id", "size"), legal_balls=("legal_balls", "sum"), runs_conceded=("runs", "sum"), wickets=("wickets", "sum"),
                maidens=("maidens", "sum"), dots_bowled=("dots", "sum"),
                four_wkts=("wickets", lambda s: int((s == 4).sum())), five_wkts=("wickets", lambda s: int((s >= 5).sum())))
    bo["best_bowling"] = bowl.groupby(keys).apply(best, include_groups=False)
    bo["overs"] = (bo["legal_balls"] // 6) + (bo["legal_balls"] % 6) / 10
    bo["economy"] = (bo["runs_conceded"] / (bo["legal_balls"] / 6)).round(2)
    bo["bowl_avg"] = (bo["runs_conceded"] / bo["wickets"].replace(0, np.nan)).round(2)
    bo["bowl_sr"] = (bo["legal_balls"] / bo["wickets"].replace(0, np.nan)).round(1)
    return bt.join(bo, how="outer").reset_index()


played = pd.concat([batting[["match_id", "player", "team"]], bowl[["match_id", "player", "team"]]]).drop_duplicates()
played = pd.concat([played, squad.rename(columns={})]).drop_duplicates(["match_id", "player"])   # squad = playing XI, includes those who neither batted nor bowled
played = played.merge(matches[["match_id", "season", "venue"]], on="match_id")


def add_matches(df, keys):
    m = played.groupby(keys)["match_id"].nunique().rename("matches")
    return m.reset_index().merge(df, on=keys, how="left")


car = add_matches(career(batting, bowl, ["player"]), ["player"])
car["player_id"] = car["player"].map(reg_map)
teams = played.groupby("player")["team"].agg(lambda s: ", ".join(sorted(set(s)))).rename("teams")
span = played.groupby("player")["season"].agg(first_season="min", last_season="max")
motm = matches.groupby("player_of_match").size().rename("player_of_match_awards")
car = car.merge(teams, on="player").merge(span, on="player").merge(motm, left_on="player", right_index=True, how="left")
car["player_of_match_awards"] = car["player_of_match_awards"].fillna(0).astype(int)
catches = reg_inn[reg_inn["wicket_type"].isin(["caught", "caught and bowled", "stumped"])]
c1 = catches.groupby("fielder_1").size().rename("catches_or_stumpings")
car = car.merge(c1, left_on="player", right_index=True, how="left").fillna({"catches_or_stumpings": 0})
lead = ["player", "player_id", "teams", "first_season", "last_season", "matches"]
car = car[lead + [c for c in car.columns if c not in lead]].sort_values("runs", ascending=False)

ps = add_matches(career(batting, bowl, ["player", "season"]), ["player", "season"])
pv = add_matches(career(batting, bowl, ["player", "venue"]), ["player", "venue"])

# ---------------------------------------------------------------- venues + teams
mv = matches.copy()
first = reg_inn[reg_inn["innings"] == 1].groupby("match_id")["total_runs"].sum().rename("first_innings_runs")
mv = mv.merge(first, on="match_id", how="left")
bat_first_win = mv["winner"].notna() & (mv["winner_runs"].notna())
venues = mv.groupby(["venue", "city"], dropna=False).agg(matches=("match_id", "size"), avg_first_innings=("first_innings_runs", "mean"),
                                                         first_season=("season", "min"), last_season=("season", "max")).reset_index()
venues["avg_first_innings"] = venues["avg_first_innings"].round(1)
venues["bat_first_win_pct"] = venues["venue"].map(mv.assign(w=bat_first_win).groupby("venue").apply(lambda g: round(g["w"].sum() / max(g["winner"].notna().sum(), 1) * 100, 1), include_groups=False))
vb = reg_inn.groupby("venue").agg(runs=("total_runs", "sum"), balls=("legal", "sum"), fours=("is_four", "sum"), sixes=("is_six", "sum"), wickets=("bowler_wicket", "sum"))
vb["run_rate"] = (vb["runs"] / (vb["balls"] / 6)).round(2)
venues = venues.merge(vb[["run_rate", "fours", "sixes", "wickets"]], left_on="venue", right_index=True, how="left").sort_values("matches", ascending=False)
team_season = pd.concat([mv.assign(team=mv["team1"]), mv.assign(team=mv["team2"])]).groupby(["season", "team"]).agg(
    matches=("match_id", "size"), wins=("winner", lambda s: 0)).drop(columns="wins").reset_index()
w = matches.groupby(["season", "winner"]).size().rename("wins").reset_index().rename(columns={"winner": "team"})
team_season = team_season.merge(w, on=["season", "team"], how="left").fillna({"wins": 0})
team_season["wins"] = team_season["wins"].astype(int)

# ---------------------------------------------------------------- write
tables = {"matches": matches, "balls": balls.drop(columns=["striker_id", "bowler_id"]), "player_registry": registry, "playing_xi": squad,
          "batting_innings": batting, "bowling_innings": bowl, "player_career": car, "player_season": ps, "player_venue": pv,
          "venues": venues, "team_season": team_season}
db = sqlite3.connect(OUT / "ipl.db")
for name, df in tables.items():
    df = df.copy()
    for c in df.columns:
        if str(df[c].dtype) == "category":
            df[c] = df[c].astype(str)
    df.to_csv(OUT / f"{name}.csv", index=False)
    df.to_sql(name, db, if_exists="replace", index=False)
    print(f"{name:16s} {len(df):>8,} rows  {len(df.columns):>3} columns")
db.close()
