/* Pokémon wishlist - vanilla JS, no dependencies. */
"use strict";

const STORE = "https://store.e-pick.xyz";
const CACHE_KEY = "epick-live-v1";
const CACHE_TTL = 6 * 60 * 60 * 1000; // 6h politeness window

let CARDS = [];

const eur = (n) =>
  n == null ? "n/a" : `€${Number(n).toLocaleString("en-NL", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

function priceSourceLabel(src) {
  if (src === "pricecharting") return "PriceCharting ungraded (converted to EUR)";
  if (src === "cardmarket-tcggo") return "Cardmarket 7-day average (EU)";
  if (src === "e-pick retail") return "e-pick retail price (NL)";
  if (src === "pokemontcg.io-fallback") return "pokemontcg.io Cardmarket trend (may lag)";
  return "Cardmarket trend (EU)";
}

function countryGrid(price) {
  const co = price && price.countries;
  if (!co || !Object.keys(co).length) return "";
  const cells = Object.keys(co).sort()
    .map((k) => `<div class="co"><span class="k">${k}</span><span class="v mono">${eur(co[k])}</span></div>`)
    .join("");
  return `<div><span class="k">Lowest NM by country</span><div class="co-grid">${cells}</div></div>`;
}

async function loadCards() {
  const res = await fetch("data/cards.json");
  if (!res.ok) throw new Error(`cards.json ${res.status}`);
  CARDS = await res.json();
}

/* ---------- rendering ---------- */

function tile(card, index, animate) {
  const el = document.createElement("button");
  el.type = "button";
  el.className = "card" + (animate ? " enter" : "");
  el.dataset.id = card.id;
  if (animate) el.style.setProperty("--i", Math.min(index, 12));
  const p = card.price || {};
  el.innerHTML = `
    <span class="card-media">
      <img loading="lazy" src="${card.image}" alt="${card.name}, ${card.set || ""}${card.number ? " " + card.number : ""}">
    </span>
    <span class="card-body">
      <span class="card-name">${card.name}</span>
      <span class="card-set">${card.set || ""}${card.number ? " · " + card.number : ""}</span>
      <span class="card-foot">
        <span class="price">${eur(p.trend)}</span>
        ${inStock(card) ? `<span class="stock-badge">In stock</span>` : ""}
      </span>
    </span>`;
  el.addEventListener("click", () => openModal(card));
  return el;
}

/* ---------- filters & sorting ---------- */

let activeSort = "default";
let stockOnly = false;

function inStock(card) {
  return !!(card.epick && card.epick.matched &&
    ((card.epick.live && card.epick.live.some((p) => p.available)) ||
     (!card.epick.live && (card.epick.products || []).some((p) => p.available))));
}

function visibleCards() {
  let list = stockOnly ? CARDS.filter(inStock) : CARDS.slice();
  if (activeSort === "price-asc" || activeSort === "price-desc") {
    const dir = activeSort === "price-asc" ? 1 : -1;
    const val = (c) => (c.price && c.price.trend != null ? c.price.trend : null);
    list.sort((a, b) => {
      const va = val(a), vb = val(b);
      if (va == null && vb == null) return 0;
      if (va == null) return 1;  // unpriced always sink
      if (vb == null) return -1;
      return dir * (va - vb);
    });
  } else if (activeSort === "name") {
    list.sort((a, b) => a.name.localeCompare(b.name, "en", { sensitivity: "base" }) ||
      (a.number || "").localeCompare(b.number || ""));
  }
  return list;
}

let firstRender = true;

function renderGrid() {
  const grid = document.getElementById("grid");
  const list = visibleCards();

  if (!list.length) {
    grid.innerHTML = CARDS.length
      ? `<div class="state">
           <p class="state-title">Nothing is in stock at e-pick right now.</p>
           <p>Local stock moves fast. <button type="button" class="linklike" data-action="show-all">Show the full wishlist</button> instead.</p>
         </div>`
      : `<div class="state"><p class="state-title">No cards yet.</p></div>`;
  } else {
    grid.replaceChildren(...list.map((c, i) => tile(c, i, firstRender)));
  }

  const priced = CARDS.filter((c) => c.price && c.price.trend != null);
  const total = priced.reduce((s, c) => s + c.price.trend, 0);
  const asOf = priced.find((c) => c.price.asOf)?.price.asOf;
  document.getElementById("meta-line").textContent =
    `${CARDS.length} cards, ${eur(total)} total${asOf ? ` (updated ${asOf})` : ""}`;

  document.getElementById("count-line").textContent =
    stockOnly ? `${list.length} of ${CARDS.length} shown` : "";

  firstRender = false;
}

/* ---------- modal ---------- */

const modal = document.getElementById("card-modal");
let modalOpen = false;
let closingFromHistory = false;

function epickProductsLiveFirst(card) {
  const any = card.epick.products || [];
  const live = card.epick.live;
  const available = (list) => list.some((p) => p.available);
  if (live) return available(live) ? live : any;
  const snapshot = any.filter((p) => p.available);
  return snapshot.length ? snapshot : any;
}

function modalEpickLine(card) {
  if (!card.epick || !card.epick.matched) return "";
  const list = epickProductsLiveFirst(card);
  if (!list.length) return "";
  const best = list.reduce((a, b) => (Number(a.price) <= Number(b.price) ? a : b));
  const liveMark = card.epick.live ? "" : " (build-time snapshot)";
  if (list.some((p) => p.available)) {
    return `<p class="epick-line in">In stock at e-pick (NL) for ${eur(best.price)}${liveMark}.</p>`;
  }
  return `<p class="epick-line out">Seen at e-pick (NL) at ${eur(best.price)}, currently out of stock${liveMark}.</p>`;
}

function openModal(card) {
  const p = card.price || {};
  const rows = [];
  if (p.trend != null) rows.push(`<div><span class="k">${priceSourceLabel(p.source)}</span><span class="v"><strong>${eur(p.trend)}</strong></span></div>`);
  if (p.avg7 != null) rows.push(`<div><span class="k">Cardmarket 7-day avg (EU)</span><span class="v">${eur(p.avg7)}</span></div>`);
  if (p.lowNm != null) rows.push(`<div><span class="k">Lowest offer, Near Mint (EU)</span><span class="v">${eur(p.lowNm)}</span></div>`);
  if (p.low != null) rows.push(`<div><span class="k">Cardmarket low</span><span class="v">${eur(p.low)}</span></div>`);
  rows.push(countryGrid(p));
  if (p.available != null) rows.push(`<div><span class="k">Cardmarket offers</span><span class="v">${p.available}</span></div>`);

  const links = [];
  if (p.url) {
    const label = p.source === "pricecharting" ? "View on PriceCharting"
      : p.source === "e-pick retail" ? "View at e-pick"
      : "View on Cardmarket";
    links.push(`<a class="btn" href="${p.url}" target="_blank" rel="noopener">${label}</a>`);
  } else if (card.links && card.links.cardmarket) {
    // owner-verified Cardmarket link stored on the card (price block has no url)
    links.push(`<a class="btn" href="${card.links.cardmarket}" target="_blank" rel="noopener">View on Cardmarket</a>`);
  }
  if (card.epick && card.epick.matched) {
    const best = (card.epick.products || []).reduce((a, b) => (Number(a.price) <= Number(b.price) ? a : b));
    if (best && best.url !== p.url) {
      links.push(`<a class="btn secondary" href="${best.url}" target="_blank" rel="noopener">View e-pick listing</a>`);
    }
  }

  const sub1 = `${card.set || ""}${card.number ? " · #" + card.number : ""}`;
  const sub2 = [card.rarity, card.language].filter(Boolean).join(" · ");

  document.getElementById("modal-body").innerHTML = `
    <figure class="modal-figure">
      <img src="${card.image}" alt="${card.name}, ${card.set || ""}">
    </figure>
    <div class="modal-info">
      <h2 id="modal-title">${card.name}</h2>
      ${sub1 ? `<p class="sub">${sub1}</p>` : ""}
      ${sub2 ? `<p class="sub">${sub2}</p>` : ""}
      <div class="price-rows">${rows.join("") || '<div><span class="k">Price</span><span class="v">not priced yet</span></div>'}</div>
      ${p.note ? `<p class="note">${p.note}</p>` : ""}
      ${modalEpickLine(card)}
      ${card.notes ? `<p class="note">${card.notes}</p>` : ""}
      <div class="modal-actions">${links.join("")}</div>
    </div>`;
  modal.showModal();
  modalOpen = true;
  history.pushState({ modal: card.id }, "");
}

function closeModal() {
  if (!modalOpen) return;
  modalOpen = false;
  closingFromHistory = true; // we own the history pop
  modal.close();
  history.back();
}

modal.addEventListener("close", () => {
  modalOpen = false;
  if (closingFromHistory) {
    closingFromHistory = false; // closeModal already called history.back()
    return;
  }
  // closed by ESC / form cancel: we own the pop
  closingFromHistory = true;
  setTimeout(() => { closingFromHistory = false; }, 0);
  if (history.state && history.state.modal) history.back();
});
document.getElementById("modal-close").addEventListener("click", closeModal);
modal.addEventListener("click", (e) => {
  if (e.target === modal) closeModal();
});
window.addEventListener("popstate", () => {
  // Android/hardware back: if the dialog is still open after the history pop,
  // close it. The 'close' handler's history.back() is guarded by state, so no loop.
  if (modalOpen && !(history.state && history.state.modal)) {
    modal.close();
  }
  modalOpen = false;
});

/* ---------- live e-pick stock ---------- */

function readCache() {
  try {
    const c = JSON.parse(sessionStorage.getItem(CACHE_KEY) || "null");
    if (c && Date.now() - c.t < CACHE_TTL) return c.data;
  } catch (_) {}
  return null;
}
function writeCache(data) {
  try { sessionStorage.setItem(CACHE_KEY, JSON.stringify({ t: Date.now(), data })); } catch (_) {}
}

function setStockLine(text, cls) {
  document.getElementById("stock-line").innerHTML = text;
  document.getElementById("stock-line").className = "meta stock" + (cls ? " " + cls : "");
}

async function refreshLiveStock() {
  const matched = CARDS.filter((c) => c.epick && c.epick.matched);
  const cached = readCache();
  if (cached) return applyLive(cached, true);
  setStockLine("Checking live stock at e-pick…", "checking");
  const urls = [...new Set(matched.flatMap((c) => (c.epick.products || []).map((p) => p.url)))];
  const results = await Promise.all(urls.map(async (u) => {
    try {
      const handle = u.split("/products/")[1];
      const res = await fetch(`${STORE}/products/${handle}.js`, { cache: "no-store" });
      if (!res.ok) throw new Error(res.status);
      const d = await res.json();
      return { url: u, price: (d.variants[0].price / 100).toFixed(2), available: !!d.variants[0].available };
    } catch (_) {
      return null; // network/CORS/shape problem -> keep snapshot
    }
  }));
  const ok = results.filter(Boolean);
  if (!ok.length) {
    setStockLine("Live check unavailable, showing the build-time snapshot.", "snapshot");
    return;
  }
  writeCache(ok);
  applyLive(ok, false);
}

function applyLive(live, fromCache) {
  const byUrl = Object.fromEntries(live.map((r) => [r.url, r]));
  for (const c of CARDS) {
    if (c.epick && c.epick.matched) {
      c.epick.live = (c.epick.products || []).map((p) => ({
        ...p, ...(byUrl[p.url] || {}),
      }));
    }
  }
  renderGrid();
  const inStockCount = CARDS.filter(inStock).length;
  setStockLine(
    `Live: ${inStockCount} of ${CARDS.length} cards in stock at e-pick (NL)${fromCache ? ", cached result" : ""}`,
    "live"
  );
}

/* ---------- toolbar ---------- */

function setStockFilter(on) {
  stockOnly = on;
  const stockBtn = document.getElementById("filter-stock");
  stockBtn.setAttribute("aria-pressed", String(stockOnly));
  renderGrid();
}

function wireToolbar() {
  document.getElementById("filter-stock").addEventListener("click", () => {
    setStockFilter(!stockOnly);
  });
  document.getElementById("sort-select").addEventListener("change", (e) => {
    activeSort = e.target.value;
    renderGrid();
  });
  document.getElementById("grid").addEventListener("click", (e) => {
    if (e.target.closest("[data-action='show-all']")) {
      setStockFilter(false);
    } else if (e.target.closest("[data-action='retry']")) {
      location.reload();
    }
  });
}

/* ---------- boot ---------- */

(async function init() {
  try {
    await loadCards();
    wireToolbar();
    renderGrid();
    setStockLine("Using stock snapshot from build time.", "snapshot");
    refreshLiveStock().catch(() => setStockLine("Live check unavailable, showing the build-time snapshot.", "snapshot"));
  } catch (e) {
    document.getElementById("meta-line").textContent = "Data unavailable.";
    document.getElementById("grid").innerHTML =
      `<div class="state">
         <p class="state-title">Couldn't load the wishlist.</p>
         <p><button type="button" class="linklike" data-action="retry">Try again</button></p>
       </div>`;
  }
})();
