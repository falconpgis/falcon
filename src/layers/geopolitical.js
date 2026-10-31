// FALCON — Engine III: Geopolitical Intelligence layer

const GEO_URL = './public/data/geopolitical.geojson?v=' + Date.now();

const CAT = {
  border:   { color: '#ef5350', label: 'Border / Crossing', size: 14 },
  battle:   { color: '#b71c1c', label: 'Historic Battle', size: 16 },
  corridor: { color: '#ff8f00', label: 'Historic Invasion Corridor', size: 15 },
  nuclear:  { color: '#7b1fa2', label: 'Nuclear Site', size: 18 },
  cpec:     { color: '#d32f2f', label: 'CPEC — Chinese Corridor', size: 14 },
  instc:    { color: '#1565c0', label: 'INSTC — India-Russia Corridor', size: 13 },
  water:    { color: '#0277bd', label: 'Water Dispute', size: 14 },
  city:     { color: '#78909c', label: 'Strategic City', size: 12 },
};

let _primitives = null;
let _labels     = [];
let _infoBox    = null;
let _loaded     = false;

export async function loadGeopolitical(viewer) {
  if (_loaded) return;
  _loaded = true;

  let geojson;
  try {
    const res = await fetch(GEO_URL);
    geojson = await res.json();
  } catch (e) {
    console.warn('FALCON geopolitical: could not load data', e);
    return;
  }

  const features = geojson.features || [];
  if (!features.length) return;

  // Fly out to regional view to show cross-border context
  viewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(75.5, 30.5, 4000000),
    orientation: { heading: 0, pitch: Cesium.Math.toRadians(-75), roll: 0 },
    duration: 2,
  });

  _primitives = viewer.scene.primitives.add(new Cesium.PointPrimitiveCollection());

  for (const f of features) {
    const [lon, lat] = f.geometry.coordinates;
    const p = f.properties;
    const cfg = CAT[p.category] || CAT.city;
    const col = Cesium.Color.fromCssColorString(cfg.color);

    _primitives.add({
      position:    Cesium.Cartesian3.fromDegrees(lon, lat),
      color:       col.withAlpha(0.92),
      pixelSize:   cfg.size,
      outlineColor: Cesium.Color.WHITE.withAlpha(0.4),
      outlineWidth: 1.5,
      scaleByDistance: new Cesium.NearFarScalar(1e4, 1.4, 1e7, 0.4),
      id: { type: 'geo', properties: p, lon, lat },
    });

    const label = viewer.entities.add({
      position: Cesium.Cartesian3.fromDegrees(lon, lat, 1000),
      label: {
        text: p.name,
        font: '10px Segoe UI',
        fillColor: col,
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 2,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        pixelOffset: new Cesium.Cartesian2(0, -cfg.size / 2 - 4),
        distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 3000000),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
        scale: 0.85,
      }
    });
    _labels.push(label);
  }

  // Click popup
  _infoBox = viewer.screenSpaceEventHandler.setInputAction(e => {
    const picked = viewer.scene.pick(e.position);
    if (picked && picked.id && picked.id.type === 'geo') {
      showGeoPopup(picked.id.properties);
    }
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

  buildGeoLegend(features);
  updateGeoBadge(features);
  console.log(`FALCON geopolitical: ${features.length} features loaded`);
}

export function removeGeopolitical(viewer) {
  if (_primitives) {
    viewer.scene.primitives.remove(_primitives);
    _primitives = null;
  }
  _labels.forEach(l => viewer.entities.remove(l));
  _labels = [];
  _loaded = false;

  if (_infoBox !== null) {
    viewer.screenSpaceEventHandler.removeInputAction(Cesium.ScreenSpaceEventType.LEFT_CLICK);
    _infoBox = null;
  }

  ['geo-badge','geo-legend','geo-popup'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = 'none';
  });

  // Return camera to Punjab
  viewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(75.35, 30.9, 150000),
    orientation: { heading: 0, pitch: Cesium.Math.toRadians(-75), roll: 0 },
    duration: 1.5,
  });
}

function showGeoPopup(p) {
  const popup = document.getElementById('geo-popup');
  if (!popup) return;
  const cfg = CAT[p.category] || CAT.city;
  popup.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px">
      <span style="font-size:10px;letter-spacing:2px;color:${cfg.color};text-transform:uppercase">${cfg.label}</span>
      <button onclick="document.getElementById('geo-popup').style.display='none'" style="background:none;border:none;color:#a09070;cursor:pointer;font-size:14px;padding:0;margin-left:8px">✕</button>
    </div>
    <div style="font-size:13px;font-weight:600;color:#e8e0d0;margin-bottom:6px">${p.name}</div>
    <div style="font-size:10px;color:#c8c0b0;line-height:1.5">${p.description}</div>
  `;
  popup.style.display = 'block';
}

function buildGeoLegend(features) {
  const legend = document.getElementById('geo-legend');
  if (!legend) return;
  const cats = [...new Set(features.map(f => f.properties.category))];
  legend.innerHTML = `
    <div class="leg-title">GEOPOLITICAL INTELLIGENCE</div>
    ${cats.map(c => {
      const cfg = CAT[c] || CAT.city;
      return `<div class="leg-row"><div class="leg-dot" style="background:${cfg.color}"></div>${cfg.label}</div>`;
    }).join('')}
    <div style="font-size:8px;margin-top:4px;opacity:0.6">Click site for details · Open source</div>
  `;
  legend.style.display = 'flex';
}

function updateGeoBadge(features) {
  const badge = document.getElementById('geo-badge');
  if (!badge) return;
  const nuclear = features.filter(f => f.properties.category === 'nuclear').length;
  const cpec    = features.filter(f => f.properties.category === 'cpec').length;
  badge.style.display = 'flex';
  badge.innerHTML = `<span style="font-size:13px">🌐</span><span>${features.length} strategic sites · ${nuclear} nuclear · ${cpec} CPEC nodes</span>`;
}
