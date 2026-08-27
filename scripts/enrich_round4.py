#!/usr/bin/env python3
"""Round 4: fix setdefault bug; Mew identity via client-side attack filter; retries."""
import json, time, urllib.parse, urllib.request, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = json.loads((ROOT / "data" / "api_matches.json").read_text())
API = "https://api.pokemontcg.io/v2/cards"

def q(query: str, **params):
    args = {"q": query, "pageSize": 100, **params}
    url = f"{API}?{urllib.parse.urlencode(args)}"
    req = urllib.request.Request(url, headers={"User-Agent": "wishlist-builder/0.4"})
    last = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except Exception as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"failed: {last}")

def add(img, cards, clear=False):
    lst = OUT["candidates"].setdefault(img, [])
    if clear:
        lst.clear()
    known = {c["id"] for c in lst}
    for c in cards:
        if c["id"] in known:
            continue
        cm = c.get("cardmarket") or {}
        prices = cm.get("prices") or {}
        lst.append({
            "id": c["id"], "name": c["name"], "set": c["set"]["name"],
            "number": c["number"], "rarity": c.get("rarity"),
            "cm_trend": prices.get("trendPrice"), "cm_avg7": prices.get("avg7"),
            "cm_low": prices.get("lowPrice"), "cm_url": cm.get("url"),
            "image": (c.get("images") or {}).get("large"),
        })
    print(f"== {img}: {len(lst)} candidates now")
    for rec in lst:
        print(f"   {rec['id']:<22} {rec['set']:<28} #{rec['number']:<8} {str(rec['rarity']):<26} trend={rec['cm_trend']}")

# 1) Mew: fetch all, filter client-side on Mysterious Tail
d = q('name:Mew')
mews = d.get("data", [])
tail = [c for c in mews if any(a.get("name") == "Mysterious Tail" for a in (c.get("attacks") or []))]
print(f"total Mew: {len(mews)}, with Mysterious Tail: {len(tail)}")
if tail:
    add("IMG-20260827-WA0020.jpg", tail, clear=True)

# 2) retries
for img, query in [
    ("IMG-20260606-WA0031.jpg", 'name:Shaymin number:185'),
    ("IMG-20260803-WA0004.jpg", 'name:Morpeko number:206'),
]:
    try:
        d = q(query)
        add(img, d.get("data", []))
    except Exception as e:
        print(f"FAIL {img} [{query}]: {e}")
    time.sleep(1.0)

(ROOT / "data" / "api_matches.json").write_text(json.dumps(OUT, indent=1))
print("\nupdated")
