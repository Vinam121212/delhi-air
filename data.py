"""Data fetching: Open-Meteo (CAMS model, free & keyless) + optional WAQI live station readings."""
import os
from datetime import date

import pandas as pd
import requests
import streamlit as st

from aqi import add_cpcb_aqi
from locations import CITIES, DEFAULT_CITY, LOCATIONS, city_locations

AQ_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
WX_URL = "https://api.open-meteo.com/v1/forecast"
WAQI_URL = "https://api.waqi.info"
TZ = "Asia/Kolkata"
HISTORY_START = date(2022, 8, 1)  # earliest date the Open-Meteo air-quality archive covers

HOURLY_VARS = [
    "pm2_5", "pm10", "carbon_monoxide", "carbon_dioxide", "nitrogen_dioxide",
    "sulphur_dioxide", "ozone", "dust", "us_aqi", "us_aqi_pm2_5", "us_aqi_pm10", "uv_index",
]
CURRENT_VARS = HOURLY_VARS

_session = requests.Session()
_session.headers["User-Agent"] = "AQIfyMe/1.0"


def _get(url, params, timeout=20, retries=2):
    for attempt in range(retries + 1):
        try:
            r = _session.get(url, params=params, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            if attempt == retries:
                raise


def _hourly_frame(payload) -> pd.DataFrame:
    df = pd.DataFrame(payload["hourly"])
    df["time"] = pd.to_datetime(df["time"])
    return df.set_index("time")


# ── Open-Meteo ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def fetch_hourly(lat, lon, past_days=3, forecast_days=4) -> pd.DataFrame:
    """Hourly pollutants for recent past + forecast, with CPCB AQI columns."""
    payload = _get(AQ_URL, {
        "latitude": lat, "longitude": lon, "hourly": ",".join(HOURLY_VARS),
        "past_days": past_days, "forecast_days": forecast_days, "timezone": TZ,
    })
    return add_cpcb_aqi(_hourly_frame(payload))


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def fetch_history(lat, lon, start: date, end: date) -> pd.DataFrame:
    """Archived hourly data for an arbitrary date range (padded 1 day earlier so 24h averages are complete)."""
    pad_start = max(HISTORY_START, start - pd.Timedelta(days=1))
    payload = _get(AQ_URL, {
        "latitude": lat, "longitude": lon, "hourly": ",".join(HOURLY_VARS),
        "start_date": pad_start.isoformat(), "end_date": end.isoformat(), "timezone": TZ,
    }, timeout=40)
    df = add_cpcb_aqi(_hourly_frame(payload))
    return df[df.index >= pd.Timestamp(start)]


@st.cache_data(ttl=3 * 3600, show_spinner=False)
def fetch_history_city(city: str, start: date, end: date) -> dict:
    """Archived hourly data for every locality in a city (one batched request) → {locality: frame}."""
    names = list(city_locations(city))
    pad_start = max(HISTORY_START, start - pd.Timedelta(days=1))
    payload = _get(AQ_URL, {
        "latitude": ",".join(str(LOCATIONS[n]["lat"]) for n in names),
        "longitude": ",".join(str(LOCATIONS[n]["lon"]) for n in names),
        "hourly": ",".join(HOURLY_VARS), "start_date": pad_start.isoformat(), "end_date": end.isoformat(), "timezone": TZ,
    }, timeout=60)
    if isinstance(payload, dict):
        payload = [payload]
    out = {}
    for name, item in zip(names, payload):
        df = add_cpcb_aqi(_hourly_frame(item))
        out[name] = df[df.index >= pd.Timestamp(start)]
    return out


@st.cache_data(ttl=300, show_spinner=False)
def fetch_all_current(city: str = DEFAULT_CITY) -> pd.DataFrame:
    """Current readings for every tracked locality in a city, in one batched request."""
    names = list(city_locations(city))
    payload = _get(AQ_URL, {
        "latitude": ",".join(str(LOCATIONS[n]["lat"]) for n in names),
        "longitude": ",".join(str(LOCATIONS[n]["lon"]) for n in names),
        "hourly": ",".join(HOURLY_VARS), "past_days": 1, "forecast_days": 1, "timezone": TZ,
    })
    if isinstance(payload, dict):
        payload = [payload]
    now = pd.Timestamp.now(tz=TZ).tz_localize(None).floor("h")
    rows = []
    for name, item in zip(names, payload):
        df = add_cpcb_aqi(_hourly_frame(item))
        df = df[df.index <= now]
        last = df.iloc[-1]
        rows.append({"location": name, **LOCATIONS[name], **last.to_dict(), "time": df.index[-1]})
    return pd.DataFrame(rows)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_weather(lat, lon) -> dict:
    payload = _get(WX_URL, {
        "latitude": lat, "longitude": lon, "timezone": TZ,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m,wind_direction_10m,surface_pressure,visibility,weather_code,is_day",
        "hourly": "wind_speed_10m,wind_direction_10m,boundary_layer_height,relative_humidity_2m,visibility,temperature_2m",
        "past_days": 1, "forecast_days": 3,
    })
    return payload


# ── WAQI (optional, needs a free token from https://aqicn.org/data-platform/token/) ──
def server_token():
    """Token configured by the site owner (secrets.toml / hosting secrets / env) — shared by every visitor."""
    tok = os.environ.get("WAQI_TOKEN")
    if not tok:
        try:
            tok = st.secrets.get("WAQI_TOKEN")
        except Exception:
            tok = None
    return (tok or "").strip() or None


def waqi_token():
    """Owner's server token first; otherwise a token the visitor pasted in this session."""
    return server_token() or (st.session_state.get("waqi_token") or "").strip() or None


def is_local():
    try:
        host = (st.context.headers.get("Host") or "").split(":")[0]
    except Exception:
        return True
    return host in ("localhost", "127.0.0.1", "::1", "")


MAX_STATION_KM = 20


@st.cache_data(ttl=300, show_spinner=False)
def waqi_nearby(token: str, lat: float, lon: float, box: float = 0.2) -> pd.DataFrame:
    """Reporting stations in a small box around a point (WAQI's geo lookup can return far-away stations)."""
    js = _get(f"{WAQI_URL}/map/bounds/", {"latlng": f"{lat - box},{lon - box},{lat + box},{lon + box}", "token": token})
    if js.get("status") != "ok":
        raise RuntimeError(js.get("data", "WAQI error"))
    rows = []
    for s_ in js["data"]:
        try:
            rows.append({"uid": s_["uid"], "lat": s_["lat"], "lon": s_["lon"], "aqi": float(s_["aqi"])})
        except (TypeError, ValueError):
            continue
    return pd.DataFrame(rows)


@st.cache_data(ttl=300, show_spinner=False)
def waqi_feed_uid(token: str, uid: int) -> dict:
    js = _get(f"{WAQI_URL}/feed/@{uid}/", {"token": token})
    if js.get("status") != "ok":
        raise RuntimeError(js.get("data", "WAQI error"))
    return js["data"]


def station_reading(lat, lon):
    """Live reading from the closest reporting WAQI station within MAX_STATION_KM, or None."""
    token = waqi_token()
    if not token:
        return None
    from browser_js import haversine_km
    from station import parse_feed
    try:
        near = waqi_nearby(token, round(lat, 3), round(lon, 3))
        if near.empty:
            return None
        near["km"] = [haversine_km(lat, lon, a, b) for a, b in zip(near["lat"], near["lon"])]
        best = near.sort_values("km").iloc[0]
        if best["km"] > MAX_STATION_KM:
            return None
        reading = parse_feed(waqi_feed_uid(token, int(best["uid"])), lat, lon)
        return reading if reading and reading["distance_km"] <= MAX_STATION_KM else None
    except Exception:
        return None


def save_waqi_token(token: str):
    """Persist the token in .streamlit/secrets.toml (git-ignored) so it loads automatically."""
    from pathlib import Path
    path = Path(__file__).parent / ".streamlit" / "secrets.toml"
    path.parent.mkdir(exist_ok=True)
    lines = [l for l in (path.read_text().splitlines() if path.exists() else []) if not l.startswith("WAQI_TOKEN")]
    lines.append(f'WAQI_TOKEN = "{token.strip()}"')
    path.write_text("\n".join(lines) + "\n")


@st.cache_data(ttl=300, show_spinner=False)
def waqi_stations(token: str, city: str = DEFAULT_CITY) -> pd.DataFrame:
    lat1, lon1, lat2, lon2 = CITIES[city]["bounds"]
    js = _get(f"{WAQI_URL}/map/bounds/", {"latlng": f"{lat1},{lon1},{lat2},{lon2}", "token": token})
    if js.get("status") != "ok":
        raise RuntimeError(js.get("data", "WAQI error"))
    rows = []
    for s in js["data"]:
        try:
            aqi_v = float(s["aqi"])
        except (TypeError, ValueError):
            continue
        rows.append({"uid": s["uid"], "station": s["station"]["name"], "lat": s["lat"], "lon": s["lon"],
                     "aqi": aqi_v, "time": s["station"].get("time")})
    return pd.DataFrame(rows)


@st.cache_data(ttl=300, show_spinner=False)
def waqi_feed(token: str, lat: float, lon: float) -> dict:
    """Nearest station's live reading (WAQI sub-indices are on the US EPA scale)."""
    js = _get(f"{WAQI_URL}/feed/geo:{lat};{lon}/", {"token": token})
    if js.get("status") != "ok":
        raise RuntimeError(js.get("data", "WAQI error"))
    return js["data"]
