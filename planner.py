"""Outdoor activity planner: find the cleanest time slots in the forecast and estimate the inhaled dose."""
import math

import pandas as pd

# breathing rate (m³/h) and how strict to be (CPCB AQI the activity is comfortable up to)
ACTIVITIES = {
    "🏃 Running": {"rate": 3.0, "ok": 100},
    "🚴 Cycling": {"rate": 2.5, "ok": 100},
    "🚶 Walking": {"rate": 1.3, "ok": 150},
    "🧒 Kids playing": {"rate": 1.2, "ok": 100},
    "🧘 Outdoor yoga": {"rate": 0.9, "ok": 120},
    "🎒 School run / commute": {"rate": 1.1, "ok": 200},
    "🐕 Dog walk": {"rate": 1.2, "ok": 150},
}


def find_slots(future: pd.DataFrame, aqi_col: str, minutes: int, start_h: int, end_h: int, top: int = 3):
    """Return (slots, all_candidates). A slot = dict(start, end, aqi, pm25)."""
    hours = max(1, math.ceil(minutes / 60))
    df = future[[aqi_col, "pm2_5"]].copy()
    cands = []
    for i in range(len(df) - hours + 1):
        window = df.iloc[i:i + hours]
        t0 = window.index[0]
        t_end = t0 + pd.Timedelta(minutes=minutes)
        if t0.hour < start_h or (t_end - pd.Timedelta(minutes=1)).hour >= end_h or t_end.date() != t0.date():
            continue
        if (window.index[-1] - t0) != pd.Timedelta(hours=hours - 1):
            continue
        cands.append({"start": t0, "end": t_end, "aqi": window[aqi_col].mean(), "pm25": window["pm2_5"].mean()})
    # rank by hourly PM2.5: the AQI is a 24 h rolling average, too smooth to pick a 45-minute window
    ranked = sorted(cands, key=lambda c: (c["pm25"], c["aqi"]))
    picked = []
    for c in ranked:
        if all(c["end"] <= p["start"] or c["start"] >= p["end"] for p in picked):
            picked.append(c)
        if len(picked) == top:
            break
    return picked, cands


def dose_ug(pm25, minutes, rate):
    """Inhaled PM2.5 mass in micrograms."""
    return pm25 * rate * minutes / 60


def verdict(aqi_value, ok_limit):
    if aqi_value <= ok_limit * 0.6:
        return "Great time", "#4ade80"
    if aqi_value <= ok_limit:
        return "Okay", "#facc15"
    if aqi_value <= ok_limit * 1.5:
        return "Go easy / shorten it", "#fb923c"
    return "Better indoors", "#f87171"
