// fx.js — visual effects only. Watches the page for content the dashboards render
// (stat numbers, score ring) and animates it. Touches no data and no API calls.
(function () {
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const NUM = /-?\d+(\.\d+)?/;

  function countUp(el) {
    const text = el.textContent.trim();
    const m = text.match(NUM);
    if (!m || el.dataset.fxRun || el.dataset.fx === text) return;
    if (document.body.classList.contains('fx-quiet')) { el.dataset.fx = text; return; }
    const target = parseFloat(m[0]), dec = (m[1] || '').length - (m[1] ? 1 : 0);
    if (reduce) { el.dataset.fx = text; return; }
    el.dataset.fxRun = '1';
    const t0 = performance.now(), dur = 1100;
    (function tick(now) {
      const k = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - k, 3);
      el.textContent = text.replace(NUM, (target * e).toFixed(dec));
      if (k < 1) requestAnimationFrame(tick);
      else { el.textContent = text; el.dataset.fx = text; delete el.dataset.fxRun; }
    })(t0);
  }

  function ring(val) {
    const r = val.closest('.score-ring'), n = parseFloat(val.textContent);
    if (!r || isNaN(n) || r.dataset.fx === String(n)) return;
    r.dataset.fx = String(n);
    requestAnimationFrame(() => r.style.setProperty('--p', Math.max(0, Math.min(100, n))));
  }

  let queued = false;
  function scan() {
    queued = false;
    document.querySelectorAll('.stat .num, #scoreVal').forEach(el => {
      if (el.dataset.fxRun) return;
      if (el.id === 'scoreVal') ring(el);
      countUp(el);
    });
  }
  new MutationObserver(() => { if (!queued) { queued = true; requestAnimationFrame(scan); } })
    .observe(document.body, { childList: true, subtree: true, characterData: true });
  scan();

  // after the admin changes an offer status the page reloads its data: keep it calm
  document.addEventListener('change', e => {
    if (e.target.matches('table select')) {
      document.body.classList.add('fx-quiet');
      setTimeout(() => document.body.classList.remove('fx-quiet'), 2500);
    }
  });

  // soft light that follows the pointer on the landing role cards
  document.querySelectorAll('.role-card').forEach(c =>
    c.addEventListener('pointermove', e => {
      const b = c.getBoundingClientRect();
      c.style.setProperty('--mx', e.clientX - b.left + 'px');
      c.style.setProperty('--my', e.clientY - b.top + 'px');
    }));
})();
