/* Pokémon wishlist — vanilla JS, no dependencies. */
"use strict";

const STORE = "https://store.e-pick.xyz";
const CACHE_KEY = "epick-live-v1";
const CACHE_TTL = 6 * 60 * 60 * 1000; // 6h politeness window

let CARDS = [];

const eur = (n) =>
  n == null ? "—" : `€${Number(n).toLocaleString("en-NL", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

function priceSourceLabel(src) {
  if (src === "pricecharting") return "PriceCharting (converted to EUR)";
  if (src === "e-pick retail") return "e-pick retail price";
  return "Cardmarket trend";
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
    return `<span class="epick-badge in">In stock @ e-pick · ${eur(best.price)}${liveMark} — <a href="${best.url}" target="_blank" rel="noopener">view</a></span>`;
  }
  return `<span class="epick-badge out">Seen at e-pick (${eur(best.price)})${liveMark} — <a href="${best.url}" target="_blank" rel="noopener">view</a></span>`;
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

function renderGrid() {
  const grid = document.getElementById("grid");
  grid.replaceChildren(...CARDS.map(tile));
  const priced = CARDS.filter((c) => c.price && c.price.trend != null);
  const total = priced.reduce((s, c) => s + c.price.trend, 0);
  const asOf = priced.find((c) => c.price.asOf)?.price.asOf;
  document.getElementById("meta-line").textContent =
    `${CARDS.length} cards · ${eur(total)} total · prices as of ${asOf || "n/a"}`;
}

/* ---------- modal ---------- */

const modal = document.getElementById("card-modal");
let modalOpen = false;

function openModal(card) {
  const p = card.price || {};
  const rows = [];
  if (p.trend != null) rows.push(`<div><span class="k">${priceSourceLabel(p.source)}</span><span><b>${eur(p.trend)}</b></span></div>`);
  if (p.avg7 != null) rows.push(`<div><span class="k">Cardmarket 7-day avg</span><span>${eur(p.avg7)}</span></div>`);
  if (p.low != null) rows.push(`<div><span class="k">Cardmarket low</span><span>${eur(p.low)}</span></div>`);
  const links = [];
  if (p.url) {
    const label = p.source === "pricecharting" ? "View on PriceCharting"
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
  modal.close();
  modalOpen = false;
  if (history.state && history.state.modal) history.back();
}

modal.addEventListener("close", () => {
  modalOpen = false;
  if (history.state && history.state.modal) history.back();
});
document.getElementById("modal-close").addEventListener("click", closeModal);
modal.addEventListener("click", (e) => {
  if (e.target === modal) closeModal();
});
window.addEventListener("popstate", () => { modalOpen = false; }); // back button closes modal

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
  const inStock = CARDS.filter((c) => c.epick && c.epick.matched && (c.epick.live || []).some((p) => p.available)).length;
  setStockLine(
    `stock: live ✓ (${inStock}/${CARDS.length} wishlist cards available @ e-pick${fromCache ? ", cached" : ""})`,
    "live"
  );
}

/* ---------- boot ---------- */

(async function init() {
  try {
    await loadCards();
    renderGrid();
    setStockLine("stock: snapshot (build time)", "snapshot");
    refreshLiveStock().catch(() => setStockLine("stock: snapshot (build time) — live check unavailable", "snapshot"));
  } catch (e) {
    document.getElementById("meta-line").textContent = `failed to load data: ${e.message}`;
  }
})();
