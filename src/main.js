// FALCON Phase 0 — Base globe, Punjab camera, no token required
// Uses OpenStreetMap imagery + ellipsoid terrain (no Cesium ion token needed)

const PUNJAB = {
  lon: 75.35,
  lat: 31.0,
  alt: 750000,          // ~750 km — full Punjab in view
  bounds: { west: 73.8, south: 29.5, east: 76.9, north: 32.5 },
};

function setStatus(text) {
  const el = document.getElementById('status-text');
  if (el) el.textContent = text;
}

function setLoadLabel(text) {
  const el = document.getElementById('load-label');
  if (el) el.textContent = text;
}

function hideLoading() {
  const el = document.getElementById('loading');
  if (el) {
    el.classList.add('fade-out');
    setTimeout(() => { el.style.display = 'none'; }, 650);
  }
}

function initEngineButtons(viewer) {
  document.querySelectorAll('.eng-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.eng-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      // Engine switching will be wired in later phases
      setStatus('Engine ' + btn.dataset.engine + ' — coming soon');
      setTimeout(() => setStatus('Phase 0 · Live'), 2000);
    });
  });
}

function updateCoords(viewer) {
  const coordEl = document.getElementById('coords');
  if (!coordEl) return;

  viewer.scene.canvas.addEventListener('mousemove', e => {
    const rect = viewer.scene.canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const ray = viewer.camera.getPickRay(new Cesium.Cartesian2(x, y));
    if (!ray) return;
    const pos = viewer.scene.globe.pick(ray, viewer.scene);
    if (!pos) return;
    const carto = Cesium.Cartographic.fromCartesian(pos);
    const lat = Cesium.Math.toDegrees(carto.latitude).toFixed(3);
    const lon = Cesium.Math.toDegrees(carto.longitude).toFixed(3);
    coordEl.textContent = `ਪੰਜਾਬ · ${lat}°N ${lon}°E`;
  });
}

function init() {
  setLoadLabel('Initialising CesiumJS…');

  // No Cesium ion token — use bundled Natural Earth II imagery (served from
  // same CDN as CesiumJS itself, no external tile requests needed).
  // In Cesium 1.117+ imageryProvider constructor option is deprecated;
  // use baseLayer with ImageryLayer.fromProviderAsync instead.
  Cesium.Ion.defaultAccessToken = '';

  // baseLayer constructor option is unreliable in 1.120 — add layer after init
  const viewer = new Cesium.Viewer('cesiumContainer', {
    baseLayer: false,
    terrainProvider: new Cesium.EllipsoidTerrainProvider(),
    animation: false,
    baseLayerPicker: false,
    fullscreenButton: false,
    geocoder: false,
    homeButton: false,
    infoBox: false,
    sceneModePicker: false,
    selectionIndicator: false,
    timeline: false,
    navigationHelpButton: false,
  });

  // OSM tiles — full zoom pyramid, sharp at Punjab district level
  viewer.imageryLayers.add(
    Cesium.ImageryLayer.fromProviderAsync(
      Cesium.OpenStreetMapImageryProvider.fromUrl('https://tile.openstreetmap.org/', {
        credit: new Cesium.Credit('© OpenStreetMap contributors', false),
      })
    )
  );

  // Dark space background
  viewer.scene.backgroundColor = Cesium.Color.fromCssColorString('#0a0a0f');
  viewer.scene.skyBox.show = false;
  viewer.scene.sun.show = true;
  viewer.scene.moon.show = false;
  viewer.scene.globe.enableLighting = false;

  setLoadLabel('Flying to Punjab…');

  // Fly to Punjab
  viewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(PUNJAB.lon, PUNJAB.lat, PUNJAB.alt),
    orientation: {
      heading: Cesium.Math.toRadians(0),
      pitch: Cesium.Math.toRadians(-50),
      roll: 0,
    },
    duration: 2.5,
    complete: () => {
      hideLoading();
      setStatus('Phase 0 · Live');
    },
  });

  initEngineButtons(viewer);
  updateCoords(viewer);

  // Expose globally for layer modules loaded in later phases
  window.FALCON = { viewer, Cesium, PUNJAB };
}

// Wait for Cesium to be available (loaded via CDN script tag)
if (typeof Cesium !== 'undefined') {
  init();
} else {
  window.addEventListener('load', init);
}
