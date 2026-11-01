// FALCON Intelligence Feed — news headlines, GDELT scores, Eurasian signals

const GOLD  = '#f0a500';
const MUTED = '#8a7a60';
const TEXT  = '#e2d8c4';

function hexAlpha(hex, a) {
  if (!hex.startsWith('#')) return hex;
  const r = parseInt(hex.slice(1,3),16), g = parseInt(hex.slice(3,5),16), b = parseInt(hex.slice(5,7),16);
  return `rgba(${r},${g},${b},${a})`;
}

// Topic → display config
const TOPIC_META = {
  punjab_fires:    { label: '🔥 Fires',           color: '#ff7043' },
  punjab_farm:     { label: '🌾 Agriculture',      color: '#ffd600' },
  punjab_water:    { label: '💧 Water',            color: '#42a5f5' },
  punjab_drugs:    { label: '⚠ Drugs',             color: '#ab47bc' },
  sikh_diaspora:   { label: '🌍 Diaspora',          color: GOLD },
  pakistan_border: { label: '🚩 Border',            color: '#ef5350' },
  india_canada:    { label: '🍁 India-Canada',       color: '#ef5350' },
  ukraine_wheat:   { label: '🌾 Ukraine Wheat',      color: '#ffd600' },
  russia_eurasia:  { label: '⚡ Russia/Eurasia',     color: '#ff9800' },
  cpec_china:      { label: '🔗 CPEC/China',         color: '#ef5350' },
  iran_chabahar:   { label: '⚓ Iran/Chabahar',      color: '#42a5f5' },
  afghanistan:     { label: '💊 Afghanistan',        color: '#ab47bc' },
  balticdry:       { label: '🚢 Shipping/BDI',       color: '#42a5f5' },
  rss:             { label: '📰 News',               color: MUTED },
};

// ── Headline card ─────────────────────────────────────────────────────────────
function headlineCard(art) {
  const meta = TOPIC_META[art.topic] || TOPIC_META.rss;
  const col  = meta.color;
  const src  = art.source || art.domain || '';
  const url  = art.url || '#';
  return `<a class="news-card" href="${url}" target="_blank" rel="noopener"
      style="border-left:3px solid ${hexAlpha(col, 0.7)}">
    <div class="news-topic-chip" style="color:${col};background:${hexAlpha(col,0.1)}">${meta.label}</div>
    <div class="news-title">${art.title}</div>
    <div class="news-meta">${src} &nbsp;·&nbsp; ${art.date || ''}</div>
  </a>`;
}

// ── GDELT tone indicator ──────────────────────────────────────────────────────
function toneChip(key, score) {
  if (score == null) return '';
  const col   = score >= 2 ? '#5a9f5a' : score <= -2 ? '#f44336' : '#ff9800';
  const label = score >= 2 ? 'POSITIVE' : score <= -2 ? 'NEGATIVE' : 'MIXED';
  const labels = {
    punjab_overall:   'Punjab Overall',
    india_canada:     'India–Canada',
    ukraine_wheat:    'Ukraine Wheat',
    russia_energy:    'Russia Energy',
    pakistan_economy: 'Pakistan Economy',
  };
  return `<div class="tone-chip" style="border-color:${hexAlpha(col,0.4)}">
    <span class="tone-key">${labels[key] || key}</span>
    <span class="tone-score" style="color:${col}">${score > 0 ? '+' : ''}${score}</span>
    <span class="tone-label" style="color:${col}">${label}</span>
  </div>`;
}

// ── Eurasian signals quick summary ────────────────────────────────────────────
function buildEurasianSummary(signals) {
  if (!signals) return '';
  const com = signals.commodities || {};
  const bdi = signals.baltic_dry_index || {};
  const cur = signals.currency_30d || {};

  function signalRow(label, value, unit, color, note='') {
    return `<div class="eurasia-row">
      <span class="eurasia-label">${label}</span>
      <span class="eurasia-value" style="color:${color}">${value != null ? value + ' ' + unit : '—'}</span>
      ${note ? `<span class="eurasia-note">${note}</span>` : ''}
    </div>`;
  }

  const wheat  = com.wheat?.value;
  const potash = com.potash?.value;
  const crude  = com.crude?.value;
  const bdi_v  = bdi.value;

  const cad = cur.CAD?.latest;
  const gbp = cur.GBP?.latest;
  const cad_ch = cur.CAD?.change_30d_pct;
  const gbp_ch = cur.GBP?.change_30d_pct;

  const rows = [
    signalRow('Wheat (global)', wheat, 'USD/mt', wheat > 300 ? '#ff9800' : GOLD, 'World Bank'),
    signalRow('Potash (MOP)', potash, 'USD/mt', potash > 450 ? '#f44336' : '#5a9f5a', 'input cost pressure'),
    signalRow('Brent Crude', crude, 'USD/bbl', crude > 90 ? '#f44336' : GOLD, 'diesel → tubewells'),
    signalRow('Baltic Dry Index', bdi_v, '', bdi_v > 2000 ? '#ff9800' : GOLD, 'freight cost'),
    signalRow('CAD/INR', cad ? '₹' + cad : null, '', GOLD, cad_ch ? (cad_ch >= 0 ? '+' : '') + cad_ch + '% 30d' : ''),
    signalRow('GBP/INR', gbp ? '₹' + gbp : null, '', GOLD, gbp_ch ? (gbp_ch >= 0 ? '+' : '') + gbp_ch + '% 30d' : ''),
  ].join('');

  return `<div class="eurasia-table">${rows}</div>`;
}

// ── Main render ───────────────────────────────────────────────────────────────
export async function renderIntelligenceTab(pane) {
  if (!pane) return;
  pane.innerHTML = '<div style="padding:40px;text-align:center;color:#8a7a60;font-size:10px;letter-spacing:2px">LOADING INTELLIGENCE FEED…</div>';

  // Fetch in parallel
  let headlines = null, gdelt = null, eurasian = null;
  try {
    [headlines, gdelt, eurasian] = await Promise.all([
      fetch('./public/data/news/headlines.json?v='+Date.now()).then(r=>r.json()).catch(()=>null),
      fetch('./public/data/news/gdelt_scores.json?v='+Date.now()).then(r=>r.json()).catch(()=>null),
      fetch('./public/data/eurasian_signals.json?v='+Date.now()).then(r=>r.json()).catch(()=>null),
    ]);
  } catch(e) {}

  const articles  = headlines?.articles || [];
  const tone      = gdelt?.tone_scores || {};
  const generated = headlines?.generated?.slice(0,10) || 'not yet fetched';

  // Filter controls — active topics
  const TOPICS = [...new Set(articles.map(a => a.topic))];

  pane.innerHTML = `
    <div class="dash-row">
      <div class="dash-card" style="grid-column:1/-1">
        <div class="dash-card-title" style="display:flex;justify-content:space-between;align-items:center">
          <span>Eurasian Signal Dashboard</span>
          <span style="font-size:8px;color:#8a7a60">${eurasian?.date || '—'}</span>
        </div>
        <div id="eurasia-summary"></div>
      </div>
    </div>
    <div class="dash-row">
      <div class="dash-card" style="grid-column:1/-1">
        <div class="dash-card-title" style="display:flex;justify-content:space-between;align-items:center">
          <span>GDELT Sentiment Scores — Global Coverage</span>
          <span style="font-size:8px;color:#8a7a60">${generated}</span>
        </div>
        <div id="tone-scores" class="tone-grid"></div>
      </div>
    </div>
    <div class="dash-row">
      <div class="dash-card" style="grid-column:1/-1">
        <div class="news-filter-row" id="topic-filters"></div>
        <div class="dash-card-title" style="display:flex;justify-content:space-between;align-items:center;margin-top:8px">
          <span>Intelligence Headlines — <span id="news-count">${articles.length}</span> articles</span>
          <span style="font-size:8px;color:#8a7a60">GDELT + RSS aggregation</span>
        </div>
        <div id="news-feed"></div>
      </div>
    </div>
  `;

  // Eurasian signals
  const esEl = document.getElementById('eurasia-summary');
  if (esEl) esEl.innerHTML = eurasian ? buildEurasianSummary(eurasian) : '<p class="pred-empty">Run weekly pipeline for Eurasian signals</p>';

  // GDELT tone scores
  const tsEl = document.getElementById('tone-scores');
  if (tsEl) tsEl.innerHTML = Object.keys(tone).length
    ? Object.entries(tone).map(([k,v]) => toneChip(k, v)).join('')
    : '<p class="pred-empty" style="margin:0">Run daily pipeline for GDELT sentiment data</p>';

  // Topic filters
  const filterEl = document.getElementById('topic-filters');
  let activeTopics = new Set(TOPICS);

  function renderFeed() {
    const feed = document.getElementById('news-feed');
    if (!feed) return;
    const filtered = articles.filter(a => activeTopics.has(a.topic));
    document.getElementById('news-count').textContent = filtered.length;
    feed.innerHTML = filtered.length
      ? filtered.map(headlineCard).join('')
      : '<p class="pred-empty">No articles for selected topics</p>';
  }

  if (filterEl && TOPICS.length) {
    const allBtn = `<button class="news-filter-btn active" data-topic="__all" onclick="toggleNewsFilter('__all', this)">ALL</button>`;
    const topicBtns = TOPICS.map(t => {
      const m = TOPIC_META[t] || TOPIC_META.rss;
      return `<button class="news-filter-btn active" data-topic="${t}"
        style="border-color:${hexAlpha(m.color,0.4)};color:${m.color}"
        onclick="toggleNewsFilter('${t}', this)">${m.label}</button>`;
    }).join('');
    filterEl.innerHTML = allBtn + topicBtns;

    window.toggleNewsFilter = function(topic, btn) {
      if (topic === '__all') {
        activeTopics = new Set(TOPICS);
        filterEl.querySelectorAll('.news-filter-btn').forEach(b => b.classList.add('active'));
      } else {
        btn.classList.toggle('active');
        if (btn.classList.contains('active')) activeTopics.add(topic);
        else activeTopics.delete(topic);
        filterEl.querySelector('[data-topic="__all"]').classList.remove('active');
      }
      renderFeed();
    };
  }

  renderFeed();
}

// ── Mini news panel for intel sidebar ────────────────────────────────────────
export async function renderMiniNewsFeed(container, limit=5) {
  let headlines = null;
  try {
    const r = await fetch('./public/data/news/headlines.json?v='+Date.now());
    headlines = await r.json();
  } catch(e) {}

  const articles = (headlines?.articles || []).slice(0, limit);
  if (!articles.length) {
    container.innerHTML = '<div style="font-size:9px;color:#8a7a60;padding:8px 14px">News feed not yet available</div>';
    return;
  }

  container.innerHTML = articles.map(art => {
    const meta = TOPIC_META[art.topic] || TOPIC_META.rss;
    return `<a class="mini-news-item" href="${art.url}" target="_blank" rel="noopener">
      <div class="mini-news-topic" style="color:${meta.color}">${meta.label}</div>
      <div class="mini-news-title">${art.title.slice(0,70)}${art.title.length>70?'…':''}</div>
      <div class="mini-news-src">${art.source}</div>
    </a>`;
  }).join('');
}
