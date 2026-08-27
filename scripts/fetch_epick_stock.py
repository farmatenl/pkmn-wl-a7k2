#!/usr/bin/env python3
"""Fetch full e-pick Shopify catalog snapshot; match wishlist cards against it."""
import json, re, time, urllib.request, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = "https://store.e-pick.xyz"

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "wishlist-builder/0.1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

# 1) snapshot
products, page = [], 1
while page <= 10:
    d = fetch(f"{BASE}/products.json?limit=250&page={page}")
    batch = d.get("products", [])
    products.extend(batch)
    print(f"page {page}: +{len(batch)} (total {len(products)})")
    if len(batch) < 250:
        break
    page += 1
    time.sleep(0.5)

stock = {"fetchedAt": time.strftime("%Y-%m-%d"), "count": len(products), "products": []}
for p in products:
    body = re.sub(r"<[^>]+>", " ", p.get("body_html") or "")
    m = re.search(r"single card from (.+?) \(([^)]+)\)\. Language: (\w+)\. Condition: ([^.\n]+)", body)
    v = (p.get("variants") or [{}])[0]
    stock["products"].append({
        "title": p["title"], "handle": p["handle"],
        "url": f"{BASE}/products/{p['handle']}",
        "price": v.get("price"), "available": bool(v.get("available")),
        "set": m.group(1).strip() if m else None,
        "number": m.group(2).strip() if m else None,
        "language": m.group(3) if m else None,
        "condition": m.group(4).strip() if m else None,
        "tags": p.get("tags", []),
    })
(ROOT / "data" / "epick-stock.json").write_text(json.dumps(stock, indent=1))
singles = [p for p in stock["products"] if p["set"]]
print(f"snapshot: {len(products)} products, {len(singles)} parsed singles")

# 2) match
def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())

cards = json.loads((ROOT / "data" / "cards.json").read_text())
print("\nmatching:")
for c in cards:
    cnum = norm(str(c.get("number", "")).split("/")[0])
    cname = norm(c["name"])
    hits = []
    for p in singles:
        pnum = norm(p["number"] or "")
        if not pnum or pnum != cnum:
            continue
        pt = norm(p["title"])
        if cname and (cname in pt or pt in cname or norm(c["name"].replace("'s", "")) in pt):
            hits.append(p)
    c["epick"] = {"matched": bool(hits),
                  "products": [{"url": h["url"], "title": h["title"], "price": h["price"],
                                "available": h["available"], "condition": h["condition"],
                                "language": h["language"]} for h in hits[:3]]}
    status = "; ".join(f"{h['title']} €{h['price']} avail={h['available']} [{h['condition']}]" for h in hits[:3]) or "—"
    print(f"  {c['name']:<22} #{str(c.get('number')):<10} -> {status}")

(ROOT / "data" / "cards.json").write_text(json.dumps(cards, indent=1))
print("\nupdated cards.json with epick matches")
