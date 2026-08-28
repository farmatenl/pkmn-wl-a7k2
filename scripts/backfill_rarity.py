#!/usr/bin/env python3
"""Backfill missing `rarity` on cards.json from pokemontcg.io (card data only, no prices).

Convention (AGENTS.md): card identity in cards.json is owner-verified truth. We set
rarity ONLY when the API result for the card's set+number carries the same name.
A name conflict (e.g. matches2 claimed g1-RC23 = "Swablu" vs owner's Pikachu) is
reported and skipped for the owner to resolve — never silently applied.

API is flaky (502/500 interleaved with 200): retry with backoff, sleep between cards.
"""
import json, pathlib, time, unicodedata, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
API = "https://api.pokemontcg.io/v2/cards"


def norm_name(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("-", " ").replace("’", "'")
    s = s.replace("mega ", "m ")  # API style: "M Lopunny & Jigglypuff-GX"
    return " ".join(s.split())


def norm_num(s):
    s = str(s or "").strip().upper().split("/")[0]
    return str(int(s)) if s.isdigit() else s


def get(url, tries=5):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "pkmn-wishlist-rarity-backfill/1.0"})
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.load(r)
        except Exception as e:
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))


cards = json.loads((ROOT / "data" / "cards.json").read_text())
need = [c for c in cards if not c.get("rarity")]
print(f"{len(need)} cards need rarity\n")

# set-name variants to try, in order (cards.json name first)
VARIANTS = {"Crown Zenith Galarian Gallery": ["Crown Zenith: Galarian Gallery", "Crown Zenith Galarian Gallery", "Crown Zenith"]}

def num_variants(n):
    base = str(n).split("/")[0]
    return [base, str(int(base))] if base.isdigit() and base != str(int(base)) else [base]

set_fails, conflicts, applied = [], [], []
for c in need:
    variants = VARIANTS.get(c["set"], [c["set"]])
    found = []
    for v in variants:
        for n in num_variants(c["number"]):
            q = urllib.parse.quote(f'set.name:"{v}" number:"{n}"')
            try:
                d = get(f"{API}?q={q}")
            except Exception as e:
                set_fails.append((c["id"], f"API error: {e}"))
                break
            if d.get("totalCount"):
                found = d["data"]
                break
            time.sleep(1.2)
        if found or set_fails and set_fails[-1][0] == c["id"]:
            break
    if not found:
        if not any(cid == c["id"] for cid, _ in set_fails):
            set_fails.append((c["id"], f"no API result for set={c['set']!r} number={c['number']!r}"))
        continue
    matches = [x for x in found if norm_name(x["name"]) == norm_name(c["name"]) and x.get("rarity")]
    if len(matches) == 1:
        c["rarity"] = matches[0]["rarity"]
        applied.append((c["id"], c["name"], c["set"], c["number"], c["rarity"], matches[0]["id"]))
    elif not matches:
        conflicts.append((c["id"], c["name"], [x["name"] for x in found]))
    else:
        rars = {m["rarity"] for m in matches}
        if len(rars) == 1:  # same rarity across printings — safe
            c["rarity"] = matches[0]["rarity"]
            applied.append((c["id"], c["name"], c["set"], c["number"], c["rarity"], "multiple printings, same rarity"))
        else:
            conflicts.append((c["id"], c["name"], [f"{x['name']} ({x['rarity']})" for x in found]))
    time.sleep(1.2)

(ROOT / "data" / "cards.json").write_text(json.dumps(cards, indent=1))
print(f"APPLIED {len(applied)}:")
for cid, name, s, n, rar, src in applied:
    print(f"  {cid:<17} {name:<30} {s} #{n:<7} -> {rar}   [{src}]")
print(f"\nCONFLICTS (owner must resolve) {len(conflicts)}:")
for cid, name, got in conflicts:
    print(f"  {cid:<17} cards.json says {name!r}; API returned {got}")
print(f"\nNOT FOUND / API FAILS {len(set_fails)}:")
for cid, why in set_fails:
    print(f"  {cid:<17} {why}")
