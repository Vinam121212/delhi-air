"""AQIfyMe morning digest → Telegram channel. Run by .github/workflows/daily-digest.yml every day at 7:00 AM IST.

Env: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID (e.g. @aqifyme or a numeric id), optional WAQI_TOKEN and
DIGEST_LOCATIONS (comma-separated locality names). `python digest.py --dry-run` prints the message and saves the image.
"""
import logging
import os
import sys
from html import escape

logging.getLogger("streamlit").setLevel(logging.ERROR)

import pandas as pd
import requests

import data
from aqi import HEALTH, POLLUTANTS, category, cigarettes_per_day
from locations import LOCATIONS
from planner import find_slots
from sharecard import make_card
from station import calibrate, parse_feed

PUBLIC_URL = "https://aqifyme.streamlit.app"
DEFAULT_LOCS = ["ITO", "Anand Vihar", "Gurugram Vikas Sadan", "Noida Sector 62"]


def station(lat, lon):
    tok = os.environ.get("WAQI_TOKEN")
    if not tok:
        return None
    try:
        from browser_js import haversine_km
        near = data.waqi_nearby(tok, round(lat, 3), round(lon, 3))
        if near.empty:
            return None
        near["km"] = [haversine_km(lat, lon, a, b) for a, b in zip(near["lat"], near["lon"])]
        best = near.sort_values("km").iloc[0]
        if best["km"] > data.MAX_STATION_KM:
            return None
        return parse_feed(data.waqi_feed_uid(tok, int(best["uid"])), lat, lon)
    except Exception:
        return None


def summarise(name):
    loc = LOCATIONS[name]
    now = pd.Timestamp.now(tz=data.TZ).tz_localize(None).floor("h")
    h = data.fetch_hourly(loc["lat"], loc["lon"])
    stn = station(loc["lat"], loc["lon"])
    if stn:
        h, _ = calibrate(h, stn, now)
    cur = h[h.index <= now].iloc[-1]
    today = h[h.index.date == now.date()]["in_aqi"]
    fut = h[h.index > now]
    slots, _ = find_slots(fut[fut.index.date == now.date()], "in_aqi", 60, 6, 21, top=1)
    dom = cur.get("dominant")
    return {"name": name, "loc": loc, "now": now, "aqi": float(cur["in_aqi"]), "cur": cur, "hi": today.max(), "lo": today.min(),
            "best": slots[0] if slots else None, "dom": POLLUTANTS[dom]["label"] if isinstance(dom, str) else "—",
            "cig": cigarettes_per_day(h[h.index <= now]["pm2_5"].tail(24).mean()) or 0, "station": stn}


def message(rows):
    now = rows[0]["now"]
    lines = [f"🌤️ <b>AQIfyMe · {now:%A %d %b}</b>", "Good morning! Here's the air today:", ""]
    for r in rows:
        name, col, emo, lvl = category(r["aqi"], "India (CPCB)")
        best = f" · best hour {r['best']['start']:%-I %p}" if r["best"] else ""
        lines.append(f"{emo} <b>{escape(r['name'])}</b>: AQI <b>{r['aqi']:.0f}</b> ({name}) · today {r['lo']:.0f}–{r['hi']:.0f}{best}")
    worst = max(rows, key=lambda r: r["aqi"])
    h = HEALTH[max(category(worst["aqi"], "India (CPCB)")[3], 0)]
    lines += ["", f"😷 Mask: {escape(h['mask'])} · 🏃 Outdoors: {escape(h['outdoor'])}",
              f"🚬 Breathing {escape(worst['name'])}'s air today ≈ {worst['cig']:.1f} cigarettes"]
    if now.weekday() == 0:   # Monday: last week's recap
        try:
            first = rows[0]
            wk = data.fetch_history(first["loc"]["lat"], first["loc"]["lon"],
                                                (now - pd.Timedelta(days=7)).date(), (now - pd.Timedelta(days=1)).date())
            lines.append(f"📊 Last week at {escape(first['name'])}: average AQI {wk['in_aqi'].mean():.0f}")
        except Exception:
            pass
    lines += ["", f"👉 Live map, forecast & tips: {PUBLIC_URL}"]
    return "\n".join(lines)


def main():
    dry = "--dry-run" in sys.argv
    names = [n.strip() for n in os.environ.get("DIGEST_LOCATIONS", ",".join(DEFAULT_LOCS)).split(",") if n.strip() in LOCATIONS]
    rows = [summarise(n) for n in names or DEFAULT_LOCS]
    text = message(rows)
    r0 = rows[0]
    cat, col, _, lvl = category(r0["aqi"], "India (CPCB)")
    png = make_card(location=r0["name"], place=r0["loc"]["zone"], aqi=r0["aqi"], standard="India (CPCB)", category=cat, colour=col,
                    pm25=float(r0["cur"]["pm2_5"]), cigarettes=float(r0["cig"]), main_pollutant=r0["dom"],
                    time_str=f"{r0['now']:%d %b · %-I:%M %p}", url=PUBLIC_URL.replace("https://", ""),
                    station=r0["station"]["name"] if r0["station"] else None,
                    advice=f"{HEALTH[max(lvl, 0)]['outdoor']} · Mask: {HEALTH[max(lvl, 0)]['mask']}")
    if dry:
        print(text)
        with open("digest_preview.png", "wb") as f:
            f.write(png)
        print("\n(saved digest_preview.png)")
        return
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set — skipping (see DEPLOY.md to set up the bot).")
        return
    api = f"https://api.telegram.org/bot{token}"
    r = requests.post(f"{api}/sendPhoto", data={"chat_id": chat}, files={"photo": ("aqifyme.png", png, "image/png")}, timeout=60)
    r.raise_for_status()
    r = requests.post(f"{api}/sendMessage", data={"chat_id": chat, "text": text, "parse_mode": "HTML",
                                                  "disable_web_page_preview": "true"}, timeout=30)
    r.raise_for_status()
    print("Sent digest for", ", ".join(x["name"] for x in rows))


if __name__ == "__main__":
    main()
