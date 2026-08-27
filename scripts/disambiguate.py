#!/usr/bin/env python3
"""Build side-by-side sheets: user photo | API candidate images, for visual disambiguation."""
import json, urllib.request, pathlib
from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parent.parent
M = json.loads((ROOT / "data" / "api_matches.json").read_text())
BYID = {}
for img, cands in M["candidates"].items():
    for c in cands:
        BYID[c["id"]] = c

SHEETS = {
    "beedrill":  ("IMG-20260606-WA0063.jpg", ["swsh10-1", "swsh10-160", "swsh10-161"]),
    "leafeon":   ("IMG-20260608-WA0026.jpg", ["swshp-SWSH195", "swsh12pt5-14", "swsh12pt5gg-GG35"]),
    "lisia":     ("IMG-20260719-WA0003.jpg", ["sv8-179", "sv8-234", "sv8-246"]),
    "meowth":    ("IMG-20260719-WA0005.jpg", ["basep-18", "sv10-149", "sv10-203"]),
    "mew":       ("IMG-20260827-WA0019.jpg", ["sv3pt5-151", "sv3pt5-193", "sv3pt5-205"]),
    "dedenne":   ("IMG-20260827-WA0020.jpg", ["sm10-57", "sm10-195", "sm10-195a", "sm10-219"]),
}

CACHE = pathlib.Path("/tmp/cardimgs"); CACHE.mkdir(exist_ok=True)
TH = 460

def load_card(cid):
    p = CACHE / f"{cid}.png"
    if not p.exists():
        url = BYID[cid]["image"]
        req = urllib.request.Request(url, headers={"User-Agent": "wishlist/0.1"})
        with urllib.request.urlopen(req, timeout=30) as r, open(p, "wb") as f:
            f.write(r.read())
    return Image.open(p).convert("RGB")

for name, (photo, cids) in SHEETS.items():
    ph = Image.open(ROOT / "images" / photo).convert("RGB")
    ph.thumbnail((TH, TH * 2))
    tiles = [("PHOTO", ph)]
    for cid in cids:
        try:
            im = load_card(cid)
            im.thumbnail((TH, TH * 2))
            tiles.append((cid, im))
        except Exception as e:
            print(f"img fail {cid}: {e}")
    h = max(t.height for _, t in tiles) + 46
    w = sum(t.width + 10 for _, t in tiles) + 10
    sheet = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(sheet)
    x = 10
    for label, t in tiles:
        sheet.paste(t, (x, 36))
        d.text((x, 8), label, fill="black")
        x += t.width + 10
    out = f"/tmp/sheet-{name}.png"
    sheet.save(out)
    print(out, sheet.size)
