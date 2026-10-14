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
  float cover = mix(0.62, 0.36, pol);            // worse air → more cloud / smog cover
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
  const U = {}; ['uRes','uTime','uAqi','uDay','uDusk','uSun'].forEach(n => U[n] = gl.getUniformLocation(prog, n));

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
    for (const k of ['aqi','day','dusk','sx','sy']) cur[k] += (tgt[k] - cur[k]) * 0.04;
    let t = (now - t0) / 1000 + 400;
    if (tgt.paused || reduce) { if (frozenAt === null) frozenAt = t; t = frozenAt; } else frozenAt = null;
    gl.uniform2f(U.uRes, canvas.width, canvas.height); gl.uniform1f(U.uTime, t);
    gl.uniform1f(U.uAqi, cur.aqi); gl.uniform1f(U.uDay, cur.day); gl.uniform1f(U.uDusk, cur.dusk);
    gl.uniform2f(U.uSun, cur.sx, cur.sy);
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


def sky_html(level: float, hour: float, paused: bool = False) -> str:
    return (JS.replace("__TARGET__", json.dumps(sky_state(level, hour, paused)))
              .replace("__SHADER__", json.dumps(FRAGMENT_SHADER)))
