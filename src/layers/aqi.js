// FALCON — Engine II add-on: CPCB Air Quality Index layer

const AQI_URL = './public/data/punjab_aqi.json?v=' + Date.now();

const AQI_COLORS = {
  'Good':         '#00e400',
  'Satisfactory': '#92d050',
  'Moderate':     '#ffff00',
  'Poor':         '#ff7e00',
  'Very Poor':    '#ff0000',
  'Severe':       '#800026',
};

let _primitives = null;
let _labels     = [];
let _loaded     = false;

export async function loadAQI(viewer) {
  if (_loaded) return;
  _loaded = true;

  let geojson;
  try {
    const res = await fetch(AQI_URL);
    geojson = await res.json();
  } catch (e) {
    console.warn('FALCON AQI: could not load data', e);
    return;
  }

  const features = geojson.features || [];
  if (!features.length) return;

  _primitives = viewer.scene.primitives.add(new Cesium.PointPrimitiveCollection());

  for (const f of features) {
    const [lon, lat] = f.geometry.coordinates;
    const p = f.properties;
    const color = Cesium.Color.fromCssColorString(AQI_COLORS[p.category] || '#ff7e00');
    const size  = Math.min(10 + (p.aqi / 500) * 24, 34);

    _primitives.add({
      position:    Cesium.Cartesian3.fromDegrees(lon, lat),
      color:       color.withAlpha(0.88),
      pixelSize:   size,
      outlineColor: Cesium.Color.BLACK.withAlpha(0.5),
      outlineWidth: 1,
      scaleByDistance: new Cesium.NearFarScalar(1e4, 1.4, 8e6, 0.5),
    });

    const label = viewer.entities.add({
      position: Cesium.Cartesian3.fromDegrees(lon, lat, 500),
      label: {
        text: `${p.city}\nAQI ${p.aqi}`,
        font: '11px Segoe UI',
        fillColor: color,
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 2,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        pixelOffset: new Cesium.Cartesian2(0, -size / 2 - 4),
        distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 500000),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
        scale: 0.9,
      }
    });
    _labels.push(label);
  }

  buildAQILegend();
  updateAQIBadge(features);
  console.log(`FALCON AQI: ${features.length} stations loaded`);
}

export function removeAQI(viewer) {
  if (_primitives) {
    viewer.scene.primitives.remove(_primitives);
    _primitives = null;
  }
  _labels.forEach(l => viewer.entities.remove(l));
  _labels = [];
  _loaded = false;

  const badge  = document.getElementById('aqi-badge');
  const legend = document.getElementById('aqi-legend');
  if (badge)  badge.style.display  = 'none';
  if (legend) legend.style.display = 'none';
}

function buildAQILegend() {
  const legend = document.getElementById('aqi-legend');
  if (!legend) return;
  legend.innerHTML = `
    <div class="leg-title">AIR QUALITY INDEX (AQI)</div>
    ${Object.entries(AQI_COLORS).map(([cat, col]) =>
      `<div class="leg-row"><div class="leg-dot" style="background:${col}"></div>${cat}</div>`
    ).join('')}
    <div style="font-size:8px;margin-top:4px;opacity:0.6">Source: CPCB SAMEER</div>
  `;
  legend.style.display = 'flex';
}

function updateAQIBadge(features) {
  const badge = document.getElementById('aqi-badge');
  if (!badge) return;
  const worst = features.reduce((a, b) => a.properties.aqi > b.properties.aqi ? a : b);
  const severe = features.filter(f => ['Very Poor','Severe'].includes(f.properties.category)).length;
  badge.style.display = 'flex';
  badge.innerHTML = `<span style="font-size:13px">🌫️</span><span>Worst: ${worst.properties.city} AQI ${worst.properties.aqi} · ${severe} stations Very Poor/Severe</span>`;
}
