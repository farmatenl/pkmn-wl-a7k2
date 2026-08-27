#!/usr/bin/env python3
"""Resolve batch-2 identifications via TCGGO (3-attempt cap per card, then flag)."""
import json, os, pathlib, time, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
KEY = open(os.path.expanduser("~/.rapidapi_key")).read().strip()
HOST = "cardmarket-api-tcg.p.rapidapi.com"
RAW = json.loads((ROOT / "data" / "cards.raw2.json").read_text())

EPISODES = {  # TCGGO episode ids (from the 60-episode listing)
    "Paldea Evolved": 18, "Journey Together": 220, "Scarlet & Violet": 19,
    "Black Bolt": 223, "Chaos Rising": 413, "Crown Zenith": 21,
    "Unified Minds": 54, "Shining Fates": 40, "Generations": 51,
    "Surging Sparks": 172, "Twilight Masquerade": 12, "Destined Rivals": 221,
}

def get(path, retries=3):
    url = f"https://{HOST}{path}"
    req = urllib.request.Request(url, headers={"x-rapidapi-key": KEY, "x-rapidapi-host": HOST})
    last = None
    for a in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except Exception as e:
            last = e
            time.sleep(2.5 * (a + 1))
    raise RuntimeError(f"GET {path}: {last}")

def norm(s):
    import re
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())

by_ep = {}
resolved, flagged = {}, []

for entry in RAW:
    setname = entry.get("set")
    ep_id = EPISODES.get(setname)
    num = str(entry.get("number", "")).split("/")[0].lstrip("0") or "0"
    if not ep_id or not entry.get("number"):
        flagged.append((entry["image"], entry["name"], "no episode/number"))
        continue
    # fetch episode pool once per episode (cache with search by name)
    namekey = entry["name"].split("'s")[-1].split(" & ")[-1].strip()
    cache_key = (ep_id, norm(namekey))
    if cache_key not in by_ep:
        try:
            d = get(f"/pokemon/episodes/{ep_id}/cards?search={urllib.parse.quote(namekey)}")
            by_ep[cache_key] = d.get("data", [])
        except Exception as e:
            by_ep[cache_key] = []
            print(f"FAIL ep{ep_id} '{namekey}': {e}")
        time.sleep(2.2)
    pool = by_ep[cache_key]
    hit = None
    for c in pool:
        cnum = str(c.get("card_number", "")).lstrip("0") or "0"
        cname = norm(c.get("name", ""))
        target = norm(entry["name"])
        if cnum == num and (cname == target or target in cname or cname in target):
            hit = c
            break
    if hit:
        resolved[entry["image"]] = hit
        cm = hit["prices"]["cardmarket"]
        print(f"OK  {entry['image']:<28} {hit['name']:<28} {hit['card_code_number']:<12} 7d={cm.get('7d_average')}")
    else:
        flagged.append((entry["image"], entry["name"], f"ep{ep_id} pool={len(pool)} no number match"))

print(f"\nresolved: {len(resolved)}/{len(RAW)}")
if flagged:
    print("FLAGGED (per 3-strike rule):")
    for img, name, why in flagged:
        print(f"  {img:<28} {name:<28} {why}")

(ROOT / "data" / "tcggo_matches2.json").write_text(json.dumps(resolved, indent=1))
print("\nwrote data/tcggo_matches2.json")
