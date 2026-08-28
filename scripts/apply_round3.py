#!/usr/bin/env python3
"""Apply round-3 TCGGO evidence (data/tcggo/round3-*.json, fetched 2026-08-28).

Targets: the 5 identity-corrected cards (owner photo re-check) + Lopunny CEC x2 +
Keldeo GG07 + Stufful ME154 + Altaria GG19. Cosmic Eclipse apiIds corrected to sm12-*
(sm11-239/225/226 were wrong-number records; sm12-225/226 7d averages match the
existing WA0046/47 trends exactly, confirming identity).
Guards as always: record name+number must match cards.json; trend drift logged.
"""
import json, pathlib, unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
ASOF = "2026-08-28"

def norm_name(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.lower().replace("-", " ").split())

def norm_num(s):
    s = str(s or "").strip().upper().split("/")[0]
    return str(int(s)) if s.isdigit() else s

def full_price(rec):
    cm = rec["prices"]["cardmarket"]
    countries = {}
    for k, v in cm.items():
        if k.startswith("lowest_near_mint_") and not k.endswith("_EU_only") and isinstance(v, (int, float)):
            countries[k.replace("lowest_near_mint_", "")] = round(v, 2)
    links = rec.get("links") or {}
    lowNm = cm.get("lowest_near_mint_EU_only") or cm.get("lowest_near_mint")
    return {
        "trend": round(cm["7d_average"], 2),
        "trendLabel": "Cardmarket 7-day average",
        "lowNm": round(lowNm, 2) if isinstance(lowNm, (int, float)) else None,
        "lowNmLabel": "lowest offer, Near Mint (EU)",
        "countries": countries,
        "available": cm.get("available_items"),
        "currency": "EUR",
        "source": "cardmarket-tcggo",
        "url": links.get("cardmarket"),
        "tcggoUrl": rec.get("tcggo_url"),
        "cardmarketId": rec.get("cardmarket_id"),
        "asOf": ASOF,
    }

# apiId corrections (CEC is sm12, not sm11) + targets
APIID_FIX = {
    "20260606-WA0041": "sm12-239",
    "20260606-WA0046": "sm12-225",
    "20260606-WA0047": "sm12-226",
    "20260606-WA0039": "swsh12pt5gg-GG07",   # Keldeo CZ GG (never had an apiId)
    "20260629-WA0020": "me1-154",            # Stufful Mega Evolution
    "20260629-WA0021": "swsh12pt5gg-GG19",   # Altaria CZ GG
}
TARGETS = ["20260606-WA0058", "20260606-WA0055", "20260606-WA0035", "20260606-WA0041",
           "20260606-WA0065", "20260606-WA0046", "20260606-WA0047", "20260606-WA0039",
           "20260629-WA0020", "20260629-WA0021"]

# index round-3 evidence by tcgid
evidence = {}
for f in sorted((ROOT / "data" / "tcggo").glob("round3-*.json")):
    for c in json.loads(f.read_text()):
        if c.get("tcgid"):
            evidence[c["tcgid"]] = c

cards = json.loads((ROOT / "data" / "cards.json").read_text())
for c in cards:
    if c["id"] in APIID_FIX:
        c["apiId"] = APIID_FIX[c["id"]]

applied, skipped = [], []
for c in cards:
    if c["id"] not in TARGETS:
        continue
    rec = evidence.get(c.get("apiId"))
    if not rec:
        skipped.append((c["id"], f"no round3 evidence for apiId={c.get('apiId')}"))
        continue
    if norm_name(rec.get("name")) != norm_name(c.get("name")) or norm_num(rec.get("card_number")) != norm_num(c.get("number")):
        skipped.append((c["id"], f"identity mismatch: record={rec.get('name')} {rec.get('card_number')} vs card={c.get('name')} {c.get('number')}"))
        continue
    old = (c.get("price") or {}).get("trend")
    c["price"] = full_price(rec)
    if rec.get("rarity") and c.get("rarity") != rec["rarity"]:
        c["rarity"] = rec["rarity"]
    if "Re-pricing pending." in (c.get("notes") or ""):
        c["notes"] = c["notes"].replace("Re-pricing pending.", f"Re-priced from TCGGO/Cardmarket 7-day avg, {ASOF}.")
    applied.append((c["id"], c["name"], old, c["price"]["trend"], c.get("rarity")))

(ROOT / "data" / "cards.json").write_text(json.dumps(cards, indent=1))
print(f"APPLIED {len(applied)}:")
for cid, name, old, new, rar in applied:
    drift = "" if old in (None, new) else f"  (was {old})"
    print(f"  {cid:<17} {name:<28} trend={new}{drift}  rarity={rar}")
print(f"\nSKIPPED {len(skipped)}:")
for cid, why in skipped:
    print(f"  {cid:<17} {why}")
