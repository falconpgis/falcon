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

let _primitives = null;
let _labels     = [];
let _loaded     = false;

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

  buildPredLegend(features);
  updatePredBadge(features);
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

  const badge  = document.getElementById('prediction-badge');
  const legend = document.getElementById('prediction-legend');
  if (badge)  badge.style.display  = 'none';
  if (legend) legend.style.display = 'none';
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
