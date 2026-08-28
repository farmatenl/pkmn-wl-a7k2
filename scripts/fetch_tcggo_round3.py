#!/usr/bin/env python3
"""Fetch TCGGO (RapidAPI) evidence for the round-3 targets (2026-08-28):
5 identity-corrected cards + Lopunny CEC x2 + Keldeo GG07 + Stufful ME154 + Altaria GG19.

Saves raw episode search results to data/tcggo/round3-*.json (evidence trail).
BASIC plan: 30 req/min -> sleep 2.5s between calls. Key: ~/.rapidapi_key (never printed).
"""
import json, os, pathlib, time, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
KEY = open(os.path.expanduser("~/.rapidapi_key")).read().strip()
HOST = "cardmarket-api-tcg.p.rapidapi.com"
OUT = ROOT / "data" / "tcggo"

def get(path):
    req = urllib.request.Request(f"https://{HOST}{path}", headers={
        "x-rapidapi-key": KEY, "x-rapidapi-host": HOST})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

# --- episode map: cached pages first, page on until we have every set we need ---
NEED = ["Generations", "White Flare", "Cosmic Eclipse", "Stellar Crown", "Crown Zenith", "Mega Evolution"]
EPS = {}
for f in ("/tmp/eps.json", "/tmp/eps2.json", "/tmp/eps3.json"):
    p = pathlib.Path(f)
    if p.exists():
        for e in json.loads(p.read_text())["data"]:
            EPS[e["name"]] = e["id"]
page = 4
while not all(s in EPS for s in NEED):
    d = get(f"/pokemon/episodes?page={page}")
    data = d.get("data", [])
    if not data:
        break
    for e in data:
        EPS[e["name"]] = e["id"]
    pathlib.Path(f"/tmp/eps{page}.json").write_text(json.dumps(d))  # extend the cache
    page += 1
    time.sleep(2.5)
missing = [s for s in NEED if s not in EPS]
print("episodes:", {s: EPS.get(s) for s in NEED})
if missing:
    print("MISSING EPISODES:", missing, "- targets in those sets will fail")

# --- targeted searches: (episode name, search term, filename) ---
SEARCHES = [
    ("Generations", "Pikachu", "round3-gen-pikachu"),
    ("Generations", "Flareon", "round3-gen-flareon"),
    ("White Flare", "Deerling", "round3-wht-deerling"),
    ("Cosmic Eclipse", "Piplup", "round3-cec-piplup"),
    ("Cosmic Eclipse", "Lopunny", "round3-cec-lopunny"),
    ("Stellar Crown", "Bulbasaur", "round3-scr-bulbasaur"),
    ("Crown Zenith", "Keldeo", "round3-cz-keldeo"),
    ("Crown Zenith", "Altaria", "round3-cz-altaria"),
    ("Mega Evolution", "Stufful", "round3-me-stufful"),
]
TARGETS = ["g1-RC29", "g1-RC28", "rsv10pt5-91", "sm11-239", "sm11-225", "sm11-226",
           "sv7-143", "swsh12pt5gg-GG07", "swsh12pt5gg-GG19", "me1-154"]

found = {}
for ep, term, fname in SEARCHES:
    if ep not in EPS:
        continue
    d = get(f"/pokemon/episodes/{EPS[ep]}/cards?search={urllib.parse.quote(term)}")
    pool = d.get("data", [])
    (OUT / f"{fname}.json").write_text(json.dumps(pool, indent=1))
    hits = [c for c in pool if c.get("tcgid") in TARGETS]
    for c in hits:
        found[c["tcgid"]] = c
    print(f"{fname}: {len(pool)} results, {len(hits)} target hits " +
          (", ".join(f"{c['tcgid']}={c.get('name_numbered', c.get('name'))}" for c in hits) or "-"))
    time.sleep(2.5)

print("\n=== summary ===")
for t in TARGETS:
    c = found.get(t)
    print(f"{t:<17} {'FOUND: ' + str(c.get('name_numbered', c.get('name'))) + ' 7d=' + str((c.get('prices', {}).get('cardmarket', {}) or {}).get('7d_average')) if c else 'not found'}")
