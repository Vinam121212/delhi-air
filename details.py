"""Rich "expanded" views for every box on the home page.

Each builder returns {"title", "html", "summary"}; the HTML is injected into the expanding glass panel
(see expand.py). Charts are self-contained animated SVGs with a hover tooltip handled client-side.
"""
import html as htmllib
import json
import math

import numpy as np
import pandas as pd

from aqi import HEALTH, POLLUTANTS, categories, category, cigarettes_per_day

TIPS = {
    "pm2_5": ["Wear a well-fitted N95 outdoors — cloth and surgical masks don't stop PM2.5.",
              "Run a HEPA purifier in the room you sleep in.", "Avoid exercising near traffic, especially 7–10 AM and 6–10 PM."],
    "pm10": ["Keep windows shut on dusty, windy days.", "Damp-mop floors instead of sweeping, which re-suspends dust.",
             "Avoid construction zones and unpaved roads."],
    "nitrogen_dioxide": ["Walk or cycle on side streets rather than main roads.", "Keep car windows up and set AC to recirculate in traffic.",
                         "Ventilate the kitchen when cooking on gas."],
    "ozone": ["Ozone peaks on sunny afternoons — exercise in the early morning instead.",
              "Indoor levels are much lower than outdoors.", "People with asthma should keep relief inhalers close."],
    "carbon_monoxide": ["Never run generators, heaters or charcoal stoves in closed rooms.",
                        "Avoid long waits in congested traffic with windows open.", "Install a CO alarm if you use gas heating."],
    "sulphur_dioxide": ["Levels are highest near industrial areas and power plants.",
                        "People with asthma are especially sensitive — limit exertion downwind of industry."],
    "carbon_dioxide": ["Outdoor CO₂ isn't a direct health risk, but indoor CO₂ above ~1000 ppm causes drowsiness — ventilate rooms.",
                       "Use public transport, carpool, or EVs to cut emissions."],
    "dust": ["Desert dust events usually blow in from the west on windy days in April–June.",
             "Wear wrap-around glasses and a mask during dust storms."],
}


def _esc(s):
    return htmllib.escape(str(s), quote=True)


def _fmt(v, nd=0):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    return f"{v:,.{nd}f}"


# ── SVG charts ────────────────────────────────────────────────────────────────
def _smooth_path(pts):
    """Catmull-Rom → cubic Bézier for a smooth line through pts."""
    if len(pts) < 2:
        return ""
    d = [f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"]
    for i in range(len(pts) - 1):
        p0 = pts[i - 1] if i > 0 else pts[i]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < len(pts) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d.append(f"C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}")
    return " ".join(d)


def line_chart(times, series, now=None, hlines=(), bands=None, height=230, unit="", ymin=0.0):
    """series: list of (label, values, colour). bands: AQI category list to shade."""
    W, H, L, R, T, B = 820, height, 44, 14, 16, 30
    pw, ph = W - L - R, H - T - B
    n = len(times)
    allv = [v for _, vals, _ in series for v in vals if v is not None and not pd.isna(v)]
    if not allv or n < 2:
        return '<div class="muted">Not enough data for a chart.</div>'
    ymax = max(allv + [h[0] for h in hlines]) * 1.12 or 1
    x = lambda i: L + pw * i / (n - 1)
    y = lambda v: T + ph * (1 - (v - ymin) / (ymax - ymin))
    uid = f"c{abs(hash((tuple(times[:2]), len(series), ymax))) % 10 ** 8}"
    out = [f'<svg class="xchart" viewBox="0 0 {W} {H}" preserveAspectRatio="none" data-chart="{uid}" '
           f'data-l="{L}" data-pw="{pw}" data-n="{n}">', "<defs>"]
    for k, (_, _, col) in enumerate(series):
        out.append(f'<linearGradient id="{uid}g{k}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{col}" stop-opacity=".35"/>'
                   f'<stop offset="1" stop-color="{col}" stop-opacity="0"/></linearGradient>')
    out.append("</defs>")
    if bands:
        lo = 0
        for hi, _, col, _ in bands:
            if lo >= ymax:
                break
            out.append(f'<rect x="{L}" y="{y(min(hi, ymax)):.1f}" width="{pw}" height="{y(lo) - y(min(hi, ymax)):.1f}" '
                       f'fill="{col}" opacity=".10"/>')
            lo = hi
    for g in range(5):  # grid
        gv = ymin + (ymax - ymin) * g / 4
        out.append(f'<line x1="{L}" x2="{W - R}" y1="{y(gv):.1f}" y2="{y(gv):.1f}" stroke="rgba(255,255,255,.12)"/>'
                   f'<text x="{L - 8}" y="{y(gv) + 4:.1f}" text-anchor="end" class="ax">{gv:,.0f}</text>')
    step = max(1, n // 6)
    for i in range(0, n, step):
        out.append(f'<text x="{x(i):.1f}" y="{H - 8}" text-anchor="middle" class="ax">{pd.Timestamp(times[i]):%a %-I%p}</text>')
    if now is not None:
        idx = int(np.argmin([abs((pd.Timestamp(t) - now).total_seconds()) for t in times]))
        out.append(f'<rect x="{x(idx):.1f}" y="{T}" width="{W - R - x(idx):.1f}" height="{ph}" fill="rgba(255,255,255,.05)"/>'
                   f'<line x1="{x(idx):.1f}" x2="{x(idx):.1f}" y1="{T}" y2="{T + ph}" stroke="#fff" stroke-dasharray="3 4" opacity=".7"/>'
                   f'<text x="{x(idx) + 6:.1f}" y="{T + 12}" class="ax" fill="#fff">NOW · forecast →</text>')
    for hv, hl, hc in hlines:
        out.append(f'<line x1="{L}" x2="{W - R}" y1="{y(hv):.1f}" y2="{y(hv):.1f}" stroke="{hc}" stroke-dasharray="6 5" stroke-width="1.5"/>'
                   f'<text x="{W - R - 4}" y="{y(hv) - 5:.1f}" text-anchor="end" class="ax" fill="{hc}">{_esc(hl)}</text>')
    data = []
    for k, (label, vals, col) in enumerate(series):
        pts = [(x(i), y(v)) for i, v in enumerate(vals) if v is not None and not pd.isna(v)]
        if len(pts) < 2:
            continue
        path = _smooth_path(pts)
        out.append(f'<path d="{path} L{pts[-1][0]:.1f},{T + ph} L{pts[0][0]:.1f},{T + ph} Z" fill="url(#{uid}g{k})" class="area"/>')
        out.append(f'<path d="{path}" fill="none" stroke="{col}" stroke-width="2.6" stroke-linecap="round" pathLength="1" '
                   f'class="draw" style="animation-delay:{.15 * k:.2f}s;filter:drop-shadow(0 0 6px {col})"/>')
        data.append({"l": label, "c": col, "v": [None if v is None or pd.isna(v) else round(float(v), 1) for v in vals]})
    out.append(f'<line class="guide" x1="0" x2="0" y1="{T}" y2="{T + ph}" stroke="rgba(255,255,255,.6)" opacity="0"/>')
    out.append("</svg>")
    meta = {"t": [f"{pd.Timestamp(t):%a %d %b, %-I %p}" for t in times], "s": data, "u": unit,
            "ymin": ymin, "ymax": ymax, "T": T, "ph": ph}
    return (f'<div class="xchart-wrap">{"".join(out)}<div class="xtip"></div>'
            f'<script type="application/json" class="xchart-data">{json.dumps(meta)}</script></div>')


def bar_rows(rows, max_val=None):
    """Horizontal labelled bars: rows = (label, value, colour, right_text)."""
    max_val = max_val or max([r[1] for r in rows if r[1] is not None] + [1])
    out = []
    for i, (lab, v, col, txt) in enumerate(rows):
        pct = 0 if v is None or pd.isna(v) else max(2, min(100, v / max_val * 100))
        out.append(f'<div class="brow"><span class="bl">{lab}</span><div class="bt"><span style="width:{pct:.1f}%;background:'
                   f'linear-gradient(90deg,{col}88,{col});box-shadow:0 0 10px {col}88;animation-delay:{.05 * i:.2f}s"></span></div>'
                   f'<span class="bv">{txt}</span></div>')
    return '<div class="brows">' + "".join(out) + "</div>"


def hour_profile(series: pd.Series, colour_fn):
    """24 columns: average by hour of day."""
    prof = series.groupby(series.index.hour).mean().reindex(range(24))
    mx = prof.max() or 1
    cols = []
    for h, v in prof.items():
        hgt = 0 if pd.isna(v) else max(4, v / mx * 100)
        col = colour_fn(v) if not pd.isna(v) else "#64748b"
        cols.append(f'<div class="hcol" title="{h:02d}:00 · {_fmt(v)}"><span style="height:{hgt:.0f}%;background:{col};'
                    f'animation-delay:{h * .025:.2f}s"></span><i>{h if h % 3 == 0 else ""}</i></div>')
    worst = int(prof.idxmax()) if prof.notna().any() else None
    best = int(prof.idxmin()) if prof.notna().any() else None
    return '<div class="hprof">' + "".join(cols) + "</div>", worst, best


def stat_grid(items):
    return '<div class="xstats">' + "".join(
        f'<div class="xstat"><div class="k">{k}</div><div class="v"{f" style=color:{c}" if c else ""}>{v}</div>'
        f'<div class="s">{s}</div></div>' for k, v, s, c in items) + "</div>"


def section(title, body):
    return f'<section class="xsec"><h4>{title}</h4>{body}</section>'


def head(kicker, title, value_html, sub, colour):
    return (f'<header class="xhead" style="--c:{colour}"><div class="xk">{kicker}</div><div class="xt">{title}</div>'
            f'<div class="xv">{value_html}</div><div class="xs">{sub}</div></header>')


def _hfmt(h):
    return pd.Timestamp(2000, 1, 1, h).strftime("%-I %p") if h is not None else "—"


# ── builders ──────────────────────────────────────────────────────────────────
class DetailBuilder:
    def __init__(self, *, hourly, now, location, zone, standard, aqi_col, weather, all_current, label, city="Delhi NCR"):
        self.h = hourly
        self.now = now
        self.past = hourly[hourly.index <= now]
        self.future = hourly[hourly.index > now]
        self.cur = self.past.iloc[-1]
        self.loc, self.zone, self.city = location, zone, city
        self.std, self.col = standard, aqi_col
        self.cats = categories(standard)
        self.wx = weather or {}
        self.all = all_current
        self.label = label
        self.win = hourly[(hourly.index > now - pd.Timedelta(hours=72)) & (hourly.index <= now + pd.Timedelta(hours=48))]

    def colour(self, v):
        return category(v, self.std)[1]

    def in_colour(self, si):
        return category(si, "India (CPCB)")[1]

    # pollutant ----------------------------------------------------------------
    def pollutant(self, key):
        m = POLLUTANTS[key]
        unit = m["unit"]
        v = self.cur.get(key)
        si = self.cur.get(f"si_{key}")
        has_si = si is not None and not pd.isna(si)
        col = self.in_colour(si) if has_si else "#7dd3fc"
        cat = category(si, "India (CPCB)")[0] if has_si else ""
        p24 = self.past[key].tail(24)
        p72 = self.past[key].tail(72)
        f24 = self.future[key].head(24)
        hl = []
        if m.get("who"):
            hl.append((m["who"], f"WHO {m['who']}", "#4ade80"))
        if m.get("naaqs"):
            hl.append((m["naaqs"], f"India limit {m['naaqs']}", "#facc15"))
        chart = line_chart(list(self.win.index), [(m["label"], list(self.win[key]), col)], now=self.now, hlines=hl, unit=unit)
        prof, worst, best = hour_profile(self.past[key], lambda x: self.in_colour(
            category_si(key, x)) if key in ("pm2_5", "pm10", "nitrogen_dioxide", "ozone", "carbon_monoxide", "sulphur_dioxide") else "#7dd3fc")
        stats = stat_grid([
            ("Now", f"{_fmt(v, 1)}", unit, col),
            ("24 h average", _fmt(p24.mean(), 1), unit, None),
            ("24 h range", f"{_fmt(p24.min())}–{_fmt(p24.max())}", unit, None),
            ("72 h peak", _fmt(p72.max()), f"{p72.idxmax():%a %-I %p}" if p72.notna().any() else "", None),
            ("Next 24 h peak", _fmt(f24.max()), f"{f24.idxmax():%a %-I %p}" if f24.notna().any() else "", None),
            ("Sub-index", _fmt(si) if has_si else "—", cat, col if has_si else None),
        ])
        limits = ""
        if m.get("who") and v is not None and not pd.isna(v):
            rows = [("Current", v, col, f"{v:,.1f}"), ("WHO guideline", m["who"], "#4ade80", f"{m['who']}")]
            if m.get("naaqs"):
                rows.append(("India NAAQS", m["naaqs"], "#facc15", f"{m['naaqs']}"))
            limits = section("Against the limits", bar_rows(rows) +
                             f'<p class="xnote">Right now it is <b>{v / m["who"]:.1f}×</b> the WHO guideline.</p>')
        rank = ""
        if self.all is not None and key in self.all:
            df = self.all[["location", key]].dropna().sort_values(key, ascending=False).reset_index(drop=True)
            pos = df.index[df["location"] == self.loc]
            if len(pos):
                mine = float(df.loc[pos[0], key])
                r = int((df[key] > mine + 1e-9).sum()) + 1       # ties share a rank
                ties = int((abs(df[key] - mine) < 1e-9).sum()) - 1
                top = df.head(5)
                rows = [(("📍 " if l == self.loc else "") + l, val, self.in_colour(category_si(key, val)) if key in CPCB_KEYS else "#7dd3fc",
                         f"{val:,.0f}") for l, val in zip(top["location"], top[key])]
                if self.loc not in set(top["location"]):
                    rows.append((f"📍 {self.loc}", mine, col, f"{mine:,.0f}"))
                tie_txt = f" (tied with {ties})" if ties else ""
                rank = section(f"Across {self.city} · #{r} most polluted of {len(df)}{tie_txt}", bar_rows(rows) +
                               '<p class="xnote">Model data on a coarse grid — nearby localities can share values.</p>')
        tips = "".join(f"<li>{t}</li>" for t in TIPS.get(key, []))
        body = (head(f"{self.loc} · {m['name'].split('(')[0].strip()}", m["label"], f'{_fmt(v, 1)}<span class="xu">{unit}</span>',
                     cat or "Not part of the AQI", col)
                + stats + section("Last 72 hours & next 48 hours", chart)
                + '<div class="xgrid2">'
                + section("When is it worst? (by hour of day)", prof +
                          f'<p class="xnote">Usually highest around <b>{_hfmt(worst)}</b>, lowest around <b>{_hfmt(best)}</b>.</p>')
                + (limits or section("About", f"<p>{m['effects']}</p>"))
                + "</div>"
                + '<div class="xgrid2">'
                + section("Where it comes from", f"<p>{m['sources']}</p>")
                + section("Health effects", f"<p>{m['effects']}</p>")
                + "</div>"
                + (rank or "")
                + section("How to protect yourself", f'<ul class="xlist">{tips}</ul>'))
        summary = (f"{m['label']} at {self.loc}, {self.city}: {_fmt(v, 1)} {unit}"
                   + (f" ({cat}, sub-index {si:.0f})" if has_si else "")
                   + (f", {v / m['who']:.1f}× WHO guideline" if m.get("who") and v else "") + ".")
        return {"title": m["label"], "html": body, "summary": summary}

    # hero ---------------------------------------------------------------------
    def aqi(self):
        a = self.cur[self.col]
        name, col, emo, lvl = category(a, self.std)
        rows = []
        for k in CPCB_KEYS:
            s = self.cur.get(f"si_{k}")
            if s is not None and not pd.isna(s):
                rows.append((POLLUTANTS[k]["label"], float(s), self.in_colour(s), f"{s:.0f}"))
        rows.sort(key=lambda r: -r[1])
        chart = line_chart(list(self.win.index), [("AQI", list(self.win[self.col]), "#ffffff")], now=self.now,
                           bands=self.cats, unit="AQI")
        other = "us_aqi" if self.col == "in_aqi" else "in_aqi"
        other_name = "US (EPA)" if other == "us_aqi" else "India (CPCB)"
        h = HEALTH[max(category(self.cur["in_aqi"], "India (CPCB)")[3], 0)]
        stats = stat_grid([
            (self.std, f'<span class="xnum" style="--num:{int(round(a))}"></span>', name, col),
            (other_name, _fmt(self.cur.get(other)), category(self.cur.get(other), other_name)[0], category(self.cur.get(other), other_name)[1]),
            ("24 h average", _fmt(self.past[self.col].tail(24).mean()), "", None),
            ("Today's high", _fmt(self.h[self.h.index.date == self.now.date()][self.col].max()), "", None),
            ("Today's low", _fmt(self.h[self.h.index.date == self.now.date()][self.col].min()), "", None),
            ("Main pollutant", self.label.get(self.cur.get("dominant"), "—"), "highest sub-index", None),
        ])
        recs = (f'<div class="xrecs"><div><span>😷</span><b>{h["mask"]}</b><i>Mask</i></div>'
                f'<div><span>🏃</span><b>{h["outdoor"]}</b><i>Outdoors</i></div>'
                f'<div><span>🌀</span><b>{h["purifier"]}</b><i>Purifier</i></div>'
                f'<div><span>🪟</span><b>{h["windows"]}</b><i>Windows</i></div></div>')
        body = (head(f"📍 {self.loc} · {self.zone}", "Air Quality Index",
                     f'<span class="xnum" style="--num:{int(round(a))}"></span>', f"{emo} {name}", col)
                + stats + section("What to do right now", recs + f'<p class="xnote">{h["impact"]}</p>')
                + section("AQI · last 72 hours & next 48 hours", chart)
                + '<div class="xgrid2">'
                + section("Pollutant sub-indices (CPCB)", bar_rows(rows, 500) +
                          '<p class="xnote">The overall Indian AQI is the <b>highest</b> sub-index — here '
                          f'{rows[0][0] if rows else "—"}.</p>')
                + section("How it's calculated", "<p>CPCB's National AQI converts each pollutant into a 0–500 sub-index "
                          "using 24-hour averages (PM2.5, PM10, NO₂, SO₂) and 8-hour averages (CO, O₃), then takes the worst one. "
                          "The US EPA AQI uses different breakpoints and is usually higher for the same PM2.5.</p>")
                + "</div>")
        return {"title": "AQI", "html": body,
                "summary": f"AQI at {self.loc}, {self.city}: {a:.0f} ({name}, {self.std}). Main pollutant: "
                           f"{self.label.get(self.cur.get('dominant'), '—')}."}

    # hourly strip -------------------------------------------------------------
    def hourly(self):
        fut = self.future.head(48)
        chart = line_chart(list(self.win.index), [("AQI", list(self.win[self.col]), "#7dd3fc")], now=self.now, bands=self.cats, unit="AQI")
        day = fut[(fut.index.hour >= 6) & (fut.index.hour <= 21)]
        r = day[self.col].rolling(2).mean().dropna()
        cells = []
        for t, row in fut.head(48).iterrows():
            v = row[self.col]
            cells.append(f'<div class="xh" style="--c:{self.colour(v)}"><b>{t:%-I %p}</b><span>{v:.0f}</span><i>{t:%a}</i></div>')
        stats = stat_grid([
            ("Best outdoor window", f"{(r.idxmin() - pd.Timedelta(hours=1)):%a %-I %p}" if not r.empty else "—",
             f"AQI ≈ {r.min():.0f}" if not r.empty else "", "#4ade80"),
            ("Worst window", f"{(r.idxmax() - pd.Timedelta(hours=1)):%a %-I %p}" if not r.empty else "—",
             f"AQI ≈ {r.max():.0f}" if not r.empty else "", "#f87171"),
            ("Next 24 h average", _fmt(fut.head(24)[self.col].mean()), "", None),
            ("Hours ≥ Poor (next 48 h)", str(int((fut[self.col] > (200 if self.col == 'in_aqi' else 150)).sum())), "hours", None),
        ])
        body = (head(f"📍 {self.loc}", "Hourly forecast", f"{len(fut)} h", "AQI hour by hour", "#7dd3fc")
                + stats + section("Trend", chart) + section("Next 48 hours", f'<div class="xhours">{"".join(cells)}</div>')
                + section("Why it changes through the day", "<p>Pollution in most Indian cities peaks late at night and early "
                          "morning, when the air near the ground is cold and still (a low <b>mixing height</b>) and traffic "
                          "and heating emissions get trapped. Afternoon sun heats the ground, the air mixes upward and levels fall.</p>"))
        return {"title": "Hourly forecast", "html": body, "summary": f"Hourly AQI forecast for {self.loc}, {self.city}."}

    # daily --------------------------------------------------------------------
    def daily(self):
        d = self.h[self.h.index.date >= self.now.date()]
        g = d.groupby(d.index.date)
        rows = []
        for day, grp in g:
            a = grp[self.col]
            if a.dropna().empty:
                continue
            name, col, emo, _ = category(a.mean(), self.std)
            dom = grp["dominant"].mode()
            daylight = grp[(grp.index.hour >= 6) & (grp.index.hour <= 21)][self.col]
            best = f"{daylight.idxmin():%-I %p}" if daylight.notna().any() else "—"
            rows.append(f'<tr><td><b>{pd.Timestamp(day):%A}</b><br><i>{pd.Timestamp(day):%d %b}</i></td><td>{emo}</td>'
                        f'<td style="color:{col}"><b>{a.mean():.0f}</b><br><i>{name}</i></td><td>{a.min():.0f} – {a.max():.0f}</td>'
                        f'<td>{self.label.get(dom.iloc[0], "—") if not dom.empty else "—"}</td><td>{best}</td>'
                        f'<td>{_fmt(grp["pm2_5"].mean())} µg/m³</td></tr>')
        table = ('<table class="xtable"><thead><tr><th>Day</th><th></th><th>Avg AQI</th><th>Range</th><th>Main pollutant</th>'
                 f'<th>Best hour</th><th>PM2.5 avg</th></tr></thead><tbody>{"".join(rows)}</tbody></table>')
        series = [(POLLUTANTS[k]["label"], list(d[k]), c) for k, c in
                  [("pm2_5", "#7dd3fc"), ("pm10", "#c4b5fd"), ("nitrogen_dioxide", "#f9a8d4")]]
        chart = line_chart(list(d.index), series, now=self.now, unit="µg/m³")
        body = (head(f"📍 {self.loc}", "Daily outlook", f"{len(rows)} days", "AQI forecast by day", "#c4b5fd")
                + section("Day by day", table) + section("Main pollutants ahead", chart))
        return {"title": "Daily forecast", "html": body, "summary": f"{len(rows)}-day AQI outlook for {self.loc}, {self.city}."}

    # tiles --------------------------------------------------------------------
    def _wx_hourly(self):
        hw = self.wx.get("hourly")
        if not hw:
            return None
        df = pd.DataFrame(hw)
        df["time"] = pd.to_datetime(df["time"])
        return df.set_index("time")

    def cigarettes(self):
        pm = self.past["pm2_5"].tail(24).mean()
        c = cigarettes_per_day(pm) or 0
        stats = stat_grid([("Per day", f"{c:.1f}", "cigarettes", "#fca5a5"), ("Per week", f"{c * 7:.0f}", "cigarettes", None),
                           ("Per month", f"{c * 30:.0f}", "cigarettes", None), ("Per year", f"{c * 365:,.0f}", "cigarettes", None)])
        packs = "".join('<span class="cig">🚬</span>' for _ in range(min(30, int(round(c * 7)))))
        body = (head(f"📍 {self.loc}", "Cigarette equivalent", f"{c:.1f}", "cigarettes per day of breathing", "#fca5a5")
                + stats + section("This week, in cigarettes", f'<div class="cigs">{packs}</div>')
                + section("Where this comes from", "<p>Berkeley Earth estimated that breathing air with <b>22 µg/m³ of PM2.5</b> "
                          f"for a day is roughly as harmful as smoking one cigarette. The last 24 hours here averaged <b>{pm:.0f} µg/m³</b>. "
                          "Air meeting the WHO guideline (15 µg/m³) would be about 0.7 cigarettes a day.</p>"))
        return {"title": "Cigarette equivalent", "html": body,
                "summary": f"Breathing the air at {self.loc} today ≈ smoking {c:.1f} cigarettes."}

    def change(self):
        last = self.past[self.col].tail(24)
        prev = self.past[self.col].iloc[-48:-24]
        times = list(last.index)
        chart = line_chart(times, [("Last 24 h", list(last), "#7dd3fc"),
                                   ("Previous 24 h", list(prev.reindex(prev.index)) if len(prev) == len(last) else [], "#94a3b8")],
                           unit="AQI", bands=self.cats)
        d = last.mean() - prev.mean() if len(prev) else float("nan")
        stats = stat_grid([("Last 24 h average", _fmt(last.mean()), "", None), ("Previous 24 h", _fmt(prev.mean()), "", None),
                           ("Change", ("▲ " if d > 0 else "▼ ") + _fmt(abs(d)) if not pd.isna(d) else "—",
                            "worse" if d > 0 else "better", "#f87171" if d > 0 else "#4ade80")])
        body = (head(f"📍 {self.loc}", "Since yesterday", ("▲ " if d > 0 else "▼ ") + _fmt(abs(d)), "change in 24 h average AQI",
                     "#f87171" if d > 0 else "#4ade80") + stats + section("Today vs yesterday, hour by hour", chart))
        return {"title": "Since yesterday", "html": body, "summary": f"AQI at {self.loc} changed by {d:+.0f} vs the previous 24 h."}

    def wind(self):
        hw = self._wx_hourly()
        cw = self.wx.get("current", {})
        body = head(f"📍 {self.loc}", "Wind & mixing height", f'{_fmt(cw.get("wind_speed_10m"))}<span class="xu">km/h</span>',
                    "wind carries pollution away", "#6ee7b7")
        if hw is not None:
            win = hw[(hw.index >= self.now - pd.Timedelta(hours=12)) & (hw.index <= self.now + pd.Timedelta(hours=48))]
            body += section("Wind speed (km/h)", line_chart(list(win.index), [("Wind", list(win["wind_speed_10m"]), "#6ee7b7")],
                                                            now=self.now, unit="km/h"))
            if "boundary_layer_height" in win:
                body += section("Mixing height (m)", line_chart(list(win.index), [("Mixing height", list(win["boundary_layer_height"]), "#fde047")],
                                                                now=self.now, hlines=[(500, "trapping below ~500 m", "#f87171")], unit="m"))
        body += section("Why it matters", "<p>Strong winds blow pollutants away, while calm winds let them accumulate. "
                        "The <b>mixing height</b> is how high the air can stir — on cold winter nights it can drop below 200 m, "
                        "squeezing a whole city's emissions into a thin layer. That's why north India's smog is worst on still November nights.</p>")
        return {"title": "Wind", "html": body, "summary": f"Wind at {self.loc}: {_fmt(cw.get('wind_speed_10m'))} km/h."}

    def humidity(self):
        hw = self._wx_hourly()
        cw = self.wx.get("current", {})
        body = head(f"📍 {self.loc}", "Humidity", f'{_fmt(cw.get("relative_humidity_2m"))}<span class="xu">%</span>', "relative humidity", "#93c5fd")
        if hw is not None:
            win = hw[(hw.index >= self.now - pd.Timedelta(hours=12)) & (hw.index <= self.now + pd.Timedelta(hours=48))]
            body += section("Humidity (%)", line_chart(list(win.index), [("Humidity", list(win["relative_humidity_2m"]), "#93c5fd")],
                                                       now=self.now, unit="%"))
        body += section("Humidity and smog", "<p>Moist air helps fine particles grow by absorbing water — they scatter more light, "
                        "so haze looks thicker. In winter, high humidity plus calm winds and cold air creates north India's dense smog-fog.</p>")
        return {"title": "Humidity", "html": body, "summary": f"Humidity at {self.loc}: {_fmt(cw.get('relative_humidity_2m'))}%."}

    def visibility(self):
        hw = self._wx_hourly()
        cw = self.wx.get("current", {})
        v = cw.get("visibility")
        body = head(f"📍 {self.loc}", "Visibility", f'{_fmt((v or 0) / 1000, 1)}<span class="xu">km</span>', "how far you can see", "#e2e8f0")
        if hw is not None and "visibility" in hw:
            win = hw[(hw.index >= self.now - pd.Timedelta(hours=12)) & (hw.index <= self.now + pd.Timedelta(hours=48))]
            body += section("Visibility (km)", line_chart(list(win.index), [("Visibility", list(win["visibility"] / 1000), "#e2e8f0")],
                                                          now=self.now, unit="km"))
        body += section("Haze vs fog", "<p>Particles scatter sunlight, so heavy PM2.5 shows up as a brownish-grey haze and "
                        "can cut visibility below 1 km — and delaying flights. True fog is white and forms when air is near "
                        "100% humidity; north India's winter 'smog' is usually both at once.</p>")
        return {"title": "Visibility", "html": body, "summary": f"Visibility at {self.loc}: {_fmt((v or 0) / 1000, 1)} km."}

    def main_pollutant(self):
        dom = self.cur.get("dominant")
        if isinstance(dom, str) and dom in POLLUTANTS:
            return self.pollutant(dom)
        return self.aqi()

    def scale(self):
        cards = []
        for i, (hi, name, col, emo) in enumerate(categories("India (CPCB)")):
            h = HEALTH[i]
            lo = 0 if i == 0 else categories("India (CPCB)")[i - 1][0] + 1
            on = " on" if i == category(self.cur["in_aqi"], "India (CPCB)")[3] else ""
            cards.append(f'<div class="xcat{on}" style="--c:{col}"><div class="xcat-h"><span>{emo}</span><b>{name}</b><i>{lo}–{hi}</i></div>'
                         f'<p>{h["impact"]}</p><div class="xcat-g"><span>😷 {h["mask"]}</span><span>🏃 {h["outdoor"]}</span>'
                         f'<span>🌀 {h["purifier"]}</span><span>🪟 {h["windows"]}</span></div></div>')
        us = "".join(f'<span class="xpill" style="--c:{c}">{e} {n} · ≤{hi}</span>' for hi, n, c, e in categories("US (EPA)"))
        body = (head("India CPCB National AQI", "The AQI scale", "0–500", "six categories, from Good to Severe", "#c4b5fd")
                + section("Every level explained", f'<div class="xcats">{"".join(cards)}</div>')
                + section("US EPA scale for comparison", f'<div class="xpills">{us}</div>'))
        return {"title": "AQI scale", "html": body, "summary": "India CPCB AQI scale: Good, Satisfactory, Moderate, Poor, Very Poor, Severe."}


CPCB_KEYS = ["pm2_5", "pm10", "nitrogen_dioxide", "ozone", "carbon_monoxide", "sulphur_dioxide"]


def category_si(key, conc):
    from aqi import sub_index
    return sub_index(key, conc)
