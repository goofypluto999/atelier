// Drawn films for Atelier: a canvas world under the page's words, moved only by time. Atelier's own code (MIT).
// It joins huashu-art-motion's drawing files (MIT, alchaincyf, vendor/MANIFEST.md) to Atelier's one render contract,
// window.seek(t) on <section class="page">, so scripts/motion.mjs renders the film and render.mjs --audit, attention.py
// and video_check.py check it like any other motion page. Load, in this order, after tokens.css and palette.css:
//   vendor/huashu-art-motion/lib/util.js, motion.js, camera.js, palettes.js, finish.js, then assets/lib/art-motion.js
//
//   ART.film({ duration: 8, theme: "page", finish: "soft", init(pal) {}, draw(c, t, pal) {} })
//     theme   "page" (default): the page's palette.css roles (--ground, --text, --text-2, --accent, --accent-2),
//             so the dealt colour plan colours the film; or a PAL name (paper, ink, wood, ...) or an object (palettes.js).
//     finish  null (default), "soft", "film" or "punch" (finish.js): vignette, bloom, grain, all fixed by t.
//     draw    paints the frame for t seconds on c (page pixels). Take every move from t (MO, CAM) and every random
//             value from a seed (U.rng); no clock, no Math.random, no state carried between frames.
// Words stay HTML with their data-role, above the canvas, so the audit measures their size and contrast.
// The canvas is painted at frame 0 at once, so the audit and attention.py see the first frame. Method: references/art-motion.md.
(function () {
  const probe = (sec, value) => {
    const i = document.createElement("i");
    sec.appendChild(i);
    i.style.color = value;
    const m = getComputedStyle(i).color.match(/\d+(\.\d+)?/g) || [0, 0, 0];
    i.remove();
    return "#" + m.slice(0, 3).map((n) => Math.round(+n).toString(16).padStart(2, "0")).join("");
  };
  // palette.css roles to the six keys palettes.js uses; surface is the ground moved a step toward the text
  function pagePalette(sec) {
    const role = (name) => getComputedStyle(sec).getPropertyValue(name).trim();
    if (!role("--ground") || !role("--text")) throw new Error('ART.film theme "page" needs palette.css on the page (--ground and --text): link it, or pass a PAL name');
    const bg = probe(sec, role("--ground")), ink = probe(sec, role("--text"));
    const sub = role("--text-2") ? probe(sec, role("--text-2")) : PAL.mix(bg, ink, 0.7);
    const accent = role("--accent") ? probe(sec, role("--accent")) : ink;
    const accent2 = role("--accent-2") ? probe(sec, role("--accent-2")) : sub;
    return PAL.resolve({ bg, surface: PAL.mix(bg, ink, 0.06), ink, sub, accent, accent2 });
  }
  window.ART = {
    film(spec) {
      const sec = spec.page || document.querySelector("section.page");
      if (!sec) throw new Error('ART.film needs a <section class="page">');
      const { duration, theme = "page", finish = null, fps = 30, init, draw } = spec;
      if (!(duration > 0) || typeof draw !== "function") throw new Error("ART.film needs duration > 0 and draw(c, t, pal)");
      const w = sec.clientWidth, h = sec.clientHeight;
      U.setStage(w, h);
      // the canvas sits under every word: the page becomes its own stacking context and the canvas goes to its back
      sec.style.isolation = "isolate";
      if (getComputedStyle(sec).position === "static") sec.style.position = "relative";
      const cv = sec.querySelector("canvas.film") || sec.insertBefore(document.createElement("canvas"), sec.firstChild);
      cv.className = "film";
      cv.width = w; cv.height = h;
      Object.assign(cv.style, { position: "absolute", left: "0", top: "0", width: `${w}px`, height: `${h}px`, zIndex: "-1" });
      const c = cv.getContext("2d");
      const pal = theme === "page" ? pagePalette(sec) : PAL.resolve(theme);
      const fin = FINISH.resolve(finish);
      if (init) init(pal);
      window.seek = (t) => {
        c.save(); c.setTransform(1, 0, 0, 1, 0, 0); c.clearRect(0, 0, w, h);
        draw(c, t, pal);
        c.restore();
        FINISH.apply(c, t, fin, w, h, fps);
      };
      window.ART.duration = duration;
      window.seek(0);
      return { canvas: cv, pal };
    },
  };
})();
