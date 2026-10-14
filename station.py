"""Turn a WAQI (aqicn.org) station feed into readings the dashboard can use.

WAQI publishes PM2.5/PM10 as US-EPA AQI sub-indices, so they're converted back to µg/m³ and then to India's CPCB AQI.
"""
import pandas as pd

from aqi import sub_index
from browser_js import haversine_km

# pre-2024 US EPA breakpoints (what aqicn.org uses): (C_lo, C_hi, I_lo, I_hi)
US_BP = {
    "pm25": [(0, 12, 0, 50), (12.1, 35.4, 51, 100), (35.5, 55.4, 101, 150), (55.5, 150.4, 151, 200),
             (150.5, 250.4, 201, 300), (250.5, 350.4, 301, 400), (350.5, 500.4, 401, 500)],
    "pm10": [(0, 54, 0, 50), (55, 154, 51, 100), (155, 254, 101, 150), (255, 354, 151, 200),
             (355, 424, 201, 300), (425, 504, 301, 400), (505, 604, 401, 500)],
}


def us_index_to_conc(pol, idx):
    if idx is None or pd.isna(idx):
        return None
    for c_lo, c_hi, i_lo, i_hi in US_BP[pol]:
        if idx <= i_hi:
            return c_lo + (c_hi - c_lo) * (idx - i_lo) / (i_hi - i_lo)
    return US_BP[pol][-1][1]


def parse_feed(feed: dict, lat: float, lon: float) -> dict | None:
    try:
        us = float(feed.get("aqi"))
    except (TypeError, ValueError):
        return None                                   # station offline ("-")
    iaqi = feed.get("iaqi", {})
    get = lambda k: iaqi.get(k, {}).get("v")
    pm25 = us_index_to_conc("pm25", get("pm25"))
    pm10 = us_index_to_conc("pm10", get("pm10"))
    subs = [s for s in (sub_index("pm2_5", pm25), sub_index("pm10", pm10)) if s is not None]
    geo = feed.get("city", {}).get("geo") or [lat, lon]
    name = feed.get("city", {}).get("name", "Nearest station")
    return {
        "name": name.split(",")[0].strip(), "full_name": name, "url": feed.get("city", {}).get("url", ""),
        "distance_km": haversine_km(lat, lon, float(geo[0]), float(geo[1])),
        "time": feed.get("time", {}).get("s", ""), "us_aqi": us, "in_aqi": max(subs) if subs else None,
        "pm2_5": pm25, "pm10": pm10, "dominant": feed.get("dominentpol"),
        "raw": {k: get(k) for k in ("pm25", "pm10", "no2", "o3", "so2", "co")},
    }


def us_index(pol, conc):
    """US-EPA sub-index for a PM concentration (µg/m³)."""
    if conc is None or pd.isna(conc):
        return None
    for c_lo, c_hi, i_lo, i_hi in US_BP[pol]:
        if conc <= c_hi:
            return i_lo + (i_hi - i_lo) * (max(conc, c_lo) - c_lo) / (c_hi - c_lo)
    return 500


def calibrate(hourly: pd.DataFrame, stn: dict | None, now: pd.Timestamp, tau_h: float = 18.0):
    """Scale the model's PM2.5/PM10 so 'now' matches the live station, fading the correction out over ~a day
    in both directions, then recompute both AQIs. Returns (frame, info) — info is None if nothing changed."""
    import numpy as np
    from aqi import add_cpcb_aqi
    if not stn:
        return hourly, None
    cur = hourly[hourly.index <= now].iloc[-1]
    ratios = {}
    for col in ("pm2_5", "pm10"):
        s_val, m_val = stn.get(col), cur.get(col)
        if s_val and m_val and m_val > 0:
            ratios[col] = float(min(3.0, max(0.33, s_val / m_val)))
    if not ratios:
        return hourly, None
    df = hourly.copy()
    hrs = np.asarray((df.index - now) / pd.Timedelta(hours=1), dtype=float)
    weight = np.exp(-np.abs(hrs) / tau_h)
    for col, r in ratios.items():
        df[col] = df[col] * (1 + (r - 1) * weight)
    # India: recompute sub-indices from the corrected concentrations
    df = add_cpcb_aqi(df.drop(columns=[c for c in df.columns if c.startswith("si_")] + ["in_aqi", "dominant"], errors="ignore"))

    # US: shift the model's AQI by however much the correction moves the PM index (24 h means), unless a gas drove it
    def us_pm(frame):
        p25 = frame["pm2_5"].rolling(24, min_periods=8).mean().map(lambda c: us_index("pm25", c))
        p10 = frame["pm10"].rolling(24, min_periods=8).mean().map(lambda c: us_index("pm10", c))
        return pd.concat([p25, p10], axis=1).max(axis=1)
    delta = (us_pm(df) - us_pm(hourly)).fillna(0)
    pm_driven = True
    if "us_aqi_pm2_5" in df and "us_aqi_pm10" in df:
        pm_driven = df["us_aqi"] <= df[["us_aqi_pm2_5", "us_aqi_pm10"]].max(axis=1) + 1
    df["us_aqi"] = (df["us_aqi"] + delta.where(pm_driven, 0)).clip(lower=0).round()
    return df, {"ratios": ratios, "station": stn["name"]}
