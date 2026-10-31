// FALCON — Engine V: Sikh Diaspora layer

const DIASPORA_URL = './public/data/sikh_diaspora.geojson?v=' + Date.now();
const CURRENCIES_URL = './public/data/currencies.json?v=' + Date.now();

const REGION_COLOR = {
  canada:      '#ff6f00',
  uk:          '#1565c0',
  usa:         '#b71c1c',
  gulf:        '#00897b',
  australia:   '#6a1b9a',
  italy:       '#2e7d32',
  new_zealand: '#4527a0',
  europe:      '#00838f',
  singapore:   '#c62828',
  malaysia:    '#558b2f',
  africa:      '#e65100',
};

let _primitives   = null;
let _labels       = [];
let _loaded       = false;
let _clickHandler = null;
let _currencies   = null;

export async function loadDiaspora(viewer) {
  if (_loaded) return;
  _loaded = true;

  let geojson, currencies;
  try {
    [geojson, currencies] = await Promise.all([
      fetch(DIASPORA_URL).then(r => r.json()),
      fetch(CURRENCIES_URL).then(r => r.json()).catch(() => null),
    ]);
    _currencies = currencies;
  } catch (e) {
    console.warn('FALCON diaspora: could not load data', e);
    return;
  }

  const features = geojson.features || [];
  if (!features.length) return;

  _primitives = viewer.scene.primitives.add(new Cesium.PointPrimitiveCollection());

  for (const f of features) {
    const [lon, lat] = f.geometry.coordinates;
    const p = f.properties;
    const color = Cesium.Color.fromCssColorString(REGION_COLOR[p.region] || '#f0a500');
    const size  = Math.min(8 + Math.sqrt(p.sikh_population) * 0.12, 38);

    _primitives.add({
      position:    Cesium.Cartesian3.fromDegrees(lon, lat),
      color:       color.withAlpha(0.85),
      pixelSize:   size,
      outlineColor: Cesium.Color.WHITE.withAlpha(0.3),
      outlineWidth: 1.5,
      scaleByDistance: new Cesium.NearFarScalar(1e4, 1.2, 2e7, 0.3),
      id: { type: 'diaspora', lon, lat, props: p },
    });

    const pop = p.sikh_population >= 100000
      ? (p.sikh_population / 1000).toFixed(0) + 'k'
      : p.sikh_population.toLocaleString();

    const label = viewer.entities.add({
      position: Cesium.Cartesian3.fromDegrees(lon, lat, 1000),
      label: {
        text: `${p.city}\n~${pop} Sikhs`,
        font: '11px Segoe UI',
        fillColor: color,
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 2,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        pixelOffset: new Cesium.Cartesian2(0, -size / 2 - 4),
        distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 8000000),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
        scale: 0.9,
      }
    });
    _labels.push(label);
  }

  if (!_clickHandler) {
    _clickHandler = viewer.screenSpaceEventHandler.setInputAction(e => {
      const picked = viewer.scene.pick(e.position);
      if (picked && picked.id && picked.id.type === 'diaspora') {
        showDiasporaPopup(picked.id.props, picked.id.lon, picked.id.lat, _currencies);
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
  }

  buildDiasporaLegend(features, currencies);
  updateDiasporaBadge(features);
  console.log(`FALCON diaspora: ${features.length} locations loaded`);
}

export function removeDiaspora(viewer) {
  if (_primitives) {
    viewer.scene.primitives.remove(_primitives);
    _primitives = null;
  }
  _labels.forEach(l => viewer.entities.remove(l));
  _labels     = [];
  _loaded     = false;
  _currencies = null;

  if (_clickHandler !== null) {
    viewer.screenSpaceEventHandler.removeInputAction(Cesium.ScreenSpaceEventType.LEFT_CLICK);
    _clickHandler = null;
  }

  const badge  = document.getElementById('diaspora-badge');
  const legend = document.getElementById('diaspora-legend');
  const popup  = document.getElementById('diaspora-popup');
  if (badge)  badge.style.display  = 'none';
  if (legend) legend.style.display = 'none';
  if (popup)  popup.style.display  = 'none';
}

function showDiasporaPopup(p, lon, lat, currencies) {
  const popup = document.getElementById('diaspora-popup');
  if (!popup) return;
  const col = REGION_COLOR[p.region] || '#f0a500';
  const pop = p.sikh_population >= 100000
    ? (p.sikh_population / 1000).toFixed(0) + ',000+'
    : p.sikh_population.toLocaleString();

  let currHTML = '';
  if (currencies && currencies.rates) {
    const regionCurrency = {
      canada:'CAD', uk:'GBP', usa:'USD', gulf:'AED',
      australia:'AUD', europe:'EUR', singapore:'SGD', malaysia:'MYR',
      new_zealand:'NZD', italy:'EUR',
    };
    const code = regionCurrency[p.region];
    const rate = code && currencies.rates[code];
    if (rate) {
      currHTML = `<span style="color:#a09070">Rate</span><span>1 ${code} = ₹${rate.inr_per_unit}</span>`;
    }
  }

  popup.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px">
      <span style="font-size:10px;letter-spacing:2px;color:${col};text-transform:uppercase">🌍 SIKH DIASPORA</span>
      <button onclick="document.getElementById('diaspora-popup').style.display='none'" style="background:none;border:none;color:#a09070;cursor:pointer;font-size:14px;padding:0;margin-left:8px">✕</button>
    </div>
    <div style="font-size:13px;font-weight:600;color:#e8e0d0;margin-bottom:2px">${p.city}</div>
    <div style="font-size:10px;color:#a09070;margin-bottom:8px">${p.country}</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px 12px;font-size:10px;color:#c8c0b0">
      <span style="color:#a09070">Sikh population</span><span style="color:${col};font-weight:600">~${pop}</span>
      <span style="color:#a09070">Region</span><span>${p.region}</span>
      ${currHTML}
      <span style="color:#a09070">Location</span><span>${lat.toFixed(2)}°N ${lon.toFixed(2)}°E</span>
    </div>
  `;
  popup.style.display = 'block';
}

function buildDiasporaLegend(features, currencies) {
  const legend = document.getElementById('diaspora-legend');
  if (!legend) return;

  const regions = [...new Set(features.map(f => f.properties.region))];
  const regionLabels = {
    canada:'Canada', uk:'United Kingdom', usa:'United States',
    gulf:'Gulf (UAE)', australia:'Australia', italy:'Italy',
    new_zealand:'New Zealand', europe:'Europe', singapore:'Singapore',
    malaysia:'Malaysia', africa:'Africa (Kenya)',
  };

  let currencyHTML = '';
  if (currencies && currencies.rates) {
    const r = currencies.rates;
    const pairs = [['CAD',r.CAD],['GBP',r.GBP],['USD',r.USD],['AED',r.AED]];
    currencyHTML = `
      <div style="border-top:1px solid rgba(240,165,0,0.15);margin-top:6px;padding-top:6px">
        <div style="font-size:8px;letter-spacing:2px;color:#f0a500;margin-bottom:4px">DIASPORA CURRENCIES vs INR</div>
        ${pairs.map(([code,info]) => info
          ? `<div style="display:flex;justify-content:space-between;gap:12px"><span>${code}</span><span style="color:#e8e0d0">₹${info.inr_per_unit}</span></div>`
          : '').join('')}
      </div>`;
  }

  legend.innerHTML = `
    <div class="leg-title">SIKH DIASPORA · GLOBAL</div>
    ${regions.map(r => `<div class="leg-row">
      <div class="leg-dot" style="background:${REGION_COLOR[r]||'#f0a500'}"></div>
      ${regionLabels[r]||r}
    </div>`).join('')}
    <div style="font-size:8px;margin-top:4px;opacity:0.6">Circle size ∝ population</div>
    ${currencyHTML}
  `;
  legend.style.display = 'flex';
}

function updateDiasporaBadge(features) {
  const badge = document.getElementById('diaspora-badge');
  if (!badge) return;
  const total = features.reduce((s, f) => s + f.properties.sikh_population, 0);
  const countries = new Set(features.map(f => f.properties.country)).size;
  badge.style.display = 'flex';
  badge.innerHTML = `<span style="font-size:13px">🌍</span><span>~${(total/1000).toFixed(0)}k Sikhs across ${countries} countries tracked</span>`;
}
