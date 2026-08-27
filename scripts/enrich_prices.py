#!/usr/bin/env python3
"""Resolve wishlist cards against pokemontcg.io; keep Cardmarket price data.

Phase A (default): for each entry in data/cards.raw.json with api=true,
query the API, print candidate matches (id, set, number, cm trend, image url).
Writes data/api_matches.json for disambiguation.
Phase B (later, manual): disambiguated picks get baked into data/cards.json
by write_cards.py with prices.
"""
import json, time, urllib.parse, urllib.request, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = json.loads((ROOT / "data" / "cards.raw.json").read_text())
OUT = {"resolved": {}, "candidates": {}}

API = "https://api.pokemontcg.io/v2/cards"

def q(params: dict):
    qs = urllib.parse.urlencode({"q": " ".join(f'{k}:"{v}"' if " " in str(v) else f"{k}:{v}" for k, v in params.items())})
    url = f"{API}?{qs}"
    req = urllib.request.Request(url, headers={"User-Agent": "wishlist-builder/0.1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

# per-card query spec: raw.json index -> query params + optional filter
QUERIES = {
    "IMG-20260606-WA0031.jpg": {"name": "Shaymin", "number": "185"},
    "IMG-20260606-WA0056.jpg": {"name": "Lapras", "number": "GG05"},
    "IMG-20260606-WA0063.jpg": {"name": "Beedrill V"},
    "IMG-20260608-WA0026.jpg": {"name": "Leafeon VSTAR"},
    "IMG-20260626-WA0007.jpg": {"name": "Horsea", "number": "067"},
    "IMG-20260629-WA0019.jpg": {"name": "Psyduck", "number": "175"},
    "IMG-20260629-WA0025.jpg": {"name": "Vaporeon", "number": "TG02"},
    "IMG-20260712-WA0013.jpg": {"name": "Psyduck", "number": "226"},
    "IMG-20260712-WA0014.jpg": {"name": "Misty's Psyduck", "number": "193"},
    "IMG-20260719-WA0001.jpg": {"name": "Pikachu", "number": "022"},
    "IMG-20260719-WA0003.jpg": {"name": "Lisia's Appeal"},
    "IMG-20260719-WA0005.jpg": {"name": "Team Rocket's Meowth"},
    "IMG-20260719-WA0007.jpg": {"name": "Tepig", "number": "096"},
    "IMG-20260719-WA0010.jpg": {"name": "Dwebble", "number": "129"},
    "IMG-20260803-WA0004.jpg": {"name": "Marnie's Morpeko"},
    "IMG-20260803-WA0007.jpg": {"name": "Pikachu", "number": "088"},
    "IMG-20260803-WA0012.jpg": {"name": "Chansey", "number": "187"},
    "IMG-20260827-WA0016.jpg": {"name": "Foongus", "number": "095"},
    "IMG-20260827-WA0017.jpg": {"name": "Whimsicott", "number": "165"},
    "IMG-20260827-WA0018.jpg": {"name": "Maushold", "number": "226"},
    "IMG-20260827-WA0019.jpg": {"name": "Mew"},
    "IMG-20260827-WA0020.jpg": {"name": "Dedenne GX"},
    "IMG-20260827-WA0021.jpg": {"name": "Manaphy", "number": "XY113"},
}

for entry in RAW:
    img = entry["image"]
    if not entry.get("api"):
        print(f"SKIP (manual): {img} {entry['name']}")
        continue
    params = QUERIES[img]
    try:
        d = q(params)
    except Exception as e:
        print(f"FAIL {img}: {e}")
        continue
    cards = d.get("data", [])
    OUT["candidates"][img] = []
    for c in cards:
        cm = c.get("cardmarket") or {}
        prices = cm.get("prices") or {}
        rec = {
            "id": c["id"], "name": c["name"], "set": c["set"]["name"],
            "number": c["number"], "rarity": c.get("rarity"),
            "cm_trend": prices.get("trendPrice"), "cm_avg7": prices.get("avg7"),
            "cm_low": prices.get("lowPrice"), "cm_url": cm.get("url"),
            "image": (c.get("images") or {}).get("large"),
        }
        OUT["candidates"][img].append(rec)
    n = len(cards)
    print(f"{img} [{params}]: {n} hit(s)")
    for rec in OUT["candidates"][img]:
        print(f"   {rec['id']:<22} {rec['set']:<28} #{rec['number']:<8} {str(rec['rarity']):<28} trend={rec['cm_trend']}")
    time.sleep(1.1)

(ROOT / "data" / "api_matches.json").write_text(json.dumps(OUT, indent=1))
print("\nwrote data/api_matches.json")
