// Motion helpers for motion.html files: every value is a pure function of time t (seconds),
// so scripts/motion.mjs can paint any frame in any order. Load with
//   <script src="../../../assets/lib/motion.js"></script>   then use window.M.spring etc.
// Springs, not easing curves: they accelerate, overshoot a hair and settle, which reads as weight.
// Stiff springs (k 300+) for small UI parts; soft ones (k 90 to 140) for big type and objects.
(function () {
  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));

  // Damped spring from 0 to 1. k = stiffness, d = damping. d near 2*sqrt(k) settles with no overshoot.
  function spring(t, k = 170, d = 26) {
    if (t <= 0) return 0;
    const w0 = Math.sqrt(k), z = d / (2 * w0);
    if (z < 1) {
      const wd = w0 * Math.sqrt(1 - z * z);
      return 1 - Math.exp(-z * w0 * t) * (Math.cos(wd * t) + (z * w0 / wd) * Math.sin(wd * t));
    }
    return 1 - Math.exp(-w0 * t) * (1 + w0 * t);
  }

  // keys: [[time, value], ...]. One spring per change, summed, so a value can change target many
  // times and stay smooth, and any frame can still be computed directly.
  function track(t, keys, k = 170, d = 26) {
    let v = keys[0][1];
    for (let i = 1; i < keys.length; i++) v += (keys[i][1] - keys[i - 1][1]) * spring(t - keys[i][0], k, d);
    return v;
  }

  // Ease-out for things that must not overshoot (type, rules): expo out, cubic-bezier(.16,1,.3,1) in CSS.
  const expoOut = (x) => (x >= 1 ? 1 : 1 - Math.pow(2, -10 * clamp(x)));
  // Progress of a window [a, b] in seconds, 0..1.
  const win = (t, a, b) => clamp((t - a) / (b - a));
  // Seeded noise (never Math.random): same value for the same inputs on every render.
  const hash = (n) => { const s = Math.sin(n * 127.1) * 43758.5453; return s - Math.floor(s); };
  // Rolling counter that settles sharply on its final value.
  const counter = (t, a, b, to, from = 0) => Math.round(from + (to - from) * expoOut(win(t, a, b)));

  window.M = { clamp, spring, track, expoOut, win, hash, counter };
})();
