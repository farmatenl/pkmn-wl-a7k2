# AGENTS.md — Pokémon Wishlist

Static, dependency-free single-page wishlist of Pokémon TCG cards. Public GitHub Pages site,
shared by URL. **Privacy convention: no personal names anywhere in this repo or on the page**
(the URL slug is intentionally non-obvious; keep it that way).

- Live: https://farmatenl.github.io/pkmn-wl-a7k2/
- Repo: `farmatenl/pkmn-wl-a7k2` (branch `main`, GitHub Pages `build_type=legacy`, deploy from `/`)
- Stack: vanilla HTML/CSS/JS. No build step, no npm, no frameworks. Keep it that way.

## Layout

```
index.html            page shell (header, toolbar, grid, modal)
style.css             mobile-first; CSS custom props at top define the theme
app.js                all logic: render, filters/sort, modal, live stock
images/               card scans (filenames are the stable card ids, e.g. 20260629-WA0019)
data/cards.json       THE data file the page renders (generated — see pipeline)
data/cards.raw.json   vision-identification notes (input to write_cards.py)
data/epick-stock.json e-pick catalog snapshot at build time (fallback for live check)
data/tcggo/           raw TCGGO API responses per episode (evidence trail)
scripts/              python data pipeline (stdlib only)
```

## Data pipeline (how cards.json is made)

1. `scripts/write_cards.py` — regenerates `data/cards.json` from `cards.raw.json` +
   verified API picks (PICKS table = visually disambiguated matchings). Rerunning it
   **overwrites** later price updates, so prefer the targeted scripts below.
2. `scripts/update_prices_tcggo.py` — applies TCGGO (live Cardmarket) prices onto
   cards.json using `data/tcggo/*.json` evidence files. Keeps PriceCharting for the
   Chinese card and pokemontcg.io for XY promos (not in TCGGO).
3. `scripts/fetch_epick_stock.py` + `finalize_matches.py` — store snapshot + the 6
   human-verified e-pick matches. Verified matches live in `finalize_matches.py`.

Price fields on a card (`price.source` decides the modal layout):
- `cardmarket-tcggo`: `trend` = CM **7-day average** (headline), `lowNm` = lowest NM offer,
  `countries` = {DE,FR,ES,IT} lowest NM, `available` = offer count, `url` = deep CM link.
- `pricecharting` / `e-pick retail`: single `trend` + explanatory `notes`.

## Hard-won facts (do not re-learn these)

- **pokemontcg.io Cardmarket prices are stale** (months behind). Validated 2026-08-27:
  CM site showed €57.03 7d-avg for Psyduck 151 #175; TCGGO matched exactly; pokemontcg
  said €23.66. Use pokemontcg.io only for card *data* (images, IDs) and for cards TCGGO lacks.
- **TCGGO cardmarket prices are already EUR floats.** Their docs sample shows integers that
  look like cents for *graded* prices only. Never divide by 100 for the cardmarket block.
- TCGGO `lowest_near_mint` (global) can exceed a per-country lowest — fields have different
  semantics; that's why the UI labels them separately instead of treating one as truth.
- TCGGO has **no NL country field** (DE/FR/ES/IT only). True NL price = e-pick (live badge).
- TCGGO via RapidAPI: BASIC plan, 30 req/min. Sleep ≥2 s between calls. Key lives in
  `~/.rapidapi_key` (chmod 600) — **never commit, never paste it in chat or logs**.
- store.e-pick.xyz (Shopify) sends `CORS: *` on `/products.json` and `/products/<handle>.js`.
  The page live-checks stock client-side (6h sessionStorage cache). `.js` prices are in CENTS.
- GitHub Pages CDN caches ~10 min (`max-age=600`). After deploying, verify with cache-busting
  (`curl "...?nocache=$(date +%s)"`) and test in a **fresh browser tab** — reused tabs serve
  stale JS and will gaslight your verification.
- e-pick descriptions are parseable: `single card from {Set} ({number}). Language: {lang}.`
  Store stocks Japanese prints too ("White Flare JP") — matches must filter `language: English`
  (wishlist convention: EN primary, JP/CN secondary).

## Best practices

- **Never invent a price.** Every number traces to an API response, a manual page visit
  (recorded in `notes`), or a verified store listing. Unpriced beats fabricated.
- **Every store match is human-verified** (same set, same printing, right language).
  No-match → no badge; absence is honest.
- Card identity changes go through visual disambiguation (see `scripts/disambiguate.py`
  pattern: user photo | candidate images side-by-side) — never match on name alone.
- `node --check app.js` before every commit. Commit after every logical change; push = deploy.
- Modal history rule: **exactly one code path may call `history.back()`** (currently
  `closeModal`, guarded by `closingFromHistory`). The dialog `close` event fires on every
  close path; if you add one, respect the guard or you'll double-pop users out of the page.
- Verify user-facing changes end-to-end (open modal, toggle filter, sort) — the toolbar,
  filter, and sort were all browser-verified before handoff, keep that bar.

## Known open items

- NL-specific price exists only for the 6 e-pick cards; candidate fix: add 1–2 more NL
  webshops with clean JSON endpoints (same pattern as e-pick).
- Weekly price refresh (rerun TCGGO fetch + `update_prices_tcggo.py` + push) is cron-ready;
  free tier covers it (~30 calls/run at 30 req/min with sleeps).
- `IMG-20260719-WA0010.jpg` (Manaphy XY113) price still from pokemontcg.io trend — recheck
  when TCGGO covers XY Black Star Promos.
