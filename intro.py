"""AQIfyMe intro: the name assembles, explains itself (AQI + verify + me), then shrinks into the sidebar
logo while every home-page block expands into place. Plays once per browser session; tap the logo to replay."""
import re

INTRO_CSS = """
<style>
/* hold the page still while the intro plays */
body.intro-on .card, body.intro-on .hero, body.intro-on [data-testid="stPlotlyChart"] { opacity: 0 !important; animation: none !important; }
body.intro-play .card, body.intro-play .hero {
  animation: blockIn .9s cubic-bezier(.2,.9,.3,1.15) both !important; animation-delay: calc(var(--i, 0) * 55ms) !important; }
@keyframes blockIn { 0% { opacity: 0; transform: scale(.82) translateY(30px); filter: blur(10px); }
                     60% { opacity: 1; filter: blur(0); } 100% { opacity: 1; transform: none; filter: none; } }

#aqf-intro { position: fixed; inset: 0; z-index: 9999999; display: grid; place-items: center; overflow: hidden;
  background: radial-gradient(120% 90% at 50% 40%, rgba(40,70,140,.55), rgba(5,10,30,.85));
  backdrop-filter: blur(26px) saturate(160%); -webkit-backdrop-filter: blur(26px) saturate(160%);
  transition: opacity .7s ease, backdrop-filter .7s ease; color: #fff; font-family: var(--font); }
#aqf-intro.out { opacity: 0; pointer-events: none; }
.aqf-stage { text-align: center; padding: 1rem; }
.aqf-word { display: inline-flex; align-items: baseline; font-size: clamp(3.4rem, 11vw, 8.5rem); font-weight: 700; letter-spacing: -.045em;
  line-height: 1; will-change: transform; }
.aqf-word span { display: inline-block; opacity: 0; transform: translateY(40px) scale(.7); filter: blur(12px);
  animation: aqfIn .9s cubic-bezier(.2,.9,.3,1.3) forwards; }
.aqf-word .a { background: linear-gradient(180deg, #fff, #bfe3ff); -webkit-background-clip: text; background-clip: text; color: transparent; }
.aqf-word .f { font-weight: 300; font-style: italic; color: #7dd3fc; margin: 0 .02em; }
.aqf-word .m { background: linear-gradient(135deg, #4ade80, #22d3ee); -webkit-background-clip: text; background-clip: text; color: transparent; }
@keyframes aqfIn { to { opacity: 1; transform: none; filter: none; } }
.aqf-parts { display: flex; justify-content: center; gap: clamp(.6rem, 3vw, 2.4rem); margin-top: 1.6rem; flex-wrap: wrap; }
.aqf-part { opacity: 0; transform: translateY(16px); animation: aqfIn .7s cubic-bezier(.2,.8,.2,1) forwards; text-align: center;
  padding: .7rem 1.1rem; border-radius: 20px; background: rgba(255,255,255,.10); min-width: 9rem;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.4), 0 10px 30px -12px rgba(0,0,0,.5); }
.aqf-part b { display: block; font-size: 1.35rem; letter-spacing: -.01em; }
.aqf-part i { font-style: normal; font-size: .82rem; color: rgba(255,255,255,.75); }
.aqf-plus { align-self: center; opacity: 0; animation: aqfIn .5s forwards; font-size: 1.4rem; color: rgba(255,255,255,.55); }
.aqf-tag { margin-top: 1.6rem; font-size: clamp(1rem, 2.4vw, 1.35rem); font-weight: 500; opacity: 0;
  animation: aqfIn .8s cubic-bezier(.2,.8,.2,1) forwards; }
.aqf-tag em { font-style: normal; background: linear-gradient(90deg, #7dd3fc, #4ade80); -webkit-background-clip: text;
  background-clip: text; color: transparent; font-weight: 700; }
.aqf-skip { position: absolute; bottom: 1.6rem; right: 1.6rem; border: none; border-radius: 999px; padding: .5rem 1rem; color: #fff;
  font: 600 .82rem var(--font); background: rgba(255,255,255,.16); box-shadow: inset 0 1px 0 rgba(255,255,255,.45); cursor: pointer; }
.aqf-glow { position: absolute; width: 60vmax; height: 60vmax; border-radius: 50%; pointer-events: none;
  background: radial-gradient(circle, rgba(125,211,252,.25), transparent 60%); animation: aqfPulse 4s ease-in-out infinite; }
@keyframes aqfPulse { 50% { transform: scale(1.15); opacity: .7; } }

.aqf-load { margin-top: 1.2rem; font-size: .85rem; color: rgba(255,255,255,.75); display: inline-flex; gap: .35rem; align-items: center;
  animation: aqfIn .5s forwards; opacity: 0; }
.aqf-load span { width: 6px; height: 6px; border-radius: 50%; background: #7dd3fc; animation: aqfDot 1s infinite ease-in-out; }
.aqf-load span:nth-child(2) { animation-delay: .15s; } .aqf-load span:nth-child(3) { animation-delay: .3s; margin-right: .3rem; }
@keyframes aqfDot { 50% { transform: translateY(-5px); opacity: .4; } }

/* the brand mark everywhere else */
.brand-name .a { font-weight: 800; } .brand-name .f { font-weight: 300; font-style: italic; color: #7dd3fc; }
.brand-name .m { background: linear-gradient(135deg, #4ade80, #22d3ee); -webkit-background-clip: text; background-clip: text; color: transparent; font-weight: 800; }
.brand { cursor: pointer; }
</style>
"""

INTRO_JS = r"""
<script>
(function () {
  const replay = window.__aqfReplay === true;
  window.__aqfReplay = false;
  let seen = false;
  try { seen = sessionStorage.getItem('aqf-intro') === '1'; } catch (e) {}
  if (window.__aqfBound !== true) {           // tap the logo to replay
    window.__aqfBound = true;
    document.addEventListener('click', e => { if (e.target.closest('.brand')) { window.__aqfReplay = true; play(); } });
  }
  if ((seen && !replay) || document.getElementById('aqf-intro') || matchMedia('(prefers-reduced-motion: reduce)').matches) {
    if (!document.getElementById('aqf-intro')) document.body.classList.remove('intro-on');
    return;
  }
  play();

  function play() {
    if (document.getElementById('aqf-intro')) return;
    try { sessionStorage.setItem('aqf-intro', '1'); } catch (e) {}
    document.body.classList.remove('intro-play'); document.body.classList.add('intro-on');
    const o = document.createElement('div'); o.id = 'aqf-intro';
    o.innerHTML = `
      <div class="aqf-glow"></div>
      <div class="aqf-stage">
        <div class="aqf-word" id="aqf-word">
          <span class="a" style="animation-delay:.10s">A</span><span class="a" style="animation-delay:.18s">Q</span><span class="a" style="animation-delay:.26s">I</span><span class="f" style="animation-delay:.55s">fy</span><span class="m" style="animation-delay:.85s">Me</span>
        </div>
        <div class="aqf-parts">
          <div class="aqf-part" style="animation-delay:1.3s"><b>AQI</b><i>the air you breathe</i></div>
          <div class="aqf-plus" style="animation-delay:1.5s">+</div>
          <div class="aqf-part" style="animation-delay:1.65s"><b>-fy</b><i>as in veri<b style="display:inline;font-size:inherit;color:#7dd3fc">fy</b></i></div>
          <div class="aqf-plus" style="animation-delay:1.85s">+</div>
          <div class="aqf-part" style="animation-delay:2.0s"><b>Me</b><i>for you</i></div>
        </div>
        <div class="aqf-tag" style="animation-delay:2.5s"><em>Verified air-quality information,</em> made for you.</div>
      </div>
      <button class="aqf-skip">Skip ›</button>`;
    document.body.append(o);
    const t0 = Date.now();
    const timer = setTimeout(whenReady, 4600);
    o.querySelector('.aqf-skip').onclick = () => { clearTimeout(timer); finish(); };

    // hold the intro until the live dashboard has actually rendered (first load fetches data)
    function whenReady() {
      const ready = document.querySelector('.hero, .hero-title');
      if (ready || Date.now() - t0 > 20000) return finish();
      const tag = o.querySelector('.aqf-tag');
      if (!o.querySelector('.aqf-load')) {
        const l = document.createElement('div'); l.className = 'aqf-load';
        l.innerHTML = '<span></span><span></span><span></span> Fetching live air data…';
        tag.after(l);
      }
      setTimeout(whenReady, 250);
    }

    function finish() {
      if (o.dataset.done) return; o.dataset.done = '1';
      const word = o.querySelector('#aqf-word');
      const target = document.querySelector('.brand-name');
      const wr = word.getBoundingClientRect();
      let tr = target && target.getBoundingClientRect();
      if (!tr || tr.width === 0) tr = {left: 24, top: 24, width: 120, height: 24};   // sidebar hidden: fly to top-left
      const scale = tr.height / wr.height * 1.15;
      word.animate([{transform: 'none', opacity: 1},
                    {transform: `translate(${tr.left - wr.left - wr.width * (1 - scale) / 2}px, ${tr.top - wr.top - wr.height * (1 - scale) / 2}px) scale(${scale})`, opacity: .2}],
                   {duration: 850, easing: 'cubic-bezier(.6,0,.2,1)', fill: 'forwards'});
      o.querySelectorAll('.aqf-parts, .aqf-tag, .aqf-skip, .aqf-load').forEach(el =>
        el.animate([{opacity: 1}, {opacity: 0, transform: 'translateY(20px)'}], {duration: 400, fill: 'forwards'}));
      setTimeout(() => {
        o.classList.add('out');
        document.querySelectorAll('.card, .hero').forEach((el, i) => el.style.setProperty('--i', Math.min(i, 24)));
        document.body.classList.remove('intro-on'); document.body.classList.add('intro-play');
        setTimeout(() => { o.remove(); document.body.classList.remove('intro-play'); }, 2600);
      }, 650);
    }
  }
})();
</script>
"""


def intro_html() -> str:
    inner = INTRO_JS.strip()[len("<script>"):-len("</script>")]
    # Streamlit sanitises st.html; hide "<tag" sequences inside the JS template string
    return "<script>" + re.sub(r"<(?=[/\w!])", r"\\x3c", inner) + "</script>"
