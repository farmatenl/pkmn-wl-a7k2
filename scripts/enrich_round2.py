#!/usr/bin/env python3
"""Round 2: retry failures + smarter fallbacks. Merges into data/api_matches.json."""
import json, time, urllib.parse, urllib.request, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = json.loads((ROOT / "data" / "api_matches.json").read_text())
API = "https://api.pokemontcg.io/v2/cards"

def q(query: str):
    url = f"{API}?{urllib.parse.urlencode({'q': query})}"
    req = urllib.request.Request(url, headers={"User-Agent": "wishlist-builder/0.2"})
    last = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except Exception as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"query failed after retries: {last}")

def show(img, tag, cards):
    OUT["candidates"].setdefault(img, [])
    known = {c["id"] for c in OUT["candidates"][img]}
    for c in cards:
        if c["id"] in known:
            continue
        cm = c.get("cardmarket") or {}
        prices = cm.get("prices") or {}
        OUT["candidates"][img].append({
            "id": c["id"], "name": c["name"], "set": c["set"]["name"],
            "number": c["number"], "rarity": c.get("rarity"),
            "cm_trend": prices.get("trendPrice"), "cm_avg7": prices.get("avg7"),
            "cm_low": prices.get("lowPrice"), "cm_url": cm.get("url"),
            "image": (c.get("images") or {}).get("large"),
        })
    print(f"{img} [{tag}] +{len(cards)}")
    for rec in OUT["candidates"][img]:
        print(f"   {rec['id']:<22} {rec['set']:<28} #{rec['number']:<8} {str(rec['rarity']):<30} trend={rec['cm_trend']}")

# images that failed (5xx) or returned 0 hits in round 1
RETRY = {
    "IMG-20260606-WA0031.jpg": ['name:"Shaymin" number:185'],
    "IMG-20260606-WA0056.jpg": ['name:"Lapras" number:GG05'],
    "IMG-20260606-WA0063.jpg": ['name:"Beedrill V"'],  # pick 163/189 Astral Radiance
    "IMG-20260608-WA0026.jpg": ['name:"Leafeon VSTAR"'],
    "IMG-20260626-WA0007.jpg": ['name:"Horsea" set.id:sfa', 'name:"Horsea" set.name:"Shrouded Fable"', 'name:"Horsea" number:67'],
    "IMG-20260629-WA0019.jpg": ['name:"Psyduck" number:175'],
    "IMG-20260629-WA0025.jpg": ['name:"Vaporeon" number:TG02'],
    "IMG-20260719-WA0001.jpg": ['name:"Pikachu" number:022', 'name:"Pikachu" number:22'],
    "IMG-20260719-WA0007.jpg": ['name:"Tepig" set.name:"White Flare"', 'name:"Tepig" number:96'],
    "IMG-20260719-WA0010.jpg": ['name:"Dwebble" number:129', 'name:"Dwebble" set.name:"Black Bolt"'],
    "IMG-20260803-WA0004.jpg": ['name:"Marnie\'s Morpeko"'],
    "IMG-20260803-WA0007.jpg": ['name:"Pikachu" set.id:svp number:088', 'name:"Pikachu" set.id:svp number:88'],
    "IMG-20260803-WA0012.jpg": ['name:"Chansey" number:187'],
    "IMG-20260827-WA0016.jpg": ['name:"Foongus" number:095', 'name:"Foongus" set.name:"Black Bolt"'],
    "IMG-20260827-WA0018.jpg": ['name:"Maushold" number:226'],
    "IMG-20260827-WA0019.jpg": ['name:"Mew"'],
    "IMG-20260827-WA0020.jpg": ['name:"Dedenne-GX"'],
    "IMG-20260827-WA0021.jpg": ['name:"Manaphy" number:XY113'],
}

for img, queries in RETRY.items():
    got = False
    for query in queries:
        try:
            d = q(query)
        except Exception as e:
            print(f"FAIL {img} [{query}]: {e}")
            continue
        cards = d.get("data", [])
        if cards:
            show(img, query, cards)
            got = True
            break
        time.sleep(0.8)
    if not got:
        print(f"STILL EMPTY: {img}")
    time.sleep(1.0)

(ROOT / "data" / "api_matches.json").write_text(json.dumps(OUT, indent=1))
print("\nupdated data/api_matches.json")
