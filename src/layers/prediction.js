// FALCON — Engine IV: Agrarian Distress Prediction layer

const PRED_URL = './public/data/punjab_prediction.geojson?v=' + Date.now();

const CAT_COLORS = {
  'Low':      '#4caf50',
  'Moderate': '#ffeb3b',
  'High':     '#ff9800',
  'Critical': '#f44336',
  'Extreme':  '#7b1fa2',
};

const REGION_LABELS = {
  doaba: 'Doaba', malwa: 'Malwa', majha: 'Majha', himachal_foothills: 'Foothills',
};

let _primitives   = null;
let _labels       = [];
let _loaded       = false;
let _clickHandler = null;

export async function loadPrediction(viewer) {
  if (_loaded) return;
  _loaded = true;

  let geojson;
  try {
    const res = await fetch(PRED_URL);
    geojson = await res.json();
  } catch (e) {
    console.warn('FALCON prediction: could not load data', e);
    return;
  }

  const features = geojson.features || [];
  if (!features.length) return;

  _primitives = viewer.scene.primitives.add(new Cesium.PointPrimitiveCollection());

  for (const f of features) {
    const [lon, lat] = f.geometry.coordinates;
    const p = f.properties;
    const color = Cesium.Color.fromCssColorString(CAT_COLORS[p.category] || '#ff9800');
    const size  = Math.min(10 + p.ddi_score * 2.5, 42);

    _primitives.add({
      position:    Cesium.Cartesian3.fromDegrees(lon, lat),
      color:       color.withAlpha(0.88),
      pixelSize:   size,
      outlineColor: Cesium.Color.BLACK.withAlpha(0.5),
      outlineWidth: 1.5,
      scaleByDistance: new Cesium.NearFarScalar(1e4, 1.4, 8e6, 0.4),
      id: { type: 'pred', lon, lat, props: p },
    });

    const label = viewer.entities.add({
      position: Cesium.Cartesian3.fromDegrees(lon, lat, 500),
      label: {
        text: `${p.district}\nDDI ${p.ddi_score}/10`,
        font: '11px Segoe UI',
        fillColor: color,
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 2,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        pixelOffset: new Cesium.Cartesian2(0, -size / 2 - 4),
        distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 500000),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
        scale: 0.88,
      }
    });
    _labels.push(label);
  }

  // Click popup
  if (!_clickHandler) {
    _clickHandler = viewer.screenSpaceEventHandler.setInputAction(e => {
      const picked = viewer.scene.pick(e.position);
      if (picked && picked.id && picked.id.type === 'pred') {
        showPredPopup(picked.id.props, picked.id.lon, picked.id.lat);
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
  }

  buildPredLegend(features);
  updatePredBadge(features);
  loadSDLBonds();
  console.log(`FALCON prediction: ${features.length} districts loaded`);
}

export function removePrediction(viewer) {
  if (_primitives) {
    viewer.scene.primitives.remove(_primitives);
    _primitives = null;
  }
  _labels.forEach(l => viewer.entities.remove(l));
  _labels = [];
  _loaded = false;

  if (_clickHandler !== null) {
    viewer.screenSpaceEventHandler.removeInputAction(Cesium.ScreenSpaceEventType.LEFT_CLICK);
    _clickHandler = null;
  }

  ['prediction-badge','prediction-legend','pred-popup'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = 'none';
  });
}

function showPredPopup(p, lon, lat) {
  const popup = document.getElementById('pred-popup');
  if (!popup) return;
  const col = CAT_COLORS[p.category] || '#ff9800';
  const bar = (score) => {
    const pct = Math.round(score * 10);
    return `<div style="background:rgba(255,255,255,0.1);border-radius:2px;height:6px;width:100%;margin-top:2px">
      <div style="background:${col};height:6px;border-radius:2px;width:${pct}%"></div></div>`;
  };
  popup.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px">
      <span style="font-size:10px;letter-spacing:2px;color:${col};text-transform:uppercase">⚠️ ${p.category} DISTRESS</span>
      <button onclick="document.getElementById('pred-popup').style.display='none'" style="background:none;border:none;color:#a09070;cursor:pointer;font-size:14px;padding:0;margin-left:8px">✕</button>
    </div>
    <div style="font-size:13px;font-weight:600;color:#e8e0d0;margin-bottom:2px">${p.district}</div>
    <div style="font-size:10px;color:#a09070;margin-bottom:8px">${REGION_LABELS[p.region] || p.region} Region</div>
    <div style="font-size:11px;color:${col};font-weight:700;margin-bottom:6px">DDI Score: ${p.ddi_score} / 10</div>
    ${bar(p.ddi_score)}
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px 12px;font-size:10px;color:#c8c0b0;margin-top:10px">
      <span style="color:#a09070">Groundwater (35%)</span><span>${p.gw_score ?? '—'}/10</span>
      <span style="color:#a09070">Fire risk (20%)</span><span>${p.fire_score ?? '—'}/10</span>
      <span style="color:#a09070">Debt burden (25%)</span><span>${p.debt_score ?? '—'}/10</span>
      <span style="color:#a09070">Migration (20%)</span><span>${p.migration_score ?? '—'}/10</span>
    </div>
  `;
  popup.style.display = 'block';
}

async function loadSDLBonds() {
  try {
    const res = await fetch('./public/data/punjab_sdl_bonds.json?v=' + Date.now());
    const data = await res.json();
    const legend = document.getElementById('prediction-legend');
    if (!legend || !data.latest) return;
    const l = data.latest;
    const spreadColor = l.spread_bps > 70 ? '#f44336' : l.spread_bps > 50 ? '#ff9800' : '#4caf50';
    const extra = document.createElement('div');
    extra.innerHTML = `
      <div style="border-top:1px solid rgba(240,165,0,0.15);margin-top:6px;padding-top:6px">
        <div style="font-size:8px;letter-spacing:2px;color:#f0a500;margin-bottom:4px">PUNJAB FISCAL STRESS</div>
        <div class="leg-row" style="justify-content:space-between"><span>SDL yield</span><span style="color:#e8e0d0">${l.sdl_yield_pct}%</span></div>
        <div class="leg-row" style="justify-content:space-between"><span>Spread vs G-Sec</span><span style="color:${spreadColor}">${l.spread_bps} bps</span></div>
        <div class="leg-row" style="justify-content:space-between"><span>Fiscal deficit</span><span style="color:#ff9800">${l.fiscal_deficit_gdp_pct}% GDP</span></div>
        <div class="leg-row" style="justify-content:space-between"><span>Debt outstanding</span><span style="color:#e8e0d0">₹${(l.outstanding_debt_cr/1e5).toFixed(1)}L Cr</span></div>
      </div>`;
    legend.appendChild(extra);
  } catch (e) { /* SDL data optional */ }
}

function buildPredLegend(features) {
  const legend = document.getElementById('prediction-legend');
  if (!legend) return;
  const top3 = [...features].sort((a,b) => b.properties.ddi_score - a.properties.ddi_score).slice(0,3);
  legend.innerHTML = `
    <div class="leg-title">DISTRESS INDEX (DDI) 0–10</div>
    ${Object.entries(CAT_COLORS).map(([cat,col]) =>
      `<div class="leg-row"><div class="leg-dot" style="background:${col}"></div>${cat}</div>`
    ).join('')}
    <div style="border-top:1px solid rgba(240,165,0,0.15);margin-top:6px;padding-top:6px;font-size:8px;letter-spacing:2px;color:#f0a500">TOP DISTRESS DISTRICTS</div>
    ${top3.map(f => `<div class="leg-row" style="justify-content:space-between">
      <span>${f.properties.district}</span>
      <span style="color:${CAT_COLORS[f.properties.category]}">${f.properties.ddi_score}</span>
    </div>`).join('')}
    <div style="font-size:8px;margin-top:4px;opacity:0.6">Groundwater · Fire · Debt · Migration</div>
  `;
  legend.style.display = 'flex';
}

function updatePredBadge(features) {
  const badge = document.getElementById('prediction-badge');
  if (!badge) return;
  const extreme  = features.filter(f => f.properties.category === 'Extreme').length;
  const critical = features.filter(f => f.properties.category === 'Critical').length;
  const worst = features.reduce((a,b) => a.properties.ddi_score > b.properties.ddi_score ? a : b);
  badge.style.display = 'flex';
  badge.innerHTML = `<span style="font-size:13px">⚠️</span><span>${extreme} Extreme · ${critical} Critical · Worst: ${worst.properties.district} DDI ${worst.properties.ddi_score}</span>`;
}
