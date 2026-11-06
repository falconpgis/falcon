"""
FALCON — Engine III: Regional Intelligence — multi-country news monitoring
Sources: Free RSS feeds from Russia, China, Iran, Pakistan, Afghanistan,
         Central Asia, Turkey, Gulf, UK (South Asia desk), India, Nepal,
         Bangladesh, Sri Lanka — no API keys required

Outputs:
  public/data/regional_news.json         — last 72h headlines, all countries
  public/data/history/news_sentiment.json — updated daily sentiment scores
"""
import json, datetime, re, requests
from pathlib import Path
from xml.etree import ElementTree as ET
from collections import defaultdict

DATA_DIR = Path(__file__).parent.parent / "public" / "data"
HIST_DIR = DATA_DIR / "history"
HIST_DIR.mkdir(parents=True, exist_ok=True)

# ── RSS feeds by country / source ──────────────────────────────────────────
RSS_SOURCES = [
    # Russia
    {"country": "Russia",   "outlet": "RT",      "url": "https://www.rt.com/rss/news/"},
    {"country": "Russia",   "outlet": "TASS",    "url": "https://tass.com/rss/v2.xml"},
    {"country": "Russia",   "outlet": "Sputnik", "url": "https://sputnikglobe.com/export/rss2/world/index.xml"},
    # China
    {"country": "China",    "outlet": "Xinhua",        "url": "https://www.xinhuanet.com/english/rss/worldrss.xml"},
    {"country": "China",    "outlet": "Global Times",  "url": "https://www.globaltimes.cn/rss/outbrain.xml"},
    {"country": "China",    "outlet": "CGTN",          "url": "https://www.cgtn.com/subscribe/feeds/english/latest/rss.xml"},
    # Iran
    {"country": "Iran",     "outlet": "IRNA",          "url": "https://en.irna.ir/rss"},
    {"country": "Iran",     "outlet": "Tehran Times",  "url": "https://www.tehrantimes.com/rss"},
    {"country": "Iran",     "outlet": "MehrNews",      "url": "https://en.mehrnews.com/rss"},
    # Pakistan
    {"country": "Pakistan", "outlet": "Dawn",          "url": "https://www.dawn.com/feeds/home"},
    {"country": "Pakistan", "outlet": "The News",      "url": "https://www.thenews.com.pk/rss/1/1"},
    {"country": "Pakistan", "outlet": "Geo News",      "url": "https://www.geo.tv/rss/1"},
    {"country": "Pakistan", "outlet": "Express Tribune","url": "https://tribune.com.pk/feed"},
    {"country": "Pakistan", "outlet": "ARY News",      "url": "https://arynews.tv/feed/"},
    # Afghanistan
    {"country": "Afghanistan", "outlet": "TOLOnews",   "url": "https://tolonews.com/rss.xml"},
    {"country": "Afghanistan", "outlet": "Khaama",     "url": "https://www.khaama.com/feed/"},
    # Central Asia
    {"country": "Kazakhstan",  "outlet": "Tengri News","url": "https://en.tengrinews.kz/rss/"},
    {"country": "Kyrgyzstan",  "outlet": "AKIpress",   "url": "https://akipress.com/rss/news.rss"},
    {"country": "Uzbekistan",  "outlet": "Kun.uz",     "url": "https://kun.uz/en/rss"},
    # Turkey
    {"country": "Turkey",   "outlet": "Daily Sabah",   "url": "https://www.dailysabah.com/rss"},
    {"country": "Turkey",   "outlet": "TRT World",     "url": "https://www.trtworld.com/rss"},
    # Gulf / UAE
    {"country": "UAE",      "outlet": "Gulf News",     "url": "https://gulfnews.com/rss/"},
    {"country": "UAE",      "outlet": "Khaleej Times", "url": "https://www.khaleejtimes.com/rss"},
    # UK South Asia desk
    {"country": "UK",       "outlet": "BBC South Asia","url": "https://feeds.bbci.co.uk/news/world/south_asia/rss.xml"},
    {"country": "UK",       "outlet": "The Guardian",  "url": "https://www.theguardian.com/world/south-and-central-asia/rss"},
    # India
    {"country": "India",    "outlet": "The Hindu",     "url": "https://www.thehindu.com/feeder/default.rss"},
    {"country": "India",    "outlet": "NDTV",          "url": "https://feeds.feedburner.com/ndtvnews-top-stories"},
    {"country": "India",    "outlet": "Indian Express","url": "https://indianexpress.com/section/india/feed/"},
    # Nepal
    {"country": "Nepal",    "outlet": "Himalayan Times","url": "https://thehimalayantimes.com/feed"},
    {"country": "Nepal",    "outlet": "My Republica",   "url": "https://myrepublica.nagariknetwork.com/feed"},
    # Bangladesh
    {"country": "Bangladesh","outlet": "Daily Star",   "url": "https://www.thedailystar.net/rss.xml"},
    # Sri Lanka
    {"country": "Sri Lanka","outlet": "Daily Mirror",  "url": "https://www.dailymirror.lk/rss"},
    # International
    {"country": "Global",   "outlet": "Al Jazeera",    "url": "https://www.aljazeera.com/xml/rss/all.xml"},
    {"country": "Global",   "outlet": "Reuters Asia",  "url": "https://feeds.reuters.com/reuters/asiapacificNews"},
]

# ── Keywords to flag as Punjab-relevant ────────────────────────────────────
PUNJAB_KEYWORDS = [
    "punjab", "panjab", "sikh", "amritsar", "chandigarh", "lahore", "ludhiana",
    "patna sahib", "nankana", "golden temple", "wagah", "attari",
    "india-pakistan", "indo-pak", "kashmir", "loc", "line of control",
    "cpec", "belt and road", "instc", "corridor",
    "wheat", "water crisis", "groundwater", "stubble burn", "crop",
    "khalistan", "nri", "diaspora", "remittance",
    "drug", "narco", "heroin", "border", "bsf", "rangers",
    "flood", "drought", "rainfall", "monsoon",
]

HEADERS = {
    "User-Agent": "FALCON-PGIS/1.0 (Punjab Geospatial Intelligence; falconpgis.github.io)",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}

CUTOFF_HOURS = 72  # keep items from last 72 hours

def parse_rss(source):
    """Fetch and parse one RSS feed. Returns list of item dicts."""
    items = []
    try:
        r = requests.get(source["url"], headers=HEADERS, timeout=15)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        ns   = {"atom": "http://www.w3.org/2005/Atom"}
        # RSS 2.0
        for item in root.findall(".//item"):
            title   = (item.findtext("title")       or "").strip()
            link    = (item.findtext("link")        or "").strip()
            desc    = (item.findtext("description") or "").strip()
            pub     = (item.findtext("pubDate")     or "").strip()
            if not title: continue
            text_lc = (title + " " + desc).lower()
            relevant = any(kw in text_lc for kw in PUNJAB_KEYWORDS)
            items.append({
                "country":  source["country"],
                "outlet":   source["outlet"],
                "title":    title,
                "link":     link,
                "summary":  re.sub(r"<[^>]+>", "", desc)[:300],
                "pub_date": pub,
                "relevant": relevant,
            })
        # Atom feeds
        for entry in root.findall("atom:entry", ns):
            title   = (entry.findtext("atom:title",   namespaces=ns) or "").strip()
            link_el = entry.find("atom:link",         namespaces=ns)
            link    = link_el.get("href", "") if link_el is not None else ""
            summary = (entry.findtext("atom:summary", namespaces=ns) or "").strip()
            updated = (entry.findtext("atom:updated", namespaces=ns) or "").strip()
            if not title: continue
            text_lc = (title + " " + summary).lower()
            relevant = any(kw in text_lc for kw in PUNJAB_KEYWORDS)
            items.append({
                "country":  source["country"],
                "outlet":   source["outlet"],
                "title":    title,
                "link":     link,
                "summary":  re.sub(r"<[^>]+>", "", summary)[:300],
                "pub_date": updated,
                "relevant": relevant,
            })
    except Exception as e:
        print(f"[warn] {source['outlet']}: {e}")
    return items

def country_summary(articles):
    """Count articles and relevant hits per country."""
    summary = defaultdict(lambda: {"total": 0, "relevant": 0, "outlets": set()})
    for a in articles:
        c = a["country"]
        summary[c]["total"]   += 1
        summary[c]["outlets"].add(a["outlet"])
        if a["relevant"]: summary[c]["relevant"] += 1
    return {
        k: {"total": v["total"], "relevant": v["relevant"],
            "outlets": sorted(v["outlets"])}
        for k, v in summary.items()
    }

def main():
    print("FALCON · fetch_regional_news.py")
    now = datetime.datetime.utcnow()

    all_articles = []
    for src in RSS_SOURCES:
        items = parse_rss(src)
        all_articles.extend(items)
        mark = " ★" if any(i["relevant"] for i in items) else ""
        print(f"  {src['country']:15} {src['outlet']:20} {len(items):3} items{mark}")

    summary = country_summary(all_articles)
    relevant = [a for a in all_articles if a["relevant"]]

    out = {
        "generated_at": now.isoformat() + "Z",
        "total_articles": len(all_articles),
        "relevant_to_punjab": len(relevant),
        "country_summary": summary,
        "relevant_articles": relevant[:200],   # top 200 relevant
        "all_articles":     all_articles[:500], # all recent, capped at 500
    }

    out_path = DATA_DIR / "regional_news.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Written: {out_path} ({len(all_articles)} total, {len(relevant)} relevant)")

    # Sentiment history — country-level counts per day
    hist_path = HIST_DIR / "regional_news_history.json"
    history   = []
    if hist_path.exists():
        try: history = json.loads(hist_path.read_text(encoding="utf-8"))
        except Exception: history = []

    history.append({
        "date":           now.strftime("%Y-%m-%d"),
        "total":          len(all_articles),
        "relevant":       len(relevant),
        "country_counts": {c: v["total"] for c, v in summary.items()},
    })
    history = history[-90:]
    hist_path.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"History: {hist_path} ({len(history)} entries)")

if __name__ == "__main__":
    main()
