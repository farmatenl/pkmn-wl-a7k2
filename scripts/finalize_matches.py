#!/usr/bin/env python3
"""Overwrite epick matches in cards.json with human-verified EN-only matches."""
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = "https://store.e-pick.xyz"

VERIFIED = {
    "20260606-WA0031": {  # Shaymin DR 185
        "products": [{"url": f"{BASE}/products/shaymin-11", "title": "Shaymin", "price": "13.00", "available": False, "condition": "Near Mint"}]},
    "20260606-WA0056": {  # Lapras CZ GG05
        "products": [{"url": f"{BASE}/products/lapras-18", "title": "Lapras", "price": "30.00", "available": False, "condition": "Near Mint"}]},
    "20260629-WA0019": {  # Psyduck 151 175
        "products": [{"url": f"{BASE}/products/psyduck-56", "title": "Psyduck", "price": "60.00", "available": True, "condition": "Near Mint"}]},
    "20260712-WA0013": {  # Psyduck Ascended Heroes 226
        "products": [{"url": f"{BASE}/products/psyduck-53", "title": "Psyduck", "price": "81.00", "available": True, "condition": "Near Mint"}]},
    "20260712-WA0014": {  # Misty's Psyduck DR 193
        "products": [{"url": f"{BASE}/products/mistys-psyduck-11", "title": "Misty's Psyduck", "price": "70.00", "available": False, "condition": "Near Mint"}]},
    "20260719-WA0001": {  # Pikachu 151 173 (two listings; cheapest available)
        "products": [{"url": f"{BASE}/products/pikachu-226", "title": "Pikachu", "price": "76.00", "available": True, "condition": "Good"},
                      {"url": f"{BASE}/products/pikachu-225", "title": "Pikachu", "price": "87.00", "available": True, "condition": "Excellent"}]},
}

cards = json.loads((ROOT / "data" / "cards.json").read_text())
for c in cards:
    key = c["id"]
    if key in VERIFIED:
        c["epick"] = {"matched": True, "verifiedBy": "hermes", **VERIFIED[key]}
    else:
        c["epick"] = {"matched": False}
    # Ascended Heroes Psyduck: store retail is the only real price reference
    if key == "20260712-WA0013":
        c["price"] = {"trend": 81.00, "avg7": None, "low": None, "currency": "EUR",
                      "source": "e-pick retail",
                      "url": f"{BASE}/products/psyduck-53", "asOf": "2026-08-27"}
        c["notes"] = "Set released Aug 2026; no Cardmarket market data yet. Price shown is e-pick retail (in stock there)."

(ROOT / "data" / "cards.json").write_text(json.dumps(cards, indent=1))
m = [c for c in cards if c["epick"]["matched"]]
p = [c for c in cards if c["price"] and c["price"]["trend"]]
print(f"{len(cards)} cards | {len(p)} priced | {len(m)} at e-pick | total trend EUR {sum(c['price']['trend'] for c in p):.2f}")
