"""Verified record of player trades between IPL franchises, up to 11 Nov 2026, and the 'current team' after them.

Trade data is entered by hand from the sources named in each row (checked 11 Nov 2026); it is not scraped, because the later deals are only
reported in news coverage. Fees are in rupees crore. Rumoured or "agreed in principle" deals are kept in the separate pending table, never in the trade table.

Outputs: data/processed/trades_all.csv, trades_pending.csv; adds current_team and 2027-cycle trade columns to players_2026.csv and ipl.db.
Run after build_players.py:  python -I scripts/build_trades.py
"""
import sqlite3
from pathlib import Path

import pandas as pd

PROC = Path(__file__).resolve().parents[1] / "data" / "processed"
W = "Nov 2025 window (for IPL 2026)"
N = "Pre-IPL 2027 trades"
COLS = ["window", "date", "player", "from_team", "to_team", "fee_crore", "previous_fee_crore", "deal", "status", "confidence", "sources"]
WIKI = "Wikipedia 'List of 2026 IPL personnel changes'"
rows = [
    # ---- trades agreed in the Nov 2025 window (all announced by the BCCI on 13-15 Nov 2025)
    (W, "2025-11-13", "Shardul Thakur", "Lucknow Super Giants", "Mumbai Indians", 2.0, None, "Shardul Thakur for cash", "Completed", "High", f"{WIKI}; cricket.com; Wisden trades list"),
    (W, "2025-11-13", "Sherfane Rutherford", "Gujarat Titans", "Mumbai Indians", 2.6, None, "Rutherford for cash", "Completed", "Medium", f"{WIKI}; listed among moves in press coverage (destination checked on Wikipedia only)"),
    (W, "2025-11-13", "Ravindra Jadeja", "Chennai Super Kings", "Rajasthan Royals", 14.0, None, "Samson for Jadeja + Curran", "Completed", "High", f"{WIKI}; Telangana Today; Sportskeeda (BCCI announcement); Outlook India"),
    (W, "2025-11-13", "Sam Curran", "Chennai Super Kings", "Rajasthan Royals", 2.4, None, "Samson for Jadeja + Curran", "Completed", "High", f"{WIKI}; Sportskeeda (BCCI announcement); Outlook India"),
    (W, "2025-11-13", "Sanju Samson", "Rajasthan Royals", "Chennai Super Kings", 18.0, None, "Samson for Jadeja + Curran", "Completed", "High", f"{WIKI}; Telangana Today; Sportskeeda (BCCI announcement); Outlook India"),
    (W, "2025-11-15", "Mohammed Shami", "Sunrisers Hyderabad", "Lucknow Super Giants", 10.0, None, "Shami for cash", "Completed", "High", f"{WIKI}; Rozana Spokesman (cites Economic Times); Outlook India"),
    (W, "2025-11-15", "Donovan Ferreira", "Delhi Capitals", "Rajasthan Royals", 1.0, None, "Ferreira for Rana", "Completed", "High", f"{WIKI}; Sportskeeda (BCCI announcement); DNA India"),
    (W, "2025-11-15", "Nitish Rana", "Rajasthan Royals", "Delhi Capitals", 4.2, None, "Ferreira for Rana", "Completed", "High", f"{WIKI}; Sportskeeda (BCCI announcement); DNA India"),
    (W, "2025-11-15", "Mayank Markande", "Kolkata Knight Riders", "Mumbai Indians", 0.3, None, "Markande for cash", "Completed", "High", f"{WIKI}; DNA India; Bizzbuzz"),
    (W, "2025-11-15", "Arjun Tendulkar", "Mumbai Indians", "Lucknow Super Giants", 0.3, None, "Tendulkar for cash", "Completed", "High", f"{WIKI}; DNA India; Bizzbuzz"),
    # ---- trades for IPL 2027 (made after the 2026 season began; no BCCI primary page was readable, so status comes from multiple outlets)
    (N, "2026-06-23", "Rishabh Pant", "Lucknow Super Giants", "Delhi Capitals", 15.0, 27.0, "Pant for Kuldeep", "Completed", "Medium",
     "Cricinfo 'LSG and DC complete' (headline seen in search; page blocked); Outlook India; Yahoo/Cricket News tracker (says signed off by the IPL governing council; date from a DC post of 23 Jun 2026)"),
    (N, "2026-06-23", "Kuldeep Yadav", "Delhi Capitals", "Lucknow Super Giants", 13.5, 13.5, "Pant for Kuldeep", "Completed", "Medium", "same as Pant"),
    (N, "2026-10-14", "T Natarajan", "Delhi Capitals", "Sunrisers Hyderabad", 5.0, 10.75, "Natarajan for Ansari", "Completed", "Medium", "Yahoo/Cricket News tracker (completed, no date); trade-tracker sites give 14 Oct 2026; a single dated source"),
    (N, "2026-10-14", "Zeeshan Ansari", "Sunrisers Hyderabad", "Delhi Capitals", 0.4, None, "Natarajan for Ansari", "Completed", "Medium", "same as Natarajan"),
    (N, "2026-11-05", "Liam Livingstone", "Sunrisers Hyderabad", "Chennai Super Kings", 6.0, 13.0, "4-player swap CSK-SRH", "Completed", "High", "chennaisuperkings.com (official); Yahoo Sports; Daily Pioneer (PTI); Yardbarker"),
    (N, "2026-11-05", "Jack Edwards", "Sunrisers Hyderabad", "Chennai Super Kings", 3.0, 3.0, "4-player swap CSK-SRH", "Completed", "High", "same as Livingstone"),
    (N, "2026-11-05", "Khaleel Ahmed", "Chennai Super Kings", "Sunrisers Hyderabad", 4.8, 4.8, "4-player swap CSK-SRH", "Completed", "High", "same as Livingstone"),
    (N, "2026-11-05", "Nathan Ellis", "Chennai Super Kings", "Sunrisers Hyderabad", 2.0, 2.0, "4-player swap CSK-SRH", "Completed", "High", "same as Livingstone"),
    (N, "2026-11-11", "Hardik Pandya", "Mumbai Indians", "Punjab Kings", 18.0, 16.5, "Hardik for Arshdeep", "Completed (announced 11 Nov)", "Medium-High",
     "Outlook India ('officially complete'); SportsTak ('official'); Yahoo Sports; Onmanorama. Earlier Cricinfo report 7 Nov said 'set to trade'. Previous fee reported as 16.35 or 16.5 crore"),
    (N, "2026-11-11", "Arshdeep Singh", "Punjab Kings", "Mumbai Indians", 18.0, 18.0, "Hardik for Arshdeep", "Completed (announced 11 Nov)", "Medium-High", "same as Hardik"),
]
trades = pd.DataFrame(rows, columns=COLS)
trades["date"] = pd.to_datetime(trades["date"])
trades.to_csv(PROC / "trades_all.csv", index=False)

pending = pd.DataFrame([
    ("LSG and RR", "3 or 4 player swap, players not named", "Agreed in principle (Cricbuzz via Yahoo tracker)", "Not a trade yet"),
    ("Sam Curran (RCB) / Romario Shepherd (RR)", "possible swap", "Rumour", "Not a trade yet"),
    ("Urvil Patel (CSK) to GT", "possible swap involving Washington Sundar or Sai Kishore", "Rumour", "Not a trade yet"),
    ("Nihal Wadhera (GT) / Gurnoor Brar (PBKS)", "possible swap", "Exploring", "Not a trade yet"),
    ("Axar Patel (DC) to CSK", "rumour", "Denied by the DC co-owner", "Not a trade yet"),
    ("Yashasvi Jaiswal (RR) to LSG", "rumour", "Unconfirmed", "Not a trade yet"),
    ("Ashutosh Sharma (DC) to GT or LSG", "possible", "Sources contradict each other", "Not a trade yet"),
    ("Harshal Patel (GT) to SRH", "cash deal or swap with Tom Banton", "Early talks", "Not a trade yet"),
    ("Suryakumar Yadav (MI) to KKR", "interest reported", "Early", "Not a trade yet"),
    ("Jason Holder (GT) to KKR", "KKR approached", "GT declined", "No deal"),
    ("Abhishek Sharma (SRH) exit", "talk", "Denied by the SRH CEO", "No deal"),
], columns=["players", "what", "reported_status", "recorded_as"])
pending.to_csv(PROC / "trades_pending.csv", index=False)

# ---- current team after every completed trade
pl = pd.read_csv(PROC / "players_2026.csv")
key = lambda x: x.str.lower().str.replace(r"[^a-z ]", "", regex=True).str.strip()      # "T. Natarajan" == "T Natarajan"
pl["_k"] = key(pl["player"])
n = trades[trades["window"] == N].assign(_k=lambda d: key(d["player"])).set_index("_k")
pl["current_team"] = pl["team"]
pl["trade_2027_date"] = pl["_k"].map(n["date"].dt.strftime("%Y-%m-%d"))
pl["trade_2027_from"] = pl["_k"].map(n["from_team"])
pl["trade_2027_to"] = pl["_k"].map(n["to_team"])
pl["trade_2027_fee_crore"] = pl["_k"].map(n["fee_crore"])
moved = pl["trade_2027_to"].notna()
chk = pl[moved & (pl["trade_2027_from"] != pl["team"])]
assert chk.empty, chk[["player", "team", "trade_2027_from"]]       # every 2027 trade must start from the player's 2026 team
pl.loc[moved, "current_team"] = pl.loc[moved, "trade_2027_to"]
pl["traded_since_2026_season"] = moved
pl = pl.drop(columns="_k")
pl.to_csv(PROC / "players_2026.csv", index=False)
db = sqlite3.connect(PROC / "ipl.db")
pl.to_sql("players_2026", db, if_exists="replace", index=False)
trades.to_sql("trades_all", db, if_exists="replace", index=False)
pending.to_sql("trades_pending", db, if_exists="replace", index=False)
db.close()

# ---- checks
ok2026 = trades[trades["window"] == W]
p26 = pl[pl["traded_in_2025_window"]].set_index("player")
bad = [(r.player, r.to_team, p26.at[r.player, "traded_to"]) for r in ok2026.itertuples() if r.player in p26.index and p26.at[r.player, "traded_to"] != r.to_team]
print(f"trades recorded: {len(trades)} ({len(ok2026)} in Nov 2025 window, {len(trades) - len(ok2026)} since); disagreements with players_2026: {bad}")
print("2025-window trades checked against players_2026 team/fee:",
      all(abs(p26.at[r.player, "trade_price_lakh"] / 100 - r.fee_crore) < 0.01 for r in ok2026.itertuples()))
print("players with a new team for 2027:", int(pl["traded_since_2026_season"].sum()), "of", len(trades) - len(ok2026), "traded; not in a 2026 squad:", sorted(set(n.index) - set(key(pl["player"]))))
print(pl[pl["traded_since_2026_season"]][["player", "team", "current_team", "trade_2027_fee_crore"]].to_string())
print(pl.groupby("current_team").size().to_dict())
