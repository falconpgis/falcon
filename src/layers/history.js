// FALCON — Engine I: Sikh Historical Sites layer

const HIST_URL = './public/data/sikh_historical_sites.geojson?v=' + Date.now();

const CAT = {
  guru_parkash:  { color: '#f0a500', label: 'Guru Sahib — Parkash / Key Site', size: 14 },
  shaheedi:      { color: '#e53935', label: 'Shaheedi', size: 16 },
  jyoti_jot:     { color: '#ff9800', label: 'Jyoti Jot', size: 14 },
  takht:         { color: '#ce93d8', label: 'Sri Takht Sahib', size: 16 },
  gurdwara:      { color: '#81d4fa', label: 'Historic Gurdwara', size: 12 },
  ghalughara:    { color: '#b71c1c', label: 'Ghalughara — Mass Martyrdom', size: 18 },
  battle:        { color: '#ef9a9a', label: 'Anglo-Sikh War Battle', size: 11 },
  sikh_empire:   { color: '#80cbc4', label: 'Sikh Empire / Misl', size: 12 },
  massacre:      { color: '#7b1fa2', label: 'Massacre', size: 18 },
  partition:     { color: '#ff7043', label: 'Partition 1947', size: 13 },
};

let _primitives = null;
let _labels     = [];
let _loaded     = false;
let _infoBox    = null;

export async function loadHistory(viewer) {
  if (_loaded) return;
  _loaded = true;

  let geojson;
  try {
    const res = await fetch(HIST_URL);
    geojson = await res.json();
  } catch (e) {
    console.warn('FALCON history: could not load data', e);
    return;
  }

  const features = geojson.features || [];
  if (!features.length) return;

  _primitives = viewer.scene.primitives.add(new Cesium.PointPrimitiveCollection());

  for (const f of features) {
    const [lon, lat] = f.geometry.coordinates;
    const p = f.properties;
    const cfg = CAT[p.category] || CAT.gurdwara;
    const col = Cesium.Color.fromCssColorString(cfg.color);

    _primitives.add({
      position:    Cesium.Cartesian3.fromDegrees(lon, lat),
      color:       col.withAlpha(0.92),
      pixelSize:   cfg.size,
      outlineColor: Cesium.Color.BLACK.withAlpha(0.6),
      outlineWidth: 1.5,
      scaleByDistance: new Cesium.NearFarScalar(1e4, 1.4, 8e6, 0.5),
      id: { type: 'history', properties: p, lon, lat },
    });

    // Labels visible when zoomed in
    const label = viewer.entities.add({
      position: Cesium.Cartesian3.fromDegrees(lon, lat, 500),
      label: {
        text: p.name,
        font: '11px Segoe UI',
        fillColor: Cesium.Color.fromCssColorString(cfg.color),
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 2,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        pixelOffset: new Cesium.Cartesian2(0, -cfg.size / 2 - 4),
        distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 500000),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
        scale: 0.85,
      }
    });
    _labels.push(label);
  }

  // Click handler for info popup
  _infoBox = viewer.screenSpaceEventHandler.setInputAction(e => {
    const picked = viewer.scene.pick(e.position);
    if (picked && picked.id && picked.id.type === 'history') {
      showHistoryPopup(picked.id.properties, picked.id.lon, picked.id.lat);
    }
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

  buildLegend(features);
  updateHistBadge(features);
  console.log(`FALCON history: ${features.length} sites loaded`);
}

export function removeHistory(viewer) {
  if (_primitives) {
    viewer.scene.primitives.remove(_primitives);
    _primitives = null;
  }
  _labels.forEach(l => viewer.entities.remove(l));
  _labels = [];
  _loaded = false;

  // Remove click handler
  if (_infoBox !== null) {
    viewer.screenSpaceEventHandler.removeInputAction(Cesium.ScreenSpaceEventType.LEFT_CLICK);
    _infoBox = null;
  }

  const badge  = document.getElementById('hist-badge');
  const legend = document.getElementById('hist-legend');
  const popup  = document.getElementById('hist-popup');
  if (badge)  badge.style.display  = 'none';
  if (legend) legend.style.display = 'none';
  if (popup)  popup.style.display  = 'none';
}

function showHistoryPopup(p, lon, lat) {
  const popup = document.getElementById('hist-popup');
  if (!popup) return;
  const cfg = CAT[p.category] || CAT.gurdwara;
  popup.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px">
      <span style="font-size:10px;letter-spacing:2px;color:${cfg.color};text-transform:uppercase">${cfg.label}</span>
      <button onclick="document.getElementById('hist-popup').style.display='none'" style="background:none;border:none;color:#a09070;cursor:pointer;font-size:14px;padding:0;margin-left:8px">✕</button>
    </div>
    <div style="font-size:13px;font-weight:600;color:#e8e0d0;margin-bottom:2px">${p.name}</div>
    <div style="font-size:10px;color:#a09070;margin-bottom:6px">${p.location}</div>
    <div style="font-size:10px;color:#c8c0b0;line-height:1.5">${p.description}</div>
    <div style="font-size:9px;color:#706050;margin-top:6px">${lat.toFixed(3)}°N ${lon.toFixed(3)}°E</div>
  `;
  popup.style.display = 'block';
}

function buildLegend(features) {
  const legend = document.getElementById('hist-legend');
  if (!legend) return;
  const presentCats = [...new Set(features.map(f => f.properties.category))];
  legend.innerHTML = `
    <div class="leg-title">SIKH HISTORICAL SITES</div>
    ${presentCats.map(c => {
      const cfg = CAT[c] || CAT.gurdwara;
      return `<div class="leg-row"><div class="leg-dot" style="background:${cfg.color};width:${Math.min(cfg.size,12)}px;height:${Math.min(cfg.size,12)}px"></div>${cfg.label}</div>`;
    }).join('')}
    <div style="font-size:8px;margin-top:4px;opacity:0.6">Click site for details</div>
  `;
  legend.style.display = 'flex';
}

function updateHistBadge(features) {
  const badge = document.getElementById('hist-badge');
  if (!badge) return;
  const shaheedi = features.filter(f => ['shaheedi','ghalughara','massacre'].includes(f.properties.category)).length;
  const takhts   = features.filter(f => f.properties.category === 'takht').length;
  badge.style.display = 'flex';
  badge.innerHTML = `<span style="font-size:13px">🏛️</span><span>${features.length} sites · ${takhts} Takhts · ${shaheedi} Shaheedi</span>`;
}
