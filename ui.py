"""Styling (liquid glass over a live sky) and HTML building blocks for the dashboard."""
import pandas as pd
import plotly.graph_objects as go

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400;500;600;700;800&display=swap');

:root {
  --font: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Inter", "Helvetica Neue", sans-serif;
  --muted: rgba(255,255,255,.66);
  --soft: rgba(255,255,255,.82);
  --accent: #7dd3fc;
}
html, body { background: #0a1630; }
html, body, .stApp, .stMarkdown, .stText, p, span, div, label, li, h1, h2, h3, h4, h5, h6, button, input, textarea, select {
  font-family: var(--font); }
[data-testid="stIconMaterial"], .material-symbols-rounded, [class*="material-symbols"] { font-family: "Material Symbols Rounded" !important; }
html, body { -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; text-rendering: optimizeLegibility;
  font-feature-settings: "ss01", "cv11"; letter-spacing: -0.005em; }
.card-value, .hero-aqi, .hr .v, .day, .tile .big, .bubble { font-variant-numeric: tabular-nums; }
body.sky-fallback { background: linear-gradient(180deg, #1c3f7a 0%, #4a6fa0 55%, #a89a80 100%) fixed; }

/* let the WebGL sky show through every Streamlit layer */
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stHeader"], [data-testid="stBottom"] > div {
  background: transparent !important;
}
.block-container { padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1320px; }
.stMarkdown, .stMarkdown p, label, .stCaption { color: #fff; text-shadow: 0 1px 2px rgba(0,0,0,.25); }

/* ── animations ── */
@keyframes fadeUp { from { opacity: 0; transform: translateY(16px) scale(.985); filter: blur(4px); } to { opacity: 1; transform: none; filter: none; } }
@keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(74,222,128,.7); } 70% { box-shadow: 0 0 0 10px rgba(74,222,128,0); } 100% { box-shadow: 0 0 0 0 rgba(74,222,128,0); } }
@keyframes grow { from { width: 0; } }
@keyframes slideKnob { from { left: 0; } }
@property --num { syntax: '<integer>'; initial-value: 0; inherits: false; }
@keyframes count { from { --num: 0; } }
@keyframes floaty { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-4px); } }
@keyframes glint { 0%, 78% { transform: translateX(-120%) skewX(-18deg); } 100% { transform: translateX(260%) skewX(-18deg); } }
@keyframes ring { 0% { transform: scale(.6); opacity: .9; } 100% { transform: scale(2.4); opacity: 0; } }
.fade { animation: fadeUp .8s cubic-bezier(.2,.8,.2,1) both; }

/* ══ LIQUID GLASS ═══════════════════════════════════════════════════════════ */
.card, div[data-testid="stMetric"], [data-testid="stPlotlyChart"], [data-testid="stDataFrame"],
[data-testid="stExpander"] details, .glass {
  --mx: 30%; --my: 0%;
  position: relative; isolation: isolate; overflow: hidden;
  border-radius: 28px !important; border: none !important;
  background:
    radial-gradient(140% 90% at var(--mx) var(--my), rgba(255,255,255,.20) 0%, rgba(255,255,255,0) 45%),
    linear-gradient(165deg, rgba(255,255,255,.17) 0%, rgba(255,255,255,.06) 42%, rgba(255,255,255,.03) 60%, rgba(255,255,255,.10) 100%),
    rgba(20,28,52,.16) !important;
  backdrop-filter: blur(26px) saturate(210%) brightness(1.06) contrast(1.04);
  -webkit-backdrop-filter: blur(26px) saturate(210%) brightness(1.06) contrast(1.04);
  box-shadow:
    inset 0 1.5px 0.5px rgba(255,255,255,.65),            /* bright top rim */
    inset 0 -1px 0.5px rgba(255,255,255,.18),             /* bottom rim catch-light */
    inset 1px 0 0.5px rgba(255,255,255,.22), inset -1px 0 0.5px rgba(255,255,255,.12),
    inset 0 22px 34px -22px rgba(255,255,255,.38),        /* top inner sheen — thickness */
    inset 0 -26px 36px -26px rgba(0,0,0,.22),             /* bottom inner depth */
    inset 0 0 0 0.5px rgba(255,255,255,.10),
    0 24px 48px -16px rgba(0,0,0,.45), 0 3px 10px rgba(0,0,0,.14);
  transition: transform .45s cubic-bezier(.2,.9,.25,1.2), box-shadow .35s ease;
}
/* gradient rim: brighter where light hits (top-left / bottom-right) */
.card::before, [data-testid="stPlotlyChart"]::before, div[data-testid="stMetric"]::before, .glass::before {
  content: ""; position: absolute; inset: 0; border-radius: inherit; padding: 1.3px; pointer-events: none; z-index: 2;
  background: linear-gradient(135deg, rgba(255,255,255,.85) 0%, rgba(255,255,255,.18) 22%, rgba(255,255,255,.02) 50%,
                                      rgba(255,255,255,.12) 78%, rgba(255,255,255,.55) 100%);
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  -webkit-mask-composite: xor; mask-composite: exclude;
}
/* sweeping light reflection */
.card::after, .glass::after {
  content: ""; position: absolute; top: -20%; left: 0; width: 35%; height: 140%; pointer-events: none; z-index: 1;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,.13), rgba(255,255,255,.04) 60%, transparent);
  animation: glint 9s cubic-bezier(.4,0,.2,1) infinite; filter: blur(2px);
}
.card:hover {
  transform: translateY(-4px) scale(1.012);
  box-shadow:
    inset 0 1.5px 0.5px rgba(255,255,255,.8), inset 0 -1px 0.5px rgba(255,255,255,.22),
    inset 0 26px 40px -22px rgba(255,255,255,.45), inset 0 -26px 36px -26px rgba(0,0,0,.22),
    0 30px 60px -18px rgba(0,0,0,.5), 0 4px 12px rgba(0,0,0,.16);
}
[data-testid="stPlotlyChart"] { padding: .7rem .5rem; }
div[data-testid="stMetric"] { padding: .9rem 1.1rem; }
[data-testid="stExpander"] details { border-radius: 20px !important; }

[data-testid="stSidebar"] {
  background: linear-gradient(180deg, rgba(255,255,255,.12), rgba(255,255,255,.04)), rgba(15,22,45,.25) !important;
  backdrop-filter: blur(30px) saturate(200%); -webkit-backdrop-filter: blur(30px) saturate(200%);
  border-right: none; box-shadow: inset -1px 0 0 rgba(255,255,255,.25), 10px 0 40px rgba(0,0,0,.25);
}
/* light liquid-glass form controls */
[data-rac][role="group"], [data-testid="stTextInputRootElement"], [data-testid="stDateInput"] > div > div,
[data-testid="stNumberInput"] > div > div, [data-baseweb="select"] > div, [data-baseweb="input"] {
  background: linear-gradient(180deg, rgba(255,255,255,.26), rgba(255,255,255,.14)) !important;
  border: 1px solid rgba(255,255,255,.38) !important; border-radius: 16px !important; color: #fff !important;
  backdrop-filter: blur(18px) saturate(180%); -webkit-backdrop-filter: blur(18px) saturate(180%);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.55), inset 0 -1px 0 rgba(255,255,255,.1), 0 6px 18px -8px rgba(0,0,0,.35) !important;
  transition: background .25s, box-shadow .25s;
}
[data-rac][role="group"]:hover, [data-testid="stTextInputRootElement"]:hover {
  background: linear-gradient(180deg, rgba(255,255,255,.34), rgba(255,255,255,.20)) !important;
}
[data-testid="stSelectbox"] [data-rac] *, [data-testid="stMultiSelect"] [data-rac] > div, [data-testid="stTextInputRootElement"] *, [data-baseweb="input"] * { background-color: transparent; color: #fff; }
[data-rac][role="group"] input::placeholder { color: rgba(255,255,255,.7); }
[data-tag] { background: rgba(255,255,255,.30) !important; color: #fff !important; border-radius: 999px !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.5); font-weight: 600; }
[role="listbox"], [data-baseweb="popover"] > div, [data-baseweb="menu"] {
  background: rgba(40,52,85,.62) !important; backdrop-filter: blur(28px) saturate(190%) !important;
  -webkit-backdrop-filter: blur(28px) saturate(190%) !important; border-radius: 18px !important;
  border: 1px solid rgba(255,255,255,.25) !important; box-shadow: inset 0 1px 0 rgba(255,255,255,.4), 0 20px 50px rgba(0,0,0,.45) !important;
}
[role="option"] { border-radius: 12px; margin: 2px 6px; color: #fff; }
[role="option"]:hover, [role="option"][aria-selected="true"] { background: rgba(255,255,255,.18) !important; }
[data-testid="stSlider"] [role="slider"] { background: #fff !important; box-shadow: 0 2px 8px rgba(0,0,0,.35), 0 0 0 4px rgba(255,255,255,.25) !important; }

[data-testid="stSlider"] [data-rac][role="group"] {
  background: none !important; border: none !important; box-shadow: none !important; backdrop-filter: none !important; }
/* segmented view switcher → floating glass pill */
[data-testid="stButtonGroup"] > div { gap: 0 !important; padding: .3rem; border-radius: 999px; width: fit-content;
  background: rgba(255,255,255,.14); backdrop-filter: blur(22px) saturate(180%); -webkit-backdrop-filter: blur(22px) saturate(180%);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.5), 0 10px 30px -12px rgba(0,0,0,.45); }
[data-testid="stButtonGroup"] button { background: transparent !important; border: none !important; border-radius: 999px !important;
  color: #fff !important; font-weight: 600; padding: .4rem 1.1rem !important; box-shadow: none !important; backdrop-filter: none; }
[data-testid="stButtonGroup"] button[kind$="Active"], [data-testid="stButtonGroup"] button[aria-checked="true"],
[data-testid="stButtonGroup"] button[aria-pressed="true"] {
  background: rgba(255,255,255,.30) !important; box-shadow: inset 0 1px 0 rgba(255,255,255,.6), 0 4px 12px -4px rgba(0,0,0,.3) !important; }

/* sidebar typography (iOS Settings style section headers) */
[data-testid="stSidebar"] h4 { font-size: .74rem !important; font-weight: 600 !important; text-transform: uppercase;
  letter-spacing: .09em; color: rgba(255,255,255,.72) !important; margin: 1.1rem 0 .35rem !important; padding: 0 !important; }
[data-testid="stSidebar"] label p { font-size: .86rem !important; font-weight: 500; color: rgba(255,255,255,.92) !important; }
.brand { display: flex; align-items: center; gap: .6rem; margin-bottom: .2rem; }
.brand-icon { width: 34px; height: 34px; border-radius: 10px; flex: none;
  background: radial-gradient(circle at 30% 30%, #fde68a, #f59e0b 45%, transparent 46%), linear-gradient(160deg, #60a5fa, #1d4ed8);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.6), 0 6px 16px -4px rgba(0,0,0,.4); }
.brand-name { font-size: 1.25rem; font-weight: 700; letter-spacing: -.02em; color: #fff; }
.brand-sub { font-size: .76rem; color: rgba(255,255,255,.7); font-weight: 500; }
[data-baseweb="popover"] [role="listbox"], [data-baseweb="popover"] ul {
  background: rgba(30,40,70,.72) !important; backdrop-filter: blur(24px) saturate(180%); border-radius: 16px !important;
}
[data-testid="stSegmentedControl"] button, [data-testid="stPills"] button, .stButton button, .stDownloadButton button {
  background: rgba(255,255,255,.12); border-color: rgba(255,255,255,.22) !important; color: #fff; border-radius: 999px !important;
  backdrop-filter: blur(14px); box-shadow: inset 0 1px 0 rgba(255,255,255,.3);
}
.stTabs [data-baseweb="tab-list"] {
  gap: .25rem; padding: .35rem; border-radius: 999px; width: fit-content; max-width: 100%; overflow-x: auto;
  background: rgba(255,255,255,.10); backdrop-filter: blur(20px) saturate(180%);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.4), 0 10px 30px -12px rgba(0,0,0,.4); border: none;
}
.stTabs [data-baseweb="tab"] { border-radius: 999px; padding: .45rem 1.05rem; font-weight: 600; color: #fff; height: auto; }
.stTabs [aria-selected="true"] { background: rgba(255,255,255,.22); box-shadow: inset 0 1px 0 rgba(255,255,255,.5); }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none; }

/* ── typography helpers ── */
.card { padding: 1.15rem 1.3rem; animation: fadeUp .8s cubic-bezier(.2,.8,.2,1) both; height: 100%; color: #fff; }
.card-label { color: var(--muted); font-size: .72rem; font-weight: 600; text-transform: uppercase; letter-spacing: .07em;
  display: flex; align-items: center; gap: .4rem; }
.card-value { font-size: 1.75rem; font-weight: 600; margin-top: .2rem; letter-spacing: -.01em; }
.card-unit { color: var(--muted); font-size: .8rem; font-weight: 500; margin-left: .25rem; }
.muted { color: var(--muted); }
.sep { height: 1px; background: rgba(255,255,255,.16); margin: .75rem 0; }

.hero-title { font-size: 2.2rem; font-weight: 600; letter-spacing: -.02em; color: #fff; margin: 0; text-shadow: 0 2px 12px rgba(0,0,0,.3); }
.hero-sub { color: var(--soft); margin-top: .3rem; }

/* ── iOS-style hero ── */
.hero { text-align: center; padding: 1.2rem 0 1.6rem; color: #fff; text-shadow: 0 2px 12px rgba(0,0,0,.25); }
.hero-loc { font-size: 2.1rem; font-weight: 500; letter-spacing: -.01em; }
.hero-zone { font-size: .82rem; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: var(--soft); }
.hero-aqi { font-size: 7.5rem; font-weight: 200; line-height: 1; letter-spacing: -.04em; margin: .2rem 0 .1rem;
  counter-reset: num var(--num); animation: count 1.8s cubic-bezier(.2,.8,.2,1) both; }
.hero-aqi::after { content: counter(num); }
.hero-cat { font-size: 1.35rem; font-weight: 600; display: inline-flex; align-items: center; gap: .5rem; }
.hero-dot { width: 12px; height: 12px; border-radius: 50%; position: relative; display: inline-block; }
.hero-dot::after { content: ""; position: absolute; inset: 0; border-radius: 50%; background: inherit; animation: ring 2s ease-out infinite; }
.hero-hl { font-size: 1.05rem; font-weight: 500; margin-top: .25rem; color: var(--soft); }
.live-pill {
  display: inline-flex; align-items: center; gap: .5rem; padding: .32rem .8rem; border-radius: 999px; margin-top: .9rem;
  background: rgba(255,255,255,.14); backdrop-filter: blur(16px); color: #fff; font-size: .75rem; font-weight: 600;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.45);
}
.live-dot { width: 8px; height: 8px; border-radius: 50%; background: #4ade80; animation: pulse 1.8s infinite; }
.paused .live-dot { background: #cbd5e1; animation: none; }

.station-pill { display: inline-flex; align-items: center; gap: .45rem; margin-top: .7rem; padding: .38rem .9rem;
  border-radius: 999px; font-size: .82rem; background: rgba(255,255,255,.16); backdrop-filter: blur(16px);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.45); max-width: 100%; flex-wrap: wrap; justify-content: center; }
.station-pill .sdot { width: 8px; height: 8px; border-radius: 50%; box-shadow: 0 0 8px currentColor; }
/* ── hourly strip ── */
.summary { font-size: .95rem; line-height: 1.45; color: #fff; }
.hours { display: flex; gap: .2rem; overflow-x: auto; padding: .2rem 0 .3rem; scrollbar-width: thin; }
.hours::-webkit-scrollbar { height: 6px; } .hours::-webkit-scrollbar-thumb { background: rgba(255,255,255,.25); border-radius: 9px; }
.hr { flex: 0 0 64px; text-align: center; padding: .55rem 0; border-radius: 18px; transition: background .25s; }
.hr:hover { background: rgba(255,255,255,.10); }
.hr .t { font-size: .82rem; font-weight: 600; }
.hr .e { font-size: 1.35rem; margin: .4rem 0; }
.hr .v { font-size: 1.05rem; font-weight: 600; }
.hr .b { height: 4px; width: 26px; margin: .4rem auto 0; border-radius: 9px; }
.hr.now { background: rgba(255,255,255,.14); box-shadow: inset 0 1px 0 rgba(255,255,255,.35); }

/* ── daily range bars ── */
.day { display: grid; grid-template-columns: 4.2rem 2rem 2.4rem 1fr 2.4rem; align-items: center; gap: .6rem; padding: .62rem 0;
  border-top: 1px solid rgba(255,255,255,.14); font-weight: 600; }
.day:first-of-type { border-top: none; }
.day .lo { color: var(--muted); text-align: right; }
.track { position: relative; height: 6px; border-radius: 99px; background: rgba(0,0,0,.22); box-shadow: inset 0 1px 2px rgba(0,0,0,.25); }
.track > .fill { position: absolute; top: 0; bottom: 0; border-radius: 99px; animation: grow 1.2s cubic-bezier(.2,.8,.2,1) both; }
.track > .cur { position: absolute; top: 50%; width: 10px; height: 10px; border-radius: 50%; background: #fff;
  transform: translate(-50%,-50%); box-shadow: 0 0 0 2.5px rgba(0,0,0,.35); }

/* ── tiles ── */
.tiles { display: grid; grid-template-columns: repeat(3, 1fr); gap: .9rem; }
.tile { min-height: 150px; display: flex; flex-direction: column; }
.tile .big { font-size: 1.9rem; font-weight: 500; margin-top: .35rem; letter-spacing: -.01em; }
.tile .note { margin-top: auto; font-size: .82rem; color: var(--soft); line-height: 1.35; }

/* ── AQI scale ── */
.scale-track { position: relative; height: 14px; border-radius: 99px; margin: 2.6rem .4rem .5rem;
  box-shadow: inset 0 1px 2px rgba(0,0,0,.35), 0 0 0 1px rgba(255,255,255,.18); }
.knob { position: absolute; top: 50%; width: 26px; height: 26px; border-radius: 50%; transform: translate(-50%,-50%);
  background: radial-gradient(circle at 35% 30%, #fff, rgba(255,255,255,.75) 55%, rgba(255,255,255,.5));
  box-shadow: 0 0 0 4px rgba(255,255,255,.25), 0 4px 14px rgba(0,0,0,.4); animation: slideKnob 1.6s cubic-bezier(.2,.8,.2,1) both; }
.knob .bubble { position: absolute; bottom: 36px; left: 50%; transform: translateX(-50%); white-space: nowrap;
  padding: .28rem .7rem; border-radius: 999px; font-size: .78rem; font-weight: 700; color: #fff;
  background: rgba(15,20,40,.55); backdrop-filter: blur(10px); box-shadow: inset 0 1px 0 rgba(255,255,255,.3); }
.knob .bubble::after { content: ""; position: absolute; top: 100%; left: 50%; transform: translateX(-50%);
  border: 6px solid transparent; border-top-color: rgba(15,20,40,.55); }
.ticks { position: relative; height: 1.1rem; margin: 0 .4rem; font-size: .7rem; color: var(--muted); }
.ticks span { position: absolute; transform: translateX(-50%); }
.chips { display: grid; grid-template-columns: repeat(6, 1fr); gap: .6rem; margin-top: .9rem; }
.chip-cat { border-radius: 20px; padding: .75rem .7rem; background: rgba(255,255,255,.07);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.18); transition: transform .3s, background .3s; position: relative; overflow: hidden; }
.chip-cat:hover { transform: translateY(-2px); background: rgba(255,255,255,.12); }
.chip-cat .nm { font-weight: 700; font-size: .88rem; display: flex; align-items: center; gap: .4rem; }
.chip-cat .sw { width: 10px; height: 10px; border-radius: 50%; flex: none; }
.chip-cat .rg { font-size: .72rem; color: var(--muted); margin-top: .15rem; font-weight: 600; }
.chip-cat .ds { font-size: .74rem; color: var(--soft); margin-top: .4rem; line-height: 1.3; }
.chip-cat.on { background: rgba(255,255,255,.2); box-shadow: inset 0 1px 0 rgba(255,255,255,.5), 0 0 0 1.5px var(--c), 0 0 26px -4px var(--c); }
.chip-cat.on::after { content: "NOW"; position: absolute; top: .55rem; right: .65rem; font-size: .58rem; font-weight: 800;
  letter-spacing: .08em; padding: .1rem .4rem; border-radius: 99px; background: var(--c); color: #111; }

/* ── pollutant cards ── */
.pgrid { display: grid; grid-template-columns: repeat(4, 1fr); gap: .9rem; }
.pcard.focus { box-shadow: inset 0 1.5px 0.5px rgba(255,255,255,.7), 0 0 0 2px rgba(125,211,252,.9), 0 0 34px -4px rgba(125,211,252,.6),
  0 24px 48px -16px rgba(0,0,0,.45) !important; }
.bar { height: 6px; border-radius: 99px; background: rgba(0,0,0,.22); margin-top: .75rem; overflow: hidden; box-shadow: inset 0 1px 2px rgba(0,0,0,.25); }
.bar > span { display: block; height: 100%; border-radius: 99px; animation: grow 1.3s cubic-bezier(.2,.8,.2,1) both; }
.chip { display: inline-block; font-size: .7rem; font-weight: 600; padding: .16rem .55rem; border-radius: 999px;
  background: rgba(255,255,255,.14); color: #fff; margin-top: .6rem; box-shadow: inset 0 1px 0 rgba(255,255,255,.2); }

.tip { display: flex; gap: .7rem; align-items: flex-start; padding: .6rem 0; border-bottom: 1px solid rgba(255,255,255,.12); }
.tip:last-child { border-bottom: none; }
.tip .ic { font-size: 1.15rem; }
.rec-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: .9rem; }
.rec { text-align: center; padding: 1.1rem .6rem; }
.rec .ic { font-size: 2rem; animation: floaty 3.5s ease-in-out infinite; }
.rec .v { font-weight: 700; margin-top: .3rem; }
.emoji { font-size: 2.4rem; display: inline-block; animation: floaty 3s ease-in-out infinite; }

.footer { color: var(--soft); font-size: .78rem; text-align: center; margin-top: 2.5rem; line-height: 1.6; text-shadow: 0 1px 2px rgba(0,0,0,.4); }
.footer a { color: #fff; }

@media (max-width: 1000px) {
  .pgrid, .rec-grid { grid-template-columns: repeat(2, 1fr); }
  .tiles { grid-template-columns: repeat(2, 1fr); }
  .chips { grid-template-columns: repeat(3, 1fr); }
  .hero-aqi { font-size: 5.5rem; }
}
@media (max-width: 640px) {
  .block-container { padding: .6rem .7rem 3rem !important; }
  .hero { padding: .4rem 0 1rem; } .hero-loc { font-size: 1.7rem; } .hero-aqi { font-size: 5.2rem; }
  .hero-cat { font-size: 1.15rem; } .hero-hl { font-size: .92rem; }
  .card { padding: .95rem 1rem; border-radius: 22px !important; }
  .tiles { grid-template-columns: repeat(2, 1fr); gap: .6rem; } .tile { min-height: 128px; } .tile .big { font-size: 1.5rem; }
  .pgrid { grid-template-columns: repeat(2, 1fr); gap: .6rem; } .card-value { font-size: 1.4rem; }
  .chips { grid-template-columns: repeat(2, 1fr); } .chip-cat .ds { display: none; }
  .day { grid-template-columns: 3.4rem 1.6rem 2rem 1fr 2rem; gap: .4rem; font-size: .9rem; }
  .hr { flex-basis: 54px; } .rec-grid { grid-template-columns: repeat(2, 1fr); }
  [data-testid="stButtonGroup"] > div { overflow-x: auto; max-width: 100%; flex-wrap: nowrap !important; }
  [data-testid="stButtonGroup"] button { padding: .35rem .75rem !important; font-size: .82rem; white-space: nowrap; }
  .stTabs [data-baseweb="tab"] { padding: .4rem .75rem; font-size: .84rem; }
  .xp-bar .xp-btn[data-act="copy"] { display: none; }
}
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation: none !important; transition: none !important; } }
</style>
"""

PLOT_BG = "rgba(0,0,0,0)"
FONT = dict(family="-apple-system, BlinkMacSystemFont, Inter, sans-serif", color="#ffffff", size=12)
SERIES_COLORS = ["#7dd3fc", "#f9a8d4", "#c4b5fd", "#fde047", "#6ee7b7", "#fdba74", "#fca5a5", "#67e8f9"]


def style_fig(fig: go.Figure, height=380, legend=True) -> go.Figure:
    fig.update_layout(
        template="plotly_dark", paper_bgcolor=PLOT_BG, plot_bgcolor=PLOT_BG, font=FONT, height=height,
        margin=dict(l=10, r=10, t=44, b=10), hovermode="x unified", colorway=SERIES_COLORS,
        title_font=dict(size=15, color="#fff"),
        legend=dict(orientation="h", yanchor="top", y=-0.12, xanchor="left", x=0, bgcolor=PLOT_BG) if legend else None,
        showlegend=legend, hoverlabel=dict(bgcolor="rgba(15,20,40,.85)", bordercolor="rgba(255,255,255,.3)", font=FONT),
        transition=dict(duration=500, easing="cubic-in-out"),
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.10)", zeroline=False, linecolor="rgba(255,255,255,.2)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.10)", zeroline=False)
    return fig


def hex_to_rgba(hex_colour, alpha):
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def compact(html: str) -> str:
    """Collapse indentation so Streamlit's markdown renderer never treats HTML as a code block."""
    return " ".join(line.strip() for line in html.splitlines() if line.strip())


def scale_gradient(cats, max_val=500):
    stops, lo = [], 0
    for hi, _, col, _ in cats:
        mid = (lo + min(hi, max_val)) / 2
        stops.append(f"{col} {mid / max_val * 100:.1f}%")
        lo = hi
    return "linear-gradient(90deg," + ",".join(stops) + ")"


def scale_html(cats, active_idx, aqi=None, descriptions=None, max_val=500, detail=None):
    from i18n import t
    """Rounded gradient AQI track with a marker, plus a detailed chip for every category."""
    descriptions = descriptions or {}
    knob = ""
    if aqi is not None and not pd.isna(aqi):
        pos = max(0.0, min(100.0, aqi / max_val * 100))
        name = cats[max(active_idx, 0)][1]
        knob = f'<div class="knob" style="left:{pos:.1f}%"><div class="bubble">{aqi:.0f} · {t(name)}</div></div>'
    ticks = "".join(f'<span style="left:{v / max_val * 100:.1f}%">{v}</span>' for v in [0] + [c[0] for c in cats])
    chips, lo = [], 0
    for i, (hi, name, col, emo) in enumerate(cats):
        on = " on" if i == active_idx else ""
        chips.append(f'<div class="chip-cat{on}" style="--c:{col}"><div class="nm"><span class="sw" style="background:{col};'
                     f'box-shadow:0 0 10px {col}"></span>{t(name)}</div><div class="rg">{emo} {lo if lo == 0 else lo + 1}–{hi}</div>'
                     f'<div class="ds">{descriptions.get(name, "")}</div></div>')
        lo = hi
    return compact(f"""
    <div class="card{' xp' if detail else ''}" {f'data-detail="{detail}"' if detail else ''} style="padding:1.2rem 1.4rem 1.3rem">
      {'<span class="xp-hint">⤢</span>' if detail else ''}<div class="card-label">🎚️ {t('AQI scale')}</div>
      <div class="scale-track" style="background:{scale_gradient(cats, max_val)}">{knob}</div>
      <div class="ticks">{ticks}</div>
      <div class="chips">{''.join(chips)}</div>
    </div>""")
