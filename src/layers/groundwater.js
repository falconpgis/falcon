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
let _clickHandler = null;

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
      id: { type: 'gw', lon, lat, props: p },
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

  // Click popup
  if (!_clickHandler) {
    _clickHandler = viewer.screenSpaceEventHandler.setInputAction(e => {
      const picked = viewer.scene.pick(e.position);
      if (picked && picked.id && picked.id.type === 'gw') {
        showGWPopup(picked.id.props, picked.id.lon, picked.id.lat);
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
  }

  buildLegend();
  updateGWBadge(features);
  console.log(`FALCON groundwater: ${features.length} districts loaded`);
}

function showGWPopup(p, lon, lat) {
  const popup = document.getElementById('gw-popup');
  if (!popup) return;
  const catColor = { safe:'#4caf50','semi-critical':'#ffeb3b',critical:'#ff9800','over-exploited':'#f44336' };
  const col = catColor[p.category] || '#ff9800';
  const trendIcon = { stable:'→', declining:'↓', 'rapidly declining':'↓↓' }[p.trend] || '→';
  popup.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px">
      <span style="font-size:10px;letter-spacing:2px;color:${col};text-transform:uppercase">💧 ${p.category}</span>
      <button onclick="document.getElementById('gw-popup').style.display='none'" style="background:none;border:none;color:#a09070;cursor:pointer;font-size:14px;padding:0;margin-left:8px">✕</button>
    </div>
    <div style="font-size:13px;font-weight:600;color:#e8e0d0;margin-bottom:2px">${p.block || p.district}</div>
    <div style="font-size:10px;color:#a09070;margin-bottom:8px">${p.district} District</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px 12px;font-size:10px;color:#c8c0b0">
      <span style="color:#a09070">Depth to water</span><span style="color:${col};font-weight:600">${p.depth_mbgl} m below ground</span>
      <span style="color:#a09070">Extraction stage</span><span>${p.stage_pct}% of safe yield</span>
      <span style="color:#a09070">Trend</span><span>${trendIcon} ${p.trend || '—'}</span>
      <span style="color:#a09070">Source</span><span>CGWB 2023-24</span>
    </div>
  `;
  popup.style.display = 'block';
}

export function removeGroundwater(viewer) {
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

  ['gw-badge','gw-legend','gw-popup'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = 'none';
  });
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
