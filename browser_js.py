"""Small browser-side helpers: geolocation lookup and AQI alert notifications."""
import json
import math
import re
import time

from locations import CITIES, LOCATIONS


def _safe(js: str) -> str:
    # Streamlit's sanitiser drops scripts whose text looks like markup — escape "<tag" inside JS strings.
    return re.sub(r"<(?=[/\w!])", r"\\x3c", js)


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def nearest_locality(lat, lon):
    """(nearest locality, km to it, km to that city's centre)."""
    name = min(LOCATIONS, key=lambda n: haversine_km(lat, lon, LOCATIONS[n]["lat"], LOCATIONS[n]["lon"]))
    c = CITIES[LOCATIONS[name]["city"]]["center"]
    return name, haversine_km(lat, lon, LOCATIONS[name]["lat"], LOCATIONS[name]["lon"]), haversine_km(lat, lon, c["lat"], c["lon"])


def geolocate_html() -> str:
    """Ask the browser for its position, then reload with ?near=lat,lon."""
    return "<script>" + _safe("""
(function () {
  const nonce = %d;
  if (window.__geoNonce === nonce) return; window.__geoNonce = nonce;
  const say = m => { const t = document.createElement('div'); t.className = 'xp-toast on'; t.textContent = m;
                     document.body.append(t); setTimeout(() => t.remove(), 3500); };
  if (!navigator.geolocation) { say('Location is not available in this browser'); return; }
  say('Finding your location…');
  navigator.geolocation.getCurrentPosition(p => {
    const u = new URL(window.location.href);
    u.searchParams.set('near', p.coords.latitude.toFixed(4) + ',' + p.coords.longitude.toFixed(4));
    window.location.href = u.toString();
  }, e => say(e.code === 1 ? 'Location permission was denied' : 'Could not get your location'),
     {enableHighAccuracy: false, timeout: 12000, maximumAge: 600000});
})();
""" % int(time.time() * 1000)) + "</script>"


ALERT_CSS = """
<style>
#aqi-alert { position: fixed; top: .9rem; left: 50%; transform: translate(-50%, -140%); z-index: 999980; display: flex;
  align-items: center; gap: .8rem; padding: .7rem .8rem .7rem 1.1rem; border-radius: 999px; color: #fff; max-width: calc(100vw - 2rem);
  background: linear-gradient(135deg, rgba(239,68,68,.55), rgba(185,28,28,.45)); backdrop-filter: blur(22px) saturate(180%);
  -webkit-backdrop-filter: blur(22px) saturate(180%); box-shadow: inset 0 1px 0 rgba(255,255,255,.5), 0 14px 40px -10px rgba(0,0,0,.5);
  transition: transform .6s cubic-bezier(.2,.9,.3,1.3); font-weight: 600; font-size: .9rem; }
#aqi-alert.on { transform: translate(-50%, 0); }
#aqi-alert .pulse { width: 10px; height: 10px; border-radius: 50%; background: #fff; animation: pulse 1.4s infinite; flex: none; }
#aqi-alert button { border: none; border-radius: 999px; padding: .4rem .8rem; font: 600 .8rem var(--font); color: #fff; cursor: pointer;
  background: rgba(255,255,255,.22); box-shadow: inset 0 1px 0 rgba(255,255,255,.5); white-space: nowrap; }
</style>
"""


def alerts_html(cfg: dict) -> str:
    """cfg: enabled, threshold, aqi, cat, loc, std, soon_max, soon_time, soon_cat, hour_key."""
    return ALERT_CSS + "<script>" + _safe("""
(function () {
  const c = %s;
  let bar = document.getElementById('aqi-alert');
  if (!c.enabled) { if (bar) bar.classList.remove('on'); return; }
  const now = c.aqi >= c.threshold, soon = !now && c.soon_max != null && c.soon_max >= c.threshold;
  if (!now && !soon) { if (bar) bar.classList.remove('on'); return; }
  const msg = now ? `AQI ${Math.round(c.aqi)} (${c.cat}) at ${c.loc} is above your alert level`
                  : `AQI expected to reach ${Math.round(c.soon_max)} (${c.soon_cat}) around ${c.soon_time} at ${c.loc}`;
  if (!bar) { bar = document.createElement('div'); bar.id = 'aqi-alert'; document.body.append(bar); }
  const perm = ('Notification' in window) ? Notification.permission : 'unsupported';
  bar.innerHTML = '<span class="pulse"></span><span>⚠️ ' + msg + '</span>' +
    (perm === 'default' ? '<button data-a="perm">🔔 Enable notifications</button>' : '') + '<button data-a="x">✕</button>';
  bar.onclick = e => { const a = e.target.dataset.a;
    if (a === 'x') bar.classList.remove('on');
    if (a === 'perm') Notification.requestPermission().then(() => { e.target.remove(); notify(); }); };
  requestAnimationFrame(() => bar.classList.add('on'));
  function notify() {
    if (!('Notification' in window) || Notification.permission !== 'granted') return;
    const key = 'aqi-alert-' + c.hour_key + (now ? '-now' : '-soon');
    try { if (localStorage.getItem(key)) return; localStorage.setItem(key, '1'); } catch (e) {}
    new Notification('AQIfyMe · AQI alert', {body: msg, tag: 'aqi-alert'});
  }
  notify();
})();
""" % json.dumps(cfg)) + "</script>"
