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
