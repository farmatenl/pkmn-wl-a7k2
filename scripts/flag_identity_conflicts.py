#!/usr/bin/env python3
"""Null out prices on 5 batch-2 cards whose set+number identity conflicts with
both pokemontcg.io and TCGGO's own fallback records (2026-08-28 audit).

The wishlist names/numbers for these cards disagree with the card actually living
at that set+number (e.g. 'Pikachu RC23' vs RC23=Swablu). Until the owner re-verifies
the photos, the displayed price would be *another card's* price — "unpriced beats
fabricated" (AGENTS.md). Evidence trail: data/tcggo_matches2.json `_fallback` records
+ scripts/backfill_rarity.py conflict report.

Revert: `git revert` of the committing change or restore trend from git history.
"""
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFLICTS = {
    "20260606-WA0035": ("Deerling", "Petilil", None),
    "20260606-WA0041": ("Piplup", "Slowpoke & Psyduck-GX", None),
    "20260606-WA0055": ("Flareon-EX", "Pikachu",
                          "Previous price €106.02 (PriceCharting, looked up by name — may still be "
                          "right for the card if only the printed number is wrong)."),
    "20260606-WA0058": ("Pikachu", "Swablu", None),
    "20260606-WA0065": ("Bulbasaur", "Darumaka", None),
}

cards = json.loads((ROOT / "data" / "cards.json").read_text())
for c in cards:
    if c["id"] not in CONFLICTS:
        continue
    name, api_name, extra = CONFLICTS[c["id"]]
    assert c["name"] == name, c["id"]
    old = (c.get("price") or {}).get("trend")
    c["price"] = {"trend": None, "currency": None, "source": None, "asOf": "2026-08-28"}
    note = (f"Identity under re-verification: {c.get('set')} #{c.get('number')} is listed as "
            f"{api_name} on pokemontcg.io/TCGGO, not {name}. Price removed 2026-08-28 until the "
            f"photo is re-checked; the number belongs to the other card. "
            + (extra or f"Previous price €{old} (for the other card's listing)."))
    c["notes"] = (c["notes"] + " " + note) if c.get("notes") else note
    print(f"{c['id']:<17} {name:<14} price nulled (was {old}) | set={c.get('set')} #{c.get('number')}")

(ROOT / "data" / "cards.json").write_text(json.dumps(cards, indent=1))
print("\nOwner action: re-check photos for set/number; fix identity, then re-price.")
