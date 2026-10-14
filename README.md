# 🌤️ AQIfyMe

**AQI + verify + me**: verified air-quality information, made for you. A live air-quality site for 25 Delhi localities, built with Python and Streamlit.

Live at **https://aqifyme.streamlit.app**

A live air-quality dashboard for 25 Delhi localities, built with Python + Streamlit.

## Run it

```bash
./run.sh
```

The first run creates a virtual environment and installs everything. After that it opens
http://localhost:8501 in your browser.

Manual alternative:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

## Features
- **Live dashboard**: fetches fresh data every time the page opens, and re-checks automatically
  every 1–30 min (set in the sidebar).
- **Realistic live sky** (WebGL shader, like the iPhone Weather app): soft sunlit clouds, and the sun or moon
  placed for Delhi's real time of day. Smog haze thickens and turns brown as the AQI worsens, with sunset glow,
  stars on clean nights, and floating particulates on bad days. Preview it with `?sky=0` … `?sky=5` and `?hour=0` … `?hour=23`
  in the URL, or turn it off with **Animated sky** in the sidebar.
- **Liquid-glass UI**: frosted cards with light rims, a cursor-following highlight and light sweeps; glass dropdowns and inputs.
- **iOS-style layout**: a big AQI reading, today's high/low, a 12-hour outlook sentence, a 24-hour hourly strip,
  daily low→high range bars, and detail tiles (main pollutant, cigarette equivalent, change since yesterday, wind, humidity, visibility).
- **AQI scale**: a rounded gradient track with a "you are here" marker, plus a detailed chip for every category.
- **Tap any box to expand it**: it grows into a large glass panel with more detail.
  - Pollutants: 72 h history and 48 h forecast chart with hover tooltips, stats, WHO and Indian limits, the hours of day it peaks,
    its rank across Delhi, sources, health effects and protection tips.
  - The AQI, hourly, daily, AQI scale and every tile (wind, humidity, visibility, cigarettes, since yesterday) have their own views.
  - Use ‹ › or the arrow keys to move between panels and Esc to close. **Copy** copies a one-line summary.
  - Cards tilt in 3D on hover and ripple on click.
- **Pollutants**: PM2.5, PM10, NO₂, O₃, CO, SO₂, CO₂ and dust, each with its CPCB sub-index and how it compares to the WHO limit.
- **Trends**: last 72 hours, what's driving the AQI, and an hour-of-day heatmap.
- **Forecast**: next ~4 days hourly, the best and worst times to be outdoors, and daily summaries.
- **Map** and **Compare areas**: every locality ranked, plus averages by zone.
- **History explorer**: any date range since Aug 2022 for up to 4 localities, a year-over-year overlay,
  a calendar heatmap, days spent in each category, a lookup for a specific day and hour, and CSV download.
- **Health advice**: tailored to your profile (children, elderly, asthma, pregnant, athletes…), plus mask, purifier and window guidance.
- **Learn**: pollutant explainers, both AQI scales, Delhi's GRAP stages and tips.
- Switch between India (CPCB) and US (EPA) AQI.

## More features
- **📍 Use my location**: the sidebar button finds your nearest locality (your browser asks for permission first).
- **🔔 AQI alerts**: pick a level such as Poor or Very Poor. While the page is open, you get a banner and a desktop
  notification when the AQI reaches that level, or is forecast to within 3 hours.
- **🗓️ Planner tab**: choose an activity, duration, day and hours. It finds the 3 cleanest slots from the hourly PM2.5
  forecast and estimates how much PM2.5 you'd breathe in.
- **🔎 Why? tab**: explains what's driving pollution right now. It combines NASA satellite fire hotspots (stubble burning),
  wind direction and speed, mixing height, traffic gases, dust, humidity, Diwali dates and ozone, and maps the fires
  with the wind blowing toward Delhi.
- **⚖️ Compare**: two places side by side, with a verdict, a 72 h + 48 h chart and a pollutant table.
- **🫁 My exposure**: log your time outdoors to get a 0–100 daily clean-air score, a cigarette equivalent, streaks and
  badges. It's saved in `my_exposure.json` on your computer.
- **हिन्दी**: a language switch at the top of the sidebar. It covers the menus, labels and categories; detailed
  explanations stay in English.
- **Phone friendly**: tighter layout, two-column grids, and full-screen detail panels on small screens.
- **Putting it online**: see [DEPLOY.md](DEPLOY.md).

## Worldwide
- **Search any place on Earth** (sidebar): cities, towns or postcodes, via Open-Meteo's free geocoding. Or pick one of 23 world
  cities (London, New York, Beijing, Lahore, Lagos, Sydney…) next to the 10 Indian ones.
- Times, forecasts and day/night follow each place's **local time zone**. The AQI defaults to **US EPA** outside India.
- Live stations (WAQI) and NASA fire detection work worldwide. The Why? tab looks for fires within 500 km and checks
  whether they're upwind.
- **Sky with real weather**: rain, snow, thunderstorms with lightning, fog and cloud cover follow the live conditions. Preview them with
  `?wx=rain|snow|storm|fog`.
- New tiles: **weather**, **UV index**, and **pollen** in Europe; each expands into its own chart panel.
- Cards reveal as you scroll and their numbers count up.

## Newest
- **10 cities, 73 localities**: Delhi NCR (now with Noida, Gurugram, Ghaziabad and Faridabad), Mumbai, Bengaluru, Kolkata,
  Chennai, Hyderabad, Pune, Lucknow, Chandigarh and Patna. Pick the city at the top of the sidebar.
- **Station-corrected forecasts**: the nearest live station fixes the model's bias; the correction fades out over about a day.
- **Private exposure log**: each visitor's log is stored in their own browser (compressed cookies), never on the server.
- **📤 Share**: an Instagram/WhatsApp-ready image of the current AQI, plus a WhatsApp button and a link that opens your locality.
- **📊 Weekly report**: this week vs last, cleanest and worst days, hourly rhythm, and every locality in the city ranked.
- **Telegram morning digest**: `digest.py`, run daily by GitHub Actions at 7:00 AM IST. See [DEPLOY.md](DEPLOY.md) for the
  2-minute bot setup.

## Data
- [Open-Meteo Air Quality API](https://open-meteo.com/en/docs/air-quality-api) (Copernicus CAMS model): free, no key.
  It's model data on a coarse grid, so nearby localities can show similar values.
- **Optional real station data**: get a free token at https://aqicn.org/data-platform/token/ and paste it into
  the sidebar (or set the `WAQI_TOKEN` env var, or add it to `.streamlit/secrets.toml`).
  This adds live CPCB/DPCC ground-station readings and plots every Delhi station on the map.

## Putting it online 24/7
Push this folder to GitHub and deploy it free on https://share.streamlit.io (pick `app.py`).
Anyone who opens the link gets the current AQI.
