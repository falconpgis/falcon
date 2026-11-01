// FALCON Prediction Engine — browser-side rendering
// Reads predictions.json + timeseries; renders into dashboard Intelligence tab

const GOLD   = '#f0a500';
const RED    = '#f44336';
const ORANGE = '#ff9800';
const YELLOW = '#ffd600';
const GREEN  = '#5a9f5a';

function riskColor(level) {
  return { critical: RED, high: ORANGE, elevated: YELLOW,
           HIGH: RED, ELEVATED: ORANGE, MODERATE: YELLOW, LOW: GREEN, low: GREEN,
           moderate: YELLOW }[level] || GOLD;
}

function hexAlpha(hex, a) {
  if (!hex.startsWith('#')) return hex;
  const r = parseInt(hex.slice(1,3),16), g = parseInt(hex.slice(3,5),16), b = parseInt(hex.slice(5,7),16);
  return `rgba(${r},${g},${b},${a})`;
}

// ── Section builder helper ────────────────────────────────────────────────────
function section(title, content) {
  return `<div class="pred-section">
    <div class="pred-section-title">${title}</div>
    <div class="pred-section-body">${content}</div>
  </div>`;
}

function scoreGauge(label, score, level, sub='') {
  const col = riskColor(level);
  const barW = Math.round(score);
  return `<div class="pred-gauge">
    <div class="pred-gauge-header">
      <span class="pred-gauge-label">${label}</span>
      <span class="pred-gauge-score" style="color:${col}">${score}<span style="font-size:9px;color:#8a7a60">/100</span></span>
      <span class="pred-level-chip" style="background:${hexAlpha(col,0.15)};border:1px solid ${hexAlpha(col,0.4)};color:${col}">${level}</span>
    </div>
    <div class="pred-gauge-track">
      <div class="pred-gauge-fill" style="width:${barW}%;background:${col}"></div>
    </div>
    ${sub ? `<div class="pred-gauge-sub">${sub}</div>` : ''}
  </div>`;
}

// ── 1. Groundwater countdown ──────────────────────────────────────────────────
export function renderGroundwaterCountdown(container, data) {
  if (!data || !data.timeline) { container.innerHTML = '<p class="pred-empty">No data</p>'; return; }
  const districts = data.timeline.slice(0, 22);

  const grid = districts.map(d => {
    const col = riskColor(d.risk);
    const yrs = d.years_to_critical;
    const display = yrs >= 999 ? '∞' : yrs > 99 ? '99+' : String(yrs);
    return `<div class="gw-tile" title="${d.district} — ${d.depth_mbgl}m depth, ${d.rate_m_yr}m/yr">
      <div class="gw-tile-top" style="border-top-color:${col}"></div>
      <div class="gw-tile-name">${d.district.slice(0,7)}</div>
      <div class="gw-tile-years" style="color:${col}">${display}</div>
      <div class="gw-tile-sub">${d.depth_mbgl}m · ${d.rate_m_yr}m/yr</div>
    </div>`;
  }).join('');

  const critical = districts.filter(d => d.years_to_critical <= 10);
  container.innerHTML = `
    <div class="pred-kpi-row">
      <div class="pred-kpi-tile" style="border-color:rgba(244,67,54,0.4)">
        <div class="pred-kpi-label">Critical (&le;10yr)</div>
        <div class="pred-kpi-value" style="color:${RED}">${critical.length}</div>
        <div class="pred-kpi-sub">districts</div>
      </div>
      <div class="pred-kpi-tile">
        <div class="pred-kpi-label">Worst District</div>
        <div class="pred-kpi-value" style="color:${RED};font-size:13px">${districts[0].district}</div>
        <div class="pred-kpi-sub">${districts[0].years_to_critical} yrs · ${districts[0].depth_mbgl}m</div>
      </div>
      <div class="pred-kpi-tile">
        <div class="pred-kpi-label">Critical Depth</div>
        <div class="pred-kpi-value" style="color:${ORANGE}">50m</div>
        <div class="pred-kpi-sub">economic pump limit</div>
      </div>
    </div>
    <div class="pred-legend-row">
      <span class="pred-leg-chip" style="border-color:${hexAlpha(RED,0.5)};color:${RED}">● ≤5yr critical</span>
      <span class="pred-leg-chip" style="border-color:${hexAlpha(ORANGE,0.5)};color:${ORANGE}">● 5-10yr high</span>
      <span class="pred-leg-chip" style="border-color:${hexAlpha(YELLOW,0.5)};color:${YELLOW}">● 10-20yr elevated</span>
      <span class="pred-leg-chip" style="border-color:${hexAlpha(GREEN,0.5)};color:${GREEN}">● >20yr moderate</span>
    </div>
    <div class="gw-grid">${grid}</div>
    <div class="pred-source">Source: CGWB 2024 · Linear extrapolation from district depletion rates</div>
  `;
}

// ── 2. Debt trajectory chart ──────────────────────────────────────────────────
export function renderDebtTrajectory(container, canvas, data) {
  if (!data || !data.projections) { container.innerHTML = '<p class="pred-empty">No data</p>'; return; }

  const crisis = data.estimated_crisis_year;
  container.innerHTML = `
    <div class="pred-kpi-row">
      <div class="pred-kpi-tile">
        <div class="pred-kpi-label">Current Debt</div>
        <div class="pred-kpi-value" style="color:${ORANGE}">₹${data.current_debt_lc}L Cr</div>
        <div class="pred-kpi-sub">lakh crore 2024-25</div>
      </div>
      <div class="pred-kpi-tile">
        <div class="pred-kpi-label">CAGR</div>
        <div class="pred-kpi-value" style="color:${YELLOW}">${data.debt_cagr_pct}%</div>
        <div class="pred-kpi-sub">annual growth</div>
      </div>
      <div class="pred-kpi-tile" style="border-color:rgba(244,67,54,0.4)">
        <div class="pred-kpi-label">Crisis Year</div>
        <div class="pred-kpi-value" style="color:${RED}">${crisis || '?'}</div>
        <div class="pred-kpi-sub">debt service >30% revenue</div>
      </div>
    </div>
  `;

  if (!canvas) return;
  const projs = data.projections;
  const W = canvas.width = canvas.offsetWidth || 600;
  const H = canvas.height = 120;
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0,0,W,H);

  const pad = {t:12, r:8, b:24, l:44};
  const cW = W - pad.l - pad.r;
  const cH = H - pad.t - pad.b;
  const maxDebt = Math.max(...projs.map(p => p.debt_lc)) * 1.05;

  // Grid
  [2, 4, 6].forEach(v => {
    const y = pad.t + cH * (1 - v / Math.ceil(maxDebt));
    ctx.strokeStyle = 'rgba(240,165,0,0.07)'; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(W-pad.r, y); ctx.stroke();
    ctx.fillStyle = 'rgba(160,144,112,0.5)'; ctx.font = '8px Consolas'; ctx.textAlign = 'right';
    ctx.fillText('₹' + v + 'L', pad.l - 3, y + 3);
  });

  // Crisis threshold line (30% = estimate)
  const crisis_y = pad.t + cH * 0.25;
  ctx.strokeStyle = 'rgba(244,67,54,0.4)'; ctx.lineWidth = 1;
  ctx.setLineDash([4,4]);
  ctx.beginPath(); ctx.moveTo(pad.l, crisis_y); ctx.lineTo(W-pad.r, crisis_y); ctx.stroke();
  ctx.setLineDash([]);
  ctx.fillStyle = 'rgba(244,67,54,0.6)'; ctx.font = '7px Consolas'; ctx.textAlign = 'right';
  ctx.fillText('CRISIS THRESHOLD', W-pad.r, crisis_y - 3);

  // Debt line
  const pts = projs.map((p,i) => ({
    x: pad.l + (i / Math.max(projs.length - 1, 1)) * cW,
    y: pad.t + cH * (1 - p.debt_lc / maxDebt),
  }));
  ctx.beginPath();
  pts.forEach((p,i) => i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y));
  ctx.strokeStyle = ORANGE; ctx.lineWidth = 2; ctx.stroke();

  // Year labels
  ctx.fillStyle = 'rgba(138,122,96,0.6)'; ctx.font = '8px Consolas'; ctx.textAlign = 'center';
  projs.filter((_,i) => i % 3 === 0).forEach((p,i) => {
    const x = pad.l + (projs.indexOf(p) / Math.max(projs.length-1,1)) * cW;
    ctx.fillText(p.year, x, H - 6);
  });
  ctx.textAlign = 'left';
}

// ── 3. Composite scores panel ─────────────────────────────────────────────────
export function renderPredictionScores(container, data) {
  if (!data) { container.innerHTML = '<p class="pred-empty">No data</p>'; return; }

  const protest   = data.farmer_protest_probability  || {};
  const migration = data.migration_pressure          || {};
  const doaba     = data.doaba_distress_index        || {};

  container.innerHTML = `
    ${scoreGauge('Farmer Protest Probability', protest.score || 0, protest.level || 'LOW',
      `MSP gap: ${protest.components?.msp_gap || 0} · Seasonal: ${protest.components?.seasonal || 0} · Election: ${protest.components?.election || 0}`)}
    ${scoreGauge('Migration Pressure Index', migration.score || 0, migration.level || 'LOW',
      `Farm distress: ${migration.components?.farm_distress_push || 0} · GW push: ${migration.components?.groundwater_push || 0} · CAD pull: ${migration.components?.cad_pull_weakening || 0}`)}
    ${scoreGauge('Doaba Distress Index', doaba.score || 0, doaba.level || 'LOW',
      `Potash: ${doaba.components?.potash_price_spike || 0} · CAD weakening: ${doaba.components?.cad_weakening || 0} · BDI: ${doaba.components?.bdi_spike || 0}`)}
  `;
}

// ── 4. Sikh demographic projection ───────────────────────────────────────────
export function renderDemographicProjection(container, data) {
  if (!data || !data.projections) { container.innerHTML = '<p class="pred-empty">No data</p>'; return; }
  const { projections, minority_year, trend_per_decade, census_data } = data;

  const bars = projections.map(p => {
    const pct = p.sikh_pct_projected;
    const col = pct > 55 ? GREEN : pct > 50 ? YELLOW : pct > 45 ? ORANGE : RED;
    return `<div class="demog-bar-row">
      <span class="demog-year">${p.year}</span>
      <div class="demog-track">
        <div class="demog-fill" style="width:${Math.min(100, pct)}%;background:${col}"></div>
      </div>
      <span class="demog-pct" style="color:${col}">${pct}%</span>
    </div>`;
  }).join('');

  container.innerHTML = `
    <div class="pred-kpi-row">
      <div class="pred-kpi-tile">
        <div class="pred-kpi-label">2011 Census</div>
        <div class="pred-kpi-value" style="color:${GREEN}">57.7%</div>
        <div class="pred-kpi-sub">Sikh share Punjab</div>
      </div>
      <div class="pred-kpi-tile">
        <div class="pred-kpi-label">Trend</div>
        <div class="pred-kpi-value" style="color:${ORANGE}">${trend_per_decade > 0 ? '+' : ''}${trend_per_decade}%</div>
        <div class="pred-kpi-sub">per decade</div>
      </div>
      <div class="pred-kpi-tile" style="border-color:rgba(244,67,54,0.4)">
        <div class="pred-kpi-label">Minority Year</div>
        <div class="pred-kpi-value" style="color:${RED}">${minority_year || '—'}</div>
        <div class="pred-kpi-sub">projected &lt;50%</div>
      </div>
    </div>
    <div class="demog-bars">${bars}</div>
    <div class="pred-source">2021 census not released. Projection from 2001→2011 trend. Update when 2021 data publishes.</div>
  `;
}

// ── 5. Geopolitical indexes ───────────────────────────────────────────────────
export function renderGeopoliticalIndexes(container, data) {
  if (!data) { container.innerHTML = '<p class="pred-empty">No data</p>'; return; }

  const indexes = [
    { key: 'india_pakistan_conflict',  label: 'India-Pakistan Conflict Risk',    icon: '⚔️' },
    { key: 'food_security_cascade',    label: 'Global Food Crisis → Punjab',     icon: '🌾' },
    { key: 'diaspora_corridor_risk',   label: 'Diaspora Corridor Risk',          icon: '🍁' },
    { key: 'technology_sovereignty',   label: 'Tech Sovereignty Risk',           icon: '🔌' },
    { key: 'india_alignment_index',    label: 'India Global Alignment',          icon: '🧭' },
  ];

  container.innerHTML = indexes.map(idx => {
    const d = data[idx.key];
    if (!d) return '';
    const col = riskColor(d.level);
    const barW = Math.round(d.score);
    const compHtml = d.components
      ? Object.entries(d.components).map(([k,v]) =>
          `<span style="color:#8a7a60">${k.replace(/_/g,' ')}: </span><span style="color:${col}">${v}</span>`
        ).join(' &nbsp;·&nbsp; ')
      : '';
    const extra = d.label || d.interpretation || d.note || '';
    return `<div class="pred-gauge" style="margin-bottom:14px">
      <div class="pred-gauge-header">
        <span class="pred-gauge-label">${idx.icon} ${idx.label}</span>
        <span class="pred-gauge-score" style="color:${col}">${d.score}<span style="font-size:9px;color:#8a7a60">/100</span></span>
        <span class="pred-level-chip" style="background:rgba(0,0,0,0.3);border:1px solid ${col}44;color:${col}">${d.level}</span>
      </div>
      <div class="pred-gauge-track">
        <div class="pred-gauge-fill" style="width:${barW}%;background:${col}"></div>
      </div>
      ${compHtml ? `<div class="pred-gauge-sub" style="font-size:7px">${compHtml}</div>` : ''}
      ${extra ? `<div class="pred-gauge-sub" style="color:#8a7a60;margin-top:3px">${extra.slice(0,180)}</div>` : ''}
    </div>`;
  }).join('');
}

// ── Main render ───────────────────────────────────────────────────────────────
export async function renderPredictionsTab(pane) {
  if (!pane) return;
  pane.innerHTML = '<div style="padding:40px;text-align:center;color:#8a7a60;font-size:10px;letter-spacing:2px">LOADING PREDICTIONS…</div>';

  let data;
  try {
    const r = await fetch('./public/data/predictions.json?v=' + Date.now());
    data = await r.json();
  } catch(e) {
    pane.innerHTML = '<div class="pred-empty">Predictions data not yet available. Run the monthly pipeline first.</div>';
    return;
  }

  pane.innerHTML = `
    <div class="dash-row">
      <div class="dash-card full">
        <div class="dash-card-title">Geopolitical Risk Indexes — Engine IV · Global Signals → Punjab Impact</div>
        <div id="geo-indexes-el"></div>
      </div>
    </div>
    <div class="dash-row">
      <div class="dash-card full">
        <div class="dash-card-title">Domestic Intelligence Scores — Engine IV</div>
        <div id="pred-scores-el"></div>
      </div>
    </div>
    <div class="dash-row">
      <div class="dash-card full">
        <div class="dash-card-title">Groundwater Collapse Timeline — Years to Agricultural Unviability by District</div>
        <div id="gw-countdown-el"></div>
      </div>
    </div>
    <div class="dash-row">
      <div class="dash-card">
        <div class="dash-card-title">Punjab Fiscal Debt Trajectory</div>
        <div id="debt-kpi-el"></div>
        <canvas id="debt-canvas" class="dash-canvas" height="120" style="margin-top:10px"></canvas>
      </div>
      <div class="dash-card">
        <div class="dash-card-title">Sikh Demographic Projection</div>
        <div id="demog-el"></div>
      </div>
    </div>
  `;

  renderGeopoliticalIndexes(document.getElementById('geo-indexes-el'), data);
  renderPredictionScores(document.getElementById('pred-scores-el'), data);
  renderGroundwaterCountdown(document.getElementById('gw-countdown-el'), data.groundwater);
  const debtCanvas = document.getElementById('debt-canvas');
  renderDebtTrajectory(document.getElementById('debt-kpi-el'), debtCanvas, data.fiscal_debt);
  renderDemographicProjection(document.getElementById('demog-el'), data.sikh_demographic);
}
