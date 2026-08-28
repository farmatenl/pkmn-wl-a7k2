#!/usr/bin/env python3
"""Apply verified TCGGO batch-2 evidence (data/tcggo_matches2.json) to cards.json.

Guards (AGENTS.md: never apply unverified matches):
  1. Skip `_fallback` records — those are pokemontcg.io data (stale) and several
     carry wrong identities (e.g. g1-RC23 named "Swablu" vs owner-confirmed Pikachu).
  2. Apply only when record name AND number match the current card identity
     (owner-verified truth lives in cards.json; matches2 predates the c79156c fixes).
  3. If the card already has a cardmarket-tcggo trend, it must equal the record's
     7d_average — proves the record is the source of that number.
Also fills Leafeon VSTAR from data/tcggo/ep21-leafeon.json (owner-confirmed CZ 014).
Data hygiene: purge stale price.note on the e-pick Psyduck; relabel Manaphy's
source to pokemontcg.io-fallback (that is where its trend actually comes from).
"""
import json, pathlib, unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
ASOF = "2026-08-27"  # matches2 evidence was fetched 2026-08-27 (batch-2 session)


def norm_name(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join((s or "").lower().replace("-", " ").split())


def norm_num(s):
    s = str(s or "").strip().upper().split("/")[0]  # '070/072' -> '070'
    if s.isdigit():
        return str(int(s))
    return s


def full_price(rec):
    """Build the full price block from a TCGGO record (same shape as update_prices_tcggo)."""
    cm = rec["prices"]["cardmarket"]
    countries = {}
    for k, v in cm.items():
        if k.startswith("lowest_near_mint_") and not k.endswith("_EU_only") and isinstance(v, (int, float)):
            countries[k.replace("lowest_near_mint_", "")] = round(v, 2)
    links = rec.get("links") or {}
    return {
        "trend": round(cm["7d_average"], 2),
        "trendLabel": "Cardmarket 7-day average",
        "lowNm": round(v, 2) if isinstance(v := (cm.get("lowest_near_mint_EU_only") or cm.get("lowest_near_mint")), (int, float)) else None,
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


cards = json.loads((ROOT / "data" / "cards.json").read_text())
by_img = {c["image"].split("/")[-1]: c for c in cards}
m2 = json.loads((ROOT / "data" / "tcggo_matches2.json").read_text())

applied, skipped = [], []
for img, rec in sorted(m2.items()):
    cid = img.replace("IMG-", "").replace(".jpg", "")
    card = by_img.get(img)
    if not card:
        skipped.append((cid, "card removed from site (Emolga)"))
        continue
    if rec.get("_fallback"):
        skipped.append((cid, "pokemontcg.io fallback record (stale source, untrusted identity)"))
        continue
    if norm_name(rec.get("name")) != norm_name(card.get("name")) or norm_num(rec.get("card_number")) != norm_num(card.get("number")):
        skipped.append((cid, f"identity mismatch: record={rec.get('name')} {rec.get('card_number')} vs card={card.get('name')} {card.get('number')}"))
        continue
    p = card.get("price") or {}
    if p.get("source") == "cardmarket-tcggo" and p.get("trend") is not None and p["trend"] != rec["prices"]["cardmarket"].get("7d_average"):
        skipped.append((cid, f"trend drift: card={p['trend']} vs record 7d={rec['prices']['cardmarket'].get('7d_average')}"))
        continue
    card["price"] = full_price(rec)
    if rec.get("rarity") and card.get("rarity") != rec["rarity"]:
        card["rarity"] = rec["rarity"]  # canonical rarity from the applied record
    applied.append((cid, card["name"], card["price"]["trend"], card.get("rarity")))

# Leafeon VSTAR CZ 014 (owner-confirmed): full evidence already in data/tcggo/
ev = [c for c in json.loads((ROOT / "data" / "tcggo" / "ep21-leafeon.json").read_text())["data"]
      if c.get("tcgid") == "swsh12pt5-14"]
leaf = next(c for c in cards if c["id"] == "20260608-WA0026")
assert len(ev) == 1 and norm_name(ev[0]["name"]) == norm_name(leaf["name"]) and norm_num(ev[0]["card_number"]) == norm_num(leaf["number"])
leaf["price"] = full_price(ev[0])
if ev[0].get("rarity"):
    leaf["rarity"] = ev[0]["rarity"]
applied.append((leaf["id"], leaf["name"], leaf["price"]["trend"], leaf.get("rarity")))

# Hygiene: stale note + honest source label
for c in cards:
    p = c.get("price") or {}
    if c["id"] == "20260712-WA0013" and p.get("note"):
        del p["note"]
        skipped.append((c["id"], "purged stale price.note (price is e-pick retail now)"))
    if c["id"] == "20260827-WA0021" and p.get("source") == "cardmarket":
        p["source"] = "pokemontcg.io-fallback"
        skipped.append((c["id"], "source relabeled cardmarket -> pokemontcg.io-fallback (honest label)"))

(ROOT / "data" / "cards.json").write_text(json.dumps(cards, indent=1))

print(f"APPLIED {len(applied)}:")
for cid, name, trend, rar in applied:
    print(f"  {cid:<17} {name:<28} trend={trend:<7} rarity={rar}")
print(f"\nSKIPPED {len(skipped)}:")
for cid, why in skipped:
    print(f"  {cid:<17} {why}")
