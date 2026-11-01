"""
fetch_predictions.py — Compute prediction indexes from existing public data
NO API KEY REQUIRED — uses only data already fetched by other scripts.
Runs monthly (or on demand) via GitHub Actions.
Output:
  public/data/predictions.json      — current scores + projections
  public/data/history/predictions_timeseries.json
"""

import json, os, datetime, math

ROOT  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA  = os.path.join(ROOT, 'public', 'data')
HIST  = os.path.join(DATA, 'history')

TODAY = datetime.datetime.utcnow().strftime('%Y-%m-%d')
NOW   = datetime.datetime.utcnow().isoformat() + 'Z'
YEAR  = datetime.datetime.utcnow().year

def load_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return default or {}

# ═══════════════════════════════════════════════════════════════════════════════
# 1. GROUNDWATER COLLAPSE TIMELINE
# ═══════════════════════════════════════════════════════════════════════════════
# Source: CGWB published district data (pre-loaded in groundwater.geojson)
# Method: current depth + known depletion rate → years to critical threshold (50m)
# Critical: 50m = economic pump depth limit; >50m = agricultural unviability

DEPLETION_RATES = {
    # CGWB 2024 district-level annual decline rates (m/year)
    # Negative = declining, positive = recovering
    'Sangrur':    -1.35, 'Barnala':    -1.26, 'Ludhiana':  -1.08,
    'Bathinda':   -0.98, 'Mansa':      -0.92, 'Faridkot':  -0.87,
    'Muktsar':    -0.83, 'Fazilka':    -0.76, 'Ferozepur': -0.71,
    'Patiala':    -0.65, 'Moga':       -0.62, 'Kapurthala':-0.55,
    'Jalandhar':  -0.52, 'Amritsar':   -0.48, 'Tarn Taran':-0.44,
    'Hoshiarpur': -0.22, 'Nawanshahr': -0.18, 'Rupnagar':  -0.14,
    'Pathankot':  -0.08, 'Gurdaspur':  -0.06, 'SAS Nagar': -0.55,
    'Fatehgarh Sahib': -0.70,
}

DISTRICT_CURRENT_DEPTH = {
    # CGWB 2024 average pre-monsoon depth (mbgl)
    'Sangrur': 12.5, 'Barnala': 11.8, 'Ludhiana': 10.2,
    'Bathinda': 9.5, 'Mansa': 8.7, 'Faridkot': 8.2,
    'Muktsar': 9.1, 'Fazilka': 8.6, 'Ferozepur': 8.0,
    'Patiala': 10.8, 'Moga': 9.3, 'Kapurthala': 7.5,
    'Jalandhar': 8.9, 'Amritsar': 7.2, 'Tarn Taran': 7.8,
    'Hoshiarpur': 6.5, 'Nawanshahr': 6.2, 'Rupnagar': 5.8,
    'Pathankot': 5.1, 'Gurdaspur': 5.5, 'SAS Nagar': 9.0,
    'Fatehgarh Sahib': 10.5,
}

CRITICAL_DEPTH = 50.0  # metres below ground level

def compute_groundwater_timeline():
    districts = []
    for district, rate in DEPLETION_RATES.items():
        current = DISTRICT_CURRENT_DEPTH.get(district, 10.0)
        if rate >= 0:
            years = 999  # stable or recovering
        else:
            remaining = CRITICAL_DEPTH - current
            years = int(math.ceil(remaining / abs(rate)))
        target_year = YEAR + years if years < 999 else None
        districts.append({
            'district':    district,
            'depth_mbgl':  current,
            'rate_m_yr':   rate,
            'years_to_critical': years,
            'critical_year':     target_year,
            'risk': (
                'critical' if years <= 5 else
                'high'     if years <= 10 else
                'elevated' if years <= 20 else
                'moderate' if years <= 40 else
                'low'
            ),
        })
    districts.sort(key=lambda d: d['years_to_critical'])
    return districts

# ═══════════════════════════════════════════════════════════════════════════════
# 2. PUNJAB FISCAL DEBT TRAJECTORY
# ═══════════════════════════════════════════════════════════════════════════════
# Source: PRS India state finances (pre-baked known data)
# Punjab debt trajectory: ₹ lakh crore

DEBT_HISTORY = [
    {'year': 2014, 'debt_lc': 1.52},
    {'year': 2016, 'debt_lc': 1.79},
    {'year': 2018, 'debt_lc': 2.04},
    {'year': 2020, 'debt_lc': 2.29},
    {'year': 2022, 'debt_lc': 2.73},
    {'year': 2024, 'debt_lc': 3.27},
]
REVENUE_2024 = 1.08  # lakh crore (Punjab own + devolution + grants)
DEBT_SERVICE_RATE_2024 = 0.22  # 22% of revenue goes to debt service
CRISIS_THRESHOLD = 0.30  # 30% = fiscal emergency threshold

def compute_debt_trajectory():
    if len(DEBT_HISTORY) < 2:
        return {}
    # CAGR over last 4 periods
    n = len(DEBT_HISTORY)
    years_span = DEBT_HISTORY[-1]['year'] - DEBT_HISTORY[0]['year']
    cagr = (DEBT_HISTORY[-1]['debt_lc'] / DEBT_HISTORY[0]['debt_lc']) ** (1 / years_span) - 1

    projections = []
    for yr in range(YEAR, YEAR + 15):
        years_ahead = yr - DEBT_HISTORY[-1]['year']
        proj_debt = DEBT_HISTORY[-1]['debt_lc'] * ((1 + cagr) ** years_ahead)
        # Revenue grows slower than debt
        proj_rev  = REVENUE_2024 * (1.07 ** years_ahead)
        proj_ds_pct = (proj_debt * 0.075) / proj_rev  # ~7.5% interest + repayment
        projections.append({
            'year': yr,
            'debt_lc': round(proj_debt, 2),
            'revenue_lc': round(proj_rev, 2),
            'debt_service_pct': round(proj_ds_pct * 100, 1),
            'crisis_level': proj_ds_pct >= CRISIS_THRESHOLD,
        })

    crisis_year = next((p['year'] for p in projections if p['crisis_level']), None)
    return {
        'current_debt_lc':       DEBT_HISTORY[-1]['debt_lc'],
        'debt_cagr_pct':         round(cagr * 100, 1),
        'crisis_threshold_pct':  30,
        'estimated_crisis_year': crisis_year,
        'projections':           projections,
    }

# ═══════════════════════════════════════════════════════════════════════════════
# 3. FARMER PROTEST PROBABILITY SCORE
# ═══════════════════════════════════════════════════════════════════════════════
# Built from mandi prices vs MSP gap + calendar proximity to election
# Score 0-100; threshold 70 = high protest probability

def compute_protest_score():
    mandi = load_json(os.path.join(DATA, 'punjab_mandi.json'))
    features = mandi.get('features', [])

    # MSP 2024-25 (₹/quintal)
    MSP = {'wheat': 2275, 'paddy': 2320, 'cotton': 7020}

    # Mandi-MSP gap score (0-40 points)
    gap_scores = []
    for f in features:
        p = f.get('properties', {})
        prices = p.get('prices', {})
        for crop, msp in MSP.items():
            price = prices.get(crop)
            if price and price > 0:
                gap_pct = (price - msp) / msp * 100
                # negative gap = farmer distress
                score = max(0, min(40, -gap_pct * 4))
                gap_scores.append(score)
    msp_gap_score = round(sum(gap_scores) / len(gap_scores), 1) if gap_scores else 0

    # Seasonal score — stubble burning season (Oct-Nov) = higher tension (0-20 points)
    month = datetime.datetime.utcnow().month
    seasonal_score = 20 if month in [10, 11] else 15 if month in [9, 12, 4, 5] else 5

    # Election proximity score (Punjab state election Feb 2027) (0-20 points)
    next_election = datetime.date(2027, 2, 1)
    days_to_election = (next_election - datetime.date.today()).days
    election_score = max(0, 20 - int(days_to_election / 60))

    # Timeseries trend — are fires/protests increasing? (0-20 points)
    fires_ts = load_json(os.path.join(HIST, 'fires_timeseries.json'))
    records = fires_ts.get('records', [])[-14:]  # last 14 days
    fire_trend_score = 0
    if len(records) >= 7:
        first_half = sum(r['count'] for r in records[:7])
        second_half = sum(r['count'] for r in records[7:])
        if first_half > 0:
            pct_change = (second_half - first_half) / first_half * 100
            fire_trend_score = max(0, min(20, int(pct_change / 5)))

    total = msp_gap_score + seasonal_score + election_score + fire_trend_score
    total = min(100, total)

    return {
        'score': round(total, 1),
        'level': 'HIGH' if total >= 70 else 'ELEVATED' if total >= 50 else 'MODERATE' if total >= 30 else 'LOW',
        'components': {
            'msp_gap':    round(msp_gap_score, 1),
            'seasonal':   seasonal_score,
            'election':   election_score,
            'fire_trend': fire_trend_score,
        },
        'note': 'Score 0-100. Above 70 = high probability of farmer mobilisation.',
    }

# ═══════════════════════════════════════════════════════════════════════════════
# 4. MIGRATION PRESSURE INDEX
# ═══════════════════════════════════════════════════════════════════════════════
def compute_migration_pressure():
    cur = load_json(os.path.join(DATA, 'currencies.json'))
    rates = cur.get('rates', {})

    # CAD/INR weakening = less remittance value = reduced Canada pull
    cad = rates.get('CAD', {}).get('inr_per_unit', 61)
    cad_baseline = 62.5  # 2020 baseline
    cad_factor = max(0, min(30, int((cad_baseline - cad) / cad_baseline * 100 * 3)))

    # MSP gap → push factor (reuse protest score components)
    mandi = load_json(os.path.join(DATA, 'punjab_mandi.json'))
    below_msp = sum(1 for f in mandi.get('features', []) if f.get('properties', {}).get('below_msp', False))
    total_mandis = len(mandi.get('features', []))
    push_score = int(below_msp / max(total_mandis, 1) * 40)

    # Ground water stress → push (if Sangrur/Malwa critical, people leave)
    gw = load_json(os.path.join(DATA, 'punjab_groundwater.geojson'))
    critical_blocks = sum(
        1 for f in gw.get('features', [])
        if f.get('properties', {}).get('category') in ('over-exploited', 'critical')
    )
    gw_score = min(30, int(critical_blocks / 2))

    total = cad_factor + push_score + gw_score
    return {
        'score': min(100, total),
        'level': 'HIGH' if total >= 70 else 'ELEVATED' if total >= 45 else 'MODERATE' if total >= 25 else 'LOW',
        'components': {
            'cad_pull_weakening': cad_factor,
            'farm_distress_push': push_score,
            'groundwater_push':   gw_score,
        },
        'note': 'Higher score = greater emigration pressure from Punjab.',
    }

# ═══════════════════════════════════════════════════════════════════════════════
# 5. DOABA DISTRESS INDEX (composite)
# ═══════════════════════════════════════════════════════════════════════════════
def compute_doaba_distress():
    eurasian = load_json(os.path.join(DATA, 'eurasian_signals.json'))
    commodities = eurasian.get('commodities', {})
    cur_30d = eurasian.get('currency_30d', {})

    # Potash price spike → input cost pressure (0-30)
    potash = (commodities.get('potash') or {}).get('value')
    potash_score = 0
    if potash and potash > 400:
        potash_score = min(30, int((potash - 400) / 10))

    # CAD weakening → NRI investment slowing (0-35)
    cad_change = (cur_30d.get('CAD') or {}).get('change_30d_pct', 0) or 0
    cad_score = max(0, min(35, int(-cad_change * 5)))  # negative change = score rises

    # BDI spike → fertiliser import cost → farm input spike (0-35)
    bdi = eurasian.get('baltic_dry_index', {}).get('value')
    bdi_score = 0
    if bdi and bdi > 1500:
        bdi_score = min(35, int((bdi - 1500) / 50))

    total = potash_score + cad_score + bdi_score
    return {
        'score': min(100, total),
        'level': 'HIGH' if total >= 65 else 'ELEVATED' if total >= 40 else 'MODERATE' if total >= 20 else 'LOW',
        'components': {
            'potash_price_spike': potash_score,
            'cad_weakening':      cad_score,
            'bdi_spike':          bdi_score,
        },
        'note': 'Doaba-specific. NRI investment + farm input cost pressure.',
    }

# ═══════════════════════════════════════════════════════════════════════════════
# 6. SIKH DEMOGRAPHIC PROJECTION
# ═══════════════════════════════════════════════════════════════════════════════
CENSUS_DATA = [
    {'year': 2001, 'sikh_pct': 59.9},
    {'year': 2011, 'sikh_pct': 57.7},
    # 2021 census not yet released; projection based on trend
]

def compute_sikh_demographic():
    if len(CENSUS_DATA) < 2:
        return {}
    rate = (CENSUS_DATA[-1]['sikh_pct'] - CENSUS_DATA[0]['sikh_pct']) / \
           (CENSUS_DATA[-1]['year'] - CENSUS_DATA[0]['year'])  # pct pts/year

    projections = []
    for yr in range(2021, 2061, 5):
        pct = CENSUS_DATA[-1]['sikh_pct'] + rate * (yr - CENSUS_DATA[-1]['year'])
        projections.append({'year': yr, 'sikh_pct_projected': round(max(0, pct), 1)})

    minority_year = next(
        (p['year'] for p in projections if p['sikh_pct_projected'] < 50.0),
        None
    )
    return {
        'census_data':       CENSUS_DATA,
        'trend_per_decade':  round(rate * 10, 2),
        'projections':       projections,
        'minority_year':     minority_year,
        'note': '2021 census not yet released. Projection based on 2001→2011 trend.',
        'source':            'Census of India 2001, 2011',
    }

# ── Run all ───────────────────────────────────────────────────────────────────
print('=== FALCON Prediction Engine ===')

print('[1] Groundwater timeline...')
gw_timeline = compute_groundwater_timeline()
print(f'  Most critical: {gw_timeline[0]["district"]} ({gw_timeline[0]["years_to_critical"]} years)')

print('[2] Debt trajectory...')
debt = compute_debt_trajectory()
print(f'  Crisis year estimate: {debt.get("estimated_crisis_year")}')

print('[3] Farmer protest score...')
protest = compute_protest_score()
print(f'  Score: {protest["score"]} ({protest["level"]})')

print('[4] Migration pressure...')
migration = compute_migration_pressure()
print(f'  Score: {migration["score"]} ({migration["level"]})')

print('[5] Doaba distress index...')
doaba = compute_doaba_distress()
print(f'  Score: {doaba["score"]} ({doaba["level"]})')

print('[6] Sikh demographic...')
demographic = compute_sikh_demographic()
print(f'  Minority year projection: {demographic.get("minority_year")}')

# ═══════════════════════════════════════════════════════════════════════════════
# 7. GEOPOLITICAL PREDICTION INDEXES
# ═══════════════════════════════════════════════════════════════════════════════

def compute_india_pakistan_conflict():
    """
    India-Pakistan conflict probability (0-100).
    Based on: water treaty stress, ACLED-proxy events, Pakistani economic collapse risk,
    nuclear risk, historical pattern.
    """
    # Base from structural factors (static, update annually)
    base = 15  # baseline nuclear deterrence keeps this below 20
    eurasian = load_json(os.path.join(DATA, 'eurasian_signals.json'))
    geo = load_json(os.path.join(DATA, 'geopolitics.json'))

    # Pakistan economic collapse → desperate regimes take risks
    pak_score = 0
    if eurasian:
        pkr = ((eurasian.get('currency_30d') or {}).get('PKR') or {}).get('change_30d_pct')
        if pkr and pkr < -3:
            pak_score += 10  # PKR collapsing
        elif pkr and pkr < -1:
            pak_score += 5

    # Geo tone scores for india-pakistan topics
    tone_ip = (geo.get('geo_tone_scores') or {}).get('india_pakistan', None) if geo else None
    tone_score = 0
    if tone_ip is not None and tone_ip < -4:
        tone_score = 12
    elif tone_ip is not None and tone_ip < -2:
        tone_score = 6

    score = min(100, base + pak_score + tone_score)
    level = 'CRITICAL' if score >= 60 else 'HIGH' if score >= 40 else 'ELEVATED' if score >= 25 else 'LOW'
    return {
        'score': score, 'level': level,
        'components': {'structural_deterrence': base, 'pakistan_economic_stress': pak_score, 'diplomatic_tone': tone_score},
        'note': 'Nuclear deterrence maintains low baseline. Elevated by Pakistan economic fragility and water treaty stress.',
    }

def compute_india_alignment_index():
    """India global alignment score: 0=China/Russia bloc, 100=USA/West bloc."""
    signals = {
        'UN_abstain_Ukraine': 12, 'BRICS_membership': -15, 'SCO_membership': -10,
        'QUAD_membership': 20, 'Russia_oil_imports': -18, 'US_weapons_deals': 15,
        'Russia_S400': -12, 'France_Rafale': 10, 'Chabahar': 8,
        'CPEC_opposition': 10, 'NRI_Five_Eyes': 15,
    }
    raw = sum(signals.values())
    score = max(0, min(100, int((raw + 60) / 160 * 100)))
    label = 'Leaning West' if score > 55 else 'Genuinely Non-Aligned' if score > 35 else 'Leaning East'
    return {
        'score': score, 'label': label, 'signals': signals,
        'interpretation': 'India buys Russian oil, sits in BRICS/SCO, but also joins QUAD and buys Western weapons. Under increasing pressure to choose a bloc.',
        'punjab_impact': 'Non-alignment keeps both Five Eyes diaspora corridors and Russia/Gulf channels open. A forced choice closes one.',
    }

def compute_food_security_cascade():
    """
    Global food crisis risk → Punjab farmer income impact (0-100).
    Higher = worse for Punjab farmers (export bans cut income OR input costs spike).
    """
    eurasian = load_json(os.path.join(DATA, 'eurasian_signals.json'))
    base = 30
    wheat_score = 0
    if eurasian:
        wheat = ((eurasian.get('commodities') or {}).get('wheat') or {}).get('value')
        if wheat and wheat > 350:
            wheat_score = 20  # very high global wheat price
        elif wheat and wheat > 280:
            wheat_score = 10

    potash_score = 0
    potash = ((eurasian.get('commodities') or {}).get('potash') or {}).get('value') if eurasian else None
    if potash and potash > 450:
        potash_score = 15
    elif potash and potash > 320:
        potash_score = 8

    score = min(100, base + wheat_score + potash_score)
    level = 'CRITICAL' if score >= 70 else 'HIGH' if score >= 50 else 'ELEVATED' if score >= 35 else 'LOW'
    return {
        'score': score, 'level': level,
        'components': {'base_vulnerability': base, 'wheat_price_signal': wheat_score, 'fertiliser_cost_signal': potash_score},
        'note': 'Combines global wheat price (export opportunity) with fertiliser cost (input pressure). Punjab at centre of both.',
    }

def compute_diaspora_corridor_risk():
    """
    Risk to Punjab NRI remittance and immigration corridors (0-100).
    Monitors: Canada-India tension, UK immigration, CAD/GBP weakness.
    """
    eurasian = load_json(os.path.join(DATA, 'eurasian_signals.json'))
    base = 20
    cad_score = 0
    if eurasian:
        cad = ((eurasian.get('currency_30d') or {}).get('CAD') or {}).get('change_30d_pct')
        if cad and cad < -2:
            cad_score = 15
        elif cad and cad < -0.5:
            cad_score = 8

    # Canada-India tension — static assessment (update when geo tone available)
    canada_tension = 25  # HIGH — Nijjar case unresolved

    score = min(100, base + cad_score + canada_tension)
    level = 'HIGH' if score >= 55 else 'ELEVATED' if score >= 35 else 'MODERATE' if score >= 20 else 'LOW'
    return {
        'score': score, 'level': level,
        'components': {'base': base, 'cad_weakening': cad_score, 'canada_india_tension': canada_tension},
        'note': 'Doaba region most exposed. 770K Punjabis in Canada. Nijjar case unresolved. GBP/CAD weakness reduces remittance purchasing power.',
    }

def compute_technology_sovereignty():
    """
    Punjab/India technology sovereignty risk (0-100). Higher = more dependent on foreign tech.
    Tracks: semiconductor imports, AI policy gap, digital payment infrastructure.
    """
    # Static assessment from public data — update when live signals available
    score = 68
    level = 'HIGH'
    return {
        'score': score, 'level': level,
        'components': {'semiconductor_import_dependency': 35, 'ai_capability_gap': 20, 'digital_infra_foreign': 13},
        'note': 'India imports >90% semiconductors. No domestic fab at scale. AI: behind China and US by 3-5 years. UPI is domestic success. Punjab\'s future economy depends on India closing this gap.',
        'signals': ['TSMC fab not in India', 'India Semiconductor Mission: $10Bn pledged', 'NVIDIA AI partnership with India 2024', 'No large-scale GPU domestic production'],
    }

print('[7] Geopolitical indexes...')
ip_conflict     = compute_india_pakistan_conflict()
alignment       = compute_india_alignment_index()
food_cascade    = compute_food_security_cascade()
diaspora_risk   = compute_diaspora_corridor_risk()
tech_sovereignty= compute_technology_sovereignty()
print(f'  IP conflict: {ip_conflict["score"]} | Alignment: {alignment["score"]} | Food: {food_cascade["score"]} | Diaspora: {diaspora_risk["score"]} | Tech: {tech_sovereignty["score"]}')

# ── Save predictions.json ─────────────────────────────────────────────────────
predictions = {
    'generated':   NOW,
    'date':        TODAY,
    'groundwater': {'timeline': gw_timeline},
    'fiscal_debt': debt,
    'farmer_protest_probability': protest,
    'migration_pressure': migration,
    'doaba_distress_index': doaba,
    'sikh_demographic': demographic,
    'india_pakistan_conflict': ip_conflict,
    'india_alignment_index': alignment,
    'food_security_cascade': food_cascade,
    'diaspora_corridor_risk': diaspora_risk,
    'technology_sovereignty': tech_sovereignty,
}

path_p = os.path.join(DATA, 'predictions.json')
with open(path_p, 'w') as f:
    json.dump(predictions, f, separators=(',', ':'))
print(f'\nSaved predictions.json -> {path_p}')

# ── Append to predictions timeseries ─────────────────────────────────────────
ts_path = os.path.join(HIST, 'predictions_timeseries.json')
try:
    with open(ts_path) as f:
        ts = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    ts = {'records': []}

record = {
    'date':           TODAY,
    'protest_score':  protest['score'],
    'migration_score':migration['score'],
    'doaba_distress': doaba['score'],
    'debt_lc':        debt.get('current_debt_lc'),
}
ts['records'] = [r for r in ts['records'] if r['date'] != TODAY]
ts['records'].append(record)
ts['records'].sort(key=lambda r: r['date'])
ts['records'] = ts['records'][-1825:]

with open(ts_path, 'w') as f:
    json.dump(ts, f, separators=(',', ':'))
print(f'Timeseries: {len(ts["records"])} records')
