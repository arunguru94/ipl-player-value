"""Fetch the one-paragraph Wikipedia introduction of every 2026 squad player (their playing role is usually in the first sentence).
Saves data/raw/wikipedia/player_intros.json  {player name as in the squad: {"title": ..., "extract": ...}}.
Run:  python -I scripts/fetch_roles.py     (needs data/processed/players_2026.csv from build_players.py)
Polite: 20 titles per request, 3 seconds apart, descriptive User-Agent.
"""
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "wikipedia" / "player_intros.json"
names = sorted(pd.read_csv(ROOT / "data" / "processed" / "players_2026.csv")["player"].unique())
done = json.load(open(OUT)) if OUT.exists() else {}
todo = [n for n in names if n not in done]
for i in range(0, len(todo), 20):
    batch = todo[i:i + 20]
    q = urllib.parse.urlencode({"action": "query", "format": "json", "formatversion": 2, "prop": "extracts", "exintro": 1, "explaintext": 1,
                                "exlimit": 20, "redirects": 1, "titles": "|".join(batch)})
    req = urllib.request.Request("https://en.wikipedia.org/w/api.php?" + q, headers={"User-Agent": "ipl-analysis-research/1.0 (personal analysis project)"})
    for wait in (0, 60, 120, 240):                                  # back off on HTTP 429
        time.sleep(wait)
        try:
            d = json.load(urllib.request.urlopen(req, timeout=60))["query"]
            break
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
    else:
        raise SystemExit("still rate limited; run again later (progress is saved)")
    alias = {}
    for k in ("normalized", "redirects"):
        for r in d.get(k, []):
            alias[r["from"]] = r["to"]
    pages = {p["title"]: p.get("extract", "") for p in d["pages"]}
    for n in batch:
        t = n
        for _ in range(3):
            t = alias.get(t, t)
        done[n] = {"title": t, "extract": pages.get(t, "")[:500]}
    json.dump(done, open(OUT, "w"), indent=1, ensure_ascii=False)
    print(i + len(batch), "/", len(todo))
    time.sleep(3)

# pass 2: names whose page is missing or about someone else -> try "Name (cricketer)"
retry = [n for n in names if "cricket" not in done.get(n, {}).get("extract", "").lower() and not done.get(n, {}).get("retried")]
for i in range(0, len(retry), 20):
    batch = retry[i:i + 20]
    q = urllib.parse.urlencode({"action": "query", "format": "json", "formatversion": 2, "prop": "extracts", "exintro": 1, "explaintext": 1,
                                "exlimit": 20, "redirects": 1, "titles": "|".join(n + " (cricketer)" for n in batch)})
    req = urllib.request.Request("https://en.wikipedia.org/w/api.php?" + q, headers={"User-Agent": "ipl-analysis-research/1.0 (personal analysis project)"})
    for wait in (0, 60, 120, 240):
        time.sleep(wait)
        try:
            d = json.load(urllib.request.urlopen(req, timeout=60))["query"]
            break
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
    else:
        raise SystemExit("still rate limited; run again later (progress is saved)")
    alias = {r["from"]: r["to"] for k in ("normalized", "redirects") for r in d.get(k, [])}
    pages = {p["title"]: p.get("extract", "") for p in d["pages"]}
    for n in batch:
        t = alias.get(n + " (cricketer)", n + " (cricketer)")
        t = alias.get(t, t)
        ex = pages.get(t, "")
        done[n] = {"title": t, "extract": ex[:500] if "cricket" in ex.lower() else done.get(n, {}).get("extract", ""), "retried": True}
    json.dump(done, open(OUT, "w"), indent=1, ensure_ascii=False)
    print("retry", i + len(batch), "/", len(retry))
    time.sleep(3)
