// FALCON — Engine II: NASA FIRMS fire layer
// Loads public/data/punjab_fires.geojson and renders glowing hotspots

const FIRE_DATA_URL = './public/data/punjab_fires.geojson';

// Colour by confidence level
const CONF_COLOR = {
  h: Cesium.Color.fromCssColorString('#ff2200'),   // high — bright red
  n: Cesium.Color.fromCssColorString('#ff7700'),   // nominal — orange
  l: Cesium.Color.fromCssColorString('#ffcc00'),   // low — amber
};

// Scale point size by FRP (fire radiative power, MW)
function frpToPixels(frp) {
  if (frp <= 0)   return 5;
  if (frp < 10)   return 7;
  if (frp < 50)   return 10;
  if (frp < 200)  return 14;
  return 18;
}

let _primitives = null;   // PointPrimitiveCollection
let _loaded     = false;

export async function loadFires(viewer) {
  if (_loaded) return;
  _loaded = true;

  let geojson;
  try {
    const res = await fetch(FIRE_DATA_URL);
    geojson = await res.json();
  } catch (e) {
    console.warn('FALCON fires: could not load data', e);
    updateBadge(0, null);
    return;
  }

  const features = geojson.features || [];
  const meta     = geojson.metadata || {};

  if (features.length === 0) {
    updateBadge(0, meta.generated);
    return;
  }

  // Use PointPrimitiveCollection for performance
  _primitives = viewer.scene.primitives.add(
    new Cesium.PointPrimitiveCollection()
  );

  for (const f of features) {
    const [lon, lat] = f.geometry.coordinates;
    const p = f.properties;
    const conf  = (p.confidence || 'n').toLowerCase()[0];
    const color = CONF_COLOR[conf] || CONF_COLOR.n;

    _primitives.add({
      position:          Cesium.Cartesian3.fromDegrees(lon, lat),
      color:             color,
      pixelSize:         frpToPixels(p.frp),
      outlineColor:      Cesium.Color.BLACK.withAlpha(0.4),
      outlineWidth:      1,
      translucencyByDistance: new Cesium.NearFarScalar(1e5, 1.0, 8e6, 0.4),
      scaleByDistance:        new Cesium.NearFarScalar(1e4, 2.0, 5e6, 0.5),
    });
  }

  updateBadge(features.length, meta.generated);
  console.log(`FALCON fires: ${features.length} hotspots loaded`);
}

export function removeFires(viewer) {
  if (_primitives) {
    viewer.scene.primitives.remove(_primitives);
    _primitives = null;
    _loaded = false;
  }
  updateBadge(null, null);
}

function updateBadge(count, generated) {
  const badge = document.getElementById('fire-badge');
  if (!badge) return;

  if (count === null) {
    badge.style.display = 'none';
    return;
  }

  const dateStr = generated
    ? new Date(generated).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })
    : '';

  badge.style.display = 'flex';
  badge.innerHTML = count === 0
    ? `<span class="fire-icon">🔥</span><span>No fires detected · ${dateStr}</span>`
    : `<span class="fire-icon">🔥</span><span>${count} fire${count > 1 ? 's' : ''} · ${dateStr}</span>`;
}
