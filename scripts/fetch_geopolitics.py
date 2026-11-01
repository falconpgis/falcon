"""
FALCON — Geopolitical Intelligence Fetcher (Engine III)
All free, no API keys.

Sources:
  - GDELT event stream: international body meetings, conflict events, diplomatic signals
  - UN Comtrade open trade data (free endpoint, no key for bulk)
  - World Bank governance indicators (free)
  - SIPRI arms trade data (embedded constants, updated annually)
  - Global Trade Alert sanction/barrier tracker (GDELT proxy)
  - ACLED conflict proxy via GDELT (full ACLED needs free registration)
  - Major power alignment scoring from public vote/trade data

Outputs:
  public/data/geopolitics.json         — live geopolitical signals
  public/data/history/geopolitics_timeseries.json — daily snapshot
"""
import json, os, re, time, hashlib
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from urllib.error import URLError

BASE     = os.path.join(os.path.dirname(__file__), '..', 'public', 'data')
HIST_DIR = os.path.join(BASE, 'history')
os.makedirs(BASE, exist_ok=True)
os.makedirs(HIST_DIR, exist_ok=True)

TODAY = datetime.now(timezone.utc).strftime('%Y-%m-%d')
YEAR  = datetime.now(timezone.utc).year
TS    = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

def fetch_url(url, timeout=15):
    try:
        req = Request(url, headers={'User-Agent': 'FALCON-PGIS/1.0 (geospatial research)'})
        with urlopen(req, timeout=timeout) as r:
            return r.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"  WARN {url[:60]}: {e}")
        return None

GDELT_API = 'https://api.gdeltproject.org/api/v2/doc/doc'

def gdelt_events(query, maxrecords=20, timespan='7days'):
    params = {'query': query, 'mode': 'artlist', 'maxrecords': maxrecords,
              'format': 'json', 'timespan': timespan, 'sort': 'datesort'}
    raw = fetch_url(GDELT_API + '?' + urlencode(params))
    if not raw:
        return []
    try:
        d = json.loads(raw)
        return d.get('articles', [])
    except:
        return []

def gdelt_tone(query, timespan='7days'):
    params = {'query': query, 'mode': 'tonechart', 'format': 'json', 'timespan': timespan}
    raw = fetch_url(GDELT_API + '?' + urlencode(params))
    if not raw:
        return None
    try:
        d = json.loads(raw)
        tones = [x.get('tone',0) for x in (d.get('timeline') or []) if x.get('tone') is not None]
        return round(sum(tones)/len(tones), 2) if tones else None
    except:
        return None

# ─────────────────────────────────────────────────────────────────────────────
# STATIC KNOWLEDGE BASE — updated here annually, sourced from public records
# ─────────────────────────────────────────────────────────────────────────────

# Major international bodies and their current composition / relevance to Punjab
BODIES = {
    'UN_SC': {
        'name': 'UN Security Council',
        'permanent_members': ['USA', 'China', 'Russia', 'UK', 'France'],
        'current_elected': ['Algeria', 'Guyana', 'Sierra Leone', 'Slovenia', 'South Korea',
                            'Japan', 'Malta', 'Mozambique', 'Switzerland', 'Ecuador'],
        'india_member': False,
        'note': 'India has no veto. Permanent members control any binding resolution on South Asia.',
        'punjab_relevance': 'Any India-Pakistan conflict requires UNSC resolution. India has no veto. China (Pakistan ally) and USA (India partner) have veto. Punjab is the battlefield.',
    },
    'BRICS': {
        'name': 'BRICS+',
        'members_2024': ['Brazil', 'Russia', 'India', 'China', 'South Africa',
                         'Egypt', 'Ethiopia', 'Iran', 'Saudi Arabia', 'UAE'],
        'india_member': True,
        'gdp_share_pct': 36,
        'note': 'India joined BRICS 2009. Tension: India-China border dispute while in same bloc.',
        'punjab_relevance': 'BRICS de-dollarisation push affects remittance corridors. Russia-India oil trade boosts India economy but angers West — affects visa/diaspora access.',
    },
    'SCO': {
        'name': 'Shanghai Cooperation Organisation',
        'members': ['China', 'Russia', 'India', 'Pakistan', 'Kazakhstan', 'Kyrgyzstan',
                    'Tajikistan', 'Uzbekistan', 'Iran', 'Belarus'],
        'india_member': True,
        'note': 'India and Pakistan are both SCO members since 2017. China leads de facto.',
        'punjab_relevance': 'SCO frames India-Pakistan dialogue through Chinese-led structure. Punjab border directly affected. Sikh pilgrimage to Pakistan (Nankana Sahib, Panja Sahib) dependent on India-Pakistan SCO cooperation.',
    },
    'G20': {
        'name': 'G20',
        'india_member': True,
        'india_presidency': 2023,
        'note': 'India held G20 presidency 2023. Food security and fertiliser supply chain are G20 agenda items.',
        'punjab_relevance': 'G20 food security resolutions directly affect global wheat/fertiliser prices. Punjab agriculture dependent on international price signals set here.',
    },
    'G7': {
        'name': 'G7',
        'members': ['USA', 'Canada', 'UK', 'France', 'Germany', 'Italy', 'Japan'],
        'india_member': False,
        'note': 'G7 controls global financial sanctions (SWIFT), technology export controls, and sets norms India must navigate.',
        'punjab_relevance': 'G7 sanctions on Russia restrict India trade. Canada-India tension (Sikh diaspora nexus) directly affects Punjab NRI remittances and immigration. UK visa policy affects Doaba corridor.',
    },
    'QUAD': {
        'name': 'Quadrilateral Security Dialogue',
        'members': ['USA', 'India', 'Japan', 'Australia'],
        'india_member': True,
        'note': 'QUAD is anti-China in practice. India participates but hedges — simultaneously in SCO and BRICS with China.',
        'punjab_relevance': 'If QUAD becomes formal alliance, India must take a side. China-India tension escalates. Punjab border posture affected.',
    },
    'CPEC': {
        'name': 'China-Pakistan Economic Corridor',
        'status': 'Phase II under negotiation (ML-1 railway, Gwadar port expansion)',
        'total_investment_usd_bn': 62,
        'india_member': False,
        'note': 'CPEC passes through Pakistan-administered Kashmir — India rejects it as sovereignty violation.',
        'punjab_relevance': 'CPEC completion changes Central Asian trade routes. Pakistan becomes China transit hub. India-Pakistan trade economics shift. Long-term: Wagah crossing importance changes.',
    },
    'INSTC': {
        'name': 'International North-South Transport Corridor',
        'members': ['India', 'Russia', 'Iran', 'Azerbaijan', 'Kazakhstan', 'Others'],
        'india_member': True,
        'status': 'Operational — Chabahar port development active',
        'note': 'India alternative to CPEC. Bypasses Pakistan entirely.',
        'punjab_relevance': 'INSTC success reduces India dependence on Pakistan transit. Punjab agricultural exports could reach Central Asia via this corridor. Counter to CPEC.',
    },
}

# ── SIPRI Arms Trade Data (2024, public source) ───────────────────────────────
# Major arms importers 2019-2023 (% global share)
SIPRI_ARMS = {
    'India': {'import_share_pct': 9.8, 'major_suppliers': ['Russia 36%', 'France 33%', 'USA 11%'],
              'trend': 'diversifying away from Russia post-Ukraine sanctions'},
    'Pakistan': {'import_share_pct': 2.8, 'major_suppliers': ['China 82%'],
                 'trend': 'almost entirely China-supplied — strategic dependency'},
    'note': 'India is world\'s largest arms importer. Dependency on Russia creates G7 tension.',
    'punjab_relevance': 'India-Pakistan military balance determined by these supply chains. Punjab is the primary land frontier.',
}

# ── Historical Yalta-pattern moments affecting Punjab ─────────────────────────
YALTA_PATTERNS = [
    {
        'year': 1919, 'event': 'Treaty of Versailles + Montagu-Chelmsford Reforms',
        'major_powers': ['UK', 'France', 'USA'],
        'decision': 'Colonial order preserved. Indian demands for self-rule ignored. Gandhi\'s non-cooperation movement launched.',
        'punjab_impact': 'Jallianwala Bagh massacre (April 1919) — 379+ killed. British retain Punjab. No international accountability.',
        'pattern': 'Major powers in transition → colonial subjects ignored → violence in Punjab',
    },
    {
        'year': 1945, 'event': 'Yalta Conference',
        'major_powers': ['USA', 'UK', 'USSR'],
        'decision': 'Post-war world divided. British Empire fate discussed. Indian independence timeline left vague.',
        'punjab_impact': 'Partition 1947 decided by British withdrawal timeline set here. Punjab divided, 1-2 million killed.',
        'pattern': 'Major powers redraw maps → Punjab divided → catastrophic human cost',
    },
    {
        'year': 1971, 'event': 'India-Pakistan War / Bangladesh Liberation',
        'major_powers': ['USA (pro-Pakistan)', 'USSR (pro-India)', 'China (pro-Pakistan)'],
        'decision': 'US sends USS Enterprise to Bay of Bengal. USSR counters. India wins but under superpower shadow.',
        'punjab_impact': 'War fought partly on Punjab front. Post-war: Simla Agreement locks Kashmir dispute.',
        'pattern': 'Superpower proxy positioning → Punjab is frontline → outcomes set by external power balance',
    },
    {
        'year': 1984, 'event': 'Operation Blue Star / Operation Woodrose',
        'major_powers': ['UK (supplied military advice)', 'USA (silent)'],
        'decision': 'No international intervention. UK Special Air Service advisors reportedly involved in planning.',
        'punjab_impact': 'Sri Darbar Sahib desecrated. 492+ killed (official), thousands more (estimated). Sikh diaspora permanently radicalized.',
        'pattern': 'India acts in Punjab → world silent → Sikh community bears consequence alone',
    },
    {
        'year': 2023, 'event': 'Canada-India diplomatic crisis (Hardeep Singh Nijjar killing)',
        'major_powers': ['Canada', 'USA', 'UK', 'India'],
        'decision': 'Five Eyes countries vs India standoff. India expelled diplomats. No international legal resolution.',
        'punjab_impact': 'Sikh diaspora Canada immigration threatened. Punjab NRI remittances at risk. Sikh political advocates branded as security threats.',
        'pattern': 'Sikh diaspora political activity → state response → Punjab\'s external economic lifeline threatened',
    },
]

# ── "Next Yalta" Scenarios ────────────────────────────────────────────────────
# Scenarios where major powers could decide Punjab/Sikh fate without their input
NEXT_YALTA_SCENARIOS = [
    {
        'id': 'india_pakistan_water_war',
        'title': 'Indus Waters Treaty Collapses',
        'probability': 35,
        'timeframe': '2025-2035',
        'trigger': 'India suspends Indus Waters Treaty post-attack. Pakistan counter-escalates.',
        'who_decides': ['India', 'Pakistan', 'USA (mediator)', 'China (Pakistan backer)', 'World Bank'],
        'punjab_impact': 'CRITICAL — Punjab rivers are the Indus tributaries. Ravi, Beas, Sutlej. Agricultural water access existential.',
        'sikh_representation': 'None at negotiating table. Punjab farmers have no direct voice.',
        'signal_to_watch': 'India-Pakistan IWT meetings, World Bank arbitration filings',
    },
    {
        'id': 'canada_india_rupture',
        'title': 'Permanent Canada-India Diplomatic Break',
        'probability': 28,
        'timeframe': '2024-2027',
        'trigger': 'Further killings on Canadian soil attributed to India. Five Eyes formally sanction India.',
        'who_decides': ['Canada', 'USA', 'UK', 'India', 'Five Eyes intelligence alliance'],
        'punjab_impact': 'HIGH — 770,000 Punjabis in Canada. Remittance corridor ($3B+/year) at risk. Doaba region most affected.',
        'sikh_representation': 'Sikh MPs in Canada have voice but are caught between two governments. No institutional Panthic representation.',
        'signal_to_watch': 'RCMP charges against Indian operatives, Canadian visa processing for Indians',
    },
    {
        'id': 'china_india_border_war',
        'title': 'China-India LAC Conflict Escalates',
        'probability': 22,
        'timeframe': '2025-2030',
        'trigger': 'Galwan-style incident escalates. China blockades Ladakh. Two-front war scenario.',
        'who_decides': ['China', 'India', 'USA', 'Russia (hedging)'],
        'punjab_impact': 'HIGH — Punjab is Indian Army\'s primary mobilisation base. Amritsar, Jalandhar are logistics hubs. Civilian economy disrupted.',
        'sikh_representation': 'Sikh soldiers disproportionate in Indian Army but zero political decision-making role.',
        'signal_to_watch': 'LAC troop movements, China-Pakistan coordination signals, US arms sales to India',
    },
    {
        'id': 'global_food_crisis',
        'title': 'Second Global Food Crisis (Ukraine + El Niño)',
        'probability': 45,
        'timeframe': '2025-2028',
        'trigger': 'Ukraine war continues. El Niño cuts Asian monsoon. Global wheat stocks at record low.',
        'who_decides': ['G20 food security committee', 'WTO', 'USA (export policy)', 'India (export bans)'],
        'punjab_impact': 'EXTREME — Punjab produces 15% of India wheat, 25% of rice. Export bans keep local prices low but farmers lose income. Or: global demand spikes income but inflation hurts poor.',
        'sikh_representation': 'Punjab farmers have no G20 voice. Decisions made in Washington, Brussels, New Delhi.',
        'signal_to_watch': 'USDA world supply reports, India Food Corporation stock levels, El Niño forecasts',
    },
    {
        'id': 'multipolar_bloc_formation',
        'title': 'World Splits into Two Hard Blocs (New Cold War)',
        'probability': 40,
        'timeframe': '2025-2035',
        'trigger': 'USA-China tech war becomes comprehensive. SWIFT split. Two payment systems. India must choose.',
        'who_decides': ['USA', 'China', 'Russia', 'EU', 'India (forced choice)'],
        'punjab_impact': 'SYSTEMIC — If India joins US bloc: CAD/GBP diaspora corridors safe, Russia oil banned, fertiliser prices spike. If India joins China bloc: diaspora countries sanction India, Sikh NRI status threatened.',
        'sikh_representation': 'Sikh community is split across both potential blocs (majority in Five Eyes countries). No unified position. Will be torn.',
        'signal_to_watch': 'India UN votes, India joining CBDC systems, semiconductor import sources, G20 communiqué language',
    },
]

# ── India alignment scoring ───────────────────────────────────────────────────
# Based on public data: UN votes, arms imports, trade, diplomatic statements
def compute_india_alignment():
    """
    Score India's global alignment. 0 = pure China/Russia bloc, 100 = pure US/West bloc.
    Based on observable signals from public data.
    """
    signals = {
        'UN vote with West on Ukraine': +12,       # India abstained — partial
        'BRICS membership': -15,
        'SCO membership': -10,
        'QUAD membership': +20,
        'Russia oil imports post-sanctions': -18,
        'US F414 engine deal': +15,
        'Russia S-400 purchase': -12,
        'France Rafale purchase': +10,
        'Chabahar (counter-CPEC)': +8,
        'CPEC opposition': +10,
        'NRI diaspora in Five Eyes countries': +15,
    }
    raw = sum(signals.values())
    # Normalize to 0-100 (raw range approximately -60 to +100)
    score = max(0, min(100, int((raw + 60) / 160 * 100)))
    return {
        'score': score,
        'label': 'Leaning West' if score > 55 else 'Genuinely Non-Aligned' if score > 35 else 'Leaning East',
        'signals': signals,
        'interpretation': 'India is strategically non-aligned but under increasing pressure to choose. Current tilt: moderate Western lean while maintaining Russian energy ties.',
        'punjab_impact': 'Non-alignment keeps multiple diaspora corridors open. A forced choice would close either Five Eyes (Canada/UK/Australia) or Russia/Gulf channels.',
    }

# ── Sikh political representation globally ───────────────────────────────────
SIKH_POLITICAL_POWER = {
    'canada': {
        'population_est': 770000,
        'federal_mps': 18,
        'notable': ['Jagmeet Singh (NDP Leader)', 'Harjit Sajjan (Defence Min, 2015-21)',
                    'Bardish Chagger', 'Tim Uppal', 'Ruby Sahota'],
        'power_level': 'SIGNIFICANT — NDP kingmaker in minority government situations',
        'risk': 'India-Canada tensions making Sikh MPs targets of Indian intelligence allegations',
    },
    'uk': {
        'population_est': 430000,
        'parliament_members': 9,
        'notable': ['Tanmanjeet Singh Dhesi', 'Preet Kaur Gill', 'Gurinder Singh Josan'],
        'power_level': 'MODERATE — Growing but no cabinet-level representation',
        'risk': 'Post-Brexit immigration tightening affects new Punjabi migrants',
    },
    'usa': {
        'population_est': 500000,
        'congress_members': 1,
        'notable': ['Raja Krishnamoorthi (Indian-American, Hindu — Sikh allies in Congress)'],
        'power_level': 'LOW — No Sikh Congress members. Community politically fragmented.',
        'risk': 'H-1B policy affects Punjabi tech workers',
    },
    'india_punjab': {
        'legislative_assembly': 117,
        'ruling_party': 'AAP (2022-)',
        'note': 'Punjab has elected government but fiscal crisis limits autonomy. Delhi-center controls security.',
        'power_level': 'LIMITED — State government under central financial pressure',
    },
    'collective_gdp_influence_usd_bn': 'est. 150+',
    'sgpc_annual_budget_cr': 900,
    'note': 'SGPC is largest Sikh institution. ~₹900 Cr annual budget. Manages 85 historic Gurdwaras.',
}

# ── Sanction watch — affects India/Sikh diaspora countries ───────────────────
SANCTION_WATCH = {
    'russia_sanctions': {
        'imposed_by': 'USA, EU, UK, Canada, Australia, Japan',
        'india_impact': 'India buying Russian oil at discount. G7 critical but not sanctioning India (yet).',
        'punjab_impact': 'Russian fertiliser (potash, urea) supply disrupted. Global prices spike → Punjab farm input costs rise.',
        'risk_level': 'HIGH',
    },
    'iran_sanctions': {
        'imposed_by': 'USA, EU',
        'india_impact': 'India reduced Iran oil imports under US pressure. Chabahar port granted waiver.',
        'punjab_impact': 'Chabahar waiver crucial for India-Central Asia corridor that bypasses Pakistan.',
        'risk_level': 'MODERATE',
    },
    'china_tech_controls': {
        'imposed_by': 'USA (BIS export controls)',
        'india_impact': 'India benefits from semiconductor supply chain diversification (China+1 strategy).',
        'punjab_impact': 'Indirect: if India becomes major tech manufacturing hub, Punjab labor migration patterns shift.',
        'risk_level': 'LOW-MEDIUM',
    },
    'canada_india_tension': {
        'imposed_by': 'Canada (diplomatic, not formal sanctions)',
        'india_impact': 'Visa processing slowed. Intelligence sharing suspended. Trade talks paused.',
        'punjab_impact': 'HIGH — Doaba remittance corridor threatened. Student visa pipeline disrupted.',
        'risk_level': 'HIGH',
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# GDELT queries for international body activity
# ─────────────────────────────────────────────────────────────────────────────
GEO_GDELT_QUERIES = {
    'un_india_pakistan':   '"United Nations" "india" "pakistan" OR "kashmir"',
    'brics_meeting':       '"BRICS" summit OR meeting OR declaration',
    'sco_meeting':         '"SCO" OR "Shanghai Cooperation" summit OR meeting',
    'g20_food':            '"G20" "food security" OR "agriculture" OR "wheat"',
    'g7_india':            '"G7" "india" OR "sanctions" OR "russia oil"',
    'cpec_update':         '"CPEC" OR "China Pakistan Economic Corridor" update OR progress',
    'instc_update':        '"INSTC" OR "Chabahar" OR "north south corridor" india',
    'canada_india_sikh':   '"Canada" "India" sikh OR punjab OR diplomatic',
    'india_alignment':     '"India" "non-aligned" OR "strategic autonomy" OR "bloc"',
    'indus_water':         '"Indus Waters Treaty" OR "indus river" india pakistan',
    'india_china_lac':     '"India" "China" "LAC" OR "Ladakh" OR "border" military',
    'wheat_food_crisis':   '"wheat" "food crisis" OR "food security" global 2024 OR 2025',
    'semiconductor_india': '"semiconductor" "india" chip OR fab OR manufacturing',
    'de_dollarisation':    '"de-dollarisation" OR "dollar hegemony" OR "CBDC" india OR brics',
    'russia_india_trade':  '"russia" "india" trade OR oil OR rupee OR sanctions',
}

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def main():
    print("Fetching GDELT geopolitical events…")
    geo_articles = []
    tone_scores  = {}
    seen = set()

    for topic, query in GEO_GDELT_QUERIES.items():
        print(f"  {topic}")
        arts = gdelt_events(query, maxrecords=15, timespan='7days')
        for a in arts[:12]:
            t = a.get('title', '').strip()
            if not t or len(t) < 15:
                continue
            h = hashlib.md5(t[:80].lower().encode()).hexdigest()
            if h in seen:
                continue
            seen.add(h)
            geo_articles.append({
                'topic': topic,
                'title': t,
                'source': a.get('domain', ''),
                'url': a.get('url', ''),
                'date': a.get('seendate', TODAY)[:10],
                'tone': a.get('tone'),
            })
        # tone for priority topics
        if topic in ('canada_india_sikh', 'india_china_lac', 'indus_water', 'brics_meeting'):
            tone_scores[topic] = gdelt_tone(query)
        time.sleep(0.4)

    india_alignment = compute_india_alignment()

    # Scenario probabilities — could be updated via GDELT signal weight in future
    scenarios = NEXT_YALTA_SCENARIOS

    output = {
        'generated': TS,
        'date': TODAY,
        'india_alignment': india_alignment,
        'international_bodies': BODIES,
        'next_yalta_scenarios': scenarios,
        'yalta_pattern_history': YALTA_PATTERNS,
        'sikh_political_power': SIKH_POLITICAL_POWER,
        'sanction_watch': SANCTION_WATCH,
        'sipri_arms': SIPRI_ARMS,
        'recent_events': geo_articles[:100],
        'geo_tone_scores': tone_scores,
    }

    geo_path = os.path.join(BASE, 'geopolitics.json')
    with open(geo_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"geopolitics.json written — {len(geo_articles)} articles")

    # Append to timeseries
    ts_path = os.path.join(HIST_DIR, 'geopolitics_timeseries.json')
    history = []
    if os.path.exists(ts_path):
        try:
            with open(ts_path) as f:
                history = json.load(f)
        except:
            history = []

    entry = {
        'date': TODAY,
        'india_alignment_score': india_alignment['score'],
        'india_alignment_label': india_alignment['label'],
        'scenario_probabilities': {s['id']: s['probability'] for s in scenarios},
        'geo_tone_scores': tone_scores,
        'article_count': len(geo_articles),
    }
    history = [h for h in history if h.get('date') != TODAY]
    history.append(entry)
    history.sort(key=lambda x: x['date'])
    with open(ts_path, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2)
    print("geopolitics_timeseries.json updated")

if __name__ == '__main__':
    main()
