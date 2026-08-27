#!/usr/bin/env python3
"""Batch-2 fixup: GG numbers, empty-pool retries, pokemontcg fallback for RC cards.
Bounded: one pass. Anything unresolved after this = flagged in the report."""
import json, os, pathlib, time, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
KEY = open(os.path.expanduser("~/.rapidapi_key")).read().strip()
HOST = "cardmarket-api-tcg.p.rapidapi.com"
M = json.loads((ROOT / "data" / "tcggo_matches2.json").read_text())

def tcggo(path):
    req = urllib.request.Request(f"https://{HOST}{path}", headers={"x-rapidapi-key": KEY, "x-rapidapi-host": HOST})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def ptcg(query):
    url = "https://api.pokemontcg.io/v2/cards?" + urllib.parse.urlencode({"q": query})
    req = urllib.request.Request(url, headers={"User-Agent": "wishlist/1.1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read()).get("data", [])

def norm(s):
    import re
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())

OPEN = [
    # (image, name, set, number-full, strategy)
    ("IMG-20260606-WA0035.jpg", "Deerling", "Black Bolt", "091/086", "tcggo"),
    ("IMG-20260606-WA0039.jpg", "Keldeo", "Crown Zenith Galarian Gallery", "GG07/GG70", "tcggo-gg"),
    ("IMG-20260606-WA0041.jpg", "Piplup", "Unified Minds", "239/236", "tcggo"),
    ("IMG-20260606-WA0042.jpg", "Lillipup", None, None, "tcggo-find"),
    ("IMG-20260606-WA0043.jpg", "Milcery", "Surging Sparks", "152/142", "tcggo"),
    ("IMG-20260606-WA0045.jpg", "Poke Kid", "Shining Fates", "070/072", "tcggo"),
    ("IMG-20260606-WA0046.jpg", "Mega Lopunny & Jigglypuff GX", "Unified Minds", "226/236", "tcggo"),
    ("IMG-20260606-WA0047.jpg", "Mega Lopunny & Jigglypuff GX", "Unified Minds", "225/236", "tcggo"),
    ("IMG-20260606-WA0051.jpg", "Sylveon ex", "Generations", "RC28/RC32", "ptcg"),
    ("IMG-20260606-WA0055.jpg", "Flareon ex", "Generations", "RC29/RC32", "ptcg"),
    ("IMG-20260606-WA0058.jpg", "Pikachu", "Generations", "RC23/RC32", "ptcg"),
    ("IMG-20260606-WA0060.jpg", "Emolga", "Generations", "RC32/RC32", "ptcg"),
    ("IMG-20260606-WA0065.jpg", "Bulbasaur", "Black Bolt", "013/086", "tcggo"),
    ("IMG-20260629-WA0020.jpg", "Stufful", "Twilight Masquerade", "193/167", "tcggo"),
    ("IMG-20260629-WA0021.jpg", "Altaria", "Crown Zenith Galarian Gallery", "GG19/GG70", "tcggo-gg"),
]
EPS = {"Black Bolt": 223, "Crown Zenith": 21, "Unified Minds": 54, "Surging Sparks": 172,
       "Shining Fates": 40, "Twilight Masquerade": 12}

for img, name, setname, number, strategy in OPEN:
    hit = None
    try:
        if strategy in ("tcggo", "tcggo-gg", "tcggo-find"):
            ep = EPS.get(setname, 54) if setname else 54
            term = name.split("'s")[-1].split(" & ")[-1].strip()
            d = tcggo(f"/pokemon/episodes/{ep}/cards?search={urllib.parse.quote(term)}")
            pool = d.get("data", [])
            time.sleep(2.5)
            want_num = (number or "").split("/")[0]
            for c in pool:
                cn = str(c.get("card_number", ""))
                if strategy == "tcggo-gg":
                    if cn.upper() == want_num.upper():
                        hit = c; break
                else:
                    if cn.lstrip("0") == want_num.lstrip("0"):
                        hit = c; break
            if not hit and strategy == "tcggo-find":
                # Lillipup: search pool by name, use full card info from earlier sheet reading
                for c in pool:
                    if norm(c.get("name", "")) == "lillipup":
                        hit = c; break
        elif strategy == "ptcg":
            setid = {"Generations": "g1"}[setname]
            num = number.split("/")[0]
            cards = ptcg(f'set.id:{setid} number:{num}')
            time.sleep(1.2)
            if cards:
                c = cards[0]
                cm = (c.get("cardmarket") or {})
                pr = cm.get("prices") or {}
                hit = {"tcgid": c["id"], "name": c["name"], "card_code_number": f"{setid.upper()} {num}",
                       "card_number": num, "set": {"name": "Generations"},
                       "prices": {"cardmarket": {"currency": "EUR",
                                  "lowest_near_mint": pr.get("lowPrice"),
                                  "7d_average": pr.get("avg7"), "30d_average": pr.get("avg30")}},
                       "links": {"cardmarket": (cm.get("url") or None)},
                       "_fallback": "pokemontcg.io"}
    except Exception as e:
        print(f"ERR {img}: {e}")
    if hit:
        M[img] = hit
        cm = hit["prices"]["cardmarket"]
        print(f"OK  {img:<28} {hit['name']:<28} {hit.get('card_code_number',''):<14} 7d={cm.get('7d_average')}")
    else:
        print(f"STILL OPEN {img} {name}")

(ROOT / "data" / "tcggo_matches2.json").write_text(json.dumps(M, indent=1))
print(f"\ntotal resolved batch-2: {len(M)}/24")
