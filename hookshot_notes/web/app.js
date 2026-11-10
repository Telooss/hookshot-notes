/* Hookshot Notes — live map page (layout A). Reads /api/world once, then the /events stream. */
"use strict";

const TYPES = [
  ["skulltula", "Skulltulas", "MapIconCollectSkullSign_00"],
  ["chest", "Coffres", "MapIconTreasure_00"],
  ["heart", "Cœurs", "MapIconCollectHeartPiece_00"],
  ["place", "Lieux", "MapIconShopGeneral_00"],
  ["exit", "Sorties", "MapIconArrow_00"],
];
const DONE_ICON = { skulltula: "MapIconCollectSkullSignCheck_00", chest: "MapIconTreasure_01", heart: "MapIconCollectHeartPieceCheck_00" };
const W = 2000, H = 1440, BOUNDS = L.latLngBounds([[-H, 0], [0, W]]);
const STATUS = { no_game: "Jeu non détecté — la carte reste consultable", searching: "Recherche de Link…" };

const store = {
  get(k, d) { try { const v = localStorage.getItem("hn." + k); return v === null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem("hn." + k, JSON.stringify(v)); } catch { /* private mode */ } },
};

let world = null, zones = {}, snap = null, collected = new Set();
let mode = store.get("mode", "spoiler");
let filters = store.get("filters", Object.fromEntries(TYPES.map(([t]) => [t, true])));
let following = true;
const view = { zone: null, banc: null, floor: null };

const $ = (id) => document.getElementById(id);
const toLL = (px, py) => L.latLng(-py, px);
const map = L.map("map", { crs: L.CRS.Simple, minZoom: -3, maxZoom: 2, zoomSnap: 0.25, zoomControl: false, attributionControl: false });
map.fitBounds(BOUNDS, { animate: false });
map.setMaxBounds(BOUNDS.pad(0.4));
let overlay = null, overlayUrl = null;
const objects = L.layerGroup().addTo(map);

/* ---------- Link's arrow, animated between two readings ---------- */
const link = { marker: null, from: null, to: null, start: 0, heading: 0 };
function linkIcon() {
  return L.divIcon({ className: "link-icon", html: `<img src="/data/icons/MapIconPlayer_00.png" alt="Link">`, iconSize: [34, 34] });
}
function moveLink(p) {
  const target = toLL(p.px, p.py);
  if (!link.marker) {
    link.marker = L.marker(target, { icon: linkIcon(), interactive: false, zIndexOffset: 1000 }).addTo(map);
    link.from = link.to = target;
  } else {
    const cur = link.marker.getLatLng();
    const dx = target.lng - cur.lng, dy = -(target.lat - cur.lat);
    if (Math.hypot(dx, dy) > 2) link.heading = Math.atan2(dx, -dy) * 180 / Math.PI; // 0° = up on the map
    link.from = cur; link.to = target; link.start = performance.now();
  }
  const img = link.marker.getElement()?.querySelector("img");
  if (img) img.style.transform = `rotate(${link.heading}deg)`;
  if (following && !zooming) map.panTo(target, { animate: true, duration: 0.45 });
}
let zooming = false;
map.on("zoomstart", () => { zooming = true; });
map.on("zoomend", () => { zooming = false; });
function hideLink() { if (link.marker) { link.marker.remove(); link.marker = null; } }
(function animate(now) {
  if (link.marker && link.from && link.to) {
    const t = Math.min(1, (now - link.start) / 450);
    link.marker.setLatLng(L.latLng(link.from.lat + (link.to.lat - link.from.lat) * t, link.from.lng + (link.to.lng - link.from.lng) * t));
  }
  requestAnimationFrame(animate);
})(performance.now());

/* ---------- map image and objects ---------- */
function bancFor(zone) {
  if (snap && snap.banc in zone.maps) return snap.banc;
  const age = snap && snap.banc && zones[snap.zone] ? zones[snap.zone].maps[snap.banc]?.age : null;
  const same = Object.entries(zone.maps).find(([, m]) => m.age === age);
  return (same || Object.entries(zone.maps)[0])[0];
}
function imageFor(zone) {
  if (zone.kind === "dungeon") return zone.floors[view.floor ?? 0]?.image;
  return zone.maps[view.banc]?.image;
}
function visibleObjects(zone) {
  return zone.objects.filter((o) => zone.kind === "dungeon" ? o.floor === (view.floor ?? 0) : o.map === view.banc);
}
function isDone(o) { return o.flag === "bool64" && collected.has(o.id); }

function render(fit) {
  const zone = zones[view.zone];
  if (!zone) return;
  $("zone-name").textContent = zone.name;
  const url = "/data/" + imageFor(zone);
  if (url !== overlayUrl) {
    if (overlay) overlay.remove();
    overlay = L.imageOverlay(url, BOUNDS).addTo(map);
    overlayUrl = url;
  }
  if (fit) {
    map.fitBounds(BOUNDS, { animate: false });
    const p = snap && snap.zone === view.zone && snap.player;
    if (following && p) map.setView(toLL(p.px, p.py), map.getZoom() + 0.75, { animate: false });
  }
  drawObjects(zone);
  drawCounters(zone);
  drawFloors(zone);
}
function drawObjects(zone) {
  objects.clearLayers();
  for (const o of visibleObjects(zone)) {
    if (!filters[o.type]) continue;
    if (mode === "tracker" && (o.type === "heart" || (o.flag === "bool64" && !isDone(o)))) continue;
    const icon = isDone(o) ? DONE_ICON[o.type] : o.icon;
    const size = o.type === "exit" ? 26 : 34;
    const rot = o.type === "exit" && o.icon === "MapIconArrow_00" ? ` style="transform:rotate(${o.rotate || 0}deg)"` : "";
    L.marker(toLL(o.px, o.py), {
      icon: L.divIcon({ className: "obj", html: `<img src="/data/icons/${icon}.png" alt=""${rot}>`, iconSize: [size, size] }),
      title: o.label || TYPES.find(([t]) => t === o.type)[1],
      keyboard: false,
    }).addTo(objects);
  }
}
function drawCounters(zone) {
  const objs = visibleObjects(zone);
  const pills = [];
  for (const [type, , icon] of TYPES.slice(0, 3)) {
    const all = objs.filter((o) => o.type === type);
    if (!all.length) continue;
    const got = all.filter(isDone).length;
    if (type === "heart") { if (mode === "spoiler") pills.push([icon, `${all.length}`]); continue; }
    pills.push([icon, mode === "spoiler" ? `${got}/${all.length}` : `${got}`]);
  }
  $("counters").innerHTML = pills.map(([i, t]) => `<span class="pill"><i style="background-image:url(/data/icons/${i}.png)"></i>${t}</span>`).join("");
}
function drawFloors(zone) {
  const box = $("floors");
  if (zone.kind !== "dungeon") { box.hidden = true; return; }
  box.hidden = false;
  box.innerHTML = "";
  zone.floors.forEach((f, i) => {
    const b = document.createElement("button");
    b.textContent = f.name;
    b.setAttribute("aria-pressed", String(i === (view.floor ?? 0)));
    if (snap && snap.zone === zone.id && snap.floor === i) b.classList.add("here");
    b.onclick = () => { following = following && snap?.floor === i && snap?.zone === zone.id; view.floor = i; refresh(); };
    box.appendChild(b);
  });
}

/* ---------- controls ---------- */
function drawChips() {
  $("chips").innerHTML = "";
  for (const [type, label, icon] of TYPES) {
    const b = document.createElement("button");
    b.className = "chip";
    b.setAttribute("aria-pressed", String(!!filters[type]));
    b.innerHTML = `<i style="background-image:url(/data/icons/${icon}.png)"></i>${label}`;
    b.onclick = () => { filters[type] = !filters[type]; store.set("filters", filters); drawChips(); refresh(); };
    $("chips").appendChild(b);
  }
}
function drawMode() {
  $("mode").innerHTML = mode === "spoiler" ? "Mode <b>Spoiler</b>" : "Mode <b>Tracker</b>";
  $("mode").setAttribute("aria-pressed", String(mode === "tracker"));
}
$("mode").onclick = () => { mode = mode === "spoiler" ? "tracker" : "spoiler"; store.set("mode", mode); drawMode(); refresh(); };
function setFollowing(on) { following = on; $("recenter").classList.toggle("following", on); }
map.on("dragstart", () => setFollowing(false));
$("recenter").onclick = () => {
  setFollowing(true);
  if (snap && snap.zone) { const changed = view.zone !== snap.zone; Object.assign(view, { zone: snap.zone, banc: snap.banc, floor: snap.floor }); render(changed); }
  if (snap && snap.player) map.setView(toLL(snap.player.px, snap.player.py), Math.max(map.getZoom(), -0.5));
};
$("banner").onclick = () => {
  const ids = new Set([...(snap?.visited || []), ...(snap?.zone ? [snap.zone] : [])]);
  $("zone-list").innerHTML = "";
  for (const zone of world.zones.filter((z) => ids.has(z.id))) {
    const li = document.createElement("li"), b = document.createElement("button");
    const name = document.createElement("span");
    name.textContent = zone.name;  // text from the game files: never parsed as HTML
    b.appendChild(name);
    if (snap?.zone === zone.id) { const here = document.createElement("span"); here.className = "here"; here.textContent = "Link est ici"; b.appendChild(here); }
    b.onclick = () => {
      $("zones").hidden = true;
      setFollowing(snap?.zone === zone.id);
      Object.assign(view, { zone: zone.id, banc: bancFor(zone), floor: snap?.zone === zone.id ? snap.floor : (zone.floors.length ? 0 : null) });
      render(true);
      refreshLink();
    };
    li.appendChild(b); $("zone-list").appendChild(li);
  }
  if (!ids.size) $("zone-list").innerHTML = "<li style='padding:10px 4px'>Aucun lieu visité pour l'instant.</li>";
  $("zones").hidden = false;
};
$("zones-close").onclick = () => { $("zones").hidden = true; };

/* ---------- live state ---------- */
function refresh() { if (view.zone) render(false); refreshLink(); }
function refreshLink() {
  const p = snap && snap.player;
  const sameView = p && snap.zone === view.zone && (zones[view.zone].kind !== "dungeon" || snap.floor === (view.floor ?? 0))
    && (zones[view.zone].kind === "dungeon" || snap.banc === view.banc);
  if (sameView) moveLink(p); else hideLink();
}
function onSnapshot(s) {
  const first = !snap;
  snap = s;
  collected = new Set(s.collected);
  $("status").hidden = !STATUS[s.status];
  $("status").textContent = STATUS[s.status] || "";
  $("percent").textContent = `${s.percent.toFixed(1).replace(".", ",")} % complété`;
  if (following && s.zone) {
    const changed = view.zone !== s.zone || view.banc !== s.banc;
    Object.assign(view, { zone: s.zone, banc: s.banc, floor: s.floor });
    render(changed || first);
  } else if (view.zone) {
    render(false);
  }
  refreshLink();
}
function connect() {
  const es = new EventSource("/events");
  es.onmessage = (e) => onSnapshot(JSON.parse(e.data));
  es.onopen = () => { if (snap) onSnapshot(snap); };
  es.onerror = () => {
    $("status").hidden = false;
    $("status").textContent = "Connexion perdue — reconnexion…";
    if (es.readyState === EventSource.CLOSED) setTimeout(connect, 2000);
  };
}

fetch("/api/world").then((r) => r.json()).then((w) => {
  world = w;
  zones = Object.fromEntries(w.zones.map((z) => [z.id, z]));
  drawChips(); drawMode(); setFollowing(true);
  connect();
}).catch(() => { $("status").hidden = false; $("status").textContent = "Données introuvables — relance Hookshot Notes"; });
