"""Click-to-expand glass panels: any element with data-detail="key" grows into a large panel
showing window.__aqiDetails[key]. Also adds 3D tilt + click ripples to cards and chart tooltips."""
import json
import re

EXPAND_CSS = """
<style>
.xp { cursor: pointer; }
.xp .xp-hint { position: absolute; top: .8rem; right: .9rem; width: 26px; height: 26px; border-radius: 50%; display: grid;
  place-items: center; font-size: .78rem; color: #fff; background: rgba(255,255,255,.18); z-index: 3;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.5); opacity: 0; transform: scale(.6) rotate(-45deg);
  transition: opacity .3s, transform .4s cubic-bezier(.2,.9,.3,1.4); pointer-events: none; }
.xp:hover .xp-hint { opacity: 1; transform: none; }
.card.xp:hover { transform: perspective(900px) rotateX(var(--rx, 0deg)) rotateY(var(--ry, 0deg)) translateY(-4px) scale(1.015); }
.ripple { position: absolute; border-radius: 50%; pointer-events: none; z-index: 4; background: rgba(255,255,255,.35);
  transform: scale(0); animation: rip .6s ease-out forwards; }
@keyframes rip { to { transform: scale(1); opacity: 0; } }

/* overlay */
.xp-backdrop { position: fixed; inset: 0; z-index: 999990; background: rgba(4,8,22,.38);
  backdrop-filter: blur(14px) saturate(140%); -webkit-backdrop-filter: blur(14px) saturate(140%); opacity: 0; transition: opacity .45s ease; }
.xp-backdrop.on { opacity: 1; }
.xp-panel { position: fixed; z-index: 999991; overflow: hidden; border-radius: 34px !important; color: #fff;
  background: radial-gradient(140% 80% at 20% 0%, rgba(255,255,255,.22), transparent 50%),
              linear-gradient(165deg, rgba(255,255,255,.20), rgba(255,255,255,.07) 45%, rgba(255,255,255,.12)), rgba(22,30,58,.38) !important;
  backdrop-filter: blur(40px) saturate(220%) brightness(1.08); -webkit-backdrop-filter: blur(40px) saturate(220%) brightness(1.08);
  box-shadow: inset 0 1.5px 0.5px rgba(255,255,255,.7), inset 0 -1px 0.5px rgba(255,255,255,.2),
              inset 0 30px 50px -30px rgba(255,255,255,.4), 0 40px 100px -20px rgba(0,0,0,.6) !important; }
.xp-panel::before { content: ""; position: absolute; inset: 0; border-radius: inherit; padding: 1.4px; pointer-events: none; z-index: 5;
  background: linear-gradient(135deg, rgba(255,255,255,.9), rgba(255,255,255,.15) 25%, rgba(255,255,255,.03) 55%, rgba(255,255,255,.6));
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0); -webkit-mask-composite: xor; mask-composite: exclude; }
.xp-scroll { position: absolute; inset: 0; overflow-y: auto; overflow-x: hidden; padding: 2rem 2.2rem 2.4rem; scrollbar-width: thin; }
.xp-scroll::-webkit-scrollbar { width: 8px; } .xp-scroll::-webkit-scrollbar-thumb { background: rgba(255,255,255,.25); border-radius: 9px; }
.xp-body { opacity: 0; }
.xp-body.in > * { animation: xin .6s cubic-bezier(.2,.8,.2,1) both; }
.xp-body.in > *:nth-child(2) { animation-delay: .06s; } .xp-body.in > *:nth-child(3) { animation-delay: .12s; }
.xp-body.in > *:nth-child(4) { animation-delay: .18s; } .xp-body.in > *:nth-child(5) { animation-delay: .24s; }
.xp-body.in > *:nth-child(n+6) { animation-delay: .3s; }
@keyframes xin { from { opacity: 0; transform: translateY(18px); filter: blur(6px); } to { opacity: 1; transform: none; filter: none; } }
.xp-bar { position: absolute; top: 1rem; right: 1rem; display: flex; gap: .45rem; z-index: 6; }
.xp-btn { height: 36px; min-width: 36px; padding: 0 .8rem; border-radius: 999px; border: none; color: #fff; font: 600 .82rem var(--font);
  background: rgba(255,255,255,.18); box-shadow: inset 0 1px 0 rgba(255,255,255,.5), 0 4px 14px -4px rgba(0,0,0,.35);
  backdrop-filter: blur(10px); cursor: pointer; transition: background .2s, transform .2s; }
.xp-btn:hover { background: rgba(255,255,255,.3); transform: scale(1.06); }
.xp-btn:active { transform: scale(.94); }
.xp-toast { position: fixed; left: 50%; bottom: 2rem; transform: translateX(-50%) translateY(20px); z-index: 999999; opacity: 0;
  padding: .6rem 1.1rem; border-radius: 999px; background: rgba(20,28,52,.7); backdrop-filter: blur(16px); color: #fff; font-weight: 600;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.35); transition: all .35s cubic-bezier(.2,.9,.3,1.3); }
.xp-toast.on { opacity: 1; transform: translateX(-50%); }

/* detail content */
.xhead { padding: .2rem 0 1.2rem; }
.xk { font-size: .78rem; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: rgba(255,255,255,.7); }
.xt { font-size: 2rem; font-weight: 600; letter-spacing: -.02em; margin-top: .2rem; }
.xv { font-size: 4.6rem; font-weight: 200; letter-spacing: -.04em; line-height: 1; margin: .3rem 0; color: var(--c);
  text-shadow: 0 0 40px color-mix(in srgb, var(--c) 50%, transparent); font-variant-numeric: tabular-nums; }
.xu { font-size: 1.1rem; font-weight: 500; color: rgba(255,255,255,.7); margin-left: .4rem; letter-spacing: 0; }
.xs { font-size: 1.05rem; font-weight: 600; }
.xnum { counter-reset: num var(--num); animation: count 1.6s cubic-bezier(.2,.8,.2,1) both; }
.xnum::after { content: counter(num); }
.xsec { margin-top: 1.3rem; padding: 1.1rem 1.2rem; border-radius: 22px; background: rgba(255,255,255,.07);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.18); }
.xsec h4 { margin: 0 0 .8rem !important; padding: 0 !important; font-size: .74rem !important; font-weight: 600 !important;
  letter-spacing: .08em; text-transform: uppercase; color: rgba(255,255,255,.7) !important; }
.xsec p, .xsec li { font-size: .92rem; line-height: 1.55; color: rgba(255,255,255,.9); margin: 0; }
.xnote { margin-top: .7rem !important; font-size: .82rem !important; color: rgba(255,255,255,.75) !important; }
.xgrid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 0 1.1rem; }
.xlist { margin: 0; padding-left: 1.1rem; } .xlist li { margin: .3rem 0; }
.xstats { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: .7rem; }
.xstat { padding: .85rem .95rem; border-radius: 18px; background: rgba(255,255,255,.09); box-shadow: inset 0 1px 0 rgba(255,255,255,.22); }
.xstat .k { font-size: .7rem; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; color: rgba(255,255,255,.65); }
.xstat .v { font-size: 1.45rem; font-weight: 600; margin-top: .2rem; font-variant-numeric: tabular-nums; }
.xstat .s { font-size: .74rem; color: rgba(255,255,255,.7); margin-top: .1rem; }
.xchart-wrap { position: relative; }
.xchart { width: 100%; height: auto; display: block; overflow: visible; }
.xchart .ax { font-size: 11px; fill: rgba(255,255,255,.6); font-family: var(--font); }
.xchart .draw { stroke-dasharray: 1; stroke-dashoffset: 1; animation: draw 1.6s cubic-bezier(.4,0,.2,1) forwards; }
.xchart .area { opacity: 0; animation: areaIn 1s .6s ease forwards; }
@keyframes draw { to { stroke-dashoffset: 0; } }
@keyframes areaIn { to { opacity: 1; } }
.xtip { position: absolute; pointer-events: none; opacity: 0; transform: translate(-50%, -110%); white-space: nowrap; padding: .45rem .7rem;
  border-radius: 12px; background: rgba(15,20,40,.78); backdrop-filter: blur(10px); font-size: .78rem; line-height: 1.45;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.3), 0 8px 20px rgba(0,0,0,.35); transition: opacity .15s; }
.xtip i { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: .35rem; }
.brows { display: flex; flex-direction: column; gap: .55rem; }
.brow { display: grid; grid-template-columns: 9.5rem 1fr 3.4rem; align-items: center; gap: .7rem; font-size: .86rem; }
.brow .bl { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.brow .bv { text-align: right; font-weight: 600; font-variant-numeric: tabular-nums; }
.bt { height: 8px; border-radius: 99px; background: rgba(0,0,0,.25); overflow: hidden; }
.bt span { display: block; height: 100%; border-radius: 99px; animation: grow 1.1s cubic-bezier(.2,.8,.2,1) both; }
.hprof { display: grid; grid-template-columns: repeat(24, 1fr); gap: 3px; height: 120px; align-items: end; }
.hcol { height: 100%; display: flex; flex-direction: column; justify-content: flex-end; align-items: center; }
.hcol span { width: 100%; border-radius: 5px 5px 2px 2px; animation: rise .9s cubic-bezier(.2,.8,.2,1) both; transform-origin: bottom; }
.hcol i { font-size: .62rem; color: rgba(255,255,255,.6); height: .9rem; font-style: normal; margin-top: 3px; }
@keyframes rise { from { transform: scaleY(0); } }
.xhours { display: grid; grid-template-columns: repeat(auto-fill, minmax(62px, 1fr)); gap: .4rem; }
.xh { text-align: center; padding: .5rem .2rem; border-radius: 14px; background: rgba(255,255,255,.07);
  box-shadow: inset 0 -3px 0 var(--c); font-size: .74rem; }
.xh span { display: block; font-size: 1.05rem; font-weight: 700; color: var(--c); }
.xh i { font-style: normal; color: rgba(255,255,255,.55); }
.xtable { width: 100%; border-collapse: collapse; font-size: .86rem; }
.xtable th { text-align: left; font-size: .68rem; letter-spacing: .06em; text-transform: uppercase; color: rgba(255,255,255,.6);
  font-weight: 600; padding: .4rem .5rem; }
.xtable td { padding: .65rem .5rem; border-top: 1px solid rgba(255,255,255,.12); vertical-align: middle; }
.xtable i { font-style: normal; color: rgba(255,255,255,.65); font-size: .76rem; }
.xrecs { display: grid; grid-template-columns: repeat(4, 1fr); gap: .6rem; }
.xrecs div { text-align: center; padding: .8rem .4rem; border-radius: 18px; background: rgba(255,255,255,.09); }
.xrecs span { font-size: 1.8rem; display: block; animation: floaty 3s ease-in-out infinite; }
.xrecs b { display: block; font-size: .86rem; margin-top: .3rem; } .xrecs i { font-style: normal; font-size: .7rem; color: rgba(255,255,255,.65); }
.cigs { display: flex; flex-wrap: wrap; gap: .25rem; } .cig { font-size: 1.5rem; animation: xin .4s both; }
.cig:nth-child(n) { animation-delay: calc(var(--i, 0) * 1ms); }
.xcats { display: grid; grid-template-columns: repeat(3, 1fr); gap: .7rem; }
.xcat { padding: .9rem; border-radius: 18px; background: rgba(255,255,255,.07); box-shadow: inset 0 3px 0 var(--c); }
.xcat.on { background: rgba(255,255,255,.16); box-shadow: inset 0 3px 0 var(--c), 0 0 0 1.5px var(--c), 0 0 30px -6px var(--c); }
.xcat-h { display: flex; align-items: center; gap: .45rem; } .xcat-h span { font-size: 1.3rem; }
.xcat-h b { color: var(--c); } .xcat-h i { margin-left: auto; font-style: normal; font-size: .75rem; color: rgba(255,255,255,.65); }
.xcat p { font-size: .8rem !important; margin: .45rem 0 !important; }
.xcat-g { display: flex; flex-wrap: wrap; gap: .3rem; } .xcat-g span { font-size: .7rem; padding: .15rem .45rem; border-radius: 99px; background: rgba(255,255,255,.1); }
.xpills { display: flex; flex-wrap: wrap; gap: .45rem; }
.xpill { padding: .35rem .75rem; border-radius: 999px; font-size: .8rem; font-weight: 600; background: rgba(255,255,255,.08); box-shadow: inset 0 0 0 1.5px var(--c); }
@media (max-width: 800px) { .xgrid2, .xcats { grid-template-columns: 1fr; } .xrecs { grid-template-columns: repeat(2, 1fr); }
  .xp-scroll { padding: 1.4rem 1.1rem 2rem; } .xv { font-size: 3.4rem; } }
</style>
"""

EXPAND_JS = r"""
<script>
(function () {
  window.__aqiDetails = __DETAILS__;
  if (window.__aqiExpand) return;
  window.__aqiExpand = true;
  const ease = 'cubic-bezier(.2,.85,.25,1)';
  let open = null;   // {el, key, panel, backdrop}

  const keys = () => [...document.querySelectorAll('[data-detail]')].filter(e => window.__aqiDetails[e.dataset.detail]);
  function targetRect() {
    if (innerWidth < 640) return {left: 0, top: 0, width: innerWidth, height: innerHeight};   // full-screen sheet on phones
    const w = Math.min(980, innerWidth - 32), h = Math.min(innerHeight - 48, 900);
    return {left: (innerWidth - w) / 2, top: (innerHeight - h) / 2, width: w, height: h};
  }
  const px = r => ({left: r.left + 'px', top: r.top + 'px', width: r.width + 'px', height: r.height + 'px'});

  function fill(panel, key, dir) {
    const d = window.__aqiDetails[key];
    const body = panel.querySelector('.xp-body');
    const swap = () => {
      body.innerHTML = d.html; body.classList.remove('in'); void body.offsetWidth; body.classList.add('in');
      body.style.opacity = 1; panel.querySelector('.xp-scroll').scrollTop = 0; wireCharts(body);
    };
    if (!dir) return swap();
    body.animate([{opacity: 1, transform: 'none'}, {opacity: 0, transform: `translateX(${-40 * dir}px)`}], {duration: 180, easing: 'ease-in'})
        .onfinish = () => { swap(); body.animate([{opacity: 0, transform: `translateX(${40 * dir}px)`}, {opacity: 1, transform: 'none'}],
                                                 {duration: 320, easing: ease}); };
  }

  function expand(el) {
    const key = el.dataset.detail;
    if (!window.__aqiDetails[key] || open) return;
    const r = el.getBoundingClientRect();
    const backdrop = document.createElement('div'); backdrop.className = 'xp-backdrop';
    const panel = document.createElement('div'); panel.className = 'xp-panel';
    panel.setAttribute('role', 'dialog'); panel.setAttribute('aria-modal', 'true');
    panel.innerHTML = '<div class="xp-scroll"><div class="xp-body"></div></div><div class="xp-bar">' +
      '<button class="xp-btn" data-act="copy" title="Copy summary">⧉ Copy</button>' +
      '<button class="xp-btn" data-act="prev" title="Previous (←)">‹</button><button class="xp-btn" data-act="next" title="Next (→)">›</button>' +
      '<button class="xp-btn" data-act="close" title="Close (Esc)">✕</button></div>';
    Object.assign(panel.style, px(r));
    document.body.append(backdrop, panel);
    el.style.visibility = 'hidden';
    open = {el, key, panel, backdrop};
    document.documentElement.style.overflow = 'hidden';
    requestAnimationFrame(() => backdrop.classList.add('on'));
    const t = targetRect();
    panel.animate([{...px(r), borderRadius: '28px'}, {...px(t), borderRadius: '34px'}], {duration: 620, easing: ease, fill: 'forwards'})
         .onfinish = () => Object.assign(panel.style, px(t));
    setTimeout(() => fill(panel, key), 240);
    panel.addEventListener('click', e => {
      const a = e.target.closest('[data-act]'); if (!a) return;
      ({close, prev: () => step(-1), next: () => step(1), copy})[a.dataset.act]();
    });
    backdrop.addEventListener('click', close);
  }

  function step(dir) {
    if (!open) return;
    const ks = keys(); const i = ks.findIndex(e => e === open.el);
    const nx = ks[(i + dir + ks.length) % ks.length]; if (!nx || nx === open.el) return;
    open.el.style.visibility = ''; nx.style.visibility = 'hidden';
    open.el = nx; open.key = nx.dataset.detail; fill(open.panel, open.key, dir);
  }

  function close() {
    if (!open) return;
    const {el, panel, backdrop} = open; open = null;
    const r = el.getBoundingClientRect();
    panel.querySelector('.xp-body').animate([{opacity: 1}, {opacity: 0}], {duration: 160, fill: 'forwards'});
    backdrop.classList.remove('on');
    const from = panel.getBoundingClientRect();
    panel.animate([{...px(from), borderRadius: '34px'}, {...px(r), borderRadius: '28px', opacity: .9}],
                  {duration: 480, easing: ease, fill: 'forwards'})
         .onfinish = () => { el.style.visibility = ''; panel.remove(); backdrop.remove(); document.documentElement.style.overflow = ''; };
  }

  function copy() {
    if (!open) return;
    const s = window.__aqiDetails[open.key].summary + ' — via AQIfyMe';
    (navigator.clipboard ? navigator.clipboard.writeText(s) : Promise.reject()).then(() => toast('Summary copied'), () => toast('Copy not available'));
  }
  function toast(msg) {
    const t = document.createElement('div'); t.className = 'xp-toast'; t.textContent = msg; document.body.append(t);
    requestAnimationFrame(() => t.classList.add('on'));
    setTimeout(() => { t.classList.remove('on'); setTimeout(() => t.remove(), 400); }, 1600);
  }

  // chart crosshair tooltips
  function wireCharts(root) {
    root.querySelectorAll('.xchart-wrap').forEach(w => {
      const svg = w.querySelector('svg'), tip = w.querySelector('.xtip');
      const meta = JSON.parse(w.querySelector('.xchart-data').textContent);
      const L = +svg.dataset.l, PW = +svg.dataset.pw, N = +svg.dataset.n;
      const guide = svg.querySelector('.guide');
      const dots = meta.s.map(s => { const c = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        c.setAttribute('r', 5); c.setAttribute('fill', s.c); c.setAttribute('stroke', '#fff'); c.setAttribute('stroke-width', 2);
        c.style.opacity = 0; svg.append(c); return c; });
      svg.addEventListener('pointermove', e => {
        const b = svg.getBoundingClientRect(), vb = svg.viewBox.baseVal;
        const sx = (e.clientX - b.left) / b.width * vb.width;
        const i = Math.max(0, Math.min(N - 1, Math.round((sx - L) / PW * (N - 1))));
        const x = L + PW * i / (N - 1);
        guide.setAttribute('x1', x); guide.setAttribute('x2', x); guide.setAttribute('opacity', 1);
        let rows = '', topY = Infinity;
        meta.s.forEach((s, k) => { const v = s.v[i];
          if (v == null) { dots[k].style.opacity = 0; return; }
          const y = meta.T + meta.ph * (1 - (v - meta.ymin) / (meta.ymax - meta.ymin));
          dots[k].setAttribute('cx', x); dots[k].setAttribute('cy', y); dots[k].style.opacity = 1; topY = Math.min(topY, y);
          rows += `<div><i style="background:${s.c}"></i>${s.l}: <b>${v.toLocaleString()}</b> ${meta.u}</div>`; });
        tip.innerHTML = `<div style="opacity:.7">${meta.t[i]}</div>` + rows;
        tip.style.left = (x / vb.width * b.width) + 'px'; tip.style.top = (topY / vb.height * b.height) + 'px'; tip.style.opacity = 1;
      });
      svg.addEventListener('pointerleave', () => { tip.style.opacity = 0; guide.setAttribute('opacity', 0); dots.forEach(d => d.style.opacity = 0); });
    });
  }

  document.addEventListener('click', e => {
    if (open) return;
    const el = e.target.closest('[data-detail]'); if (!el) return;
    if (e.target.closest('a, button, input')) return;
    const r = el.getBoundingClientRect(), s = Math.max(r.width, r.height) * 2.2;
    const rp = document.createElement('span'); rp.className = 'ripple';
    Object.assign(rp.style, {width: s + 'px', height: s + 'px', left: (e.clientX - r.left - s / 2) + 'px', top: (e.clientY - r.top - s / 2) + 'px'});
    el.append(rp); setTimeout(() => rp.remove(), 650);
    setTimeout(() => expand(el), 90);
  });
  document.addEventListener('keydown', e => {
    if (!open) return;
    if (e.key === 'Escape') close(); else if (e.key === 'ArrowRight') step(1); else if (e.key === 'ArrowLeft') step(-1);
  });
  addEventListener('resize', () => { if (open) Object.assign(open.panel.style, px(targetRect())); });

  // 3D tilt following the pointer
  document.addEventListener('pointermove', e => {
    const c = e.target.closest && e.target.closest('.card.xp'); if (!c) return;
    const r = c.getBoundingClientRect(), nx = (e.clientX - r.left) / r.width - .5, ny = (e.clientY - r.top) / r.height - .5;
    c.style.setProperty('--ry', (nx * 7).toFixed(2) + 'deg'); c.style.setProperty('--rx', (-ny * 7).toFixed(2) + 'deg');
  }, {passive: true});
})();
</script>
"""


def _js_safe(code: str) -> str:
    # Streamlit sanitises st.html with DOMPurify, which drops any <script> whose text looks like markup
    # ("<" followed by a letter, "/" or "!"). Inside JS strings "\x3c" is the same character, so swap it in.
    return re.sub(r"<(?=[/\w!])", r"\\x3c", code)


def expand_html(details: dict) -> str:
    payload = json.dumps(details).replace("<", "\\u003c")
    inner = EXPAND_JS.strip()[len("<script>"):-len("</script>")]
    return "<script>" + _js_safe(inner).replace("__DETAILS__", payload) + "</script>"
