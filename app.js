/* Pokémon wishlist — vanilla JS, no dependencies. */
"use strict";

const STORE = "https://store.e-pick.xyz";
const CACHE_KEY = "epick-live-v1";
const CACHE_TTL = 6 * 60 * 60 * 1000; // 6h politeness window

let CARDS = [];

const eur = (n) =>
  n == null ? "—" : `€${Number(n).toLocaleString("en-NL", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

function priceSourceLabel(src) {
  if (src === "pricecharting") return "PriceCharting ungraded (converted to EUR)";
  if (src === "cardmarket-tcggo") return "Cardmarket 7-day average (EU)";
  if (src === "e-pick retail") return "e-pick retail price (NL)";
  return "Cardmarket trend (EU)";
}

function countryLine(price) {
  const co = price && price.countries;
  if (!co || !Object.keys(co).length) return "";
  const parts = Object.keys(co).sort().map((k) => `${k} ${eur(co[k])}`);
  return `<div><span class="k">Lowest NM by country</span><span class="mono">${parts.join(" · ")}</span></div>`;
}

async function loadCards() {
  const res = await fetch("data/cards.json");
  if (!res.ok) throw new Error(`cards.json ${res.status}`);
  CARDS = await res.json();
}

/* ---------- rendering ---------- */

function epickBadge(card) {
  if (!card.epick || !card.epick.matched) {
    return `<span class="epick-badge out">Not at e-pick</span>`;
  }
  const prods = (card.epick.products || []).filter((p) => p.available);
  const any = card.epick.products || [];
  const live = card.epick.live;
  let list = live ? (live.some((p) => p.available) ? live : any) : prods.length ? prods : any;
  if (!list.length) return `<span class="epick-badge out">Not at e-pick</span>`;
  const best = list.reduce((a, b) => (Number(a.price) <= Number(b.price) ? a : b));
  const inStock = list.some((p) => p.available);
  const liveMark = live ? "" : " · snapshot";
  if (inStock) {
    return `<span class="epick-badge in">In stock @ e-pick (NL) · ${eur(best.price)}${liveMark} — <a href="${best.url}" target="_blank" rel="noopener">view</a></span>`;
  }
  return `<span class="epick-badge out">Seen at e-pick (NL) (${eur(best.price)})${liveMark} — <a href="${best.url}" target="_blank" rel="noopener">view</a></span>`;
}

function tile(card) {
  const el = document.createElement("article");
  el.className = "card";
  el.dataset.id = card.id;
  const p = card.price || {};
  el.innerHTML = `
    <div class="card-img" role="button" tabindex="0" aria-label="Open ${card.name}">
      <img loading="lazy" src="${card.image}" alt="${card.name} — ${card.set || ""} ${card.number || ""}">
      <span class="price-chip">${eur(p.trend)}</span>
    </div>
    <div class="card-body">
      <div class="card-name">${card.name}</div>
      <div class="card-set">${card.set || ""}${card.number ? " · " + card.number : ""}</div>
      ${epickBadge(card)}
    </div>`;
  el.querySelector(".card-img").addEventListener("click", () => openModal(card));
  el.querySelector(".card-img").addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") openModal(card);
  });
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

function renderGrid() {
  const grid = document.getElementById("grid");
  const list = visibleCards();
  grid.replaceChildren(...list.map(tile));
  const priced = CARDS.filter((c) => c.price && c.price.trend != null);
  const total = priced.reduce((s, c) => s + c.price.trend, 0);
  const asOf = priced.find((c) => c.price.asOf)?.price.asOf;
  document.getElementById("meta-line").textContent =
    `${CARDS.length} cards · ${eur(total)} total · prices as of ${asOf || "n/a"}`;
  const cl = document.getElementById("count-line");
  cl.textContent = stockOnly ? `${list.length} of ${CARDS.length} shown` : "";
}

/* ---------- modal ---------- */

const modal = document.getElementById("card-modal");
let modalOpen = false;
let closingFromHistory = false;

function openModal(card) {
  const p = card.price || {};
  const rows = [];
  if (p.trend != null) rows.push(`<div><span class="k">${priceSourceLabel(p.source)}</span><span><b>${eur(p.trend)}</b></span></div>`);
  if (p.avg7 != null) rows.push(`<div><span class="k">Cardmarket 7-day avg (EU)</span><span>${eur(p.avg7)}</span></div>`);
  if (p.lowNm != null) rows.push(`<div><span class="k">Lowest offer, Near Mint (EU)</span><span>${eur(p.lowNm)}</span></div>`);
  if (p.low != null) rows.push(`<div><span class="k">Cardmarket low</span><span>${eur(p.low)}</span></div>`);
  rows.push(countryLine(p));
  if (p.available != null) rows.push(`<div><span class="k">Cardmarket offers</span><span>${p.available}</span></div>`);
  const links = [];
  if (p.url) {
    const label = p.source === "pricecharting" ? "View on PriceCharting"
      : p.source === "cardmarket-tcggo" ? "Cardmarket product page"
      : p.source === "e-pick retail" ? "View at e-pick" : "View on Cardmarket";
    links.push(`<a class="btn" href="${p.url}" target="_blank" rel="noopener">${label}</a>`);
  }
  if (card.epick && card.epick.matched) {
    const best = (card.epick.products || []).reduce((a, b) => (Number(a.price) <= Number(b.price) ? a : b));
    links.push(`<a class="btn secondary" href="${best.url}" target="_blank" rel="noopener">e-pick listing</a>`);
  }
  document.getElementById("modal-body").innerHTML = `
    <img class="hero" src="${card.image}" alt="${card.name}">
    <div class="modal-info">
      <h2>${card.name}</h2>
      <div class="sub">${card.set || ""}${card.number ? " · #" + card.number : ""}${card.rarity ? " · " + card.rarity : ""}${card.language ? " · " + card.language : ""}</div>
      <div class="price-rows">${rows.join("") || '<div><span class="k">price</span><span>pending</span></div>'}</div>
      ${epickBadge(card)}
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
  document.getElementById("footer-stock").innerHTML = text;
  if (cls) document.getElementById("stock-line").className = "meta stock " + cls;
}

async function refreshLiveStock() {
  const matched = CARDS.filter((c) => c.epick && c.epick.matched);
  const cached = readCache();
  if (cached) return applyLive(cached, true);
  setStockLine("stock: checking live…");
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
    setStockLine("stock: snapshot (build time) — live check unavailable", "snapshot");
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
    `stock: live ✓ (${inStockCount}/${CARDS.length} wishlist cards available @ e-pick${fromCache ? ", cached" : ""})`,
    "live"
  );
}

/* ---------- toolbar ---------- */

function wireToolbar() {
  const stockBtn = document.getElementById("filter-stock");
  stockBtn.addEventListener("click", () => {
    stockOnly = !stockOnly;
    stockBtn.setAttribute("aria-pressed", String(stockOnly));
    stockBtn.classList.toggle("active", stockOnly);
    renderGrid();
  });
  document.getElementById("sort-select").addEventListener("change", (e) => {
    activeSort = e.target.value;
    renderGrid();
  });
}

/* ---------- boot ---------- */

(async function init() {
  try {
    await loadCards();
    wireToolbar();
    renderGrid();
    setStockLine("stock: snapshot (build time)", "snapshot");
    refreshLiveStock().catch(() => setStockLine("stock: snapshot (build time) — live check unavailable", "snapshot"));
  } catch (e) {
    document.getElementById("meta-line").textContent = `failed to load data: ${e.message}`;
  }
})();
