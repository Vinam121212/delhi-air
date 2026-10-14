"""'Why is the air like this?' — rule-based attribution using NASA FIRMS fires, weather and pollutant fingerprints."""
import io
from datetime import date

import numpy as np
import pandas as pd
import requests
import streamlit as st

FIRMS = "https://firms.modaps.eosdis.nasa.gov/data/active_fire"
FIRMS_FEEDS = {  # public 24 h active-fire CSVs (no key needed)
    "south_asia": [f"{FIRMS}/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_South_Asia_24h.csv",
                   f"{FIRMS}/noaa-20-viirs-c2/csv/J1_VIIRS_C2_South_Asia_24h.csv"],
    "global": [f"{FIRMS}/modis-c6.1/csv/MODIS_C6_1_Global_24h.csv"],      # 1.5 MB, worldwide
}
FIRE_RADIUS_KM = 500
# Punjab + Haryana + western UP crop belt upwind of Delhi
FIRE_BOX = (27.5, 73.8, 32.6, 78.3)   # lat_min, lon_min, lat_max, lon_max
PUNJAB_BOX = (29.5, 73.8, 32.6, 76.9)
HARYANA_BOX = (27.6, 74.4, 30.9, 77.6)

DIWALI = [date(2024, 10, 31), date(2025, 10, 20), date(2026, 11, 8), date(2027, 10, 29), date(2028, 10, 17)]


def region_for(lat, lon):
    return "south_asia" if 5 <= lat <= 38 and 60 <= lon <= 98 else "global"


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_fires(region: str = "south_asia") -> pd.DataFrame:
    """All active fires in the last 24 h for a region (filter by distance in analyse())."""
    frames = []
    for url in FIRMS_FEEDS[region]:
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            frames.append(pd.read_csv(io.StringIO(r.text)))
        except Exception:
            continue
    if not frames:
        raise RuntimeError("NASA FIRMS fire data is unavailable right now")
    df = pd.concat(frames, ignore_index=True)
    if "confidence" in df:
        conf = df["confidence"].astype(str).str.lower()
        df = df[~conf.isin(["l", "low"]) & ~(pd.to_numeric(df["confidence"], errors="coerce") < 30)]
    return df[["latitude", "longitude", "frp", "acq_date", "acq_time"]].reset_index(drop=True)


def _in(df, box):
    lat1, lon1, lat2, lon2 = box
    return df[df.latitude.between(lat1, lat2) & df.longitude.between(lon1, lon2)]


def _dir_name(deg):
    names = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return names[int(((deg % 360) + 22.5) // 45) % 8]


def nearby_fires(fires: pd.DataFrame | None, lat: float, lon: float, radius_km: float = FIRE_RADIUS_KM):
    """Fires within radius, with distance and bearing (°, from the place toward the fire)."""
    if fires is None or fires.empty:
        return fires
    la, lo = np.radians(lat), np.radians(lon)
    fl, fo = np.radians(fires["latitude"].to_numpy()), np.radians(fires["longitude"].to_numpy())
    d = 2 * 6371 * np.arcsin(np.sqrt(np.sin((fl - la) / 2) ** 2 + np.cos(la) * np.cos(fl) * np.sin((fo - lo) / 2) ** 2))
    brg = (np.degrees(np.arctan2(np.sin(fo - lo) * np.cos(fl),
                                 np.cos(la) * np.sin(fl) - np.sin(la) * np.cos(fl) * np.cos(fo - lo))) + 360) % 360
    out = fires.assign(km=d, bearing=brg)
    return out[out["km"] <= radius_km].reset_index(drop=True)


def analyse(hourly: pd.DataFrame, now: pd.Timestamp, weather: dict, fires: pd.DataFrame | None,
            city: str = "Delhi NCR", north: bool = True, lat: float = 28.61, lon: float = 77.21, india: bool = True):
    """Return (factors, facts). factors: list of dicts {icon, title, score 0-1, text, evidence}."""
    past = hourly[hourly.index <= now]
    cur = past.iloc[-1]
    last12 = past.tail(12)
    wx = pd.DataFrame(weather.get("hourly", {})) if weather.get("hourly") else pd.DataFrame()
    if not wx.empty:
        wx["time"] = pd.to_datetime(wx["time"])
        wx = wx.set_index("time")
        wx12 = wx[(wx.index <= now) & (wx.index > now - pd.Timedelta(hours=12))]
    else:
        wx12 = wx
    wind = float(wx12["wind_speed_10m"].mean()) if "wind_speed_10m" in wx12 and not wx12.empty else np.nan
    wdir = float(np.degrees(np.arctan2(np.sin(np.radians(wx12["wind_direction_10m"])).mean(),
                                       np.cos(np.radians(wx12["wind_direction_10m"])).mean())) % 360) \
        if "wind_direction_10m" in wx12 and not wx12.empty else np.nan
    blh = float(wx12["boundary_layer_height"].min()) if "boundary_layer_height" in wx12 and not wx12.empty else np.nan
    rh = float(wx12["relative_humidity_2m"].mean()) if "relative_humidity_2m" in wx12 and not wx12.empty else np.nan
    pm25, pm10 = cur.get("pm2_5"), cur.get("pm10")
    no2, co, o3, dust = cur.get("nitrogen_dioxide"), cur.get("carbon_monoxide"), cur.get("ozone"), cur.get("dust")
    factors = []

    # 1. smoke from fires (crop-residue burning in north India; wildfires / agricultural burning elsewhere)
    near = nearby_fires(fires, lat, lon)
    n_fire = 0 if near is None else len(near)
    if near is not None and n_fire and not np.isnan(wdir):
        diff = np.abs((near["bearing"] - wdir + 180) % 360 - 180)        # fires lying in the direction the wind comes from
        upwind = int((diff <= 45).sum())
    else:
        upwind = 0
    s = min(1.0, upwind / 300 + n_fire / 4000)
    what = "crop-residue (stubble) fires in Punjab–Haryana" if north else "active fires (farm burning or wildfires)"
    factors.append({
        "icon": "🔥", "title": "Smoke from fires" if not north else "Crop-residue (stubble) burning", "score": s,
        "text": (f"Satellites detected <b>{n_fire:,}</b> {what} within {FIRE_RADIUS_KM} km in the last 24 h. "
                 + (f"<b>{upwind:,}</b> of them are upwind — the wind is blowing from the {_dir_name(wdir)}, carrying smoke toward {city}."
                    if upwind else "Few or none are upwind right now, so little smoke should reach you."))
        if fires is not None else "NASA fire data is unavailable right now.",
        "evidence": f"{n_fire:,} fires · {upwind:,} upwind · wind from {_dir_name(wdir) if not np.isnan(wdir) else '—'}"})

    # 2. stagnant air / inversion
    calm = 0 if np.isnan(wind) else max(0.0, min(1.0, (10 - wind) / 8))
    low = 0 if np.isnan(blh) else max(0.0, min(1.0, (900 - blh) / 700))
    s = 0.55 * calm + 0.45 * low
    factors.append({
        "icon": "🌫️", "title": "Still air & low mixing height", "score": s,
        "text": f"Average wind over the last 12 h was <b>{wind:.0f} km/h</b> and the mixing height dropped to "
                f"<b>{blh:,.0f} m</b>. " + ("Pollution is being trapped close to the ground like a lid on a pot."
                                            if s > .5 else "The air is mixing reasonably well."),
        "evidence": f"wind {wind:.0f} km/h · mixing {blh:,.0f} m"})

    # 3. traffic / combustion
    rush = last12[last12.index.hour.isin([8, 9, 10, 18, 19, 20, 21])]
    no2_r = (no2 or 0) / 40
    s = max(0.0, min(1.0, (no2_r - 0.6) / 1.6)) * 0.7 + max(0.0, min(1.0, ((co or 0) / 1000 - 0.6) / 1.4)) * 0.3
    factors.append({
        "icon": "🚗", "title": "Traffic & combustion", "score": s,
        "text": f"NO₂ is <b>{no2 or 0:.0f} µg/m³</b> and CO <b>{(co or 0) / 1000:.2f} mg/m³</b> — both mostly from vehicle "
                "exhaust and burning fuel. " + (f"Rush hours pushed NO₂ to {rush['nitrogen_dioxide'].max():.0f}."
                                                 if not rush.empty else ""),
        "evidence": f"NO₂ {no2 or 0:.0f} · CO {(co or 0) / 1000:.2f} mg/m³"})

    # 4. dust
    ratio = (pm10 or 0) / (pm25 or 1)
    s = max(0.0, min(1.0, ((dust or 0) - 30) / 150)) * 0.6 + max(0.0, min(1.0, (ratio - 1.8) / 1.5)) * 0.4
    factors.append({
        "icon": "🏜️", "title": "Dust (construction, roads, desert)", "score": s,
        "text": f"Mineral dust is <b>{dust or 0:.0f} µg/m³</b> and PM10 is <b>{ratio:.1f}×</b> PM2.5 — "
                + ("a coarse-particle signature typical of dust storms and construction."
                   if s > .4 else "dust isn't the main driver right now."),
        "evidence": f"dust {dust or 0:.0f} · PM10/PM2.5 {ratio:.1f}"})

    # 5. humidity → secondary aerosols / smog-fog
    s = 0 if np.isnan(rh) else max(0.0, min(1.0, (rh - 60) / 30)) * min(1.0, (pm25 or 0) / 120)
    factors.append({
        "icon": "💧", "title": "Humid air forming smog", "score": s,
        "text": f"Humidity averaged <b>{rh:.0f}%</b>. Moist air helps gases turn into extra fine particles and "
                "makes haze thicker." if not np.isnan(rh) else "No humidity data.",
        "evidence": f"humidity {rh:.0f}%" if not np.isnan(rh) else "—"})

    # 6. firecrackers
    today = now.date()
    near_d = [d for d in DIWALI if abs((today - d).days) <= 3] if india else []
    s = 1.0 if near_d else 0.0
    factors.append({
        "icon": "🎆", "title": "Festival firecrackers", "score": s,
        "text": (f"It's within 3 days of Diwali ({near_d[0]:%d %b}). Firecrackers can push PM2.5 up 5–10× overnight."
                 if near_d else (f"No major firecracker festival nearby (next Diwali: "
                                 f"{min((d for d in DIWALI if d >= today), default=DIWALI[-1]):%d %b %Y})." if india else
                                 "Fireworks (New Year, national holidays) cause short spikes — none expected today.")),
        "evidence": "Diwali window" if near_d else "—"})

    # 7. ozone / photochemistry
    s = max(0.0, min(1.0, ((o3 or 0) - 100) / 100))
    factors.append({
        "icon": "☀️", "title": "Sunlight-made ozone", "score": s,
        "text": f"Ozone is <b>{o3 or 0:.0f} µg/m³</b>. It forms when sunlight cooks traffic and industrial gases — "
                "highest on hot, sunny afternoons.",
        "evidence": f"O₃ {o3 or 0:.0f}"})

    factors.sort(key=lambda f: -f["score"])
    month = now.month
    if not india:
        m = month if lat >= 0 else (month + 6 - 1) % 12 + 1          # southern hemisphere: shift seasons
        season = ("Winter: cold, still air and home heating trap pollution near the ground." if m in (12, 1, 2) else
                  "Spring: warmer days mix the air better; pollen and dust can rise." if m in (3, 4, 5) else
                  "Summer: strong sun makes more ozone on hot afternoons; wildfire smoke is possible." if m in (6, 7, 8) else
                  "Autumn: cooler nights and calmer winds start to trap pollution again.")
        facts = {"fires": n_fire, "wind": wind, "wdir": wdir, "blh": blh, "rh": rh, "season": season, "near_fires": near}
        factors.sort(key=lambda f: -f["score"])
        return factors, facts
    season = (("Winter (Oct–Jan): cold, still nights trap pollution and stubble smoke arrives — north India's worst season."
               if north else "Winter (Oct–Jan): calmer winds let pollution build up, though sea breezes and milder nights "
                             "keep levels well below north India's.")
              if month in (10, 11, 12, 1) else
              "Pre-monsoon (Apr–Jun): hot, windy and dusty; ozone and dust dominate."
              if month in (4, 5, 6) else
              f"Monsoon (Jul–Sep): rain washes particles out — usually {city}'s cleanest air."
              if month in (7, 8, 9) else "Late winter / spring: conditions are improving as nights warm up.")
    facts = {"fires": n_fire, "wind": wind, "wdir": wdir, "blh": blh, "rh": rh, "season": season, "near_fires": near}
    return factors, facts
