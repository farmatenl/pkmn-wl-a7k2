#!/usr/bin/env python3
"""Fetch fresh e-pick catalog and build verified candidate matches for batch-2 cards.

Strict rules (batch-1 standard):
- English printings only ("Language: English" in description, or EN evident in title)
- Number must match exactly (description "(0NN)" or title contains number/GG code)
- Set tokens must appear in title+description
Anything unverified stays matched=false. Absent beats wrong.
"""
import json, pathlib, re, time, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "epick_candidates.json"

def fetch_catalog():
    prods, page = [], 1
    while True:
        url = f"https://store.e-pick.xyz/products.json?limit=250&page={page}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        batch = json.loads(urllib.request.urlopen(req, timeout=30).read())["products"]
        if not batch:
            break
        prods.extend(batch)
        page += 1
        time.sleep(0.4)
        if page > 12:
            break
    return prods

SET_TOKENS = {
    "20260606-WA0033": ["Scarlet", "Violet", "SVI", "Base"],          # SV base
    "20260606-WA0035": ["Black Bolt"],
    "20260606-WA0038": ["Chaos Rising", "CRI"],
    "20260606-WA0039": ["Crown Zenith", "GG07"],
    "20260606-WA0041": ["Unified Minds"],
    "20260606-WA0042": ["White Flare"],
    "20260606-WA0043": ["Stellar Crown"],
    "20260606-WA0045": ["Cosmic Eclipse"],
    "20260606-WA0046": ["Cosmic Eclipse"],
    "20260606-WA0051": ["Generations", "RC32"],
    "20260606-WA0055": ["Generations", "RC29"],
    "20260606-WA0056": ["Crown Zenith", "GG05"],
    "20260606-WA0058": ["Generations", "RC23"],
    "20260606-WA0063": ["Astral Radiance"],
    "20260606-WA0065": ["Black Bolt"],
    "20260608-WA0026": ["Crown Zenith"],
    "20260626-WA0007": ["Shrouded Fable"],
    "20260629-WA0020": ["Mega Evolution", "MEG"],
    "20260629-WA0021": ["Crown Zenith", "GG19"],
    "20260629-WA0025": ["Brilliant Stars", "TG02", "Trainer Gallery"],
    "20260719-WA0003": ["Surging Sparks"],
    "20260719-WA0005": ["Destined Rivals"],
    "20260719-WA0007": ["White Flare"],
    "20260719-WA0010": ["Black Bolt"],
    "20260803-WA0004": ["Morpeko", "Promo"],
    "20260803-WA0007": ["Pikachu", "Promo"],
    "20260803-WA0012": ["Twilight Masquerade"],
    "20260827-WA0016": ["Black Bolt"],
    "20260827-WA0017": ["White Flare"],
    "20260827-WA0018": ["Paldea Evolved"],
    "20260827-WA0019": ["Unbroken Bonds"],
    "20260827-WA0020": ["Crown Zenith", "GG10"],
    "20260827-WA0021": ["Manaphy", "Promo", "XY"],
    "20260827-WA0028": ["Journey Together"],
    "20260827-WA0029": ["Destined Rivals"],
    "20260827-WA0030": ["Twilight Masquerade"],
}
# extra number formats to try per card id (GG/RC/TG/XY codes)
NUM_EXTRA = {
    "20260606-WA0039": ["GG07"], "20260606-WA0056": ["GG05"], "20260606-WA0051": ["RC32"],
    "20260606-WA0055": ["RC29"], "20260606-WA0058": ["RC23"], "20260608-WA0026": ["GG35"],
    "20260629-WA0021": ["GG19"], "20260629-WA0025": ["TG02"], "20260827-WA0020": ["GG10"],
    "20260827-WA0021": ["XY113"],
}

def norm_num(n):
    return str(n).split("/")[0].zfill(3)

def main():
    cards = json.loads((ROOT / "data" / "cards.json").read_text())
    targets = [c for c in cards if c["id"] in SET_TOKENS]
    prods = fetch_catalog()
    print(f"catalog: {len(prods)} products")
    out = {}
    for c in targets:
        cid = c["id"]
        nums = [norm_num(c["number"])] + NUM_EXTRA.get(cid, [])
        name_tokens = [w for w in re.split(r"[\s&'-]+", c["name"].lower()) if len(w) > 2][:2]
        cands = []
        for p in prods:
            title = p.get("title", "")
            desc = " ".join(x.get("value", "") for x in (p.get("body_html") and [{"value": re.sub(r"<[^>]+>", " ", p["body_html"])}] or []))
            blob = f"{title} {desc}"
            if "english" not in blob.lower():
                continue
            if not any(n in blob for n in nums):
                continue
            toks = SET_TOKENS[cid]
            set_ok = any(t.lower() in blob.lower() for t in toks)
            name_ok = all(t in blob.lower() for t in name_tokens) if name_tokens else True
            if set_ok and name_ok:
                v = p["variants"][0]
                cands.append({
                    "handle": p["handle"], "title": title,
                    "price": float(v["price"]) / 100, "available": v["available"],
                    "url": f"https://store.e-pick.xyz/products/{p['handle']}",
                })
        out[cid] = {"card": f"{c['name']} — {c['set']} #{c['number']}", "candidates": cands}
        print(f"{cid} {c['name']} #{c['number']}: {len(cands)} candidate(s)")
        for x in cands[:4]:
            print(f"    {x['title'][:70]} | €{x['price']} | avail={x['available']}")
    OUT.write_text(json.dumps(out, indent=1))
    print(f"\nwrote {OUT}")

if __name__ == "__main__":
    main()
