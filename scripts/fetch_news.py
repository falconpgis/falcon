"""
FALCON — News & Geopolitical Intelligence Aggregator
Fetches: GDELT 2.0 (free, no key), RSS feeds (free), Open news APIs (free)
Covers: Punjab local, Eurasian geopolitics, major power shifts, civilisational signals
"""
import json, os, re, hashlib, time
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen, Request
from urllib.parse import urlencode, quote
from urllib.error import URLError

BASE = os.path.join(os.path.dirname(__file__), '..', 'public', 'data')
NEWS_DIR = os.path.join(BASE, 'news')
HIST_DIR = os.path.join(BASE, 'history')
os.makedirs(NEWS_DIR, exist_ok=True)
os.makedirs(HIST_DIR, exist_ok=True)

TODAY = datetime.now(timezone.utc).strftime('%Y-%m-%d')
TS    = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
MAX_ARTICLES = 400  # total cap

def fetch_url(url, timeout=15):
    try:
        req = Request(url, headers={'User-Agent': 'FALCON-PGIS/1.0 (geospatial research)'})
        with urlopen(req, timeout=timeout) as r:
            return r.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"  WARN fetch {url[:60]}: {e}")
        return None

# ─────────────────────────────────────────────────────────────────────────────
# GDELT 2.0 Article API — completely free, global, indexed every 15 minutes
# Tone: negative = hostile, positive = cooperative
# ─────────────────────────────────────────────────────────────────────────────
GDELT_API = 'https://api.gdeltproject.org/api/v2/doc/doc'

# Priority geopolitical topics — this decade's major power shift signals
GDELT_QUERIES = {
    # Punjab local
    'punjab_fires':       '"punjab" "fire" OR "stubble burning" OR "parali"',
    'punjab_farm':        '"punjab" "farmer" OR "MSP" OR "wheat" OR "paddy" OR "kisan"',
    'punjab_water':       '"punjab" "groundwater" OR "water table" OR "aquifer" OR "tubewells"',
    'punjab_drugs':       '"punjab" "drugs" OR "narcotics" OR "heroin" OR "opium"',
    'punjab_economy':     '"punjab" "debt" OR "budget" OR "economy" OR "industry"',

    # Sikh diaspora
    'sikh_diaspora':      '"sikh" OR "punjabi diaspora" OR "gurdwara" OR "khalistan"',
    'india_canada':       '"india" "canada" diplomatic OR "punjab" OR "sikh" OR "khalistan"',
    'india_uk':           '"india" "UK" OR "britain" sikh OR "punjabi" OR "jatt" OR "Leicester"',

    # South Asia geopolitics
    'pakistan_border':    '"pakistan" "india" border OR "line of control" OR "wagah" OR "attari"',
    'pakistan_economy':   '"pakistan" "IMF" OR "debt" OR "default" OR "inflation" OR "rupee"',
    'pakistan_military':  '"pakistan" "army" OR "ISI" OR "coup" OR "military establishment"',
    'afghanistan_collapse':'"afghanistan" "Taliban" OR "opium" OR "refugee" OR "collapse"',
    'kashmir':            '"kashmir" conflict OR "article 370" OR "LOC" OR "militant"',

    # China / CPEC power shift
    'cpec_china':         '"CPEC" OR "belt and road" Pakistan OR "China Pakistan"',
    'china_india':        '"china" "india" "border" OR "LAC" OR "Ladakh" OR "Doklam"',
    'china_military':     '"china" "PLA" military OR "Taiwan" OR "South China Sea"',
    'china_economy':      '"china" "economy" GDP OR "slowdown" OR "yuan" OR "trade war"',

    # Russia / Eurasia
    'russia_ukraine':     '"russia" "ukraine" war OR "grain" OR "sanctions" OR "ceasefire"',
    'russia_energy':      '"russia" "gas" OR "pipeline" OR "Nord Stream" OR "energy" sanctions',
    'russia_india':       '"russia" "india" "S-400" OR "oil" OR "rupee" OR "trade"',
    'central_asia':       '"Kazakhstan" OR "Uzbekistan" OR "Kyrgyzstan" geopolitics OR "SCO"',

    # Iran / Gulf / Middle East
    'iran_chabahar':      '"iran" "chabahar" OR "india" "INSTC" OR "Iran corridor"',
    'iran_nuclear':       '"iran" "nuclear" OR "JCPOA" OR "uranium" OR "sanctions"',
    'gulf_states':        '"saudi arabia" OR "UAE" "India" OR "Pakistan" OR "diaspora"',
    'red_sea_shipping':   '"red sea" "Houthi" OR "shipping" OR "suez canal" disruption',

    # Agriculture / food security
    'ukraine_wheat':      '"ukraine" "wheat" OR "grain" export OR "food security"',
    'fertiliser_market':  '"potash" OR "urea" OR "DAP" price OR "fertiliser" market',
    'india_food':         '"india" "wheat" OR "rice" export ban OR "food inflation"',

    # Diaspora financial corridors
    'remittance_india':   '"india" "remittance" OR "NRI" investment OR "diaspora bonds"',
    'balticdry':          '"Baltic Dry Index" OR "shipping freight" OR "cargo rates"',

    # Technology / power shift
    'ai_geopolitics':     '"artificial intelligence" "china" OR "US" OR "india" regulation OR "military"',
    'semiconductor_war':  '"semiconductor" OR "chip war" "taiwan" OR "china" OR "TSMC"',
    'arctic_routes':      '"arctic" OR "northern sea route" Russia OR "climate" shipping',
    'scl_brics':          '"SCO" OR "BRICS" expansion OR "de-dollarisation" OR "multipolar"',
}

# Tone queries for geopolitical sentiment
GDELT_TONE_QUERIES = {
    'punjab_overall':    '"punjab"',
    'india_canada':      '"india" "canada"',
    'ukraine_wheat':     '"ukraine" "wheat"',
    'russia_energy':     '"russia" energy',
    'pakistan_economy':  '"pakistan" economy',
    'cpec_corridor':     '"CPEC"',
    'sikh_diaspora':     '"sikh diaspora"',
    'punjab_agriculture':'"punjab" farmer OR agriculture',
    'china_india':       '"china" "india"',
    'iran_chabahar':     '"chabahar"',
    'brics_expansion':   '"BRICS" expansion',
    'de_dollarisation':  '"de-dollarisation" OR "dollar hegemony"',
}

def gdelt_fetch(query, mode='artlist', maxrecords=30, timespan='7days'):
    params = {
        'query': query,
        'mode': mode,
        'maxrecords': maxrecords,
        'format': 'json',
        'timespan': timespan,
        'sort': 'datesort',
    }
    url = GDELT_API + '?' + urlencode(params)
    raw = fetch_url(url)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except:
        return None

def gdelt_tone(query):
    """Fetch average tone for a topic using GDELT timeline tone API."""
    params = {
        'query': query,
        'mode': 'tonechart',
        'format': 'json',
        'timespan': '7days',
    }
    url = GDELT_API + '?' + urlencode(params)
    raw = fetch_url(url)
    if not raw:
        return None
    try:
        data = json.loads(raw)
        tones = [item.get('tone', 0) for item in (data.get('timeline') or []) if item.get('tone') is not None]
        return round(sum(tones) / len(tones), 2) if tones else None
    except:
        return None

# ─────────────────────────────────────────────────────────────────────────────
# RSS feeds — expanded for geopolitics priority
# ─────────────────────────────────────────────────────────────────────────────
RSS_FEEDS = {
    # Punjab / India local
    'punjab_tribune':   ('Tribune India Punjab',     'https://www.tribuneindia.com/rss/feed.xml'),
    'ndtv_india':       ('NDTV India',               'https://feeds.feedburner.com/ndtvnews-india-news'),
    'the_wire':         ('The Wire India',            'https://thewire.in/rss'),
    'scroll_in':        ('Scroll.in India',          'https://scroll.in/rss'),

    # South Asia
    'dawn_pakistan':    ('Dawn Pakistan',             'https://www.dawn.com/feeds/home'),
    'thenews_pak':      ('The News Pakistan',         'https://www.thenews.com.pk/rss/1/1'),
    'bbc_southasia':    ('BBC South Asia',            'https://feeds.bbci.co.uk/news/world/south-asia/rss.xml'),

    # Global geopolitics
    'aljazeera_world':  ('Al Jazeera World',          'https://www.aljazeera.com/xml/rss/all.xml'),
    'reuters_world':    ('Reuters World',             'https://feeds.reuters.com/reuters/worldNews'),
    'reuters_commodities':('Reuters Commodities',    'https://feeds.reuters.com/reuters/businessNews'),
    'guardian_world':   ('Guardian World',            'https://www.theguardian.com/world/rss'),
    'ft_world':         ('Financial Times',           'https://www.ft.com/?format=rss'),

    # Eurasia / Russia / China
    'rferl_russia':     ('RFERL Russia',              'https://www.rferl.org/api/zrtqoutiqviy'),
    'scmp_china':       ('SCMP China',                'https://www.scmp.com/rss/91/feed'),
    'chinadaily':       ('China Daily',               'https://www.chinadaily.com.cn/rss/world_rss.xml'),

    # Sikh / Diaspora
    'sikh_pa':          ('Sikh PA',                   'https://www.sikhpa.com/feed/'),
    'akali_patrika':    ('Punjab Tribune UK',         'https://www.punjabtribuneuk.com/feed/'),
}

def parse_rss(xml_text, source_name, topic='rss'):
    articles = []
    items = re.findall(r'<item>(.*?)</item>', xml_text, re.DOTALL)
    for item in items[:12]:
        title = re.search(r'<title[^>]*><!\[CDATA\[(.*?)\]\]>|<title[^>]*>(.*?)</title>', item, re.DOTALL)
        link  = re.search(r'<link[^>]*>(.*?)</link>|<link[^>]*/>', item, re.DOTALL)
        pubdate = re.search(r'<pubDate[^>]*>(.*?)</pubDate>', item, re.DOTALL)
        if not title:
            continue
        t = (title.group(1) or title.group(2) or '').strip()
        t = re.sub(r'<[^>]+>', '', t)
        if len(t) < 15:
            continue
        l = ''
        if link:
            l = (link.group(1) or '').strip()
        d = ''
        if pubdate:
            d = pubdate.group(1).strip()[:10] if pubdate.group(1) else ''
        domain = re.search(r'https?://([^/]+)', l)
        articles.append({
            'topic': topic,
            'title': t,
            'source': source_name,
            'domain': domain.group(1) if domain else '',
            'url': l,
            'date': d or TODAY,
            'tone': None,
        })
    return articles

def classify_topic(title):
    """Simple keyword → topic classifier for RSS articles."""
    t = title.lower()
    if any(w in t for w in ['punjab fire','stubble','parali','hotspot']): return 'punjab_fires'
    if any(w in t for w in ['punjab farmer','kisan','msp','wheat harvest','paddy']): return 'punjab_farm'
    if any(w in t for w in ['groundwater','water table','aquifer','cgwb']): return 'punjab_water'
    if any(w in t for w in ['drugs','heroin','narcotic','opium','ndps']): return 'punjab_drugs'
    if any(w in t for w in ['sikh','gurdwara','punjabi diaspora','khalistan']): return 'sikh_diaspora'
    if any(w in t for w in ['india','canada']) and any(w in t for w in ['diplomatic','sikh','punjab']): return 'india_canada'
    if any(w in t for w in ['cpec','belt and road','china pakistan']): return 'cpec_china'
    if any(w in t for w in ['chabahar','instc','iran corridor']): return 'iran_chabahar'
    if any(w in t for w in ['russia','ukraine','war','sanctions']): return 'russia_ukraine'
    if any(w in t for w in ['wheat','grain','food security','export ban']): return 'ukraine_wheat'
    if any(w in t for w in ['potash','urea','dap','fertiliser','fertilizer']): return 'fertiliser_market'
    if any(w in t for w in ['bdi','baltic dry','freight','shipping rate']): return 'balticdry'
    if any(w in t for w in ['pakistan','imf','rupee','default']): return 'pakistan_economy'
    if any(w in t for w in ['afghanistan','taliban']): return 'afghanistan_collapse'
    if any(w in t for w in ['china','pla','taiwan','south china sea']): return 'china_military'
    if any(w in t for w in ['brics','sco','scl','multipolar','de-dollar']): return 'scl_brics'
    if any(w in t for w in ['kashmir','loc','article 370']): return 'kashmir'
    if any(w in t for w in ['remittance','nri','diaspora']): return 'remittance_india'
    if any(w in t for w in ['arctic','northern sea route']): return 'arctic_routes'
    return 'rss'

# ─────────────────────────────────────────────────────────────────────────────
# Main pipeline
# ─────────────────────────────────────────────────────────────────────────────
def main():
    all_articles = []
    seen_hashes  = set()

    def add(arts):
        for a in arts:
            h = hashlib.md5(a['title'][:80].lower().encode()).hexdigest()
            if h not in seen_hashes:
                seen_hashes.add(h)
                all_articles.append(a)

    # 1. GDELT article lists (priority topics)
    print("Fetching GDELT articles…")
    priority_topics = [
        'russia_ukraine', 'cpec_china', 'china_india', 'iran_chabahar',
        'pakistan_economy', 'ukraine_wheat', 'sikh_diaspora', 'india_canada',
        'punjab_farm', 'punjab_fires', 'scl_brics', 'afghanistan_collapse',
        'fertiliser_market', 'balticdry', 'russia_energy', 'india_canada',
        'red_sea_shipping', 'semiconductor_war', 'central_asia', 'gulf_states',
    ]
    for topic in priority_topics:
        if topic not in GDELT_QUERIES:
            continue
        print(f"  GDELT: {topic}")
        data = gdelt_fetch(GDELT_QUERIES[topic], maxrecords=25, timespan='3days')
        arts = data.get('articles', []) if data else []
        for a in arts[:20]:
            title = a.get('title', '').strip()
            if not title or len(title) < 15:
                continue
            dom = a.get('domain', '')
            url = a.get('url', '')
            add([{
                'topic': topic,
                'title': title,
                'source': a.get('sourcecountry', dom),
                'domain': dom,
                'url': url,
                'date': a.get('seendate', TODAY)[:10],
                'tone': a.get('tone'),
                'socialimage': a.get('socialimage', ''),
            }])
        time.sleep(0.5)  # polite rate limit

    # 2. Extended GDELT for remaining topics
    for topic, query in GDELT_QUERIES.items():
        if topic in priority_topics:
            continue
        print(f"  GDELT extra: {topic}")
        data = gdelt_fetch(query, maxrecords=15, timespan='7days')
        arts = data.get('articles', []) if data else []
        for a in arts[:12]:
            title = a.get('title', '').strip()
            if not title or len(title) < 15:
                continue
            add([{
                'topic': topic,
                'title': title,
                'source': a.get('domain', ''),
                'domain': a.get('domain', ''),
                'url': a.get('url', ''),
                'date': a.get('seendate', TODAY)[:10],
                'tone': a.get('tone'),
            }])
        time.sleep(0.3)

    # 3. RSS feeds
    print("Fetching RSS feeds…")
    for feed_key, (source_name, rss_url) in RSS_FEEDS.items():
        print(f"  RSS: {source_name}")
        raw = fetch_url(rss_url, timeout=10)
        if not raw:
            continue
        arts = parse_rss(raw, source_name)
        for a in arts:
            a['topic'] = classify_topic(a['title'])
        add(arts)
        time.sleep(0.2)

    # 4. GDELT tone scores
    print("Computing GDELT tone scores…")
    tone_scores = {}
    for key, query in GDELT_TONE_QUERIES.items():
        t = gdelt_tone(query)
        tone_scores[key] = t
        print(f"  tone {key}: {t}")
        time.sleep(0.3)

    # 5. Write outputs
    all_articles = all_articles[:MAX_ARTICLES]
    print(f"\nTotal articles collected: {len(all_articles)}")

    headlines_path = os.path.join(NEWS_DIR, 'headlines.json')
    with open(headlines_path, 'w', encoding='utf-8') as f:
        json.dump({
            'generated': TS,
            'date': TODAY,
            'source': 'GDELT 2.0 + RSS aggregation',
            'articles': all_articles,
        }, f, indent=2, ensure_ascii=False)

    gdelt_path = os.path.join(NEWS_DIR, 'gdelt_scores.json')
    with open(gdelt_path, 'w', encoding='utf-8') as f:
        json.dump({
            'generated': TS,
            'date': TODAY,
            'source': 'GDELT 2.0 tonechart API',
            'tone_scores': tone_scores,
        }, f, indent=2)

    # 6. Append to sentiment timeseries
    ts_path = os.path.join(HIST_DIR, 'news_sentiment.json')
    history = []
    if os.path.exists(ts_path):
        try:
            with open(ts_path) as f:
                history = json.load(f)
        except:
            history = []

    # Build topic counts
    topic_counts = {}
    for a in all_articles:
        topic_counts[a['topic']] = topic_counts.get(a['topic'], 0) + 1

    entry = {
        'date': TODAY,
        'tone_scores': tone_scores,
        'article_count': len(all_articles),
        'topic_breakdown': topic_counts,
    }
    history = [h for h in history if h.get('date') != TODAY]
    history.append(entry)
    history.sort(key=lambda x: x['date'])

    with open(ts_path, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2)

    print("Done.")

if __name__ == '__main__':
    main()
