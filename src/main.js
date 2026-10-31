// FALCON Phase 0 — Base globe, Punjab camera, no token required

const PUNJAB = {
  lon: 75.35,
  lat: 31.0,
  alt: 750000,
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

function initEngineButtons() {
  document.querySelectorAll('.eng-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.eng-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
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
    const ray = viewer.camera.getPickRay(
      new Cesium.Cartesian2(e.clientX - rect.left, e.clientY - rect.top)
    );
    if (!ray) return;
    const pos = viewer.scene.globe.pick(ray, viewer.scene);
    if (!pos) return;
    const c = Cesium.Cartographic.fromCartesian(pos);
    coordEl.textContent = `ਪੰਜਾਬ · ${Cesium.Math.toDegrees(c.latitude).toFixed(3)}°N ${Cesium.Math.toDegrees(c.longitude).toFixed(3)}°E`;
  });
}

function init() {
  setLoadLabel('Initialising CesiumJS…');

  // No Cesium ion token needed — pure CDN + OSM
  Cesium.Ion.defaultAccessToken = '';

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

  // OSM tiles — full zoom pyramid
  viewer.imageryLayers.add(
    Cesium.ImageryLayer.fromProviderAsync(
      Cesium.OpenStreetMapImageryProvider.fromUrl('https://tile.openstreetmap.org/', {
        credit: new Cesium.Credit('© OpenStreetMap contributors', false),
      })
    )
  );

  viewer.scene.backgroundColor = Cesium.Color.fromCssColorString('#0a0a0f');
  viewer.scene.skyBox.show = false;
  viewer.scene.sun.show = true;
  viewer.scene.moon.show = false;
  viewer.scene.globe.enableLighting = false;

  // Set camera instantly — no fly animation that can hang
  viewer.camera.setView({
    destination: Cesium.Cartesian3.fromDegrees(PUNJAB.lon, PUNJAB.lat, PUNJAB.alt),
    orientation: {
      heading: Cesium.Math.toRadians(0),
      pitch: Cesium.Math.toRadians(-50),
      roll: 0,
    },
  });

  // Hide loading as soon as first frame renders, or after 3s max
  const removeListener = viewer.scene.postRender.addEventListener(() => {
    removeListener();
    hideLoading();
    setStatus('Phase 0 · Live');
  });
  setTimeout(() => {
    hideLoading();
    setStatus('Phase 0 · Live');
  }, 3000);

  initEngineButtons();
  updateCoords(viewer);

  window.FALCON = { viewer, Cesium, PUNJAB };
}

if (typeof Cesium !== 'undefined') {
  init();
} else {
  window.addEventListener('load', init);
}
