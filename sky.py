"""Realistic animated sky (WebGL shader) whose clouds, haze and sunlight react to the AQI.

The canvas is injected once into the page and lives behind the Streamlit app; later calls only
update its target values, so it eases smoothly between states instead of restarting.
"""
import json
import math

FRAGMENT_SHADER = r"""
precision highp float;
uniform vec2  uRes;
uniform float uTime;
uniform float uAqi;    // 0 (Good) .. 5 (Severe), eased
uniform float uDay;    // 0 night .. 1 day
uniform float uDusk;   // 0..1 sunrise / sunset warmth
uniform vec2  uSun;    // sun (or moon) position in uv space
uniform float uCloud;  // 0..1 real cloud cover
uniform float uRain;   // 0..1
uniform float uSnow;   // 0..1
uniform float uStorm;  // 0..1 thunderstorm (lightning)
uniform float uFog;    // 0..1

float hash(vec2 p){ p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
float noise(vec2 p){
  vec2 i = floor(p), f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y);
}
float fbm(vec2 p){
  float v = 0.0, a = 0.5;
  mat2 m = mat2(1.6, 1.2, -1.2, 1.6);
  for (int i = 0; i < 6; i++) { v += a * noise(p); p = m * p; a *= 0.5; }
  return v;
}

// cloud density for one layer
float clouds(vec2 p, float t, float cover){
  vec2 q = p + vec2(t, 0.0);
  float warp = fbm(q * 0.6 + vec2(0.0, t * 0.6));
  float n = fbm(q + warp * 0.9);
  return smoothstep(cover, cover + 0.32, n);
}

void main(){
  vec2 uv = gl_FragCoord.xy / uRes;
  float aspect = uRes.x / uRes.y;
  vec2 p = vec2(uv.x * aspect, uv.y);
  vec2 sp = vec2(uSun.x * aspect, uSun.y);
  float pol = clamp(uAqi / 5.0, 0.0, 1.0);

  // ── sky gradient ───────────────────────────────────────────────────────────
  vec3 dayZen  = mix(vec3(0.10, 0.33, 0.78), vec3(0.42, 0.40, 0.36), pol);
  vec3 dayHor  = mix(vec3(0.58, 0.78, 0.97), vec3(0.86, 0.70, 0.46), pol);
  vec3 nightZen = mix(vec3(0.010, 0.020, 0.065), vec3(0.06, 0.04, 0.035), pol);
  vec3 nightHor = mix(vec3(0.05, 0.09, 0.20), vec3(0.34, 0.18, 0.08), pol);   // smog glows with city lights
  vec3 duskHor  = vec3(1.00, 0.55, 0.30);
  float h = pow(1.0 - uv.y, 1.6);
  vec3 zen = mix(nightZen, dayZen, uDay);
  vec3 hor = mix(nightHor, dayHor, uDay);
  hor = mix(hor, mix(duskHor, vec3(0.80, 0.40, 0.20), pol), uDusk * 0.75);
  vec3 col = mix(zen, hor, h);

  // ── sun / moon ─────────────────────────────────────────────────────────────
  float d = distance(p, sp);
  vec3 sunCol = mix(vec3(1.0, 0.96, 0.86), vec3(1.0, 0.55, 0.25), max(pol, uDusk));
  float sunVis = mix(1.0, 0.35, pol);
  vec3 moonCol = vec3(0.86, 0.90, 1.0);
  if (uDay > 0.01) {
    col += sunCol * exp(-d * mix(4.0, 2.2, pol)) * 0.55 * sunVis * uDay;   // wide glow
    col += sunCol * exp(-d * 18.0) * 0.6 * sunVis * uDay;                 // halo
    col = mix(col, sunCol * 1.6, smoothstep(0.045, 0.038, d) * sunVis * uDay);   // disc
  }
  float night = 1.0 - uDay;
  if (night > 0.01) {
    // stars, hidden by smog
    vec2 cellp = gl_FragCoord.xy / 9.0;
    vec2 g = floor(cellp);
    vec2 off = vec2(hash(g + 1.3), hash(g + 7.7)) - 0.5;
    float dd = length(fract(cellp) - 0.5 - off * 0.6);
    float s = step(0.955, hash(g)) * smoothstep(0.16, 0.0, dd) * (0.35 + 0.65 * hash(g + 2.0));
    float tw = 0.65 + 0.35 * sin(uTime * (1.0 + hash(g + 3.1) * 3.0) + hash(g) * 30.0);
    col += vec3(0.9, 0.93, 1.0) * s * tw * night * (1.0 - pol * 0.9) * smoothstep(0.15, 0.6, uv.y);
    // moon with soft halo (bigger halo in haze)
    float md = d;
    col += moonCol * exp(-md * mix(10.0, 4.5, pol)) * 0.22 * night;
    float disc = smoothstep(0.034, 0.030, md);
    float crater = fbm(p * 60.0) * 0.25;
    col = mix(col, moonCol * (0.95 - crater) * mix(1.0, 0.75, pol), disc * night);
  }

  // ── clouds (two parallax layers, lit from the sun / moon) ──────────────────
  float t = uTime * 0.008;
  float wet = max(uRain, max(uSnow, uStorm));
  float cover = mix(0.62, 0.36, pol) - 0.30 * uCloud - 0.12 * wet;   // worse air or real clouds → more cover
  vec2 cp = p * vec2(1.1, 2.4);
  float far  = clouds(cp * 1.7 + 11.0, t * 0.6, cover + 0.06) * 0.55;
  float near = clouds(cp, t, cover);
  near *= smoothstep(0.02, 0.35, uv.y);
  vec2 toSun = normalize(sp - p + 1e-4);
  float nearL = clouds(cp + vec2(toSun.x, toSun.y * 2.4) * 0.06, t, cover);
  float light = clamp(1.0 - (nearL - near) * 1.8, 0.0, 1.0);  // samples toward the light are thinner → brighter

  vec3 litDay   = mix(vec3(1.0, 0.99, 0.97), vec3(0.85, 0.74, 0.58), pol);
  vec3 shadeDay = mix(vec3(0.56, 0.62, 0.74), vec3(0.45, 0.38, 0.30), pol);
  vec3 litNight = mix(vec3(0.20, 0.23, 0.31), vec3(0.42, 0.26, 0.14), pol);
  vec3 shadeNight = mix(vec3(0.05, 0.06, 0.10), vec3(0.16, 0.09, 0.05), pol);
  vec3 lit = mix(litNight, litDay, uDay);
  vec3 shade = mix(shadeNight, shadeDay, uDay);
  lit = mix(lit, vec3(1.0, 0.72, 0.50), uDusk * 0.5);
  shade *= 1.0 - 0.45 * wet; lit *= 1.0 - 0.35 * wet;          // rain clouds are dark and heavy
  vec3 cloudCol = mix(shade, lit, light);
  // silver lining near the sun
  cloudCol += sunCol * exp(-d * 5.0) * (1.0 - near) * near * 2.2 * uDay * sunVis;

  col = mix(col, mix(shade, lit, 0.7), far * (0.55 + 0.3 * pol));
  col = mix(col, cloudCol, near * (0.88 + 0.1 * pol));

  // ── smog haze: thick near the ground, drifting ─────────────────────────────
  vec3 smogDay = vec3(0.72, 0.60, 0.44);
  vec3 smogNight = vec3(0.26, 0.15, 0.08);
  vec3 smog = mix(smogNight, smogDay, uDay);
  float drift = fbm(p * 1.4 + vec2(uTime * 0.012, uTime * 0.004));
  float fog = pol * (0.12 + 0.75 * pow(1.0 - uv.y, 1.4)) * (0.75 + 0.5 * drift);
  col = mix(col, smog, clamp(fog, 0.0, 0.92));

  // floating particulate specks on bad days
  if (pol > 0.35) {
    vec2 gp = gl_FragCoord.xy / 6.0 + vec2(uTime * 2.0, sin(uTime * 0.3) * 4.0);
    vec2 cell = floor(gp);
    float r = hash(cell);
    float speck = step(0.992, r) * smoothstep(0.5, 0.0, length(fract(gp) - 0.5));
    col += vec3(1.0, 0.85, 0.6) * speck * (pol - 0.35) * 0.35;
  }

  // ── weather: fog, rain, snow, lightning ─────────────────────────────────────
  vec3 fogCol = mix(vec3(0.16, 0.17, 0.20), vec3(0.78, 0.80, 0.82), uDay);
  col = mix(col, fogCol, uFog * (0.45 + 0.45 * (1.0 - uv.y)) * (0.8 + 0.2 * drift));
  col = mix(col, col * 0.72, wet * 0.5);                                      // overcast gloom
  if (uRain > 0.01) {
    for (int k = 0; k < 2; k++) {
      float sc = k == 0 ? 1.0 : 0.6;
      vec2 rp = gl_FragCoord.xy / vec2(7.0 * sc, 46.0 * sc);
      rp.x += rp.y * 0.18;
      rp.y += uTime * (k == 0 ? 3.2 : 2.2);
      vec2 id = floor(rp); vec2 f = fract(rp);
      float r = hash(id + float(k) * 13.0);
      float streak = step(1.0 - 0.35 * uRain, r) * smoothstep(0.08, 0.0, abs(f.x - fract(r * 7.3) * 0.8 - 0.1))
                     * smoothstep(0.0, 0.25, f.y) * smoothstep(1.0, 0.45, f.y);
      col += vec3(0.75, 0.8, 0.9) * streak * (k == 0 ? 0.33 : 0.18) * uRain;
    }
  }
  if (uSnow > 0.01) {
    for (int k = 0; k < 2; k++) {
      float sc = k == 0 ? 26.0 : 15.0;
      vec2 sp2 = gl_FragCoord.xy / sc;
      sp2.y += uTime * (k == 0 ? 0.55 : 0.35);
      sp2.x += sin(uTime * 0.7 + sp2.y * 1.3) * 0.25;
      vec2 id = floor(sp2); vec2 f = fract(sp2) - 0.5;
      float r = hash(id + float(k) * 7.0);
      vec2 off = vec2(hash(id + 2.1), hash(id + 5.3)) - 0.5;
      float flake = step(1.0 - 0.55 * uSnow, r) * smoothstep(k == 0 ? 0.13 : 0.09, 0.0, length(f - off * 0.6));
      col += vec3(1.0) * flake * (k == 0 ? 0.85 : 0.55) * uSnow;
    }
  }
  if (uStorm > 0.01) {
    float slot = floor(uTime * 2.5);
    float strike = step(0.965, hash(vec2(slot, 3.7)));
    float flick = strike * (0.6 + 0.4 * sin(uTime * 60.0)) * smoothstep(1.0, 0.0, fract(uTime * 2.5) * 3.0);
    col += vec3(0.8, 0.85, 1.0) * flick * uStorm * (0.35 + 0.65 * near);
  }

  // vignette + dithering to avoid banding
  vec2 vc = uv - 0.5;
  col *= 1.0 - dot(vc, vc) * 0.35;
  col += (hash(gl_FragCoord.xy + uTime) - 0.5) / 255.0;
  gl_FragColor = vec4(col, 1.0);
}
"""

JS = r"""
<script>
(function () {
  const target = __TARGET__;
  const W = window;
  if (W.__aqiSky) { W.__aqiSky.set(target); return; }

  const canvas = document.createElement('canvas');
  canvas.id = 'aqi-sky';
  Object.assign(canvas.style, {position: 'fixed', inset: '0', width: '100vw', height: '100vh',
                               zIndex: '-1', pointerEvents: 'none', transition: 'opacity 1.2s ease', opacity: '0'});
  document.body.prepend(canvas);
  const gl = canvas.getContext('webgl', {antialias: false, premultipliedAlpha: false});
  const fallback = () => { document.body.classList.add('sky-fallback'); canvas.remove(); };
  if (!gl) { fallback(); W.__aqiSky = {set(){}}; return; }

  const vs = 'attribute vec2 a;void main(){gl_Position=vec4(a,0.,1.);}';
  const fs = __SHADER__;
  function sh(type, src) { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) { console.error(gl.getShaderInfoLog(s)); } return s; }
  const prog = gl.createProgram();
  gl.attachShader(prog, sh(gl.VERTEX_SHADER, vs)); gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, fs));
  gl.linkProgram(prog);
  if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) { fallback(); W.__aqiSky = {set(){}}; return; }
  gl.useProgram(prog);
  const buf = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buf);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1, 1,-1, -1,1, 1,1]), gl.STATIC_DRAW);
  const loc = gl.getAttribLocation(prog, 'a'); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
  const U = {}; ['uRes','uTime','uAqi','uDay','uDusk','uSun','uCloud','uRain','uSnow','uStorm','uFog'].forEach(n => U[n] = gl.getUniformLocation(prog, n));

  const SCALE = 0.5;                       // render at half resolution; clouds are soft anyway
  function resize() { canvas.width = Math.max(2, innerWidth * SCALE); canvas.height = Math.max(2, innerHeight * SCALE);
                      gl.viewport(0, 0, canvas.width, canvas.height); }
  addEventListener('resize', resize); resize();

  const cur = Object.assign({}, target);
  let tgt = Object.assign({}, target);
  const t0 = performance.now(); let last = 0; let frozenAt = null;
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  function frame(now) {
    requestAnimationFrame(frame);
    if (document.hidden || now - last < 1000 / 30) return;   // cap at 30 fps
    last = now;
    for (const k of ['aqi','day','dusk','sx','sy','cloud','rain','snow','storm','fog']) cur[k] += ((tgt[k] || 0) - (cur[k] || 0)) * 0.04;
    let t = (now - t0) / 1000 + 400;
    if (tgt.paused || reduce) { if (frozenAt === null) frozenAt = t; t = frozenAt; } else frozenAt = null;
    gl.uniform2f(U.uRes, canvas.width, canvas.height); gl.uniform1f(U.uTime, t);
    gl.uniform1f(U.uAqi, cur.aqi); gl.uniform1f(U.uDay, cur.day); gl.uniform1f(U.uDusk, cur.dusk);
    gl.uniform2f(U.uSun, cur.sx, cur.sy);
    gl.uniform1f(U.uCloud, cur.cloud || 0); gl.uniform1f(U.uRain, cur.rain || 0); gl.uniform1f(U.uSnow, cur.snow || 0);
    gl.uniform1f(U.uStorm, cur.storm || 0); gl.uniform1f(U.uFog, cur.fog || 0);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    canvas.style.opacity = '1';
  }
  requestAnimationFrame(frame);

  // specular highlight on glass cards follows the pointer
  document.addEventListener('pointermove', e => {
    const c = e.target.closest && e.target.closest('.card');
    if (!c) return;
    const r = c.getBoundingClientRect();
    c.style.setProperty('--mx', ((e.clientX - r.left) / r.width * 100).toFixed(1) + '%');
    c.style.setProperty('--my', ((e.clientY - r.top) / r.height * 100).toFixed(1) + '%');
  }, {passive: true});

  W.__aqiSky = { set(v) { tgt = Object.assign({}, v); } };
})();
</script>
"""


RAIN = {51: .3, 53: .45, 55: .6, 56: .4, 57: .55, 61: .5, 63: .75, 65: 1, 66: .6, 67: .85, 80: .6, 81: .85, 82: 1,
        95: .9, 96: 1, 99: 1}
SNOW = {71: .45, 73: .7, 75: 1, 77: .4, 85: .65, 86: 1}
PREVIEW = {"rain": {"rain": .9, "cloud": .9}, "snow": {"snow": .9, "cloud": .8}, "storm": {"rain": 1, "storm": 1, "cloud": 1},
           "fog": {"fog": .9, "cloud": .5}, "clear": {}}


def weather_state(current: dict | None, preview: str | None = None) -> dict:
    """Map Open-Meteo current weather (WMO codes) to sky effect strengths 0..1."""
    if preview in PREVIEW:
        return {"cloud": 0, "rain": 0, "snow": 0, "storm": 0, "fog": 0, **PREVIEW[preview]}
    c = current or {}
    code = int(c.get("weather_code") or 0)
    vis = c.get("visibility")
    fog = .85 if code in (45, 48) else (.5 if vis is not None and vis < 2000 else 0)
    return {"cloud": round((c.get("cloud_cover") or 0) / 100, 2), "rain": RAIN.get(code, 0), "snow": SNOW.get(code, 0),
            "storm": 1.0 if code >= 95 else 0, "fog": fog}


def sky_state(level: float, hour: float, paused: bool = False) -> dict:
    """Sky parameters for an AQI level (0-5) and local hour (0-24)."""
    # daylight: full between 6:30 and 17:30, ramps across dawn and dusk
    def ramp(x, a, b):
        return max(0.0, min(1.0, (x - a) / (b - a)))
    day = ramp(hour, 5.6, 6.8) * (1 - ramp(hour, 17.3, 18.5))
    dusk = max(0.0, 1 - abs(hour - 6.3) / 1.1) + max(0.0, 1 - abs(hour - 17.9) / 1.1)
    if day > 0.01:
        f = ramp(hour, 6.0, 18.0)                       # sun travels left → right
        sx, sy = 0.08 + 0.84 * f, 0.50 + 0.40 * math.sin(math.pi * f)
    else:
        f = ((hour - 18) % 24) / 12                     # moon travels through the night
        sx, sy = 0.10 + 0.80 * f, 0.55 + 0.32 * math.sin(math.pi * min(1, f))
    return {"aqi": float(level), "day": round(day, 3), "dusk": round(min(1.0, dusk), 3),
            "sx": round(sx, 3), "sy": round(sy, 3), "paused": paused}


def sky_html(level: float, hour: float, paused: bool = False, wx: dict | None = None) -> str:
    return (JS.replace("__TARGET__", json.dumps({**sky_state(level, hour, paused), **(wx or {})}))
              .replace("__SHADER__", json.dumps(FRAGMENT_SHADER)))
