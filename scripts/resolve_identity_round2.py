#!/usr/bin/env python3
"""Apply owner-verified identity corrections (2026-08-28 photo re-check) to cards.json.

Owner message:
  WA0058 - Pikachu    GEN RC29   (was Pikachu GEN RC23 = Swablu's number)
  WA0055 - Flareon EX GEN RC28   (was Flareon-EX GEN RC29 = Pikachu's number)
  WA0035 - Deerling   WHT 091    (was Black Bolt 091 = Petilil's slot)
  WA0041 - Piplup     CEC 239    (was Unified Minds 239 = Slowpoke & Psyduck-GX)
  WA0065 - Bulbasaur  SCR 143    (was Black Bolt 013 = Darumaka's slot)
Prices stay nulled until re-priced from TCGGO (fetch_tcggo_round3.py + apply_round3.py).
"""
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIX = {
    "20260606-WA0058": {"set": "Generations", "number": "RC29", "apiId": "g1-RC29"},
    "20260606-WA0055": {"set": "Generations", "number": "RC28", "apiId": "g1-RC28"},
    "20260606-WA0035": {"set": "White Flare", "number": "091", "apiId": "rsv10pt5-91"},
    "20260606-WA0041": {"set": "Cosmic Eclipse", "number": "239", "apiId": "sm11-239"},
    "20260606-WA0065": {"set": "Stellar Crown", "number": "143", "apiId": "sv7-143"},
}
OLD = {
    "20260606-WA0058": ("Generations", "RC23"),
    "20260606-WA0055": ("Generations", "RC29"),
    "20260606-WA0035": ("Black Bolt", "091"),
    "20260606-WA0041": ("Unified Minds", "239"),
    "20260606-WA0065": ("Black Bolt", "013"),
}

cards = json.loads((ROOT / "data" / "cards.json").read_text())
for c in cards:
    if c["id"] not in FIX:
        continue
    f = FIX[c["id"]]
    oset, onum = OLD[c["id"]]
    assert c["set"] == oset and c["number"] == onum, (c["id"], c["set"], c["number"])
    c.update(f)
    # drop the 'Identity under re-verification' block, keep earlier notes
    base = (c.get("notes") or "").split(" Identity under re-verification:")[0].strip()
    c["notes"] = (base + " " if base else "") + (
        f"Identity corrected 2026-08-28 after owner photo re-check: {c['name']}, "
        f"{f['set']} #{f['number']} (was listed as {oset} #{onum}, which belongs to a "
        f"different card). Re-pricing pending.")
    print(f"{c['id']:<17} {c['name']:<12} -> {f['set']} #{f['number']}  apiId={f['apiId']}")

(ROOT / "data" / "cards.json").write_text(json.dumps(cards, indent=1))
print("\nprices still nulled; run fetch_tcggo_round3.py + apply_round3.py next")
