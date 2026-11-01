// FALCON Engine II — Analytics Dashboard
// Canvas 2D charts for fire trends, AQI, mandi prices, currencies

const GOLD = '#f0a500';
const MUTED = '#8a7a60';
const TEXT = '#e2d8c4';
const BG = 'rgba(10,10,20,0.0)';
const GRID = 'rgba(240,165,0,0.07)';

// ── Colour helpers ──────────────────────────────────────────────────────────
function hexAlpha(hex, a) {
  const r = parseInt(hex.slice(1,3),16);
  const g = parseInt(hex.slice(3,5),16);
  const b = parseInt(hex.slice(5,7),16);
  return `rgba(${r},${g},${b},${a})`;
}

const AQI_COLORS = {
  'Good':        '#00c853',
  'Satisfactory':'#69f0ae',
  'Moderate':    '#ffd600',
  'Poor':        '#ff9800',
  'Very Poor':   '#f44336',
  'Severe':      '#b71c1c',
};

// ── Canvas utilities ────────────────────────────────────────────────────────
function clearCanvas(canvas) {
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  return ctx;
}

function drawGridLines(ctx, pad, W, H, steps, maxV) {
  ctx.strokeStyle = GRID;
  ctx.lineWidth = 1;
  for (let i = 1; i <= steps; i++) {
    const y = pad.t + (H - pad.t - pad.b) * (1 - i / steps);
    ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(W - pad.r, y); ctx.stroke();
    ctx.fillStyle = 'rgba(160,144,112,0.5)';
    ctx.font = '8px Consolas,monospace';
    ctx.textAlign = 'right';
    ctx.fillText(fmtNum(maxV * i / steps), pad.l - 3, y + 3);
  }
  ctx.textAlign = 'left';
}

function fmtNum(n) {
  if (n >= 1000) return (n/1000).toFixed(1) + 'k';
  return Math.round(n).toString();
}

// ── 1. Area / Line chart (fires timeseries) ─────────────────────────────────
export function drawAreaChart(canvas, dates, values, opts = {}) {
  const W = canvas.width, H = canvas.height;
  const ctx = clearCanvas(canvas);
  if (!values.length) return;

  const color  = opts.color  || GOLD;
  const label  = opts.label  || '';
  const pad    = { t: 12, r: 8, b: 18, l: 36 };
  const cW     = W - pad.l - pad.r;
  const cH     = H - pad.t - pad.b;
  const maxV   = Math.max(...values, 1);

  drawGridLines(ctx, pad, W, H, 4, maxV);

  // X-axis date labels (first and last)
  ctx.fillStyle = MUTED;
  ctx.font = '8px Consolas,monospace';
  ctx.textAlign = 'left';
  if (dates[0]) ctx.fillText(dates[0].slice(5), pad.l, H - 2);
  ctx.textAlign = 'right';
  if (dates[dates.length-1]) ctx.fillText(dates[dates.length-1].slice(5), W - pad.r, H - 2);
  ctx.textAlign = 'left';

  const pts = values.map((v, i) => ({
    x: pad.l + (i / Math.max(values.length - 1, 1)) * cW,
    y: pad.t + cH * (1 - v / maxV),
  }));

  // Area fill
  ctx.beginPath();
  ctx.moveTo(pts[0].x, pad.t + cH);
  pts.forEach(p => ctx.lineTo(p.x, p.y));
  ctx.lineTo(pts[pts.length-1].x, pad.t + cH);
  ctx.closePath();
  const grad = ctx.createLinearGradient(0, pad.t, 0, pad.t + cH);
  grad.addColorStop(0, hexAlpha(color, 0.35));
  grad.addColorStop(1, hexAlpha(color, 0.03));
  ctx.fillStyle = grad;
  ctx.fill();

  // Line
  ctx.beginPath();
  pts.forEach((p, i) => i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y));
  ctx.strokeStyle = color;
  ctx.lineWidth = 1.5;
  ctx.stroke();

  // Peak dot
  const peakIdx = values.indexOf(Math.max(...values));
  ctx.beginPath();
  ctx.arc(pts[peakIdx].x, pts[peakIdx].y, 3, 0, Math.PI*2);
  ctx.fillStyle = color;
  ctx.fill();
}

// ── 2. Horizontal bar chart (ranked items) ──────────────────────────────────
export function drawHorizBars(canvas, labels, values, opts = {}) {
  const W = canvas.width, H = canvas.height;
  const ctx = clearCanvas(canvas);
  if (!labels.length) return;

  const colors    = opts.colors || labels.map(() => GOLD);
  const maxV      = Math.max(...values, 1);
  const pad       = { t: 6, r: 8, b: 6, l: opts.labelW || 72 };
  const barH      = Math.max(6, (H - pad.t - pad.b) / labels.length - 3);
  const barSpaceH = (H - pad.t - pad.b) / labels.length;
  const cW        = W - pad.l - pad.r;

  labels.forEach((lbl, i) => {
    const barW = Math.max(2, (values[i] / maxV) * cW);
    const y    = pad.t + i * barSpaceH;

    // bar background track
    ctx.fillStyle = 'rgba(240,165,0,0.06)';
    ctx.fillRect(pad.l, y + 1, cW, barH);

    // bar fill
    const col = typeof colors[i] === 'string' ? colors[i] : GOLD;
    ctx.fillStyle = hexAlpha(col.startsWith('#') ? col : '#f0a500', 0.75);
    ctx.fillRect(pad.l, y + 1, barW, barH);

    // label left
    ctx.fillStyle = MUTED;
    ctx.font = `8px Segoe UI,system-ui`;
    ctx.textAlign = 'right';
    ctx.fillText(lbl.length > 9 ? lbl.slice(0,9) : lbl, pad.l - 3, y + barH/2 + 3);

    // value right of bar
    ctx.fillStyle = TEXT;
    ctx.font = '9px Consolas,monospace';
    ctx.textAlign = 'left';
    ctx.fillText(fmtNum(values[i]) + (opts.unit || ''), pad.l + barW + 3, y + barH/2 + 3);
  });
  ctx.textAlign = 'left';
}

// ── 3. Bullet chart (actual vs target/MSP) ──────────────────────────────────
export function drawBulletCharts(canvas, rows, opts = {}) {
  // rows: [{label, actual, target, max, unit, color}]
  const W = canvas.width, H = canvas.height;
  const ctx = clearCanvas(canvas);
  if (!rows.length) return;

  const rowH = (H - 4) / rows.length;
  const padL = opts.labelW || 60;
  const padR = 32;
  const cW   = W - padL - padR;

  rows.forEach((row, i) => {
    const y   = 2 + i * rowH;
    const bH  = Math.max(5, rowH * 0.35);
    const bY  = y + (rowH - bH) / 2;
    const max = row.max || Math.max(row.actual, row.target) * 1.15;

    // background track
    ctx.fillStyle = 'rgba(240,165,0,0.06)';
    ctx.fillRect(padL, bY, cW, bH);

    // MSP/target marker
    const tX = padL + (row.target / max) * cW;
    ctx.fillStyle = 'rgba(240,165,0,0.5)';
    ctx.fillRect(tX - 1, bY - 3, 2, bH + 6);

    // actual bar
    const aW  = (row.actual / max) * cW;
    const col = row.actual >= row.target ? '#5a9f5a' : '#b04040';
    ctx.fillStyle = hexAlpha(col, 0.8);
    ctx.fillRect(padL, bY, aW, bH);

    // row label
    ctx.fillStyle = MUTED;
    ctx.font = '9px Segoe UI,system-ui';
    ctx.textAlign = 'right';
    ctx.fillText(row.label, padL - 4, bY + bH/2 + 3);

    // actual value
    ctx.fillStyle = col;
    ctx.font = '9px Consolas,monospace';
    ctx.textAlign = 'left';
    ctx.fillText('₹' + row.actual + (row.unit || ''), padL + aW + 4, bY + bH/2 + 3);

    // MSP label above marker
    ctx.fillStyle = hexAlpha(GOLD, 0.7);
    ctx.font = '7px Consolas,monospace';
    ctx.textAlign = 'center';
    ctx.fillText('MSP', tX, bY - 5);
  });
  ctx.textAlign = 'left';
}

// ── 4. Sparkline (single) ────────────────────────────────────────────────────
export function drawSparkline(canvas, values, color) {
  const W = canvas.width, H = canvas.height;
  const ctx = clearCanvas(canvas);
  if (!values.length) return;
  const pad = { t: 3, r: 3, b: 3, l: 3 };
  const cW = W - pad.l - pad.r;
  const cH = H - pad.t - pad.b;
  const maxV = Math.max(...values, 1);
  const minV = Math.min(...values, 0);
  const range = maxV - minV || 1;

  const pts = values.map((v, i) => ({
    x: pad.l + (i / Math.max(values.length - 1, 1)) * cW,
    y: pad.t + cH * (1 - (v - minV) / range),
  }));

  ctx.beginPath();
  pts.forEach((p, i) => i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y));
  ctx.strokeStyle = color || GOLD;
  ctx.lineWidth = 1.5;
  ctx.stroke();
}

// ── 5. Heatmap grid (district values) ──────────────────────────────────────
export function drawDistrictHeatmap(container, districtData, opts = {}) {
  // districtData: [{name, value, category, color}]
  const cols   = opts.cols   || 4;
  const title  = opts.title  || '';
  const unit   = opts.unit   || '';

  container.innerHTML = '';

  if (title) {
    const h = document.createElement('div');
    h.className = 'dash-section-title';
    h.textContent = title;
    container.appendChild(h);
  }

  const grid = document.createElement('div');
  grid.style.cssText = `display:grid;grid-template-columns:repeat(${cols},1fr);gap:3px;`;
  container.appendChild(grid);

  districtData.forEach(d => {
    const cell = document.createElement('div');
    const col  = d.color || GOLD;
    cell.style.cssText = `
      background:${hexAlpha(col.startsWith('#') ? col : '#f0a500', 0.18)};
      border:1px solid ${hexAlpha(col.startsWith('#') ? col : '#f0a500', 0.35)};
      border-radius:2px; padding:4px 3px; text-align:center; cursor:default;
    `;
    cell.title = `${d.name}: ${d.value}${unit}`;
    cell.innerHTML = `
      <div style="font-size:8px;color:#8a7a60;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${d.name.slice(0,7)}</div>
      <div style="font-size:10px;font-weight:700;color:${col}">${d.value != null ? d.value : '—'}</div>
    `;
    grid.appendChild(cell);
  });
}

// ── 6. Countdown tiles (groundwater critical years) ──────────────────────────
export function drawCountdownTiles(container, tiles, opts = {}) {
  // tiles: [{name, years, depth, trend, color}]
  container.innerHTML = '';

  const grid = document.createElement('div');
  grid.style.cssText = `display:grid;grid-template-columns:repeat(3,1fr);gap:4px;`;
  container.appendChild(grid);

  tiles.forEach(t => {
    const urgency = t.years <= 5 ? '#f44336' : t.years <= 10 ? '#ff9800' : t.years <= 20 ? '#ffd600' : '#5a9f5a';
    const cell = document.createElement('div');
    cell.style.cssText = `
      background:rgba(10,10,20,0.7);
      border:1px solid ${hexAlpha(urgency, 0.4)};
      border-top:2px solid ${urgency};
      border-radius:2px; padding:5px 4px; text-align:center;
    `;
    cell.innerHTML = `
      <div style="font-size:7px;color:#8a7a60;letter-spacing:1px;text-transform:uppercase;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${t.name}</div>
      <div style="font-size:18px;font-weight:700;color:${urgency};line-height:1.1">${t.years > 99 ? '∞' : t.years}</div>
      <div style="font-size:7px;color:#8a7a60">yrs · ${t.depth}m</div>
    `;
    grid.appendChild(cell);
  });
}

// ── 7. KPI stat row ──────────────────────────────────────────────────────────
export function buildKpiRow(container, stats) {
  // stats: [{label, value, sub, color}]
  container.innerHTML = '';
  const row = document.createElement('div');
  row.style.cssText = 'display:flex;gap:6px;flex-wrap:wrap;';
  container.appendChild(row);

  stats.forEach(s => {
    const tile = document.createElement('div');
    tile.style.cssText = `
      flex:1;min-width:72px;
      background:rgba(240,165,0,0.06);
      border:1px solid rgba(240,165,0,0.14);
      border-radius:3px; padding:6px 8px;
    `;
    tile.innerHTML = `
      <div style="font-size:7px;letter-spacing:2px;text-transform:uppercase;color:#8a7a60">${s.label}</div>
      <div style="font-size:16px;font-weight:700;color:${s.color || GOLD};line-height:1.2">${s.value}</div>
      <div style="font-size:8px;color:#8a7a60">${s.sub || ''}</div>
    `;
    row.appendChild(tile);
  });
}

// ── 8. Currency sparkline grid ────────────────────────────────────────────────
export function buildCurrencyGrid(container, rates, history) {
  // rates: {CAD:{label,inr_per_unit}, GBP, EUR, AED}
  // history: optional {CAD:[...], GBP:[...], ...}
  container.innerHTML = '';

  const entries = Object.entries(rates);
  const grid = document.createElement('div');
  grid.style.cssText = 'display:grid;grid-template-columns:1fr 1fr;gap:6px;';
  container.appendChild(grid);

  entries.forEach(([code, info]) => {
    const card = document.createElement('div');
    card.style.cssText = `
      background:rgba(240,165,0,0.05);
      border:1px solid rgba(240,165,0,0.12);
      border-radius:3px; padding:7px 8px;
    `;
    const change = history && history[code] && history[code].length > 1
      ? ((history[code][history[code].length-1] - history[code][0]) / history[code][0] * 100).toFixed(1)
      : null;
    const chColor = !change ? MUTED : parseFloat(change) >= 0 ? '#5a9f5a' : '#b04040';
    const chSign  = change && parseFloat(change) >= 0 ? '+' : '';

    card.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:baseline">
        <span style="font-size:11px;font-weight:700;color:${GOLD};letter-spacing:1px">${code}</span>
        <span style="font-size:8px;color:${chColor}">${change ? chSign + change + '%' : ''}</span>
      </div>
      <div style="font-size:15px;font-weight:700;color:${TEXT}">₹${info.inr_per_unit}</div>
      <div style="font-size:7px;color:${MUTED}">${info.label}</div>
      <canvas id="spark-${code}" width="90" height="22" style="width:100%;margin-top:3px"></canvas>
    `;
    grid.appendChild(card);

    if (history && history[code]) {
      requestAnimationFrame(() => {
        const sc = card.querySelector(`#spark-${code}`);
        if (sc) drawSparkline(sc, history[code], GOLD);
      });
    }
  });
}

// ── Dashboard state ───────────────────────────────────────────────────────────
let _open = false;

export function isDashboardOpen() { return _open; }

export function openDashboard(tab) {
  const overlay = document.getElementById('dash-overlay');
  if (!overlay) return;
  overlay.style.display = 'flex';
  _open = true;
  switchDashTab(tab || 'fires');
}

export { renderTab as _renderTab };

export function closeDashboard() {
  const overlay = document.getElementById('dash-overlay');
  if (overlay) overlay.style.display = 'none';
  _open = false;
}

function switchDashTab(tab) {
  document.querySelectorAll('.dash-tab-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.tab === tab);
  });
  document.querySelectorAll('.dash-tab-pane').forEach(p => {
    p.style.display = p.dataset.tab === tab ? 'block' : 'none';
  });
  renderTab(tab);
}

// ── Tab renders ───────────────────────────────────────────────────────────────
async function renderTab(tab) {
  if (tab === 'fires')   await renderFiresTab();
  if (tab === 'aqi')     await renderAQITab();
  if (tab === 'mandi')   await renderMandiTab();
  if (tab === 'economy') await renderEconomyTab();
}

async function renderFiresTab() {
  const pane = document.querySelector('.dash-tab-pane[data-tab="fires"]');
  if (!pane) return;

  let ts;
  try { ts = await (await fetch('./public/data/history/fires_timeseries.json?v='+Date.now())).json(); }
  catch(e) { pane.querySelector('.dash-fire-area').innerHTML = '<p class="dash-empty">No data</p>'; return; }

  const records = (ts.records || []).slice(-30);
  if (!records.length) return;

  const dates  = records.map(r => r.date);
  const counts = records.map(r => r.count);
  const frp    = records.map(r => r.peak_frp);

  // KPI
  const kpiEl = pane.querySelector('.dash-fire-kpi');
  const total  = counts.reduce((a,b)=>a+b,0);
  const peak   = Math.max(...frp);
  const latest = counts[counts.length-1] || 0;
  buildKpiRow(kpiEl, [
    { label: 'Total Detections', value: total, sub: '30-day', color: '#ff7043' },
    { label: 'Latest Day',       value: latest, sub: dates[dates.length-1]?.slice(5) || '', color: '#ff9800' },
    { label: 'Peak FRP',         value: peak + ' MW', sub: 'radiative power', color: '#ffd600' },
  ]);

  // Area chart — fire count
  const c1 = pane.querySelector('.dash-fire-canvas');
  if (c1) {
    c1.width  = c1.offsetWidth || 600;
    c1.height = 110;
    drawAreaChart(c1, dates, counts, { color: '#ff7043', label: 'hotspots' });
  }

  // Area chart — peak FRP
  const c2 = pane.querySelector('.dash-frp-canvas');
  if (c2) {
    c2.width  = c2.offsetWidth || 600;
    c2.height = 90;
    drawAreaChart(c2, dates, frp, { color: '#ffd600', label: 'MW' });
  }
}

async function renderAQITab() {
  const pane = document.querySelector('.dash-tab-pane[data-tab="aqi"]');
  if (!pane) return;

  let aqi;
  try { aqi = await (await fetch('./public/data/punjab_aqi.json?v='+Date.now())).json(); }
  catch(e) { return; }

  const features = (aqi.features || []).filter(f => f.properties);
  if (!features.length) return;

  // Sort by AQI descending
  const sorted = [...features].sort((a,b) => b.properties.aqi - a.properties.aqi);
  const labels = sorted.map(f => f.properties.city || f.properties.station.slice(0,12));
  const values = sorted.map(f => f.properties.aqi);
  const colors = sorted.map(f => f.properties.color || AQI_COLORS[f.properties.category] || GOLD);

  // KPI
  const kpiEl = pane.querySelector('.dash-aqi-kpi');
  const avgAQI = Math.round(values.reduce((a,b)=>a+b,0)/values.length);
  const maxAQI = Math.max(...values);
  const maxSt  = sorted[0].properties.city || sorted[0].properties.station;
  buildKpiRow(kpiEl, [
    { label: 'Punjab Avg AQI', value: avgAQI, sub: 'all stations', color: colors[Math.floor(colors.length/2)] },
    { label: 'Worst Station',  value: maxSt,  sub: 'AQI ' + maxAQI, color: '#f44336' },
    { label: 'Stations',       value: features.length, sub: 'monitored', color: GOLD },
  ]);

  // Ranked bar
  const c = pane.querySelector('.dash-aqi-canvas');
  if (c) {
    c.width  = c.offsetWidth || 600;
    c.height = Math.max(160, sorted.length * 16 + 12);
    drawHorizBars(c, labels, values, { colors, unit: ' AQI', labelW: 80 });
  }

  // Category breakdown
  const cats = {};
  features.forEach(f => { const cat = f.properties.category; cats[cat] = (cats[cat]||0)+1; });
  const catEl = pane.querySelector('.dash-aqi-cats');
  if (catEl) {
    catEl.innerHTML = Object.entries(cats).map(([k,v]) =>
      `<span style="display:inline-flex;align-items:center;gap:4px;background:rgba(0,0,0,0.3);border:1px solid ${hexAlpha(AQI_COLORS[k]||'#888',0.4)};border-radius:2px;padding:3px 7px;font-size:9px">
        <span style="width:7px;height:7px;border-radius:50%;background:${AQI_COLORS[k]||'#888'}"></span>
        <span style="color:#e2d8c4">${k}</span>
        <span style="color:${GOLD};font-weight:700">${v}</span>
      </span>`
    ).join('');
  }
}

async function renderMandiTab() {
  const pane = document.querySelector('.dash-tab-pane[data-tab="mandi"]');
  if (!pane) return;

  let mandi, ts;
  try {
    [mandi, ts] = await Promise.all([
      fetch('./public/data/punjab_mandi.json?v='+Date.now()).then(r=>r.json()),
      fetch('./public/data/history/mandi_timeseries.json?v='+Date.now()).then(r=>r.json()),
    ]);
  } catch(e) { return; }

  const features = mandi.features || [];
  if (!features.length) return;

  // KPI
  const below = features.filter(f => f.properties.below_msp);
  const kpiEl = pane.querySelector('.dash-mandi-kpi');
  const avgWheat  = Math.round(features.reduce((a,f)=>a+(f.properties.prices.wheat||0),0)/features.length);
  const avgPaddy  = Math.round(features.reduce((a,f)=>a+(f.properties.prices.paddy||0),0)/features.length);
  buildKpiRow(kpiEl, [
    { label: 'Mandis Below MSP', value: below.length + '/' + features.length, sub: 'this season', color: below.length > 0 ? '#f44336' : '#5a9f5a' },
    { label: 'Avg Wheat Price',  value: '₹' + avgWheat, sub: 'per quintal', color: '#ffd600' },
    { label: 'Avg Paddy Price',  value: '₹' + avgPaddy, sub: 'per quintal', color: '#69f0ae' },
  ]);

  // Bullet chart — wheat & paddy MSP comparison
  const MSP_WHEAT  = 2275;
  const MSP_PADDY  = 2320;
  const MSP_COTTON = 7020;
  const rows = [
    { label: 'Wheat',  actual: avgWheat, target: MSP_WHEAT,  max: MSP_WHEAT  * 1.2, unit: '/qtl' },
    { label: 'Paddy',  actual: avgPaddy, target: MSP_PADDY,  max: MSP_PADDY  * 1.2, unit: '/qtl' },
    {
      label: 'Cotton',
      actual: Math.round(features.reduce((a,f)=>a+(f.properties.prices.cotton||0),0)/features.length),
      target: MSP_COTTON, max: MSP_COTTON * 1.2, unit: '/qtl',
    },
  ];
  const c = pane.querySelector('.dash-mandi-bullet');
  if (c) {
    c.width  = c.offsetWidth || 600;
    c.height = rows.length * 34 + 8;
    drawBulletCharts(c, rows, { labelW: 55 });
  }

  // Price trend area charts
  if (ts.records && ts.records.length) {
    const dates  = ts.records.map(r => r.date);
    const wVals  = ts.records.map(r => r.wheat?.avg || 0);
    const pVals  = ts.records.map(r => r.paddy?.avg || 0);

    const cW = pane.querySelector('.dash-wheat-canvas');
    if (cW) {
      cW.width  = cW.offsetWidth || 600;
      cW.height = 80;
      drawAreaChart(cW, dates, wVals, { color: '#ffd600', label: '₹/qtl wheat' });
    }

    const cP = pane.querySelector('.dash-paddy-canvas');
    if (cP) {
      cP.width  = cP.offsetWidth || 600;
      cP.height = 80;
      drawAreaChart(cP, dates, pVals, { color: '#69f0ae', label: '₹/qtl paddy' });
    }
  }

  // Per-mandi heatmap
  const hmEl = pane.querySelector('.dash-mandi-heatmap');
  if (hmEl) {
    const data = features.map(f => ({
      name:     f.properties.mandi,
      value:    f.properties.main_price,
      color:    f.properties.below_msp ? '#f44336' : '#5a9f5a',
      category: f.properties.below_msp ? 'below' : 'above',
    }));
    drawDistrictHeatmap(hmEl, data, { cols: 4, title: '', unit: '₹' });
  }
}

async function renderEconomyTab() {
  const pane = document.querySelector('.dash-tab-pane[data-tab="economy"]');
  if (!pane) return;

  let cur, com;
  try {
    [cur, com] = await Promise.all([
      fetch('./public/data/currencies.json?v='+Date.now()).then(r=>r.json()),
      fetch('./public/data/commodities.json?v='+Date.now()).then(r=>r.json()),
    ]);
  } catch(e) { return; }

  // Currency grid
  const curEl = pane.querySelector('.dash-currency-grid');
  if (curEl && cur.rates) buildCurrencyGrid(curEl, cur.rates, null);

  // Commodity KPIs
  const comEl = pane.querySelector('.dash-commodity-kpi');
  if (comEl && com.prices) {
    buildKpiRow(comEl, [
      { label: 'Wheat (global)',  value: '$' + com.prices.wheat?.value,    sub: 'USD/MT ' + (com.prices.wheat?.date||''), color: '#ffd600' },
      { label: 'Rice (global)',   value: '$' + com.prices.rice?.value,     sub: 'USD/MT', color: '#69f0ae' },
      { label: 'Cotton (global)', value: '$' + com.prices.cotton?.value,   sub: 'USD/MT', color: '#90caf9' },
      { label: 'Palm Oil',        value: '$' + com.prices.palm_oil?.value, sub: 'USD/MT', color: GOLD },
    ]);
  }

  // MSP vs global — bullet
  const mspEl = pane.querySelector('.dash-msp-canvas');
  if (mspEl && com.prices && com.msp_inr_quintal) {
    const rows = [
      { label: 'Wheat',  actual: com.msp_inr_quintal.wheat,  target: com.msp_inr_quintal.wheat,  max: com.msp_inr_quintal.wheat  * 1.5, unit: '' },
      { label: 'Paddy',  actual: com.msp_inr_quintal.paddy,  target: com.msp_inr_quintal.paddy,  max: com.msp_inr_quintal.paddy  * 1.5, unit: '' },
      { label: 'Cotton', actual: com.msp_inr_quintal.cotton, target: com.msp_inr_quintal.cotton, max: com.msp_inr_quintal.cotton * 1.5, unit: '' },
    ];
    mspEl.width  = mspEl.offsetWidth || 600;
    mspEl.height = 90;
    drawBulletCharts(mspEl, rows, { labelW: 55 });
  }
}

// ── Mini charts in intel panel (Engine II sidebar) ───────────────────────────
export async function initEngine2Panel() {
  // Inject "DASHBOARD →" button in intel-header if not already there
  const hdr = document.getElementById('intel-header');
  if (hdr && !document.getElementById('dash-open-btn')) {
    const btn = document.createElement('button');
    btn.id = 'dash-open-btn';
    btn.textContent = 'DASHBOARD →';
    btn.onclick = () => openDashboard('fires');
    btn.style.cssText = `
      margin-top:8px; width:100%;
      background:rgba(240,165,0,0.1); border:1px solid rgba(240,165,0,0.3);
      color:${GOLD}; font-size:8px; letter-spacing:2px; text-transform:uppercase;
      padding:5px 0; cursor:pointer; border-radius:2px;
      transition:background 0.15s;
    `;
    btn.onmouseover = () => btn.style.background = 'rgba(240,165,0,0.2)';
    btn.onmouseout  = () => btn.style.background = 'rgba(240,165,0,0.1)';
    hdr.appendChild(btn);
  }

  // Mini fire sparkline in trend-chart section if already open
  // (full dashboard is opened on button click; panel just shows the button)
}
