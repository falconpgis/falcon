// FALCON Phase 1 — Base globe + NASA FIRMS fire layer

const PUNJAB = {
  lon: 75.35,
  lat: 30.9,
  alt: 150000,
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
  let _gwModule = null;

  document.querySelectorAll('.eng-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.eng-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const eng = btn.dataset.engine;

      // Tear down all layers — always import cached module to call remove
      import('./layers/fires.js').then(m => m.removeFires(viewer));
      import('./layers/history.js').then(m => m.removeHistory(viewer));
      import('./layers/aqi.js').then(m => m.removeAQI(viewer));
      import('./layers/mandi.js').then(m => m.removeMandi(viewer));
      import('./layers/diaspora.js').then(m => m.removeDiaspora(viewer));
      import('./layers/prediction.js').then(m => m.removePrediction(viewer));
      import('./layers/geopolitical.js').then(m => m.removeGeopolitical(viewer));
      if (_gwModule) _gwModule.removeGroundwater(viewer);

      // Hide all layer UIs
      ['fire-badge','fire-legend','gw-badge','gw-legend','timeline',
       'hist-badge','hist-legend','hist-popup','aqi-badge','aqi-legend',
       'mandi-badge','mandi-legend','diaspora-badge','diaspora-legend',
       'prediction-badge','prediction-legend','pred-popup',
       'geo-badge','geo-legend','geo-popup',
       'fire-popup','gw-popup','diaspora-popup'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
      });

      if (eng === '1') {
        import('./layers/history.js').then(m => m.loadHistory(viewer));
        setStatus('Engine I · Sikh History');
      } else if (eng === '3') {
        import('./layers/geopolitical.js').then(m => m.loadGeopolitical(viewer));
        setStatus('Engine III · Geopolitical Intelligence');
      } else if (eng === '2') {
        import('./layers/fires.js').then(m => {
          m.loadFires(viewer);
          document.getElementById('fire-legend').style.display = 'flex';
          document.getElementById('timeline').style.display = 'flex';
        });
        import('./layers/aqi.js').then(m => m.loadAQI(viewer));
        import('./layers/mandi.js').then(m => m.loadMandi(viewer));
        setStatus('Engine II · Fire · AQI · Mandi');
      } else if (eng === '4') {
        import('./layers/groundwater.js').then(m => {
          _gwModule = m;
          m.loadGroundwater(viewer);
        });
        import('./layers/prediction.js').then(m => m.loadPrediction(viewer));
        setStatus('Engine IV · Groundwater + Distress Index');
      } else if (eng === '5') {
        import('./layers/diaspora.js').then(m => m.loadDiaspora(viewer));
        // Fly out to show global view
        viewer.camera.flyTo({
          destination: Cesium.Cartesian3.fromDegrees(30, 25, 18000000),
          orientation: { heading: 0, pitch: Cesium.Math.toRadians(-90), roll: 0 },
          duration: 2,
        });
        setStatus('Engine V · Sikh Diaspora');
      } else {
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

  // ESRI World Imagery — free satellite, no API key
  viewer.imageryLayers.addImageryProvider(
    new Cesium.UrlTemplateImageryProvider({
      url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      credit: new Cesium.Credit('Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics', false),
      maximumLevel: 19,
    })
  );

  // ESRI transparent labels — cities, towns, villages, roads
  viewer.imageryLayers.addImageryProvider(
    new Cesium.UrlTemplateImageryProvider({
      url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
      credit: new Cesium.Credit('', false),
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
      pitch: Cesium.Math.toRadians(-75),
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

  // Auto-load Engine II (fires + AQI + mandi) on startup — it's the default active engine
  import('./layers/fires.js').then(m => {
    m.loadFires(viewer);
    document.getElementById('fire-legend').style.display = 'flex';
    document.getElementById('timeline').style.display = 'flex';
  });
  import('./layers/aqi.js').then(m => m.loadAQI(viewer));
  import('./layers/mandi.js').then(m => m.loadMandi(viewer));

  window.FALCON = { viewer, Cesium, PUNJAB };
}

if (typeof Cesium !== 'undefined') {
  init();
} else {
  window.addEventListener('load', init);
}
