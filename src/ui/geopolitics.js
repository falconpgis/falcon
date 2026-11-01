// FALCON Engine III — Geopolitical Intelligence Dashboard
// Renders: international bodies, Next Yalta scenarios, India alignment,
//          Sikh political power, sanction watch, Yalta pattern history

const GOLD   = '#f0a500';
const RED    = '#f44336';
const ORANGE = '#ff9800';
const YELLOW = '#ffd600';
const GREEN  = '#5a9f5a';
const MUTED  = '#8a7a60';
const TEXT   = '#e2d8c4';

function hex(h, a) {
  const r = parseInt(h.slice(1,3),16), g = parseInt(h.slice(3,5),16), b = parseInt(h.slice(5,7),16);
  return `rgba(${r},${g},${b},${a})`;
}

function riskCol(r) {
  return {CRITICAL:RED, HIGH:ORANGE, 'HIGH-MEDIUM':ORANGE, MODERATE:YELLOW,
          'LOW-MEDIUM':GREEN, LOW:GREEN}[r] || GOLD;
}

// ── Alignment arc ─────────────────────────────────────────────────────────────
function drawAlignmentArc(canvas, score) {
  const W = canvas.width = canvas.offsetWidth || 320;
  const H = canvas.height = 100;
  const cx = W / 2, cy = H - 8, r = Math.min(cx, cy) - 16;
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, W, H);

  // Background arc (180°)
  const startA = Math.PI, endA = 2 * Math.PI;
  ctx.beginPath(); ctx.arc(cx, cy, r, startA, endA);
  ctx.strokeStyle = 'rgba(240,165,0,0.1)'; ctx.lineWidth = 12; ctx.stroke();

  // Filled portion
  const fillEnd = Math.PI + (score / 100) * Math.PI;
  const grad = ctx.createLinearGradient(cx - r, cy, cx + r, cy);
  grad.addColorStop(0, '#ef5350'); grad.addColorStop(0.5, YELLOW); grad.addColorStop(1, '#42a5f5');
  ctx.beginPath(); ctx.arc(cx, cy, r, startA, fillEnd);
  ctx.strokeStyle = grad; ctx.lineWidth = 12; ctx.stroke();

  // Needle
  const a = Math.PI + (score / 100) * Math.PI;
  const nx = cx + (r) * Math.cos(a), ny = cy + (r) * Math.sin(a);
  ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(nx, ny);
  ctx.strokeStyle = GOLD; ctx.lineWidth = 2; ctx.stroke();
  ctx.beginPath(); ctx.arc(cx, cy, 5, 0, 2 * Math.PI);
  ctx.fillStyle = GOLD; ctx.fill();

  // Labels
  ctx.fillStyle = RED; ctx.font = '7px Consolas'; ctx.textAlign = 'left';
  ctx.fillText('CHINA/RUS', 4, H - 10);
  ctx.fillStyle = '#42a5f5'; ctx.textAlign = 'right';
  ctx.fillText('USA/WEST', W - 4, H - 10);
  ctx.fillStyle = GOLD; ctx.textAlign = 'center';
  ctx.font = 'bold 14px Consolas';
  ctx.fillText(score, cx, cy - r * 0.35);
  ctx.font = '7px Consolas'; ctx.fillStyle = MUTED;
  ctx.fillText('/100', cx, cy - r * 0.35 + 12);
}

// ── Scenario card ─────────────────────────────────────────────────────────────
function scenarioCard(s) {
  const prob = s.probability;
  const col  = prob >= 40 ? RED : prob >= 25 ? ORANGE : YELLOW;
  const impactCol = {CRITICAL: RED, EXTREME: RED, HIGH: ORANGE, MODERATE: YELLOW, SYSTEMIC: RED}[
    s.punjab_impact?.split(' ')[0]] || YELLOW;

  return `<div class="geo-scenario-card" style="border-left:3px solid ${hex(col,0.6)}">
    <div class="geo-scenario-header">
      <span class="geo-scenario-title">${s.title}</span>
      <span class="geo-prob-badge" style="background:${hex(col,0.15)};border:1px solid ${hex(col,0.4)};color:${col}">${prob}%</span>
    </div>
    <div class="geo-scenario-timeframe" style="color:${MUTED}">⏱ ${s.timeframe}</div>
    <div class="geo-scenario-trigger">🔴 <span style="color:#c9bfa8">${s.trigger}</span></div>
    <div class="geo-scenario-who">🔵 Decides: <span style="color:${MUTED}">${(s.who_decides||[]).join(' · ')}</span></div>
    <div class="geo-scenario-impact" style="color:${impactCol}">⚡ Punjab: ${s.punjab_impact}</div>
    <div class="geo-scenario-rep" style="color:${MUTED}">👁 Sikh voice: ${s.sikh_representation}</div>
    <div class="geo-scenario-watch">📡 Watch: <span style="color:${MUTED}">${s.signal_to_watch}</span></div>
  </div>`;
}

// ── Yalta history timeline ────────────────────────────────────────────────────
function yaltaTimeline(history) {
  if (!history || !history.length) return '<p class="pred-empty">No data</p>';
  return `<div class="yalta-timeline">
    ${history.map((h, i) => `
      <div class="yalta-item">
        <div class="yalta-year" style="color:${RED}">${h.year}</div>
        <div class="yalta-connector"></div>
        <div class="yalta-content">
          <div class="yalta-event">${h.event}</div>
          <div class="yalta-powers">Powers: ${h.major_powers.join(' · ')}</div>
          <div class="yalta-impact" style="color:${ORANGE}">${h.punjab_impact}</div>
          <div class="yalta-pattern" style="color:${MUTED}">Pattern: ${h.pattern}</div>
        </div>
      </div>
    `).join('')}
  </div>`;
}

// ── International bodies grid ─────────────────────────────────────────────────
function bodiesGrid(bodies) {
  if (!bodies) return '';
  return Object.entries(bodies).map(([key, b]) => {
    const memberCol = b.india_member ? GREEN : RED;
    const memberLabel = b.india_member ? '✓ INDIA IN' : '✗ INDIA OUT';
    return `<div class="geo-body-card">
      <div class="geo-body-header">
        <span class="geo-body-name">${b.name}</span>
        <span class="geo-body-member" style="color:${memberCol}">${memberLabel}</span>
      </div>
      <div class="geo-body-note" style="color:${MUTED}">${b.note}</div>
      <div class="geo-body-impact" style="color:${TEXT}">Punjab: ${b.punjab_relevance}</div>
    </div>`;
  }).join('');
}

// ── Sikh power map ────────────────────────────────────────────────────────────
function sikhPowerSection(data) {
  if (!data) return '';
  const countries = ['canada','uk','usa'].map(c => {
    const d = data[c]; if (!d) return '';
    const pop = d.population_est ? (d.population_est/1000).toFixed(0) + 'K' : '?';
    const reps = d.federal_mps || d.parliament_members || d.congress_members || 0;
    const col = reps >= 10 ? GREEN : reps >= 5 ? YELLOW : reps >= 1 ? ORANGE : RED;
    return `<div class="sikh-power-tile">
      <div class="sikh-power-flag">${{canada:'🍁',uk:'🇬🇧',usa:'🦅'}[c]}</div>
      <div class="sikh-power-country">${c.toUpperCase()}</div>
      <div class="sikh-power-pop" style="color:${MUTED}">${pop} Punjabis</div>
      <div class="sikh-power-reps" style="color:${col}">${reps} MPs/reps</div>
      <div class="sikh-power-level" style="color:${col};font-size:7px">${d.power_level}</div>
      <div class="sikh-power-risk" style="color:${ORANGE};font-size:7px">${d.risk}</div>
    </div>`;
  }).join('');
  return `
    <div class="sikh-power-grid">${countries}</div>
    <div class="geo-note" style="margin-top:8px">SGPC annual budget: ~₹${data.sgpc_budget_cr || 900} Cr · ${data.collective_influence_note || ''}</div>
  `;
}

// ── Sanction watch ────────────────────────────────────────────────────────────
function sanctionWatch(data) {
  if (!data) return '';
  const labels = {
    russia_sanctions: '🇷🇺 Russia Sanctions',
    iran_sanctions: '🇮🇷 Iran Sanctions',
    china_tech_controls: '🔌 China Tech Controls',
    canada_india_tension: '🍁 Canada-India Tension',
  };
  return Object.entries(data).map(([k,v]) => {
    const col = riskCol(v.risk);
    return `<div class="sanction-row">
      <span class="sanction-name">${labels[k] || k}</span>
      <span class="sanction-risk" style="color:${col};border-color:${hex(col,0.4)}">${v.risk}</span>
      <div class="sanction-impact">${v.punjab_impact}</div>
    </div>`;
  }).join('');
}

// ── Recent geopolitical events feed ──────────────────────────────────────────
function recentEvents(events) {
  if (!events || !events.length) {
    return '<p class="pred-empty">Run daily pipeline for live geopolitical events</p>';
  }
  return events.slice(0, 30).map(e => {
    const tone = e.tone;
    const tCol = tone >= 2 ? GREEN : tone <= -2 ? RED : ORANGE;
    return `<a class="news-card" href="${e.url}" target="_blank" rel="noopener"
        style="border-left:3px solid ${hex(GOLD,0.3)}">
      <div class="news-topic-chip" style="color:${tCol};background:${hex(tCol,0.1)}">${e.topic.replace(/_/g,' ').toUpperCase()}</div>
      <div class="news-title">${e.title}</div>
      <div class="news-meta">${e.source} · ${e.date}${tone != null ? ` · tone ${tone > 0 ? '+' : ''}${tone}` : ''}</div>
    </a>`;
  }).join('');
}

// ── Main render ───────────────────────────────────────────────────────────────
export async function renderGeopoliticsTab(pane) {
  if (!pane) return;
  pane.innerHTML = `<div style="padding:40px;text-align:center;color:${MUTED};font-size:10px;letter-spacing:2px">LOADING GEOPOLITICAL INTELLIGENCE…</div>`;

  let data;
  try {
    const r = await fetch('./public/data/geopolitics.json?v=' + Date.now());
    data = await r.json();
  } catch(e) {
    pane.innerHTML = '<div class="pred-empty">Geopolitics data not yet available.</div>';
    return;
  }

  const al = data.india_alignment || {};
  const scenarios = data.next_yalta_scenarios || [];
  const bodies    = data.international_bodies || {};
  const history   = data.yalta_pattern_history || [];
  const sikhPow   = data.sikh_political_power || {};
  const sanction  = data.sanction_watch || {};
  const events    = data.recent_events || [];

  pane.innerHTML = `

    <!-- Row 1: Alignment + Sanction Watch -->
    <div class="dash-row">
      <div class="dash-card">
        <div class="dash-card-title">India Global Alignment — Engine III</div>
        <canvas id="alignment-arc" class="dash-canvas" style="max-height:100px"></canvas>
        <div style="margin-top:8px">
          <div style="font-size:11px;color:${GOLD};font-weight:600;margin-bottom:4px">${al.label || ''}</div>
          <div style="font-size:9px;color:${MUTED};line-height:1.5">${al.interpretation || ''}</div>
          <div style="font-size:9px;color:${ORANGE};margin-top:6px">Punjab: ${al.punjab_impact || ''}</div>
        </div>
        <div class="geo-signals-row" id="alignment-signals"></div>
      </div>
      <div class="dash-card">
        <div class="dash-card-title">Sanction & Tension Watch</div>
        <div id="sanction-watch-el"></div>
      </div>
    </div>

    <!-- Row 2: International Bodies -->
    <div class="dash-row">
      <div class="dash-card full">
        <div class="dash-card-title">International Bodies — India's Seat at the Table</div>
        <div class="geo-bodies-grid" id="bodies-grid"></div>
      </div>
    </div>

    <!-- Row 3: Sikh Political Power -->
    <div class="dash-row">
      <div class="dash-card full">
        <div class="dash-card-title">Sikh Political Power Map — Who Represents Punjab in Global Rooms</div>
        <div id="sikh-power-el"></div>
      </div>
    </div>

    <!-- Row 4: Next Yalta Scenarios -->
    <div class="dash-row">
      <div class="dash-card full">
        <div class="dash-card-title">The Next Yalta — Scenarios Where Major Powers Decide Punjab's Future</div>
        <div style="font-size:8px;color:${MUTED};margin-bottom:12px;line-height:1.6">
          Yalta 1945: Roosevelt, Churchill, Stalin decided the post-war world. No South Asian, no Sikh, no Punjabi in the room.
          The maps were drawn. Punjab paid the price in 1947. This tracker identifies the next set of decisions being made
          in rooms where Punjab has no voice.
        </div>
        <div class="geo-scenarios-grid" id="scenarios-el"></div>
      </div>
    </div>

    <!-- Row 5: Yalta Pattern History -->
    <div class="dash-row">
      <div class="dash-card full">
        <div class="dash-card-title">Historical Yalta Pattern — Each Time Major Powers Decided, Punjab Paid</div>
        <div id="yalta-history-el"></div>
      </div>
    </div>

    <!-- Row 6: Live Events Feed -->
    <div class="dash-row">
      <div class="dash-card full">
        <div class="dash-card-title">Geopolitical Events Feed — Live Intelligence</div>
        <div id="geo-events-el"></div>
      </div>
    </div>

  `;

  // Alignment arc
  const arcCanvas = document.getElementById('alignment-arc');
  if (arcCanvas) drawAlignmentArc(arcCanvas, al.score || 52);

  // Alignment signals
  const sigEl = document.getElementById('alignment-signals');
  if (sigEl && al.signals) {
    sigEl.innerHTML = Object.entries(al.signals).map(([k,v]) => {
      const n = parseFloat(v); const col = n > 0 ? '#42a5f5' : RED;
      return `<div class="geo-signal-chip" style="color:${col}">
        ${k}: <b>${v}</b>
      </div>`;
    }).join('');
  }

  document.getElementById('sanction-watch-el').innerHTML = sanctionWatch(sanction);
  document.getElementById('bodies-grid').innerHTML = bodiesGrid(bodies);
  document.getElementById('sikh-power-el').innerHTML = sikhPowerSection(sikhPow);
  document.getElementById('scenarios-el').innerHTML = scenarios.map(scenarioCard).join('');
  document.getElementById('yalta-history-el').innerHTML = yaltaTimeline(history);
  document.getElementById('geo-events-el').innerHTML = recentEvents(events);
}
