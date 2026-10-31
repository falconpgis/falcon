// FALCON — Engine II add-on: AGMARKNET Mandi prices layer

const MANDI_URL = './public/data/punjab_mandi.json?v=' + Date.now();

// Color by MSP compliance: red = below MSP, green = at/above MSP
function priceColor(pct) {
  if (pct < 85)  return '#f44336'; // deeply below MSP
  if (pct < 95)  return '#ff9800'; // below MSP
  if (pct < 100) return '#ffeb3b'; // just below MSP
  return '#4caf50';                 // at or above MSP
}

let _primitives = null;
let _labels     = [];
let _loaded     = false;

export async function loadMandi(viewer) {
  if (_loaded) return;
  _loaded = true;

  let geojson;
  try {
    const res = await fetch(MANDI_URL);
    geojson = await res.json();
  } catch (e) {
    console.warn('FALCON mandi: could not load data', e);
    return;
  }

  const features = geojson.features || [];
  if (!features.length) return;

  _primitives = viewer.scene.primitives.add(new Cesium.PointPrimitiveCollection());

  for (const f of features) {
    const [lon, lat] = f.geometry.coordinates;
    const p = f.properties;
    const color = Cesium.Color.fromCssColorString(priceColor(p.msp_pct));

    _primitives.add({
      position:    Cesium.Cartesian3.fromDegrees(lon, lat),
      color:       color.withAlpha(0.85),
      pixelSize:   13,
      outlineColor: Cesium.Color.BLACK.withAlpha(0.5),
      outlineWidth: 1.5,
      scaleByDistance: new Cesium.NearFarScalar(1e4, 1.4, 8e6, 0.4),
    });

    const crop = (p.main_crop || 'crop').charAt(0).toUpperCase() + (p.main_crop || 'crop').slice(1);
    const label = viewer.entities.add({
      position: Cesium.Cartesian3.fromDegrees(lon, lat, 500),
      label: {
        text: `${p.city}\n${crop}: ₹${p.main_price}`,
        font: '10px Segoe UI',
        fillColor: color,
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 2,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        pixelOffset: new Cesium.Cartesian2(0, -10),
        distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 400000),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
        scale: 0.85,
      }
    });
    _labels.push(label);
  }

  buildMandiLegend(features);
  updateMandiBadge(features);
  console.log(`FALCON mandi: ${features.length} mandis loaded`);
}

export function removeMandi(viewer) {
  if (_primitives) {
    viewer.scene.primitives.remove(_primitives);
    _primitives = null;
  }
  _labels.forEach(l => viewer.entities.remove(l));
  _labels = [];
  _loaded = false;

  const badge  = document.getElementById('mandi-badge');
  const legend = document.getElementById('mandi-legend');
  if (badge)  badge.style.display  = 'none';
  if (legend) legend.style.display = 'none';
}

function buildMandiLegend(features) {
  const legend = document.getElementById('mandi-legend');
  if (!legend) return;
  const meta = features[0]?.properties;
  legend.innerHTML = `
    <div class="leg-title">MANDI PRICES vs MSP</div>
    <div class="leg-row"><div class="leg-dot" style="background:#4caf50"></div>At / Above MSP</div>
    <div class="leg-row"><div class="leg-dot" style="background:#ffeb3b"></div>Within 5% of MSP</div>
    <div class="leg-row"><div class="leg-dot" style="background:#ff9800"></div>5–15% Below MSP</div>
    <div class="leg-row"><div class="leg-dot" style="background:#f44336"></div>More than 15% Below MSP</div>
    <div style="font-size:8px;margin-top:4px;opacity:0.6">Source: AGMARKNET · Rs/quintal</div>
  `;
  legend.style.display = 'flex';
}

function updateMandiBadge(features) {
  const badge = document.getElementById('mandi-badge');
  if (!badge) return;
  const below = features.filter(f => f.properties.below_msp).length;
  badge.style.display = 'flex';
  badge.innerHTML = `<span style="font-size:13px">🌾</span><span>${below}/${features.length} mandis below MSP · click for prices</span>`;
}
