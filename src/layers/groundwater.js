// FALCON — Engine IV: CGWB Groundwater depletion layer

const GW_DATA_URL = './public/data/punjab_groundwater.geojson?v=' + Date.now();

// Color by category
const CAT_COLOR = {
  'safe':             Cesium.Color.fromCssColorString('#4caf50'),
  'semi-critical':    Cesium.Color.fromCssColorString('#ffeb3b'),
  'critical':         Cesium.Color.fromCssColorString('#ff9800'),
  'over-exploited':   Cesium.Color.fromCssColorString('#f44336'),
};

const CAT_LABEL = {
  'safe':           'Safe (< 70%)',
  'semi-critical':  'Semi-critical (70–90%)',
  'critical':       'Critical (90–100%)',
  'over-exploited': 'Over-exploited (> 100%)',
};

let _labels     = [];
let _primitives = null;
let _loaded     = false;

export async function loadGroundwater(viewer) {
  if (_loaded) return;
  _loaded = true;

  let geojson;
  try {
    const res = await fetch(GW_DATA_URL);
    geojson = await res.json();
  } catch (e) {
    console.warn('FALCON groundwater: could not load data', e);
    return;
  }

  const features = geojson.features || [];
  if (!features.length) return;

  _primitives = viewer.scene.primitives.add(new Cesium.PointPrimitiveCollection());

  for (const f of features) {
    const [lon, lat] = f.geometry.coordinates;
    const p = f.properties;
    const color = CAT_COLOR[p.category] || CAT_COLOR['safe'];
    const size  = Math.min(8 + p.depth_mbgl * 0.8, 36);

    _primitives.add({
      position:    Cesium.Cartesian3.fromDegrees(lon, lat),
      color:       color.withAlpha(0.85),
      pixelSize:   size,
      outlineColor: Cesium.Color.BLACK.withAlpha(0.5),
      outlineWidth: 1,
      scaleByDistance: new Cesium.NearFarScalar(1e4, 1.5, 8e6, 0.4),
    });

    // District label
    const label = viewer.entities.add({
      position: Cesium.Cartesian3.fromDegrees(lon, lat, 1000),
      label: {
        text: `${p.block || p.district}\n${p.depth_mbgl}m`,
        font: '11px Segoe UI',
        fillColor: Cesium.Color.WHITE,
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 2,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        pixelOffset: new Cesium.Cartesian2(0, -size / 2 - 4),
        distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 600000),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
        scale: 0.9,
      }
    });
    _labels.push(label);
  }

  buildLegend();
  updateGWBadge(features);
  console.log(`FALCON groundwater: ${features.length} districts loaded`);
}

export function removeGroundwater(viewer) {
  if (_primitives) {
    viewer.scene.primitives.remove(_primitives);
    _primitives = null;
  }
  _labels.forEach(l => viewer.entities.remove(l));
  _labels = [];
  _loaded = false;

  const badge  = document.getElementById('gw-badge');
  const legend = document.getElementById('gw-legend');
  if (badge)  badge.style.display  = 'none';
  if (legend) legend.style.display = 'none';
}

function buildLegend() {
  const legend = document.getElementById('gw-legend');
  if (!legend) return;
  legend.innerHTML = `
    <div class="leg-title">GROUNDWATER DEPTH</div>
    <div class="leg-row"><div class="leg-dot" style="background:#4caf50"></div>${CAT_LABEL['safe']}</div>
    <div class="leg-row"><div class="leg-dot" style="background:#ffeb3b"></div>${CAT_LABEL['semi-critical']}</div>
    <div class="leg-row"><div class="leg-dot" style="background:#ff9800"></div>${CAT_LABEL['critical']}</div>
    <div class="leg-row"><div class="leg-dot" style="background:#f44336"></div>${CAT_LABEL['over-exploited']}</div>
    <div style="font-size:8px;margin-top:4px;opacity:0.6">Larger circle = deeper water table<br>Source: CGWB 2023-24</div>
  `;
  legend.style.display = 'flex';
}

function updateGWBadge(features) {
  const badge = document.getElementById('gw-badge');
  if (!badge) return;
  const over = features.filter(f => f.properties.category === 'over-exploited').length;
  const crit = features.filter(f => f.properties.category === 'critical').length;
  badge.style.display = 'flex';
  badge.innerHTML = `<span style="font-size:13px">💧</span><span>${over} over-exploited · ${crit} critical districts</span>`;
}
