# IPL player-value model

Ball-by-ball IPL data (2008 to 2026) turned into player, ground and squad tables, a next-season player forecast, and a per-team squad optimiser that respects the IPL rules and the auction purse. Results and caveats are in [IPL_MODEL.md](IPL_MODEL.md). Code is MIT-licensed; the data keeps its own licences (see [DATA_SOURCES.md](DATA_SOURCES.md)).

Ball-by-ball IPL data (2008 to 2026, 1,243 matches, 295,732 deliveries) turned into player, match and ground tables.

**Data source:** Cricsheet (https://cricsheet.org), file `ipl_csv2.zip` downloaded 11 Nov 2026 (last updated by the source 3 Nov 2026).
Licence: ODC Attribution License (ODC-By), so credit Cricsheet whenever you share results. The original files are in `data/raw/`.

## Rebuild
```
python scripts/build_dataset.py        # reads data/raw/matches, writes data/processed (CSV + ipl.db)
```
To refresh: download the newest `ipl_csv2.zip` from https://cricsheet.org/downloads/ into `data/raw/`, unzip it into `data/raw/matches`, run the script.

## Tables (`data/processed/*.csv`, also all in `ipl.db`)
| Table | One row per | Key columns |
|---|---|---|
| `matches` | match | season, date, venue, city, teams, toss, winner, win margin, player of the match, umpires, target |
| `balls` | delivery | batter, bowler, runs, extras, wicket type, phase (powerplay/middle/death), four/six/dot flags |
| `batting_innings` | player innings | runs, balls, 4s, 6s, strike rate, how out, bowler who got them |
| `bowling_innings` | player spell | overs, runs, wickets, maidens, economy, figures |
| `player_career` | player | matches, runs, highest, average, strike rate, 50s/100s, wickets, best bowling, economy, 4w/5w, awards, catches |
| `player_season` | player and season | same stats per season |
| `player_venue` | player and ground | same stats per ground |
| `venues` | ground | matches, average first-innings score, bat-first win %, run rate, sixes |
| `team_season` | team and season | matches, wins |
| `playing_xi`, `player_registry` | squad entry / player | who played each match, stable player id |

## Definitions
Balls faced exclude wides. Bowler runs are bat runs plus wides and no-balls (not byes or leg-byes). Bowler wickets exclude run outs, retirements and obstructing the field. Economy is runs per over, strike rate is runs per 100 balls. Best bowling is most wickets, then fewest runs. Super-over deliveries stay in `balls` but are left out of player statistics.

## Known limits
- Cricsheet names are abbreviated ("V Kohli"); `player_id` is the stable key when two players share a name.
- Grounds are merged to one name per physical stadium (for example Feroz Shah Kotla = Arun Jaitley Stadium); the original spelling is kept in `matches.venue_raw`.
- `season` is the calendar year of the match (Cricsheet writes some as "2020/21").
- Some bowlers' overs/economy are blank for players who never bowled; batting averages are blank for players never dismissed.
- Bowling speed, player age, role, auction prices and fielding positions are not in the Cricsheet data; age, role, prices and trades come from Wikipedia (see the next section).

## Current squads, prices, ages, roles and trades (`players_2026.csv`)
One row per player in a 2026 squad (274 players, 10 teams), built by `scripts/build_players.py` (run after `build_dataset.py`).
`scripts/fetch_roles.py` fetches the Wikipedia player introductions used for roles.

| Column group | Columns |
|---|---|
| Who | player, team, age (as of 11 Nov 2026, computed from date of birth), dob, role, role_source, nationality, overseas, is_captain, batting_style, bowling_style |
| Price | `price_2026_crore` (the player's contract that season), `acquired_via` (Auction 16 Dec 2025 / Retained / Trade Nov 2025 / Replacement signing), `auction_price_crore` and `base_price_crore` (auction buys only), `team_2025` |
| Trade | `traded_in_2025_window`, `traded_from`, `traded_to`, `trade_date`, `trade_price_lakh` |
| Status | is_replacement, withdrawn (ruled out during the season), notes |
| IPL record | ipl_matches, runs, average, strike rate, 100s/50s, wickets, economy, bowling average, best bowling, player-of-match awards (from the Cricsheet tables) |

Also `trades_2026.csv` (the 10 trades) and `auction_2026.csv` (all 77 auction buys with base price, price, buyer, previous team).

Sources (Wikipedia, saved in `data/raw/wikipedia/` on 11 Nov 2026): "List of 2026 Indian Premier League personnel changes" (retentions, trades, auction, replacements) and each team's "2026 <team> season" page (squad, date of birth, styles, salary).

Limits to know:
- `auction_price_crore` exists only for the 77 players bought at the Dec 2025 mini-auction. The other 163 were retained, so their price is the retention value (many were bought at the 2025 mega-auction; that price is not in this source).
- "Team" means the 2026 squad. The 2027 retention and trade window has not happened yet, so it will change.
- Role comes from the Wikipedia auction list or article where one exists; otherwise it is derived from the IPL record (`role_source` says which). 40 players with almost no IPL data are marked `Unknown`.
- Players and squad names are matched to Cricsheet by franchise and initials; two team-mates sharing initials get only one record (the higher-paid), the other is left blank (`ipl_history_match` explains).

## Trades between teams, verified to 11 Nov 2026 (`trades_all.csv`, `trades_pending.csv`)
`scripts/build_trades.py` (run after `build_players.py`) holds a hand-checked record: 20 player moves in 7 deals, with fee, previous fee, deal, status, confidence and the sources checked.
- **Nov 2025 window (10 players, for IPL 2026):** confirmed by Wikipedia and several outlets reporting the BCCI announcement; fees match `players_2026.csv`.
- **Since the 2026 season (10 players, for IPL 2027):** Pant/Kuldeep (LSG-DC), Natarajan/Ansari (DC-SRH), the CSK-SRH four-player swap, and Hardik Pandya/Arshdeep Singh (MI-PBKS). Cricinfo and Business Standard blocked automated access, so these rest on other outlets (the CSK deal on CSK's own site); `confidence` says how well each is backed. The Natarajan/Ansari date (14 Oct) has one dated source, and the Pant/Kuldeep date (23 Jun) comes from a team post quoted by a tracker.
- `trades_pending.csv` lists rumoured or "agreed in principle" deals (for example an unnamed LSG-RR swap). They are not counted as trades.
- `players_2026.csv` now has `current_team` (after all completed trades) and `trade_2027_*` columns. The 2027 retention deadline is 17 Nov 2026 and the mini-auction is in December, so this will keep changing.

## Player-value model and team recommendations (`IPL_MODEL.md`)
Which players suit each team, using runs/wickets (ball by ball, adjusted for innings phase and ground), a next-season forecast, home-ground effects, salaries and the IPL squad rules. Read `IPL_MODEL.md` for results and per-team pages. Run order:
`model_impact.py` (season impact per player) -> `model_predict.py` (2027 forecast + walk-forward test) -> `model_home.py` (home advantage, tests player-ground fit) -> `model_recommend.py [purse]` (best squad/XI per team under the rules; default purse 125 crore) -> `model_validate_wins.py` -> `make_report.py`.
Main outputs in `data/processed/`: `player_season_impact.csv`, `impact_forecast_2027.csv`, `team_keep_values.csv` (keep value per current player), `team_fit_matrix.csv` and `team_targets.csv` (fit gain per team and outside player), `team_summary.csv`, `player_value.csv`, `team_home_advantage.csv`, `ground_factors.csv`.
Findings that shaped the design: forecasts are weak (rank correlation 0.16, no better than a 3-season average); team home advantage is real (about +5.7 points) but player-at-ground fit does not predict anything, so it is not used; impact tracks winning (0.75 correlation, +100 runs of impact is about +0.4 wins per 14 games).
