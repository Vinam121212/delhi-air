"""AQIfyMe — verified air-quality information for Delhi. Run with:  streamlit run app.py"""
from datetime import date, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import data
from aqi import (CATEGORY_DESC, GRAP_STAGES, HEALTH, PERSONA_TIPS, POLLUTANTS, categories, category,
                 cigarettes_per_day, sub_index)
from locations import DELHI_CENTER, LOCATIONS
from browser_js import alerts_html, geolocate_html, nearest_locality
from causes import analyse, fetch_fires
from details import DetailBuilder
import health_log as hl
from planner import ACTIVITIES, dose_ug, find_slots, verdict
from i18n import set_lang, t
from expand import EXPAND_CSS, expand_html
from intro import INTRO_CSS, intro_html
from sky import sky_html
from ui import CSS, compact, hex_to_rgba, scale_html, style_fig

st.set_page_config(page_title="AQIfyMe · Delhi air quality", page_icon="🌤️", layout="wide",
                   initial_sidebar_state="expanded")
st.markdown(CSS, unsafe_allow_html=True)
st.markdown(EXPAND_CSS, unsafe_allow_html=True)
st.markdown(INTRO_CSS, unsafe_allow_html=True)
st.html(intro_html(), unsafe_allow_javascript=True)   # plays once per session, before the page fades in

TZ = data.TZ
CHART_CFG = {"displayModeBar": False}
AQI_POLLUTANTS = ["pm2_5", "pm10", "nitrogen_dioxide", "ozone", "carbon_monoxide", "sulphur_dioxide"]
ALL_POLLUTANTS = AQI_POLLUTANTS + ["carbon_dioxide", "dust"]
LABEL = {k: v["label"] for k, v in POLLUTANTS.items()}
LABEL.update({"AQI": "AQI"})
TILE_KEYS = ["main", "cig", "change", "wind", "humidity", "visibility"]


def now_ist():
    return pd.Timestamp.now(tz=TZ).tz_localize(None)


# ══════════════════════════════════════════════════════════════════════════════
# Sidebar
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    lang_choice = st.segmented_control("Language", ["English", "हिन्दी"], default="English", key="lang",
                                       label_visibility="collapsed") or "English"
    set_lang(lang_choice)
    st.markdown(f"<div class='brand'><div class='brand-icon'></div><div><div class='brand-name' title='Tap to replay the intro'><span class='a'>AQI</span><span class='f'>fy</span><span class='m'>Me</span></div>"
                f"<div class='brand-sub'>{t('Live air-quality intelligence')}</div></div></div>", unsafe_allow_html=True)

    st.markdown(f"#### {t('Location')}")
    # ?near=lat,lon (set by the "Use my location" button) picks the closest locality
    near_note, near_loc = None, None
    if "near" in st.query_params:
        try:
            _lat, _lon = (float(x) for x in st.query_params["near"].split(","))
            near_loc, d_loc, d_delhi = nearest_locality(_lat, _lon)
            near_note = (f"📍 You're {d_loc:.1f} km from {near_loc}." if d_delhi < 60 else
                         f"📍 You're {d_delhi:,.0f} km from Delhi — showing the nearest tracked locality, {near_loc}.")
        except ValueError:
            pass
    zones = ["All zones"] + sorted({v["zone"] for v in LOCATIONS.values()})
    zone = st.selectbox(t("Zone"), zones, label_visibility="collapsed", format_func=t)
    loc_options = [n for n, v in LOCATIONS.items() if zone == "All zones" or v["zone"] == zone]
    pref = near_loc if near_loc in loc_options else "ITO"
    location = st.selectbox(t("Locality"), loc_options, index=loc_options.index(pref) if pref in loc_options else 0)
    if st.button(f"📍 {t('Use my location')}", width="stretch"):
        st.session_state["geo_request"] = True
    if st.session_state.pop("geo_request", False):
        st.html(geolocate_html(), unsafe_allow_javascript=True)
    if near_note:
        st.caption(near_note)

    st.markdown(f"#### {t('Pollutants')}")
    focus = st.selectbox(t("Focus pollutant"), ["AQI"] + ALL_POLLUTANTS,
                         format_func=lambda k: t("Overall AQI") if k == "AQI" else f"{LABEL[k]} — {POLLUTANTS[k]['name']}")
    trend_pollutants = st.multiselect(t("Pollutants on trend charts"), ALL_POLLUTANTS,
                                      default=["pm2_5", "pm10", "nitrogen_dioxide"], format_func=LABEL.get)
    standard = st.radio(t("AQI standard"), ["India (CPCB)", "US (EPA)"], horizontal=True)

    st.markdown(f"#### {t('Health profile')}")
    persona = st.selectbox("I am…", list(PERSONA_TIPS), label_visibility="collapsed")

    st.markdown(f"#### {t('Alerts')}")
    alerts_on = st.toggle(t("AQI alerts"), value=False,
                          help="Shows a banner and a desktop notification while this page is open.")
    _levels = [(c[1], prev + 1) for prev, c in zip([-1] + [x[0] for x in categories(standard)], categories(standard))][2:]
    alert_level = st.selectbox(t("Alert me when AQI reaches"), _levels, index=1, disabled=not alerts_on,
                               format_func=lambda x: f"{t(x[0])} ({x[1]}+)")
    alert_soon = st.checkbox(t("Also warn about the next 3 hours"), value=True, disabled=not alerts_on)

    st.markdown(f"#### {t('Live updates')}")
    auto = st.toggle(t("Auto-refresh"), value=True)
    every = st.select_slider(t("Refresh every"), options=[1, 2, 5, 10, 15, 30], value=5,
                             format_func=lambda m: f"{m} {t('min')}", disabled=not auto)
    motion = st.toggle(t("Animated sky"), value=True, help="Turn off to save battery on slower devices.")
    if st.button(t("⟳  Refresh now"), width="stretch"):
        st.cache_data.clear()
        st.rerun()

    if data.server_token():
        st.caption("🛰️ " + t("Live station data is on for everyone"))
    else:
        with st.expander(f"⚙️ {t('Live station data (optional)')}", expanded=False):
            st.caption("This site is using CAMS model data, which is coarse — nearby localities can look identical. "
                       "To switch on real CPCB/DPCC station readings for **every visitor**, the site owner adds one free token "
                       "from [aqicn.org/data-platform/token](https://aqicn.org/data-platform/token/) to the app's secrets "
                       "(`WAQI_TOKEN`). You can also try it just for yourself by pasting a token here:")
            st.text_input("WAQI token", type="password", key="waqi_token")
            if data.is_local() and st.session_state.get("waqi_token") and st.button("💾 Remember on this computer", width="stretch"):
                data.save_waqi_token(st.session_state["waqi_token"])
                st.success("Saved to .streamlit/secrets.toml — station data is now on for everyone using this computer's site.")

AQI_COL = "in_aqi" if standard == "India (CPCB)" else "us_aqi"
CATS = categories(standard)
LOC = LOCATIONS[location]


def aqi_colour(v):
    return category(v, standard)[1]


# ══════════════════════════════════════════════════════════════════════════════
# Live dashboard (re-runs on a timer)
# ══════════════════════════════════════════════════════════════════════════════
def show(html):
    st.markdown(compact(html), unsafe_allow_html=True)


def sky_for(level):
    """Inject / update the WebGL sky. URL overrides ?sky=0..5 and ?hour=0..23 preview other conditions."""
    qp = st.query_params
    try:
        level = float(qp.get("sky", level))
        hour = float(qp.get("hour", now_ist().hour + now_ist().minute / 60))
    except ValueError:
        hour = now_ist().hour + now_ist().minute / 60
    st.html(sky_html(level, hour, paused=not motion), unsafe_allow_javascript=True)


def pollutant_card(key, value, si, delay):
    meta = POLLUTANTS[key]
    unit = meta["unit"]
    shown = "—" if value is None or pd.isna(value) else (f"{value:,.0f}" if value >= 100 else f"{value:,.1f}")
    if si is not None:
        col = aqi_colour(si) if standard == "India (CPCB)" else category(si, "India (CPCB)")[1]
        pct = min(100, si / 5)
        foot = f'<span class="chip">Sub-index {si}</span>'
    else:
        col, pct, foot = "#7dd3fc", 0, ""
        if key == "carbon_dioxide" and value is not None and not pd.isna(value):
            pct = min(100, (value - 280) / 3)
            foot = f'<span class="chip">+{value - 280:.0f} ppm vs pre-industrial</span>'
    if meta.get("who") and value is not None and not pd.isna(value):
        foot += f' <span class="chip">{value / meta["who"]:.1f}× WHO</span>'
    focus_cls = " focus" if key == focus else ""
    return compact(f"""
    <div class="card pcard xp{focus_cls}" data-detail="{key}" style="animation-delay:{delay}s"><span class="xp-hint">⤢</span>
      <div class="card-label">{meta['label']} <span style="text-transform:none;letter-spacing:0;font-weight:500">· {meta['name'].split('(')[0]}</span></div>
      <div class="card-value" style="color:{col}">{shown}<span class="card-unit">{unit}</span></div>
      <div class="bar"><span style="width:{pct:.0f}%;background:linear-gradient(90deg,{hex_to_rgba(col, .55)},{col});box-shadow:0 0 12px {col};animation-delay:{delay + .2}s"></span></div>
      {foot}
    </div>""")


def outlook_sentence(past, future, aqi_now, cat_name):
    nxt = future.head(12)[AQI_COL].dropna()
    if nxt.empty:
        return f"Air quality is currently {cat_name.lower()}."
    cur_lvl = category(aqi_now, standard)[3]
    peak_t, peak_v = nxt.idxmax(), nxt.max()
    low_t, low_v = nxt.idxmin(), nxt.min()
    if category(peak_v, standard)[3] > cur_lvl:
        return (f"Air quality is expected to worsen to <b>{category(peak_v, standard)[0]}</b> around "
                f"<b>{peak_t:%-I %p}</b>, peaking near {peak_v:.0f}.")
    if category(low_v, standard)[3] < cur_lvl:
        return (f"Conditions should improve to <b>{category(low_v, standard)[0]}</b> by <b>{low_t:%-I %p}</b> "
                f"(AQI ≈ {low_v:.0f}).")
    return f"Air quality will stay <b>{cat_name}</b> for the next 12 hours, between {low_v:.0f} and {peak_v:.0f}."


def render_live():
    try:
        hourly = data.fetch_hourly(LOC["lat"], LOC["lon"])
    except Exception as e:
        st.error(f"Couldn't reach the air-quality service — retrying on the next refresh. ({e})")
        return
    try:
        weather = data.fetch_weather(LOC["lat"], LOC["lon"])
    except Exception:
        weather = {}
    w = weather.get("current", {})

    now = now_ist().floor("h")
    past = hourly[hourly.index <= now]
    future = hourly[hourly.index > now]
    cur = past.iloc[-1]
    aqi_now = cur[AQI_COL]
    cat_name, cat_col, cat_emoji, level = category(aqi_now, standard)
    in_level = category(cur["in_aqi"], "India (CPCB)")[3]
    sky_for(in_level)

    # ── hero (iOS Weather style) ─────────────────────────────────────────────
    stn = data.station_reading(LOC["lat"], LOC["lon"])
    station_line = ""
    if stn:
        s_val = stn["in_aqi"] if standard == "India (CPCB)" and stn["in_aqi"] is not None else stn["us_aqi"]
        s_std = "India (CPCB)" if standard == "India (CPCB)" and stn["in_aqi"] is not None else "US (EPA)"
        s_name, s_col, _, _ = category(s_val, s_std)
        pm_txt = f" · PM2.5 {stn['pm2_5']:.0f} µg/m³" if stn["pm2_5"] else ""
        station_line = (f'<div class="station-pill"><span class="sdot" style="background:{s_col}"></span>'
                        f'🛰️ {t("Measured at")} <b>{stn["name"]}</b> ({stn["distance_km"]:.1f} km): '
                        f'<b style="color:{s_col}">{s_val:.0f}</b> {t(s_name)}'
                        f'{pm_txt}'
                        f' <span style="opacity:.7">· {stn["time"][11:16]}</span></div>')
    today = hourly[hourly.index.date == now.date()][AQI_COL]
    temp = w.get("temperature_2m")
    pill = (f'<span class="live-pill"><span class="live-dot"></span>{t("LIVE · updates every")} {every} {t("min")}</span>' if auto
            else f'<span class="live-pill paused"><span class="live-dot"></span>{t("AUTO-REFRESH PAUSED")}</span>')
    show(f"""
    <div class="hero fade xp" data-detail="aqi" style="position:relative;border-radius:32px;overflow:hidden" title="Tap for details">
      <div class="hero-zone">📍 {LOC['zone']} Delhi{f' · {temp:.0f}°C' if temp is not None else ''}</div>
      <div class="hero-loc">{location}</div>
      <div class="hero-aqi" style="--num:{int(round(aqi_now))}"></div>
      <div class="hero-cat"><span class="hero-dot" style="background:{cat_col}"></span>{t(cat_name)}</div>
      <div class="hero-hl">H: {today.max():.0f}&nbsp;&nbsp;L: {today.min():.0f} &nbsp;·&nbsp; {standard} AQI</div>
      {station_line}
      {pill}
      <div style="font-size:.72rem;color:var(--muted);margin-top:.45rem">{t('Reading for')} {past.index[-1]:%d %b, %-I:%M %p} IST · {t('checked')} {now_ist():%-I:%M:%S %p} · {t('Tap any box for details')}</div>
    </div>""")

    # ── hourly strip ─────────────────────────────────────────────────────────
    strip = pd.concat([past.tail(1), future.head(24)])
    hours = []
    for i, (ts, row) in enumerate(strip.iterrows()):
        v = row[AQI_COL]
        _, col, emo, _ = category(v, standard)
        hours.append(f'<div class="hr{" now" if i == 0 else ""}"><div class="t">{t("Now") if i == 0 else f"{ts:%-I %p}"}</div>'
                     f'<div class="e">{emo}</div><div class="v" style="color:{col}">{v:.0f}</div>'
                     f'<div class="b" style="background:{col};box-shadow:0 0 8px {col}"></div></div>')
    dom = cur.get("dominant")
    dom_label = LABEL.get(dom, "—") if isinstance(dom, str) else "—"
    show(f"""
    <div class="card xp" data-detail="hourly" style="animation-delay:.1s;margin-bottom:1rem"><span class="xp-hint">⤢</span>
      <div class="summary">{outlook_sentence(past, future, aqi_now, cat_name)} Main pollutant: <b>{dom_label}</b>.</div>
      <div class="sep"></div>
      <div class="card-label">🕒 {t('Hourly forecast')}</div>
      <div class="hours">{''.join(hours)}</div>
    </div>""")

    # ── daily range bars + detail tiles ──────────────────────────────────────
    left, right = st.columns([1, 1.3], gap="medium")
    with left:
        daily = hourly[hourly.index.date >= now.date()].groupby(hourly[hourly.index.date >= now.date()].index.date)[AQI_COL]
        daily = daily.agg(["min", "max", "mean"]).dropna()
        g_lo, g_hi = daily["min"].min(), daily["max"].max()
        span = (g_hi - g_lo) or 1
        rows = []
        for i, (d, r) in enumerate(daily.iterrows()):
            name = t("Today") if i == 0 else pd.Timestamp(d).strftime("%a")
            c_lo, c_hi = aqi_colour(r["min"]), aqi_colour(r["max"])
            left_pct, width = (r["min"] - g_lo) / span * 100, max(4, (r["max"] - r["min"]) / span * 100)
            dot = (f'<span class="cur" style="left:{(aqi_now - g_lo) / span * 100:.1f}%"></span>' if i == 0 else "")
            rows.append(f'<div class="day"><span>{name}</span><span style="font-size:1.25rem">{category(r["mean"], standard)[2]}</span>'
                        f'<span class="lo">{r["min"]:.0f}</span><div class="track"><span class="fill" style="left:{left_pct:.1f}%;'
                        f'width:{width:.1f}%;background:linear-gradient(90deg,{c_lo},{c_hi});animation-delay:{.1 * i:.1f}s"></span>{dot}</div>'
                        f'<span>{r["max"]:.0f}</span></div>')
        show(f"""<div class="card xp" data-detail="daily" style="animation-delay:.15s"><span class="xp-hint">⤢</span>
          <div class="card-label">📅 {len(daily)}-{t('day AQI forecast')}</div><div class="sep"></div>{''.join(rows)}
          <div class="muted" style="font-size:.74rem;margin-top:.6rem">{t("Bars show each day's low → high AQI. White dot = now.")}</div></div>""")
    with right:
        prev24 = past[AQI_COL].iloc[-25] if len(past) > 25 else np.nan
        delta = None if pd.isna(prev24) else aqi_now - prev24
        cig = cigarettes_per_day(past["pm2_5"].tail(24).mean()) or 0
        wind = w.get("wind_speed_10m") or 0
        wdir = w.get("wind_direction_10m") or 0
        hum = w.get("relative_humidity_2m")
        vis = w.get("visibility")
        dom_val = cur.get(dom) if isinstance(dom, str) else None
        dom_who = POLLUTANTS.get(dom, {}).get("who") if isinstance(dom, str) else None
        dom_note = (f"{dom_val:.0f} {POLLUTANTS[dom]['unit']} — {dom_val / dom_who:.1f}× the WHO guideline."
                    if dom_val is not None and dom_who else "The pollutant with the highest sub-index.")
        tiles = [
            ("🫁 " + t("Main pollutant"), dom_label, dom_note),
            ("🚬 " + t("Cigarette equivalent"), f"{cig:.1f}", f"Breathing this air for a day ≈ smoking {cig:.1f} cigarettes."),
            ("📈 " + t("Since yesterday"), "—" if delta is None else f"{'▲' if delta > 0 else '▼'} {abs(delta):.0f}",
             "—" if delta is None else ("Worse than this time yesterday." if delta > 0 else "Better than this time yesterday.")),
            ("🍃 " + t("Wind"), f'{wind:.0f} <span style="font-size:1rem">km/h</span> '
                       f'<span style="display:inline-block;transform:rotate({wdir + 180:.0f}deg)">↑</span>',
             "Calm air lets pollution build up." if wind < 6 else "Light winds, limited dispersion." if wind < 15
             else "Breezy — helps clear pollution."),
            ("💧 " + t("Humidity"), "—" if hum is None else f"{hum:.0f}%",
             "Humid, still air traps fine particles as smog." if (hum or 0) > 70 else "Drier air — less smog formation."),
            ("👁️ " + t("Visibility"), "—" if not vis else f"{vis / 1000:.1f} km",
             "Haze is cutting visibility." if vis and vis < 5000 else "Fairly clear horizon."),
        ]
        show('<div class="tiles">' + "".join(
            f'<div class="card tile xp" data-detail="{tk}" style="animation-delay:{.2 + .05 * i:.2f}s"><span class="xp-hint">⤢</span>'
            f'<div class="card-label">{lab}</div><div class="big">{val}</div><div class="note">{note}</div></div>'
            for i, ((lab, val, note), tk) in enumerate(zip(tiles, TILE_KEYS))) + "</div>")

    st.write("")
    show(scale_html(CATS, level, aqi_now, CATEGORY_DESC, detail="scale"))
    st.write("")

    # ── pollutant cards ───────────────────────────────────────────────────────
    cards = []
    for i, key in enumerate(ALL_POLLUTANTS):
        si = cur.get(f"si_{key}")
        si = None if si is None or pd.isna(si) else int(si)
        cards.append(pollutant_card(key, cur.get(key), si, 0.05 * i))
    show(f'<div class="pgrid">{"".join(cards)}</div>')

    # ── expanded views for every box above ────────────────────────────────────
    try:
        all_current = data.fetch_all_current()
    except Exception:
        all_current = None
    db = DetailBuilder(hourly=hourly, now=now, location=location, zone=LOC["zone"], standard=standard, aqi_col=AQI_COL,
                       weather=weather, all_current=all_current, label=LABEL)
    builders = {"aqi": db.aqi, "hourly": db.hourly, "daily": db.daily, "scale": db.scale, "main": db.main_pollutant,
                "cig": db.cigarettes, "change": db.change, "wind": db.wind, "humidity": db.humidity, "visibility": db.visibility,
                **{k: (lambda k=k: db.pollutant(k)) for k in ALL_POLLUTANTS}}
    details = {}
    for k, fn in builders.items():
        try:
            details[k] = fn()
        except Exception as e:  # one broken view shouldn't take down the rest
            details[k] = {"title": k, "html": f"<p>Details unavailable right now ({e}).</p>", "summary": ""}
    st.html(expand_html(details), unsafe_allow_javascript=True)

    # ── alerts ────────────────────────────────────────────────────────────────
    soon = future.head(3)[AQI_COL]
    st.html(alerts_html({
        "enabled": bool(alerts_on), "threshold": alert_level[1], "aqi": float(aqi_now), "cat": t(cat_name), "loc": location,
        "soon_max": float(soon.max()) if alert_soon and not soon.empty else None,
        "soon_time": f"{soon.idxmax():%-I %p}" if not soon.empty else "", "soon_cat": t(category(soon.max(), standard)[0]) if not soon.empty else "",
        "hour_key": f"{location}-{now:%Y%m%d%H}"}), unsafe_allow_javascript=True)

    token = data.waqi_token()

    st.write("")
    tabs = st.tabs([t(x) for x in ["📈 Trends", "🔮 Forecast", "🗓️ Planner", "🔎 Why?", "🗺️ Map", "🏙️ Compare areas",
                                    "❤️ Health advice"]])
    with tabs[2]:
        render_planner(future, now)
    with tabs[3]:
        render_causes(hourly, now, weather)
    tabs = [tabs[0], tabs[1], tabs[4], tabs[5], tabs[6]]
    with tabs[0]:
        render_trends(past, now)
    with tabs[1]:
        render_forecast(future, hourly, now)
    with tabs[2]:
        render_map(token)
    with tabs[3]:
        render_compare()
    with tabs[4]:
        render_health(in_level)


# ── tab: trends ───────────────────────────────────────────────────────────────
def aqi_band_shapes(fig, ymax):
    lo = 0
    for hi, name, col, _ in CATS:
        if lo > ymax:
            break
        fig.add_hrect(y0=lo, y1=min(hi, ymax * 1.05), fillcolor=hex_to_rgba(col, 0.07), line_width=0, layer="below")
        lo = hi


def render_trends(past, now):
    window = past.tail(72)
    a, b = st.columns([1.6, 1], gap="large")
    with a:
        fig = go.Figure()
        ymax = max(100, float(window[AQI_COL].max() or 0) * 1.15)
        aqi_band_shapes(fig, ymax)
        fig.add_trace(go.Scatter(x=window.index, y=window[AQI_COL], mode="lines", name="AQI", fill="tozeroy",
                                 line=dict(color="#38bdf8", width=3, shape="spline"),
                                 fillcolor="rgba(56,189,248,0.12)"))
        fig.update_layout(title=f"{standard} AQI · last 72 hours", yaxis_range=[0, ymax])
        st.plotly_chart(style_fig(fig, legend=False), width="stretch", config=CHART_CFG)
    with b:
        latest = past.iloc[-1]
        si = {LABEL[p]: latest.get(f"si_{p}") for p in AQI_POLLUTANTS if not pd.isna(latest.get(f"si_{p}"))}
        fig = go.Figure(go.Pie(labels=list(si), values=list(si.values()), hole=.62, sort=False,
                               marker=dict(colors=["#38bdf8", "#a78bfa", "#f472b6", "#facc15", "#34d399", "#fb923c"],
                                           line=dict(color="#0b1120", width=2)),
                               textinfo="label", hovertemplate="%{label}: sub-index %{value}<extra></extra>"))
        fig.update_layout(title="What's driving the AQI", annotations=[dict(text="Sub-index<br>share", showarrow=False,
                                                                           font=dict(size=13, color="#94a3b8"))])
        st.plotly_chart(style_fig(fig, legend=False), width="stretch", config=CHART_CFG)

    if trend_pollutants:
        fig = go.Figure()
        for p in trend_pollutants:
            fig.add_trace(go.Scatter(x=window.index, y=window[p], name=f"{LABEL[p]} ({POLLUTANTS[p]['unit']})",
                                     mode="lines", line=dict(width=2.4, shape="spline")))
            who = POLLUTANTS[p].get("who")
            if who and len(trend_pollutants) == 1:
                fig.add_hline(y=who, line_dash="dot", line_color="#4ade80",
                              annotation_text="WHO guideline", annotation_font_color="#4ade80")
        fig.update_layout(title="Pollutant concentrations · last 72 hours")
        st.plotly_chart(style_fig(fig), width="stretch", config=CHART_CFG)

    # hour-of-day pattern heatmap
    key = "pm2_5" if focus == "AQI" else focus
    col_name = AQI_COL if focus == "AQI" else key
    hm = past.tail(24 * 7).copy() if len(past) > 24 else past.copy()
    hm["day"] = hm.index.strftime("%a %d")
    hm["hour"] = hm.index.hour
    pivot = hm.pivot_table(index="day", columns="hour", values=col_name, aggfunc="mean", sort=False)
    fig = go.Figure(go.Heatmap(z=pivot.values, x=[f"{h:02d}:00" for h in pivot.columns], y=pivot.index,
                               colorscale=[[0, "#0ea5e9"], [.35, "#facc15"], [.65, "#f97316"], [1, "#7f1d1d"]],
                               hovertemplate="%{y} %{x}<br>%{z:.0f}<extra></extra>", colorbar=dict(thickness=10)))
    fig.update_layout(title=f"Daily rhythm · {'AQI' if focus == 'AQI' else LABEL[key]} by hour of day")
    st.plotly_chart(style_fig(fig, height=300, legend=False), width="stretch", config=CHART_CFG)


# ── tab: forecast ─────────────────────────────────────────────────────────────
def render_forecast(future, hourly, now):
    fut = future.head(96)
    if fut.empty:
        st.info("No forecast available right now.")
        return
    colours = [aqi_colour(v) for v in fut[AQI_COL]]
    fig = go.Figure(go.Bar(x=fut.index, y=fut[AQI_COL], marker_color=colours, marker_line_width=0,
                           hovertemplate="%{x|%a %d %b, %I %p}<br>AQI %{y:.0f}<extra></extra>"))
    fig.update_layout(title=f"Hourly AQI forecast · next {len(fut)} hours", bargap=.15)
    st.plotly_chart(style_fig(fig, legend=False), width="stretch", config=CHART_CFG)

    # best / worst windows for outdoor time (06:00–21:00, 2-hour blocks)
    day = fut[(fut.index.hour >= 6) & (fut.index.hour <= 21)].head(48)
    roll = day[AQI_COL].rolling(2).mean().dropna()
    c = st.columns(4)
    if not roll.empty:
        best_t, worst_t = roll.idxmin(), roll.idxmax()
        c[0].metric("🌿 Best time outdoors", f"{(best_t - pd.Timedelta(hours=1)):%a %I %p}", f"AQI ≈ {roll.min():.0f}",
                    delta_color="off")
        c[1].metric("⚠️ Worst time outdoors", f"{(worst_t - pd.Timedelta(hours=1)):%a %I %p}", f"AQI ≈ {roll.max():.0f}",
                    delta_color="off")
    peak = fut[AQI_COL].idxmax()
    c[2].metric("📈 Forecast peak", f"{fut[AQI_COL].max():.0f}", f"{peak:%a %I %p}", delta_color="off")
    trend = fut[AQI_COL].head(24).mean() - hourly[hourly.index <= now][AQI_COL].tail(24).mean()
    c[3].metric("Next 24 h vs last 24 h", f"{'Worse' if trend > 0 else 'Better'}", f"{trend:+.0f} AQI",
                delta_color="inverse")

    # daily summary cards
    daily = fut.groupby(fut.index.date)[AQI_COL].agg(["mean", "max"])
    cols = st.columns(len(daily))
    for i, (d, row) in enumerate(daily.iterrows()):
        name, col, emo, _ = category(row["mean"], standard)
        cols[i].markdown(f"""<div class="card" style="text-align:center;animation-delay:{.08 * i}s;border-top:3px solid {col}">
          <div class="card-label">{pd.Timestamp(d):%A}</div><div class="muted" style="font-size:.75rem">{pd.Timestamp(d):%d %b}</div>
          <div style="font-size:2rem;margin:.3rem 0">{emo}</div>
          <div style="font-size:1.6rem;font-weight:800;color:{col}">{row['mean']:.0f}</div>
          <div style="font-size:.8rem;color:{col};font-weight:600">{name}</div>
          <div class="muted" style="font-size:.75rem;margin-top:.2rem">peak {row['max']:.0f}</div></div>""",
                         unsafe_allow_html=True)


# ── tab: map ──────────────────────────────────────────────────────────────────
def render_map(token):
    stations = None
    if token:
        try:
            stations = data.waqi_stations(token)
        except Exception as e:
            st.warning(f"Couldn't load WAQI stations ({e}); showing model data instead.")
    if stations is not None and not stations.empty:
        df = stations.rename(columns={"station": "name"})
        df["colour"] = [category(v, "US (EPA)")[1] for v in df["aqi"]]
        df["category"] = [category(v, "US (EPA)")[0] for v in df["aqi"]]
        value_col, title = "aqi", "Live CPCB/DPCC ground stations (US-scale AQI)"
    else:
        df = data.fetch_all_current().rename(columns={"location": "name"})
        value_col = AQI_COL if focus == "AQI" else focus
        df["colour"] = [aqi_colour(v) for v in df[AQI_COL]]
        df["category"] = [category(v, standard)[0] for v in df[AQI_COL]]
        title = f"{'AQI' if focus == 'AQI' else LABEL[focus]} across Delhi localities"
    vals = df[value_col].astype(float)
    size = 14 + 26 * (vals - vals.min()) / ((vals.max() - vals.min()) or 1)
    fig = go.Figure(go.Scattermap(
        lat=df["lat"], lon=df["lon"], mode="markers+text", text=df["name"].str.split(",").str[0],
        textposition="top center", textfont=dict(color="#e2e8f0", size=11),
        marker=dict(size=size, color=df["colour"], opacity=.85),
        customdata=np.stack([df["name"], vals.round(0), df["category"]], axis=-1),
        hovertemplate="<b>%{customdata[0]}</b><br>Value: %{customdata[1]}<br>%{customdata[2]}<extra></extra>"))
    sel = LOCATIONS[location]
    fig.add_trace(go.Scattermap(lat=[sel["lat"]], lon=[sel["lon"]], mode="markers", hoverinfo="skip",
                                marker=dict(size=46, color="rgba(56,189,248,0.25)")))
    fig.update_layout(map=dict(style="carto-darkmatter", center=DELHI_CENTER, zoom=9.6), title=title)
    st.plotly_chart(style_fig(fig, height=560, legend=False), width="stretch", config={"scrollZoom": True, **CHART_CFG})
    if stations is None:
        st.caption("ℹ️ Map uses CAMS atmospheric-model data (~10–40 km grid), so neighbouring localities can share values. "
                   "Add a free WAQI token in the sidebar to plot every live ground monitoring station.")


# ── tab: compare ──────────────────────────────────────────────────────────────
def render_station_ranking(token):
    try:
        stations = data.waqi_stations(token)
    except Exception as e:
        st.warning(f"Live stations unavailable: {e}")
        return
    if stations.empty:
        return
    df = stations.sort_values("aqi")
    df["name"] = df["station"].str.split(",").str[0]
    fig = go.Figure(go.Bar(y=df["name"], x=df["aqi"], orientation="h", text=df["aqi"].round(0), textposition="outside",
                           marker_color=[category(v, "US (EPA)")[1] for v in df["aqi"]],
                           hovertemplate="%{y}: US AQI %{x:.0f}<extra></extra>"))
    fig.update_layout(title=f"🛰️ Live ground stations right now ({len(df)}) · US-scale AQI", hovermode="closest")
    st.plotly_chart(style_fig(fig, height=max(420, 24 * len(df)), legend=False), width="stretch", config=CHART_CFG)


def render_compare():
    token = data.waqi_token()
    if token:
        render_station_ranking(token)
        st.caption("Below: the model estimate for each tracked locality, which also drives the forecasts.")
    df = data.fetch_all_current()
    metric = AQI_COL if focus == "AQI" else focus
    unit = "AQI" if focus == "AQI" else POLLUTANTS[focus]["unit"]
    df = df.sort_values(metric, ascending=True)
    colours = [aqi_colour(v) for v in df[AQI_COL]]
    a, b = st.columns([1.5, 1], gap="large")
    with a:
        fig = go.Figure(go.Bar(y=df["location"], x=df[metric], orientation="h", marker_color=colours,
                               text=df[metric].round(0), textposition="outside",
                               hovertemplate="%{y}: %{x:.1f} " + unit + "<extra></extra>"))
        fig.update_layout(title=f"Localities ranked by {'AQI' if focus == 'AQI' else LABEL[focus]}", hovermode="closest")
        st.plotly_chart(style_fig(fig, height=max(420, 26 * len(df)), legend=False), width="stretch", config=CHART_CFG)
    with b:
        zone_avg = df.groupby("zone")[metric].mean().sort_values()
        fig = go.Figure(go.Bar(x=zone_avg.index, y=zone_avg.values, marker_color=[aqi_colour(v) for v in
                                                                                  df.groupby("zone")[AQI_COL].mean().reindex(zone_avg.index)]))
        fig.update_layout(title="Average by zone", hovermode="closest")
        st.plotly_chart(style_fig(fig, height=300, legend=False), width="stretch", config=CHART_CFG)
        best, worst = df.iloc[0], df.iloc[-1]
        st.markdown(f"""<div class="card"><div class="card-label">Cleanest right now</div>
          <div style="font-weight:700;font-size:1.2rem;color:#4ade80">🌿 {best['location']} · {best[metric]:.0f}</div>
          <div class="card-label" style="margin-top:.8rem">Most polluted right now</div>
          <div style="font-weight:700;font-size:1.2rem;color:#f87171">🏭 {worst['location']} · {worst[metric]:.0f}</div></div>""",
                    unsafe_allow_html=True)
    table = df[["location", "zone", AQI_COL] + AQI_POLLUTANTS].sort_values(AQI_COL, ascending=False)
    st.dataframe(table.rename(columns={**LABEL, AQI_COL: "AQI", "location": "Locality", "zone": "Zone"}),
                 hide_index=True, width="stretch",
                 column_config={"AQI": st.column_config.ProgressColumn("AQI", min_value=0, max_value=500, format="%d")})


# ── tab: health ───────────────────────────────────────────────────────────────
def render_health(level):
    level = max(level, 0)
    h = HEALTH[level]
    name, col, emo, _ = category([25, 75, 150, 250, 350, 450][level], "India (CPCB)")
    st.markdown(f"""<div class="card" style="border-left:4px solid {col};margin-bottom:1rem">
      <div class="card-label">Current level (CPCB)</div>
      <div style="font-size:1.6rem;font-weight:800;color:{col}">{emo} {name}</div>
      <div style="margin-top:.3rem">{h['impact']}</div></div>""", unsafe_allow_html=True)
    st.markdown(f"""<div class="rec-grid">
      <div class="card rec"><div class="ic">😷</div><div class="card-label">Mask</div><div class="v">{h['mask']}</div></div>
      <div class="card rec" style="animation-delay:.08s"><div class="ic">🏃</div><div class="card-label">Outdoor activity</div><div class="v">{h['outdoor']}</div></div>
      <div class="card rec" style="animation-delay:.16s"><div class="ic">🌀</div><div class="card-label">Air purifier</div><div class="v">{h['purifier']}</div></div>
      <div class="card rec" style="animation-delay:.24s"><div class="ic">🪟</div><div class="card-label">Windows</div><div class="v">{h['windows']}</div></div>
    </div>""", unsafe_allow_html=True)
    st.write("")
    a, b = st.columns(2, gap="large")
    tips = lambda items, ic: "".join(f'<div class="tip"><span class="ic">{ic}</span><span>{tip}</span></div>' for tip in items)
    with a:
        st.markdown(f'<div class="card"><div class="card-label">Everyone</div>{tips(h["general"], "✅")}</div>',
                    unsafe_allow_html=True)
    with b:
        extra = PERSONA_TIPS.get(persona, [])
        st.markdown(f'<div class="card"><div class="card-label">Sensitive groups · {persona}</div>'
                    f'{tips(h["sensitive"] + extra, "🩺")}</div>', unsafe_allow_html=True)
    st.write("")
    st.markdown("##### 🚨 Symptoms that need medical attention")
    st.markdown('<div class="card">' + tips([
        "Persistent cough, wheezing or chest tightness", "Shortness of breath even at rest",
        "Chest pain, irregular heartbeat or palpitations", "Unusual fatigue, dizziness or headache",
        "Burning eyes, nose or throat that doesn't settle indoors"], "⚠️") + "</div>", unsafe_allow_html=True)


# ── tab: planner ──────────────────────────────────────────────────────────────
def render_planner(future, now):
    st.markdown(f"##### 🗓️ {t('Plan the cleanest time to go outside')}")
    c1, c2, c3, c4 = st.columns([1.3, 1, 1, 1.4])
    act = c1.selectbox(t("Activity"), list(ACTIVITIES), key="pl_act")
    mins = c2.select_slider(t("Duration"), [15, 30, 45, 60, 90, 120, 180], value=45, key="pl_min",
                            format_func=lambda m: f"{m} min" if m < 60 else f"{m / 60:g} h")
    when = c3.selectbox(t("When"), ["Today", "Tomorrow", "Next 48 h"], key="pl_when", format_func=t)
    hrs = c4.slider(t("Earliest / latest hour"), 0, 24, (6, 21), key="pl_hrs", format="%d:00")
    fut = future.copy()
    if when == "Today":
        fut = fut[fut.index.date == now.date()]
    elif when == "Tomorrow":
        fut = fut[fut.index.date == (now + pd.Timedelta(days=1)).date()]
    else:
        fut = fut.head(48)
    prof = ACTIVITIES[act]
    slots, cands = find_slots(fut, AQI_COL, mins, hrs[0], hrs[1])
    if not slots:
        st.info("No slots fit those hours in the forecast — widen the time range or pick another day.")
        return
    ok = prof["ok"] if standard == "India (CPCB)" else prof["ok"] * 0.75
    worst = max(cands, key=lambda c: c["pm25"])
    cols = st.columns(len(slots))
    for i, (col, sl) in enumerate(zip(cols, slots)):
        v_txt, v_col = verdict(sl["aqi"], ok)
        dose = dose_ug(sl["pm25"], mins, prof["rate"])
        col.markdown(compact(f"""<div class="card" style="text-align:center;animation-delay:{.08 * i}s">
          <div class="card-label" style="justify-content:center">{'🥇🥈🥉'[i]} #{i + 1}</div>
          <div style="font-size:1.6rem;font-weight:600;margin-top:.3rem">{sl['start']:%a %-I:%M %p}</div>
          <div class="muted" style="font-size:.8rem">until {sl['end']:%-I:%M %p}</div>
          <div style="font-size:2.4rem;font-weight:300;color:{aqi_colour(sl['aqi'])};margin:.3rem 0">{sl['aqi']:.0f}</div>
          <div style="font-weight:700;color:{v_col}">{v_txt}</div>
          <div class="muted" style="font-size:.78rem;margin-top:.4rem">PM2.5 {sl['pm25']:.0f} µg/m³ · ≈ {dose:,.0f} µg inhaled</div></div>"""),
                     unsafe_allow_html=True)
    best = slots[0]
    saved = 1 - dose_ug(best["pm25"], mins, prof["rate"]) / max(1e-6, dose_ug(worst["pm25"], mins, prof["rate"]))
    st.markdown(compact(f"""<div class="card" style="margin-top:1rem"><div class="summary">
      Going at <b>{best['start']:%a %-I %p}</b> instead of the worst slot (<b>{worst['start']:%a %-I %p}</b>, PM2.5 {worst['pm25']:.0f} µg/m³)
      cuts the PM2.5 you breathe in by <b>{saved:.0%}</b>. {act.split(' ', 1)[1]} breathes roughly
      <b>{prof['rate']:.1f} m³ of air per hour</b>{' — about 6× more than resting' if prof['rate'] >= 2.5 else ''}.</div></div>"""),
                unsafe_allow_html=True)
    fig = go.Figure(go.Bar(x=fut.index, y=fut["pm2_5"], marker_color=[category(sub_index("pm2_5", v), "India (CPCB)")[1] for v in fut["pm2_5"]],
                           marker_line_width=0, opacity=.85, name="PM2.5"))
    for i, sl in enumerate(slots):
        fig.add_vrect(x0=sl["start"], x1=sl["end"], fillcolor="rgba(255,255,255,.18)", line_width=1.5,
                      line_color="#fff", annotation_text=f"#{i + 1}", annotation_position="top left",
                      annotation_font_color="#fff")
    fig.add_hline(y=15, line_dash="dot", line_color="#4ade80", annotation_text="WHO guideline", annotation_font_color="#4ade80")
    fig.update_layout(title="Hourly PM2.5 forecast (µg/m³) with your best slots", bargap=.12)
    st.plotly_chart(style_fig(fig, height=320, legend=False), width="stretch", config=CHART_CFG)


# ── tab: why ──────────────────────────────────────────────────────────────────
def render_causes(hourly, now, weather):
    st.markdown(f"##### 🔎 {t('Why is the air like this?')}")
    try:
        fires = fetch_fires()
    except Exception as e:
        fires = None
        st.caption(f"Fire data unavailable: {e}")
    factors, facts = analyse(hourly, now, weather, fires)
    top = [f for f in factors if f["score"] >= .25] or factors[:1]
    st.markdown(compact(f"""<div class="card" style="margin-bottom:1rem"><div class="summary">
      Main drivers right now: <b>{', '.join(f['title'].lower() for f in top[:3])}</b>.<br>
      <span class="muted">🗓️ {facts['season']}</span></div></div>"""), unsafe_allow_html=True)
    cards = []
    for i, f in enumerate(factors):
        lvl = "High" if f["score"] >= .6 else "Medium" if f["score"] >= .3 else "Low"
        colr = "#f87171" if f["score"] >= .6 else "#fb923c" if f["score"] >= .3 else "#4ade80"
        cards.append(f"""<div class="card" style="animation-delay:{.05 * i:.2f}s">
          <div style="display:flex;align-items:center;gap:.6rem"><span style="font-size:1.8rem">{f['icon']}</span>
          <div style="flex:1"><div style="font-weight:700">{f['title']}</div><div class="muted" style="font-size:.75rem">{f['evidence']}</div></div>
          <span class="chip" style="margin:0;background:{colr}33;color:{colr}">{lvl}</span></div>
          <div class="bar"><span style="width:{max(3, f['score'] * 100):.0f}%;background:{colr};box-shadow:0 0 10px {colr}"></span></div>
          <div style="font-size:.86rem;margin-top:.7rem;line-height:1.45">{f['text']}</div></div>""")
    st.markdown(compact('<div class="tiles" style="grid-template-columns:repeat(auto-fit,minmax(280px,1fr))">' + "".join(cards) + "</div>"),
                unsafe_allow_html=True)
    if fires is not None and not fires.empty:
        fig = go.Figure(go.Scattermap(lat=fires["latitude"], lon=fires["longitude"], mode="markers",
                                      marker=dict(size=(4 + fires["frp"].clip(0, 60) / 6).tolist(), color="#ff5a1f", opacity=.75),
                                      hovertemplate="Fire · %{lat:.2f}, %{lon:.2f}<extra></extra>", name="Fires"))
        fig.add_trace(go.Scattermap(lat=[DELHI_CENTER["lat"]], lon=[DELHI_CENTER["lon"]], mode="markers+text", text=["Delhi"],
                                    textposition="bottom center", textfont=dict(color="#fff", size=13),
                                    marker=dict(size=18, color="#7dd3fc"), hoverinfo="skip"))
        wd = facts["wdir"]
        if wd == wd:  # not NaN: arrow showing where the wind blows FROM toward Delhi
            import math as _m
            rad = _m.radians(wd)
            src = (DELHI_CENTER["lat"] + 1.6 * _m.cos(rad), DELHI_CENTER["lon"] + 1.6 * _m.sin(rad) / _m.cos(_m.radians(28.6)))
            fig.add_trace(go.Scattermap(lat=[src[0], DELHI_CENTER["lat"]], lon=[src[1], DELHI_CENTER["lon"]], mode="lines",
                                        line=dict(width=4, color="rgba(255,255,255,.8)"), hoverinfo="skip"))
        fig.update_layout(map=dict(style="carto-darkmatter", center={"lat": 29.9, "lon": 76.2}, zoom=5.6),
                          title=f"🔥 {len(fires):,} fire hotspots in the last 24 h (NASA VIIRS) · white line = wind toward Delhi")
        st.plotly_chart(style_fig(fig, height=480, legend=False), width="stretch", config={"scrollZoom": True, **CHART_CFG})


# ══════════════════════════════════════════════════════════════════════════════
# Compare two places
# ══════════════════════════════════════════════════════════════════════════════
def render_compare_places():
    st.markdown(f"<h2 class='hero-title' style='font-size:1.8rem'>⚖️ {t('Compare two places')}</h2>"
                "<div class='hero-sub'>Home vs office, school vs park — see which has cleaner air now and ahead.</div>",
                unsafe_allow_html=True)
    st.write("")
    names = list(LOCATIONS)
    c1, c2 = st.columns(2)
    a = c1.selectbox(t("Place A"), names, index=names.index(location), key="cmp_a")
    b = c2.selectbox(t("Place B"), names, index=names.index("Dwarka Sector 8") if location != "Dwarka Sector 8" else 0, key="cmp_b")
    now = now_ist().floor("h")
    frames = {}
    for n in (a, b):
        try:
            frames[n] = data.fetch_hourly(LOCATIONS[n]["lat"], LOCATIONS[n]["lon"])
        except Exception as e:
            st.error(f"{n}: {e}")
            return
    cols = st.columns(2, gap="medium")
    cur = {}
    for col, n, accent in zip(cols, (a, b), ("#7dd3fc", "#f9a8d4")):
        df = frames[n]
        row = df[df.index <= now].iloc[-1]
        cur[n] = row
        name, c, emo, _ = category(row[AQI_COL], standard)
        nxt = df[df.index > now].head(24)[AQI_COL]
        col.markdown(compact(f"""<div class="card" style="text-align:center;box-shadow:inset 0 3px 0 {accent}">
          <div class="hero-zone">📍 {LOCATIONS[n]['zone']} Delhi</div><div class="hero-loc" style="font-size:1.6rem">{n}</div>
          <div style="font-size:4.5rem;font-weight:200;line-height:1.05;color:{c}">{row[AQI_COL]:.0f}</div>
          <div class="hero-cat" style="font-size:1.1rem">{emo} {t(name)}</div>
          <div class="muted" style="margin-top:.4rem;font-size:.85rem">Next 24 h: {nxt.min():.0f} – {nxt.max():.0f} · PM2.5 {row['pm2_5']:.0f} µg/m³</div>
          </div>"""), unsafe_allow_html=True)
    va, vb = cur[a][AQI_COL], cur[b][AQI_COL]
    if abs(va - vb) < 3:
        verdict_txt = f"<b>{a}</b> and <b>{b}</b> have about the same air right now."
    else:
        win, lose = (a, b) if va < vb else (b, a)
        verdict_txt = f"<b>{win}</b> is cleaner right now by <b>{abs(va - vb):.0f}</b> AQI points ({abs(va - vb) / max(va, vb):.0%} lower) than {lose}."
    fa = frames[a][frames[a].index > now].head(48)[AQI_COL].mean()
    fb = frames[b][frames[b].index > now].head(48)[AQI_COL].mean()
    verdict_txt += f" Over the next 48 h, {a if fa < fb else b} is expected to be cleaner on average ({min(fa, fb):.0f} vs {max(fa, fb):.0f})."
    st.markdown(compact(f'<div class="card" style="margin:1rem 0"><div class="summary">⚖️ {verdict_txt}</div></div>'), unsafe_allow_html=True)
    fig = go.Figure()
    for n, colr in zip((a, b), ("#7dd3fc", "#f9a8d4")):
        df = frames[n]
        w = df[(df.index > now - pd.Timedelta(hours=72)) & (df.index <= now + pd.Timedelta(hours=48))]
        fig.add_trace(go.Scatter(x=w.index, y=w[AQI_COL], name=n, mode="lines", line=dict(width=3, shape="spline", color=colr)))
    fig.add_vline(x=now, line_dash="dot", line_color="rgba(255,255,255,.6)")
    fig.update_layout(title="AQI · last 72 h and next 48 h")
    st.plotly_chart(style_fig(fig, height=360), width="stretch", config=CHART_CFG)
    rows = []
    for k in ALL_POLLUTANTS:
        x, y = cur[a].get(k), cur[b].get(k)
        diff = (x - y) if x is not None and y is not None else None
        rows.append({"Pollutant": f"{LABEL[k]} ({POLLUTANTS[k]['unit']})", a: round(x, 1) if x is not None else None,
                     b: round(y, 1) if y is not None else None,
                     "Difference": "same" if diff is None or abs(diff) < .05 else f"{a if diff < 0 else b} lower by {abs(diff):,.1f}"})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    if a == b or abs(va - vb) < 1:
        st.caption("ℹ️ The free model data is on a coarse grid, so nearby localities can be identical. "
                   "Add a WAQI token in the sidebar for station-level differences.")


# ══════════════════════════════════════════════════════════════════════════════
# My exposure: daily score + streaks
# ══════════════════════════════════════════════════════════════════════════════
def _ring(score, colour):
    r, c = 70, 2 * 3.14159 * 70
    return (f'<svg viewBox="0 0 170 170" width="170" height="170"><circle cx="85" cy="85" r="{r}" fill="none" '
            f'stroke="rgba(255,255,255,.12)" stroke-width="14"/><circle cx="85" cy="85" r="{r}" fill="none" stroke="{colour}" '
            f'stroke-width="14" stroke-linecap="round" stroke-dasharray="{c * score / 100:.1f} {c:.1f}" transform="rotate(-90 85 85)" '
            f'style="filter:drop-shadow(0 0 8px {colour});animation:ringdraw 1.6s cubic-bezier(.2,.8,.2,1) both"/>'
            f'<text x="85" y="95" text-anchor="middle" font-size="44" font-weight="300" fill="#fff">{score}</text></svg>')


def render_exposure():
    st.markdown(f"<h2 class='hero-title' style='font-size:1.8rem'>🫁 {t('Your daily clean-air score')}</h2>"
                "<div class='hero-sub'>Log the time you spend outdoors — the app works out how much polluted air you breathed.</div>",
                unsafe_allow_html=True)
    st.markdown("<style>@keyframes ringdraw { from { stroke-dasharray: 0 999; } }</style>", unsafe_allow_html=True)
    st.write("")
    db = hl.load()
    today = now_ist().date()   # Delhi's date, not this computer's
    s_today = hl.day_summary(db, today.isoformat())
    cur_streak, best_streak = hl.streaks(db, today)
    left, mid, right = st.columns([1, 1, 1.2], gap="medium")
    with left:
        sc = s_today["score"] if s_today else 0
        colr = "#4ade80" if sc >= 75 else "#facc15" if sc >= hl.GOOD_SCORE else "#fb923c" if sc >= 40 else "#f87171"
        st.markdown(compact(f"""<div class="card" style="text-align:center"><div class="card-label" style="justify-content:center">Today</div>
          {_ring(sc, colr) if s_today else '<div style="padding:2.2rem 0;font-size:3rem">🫥</div>'}
          <div class="muted" style="font-size:.85rem">{'Log some time outdoors to get a score' if not s_today else
            f"≈ {s_today['cig']:.1f} cigarettes · {s_today['outdoor_min'] / 60:.1f} h outdoors"}</div></div>"""), unsafe_allow_html=True)
    with mid:
        badges = "".join(f'<span class="chip" style="font-size:.8rem;{"" if best_streak >= n else "opacity:.35"}">{ic} {lab}</span> '
                         for n, ic, lab in hl.BADGES)
        st.markdown(compact(f"""<div class="card" style="text-align:center"><div class="card-label" style="justify-content:center">{t('Streak')}</div>
          <div style="font-size:3.4rem;margin-top:.6rem">{'🔥' if cur_streak else '🌱'}</div>
          <div style="font-size:2.4rem;font-weight:300">{cur_streak} day{'s' if cur_streak != 1 else ''}</div>
          <div class="muted" style="font-size:.8rem">Best: {best_streak} · days scoring {hl.GOOD_SCORE}+ count</div>
          <div style="margin-top:.6rem">{badges}</div></div>"""), unsafe_allow_html=True)
    with right:
        with st.form("log_form", clear_on_submit=True, border=False):
            st.markdown(f"**➕ {t('Log time outdoors')}**")
            f1, f2 = st.columns(2)
            d = f1.date_input("Day", value=today, min_value=today - timedelta(days=60), max_value=today)
            start = f2.time_input("Start", value=pd.Timestamp("2000-01-01 08:00").time(), step=900)
            f3, f4 = st.columns(2)
            mins = f3.number_input("Minutes", 5, 720, 60, step=5)
            loc = f4.selectbox("Where", list(LOCATIONS), index=list(LOCATIONS).index(location))
            act = st.selectbox("Doing", list(ACTIVITIES) + ["🧍 Other / errands"])
            if st.form_submit_button(t("Add"), width="stretch"):
                try:
                    lat, lon = LOCATIONS[loc]["lat"], LOCATIONS[loc]["lon"]
                    hrs = data.fetch_hourly(lat, lon) if (today - d).days <= 2 else data.fetch_history(lat, lon, d, d)
                    day_df = hrs[hrs.index.date == d]
                    t0 = pd.Timestamp.combine(d, start).floor("h")
                    win = day_df[(day_df.index >= t0) & (day_df.index < t0 + pd.Timedelta(minutes=int(mins)) + pd.Timedelta(minutes=59))]
                    win = win if not win.empty else day_df
                    hl.add_entry(db, day=d, start=start.strftime("%H:%M"), minutes=mins, location=loc, activity=act,
                                 pm25=win["pm2_5"].mean(), aqi=win["in_aqi"].mean(), day_pm25=day_df["pm2_5"].mean())
                    st.toast(f"Logged {mins} min at {loc} ✅")
                    st.rerun()
                except Exception as e:
                    st.error(f"Couldn't look up air data for that time: {e}")
    pur = st.toggle("I run an air purifier at home (lowers indoor exposure)", value=db.get("purifier", False))
    if pur != db.get("purifier", False):
        db["purifier"] = pur
        hl.save(db)
        st.rerun()

    days = [today - timedelta(days=i) for i in range(13, -1, -1)]
    sums = [hl.day_summary(db, x.isoformat()) for x in days]
    fig = go.Figure(go.Bar(x=[x.strftime("%a %d") for x in days], y=[s["score"] if s else 0 for s in sums],
                           marker_color=["#4ade80" if s and s["score"] >= 75 else "#facc15" if s and s["score"] >= hl.GOOD_SCORE
                                         else "#fb923c" if s and s["score"] >= 40 else "#f87171" if s else "rgba(255,255,255,.15)"
                                         for s in sums],
                           text=[s["score"] if s else "" for s in sums], textposition="outside", marker_line_width=0))
    fig.add_hline(y=hl.GOOD_SCORE, line_dash="dot", line_color="#fff", annotation_text="streak line", annotation_font_color="#fff")
    fig.update_layout(title="Last 14 days", yaxis_range=[0, 110], hovermode="closest")
    st.plotly_chart(style_fig(fig, height=300, legend=False), width="stretch", config=CHART_CFG)

    if db["entries"]:
        st.markdown("##### Your log")
        for e in sorted(db["entries"], key=lambda e: (e["day"], e["start"]), reverse=True)[:30]:
            c1, c2 = st.columns([12, 1])
            c1.markdown(compact(f"""<div class="card" style="padding:.7rem 1rem;margin-bottom:.4rem;display:flex;gap:1rem;align-items:center">
              <b style="min-width:6.5rem">{pd.Timestamp(e['day']):%a %d %b}</b><span>{e['start']} · {e['minutes']} min</span>
              <span>{e['activity']}</span><span class="muted">📍 {e['location']}</span>
              <span style="margin-left:auto;color:{category(e['aqi'], 'India (CPCB)')[1]};font-weight:700">AQI {e['aqi']:.0f}</span>
              <span class="muted">PM2.5 {e['pm25']:.0f}</span></div>"""), unsafe_allow_html=True)
            if c2.button("🗑️", key=f"del_{e['id']}", help="Delete this entry"):
                hl.delete_entry(db, e["id"])
                st.rerun()
    st.caption("How the score works: outdoor time uses the forecast/archived PM2.5 at that place and hour; indoor air is assumed "
               "at 65% of outdoor (30% with a purifier). 100 = clean air all day, 60+ keeps your streak going. "
               "Entries are saved on this computer in my_exposure.json.")


# ══════════════════════════════════════════════════════════════════════════════
# History explorer (not on the timer)
# ══════════════════════════════════════════════════════════════════════════════
def render_history():
    st.markdown("<h2 class='hero-title' style='font-size:1.8rem'>📅 History explorer</h2>"
                "<div class='hero-sub'>Look up air quality for any past date (since Aug 2022) and any locality.</div>",
                unsafe_allow_html=True)
    st.write("")
    today = date.today()
    c1, c2, c3 = st.columns([1.6, 1.2, 1])
    with c1:
        locs = st.multiselect("Localities (up to 4)", list(LOCATIONS), default=[location], max_selections=4,
                              key="hist_locs")
    with c2:
        rng = st.date_input("Date range", value=(today - timedelta(days=30), today - timedelta(days=1)),
                            min_value=data.HISTORY_START, max_value=today, key="hist_range")
    with c3:
        hist_metric = st.selectbox("Show", ["AQI"] + ALL_POLLUTANTS, key="hist_metric",
                                   index=(["AQI"] + ALL_POLLUTANTS).index(focus),
                                   format_func=lambda k: "Overall AQI" if k == "AQI" else LABEL[k])
    presets = {"Diwali 2025": (date(2025, 10, 18), date(2025, 10, 25)),
               "Diwali 2024": (date(2024, 10, 28), date(2024, 11, 4)),
               "Winter smog Nov 2024": (date(2024, 11, 10), date(2024, 11, 25)),
               "Monsoon Jul 2025": (date(2025, 7, 1), date(2025, 7, 31))}
    preset = st.pills("Quick picks", list(presets), key="hist_preset")
    if preset:
        rng = presets[preset]
    yoy = st.toggle("Overlay the same dates one year earlier", key="hist_yoy")

    if not locs or not isinstance(rng, (tuple, list)) or len(rng) != 2:
        st.info("Pick at least one locality and a start and end date.")
        return
    start, end = rng
    if (end - start).days > 366:
        st.warning("Please choose a range of one year or less.")
        return

    col_name = AQI_COL if hist_metric == "AQI" else hist_metric
    unit = "AQI" if hist_metric == "AQI" else POLLUTANTS[hist_metric]["unit"]
    frames = {}
    with st.spinner("Fetching archive data…"):
        for loc in locs:
            try:
                frames[loc] = data.fetch_history(LOCATIONS[loc]["lat"], LOCATIONS[loc]["lon"], start, end)
            except Exception as e:
                st.error(f"{loc}: {e}")
    if not frames:
        return

    hourly_mode = (end - start).days <= 10
    fig = go.Figure()
    for i, (loc, df) in enumerate(frames.items()):
        s = df[col_name] if hourly_mode else df[col_name].resample("D").mean()
        fig.add_trace(go.Scatter(x=s.index, y=s.values, name=loc, mode="lines",
                                 line=dict(width=2.5, shape="spline")))
    if yoy and start - timedelta(days=365) >= data.HISTORY_START:
        loc0 = locs[0]
        prev = data.fetch_history(LOCATIONS[loc0]["lat"], LOCATIONS[loc0]["lon"],
                                  start - timedelta(days=365), end - timedelta(days=365))
        s = prev[col_name] if hourly_mode else prev[col_name].resample("D").mean()
        s.index = s.index + pd.Timedelta(days=365)
        fig.add_trace(go.Scatter(x=s.index, y=s.values, name=f"{loc0} · year before", mode="lines",
                                 line=dict(width=2, dash="dot", color="#94a3b8")))
    if hist_metric == "AQI":
        aqi_band_shapes(fig, max(100, max(float(df[col_name].max() or 0) for df in frames.values()) * 1.1))
    fig.update_layout(title=f"{'Hourly' if hourly_mode else 'Daily average'} {LABEL[hist_metric]} ({unit})"
                            f" · {start:%d %b %Y} → {end:%d %b %Y}")
    st.plotly_chart(style_fig(fig, height=420), width="stretch", config=CHART_CFG)

    # summary stats per locality
    stat_cols = st.columns(len(frames))
    for i, (loc, df) in enumerate(frames.items()):
        daily = df[AQI_COL].resample("D").mean()
        worst_day = daily.idxmax()
        name, col, emo, _ = category(daily.mean(), standard)
        stat_cols[i].markdown(f"""<div class="card" style="border-top:3px solid {col};animation-delay:{.08 * i}s">
          <div class="card-label">{loc}</div>
          <div style="font-size:1.8rem;font-weight:800;color:{col}">{daily.mean():.0f} <span class="card-unit">avg AQI</span></div>
          <div class="muted" style="font-size:.8rem">{emo} {name} on average</div>
          <div style="margin-top:.6rem;font-size:.85rem">Worst day: <b>{worst_day:%d %b %Y}</b> ({daily.max():.0f})<br>
          Best day: <b>{daily.idxmin():%d %b %Y}</b> ({daily.min():.0f})<br>
          Avg PM2.5: <b>{df['pm2_5'].mean():.0f} µg/m³</b> ({df['pm2_5'].mean() / 15:.1f}× WHO)</div></div>""",
                              unsafe_allow_html=True)

    a, b = st.columns([1.4, 1], gap="large")
    with a:
        # calendar-style heatmap of daily AQI
        loc0 = locs[0]
        daily = frames[loc0][AQI_COL].resample("D").mean().to_frame("aqi")
        daily["week"] = daily.index.to_period("W-SUN").start_time
        daily["dow"] = daily.index.dayofweek
        piv = daily.pivot_table(index="dow", columns="week", values="aqi")
        fig = go.Figure(go.Heatmap(z=piv.values, x=piv.columns, y=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                                   xgap=3, ygap=3, colorscale=[[0, "#00b050"], [.2, "#92d050"], [.4, "#f5c518"],
                                                               [.6, "#ff8c00"], [.8, "#e5232b"], [1, "#8b1a1a"]],
                                   zmin=0, zmax=500, colorbar=dict(thickness=10),
                                   hovertemplate="Week of %{x|%d %b}<br>%{y}: AQI %{z:.0f}<extra></extra>"))
        fig.update_layout(title=f"Daily AQI calendar · {loc0}")
        st.plotly_chart(style_fig(fig, height=300, legend=False), width="stretch", config=CHART_CFG)
    with b:
        # days per category
        rows = []
        for loc, df in frames.items():
            daily = df[AQI_COL].resample("D").mean().dropna()
            for v in daily:
                rows.append({"Locality": loc, "Category": category(v, standard)[0]})
        cdf = pd.DataFrame(rows)
        order = [c[1] for c in CATS]
        fig = px.histogram(cdf, x="Locality", color="Category", category_orders={"Category": order},
                           color_discrete_map={c[1]: c[2] for c in CATS}, barmode="stack")
        fig.update_layout(title="Days in each AQI category", hovermode="closest", yaxis_title="days", xaxis_title=None)
        st.plotly_chart(style_fig(fig, height=300), width="stretch", config=CHART_CFG)

    # point-in-time lookup
    st.markdown("##### 🔎 Look up a specific day & hour")
    d1, d2 = st.columns([1, 1])
    with d1:
        pick_day = st.date_input("Day", value=start, min_value=start, max_value=end, key="hist_day")
    with d2:
        pick_hour = st.slider("Hour", 0, 23, 9, format="%d:00", key="hist_hour")
    ts = pd.Timestamp(pick_day) + pd.Timedelta(hours=pick_hour)
    snap = []
    for loc, df in frames.items():
        if ts in df.index:
            r = df.loc[ts]
            snap.append({"Locality": loc, "AQI": r[AQI_COL], "Category": category(r[AQI_COL], standard)[0],
                         **{LABEL[p]: r[p] for p in ALL_POLLUTANTS}})
    if snap:
        st.dataframe(pd.DataFrame(snap).round(1), hide_index=True, width="stretch")

    export = pd.concat({loc: df[[AQI_COL] + ALL_POLLUTANTS] for loc, df in frames.items()}, names=["locality", "time"])
    st.download_button("⬇️ Download this data (CSV)", export.to_csv().encode(), file_name=f"delhi_aqi_{start}_{end}.csv",
                       mime="text/csv")


# ══════════════════════════════════════════════════════════════════════════════
# Learn
# ══════════════════════════════════════════════════════════════════════════════
def render_learn():
    st.markdown(compact("""<div class="card" style="text-align:center;padding:1.8rem 1.4rem;margin-bottom:1.4rem">
      <div class="brand-name" style="font-size:2.6rem;letter-spacing:-.03em"><span class="a">AQI</span><span class="f">fy</span><span class="m">Me</span></div>
      <div style="display:flex;justify-content:center;gap:.8rem;flex-wrap:wrap;margin:1rem 0">
        <span class="chip" style="font-size:.85rem;padding:.35rem .8rem"><b>AQI</b> · the air you breathe</span>
        <span class="chip" style="font-size:.85rem;padding:.35rem .8rem"><b>-fy</b> · as in veri<b>fy</b></span>
        <span class="chip" style="font-size:.85rem;padding:.35rem .8rem"><b>Me</b> · for you</span></div>
      <div class="summary">Verified air-quality information, made for you: live readings, forecasts, causes and
      health advice for 25 Delhi localities, in one place. Tap the logo in the sidebar to replay the intro.</div></div>"""),
                unsafe_allow_html=True)
    st.markdown("<h2 class='hero-title' style='font-size:1.8rem'>📚 Understand the air you breathe</h2>", unsafe_allow_html=True)
    st.write("")
    st.markdown("##### The AQI scales")
    st.caption("India (CPCB) National AQI")
    st.markdown(scale_html(categories("India (CPCB)"), -1, None, CATEGORY_DESC), unsafe_allow_html=True)
    st.caption("US EPA AQI")
    st.markdown(scale_html(categories("US (EPA)"), -1, None, CATEGORY_DESC), unsafe_allow_html=True)
    st.caption("The CPCB AQI here is computed from 24-hour averages of PM2.5, PM10, NO₂ & SO₂ and 8-hour averages of "
               "CO & O₃. The overall AQI is the worst pollutant sub-index.")

    st.markdown("##### The pollutants")
    cols = st.columns(2, gap="large")
    for i, (k, m) in enumerate(POLLUTANTS.items()):
        with cols[i % 2].expander(f"**{m['label']}** — {m['name']}"):
            st.markdown(f"**Sources:** {m['sources']}\n\n**Health effects:** {m['effects']}")
            limits = []
            if m.get("who"):
                limits.append(f"WHO guideline: **{m['who']} {m['unit']}**")
            if m.get("naaqs"):
                limits.append(f"India NAAQS: **{m['naaqs']} {m['unit']}**")
            if limits:
                st.markdown(" · ".join(limits))

    st.markdown("##### 🚦 GRAP — Delhi's Graded Response Action Plan")
    cols = st.columns(4)
    for i, (stage, rng, col, desc) in enumerate(GRAP_STAGES):
        cols[i].markdown(f"""<div class="card" style="border-top:3px solid {col};animation-delay:{.08 * i}s">
          <div style="font-weight:800;color:{col}">{stage}</div><div class="card-label">{rng}</div>
          <div style="font-size:.85rem;margin-top:.5rem">{desc}</div></div>""", unsafe_allow_html=True)

    st.markdown("##### 🌱 What you can do")
    tips = [("🚇", "Use the Metro, buses or carpool — vehicles are Delhi's biggest year-round PM2.5 source."),
            ("🔥", "Never burn leaves or garbage; report open burning on the Green Delhi app."),
            ("🎆", "Celebrate a cracker-free Diwali — PM2.5 can jump 5–10× overnight."),
            ("🪴", "Indoor plants help a little, but a HEPA purifier is what actually cleans indoor air."),
            ("🚗", "Keep your PUC certificate valid and switch off the engine at red lights."),
            ("🏗️", "Report construction sites that don't cover materials or sprinkle water.")]
    cols = st.columns(3)
    for i, (ic, t) in enumerate(tips):
        cols[i % 3].markdown(f'<div class="card" style="margin-bottom:.8rem;animation-delay:{.05 * i}s">'
                             f'<div style="font-size:1.6rem">{ic}</div><div style="margin-top:.3rem">{t}</div></div>',
                             unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Page layout
# ══════════════════════════════════════════════════════════════════════════════
VIEWS = ["🌍 Live", "⚖️ Compare", "🫁 My exposure", "📅 History", "📚 Learn"]
view = st.segmented_control("View", VIEWS, default="🌍 Live", label_visibility="collapsed", key="view",
                            format_func=t) or "🌍 Live"

if view == "🌍 Live":
    st.fragment(run_every=f"{every}m" if auto else None)(render_live)()
else:
    try:  # sky reflects the selected locality's current air on the other pages too
        _h = data.fetch_hourly(LOC["lat"], LOC["lon"])
        sky_for(category(_h[_h.index <= now_ist().floor("h")].iloc[-1]["in_aqi"], "India (CPCB)")[3])
    except Exception:
        sky_for(2)
    {"⚖️ Compare": render_compare_places, "🫁 My exposure": render_exposure, "📅 History": render_history,
     "📚 Learn": render_learn}[view]()

st.markdown("""<div class="footer">
  <b>AQIfyMe</b> · verified air-quality information, made for you<br>
  Data: <a href="https://open-meteo.com/en/docs/air-quality-api" target="_blank">Open-Meteo</a> ·
  Copernicus Atmosphere Monitoring Service (CAMS) · weather by Open-Meteo ·
  optional live stations via <a href="https://aqicn.org" target="_blank">WAQI</a>.<br>
  AQI values are estimates for awareness only — follow official CPCB / SAFAR advisories for decisions.
</div>""", unsafe_allow_html=True)
