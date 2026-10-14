"""AQI maths (India CPCB National AQI + US EPA categories), pollutant metadata and health guidance."""
import math

import pandas as pd

# ── Pollutant metadata ────────────────────────────────────────────────────────
# key = Open-Meteo variable name
POLLUTANTS = {
    "pm2_5": {
        "label": "PM2.5", "unit": "µg/m³", "avg_hours": 24, "who": 15, "naaqs": 60,
        "name": "Fine particulate matter (≤2.5 µm)",
        "sources": "Vehicle exhaust, crop-residue burning, industry, construction, firecrackers, wood/coal burning.",
        "effects": "Penetrates deep into lungs and the bloodstream. Linked to heart attacks, strokes, lung cancer, asthma and reduced life expectancy.",
    },
    "pm10": {
        "label": "PM10", "unit": "µg/m³", "avg_hours": 24, "who": 45, "naaqs": 100,
        "name": "Coarse particulate matter (≤10 µm)",
        "sources": "Road dust, construction sites, unpaved roads, desert dust storms, industrial emissions.",
        "effects": "Irritates nose, throat and airways. Aggravates asthma and bronchitis.",
    },
    "nitrogen_dioxide": {
        "label": "NO₂", "unit": "µg/m³", "avg_hours": 24, "who": 25, "naaqs": 80,
        "name": "Nitrogen dioxide",
        "sources": "Diesel & petrol vehicles, power plants, generators.",
        "effects": "Inflames airways, increases susceptibility to respiratory infections, worsens asthma in children.",
    },
    "ozone": {
        "label": "O₃", "unit": "µg/m³", "avg_hours": 8, "who": 100, "naaqs": 100,
        "name": "Ground-level ozone",
        "sources": "Formed when sunlight reacts with NOx and VOCs from vehicles and industry — peaks on sunny afternoons.",
        "effects": "Chest pain, coughing, throat irritation; reduces lung function, especially during exercise.",
    },
    "carbon_monoxide": {
        "label": "CO", "unit": "µg/m³", "avg_hours": 8, "who": 4000, "naaqs": 2000,
        "name": "Carbon monoxide",
        "sources": "Incomplete combustion — traffic congestion, biomass & charcoal burning.",
        "effects": "Reduces oxygen delivery to organs; headaches, dizziness; dangerous for people with heart disease.",
    },
    "sulphur_dioxide": {
        "label": "SO₂", "unit": "µg/m³", "avg_hours": 24, "who": 40, "naaqs": 80,
        "name": "Sulphur dioxide",
        "sources": "Coal-fired power plants, industrial boilers, diesel generators.",
        "effects": "Irritates eyes and airways, triggers asthma attacks; forms secondary particulate matter.",
    },
    "carbon_dioxide": {
        "label": "CO₂", "unit": "ppm", "avg_hours": None, "who": None, "naaqs": None,
        "name": "Carbon dioxide",
        "sources": "Fossil-fuel combustion — vehicles, power generation, industry.",
        "effects": "Not toxic at outdoor levels, but the main greenhouse gas driving climate change. Pre-industrial level was ~280 ppm.",
    },
    "dust": {
        "label": "Dust", "unit": "µg/m³", "avg_hours": None, "who": None, "naaqs": None,
        "name": "Mineral dust",
        "sources": "Wind-blown desert dust (Thar), construction and road dust.",
        "effects": "Contributes to PM10 levels; irritates eyes and respiratory tract.",
    },
}

# ── India CPCB National AQI breakpoints: (C_low, C_high, I_low, I_high) ──────
# CO is in mg/m³; everything else µg/m³. The top band is extended to cap at 500.
CPCB_BREAKPOINTS = {
    "pm2_5": [(0, 30, 0, 50), (30, 60, 50, 100), (60, 90, 100, 200), (90, 120, 200, 300), (120, 250, 300, 400), (250, 380, 400, 500)],
    "pm10": [(0, 50, 0, 50), (50, 100, 50, 100), (100, 250, 100, 200), (250, 350, 200, 300), (350, 430, 300, 400), (430, 600, 400, 500)],
    "nitrogen_dioxide": [(0, 40, 0, 50), (40, 80, 50, 100), (80, 180, 100, 200), (180, 280, 200, 300), (280, 400, 300, 400), (400, 800, 400, 500)],
    "ozone": [(0, 50, 0, 50), (50, 100, 50, 100), (100, 168, 100, 200), (168, 208, 200, 300), (208, 748, 300, 400), (748, 1000, 400, 500)],
    "carbon_monoxide": [(0, 1, 0, 50), (1, 2, 50, 100), (2, 10, 100, 200), (10, 17, 200, 300), (17, 34, 300, 400), (34, 50, 400, 500)],
    "sulphur_dioxide": [(0, 40, 0, 50), (40, 80, 50, 100), (80, 380, 100, 200), (380, 800, 200, 300), (800, 1600, 300, 400), (1600, 2400, 400, 500)],
}

# ── Categories ────────────────────────────────────────────────────────────────
CPCB_CATEGORIES = [
    # (upper bound, name, colour, emoji)
    (50, "Good", "#00b050", "😊"),
    (100, "Satisfactory", "#92d050", "🙂"),
    (200, "Moderate", "#f5c518", "😐"),
    (300, "Poor", "#ff8c00", "😷"),
    (400, "Very Poor", "#e5232b", "🤢"),
    (500, "Severe", "#8b1a1a", "☠️"),
]

US_CATEGORIES = [
    (50, "Good", "#00e400", "😊"),
    (100, "Moderate", "#f5d100", "🙂"),
    (150, "Unhealthy for Sensitive Groups", "#ff7e00", "😐"),
    (200, "Unhealthy", "#ff0000", "😷"),
    (300, "Very Unhealthy", "#8f3f97", "🤢"),
    (500, "Hazardous", "#7e0023", "☠️"),
]


def categories(standard: str):
    return CPCB_CATEGORIES if standard == "India (CPCB)" else US_CATEGORIES


def category(aqi, standard: str = "India (CPCB)"):
    """Return (name, colour, emoji, level_index) for an AQI value."""
    cats = categories(standard)
    if aqi is None or (isinstance(aqi, float) and math.isnan(aqi)):
        return ("No data", "#6b7280", "❔", -1)
    for i, (hi, name, col, emo) in enumerate(cats):
        if aqi <= hi:
            return (name, col, emo, i)
    hi, name, col, emo = cats[-1]
    return (name, col, emo, len(cats) - 1)


def sub_index(pollutant: str, conc):
    """CPCB sub-index for a concentration (µg/m³; CO converted to mg/m³ internally)."""
    if conc is None or pd.isna(conc) or pollutant not in CPCB_BREAKPOINTS:
        return None
    c = conc / 1000 if pollutant == "carbon_monoxide" else conc
    for c_lo, c_hi, i_lo, i_hi in CPCB_BREAKPOINTS[pollutant]:
        if c <= c_hi:
            return round(i_lo + (i_hi - i_lo) * (c - c_lo) / (c_hi - c_lo))
    return 500


def add_cpcb_aqi(df: pd.DataFrame) -> pd.DataFrame:
    """Add rolling-averaged CPCB sub-indices and the overall 'in_aqi' column to an hourly frame."""
    df = df.copy()
    sub_cols = []
    for p in CPCB_BREAKPOINTS:
        if p not in df:
            continue
        window = POLLUTANTS[p]["avg_hours"]
        avg = df[p].rolling(window, min_periods=max(1, window // 3)).mean()
        col = f"si_{p}"
        df[col] = avg.apply(lambda v, p=p: sub_index(p, v))
        sub_cols.append(col)
    if sub_cols:
        si = df[sub_cols].apply(pd.to_numeric, errors="coerce")
        df["in_aqi"] = si.max(axis=1)
        has = si.notna().any(axis=1)
        df["dominant"] = None
        if has.any():
            df.loc[has, "dominant"] = si[has].idxmax(axis=1).str.replace("si_", "", regex=False)
    return df


def cigarettes_per_day(pm25):
    """Berkeley Earth rule of thumb: 22 µg/m³ of PM2.5 for 24h ≈ smoking one cigarette."""
    if pm25 is None or pd.isna(pm25):
        return None
    return pm25 / 22.0


# ── Health guidance (by CPCB level 0..5) ─────────────────────────────────────
HEALTH = [
    {
        "impact": "Minimal impact. Air quality is excellent.",
        "general": ["Perfect day for outdoor activities 🏃", "Open windows to ventilate your home", "No mask needed"],
        "sensitive": ["Enjoy outdoor activities as usual"],
        "mask": "Not required", "outdoor": "Unrestricted", "purifier": "Off", "windows": "Open",
    },
    {
        "impact": "Minor breathing discomfort to sensitive people.",
        "general": ["Outdoor activities are fine", "Ventilate your home during the day"],
        "sensitive": ["Unusually sensitive people should watch for coughing or shortness of breath"],
        "mask": "Not required", "outdoor": "Unrestricted", "purifier": "Optional", "windows": "Open",
    },
    {
        "impact": "Breathing discomfort for people with lung disease (asthma), heart disease, children and older adults.",
        "general": ["Reduce prolonged or heavy outdoor exertion", "Prefer walking in parks away from traffic"],
        "sensitive": ["Limit outdoor exercise; keep reliever inhalers handy", "Children should take more breaks while playing outdoors"],
        "mask": "Recommended for sensitive groups", "outdoor": "Reduce heavy exertion", "purifier": "Recommended", "windows": "Close during peak traffic",
    },
    {
        "impact": "Breathing discomfort to most people on prolonged exposure.",
        "general": ["Avoid outdoor exercise — move workouts indoors", "Wear an N95 / FFP2 mask outdoors", "Keep windows closed; run an air purifier"],
        "sensitive": ["Stay indoors as much as possible", "Follow your asthma / COPD action plan", "Consult a doctor if symptoms worsen"],
        "mask": "N95 recommended", "outdoor": "Avoid exertion", "purifier": "On (high)", "windows": "Closed",
    },
    {
        "impact": "Respiratory illness on prolonged exposure. Effects are more pronounced in people with lung and heart disease.",
        "general": ["Avoid all outdoor physical activity", "Wear an N95/N99 mask whenever outside", "Run air purifiers continuously; seal gaps around doors/windows", "Avoid burning incense, candles or mosquito coils indoors"],
        "sensitive": ["Remain indoors with purified air", "Keep medicines ready; seek medical help for chest pain or breathlessness", "Pregnant women and the elderly should avoid going out"],
        "mask": "N95/N99 essential", "outdoor": "Avoid", "purifier": "On (max)", "windows": "Sealed",
    },
    {
        "impact": "HEALTH EMERGENCY — affects healthy people and seriously impacts those with existing diseases.",
        "general": ["Stay indoors; avoid all outdoor activity", "N99 mask mandatory if you must go outside", "Work from home if possible; schools may close under GRAP Stage IV", "Drink plenty of water; use saline nasal rinses"],
        "sensitive": ["Do not go outdoors", "Seek immediate medical care for breathing difficulty, chest pain, palpitations or dizziness"],
        "mask": "N99 mandatory", "outdoor": "Stay indoors", "purifier": "On (max) in every room", "windows": "Sealed",
    },
]

PERSONA_TIPS = {
    "General public": [],
    "Children": ["Children breathe faster and inhale more pollutants per kg of body weight — shift play indoors on Poor+ days.", "Choose child-size N95 masks with a proper fit."],
    "Elderly": ["Older adults have higher risk of heart attacks and strokes on high-pollution days — avoid morning walks when AQI is Poor or worse.", "Keep BP/heart medication schedules strict."],
    "Asthma / COPD": ["Carry your reliever inhaler at all times.", "Pollution spikes can trigger attacks 24–48 h later — monitor symptoms."],
    "Heart disease": ["PM2.5 raises the risk of cardiac events — avoid exertion outdoors.", "Seek urgent care for chest pain, breathlessness or palpitations."],
    "Pregnant": ["High PM2.5 exposure is linked to low birth weight and pre-term birth — minimise outdoor time on Poor+ days.", "Use an air purifier in the bedroom."],
    "Outdoor workers": ["Wear a well-fitted N95 during shifts; replace when breathing becomes harder.", "Take breaks in cleaner indoor spaces and stay hydrated."],
    "Athletes / runners": ["Exercise increases intake of pollutants up to 10×. Train indoors or in the cleanest hours (see forecast).", "Avoid running near busy roads."],
}

GRAP_STAGES = [
    ("Stage I", "Poor (201–300)", "#ff8c00", "Ban on open burning, strict dust control at construction sites, mechanised road sweeping, PUC enforcement."),
    ("Stage II", "Very Poor (301–400)", "#e5232b", "Diesel generator restrictions, higher parking fees to discourage private vehicles, more CNG/electric buses & metro frequency."),
    ("Stage III", "Severe (401–450)", "#8b1a1a", "Ban on non-essential construction & demolition, BS-III petrol / BS-IV diesel 4-wheelers restricted, hybrid classes for primary schools."),
    ("Stage IV", "Severe+ (>450)", "#4a0d0d", "Entry of non-essential trucks stopped, 50% work-from-home for offices, schools may shift online, all construction halted."),
]

CATEGORY_DESC = {
    # CPCB
    "Good": "Minimal impact. Enjoy the outdoors.",
    "Satisfactory": "Minor discomfort for very sensitive people.",
    "Moderate": "Discomfort for asthma, heart patients, kids & elderly.",
    "Poor": "Breathing discomfort for most on long exposure.",
    "Very Poor": "Respiratory illness on prolonged exposure.",
    "Severe": "Affects healthy people; serious for the sick.",
    # US EPA
    "Unhealthy for Sensitive Groups": "Sensitive groups should cut outdoor exertion.",
    "Unhealthy": "Everyone may begin to feel effects.",
    "Very Unhealthy": "Health alert — risk increased for all.",
    "Hazardous": "Emergency conditions for everyone.",
}
