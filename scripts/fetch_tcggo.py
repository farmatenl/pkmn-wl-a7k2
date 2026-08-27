#!/usr/bin/env python3
"""Pull all wishlist cards from TCGGO (RapidAPI) and compare vs pokemontcg.io prices."""
import json, os, pathlib, time, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
KEY = open(os.path.expanduser("~/.rapidapi_key")).read().strip()
HOST = "cardmarket-api-tcg.p.rapidapi.com"
OUTDIR = ROOT / "data" / "tcggo"
OUTDIR.mkdir(exist_ok=True)

def get(path):
    req = urllib.request.Request(f"https://{HOST}{path}", headers={
        "x-rapidapi-key": KEY, "x-rapidapi-host": HOST})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read()), dict(r.headers)

# episode map from earlier snapshot files
EPS = {}
for f in ("/tmp/eps.json", "/tmp/eps2.json", "/tmp/eps3.json"):
    p = pathlib.Path(f)
    if p.exists():
        for e in json.loads(p.read_text())["data"]:
            EPS[e["name"]] = e["id"]

cards = json.loads((ROOT / "data" / "cards.json").read_text())
by_set = {}
for c in cards:
    if not c.get("apiId"):
        continue
    by_set.setdefault(c["set"], []).append(c)

SET_TO_EPISODE = {
    "151": "151", "Destined Rivals": "Destined Rivals", "Crown Zenith": "Crown Zenith",
    "Crown Zenith Galarian Gallery": "Crown Zenith", "Brilliant Stars Trainer Gallery": "Brilliant Stars",
    "Shrouded Fable": "Shrouded Fable", "Astral Radiance": "Astral Radiance",
    "Paldea Evolved": "Paldea Evolved", "Surging Sparks": "Surging Sparks",
    "Twilight Masquerade": "Twilight Masquerade", "White Flare": "White Flare",
    "Black Bolt": "Black Bolt", "Paradox Rift": "Paradox Rift",
}

def search_episode(ep_id, term):
    d, hdr = get(f"/pokemon/episodes/{ep_id}/cards?search={urllib.parse.quote(term)}")
    return d.get("data", [])

import urllib.parse
results, misses = {}, []
seen_eps = {}
for setname, group in sorted(by_set.items()):
    ep_name = SET_TO_EPISODE.get(setname)
    if not ep_name or ep_name not in EPS:
        misses.append((setname, "no episode id"))
        continue
    ep_id = EPS[ep_name]
    terms = sorted({c["name"].split("'s")[-1].strip() for c in group})  # 'Marnie's Morpeko'->'Morpeko'
    pool = []
    for t in terms:
        pool += search_episode(ep_id, t)
        time.sleep(2.2)
    (OUTDIR / f"ep{ep_id}.json").write_text(json.dumps(pool, indent=1))
    pool_byid = {p.get("tcgid"): p for p in pool}
    seen_eps[ep_id] = len(pool)
    for c in group:
        hit = pool_byid.get(c["apiId"])
        if hit:
            results[c["id"]] = hit
        else:
            misses.append((c["name"], f"tcgid {c['apiId']} not in ep{ep_id}"))

print(f"matched {len(results)}/{sum(len(g) for g in by_set.values())} API cards")
for m in misses:
    print("  MISS:", m)

# comparison table
print(f"\n{'card':<22}{'ptcg trend':>11}{'TCGGO from':>11}{'7d avg':>9}{'30d avg':>9}  countries")
total_old = total_new = 0
for c in cards:
    hit = results.get(c["id"])
    old = c["price"]["trend"] if c.get("price") and c["price"].get("trend") else None
    if not hit:
        print(f"{c['name']:<22}{str(old):>11}  — (no TCGGO data)")
        continue
    cm = hit["prices"]["cardmarket"]
    eur = lambda v: v / 100 if isinstance(v, (int, float)) else None
    frm = eur(cm.get("lowest_near_mint_EU_only") or cm.get("lowest_near_mint"))
    a7, a30 = eur(cm.get("7d_average")), eur(cm.get("30d_average"))
    countries = {k.replace("lowest_near_mint_", ""): eur(v) for k, v in cm.items()
                 if k.startswith("lowest_near_mint_") and not k.endswith("_EU_only") and v}
    if old: total_old += old
    if frm: total_new += frm
    print(f"{c['name']:<22}{str(old):>11}{str(frm):>11}{str(a7):>9}{str(a30):>9}  {countries}")

print(f"\ntotals: pokemontcg €{total_old:.2f} -> TCGGO from-price €{total_new:.2f}")
(ROOT / "data" / "tcggo_matches.json").write_text(json.dumps(results, indent=1))
print("wrote data/tcggo_matches.json")
