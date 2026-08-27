#!/usr/bin/env python3
"""Round 3: identity hunts (Mew via attack name, Pikachu in PE) + failed retries."""
import json, time, urllib.parse, urllib.request, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = json.loads((ROOT / "data" / "api_matches.json").read_text())
API = "https://api.pokemontcg.io/v2/cards"

def q(query: str):
    url = f"{API}?{urllib.parse.urlencode({'q': query})}"
    req = urllib.request.Request(url, headers={"User-Agent": "wishlist-builder/0.3"})
    last = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except Exception as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"failed: {last}")

def show(img, tag, cards, clear=False):
    if clear:
        OUT["candidates"][img] = []
    for c in cards:
        cm = c.get("cardmarket") or {}
        prices = cm.get("prices") or {}
        OUT["candidates"][img].append({
            "id": c["id"], "name": c["name"], "set": c["set"]["name"],
            "number": c["number"], "rarity": c.get("rarity"),
            "cm_trend": prices.get("trendPrice"), "cm_avg7": prices.get("avg7"),
            "cm_low": prices.get("lowPrice"), "cm_url": cm.get("url"),
            "image": (c.get("images") or {}).get("large"),
        })
    print(f"== {img} [{tag}] {len(cards)}")
    for rec in OUT["candidates"][img]:
        print(f"   {rec['id']:<22} {rec['set']:<28} #{rec['number']:<8} {str(rec['rarity']):<26} trend={rec['cm_trend']}")

JOBS = [
    ("IMG-20260827-WA0020.jpg", 'attacks.name:"Mysterious Tail" name:Mew', True),   # sleeping Mew identity
    ("IMG-20260719-WA0001.jpg", 'name:Pikachu set.name:"Paldea Evolved"', True),    # all PE pikachu
    ("IMG-20260606-WA0031.jpg", 'name:Shaymin set.name:"Destined Rivals"', False),  # retry
    ("IMG-20260606-WA0031.jpg", 'name:Shaymin number:185', False),
    ("IMG-20260803-WA0004.jpg", 'name:Morpeko number:206', False),                  # retry, no apostrophe
    ("IMG-20260803-WA0004.jpg", "name:\"Marnie's Morpeko\"", False),
]
for img, query, clear in JOBS:
    try:
        d = q(query)
        show(img, query, d.get("data", []), clear=clear)
    except Exception as e:
        print(f"FAIL {img} [{query}]: {e}")
    time.sleep(1.0)

(ROOT / "data" / "api_matches.json").write_text(json.dumps(OUT, indent=1))
print("\nupdated")
