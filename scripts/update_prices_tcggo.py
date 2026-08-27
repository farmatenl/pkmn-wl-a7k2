#!/usr/bin/env python3
"""Update cards.json prices from TCGGO (live Cardmarket data).

Headline: 7d_average (validated against Cardmarket by Giel on 2026-08-27).
Supplementary: lowest NM (EU-wide), per-country lowest NM (DE/FR/ES/IT).
Keeps PriceCharting (Chinese Cubone) and pokemontcg.io (XY-promo Manaphy).
"""
import json, os, pathlib, time, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
TODAY = "2026-08-27"

# gather all TCGGO evidence
evidence = {}  # tcgid -> card record
for f in sorted((ROOT / "data" / "tcggo").glob("*.json")):
    d = json.loads(f.read_text())
    if isinstance(d, dict):
        d = d.get("data", [])
    for c in d:
        if c.get("tcgid"):
            evidence[c["tcgid"]] = c
# special case: Marnie's Morpeko (no tcgid at TCGGO) matched by name
for c in json.loads((ROOT / "data" / "tcggo" / "ep23-morpeko.json").read_text())["data"]:
    if c["name"] == "Marnie's Morpeko" and "SVP 206" in str(c.get("name_numbered", "")):
        evidence["SPECIAL:morpeko"] = c

def eur(v):
    return round(v, 2) if isinstance(v, (int, float)) else None

cards = json.loads((ROOT / "data" / "cards.json").read_text())
updated = kept = 0
for c in cards:
    src = (c.get("price") or {}).get("source")
    if src == "pricecharting":
        kept += 1
        continue  # Chinese Cubone: keep PriceCharting
    key = "SPECIAL:morpeko" if c.get("apiId") == "svp-206" else c.get("apiId")
    hit = evidence.get(key)
    if not hit:
        kept += 1  # e.g. Manaphy XY113: keep pokemontcg trend
        c["price"]["note"] = "pokemontcg.io trend (may lag; not in TCGGO coverage)"
        continue
    cm = hit["prices"]["cardmarket"]
    countries = {}
    for k, v in cm.items():
        if k.startswith("lowest_near_mint_") and not k.endswith("_EU_only") and isinstance(v, (int, float)):
            countries[k.replace("lowest_near_mint_", "")] = eur(v)
    links = hit.get("links") or {}
    c["price"] = {
        "trend": eur(cm.get("7d_average")),
        "trendLabel": "Cardmarket 7-day average",
        "lowNm": eur(cm.get("lowest_near_mint_EU_only") or cm.get("lowest_near_mint")),
        "lowNmLabel": "lowest offer, Near Mint (EU)",
        "countries": countries,
        "available": cm.get("available_items"),
        "currency": "EUR",
        "source": "cardmarket-tcggo",
        "url": links.get("cardmarket"),
        "tcggoUrl": hit.get("tcggo_url"),
        "cardmarketId": hit.get("cardmarket_id"),
        "asOf": TODAY,
    }
    updated += 1

(ROOT / "data" / "cards.json").write_text(json.dumps(cards, indent=1))
total = sum(c["price"]["trend"] for c in cards if c["price"] and c["price"]["trend"])
print(f"updated {updated}, kept {kept} | new total €{total:.2f}\n")
for c in cards:
    p = c["price"] or {}
    co = p.get("countries") or {}
    cstr = " ".join(f"{k}€{v}" for k, v in sorted(co.items()))
    print(f"{c['name']:<22} trend={str(p.get('trend')):<7} lowNM={str(p.get('lowNm')):<7} {cstr}")
