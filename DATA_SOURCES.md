# Data sources and attribution

- **Ball-by-ball IPL data:** [Cricsheet](https://cricsheet.org) (`ipl_csv2.zip`, downloaded 11 Nov 2026), licensed under the Open Data Commons Attribution License (ODC-By). Credit Cricsheet if you share results. The raw files are not stored in this repository; `scripts/build_dataset.py` explains how to download and rebuild them.
- **Squads, salaries, dates of birth, trades, auction results, player descriptions:** Wikipedia (pages saved in `data/raw/wikipedia/` on 11 Nov 2026), licensed under CC BY-SA 4.0. Pages used: "List of 2026 Indian Premier League personnel changes" and each team's "2026 <team> season" article, plus player article introductions.
- **Trades after the 2026 season and IPL rules:** assembled from news coverage (CSK's official site, Yahoo Sports, Outlook India and others); sources are listed per row in `data/processed/trades_all.csv`.

The code in this repository is under the MIT licence (see `LICENSE`). The data is not covered by it: Cricsheet and Wikipedia keep the licences above.
