// FALCON — Engine II: NASA FIRMS fire layer with date timeline

const FIRE_DATA_URL = './public/data/punjab_fires.geojson?v=' + Date.now();

const CONF_COLOR = {
  h: Cesium.Color.fromCssColorString('#ff2200'),
  n: Cesium.Color.fromCssColorString('#ff7700'),
  l: Cesium.Color.fromCssColorString('#ffcc00'),
};

function frpToPixels(frp) {
  if (frp <= 0)  return 5;
  if (frp < 10)  return 7;
  if (frp < 50)  return 10;
  if (frp < 200) return 14;
  return 18;
}

let _viewer    = null;
let _features  = [];
let _primitives = null;
let _loaded    = false;
let _activeDate = null;   // null = all dates

export async function loadFires(viewer) {
  if (_loaded) return;
  _loaded = true;
  _viewer = viewer;

  let geojson;
  try {
    const res = await fetch(FIRE_DATA_URL);
    geojson = await res.json();
  } catch (e) {
    console.warn('FALCON fires: could not load data', e);
    updateBadge(0, null);
    return;
  }

  _features = geojson.features || [];
  const meta = geojson.metadata || {};

  if (_features.length === 0) {
    updateBadge(0, meta.generated);
    return;
  }

  buildTimeline();
  renderPoints(_features);
  updateBadge(_features.length, meta.generated);
  console.log(`FALCON fires: ${_features.length} hotspots loaded`);
}

function renderPoints(features) {
  if (_primitives) {
    _viewer.scene.primitives.remove(_primitives);
  }
  _primitives = _viewer.scene.primitives.add(new Cesium.PointPrimitiveCollection());

  for (const f of features) {
    const [lon, lat] = f.geometry.coordinates;
    const p    = f.properties;
    const conf = (p.confidence || 'n').toLowerCase()[0];
    const color = CONF_COLOR[conf] || CONF_COLOR.n;

    _primitives.add({
      position:   Cesium.Cartesian3.fromDegrees(lon, lat),
      color,
      pixelSize:  frpToPixels(p.frp),
      outlineColor: Cesium.Color.BLACK.withAlpha(0.4),
      outlineWidth: 1,
      translucencyByDistance: new Cesium.NearFarScalar(1e5, 1.0, 8e6, 0.4),
      scaleByDistance:        new Cesium.NearFarScalar(1e4, 2.0, 5e6, 0.5),
    });
  }
}

function buildTimeline() {
  const tl = document.getElementById('timeline');
  const daysDiv = document.getElementById('tl-days');
  const allBtn  = document.getElementById('tl-all');
  const label   = document.getElementById('tl-label');
  if (!tl) return;

  // Collect unique dates sorted ascending
  const dates = [...new Set(_features.map(f => f.properties.date))].sort();

  daysDiv.innerHTML = '';
  dates.forEach(d => {
    const count = _features.filter(f => f.properties.date === d).length;
    const btn = document.createElement('button');
    btn.className = 'tl-btn';
    btn.dataset.date = d;
    // Format: "30 Oct"
    const [y, m, day] = d.split('-');
    const mon = new Date(d).toLocaleDateString('en-GB', { month: 'short' });
    btn.textContent = `${parseInt(day)} ${mon}  (${count})`;
    btn.addEventListener('click', () => filterByDate(d, btn, label, allBtn));
    daysDiv.appendChild(btn);
  });

  allBtn.classList.add('active');
  allBtn.addEventListener('click', () => {
    _activeDate = null;
    renderPoints(_features);
    updateBadge(_features.length, null);
    label.textContent = 'ALL DATES';
    allBtn.classList.add('active');
    daysDiv.querySelectorAll('.tl-btn').forEach(b => b.classList.remove('active'));
  });

  tl.style.display = 'flex';
}

function filterByDate(date, btn, label, allBtn) {
  _activeDate = date;
  const filtered = _features.filter(f => f.properties.date === date);
  renderPoints(filtered);
  updateBadge(filtered.length, null);

  const [y, m, day] = date.split('-');
  const mon = new Date(date).toLocaleDateString('en-GB', { month: 'short' });
  label.textContent = `${parseInt(day)} ${mon} ${y}`;

  allBtn.classList.remove('active');
  document.querySelectorAll('.tl-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
}

export function removeFires(viewer) {
  if (_primitives) {
    viewer.scene.primitives.remove(_primitives);
    _primitives = null;
    _loaded = false;
  }
  const tl = document.getElementById('timeline');
  if (tl) tl.style.display = 'none';
  updateBadge(null, null);
}

function updateBadge(count, generated) {
  const badge = document.getElementById('fire-badge');
  if (!badge) return;
  if (count === null) { badge.style.display = 'none'; return; }

  const dateStr = generated
    ? new Date(generated).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })
    : '';

  badge.style.display = 'flex';
  badge.innerHTML = count === 0
    ? `<span class="fire-icon">🔥</span><span>No fires detected${dateStr ? ' · ' + dateStr : ''}</span>`
    : `<span class="fire-icon">🔥</span><span>${count} fire${count > 1 ? 's' : ''}${dateStr ? ' · ' + dateStr : ''}</span>`;
}
