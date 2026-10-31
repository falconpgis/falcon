// FALCON Phase 1 — Base globe + NASA FIRMS fire layer

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

const _loadStart = Date.now();
let _timerInterval = null;

function setLoadLabel(text) {
  const el = document.getElementById('load-label');
  if (el) el.textContent = text;
}

function setProgress(pct) {
  const bar = document.getElementById('progress-bar');
  const label = document.getElementById('load-pct');
  if (bar) bar.style.width = pct + '%';
  if (label) label.textContent = Math.round(pct) + '%';
}

function startTimer() {
  const el = document.getElementById('load-time');
  if (!el) return;
  _timerInterval = setInterval(() => {
    el.textContent = ((Date.now() - _loadStart) / 1000).toFixed(1) + 's';
  }, 100);
}

function stopTimer() {
  if (_timerInterval) { clearInterval(_timerInterval); _timerInterval = null; }
  const el = document.getElementById('load-time');
  if (el) el.textContent = ((Date.now() - _loadStart) / 1000).toFixed(1) + 's';
}

function hideLoading() {
  stopTimer();
  setProgress(100);
  setTimeout(() => {
    const el = document.getElementById('loading');
    if (el) {
      el.classList.add('fade-out');
      setTimeout(() => { el.style.display = 'none'; }, 650);
    }
  }, 300);
}

function initEngineButtons(viewer) {
  document.querySelectorAll('.eng-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.eng-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const eng = btn.dataset.engine;
      if (eng === '2') {
        // Engine II — Live: show fire layer + legend
        import('./layers/fires.js').then(m => {
          m.loadFires(viewer);
          document.getElementById('fire-legend').style.display = 'flex';
        });
        setStatus('Engine II · Live');
      } else {
        // Hide fire layer UI for other engines
        document.getElementById('fire-badge').style.display = 'none';
        document.getElementById('fire-legend').style.display = 'none';
        setStatus('Engine ' + eng + ' — coming soon');
        setTimeout(() => setStatus('Phase 1 · Live'), 2000);
      }
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
  startTimer();
  setProgress(10);
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

  setProgress(40);
  setLoadLabel('Loading imagery…');

  // OSM via UrlTemplateImageryProvider — synchronous, no initial network check
  viewer.imageryLayers.addImageryProvider(
    new Cesium.UrlTemplateImageryProvider({
      url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
      credit: new Cesium.Credit('© OpenStreetMap contributors', false),
      maximumLevel: 19,
    })
  );

  setProgress(65);
  setLoadLabel('Positioning over Punjab…');

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

  setProgress(85);
  setLoadLabel('Rendering first frame…');

  // Hide loading as soon as first frame renders, or after 3s max
  const removeListener = viewer.scene.postRender.addEventListener(() => {
    removeListener();
    hideLoading();
    setStatus('Phase 1 · Live');
  });
  setTimeout(() => {
    hideLoading();
    setStatus('Phase 1 · Live');
  }, 3000);

  initEngineButtons(viewer);
  updateCoords(viewer);

  // Auto-load Engine II (fires) on startup — it's the default active engine
  import('./layers/fires.js').then(m => {
    m.loadFires(viewer);
    document.getElementById('fire-legend').style.display = 'flex';
  });

  window.FALCON = { viewer, Cesium, PUNJAB };
}

if (typeof Cesium !== 'undefined') {
  init();
} else {
  window.addEventListener('load', init);
}
