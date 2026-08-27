#!/usr/bin/env python3
"""Batch-2 final sweep (strike 3). Whatever is unresolved after this = flagged."""
import json, os, pathlib, time, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
KEY = open(os.path.expanduser("~/.rapidapi_key")).read().strip()
M = json.loads((ROOT / "data" / "tcggo_matches2.json").read_text())

def tcggo(path):
    req = urllib.request.Request(f"https://cardmarket-api-tcg.p.rapidapi.com{path}",
        headers={"x-rapidapi-key": KEY, "x-rapidapi-host": "cardmarket-api-tcg.p.rapidapi.com"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def ptcg(query, tries=3):
    url = "https://api.pokemontcg.io/v2/cards?" + urllib.parse.urlencode({"q": query})
    req = urllib.request.Request(url, headers={"User-Agent": "wishlist/1.2"})
    last = None
    for a in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read()).get("data", [])
        except Exception as e:
            last = e; time.sleep(3)
    print(f"  ptcg fail [{query}]: {last}")
    return []

def as_hit_ptcg(c, setdisplay):
    cm = c.get("cardmarket") or {}; pr = cm.get("prices") or {}
    return {"tcgid": c["id"], "name": c["name"], "card_code_number": f"{setdisplay} {c['number']}",
            "card_number": c["number"], "set": {"name": setdisplay},
            "prices": {"cardmarket": {"currency": "EUR", "lowest_near_mint": pr.get("lowPrice"),
                       "7d_average": pr.get("avg7"), "30d_average": pr.get("avg30")}},
            "links": {"cardmarket": cm.get("url")}, "_fallback": "pokemontcg.io"}

# 1) Lopunny & Jigglypuff: get true numbers from TCGGO
d = tcggo("/pokemon/episodes/54/cards?search=Lopunny")
time.sleep(2.5)
lop = d.get("data", [])
print("UNM Lopunny pool:", [(c["card_code_number"], c["name"]) for c in lop])
fa = next((c for c in lop if c.get("rarity") and "Rainbow" not in str(c.get("rarity")) and int(str(c.get("card_number"))) < 236), None)
rb = next((c for c in lop if c.get("rarity") and "Rainbow" in str(c.get("rarity"))), None)
if len(lop) == 2:
    a, b = lop
    lo, hi = sorted([a, b], key=lambda c: int(str(c["card_number"])))
    if hi.get("prices", {}).get("cardmarket", {}).get("7d_average", 0) and "Rainbow" in str(hi.get("rarity", "")):
        rb, fa = hi, lo
    else:
        fa, rb = lo, hi
if fa: M["IMG-20260606-WA0047.jpg"] = fa   # full art
if rb: M["IMG-20260606-WA0046.jpg"] = rb   # rainbow
print("assigned:", "FA->WA0047", fa and fa["card_code_number"], "| RB->WA0046", rb and rb["card_code_number"])

# 2) everything else via pokemontcg (exact set+number = deterministic)
PT = [
    ("IMG-20260606-WA0035.jpg", "Deerling", "zsv10pt5", "91", "Black Bolt"),
    ("IMG-20260606-WA0039.jpg", "Keldeo", "swsh12pt5gg", "GG07", "Crown Zenith GG"),
    ("IMG-20260606-WA0041.jpg", "Piplup", "sm11", "239", "Unified Minds"),
    ("IMG-20260606-WA0043.jpg", "Milcery", "sv8", "152", "Surging Sparks"),
    ("IMG-20260606-WA0055.jpg", "Flareon-EX", "g1", "RC29", "Generations"),
    ("IMG-20260606-WA0058.jpg", "Pikachu", "g1", "RC23", "Generations"),
    ("IMG-20260606-WA0060.jpg", "Emolga", "g1", "RC32", "Generations"),
    ("IMG-20260606-WA0065.jpg", "Bulbasaur", "zsv10pt5", "13", "Black Bolt"),
    ("IMG-20260629-WA0020.jpg", "Stufful", "sv6", "193", "Twilight Masquerade"),
    ("IMG-20260629-WA0021.jpg", "Altaria", "swsh12pt5gg", "GG19", "Crown Zenith GG"),
]
for img, name, setid, num, display in PT:
    if img in M:
        continue
    cards = ptcg(f'set.id:{setid} number:{num}')
    time.sleep(1.2)
    if cards:
        M[img] = as_hit_ptcg(cards[0], display)
        pr = M[img]["prices"]["cardmarket"]
        print(f"OK  {img:<28} {name:<15} {setid} {num}  7d={pr.get('7d_average')}")
    else:
        print(f"STILL OPEN {img} {name}")

(ROOT / "data" / "tcggo_matches2.json").write_text(json.dumps(M, indent=1))
print(f"\nresolved: {len(M)}/24 | open: {24 - len(M)}")
