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

let _primitives = null;
let _labels     = [];
let _loaded     = false;

export async function loadDiaspora(viewer) {
  if (_loaded) return;
  _loaded = true;

  let geojson, currencies;
  try {
    [geojson, currencies] = await Promise.all([
      fetch(DIASPORA_URL).then(r => r.json()),
      fetch(CURRENCIES_URL).then(r => r.json()).catch(() => null),
    ]);
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
  _labels = [];
  _loaded = false;

  const badge  = document.getElementById('diaspora-badge');
  const legend = document.getElementById('diaspora-legend');
  if (badge)  badge.style.display  = 'none';
  if (legend) legend.style.display = 'none';
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
