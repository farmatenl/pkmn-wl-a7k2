#!/usr/bin/env python3
"""Build final data/cards.json from cards.raw.json + verified API picks."""
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = {e["image"]: e for e in json.loads((ROOT / "data" / "cards.raw.json").read_text())}
M = json.loads((ROOT / "data" / "api_matches.json").read_text())
BYID = {c["id"]: c for cands in M["candidates"].values() for c in cands}
for extra in ("data/pikachu_all.json", "data/mew_all.json"):
    p = ROOT / extra
    if p.exists():
        for c in json.loads(p.read_text())["data"]:
            cm = (c.get("cardmarket") or {})
            pr = cm.get("prices") or {}
            BYID.setdefault(c["id"], {
                "id": c["id"], "name": c["name"], "set": c["set"]["name"],
                "number": c["number"], "rarity": c.get("rarity"),
                "cm_trend": pr.get("trendPrice"), "cm_avg7": pr.get("avg7"),
                "cm_low": pr.get("lowPrice"), "cm_url": cm.get("url"),
                "image": (c.get("images") or {}).get("large"),
            })

# visually verified picks (disambiguation sheets, 2026-08-27)
PICKS = {
    "IMG-20260606-WA0031.jpg": "sv10-185",        # Shaymin Destined Rivals IR
    "IMG-20260606-WA0056.jpg": "swsh12pt5gg-GG05",# Lapras CZ GG
    "IMG-20260606-WA0063.jpg": "swsh10-161",      # Beedrill V Astral Radiance alt art
    "IMG-20260608-WA0026.jpg": "swsh12pt5-14",    # Leafeon VSTAR CZ #14
    "IMG-20260626-WA0007.jpg": "sv6pt5-67",       # Horsea SFA IR
    "IMG-20260629-WA0019.jpg": "sv3pt5-175",      # Psyduck 151 IR
    "IMG-20260629-WA0025.jpg": "swsh9tg-TG02",    # Vaporeon Brilliant Stars TG
    "IMG-20260712-WA0014.jpg": "sv10-193",        # Misty's Psyduck DR IR
    "IMG-20260719-WA0001.jpg": "sv3pt5-173",      # Pikachu 151 IR
    "IMG-20260719-WA0003.jpg": "sv8-246",         # Lisia's Appeal SIR
    "IMG-20260719-WA0005.jpg": "sv10-203",        # TR Meowth DR IR
    "IMG-20260719-WA0007.jpg": "rsv10pt5-96",     # Tepig White Flare IR
    "IMG-20260719-WA0010.jpg": "zsv10pt5-129",    # Dwebble Black Bolt IR
    "IMG-20260803-WA0004.jpg": "svp-206",         # Marnie's Morpeko promo
    "IMG-20260803-WA0007.jpg": "svp-88",          # Pikachu promo
    "IMG-20260803-WA0012.jpg": "sv6-187",         # Chansey Twilight Masquerade IR
    "IMG-20260827-WA0016.jpg": "zsv10pt5-95",     # Foongus Black Bolt IR
    "IMG-20260827-WA0017.jpg": "rsv10pt5-165",    # Whimsicott ex White Flare SIR
    "IMG-20260827-WA0018.jpg": "sv2-226",         # Maushold PE IR
    "IMG-20260827-WA0020.jpg": "swsh12pt5gg-GG10",# Mew CZ GG
    "IMG-20260827-WA0019.jpg": "sm10-195",        # Dedenne GX Unbroken Bonds full art
    "IMG-20260827-WA0021.jpg": "xyp-XY113",       # Manaphy XY promo
}

ASOF = "2026-08-27"
cards = []
for img in sorted(RAW):
    raw = RAW[img]
    slug = img.replace("IMG-", "").replace(".jpg", "")
    card = {
        "id": slug,
        "image": f"images/{img}",
        "name": raw["name"],
        "language": raw["language"],
        "priority": "high",
    }
    if img == "IMG-20260606-WA0022.jpg":
        card.update({
            "set": "Chinese Gem Pack Vol. 3 (2025)",
            "number": "0407/07",
            "rarity": "Art Rare",
            "price": {"trend": 194.14, "avg7": None, "low": None, "currency": "EUR",
                      "source": "pricecharting",
                      "url": "https://www.pricecharting.com/game/pokemon-chinese-gem-pack-3/cubone-407",
                      "asOf": ASOF},
            "notes": "Simplified Chinese Art Rare; verified identical artwork to PC #407. Ungraded $226.09 converted at USD/EUR 0.85874 (2026-08-27). No Cardmarket listing found.",
        })
    elif img == "IMG-20260712-WA0013.jpg":
        card.update({
            "set": "Ascended Heroes", "number": "226/226",
            "rarity": "Illustration Rare",
            "apiId": "me2pt5-226",
            "price": {"trend": None, "avg7": None, "low": None, "currency": "EUR",
                      "source": "cardmarket", "url": None, "asOf": ASOF},
            "notes": "Set released Aug 2026; no Cardmarket price data yet. Re-check in a few weeks.",
        })
    else:
        pick = BYID[PICKS[img]]
        card.update({
            "set": pick["set"], "number": pick["number"], "rarity": pick["rarity"],
            "apiId": pick["id"],
            "price": {"trend": pick["cm_trend"], "avg7": pick["cm_avg7"],
                      "low": pick["cm_low"], "currency": "EUR",
                      "source": "cardmarket", "url": pick["cm_url"], "asOf": ASOF},
        })
    card["epick"] = {"matched": False}
    cards.append(card)

(ROOT / "data" / "cards.json").write_text(json.dumps(cards, indent=1))
priced = [c for c in cards if c["price"] and c["price"]["trend"]]
total = sum(c["price"]["trend"] for c in priced)
print(f"{len(cards)} cards, {len(priced)} priced, total trend EUR {total:.2f}")
for c in cards:
    t = c["price"] and c["price"]["trend"]
    print(f"  {c['id']:<22} {c['name']:<22} {str(c.get('set')):<34} {str(c.get('number')):<10} {t if t is not None else '—'}")
