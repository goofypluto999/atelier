#!/usr/bin/env node
// atelier: render designed pages from HTML. Free and local: Playwright (Chromium) plus ffmpeg.
//
//   node render.mjs <visual.html> [--pdf] [--png] [--video scenes.json] [--audit] [--size 1080x1350] [--safe reels|story|none] [--out <dir>] [--no-png] [--raw-max 6] [--seconds N] [--poster T]
//
// visual.html holds one or more <section class="page"> elements (1080x1350 by default; --size WxH),
// styled with the skill's assets/tokens.css or your own brand tokens.
//   --png   writes page-01.png, page-02.png ... next to the HTML, and deletes page-NN.png (and page-NN.cvd.png) above the new
//           page count, so an earlier, longer render leaves nothing for attention.py or contact_sheet.py to read
//   --pdf   writes carousel.pdf (one page per section, vector text) for a LinkedIn document post
//   --video scenes.json writes video.mp4: each scene = { "page": 1, "seconds": 3.5 }.
//           Captions are part of the page design (burned in), so it reads with the sound off.
//   --audit writes audit.json and boxes.json (and the PNGs, so attention.py can run next) and exits 1 on a hard fail.
//           It checks: that the page loaded (a missing file, an image of zero width, a stylesheet that did not apply,
//           text in the browser's default font: hard fails, printed first), type floors (32px, 36px for condensed type),
//           WCAG contrast (over a gradient or hatch it samples the rendered pixels), the hook is the biggest type on
//           the cover, text clipped by the page or overlapping other text, text set sideways, mirrored or turned more than 30 degrees, shapes and images painted over text,
//           text inside platform UI zones (--safe reels or story, for 9:16), and AI-look tells (eyebrow labels,
//           glows, gradients, "A · B · C" chains, trailing arrows, too many sizes, faces, words or centred text).
//           Design-doctrine warnings (never a fail; data-allow="..." on the element or a parent marks a deliberate use):
//             fake product chrome: red, amber and green window dots; a dot beside LIVE, ONLINE, ACTIVE and kin; NEW, BETA, LIVE, PRO or HOT
//               in a pill or box (data-allow="chrome"); 3 or more pill-shaped tags, or more than 2 corner radii (data-allow="pill");
//             nested panels: a box with its own fill or border inside another inside a third (data-allow="nested");
//             raw colours: hex, rgb or hsl literals in the page's own styles instead of var(--token), more than --raw-max (default 6)
//               distinct colours on a page (data-allow="colour"). Custom-property definitions and var() fallbacks do not count.
//             audit.json and the page line report each page's rawColours.
//             accent paint: the share of the page drawn in the page's --accent (palette.css sets it), text left out; warns at 5% (SKILL.md:
//               one accent, under 5% of the area). audit.json and the page line report it as "accent".
//             display line breaks: display type (60px or more as drawn) that leaves one word alone on its last line, or ends a line on a
//               small word such as "the" or "of" (references/type.md).
//             word budget: more than 45 words on one page, every word counted (references/copy.md "Word budget"); it says how many to cut.
//           Before the critic (warnings for five faults the 30 Oct 2026 art-directors charged): phone read (text under 36px, or under 40px in a
//             weight under 500, fine print included; the page line also gives the smallest size with fine print), claim twice (a line that
//             repeats the hook's words), wrapped run (identical marks that wrap and leave a short last row), hairline accent (a data-role="accent"
//             mark drawn under 8px), empty cell (in a row of cells, one spans under 40% of its height beside one filled to 75% or more).
//           Two more from the second 30 Oct 2026 run: faint mark (a mark with no text, such as an empty slot, a dot or an outline, under 3:1
//             against the ground behind it, WCAG 1.4.11; a small shape in the mark's own colour, such as the line under a dot, or a shape
//             smaller than the mark, is not its ground; data-allow="faint" marks decoration) and thin stroke (display type, 48px or more, whose
//             strokes are under 6px, 2px on a phone, and under 6.5% of its size: a script, hairline or light face).
//           Text over a <canvas> (a drawn film, assets/lib/art-motion.js) is judged on the rendered pixels, like text over a gradient.
//           A rule through text is a hard fail: a border (a table's, a cell's, a box's) or a thin bar (an hr, a div drawn as a line) that crosses
//           the middle of a line of text and shows on the render (data-allow="over" marks a deliberate strike).
//           A motion page (window.seek, ART.film or CSS animations): every check above runs on the page as loaded, its first frame. Then
//           every hard rule (not the cover's hook rule or the turned-text rule, no warnings) runs again every half second of the film (0.5 s, 1 s, 1.5 s ...)
//           and at the poster time, seeked there as motion.mjs seeks. The length comes from --seconds, else timeline.json next to the
//           page (whose beats are set as motion.mjs sets them), else ART.film, else the end of the CSS animations; --poster T as for motion.mjs (default: 3 s, or half the length if that is less). A seek page of unknown length
//           is checked at its first frame only, and the audit says so. A fail found at a later time is printed as "at 4 s: ...", and
//           audit.json gives each page's "times", and boxes.json adds the labelled boxes at the poster time as page "poster", which
//           attention.py and cvd.py read with poster.png.
//   --seconds N, --poster T  with --audit: the film's length and poster time, as given to motion.mjs.
//   --no-png  with --audit: do not write the PNGs.
//   --out <dir>  write every output (PNGs, PDF, audit.json, boxes.json, video) there instead of next to the HTML.
// With no flags it writes PNGs and the PDF. A page that does not load cleanly writes nothing and exits 1.
import { createRequire } from "node:module";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

// Playwright is looked up in your project first, then next to this skill, then globally.
// Install once in your project: npm i -D playwright@1.63.0 && npx playwright install chromium
function loadPlaywright() {
  const bases = [path.join(process.cwd(), "noop.js"), import.meta.url];
  for (const b of bases) {
    try { return createRequire(b)("playwright"); } catch {}
  }
  console.error("Playwright not found. In your project run: npm i -D playwright@1.63.0 && npx playwright install chromium");
  process.exit(2);
}
const { chromium } = loadPlaywright();

const args = process.argv.slice(2);
const file = args.find((a) => a.endsWith(".html"));
const oIdx = args.indexOf("--out");
if (!file || (oIdx >= 0 && !args[oIdx + 1])) {
  console.error("usage: node render.mjs <visual.html> [--pdf] [--png] [--video scenes.json] [--audit] [--size 1080x1350] [--out <dir>] [--no-png] [--raw-max 6]");
  process.exit(2);
}
const dir = path.dirname(path.resolve(file));
const outDir = oIdx >= 0 ? path.resolve(args[oIdx + 1]) : dir;
fs.mkdirSync(outDir, { recursive: true });
const want = (f) => args.includes(f);
const all = !want("--pdf") && !want("--png") && !want("--video") && !want("--audit");
const vIdx = args.indexOf("--video");
const scenesFile = vIdx >= 0 ? args[vIdx + 1] : null;

const sIdx = args.indexOf("--size");
const [W, H] = (sIdx >= 0 ? args[sIdx + 1] : "1080x1350").split("x").map(Number);
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
// a film timed by timeline.json next to the page (references/sound.md) is loaded as motion.mjs loads it: window.TIMELINE, the
// --beat-<id> variables, and the audit's film length from the timeline when --seconds is not given
const tlFile = path.join(path.dirname(path.resolve(file)), "timeline.json");
let timeline = null;
if (fs.existsSync(tlFile)) {
  try { timeline = JSON.parse(fs.readFileSync(tlFile, "utf8")); } catch (err) { console.log(`warn timeline.json next to the page is not valid JSON, so it is not used: ${err.message}`); }
}
const beats = (timeline?.beats || []).filter((b) => /^[a-z0-9][a-z0-9-]*$/.test(String(b.id)) && Number.isFinite(Number(b.at)));
if (beats.length < (timeline?.beats || []).length) console.log('warn timeline.json: a beat needs an id of lower case letters, digits and dashes and a time "at"; the others are not set');
if (timeline) await page.addInitScript((tl) => { window.TIMELINE = tl; }, timeline);
// everything the page asks for and does not get: a wrong relative link renders in Times New Roman with no other sign
const missed = new Map();
const miss = (url, why) => { if (!/^(data|blob|about):/.test(url)) missed.set(url, missed.get(url) || why); };
page.on("requestfailed", (r) => { const e = r.failure()?.errorText || "failed"; if (!/ERR_ABORTED/.test(e)) miss(r.url(), /NOT_FOUND/.test(e) ? "file not found" : e.replace("net::", "")); });
page.on("response", (r) => { if (r.status() >= 400) miss(r.url(), `HTTP ${r.status()}`); });
await page.goto(pathToFileURL(path.resolve(file)).href, { waitUntil: "networkidle" });
await page.evaluate(() => document.fonts.ready);
if (beats.length) await page.evaluate((bs) => { for (const b of bs) document.documentElement.style.setProperty(`--beat-${b.id}`, `${Number(b.at)}s`); }, beats);
const sections = await page.$$("section.page");
if (!sections.length) throw new Error("no <section class=\"page\"> found");

const problems = await loadProblems();
async function loadProblems() {
  const seen = await page.evaluate(() => {
    const own = (el) => [...el.childNodes].filter((n) => n.nodeType === 3).map((n) => n.textContent).join("").trim();
    const f = document.createElement("iframe"); document.body.append(f);
    const browserDefault = f.contentWindow.getComputedStyle(f.contentDocument.body).fontFamily; f.remove();
    const reps = new Map(); // one text element per font-family value
    for (const el of document.querySelectorAll("*")) {
      const cs = getComputedStyle(el), t = own(el);
      if (!/[\p{L}\p{N}]/u.test(t) || cs.display === "none" || cs.visibility === "hidden") continue;
      if (!reps.has(cs.fontFamily) || t.length > reps.get(cs.fontFamily).t.length) reps.set(cs.fontFamily, { el, t });
    }
    return {
      browserDefault,
      images: [...document.images].filter((i) => i.complete && !i.naturalWidth).map((i) => i.currentSrc || i.src),
      sheets: [...document.querySelectorAll("link[rel~=stylesheet]")].filter((l) => !l.sheet && !l.disabled).map((l) => l.href),
      declared: [...document.fonts].filter((f) => f.status !== "error").map((f) => f.family.replace(/^["']|["']$/g, "").toLowerCase()),
      reps: [...reps].map(([fam, { el, t }], k) => { el.setAttribute("data-atl-font", k); return { fam, t: t.slice(0, 32) }; }),
    };
  });
  for (const u of seen.images) miss(u, "image has no width");
  for (const u of seen.sheets) miss(u, "stylesheet did not apply");
  const shown = (u) => (u.startsWith("file:") ? path.relative(dir, fileURLToPath(u)).replace(/\\/g, "/") : u);
  const list = [...missed].map(([u, why]) => `did not load: ${shown(u)} (${why}); fix the path, or start the page with compose.py scaffold`);
  // text that fell back to a generic font: the browser default, or a named family that is neither loaded nor installed
  const generic = /^(serif|sans-serif|monospace|cursive|fantasy|system-ui|ui-[\w-]+|math|emoji|fangsong)$/i;
  const cdp = await page.context().newCDPSession(page);
  await cdp.send("DOM.enable"); await cdp.send("CSS.enable");
  const { root } = await cdp.send("DOM.getDocument");
  for (const [k, { fam, t }] of seen.reps.entries()) {
    const names = fam.split(",").map((s) => s.trim().replace(/^["']|["']$/g, "")).filter((s) => !generic.test(s));
    if (fam === seen.browserDefault) { list.push(`text uses the browser default font (${fam}): "${t}"; no font-family reaches it, so a stylesheet or font did not load`); continue; }
    if (!names.length || names.some((n) => seen.declared.includes(n.toLowerCase()))) continue; // an @font-face family (url or local) is declared, whatever name the platform reports
    const { nodeId } = await cdp.send("DOM.querySelector", { nodeId: root.nodeId, selector: `[data-atl-font="${k}"]` });
    const used = (await cdp.send("CSS.getPlatformFontsForNode", { nodeId })).fonts.sort((a, b) => b.glyphCount - a.glyphCount)[0];
    if (used && !used.isCustomFont && !names.some((n) => n.toLowerCase() === used.familyName.toLowerCase()))
      list.push(`font "${names[0]}" is not loaded or installed, so text falls back to ${used.familyName}: "${t}"; load it with @font-face or fix the name`);
  }
  await cdp.detach();
  return list;
}
if (problems.length) {
  // a page that did not load is measured wrongly (16px Times New Roman), so say what is missing and stop
  const audit = want("--audit"), say = audit ? console.log : console.error;
  for (const p of problems) say(`  ${audit ? "FAIL" : "ERROR"} ${p}`);
  say(audit ? "audit: FAIL (the page did not load cleanly, so the other checks did not run)" : "render: the page did not load cleanly, nothing written");
  await browser.close();
  process.exit(1);
}

const pngs = [];
if (scenesFile || (!want("--no-png") && (all || want("--png") || want("--audit")))) {
  for (let i = 0; i < sections.length; i++) {
    const out = path.join(outDir, `page-${String(i + 1).padStart(2, "0")}.png`);
    await sections[i].screenshot({ path: out });
    pngs.push(out);
  }
  for (const f of fs.readdirSync(outDir)) {
    const m = f.match(/^page-(\d{2,})(\.cvd)?\.png$/);
    if (m && +m[1] > sections.length) fs.unlinkSync(path.join(outDir, f));
  }
  console.log(`png: ${pngs.length} page(s)`);
}
if (all || want("--pdf")) {
  const out = path.join(outDir, "carousel.pdf");
  await page.pdf({ path: out, width: `${W}px`, height: `${H}px`, printBackground: true, preferCSSPageSize: true });
  console.log(`pdf: ${out} (${sections.length} pages)`);
}
let auditFail = false;
const safeIdx = args.indexOf("--safe");
const safe = safeIdx >= 0 ? args[safeIdx + 1] : "none";
const rawIdx = args.indexOf("--raw-max");
const rawMax = rawIdx >= 0 ? Number(args[rawIdx + 1]) : 6; // raw colours a page may keep for fixed materials before it warns
const WORDS = 45; // the word budget of one page, every word counted (references/copy.md "Word budget")
if (want("--audit")) {
  // every check on every page, run in the page (page.evaluate takes it as source); cover: the cover's hook rule too
  const auditPages = async ({ safe, shots, rawMax, WORDS, cover }) => {
    // a computed colour as sRGB bytes. Chromium computes color-mix() and relative colours as color(srgb ...), oklab(...) or oklch(...),
    // not rgb(...); those are painted on a 1 px canvas and read back, so no colour form escapes the contrast checks
    const px1 = document.createElement("canvas").getContext("2d", { willReadFrequently: true }), painted = new Map();
    const rgb = (s) => {
      const m = s.match(/rgba?\(([^)]+)\)/);
      if (m) { const v = m[1].split(/[ ,\/]+/).filter(Boolean).map(Number); return { r: v[0], g: v[1], b: v[2], a: v.length > 3 ? v[3] : 1 }; }
      if (!/^(color|oklab|oklch|lab|lch|hwb)\(/.test(s) || !CSS.supports("color", s)) return null;
      if (!painted.has(s)) { px1.clearRect(0, 0, 1, 1); px1.fillStyle = s; px1.fillRect(0, 0, 1, 1); const d = px1.getImageData(0, 0, 1, 1).data; painted.set(s, { r: d[0], g: d[1], b: d[2], a: d[3] / 255 }); }
      return painted.get(s);
    };
    const lin = (c) => { c /= 255; return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
    const L = (c) => 0.2126 * lin(c.r) + 0.7152 * lin(c.g) + 0.0722 * lin(c.b);
    const ratio = (a, b) => { const x = L(a), y = L(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
    // the colour actually under the text: the stack of elements at the text's centre, so sibling layers
    // (absolutely positioned fields, panels) count, not only ancestors. A picture, gradient or hatch there: unknown, sampled later.
    const bgOf = (el, r) => {
      const stack = document.elementsFromPoint(r.left + Math.min(r.width / 2, 40), r.top + r.height / 2);
      const chain = stack.length ? stack : (() => { const a = []; for (let e = el; e; e = e.parentElement) a.push(e); return a; })();
      for (const e of chain) {
        const cs = getComputedStyle(e);
        if (e.tagName === "CANVAS") return { unknown: true };   // a drawn film (assets/lib/art-motion.js) under the words: sample its pixels
        if (cs.backgroundImage && cs.backgroundImage !== "none" && !e.dataset.flatBg) return { unknown: true };
        const c = rgb(cs.backgroundColor);
        if (c && c.a > 0.5) return c;
      }
      return { r: 255, g: 255, b: 255, a: 1 };
    };
    // text is measured as drawn: its font size times the scale of the SVG viewBox it sits in, or of every CSS transform, scale and zoom above it
    const scaleOf = (el) => {
      if (el instanceof SVGElement) { const m = el.getScreenCTM && el.getScreenCTM(); return m ? Math.sqrt(Math.abs(m.a * m.d - m.b * m.c)) : 1; }
      let k = 1;
      for (let e = el; e; e = e.parentElement) {
        const cs = getComputedStyle(e), m = new DOMMatrix(cs.transform), [sx, sy = sx] = cs.scale === "none" ? [1] : cs.scale.split(" ").map(Number);
        k *= Math.sqrt(Math.abs((m.a * m.d - m.b * m.c) * sx * sy)) * (+cs.zoom || 1);
      }
      return Math.round(k * 1000) / 1000;
    };
    const sizeOf = (el, cs, k = scaleOf(el)) => Math.round(parseFloat(cs.fontSize) * k * 100) / 100;
    // how text is turned from level: { tilt (degrees, 0 to 180), mirrored }, from the rotate, scale and transform of every box above it,
    // composed in the order CSS applies them. null when the text is not there to read: hidden, under a running animation (a film's first
    // frame can be mid-move), or a back face turned away. Transforms do not apply to inline boxes, so those are skipped.
    const angleOf = (v) => { const n = parseFloat(v); return /grad$/.test(v) ? n * 0.9 : /rad$/.test(v) ? n * 180 / Math.PI : /turn$/.test(v) ? n * 360 : n; };
    const rotateOf = (v) => {
      const p = v.trim().split(/\s+/), deg = angleOf(p.pop());
      const [x, y, z] = p.length === 3 ? p.map(Number) : p[0] === "x" ? [1, 0, 0] : p[0] === "y" ? [0, 1, 0] : [0, 0, 1];
      return new DOMMatrix().rotateAxisAngle(x, y, z, deg);
    };
    const tiltOf = (el) => {
      for (let e = el; e; e = e.parentElement) {
        const cs = getComputedStyle(e);
        if (Number(cs.opacity) === 0 || cs.visibility === "hidden" || e.getAnimations().length) return null;
      }
      let m = new DOMMatrix(), back = false;
      if (el instanceof SVGElement) { const c = el.getScreenCTM && el.getScreenCTM(); if (c) m = DOMMatrix.fromMatrix(c); }
      else for (let e = el; e; e = e.parentElement) {
        const cs = getComputedStyle(e);
        if (cs.display === "inline" || cs.display === "contents") continue;
        let box = cs.rotate && cs.rotate !== "none" ? rotateOf(cs.rotate) : new DOMMatrix();
        if (cs.scale && cs.scale !== "none") { const [sx, sy = sx] = cs.scale.split(" ").map(Number); box = box.scale(sx, sy); }
        m = box.multiply(new DOMMatrix(cs.transform)).multiply(m);
        if (cs.backfaceVisibility === "hidden") back = true;
      }
      const det = m.a * m.d - m.b * m.c;
      if (back && det < 0) return null;
      return { tilt: Math.round(Math.abs(Math.atan2(m.b, m.a) * 180 / Math.PI)), mirrored: det < 0 };
    };
    const condensed = (cs) => parseFloat(cs.fontStretch) < 100 || +(cs.fontVariationSettings.match(/["']wdth["']\s+([\d.]+)/) || [])[1] < 100 || /condensed|narrow|compressed/i.test(cs.fontFamily);
    // the worst-case (5th percentile) contrast of a colour against the rendered pixels in some boxes
    const sampled = (ctx, rects, fg) => {
      const rs = [];
      for (const r of rects) {
        const x = Math.max(0, Math.floor(r.x)), y = Math.max(0, Math.floor(r.y));
        const w = Math.min(ctx.canvas.width - x, Math.ceil(r.w)), h = Math.min(ctx.canvas.height - y, Math.ceil(r.h));
        if (w < 1 || h < 1) continue;
        const d = ctx.getImageData(x, y, w, h).data;
        for (let k = 0; k < d.length; k += 4) rs.push(ratio(fg, { r: d[k], g: d[k + 1], b: d[k + 2] }));
      }
      return rs.sort((a, b) => a - b)[Math.floor(rs.length * 0.05)];
    };
    const SHAPES = "path,circle,ellipse,rect,polygon,polyline,line,img";
    // ---- design-doctrine checks (warnings only, never fails): fake product chrome, pills and radii, nested panels, raw colours.
    // Each has an escape: data-allow="chrome", "pill", "nested" or "colour" on the element (or a parent) says "deliberate".
    const px = (v) => parseFloat(v) || 0;
    const visible = (el) => { const cs = getComputedStyle(el); return cs.display !== "none" && cs.visibility !== "hidden" && Number(cs.opacity) !== 0; };
    const hasFill = (cs) => { const c = rgb(cs.backgroundColor); return !!(c && c.a >= 0.05) || (!!cs.backgroundImage && cs.backgroundImage !== "none"); };
    const boxSides = (cs) => ["Top", "Right", "Bottom", "Left"].filter((s) => px(cs[`border${s}Width`]) >= 1 && !/none|hidden/.test(cs[`border${s}Style`]) && (rgb(cs[`border${s}Color`])?.a ?? 1) >= 0.1).length;
    const corners = (cs, r) => ["TopLeft", "TopRight", "BottomRight", "BottomLeft"].map((c) => {
      const [a, b = a] = cs[`border${c}Radius`].split(" "), f = (t, n) => (t.endsWith("%") ? (parseFloat(t) * n) / 100 : parseFloat(t)) || 0;
      return Math.min(f(a, r.width), f(b, r.height));
    });
    // red, amber or green: the three window-control dots
    const lightOf = (c) => {
      const r = c.r / 255, g = c.g / 255, b = c.b / 255, mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn, l = (mx + mn) / 2;
      if (!d) return null;
      const s = d / (1 - Math.abs(2 * l - 1)), h = ((mx === r ? ((g - b) / d) % 6 : mx === g ? (b - r) / d + 2 : (r - g) / d + 4) * 60 + 360) % 360;
      if (s < 0.45 || l < 0.3 || l > 0.8) return null;
      return h <= 14 || h >= 346 ? "red" : h >= 28 && h <= 56 ? "amber" : h >= 90 && h <= 150 ? "green" : null;
    };
    // a small solid circle with no text: its colour, or null
    const dotColour = (el, cs, r) => {
      if (r.width < 6 || r.width > 28 || Math.abs(r.width - r.height) > 2) return null;
      if (el instanceof SVGElement) { if (!/^(circle|ellipse)$/i.test(el.tagName)) return null; const c = rgb(cs.fill); return c && c.a > 0.5 ? c : null; }
      if (el.textContent.trim() || Math.min(...corners(cs, r)) < Math.min(r.width, r.height) / 2 - 0.5) return null;
      const c = rgb(cs.backgroundColor);
      return c && c.a > 0.5 ? c : null;
    };
    const textBox = (el) => {
      const rs = [];
      for (const n of el.childNodes) if (n.nodeType === 3 && n.textContent.trim()) { const g = document.createRange(); g.selectNodeContents(n); rs.push(...g.getClientRects()); }
      return rs.length ? { left: Math.min(...rs.map((r) => r.left)), right: Math.max(...rs.map((r) => r.right)), top: Math.min(...rs.map((r) => r.top)), bottom: Math.max(...rs.map((r) => r.bottom)) } : el.getBoundingClientRect();
    };
    const STATUS = /\b(live|online|offline|active|recording|streaming|connected|syncing|running|operational|listening)\b/i;
    const BADGE = /^(new|beta|live|pro|hot)[!.]?$/i;
    const label = (e) => e.tagName.toLowerCase() + (typeof e.className === "string" && e.className.trim() ? "." + e.className.trim().split(/\s+/)[0] : "");
    // raw colour literals (hex, rgb, hsl and kin) in the page's own CSS. Custom-property definitions, var() fallbacks, strings and url() do not count.
    const cv = document.createElement("canvas").getContext("2d");
    const keyOf = (lit) => {
      if (!CSS.supports("color", lit)) return null;
      cv.fillStyle = lit;
      const v = cv.fillStyle, m = v.match(/^#([0-9a-f]{6})$/i) || v.match(/^rgba?\(\s*(\d+),\s*(\d+),\s*(\d+)/i);
      return m ? (m.length === 2 ? m[1].toLowerCase() : [m[1], m[2], m[3]].map((n) => (+n).toString(16).padStart(2, "0")).join("")) : v;
    };
    const withoutVar = (s) => { let o = "", i = 0; while (i < s.length) { if (s.startsWith("var(", i)) { i += 3; let d = 0; do { if (s[i] === "(") d++; else if (s[i] === ")") d--; i++; } while (d && i < s.length); } else o += s[i++]; } return o; };
    const literals = (text) => (withoutVar(text.replace(/\/\*[\s\S]*?\*\//g, "").replace(/"[^"]*"|'[^']*'/g, "").replace(/url\([^)]*\)/gi, "")).match(/#[0-9a-f]{3,8}\b|\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch)\([^()]*\)/gi) || []).map(keyOf).filter(Boolean);
    const declarations = (text) => {
      const out = []; let d = 0, q = "", cur = "";
      for (const ch of text) { if (q) { if (ch === q) q = ""; } else if (ch === '"' || ch === "'") q = ch; else if (ch === "(") d++; else if (ch === ")") d--; if (ch === ";" && !d && !q) { out.push(cur); cur = ""; } else cur += ch; }
      out.push(cur);
      return out.map((s) => s.trim()).filter(Boolean);
    };
    const ruleColours = [];
    const walk = (rules) => {
      for (const r of rules) {
        if (r.selectorText && r.style) {
          const ks = declarations(r.style.cssText).filter((s) => !s.startsWith("--")).flatMap(literals);
          if (ks.length) ruleColours.push({ sel: r.selectorText.replace(/::?(?:before|after|first-line|first-letter|marker|placeholder|selection|backdrop)\b/g, "").replace(/:(?:hover|focus|focus-visible|active)\b/g, ""), ks });
        }
        if (r.cssRules && !(r instanceof CSSKeyframesRule) && !(r instanceof CSSFontFaceRule)) walk(r.cssRules);
      }
    };
    for (const sh of document.styleSheets) if (sh.ownerNode && sh.ownerNode.tagName.toLowerCase() === "style") { try { walk(sh.cssRules); } catch {} }
    const doctrine = (sec) => {
      const warns = [], els = [...sec.querySelectorAll("*")].filter(visible);
      const allowed = (e, k) => !!e.closest(`[data-allow~=${k}]`);
      const rects = new Map(els.map((e) => [e, e.getBoundingClientRect()])), css = new Map(els.map((e) => [e, getComputedStyle(e)]));
      // 1. fake product chrome: window dots, a "live" dot beside a status word, NEW or BETA badges in a box
      const dots = [];
      for (const e of els) { const c = dotColour(e, css.get(e), rects.get(e)); if (c && !allowed(e, "chrome")) dots.push({ e, r: rects.get(e), kind: lightOf(c) }); }
      const rows = [], used = new Set();
      for (const d of dots) {
        if (used.has(d)) continue;
        const row = [d]; used.add(d);
        for (let grew = true; grew;) { grew = false; for (const o of dots) if (!used.has(o) && row.some((p) => Math.abs(o.r.top + o.r.height / 2 - (p.r.top + p.r.height / 2)) <= 6 && Math.max(o.r.left - p.r.right, p.r.left - o.r.right) <= 30)) { row.push(o); used.add(o); grew = true; } }
        rows.push(row);
      }
      const windowDots = rows.filter((row) => ["red", "amber", "green"].every((k) => row.some((d) => d.kind === k))).length;
      const live = [], badges = [];
      for (const e of els) {
        const own = [...e.childNodes].filter((n) => n.nodeType === 3).map((n) => n.textContent).join(" ").replace(/\s+/g, " ").trim();
        if (!own || allowed(e, "chrome")) continue;
        if (own.length <= 28 && own.split(" ").length <= 4 && STATUS.test(own)) {
          const t = textBox(e);
          const pseudo = ["::before", "::after"].some((p) => {
            const ps = getComputedStyle(e, p), w = px(ps.width), h = px(ps.height), c = rgb(ps.backgroundColor), rad = ps.borderTopLeftRadius;
            return ps.content !== "none" && ps.content !== "normal" && w >= 6 && w <= 22 && Math.abs(w - h) <= 2 && c && c.a > 0.5 && (rad.endsWith("%") ? parseFloat(rad) >= 50 : px(rad) >= w / 2 - 0.5);
          });
          const beside = dots.find((d) => d.r.width <= 22 && d.r.top + d.r.height / 2 >= t.top - 6 && d.r.top + d.r.height / 2 <= t.bottom + 6 && Math.max(d.r.left - t.right, t.left - d.r.right) <= 36);
          if (pseudo || beside) live.push(own);
        }
        if (BADGE.test(own)) {
          const boxed = (x) => { if (!x || x === sec || x.textContent.trim() !== own || allowed(x, "chrome")) return false; const cs = getComputedStyle(x), r = x.getBoundingClientRect(); return r.height <= 100 && r.width <= 400 && (hasFill(cs) || boxSides(cs) >= 3); };
          if (boxed(e) || boxed(e.parentElement)) badges.push(own);
        }
      }
      if (windowDots) warns.push(`fake product chrome: ${windowDots} row(s) of red, amber and green dots (window controls); a social image is not an app window (mark data-allow="chrome" if deliberate)`);
      if (live.length) warns.push(`fake product chrome: a status dot beside ${live.slice(0, 3).map((t) => `"${t}"`).join(", ")}; a pulsing or solid "live" dot is app ornament, say the state in words (mark data-allow="chrome" if deliberate)`);
      if (badges.length) warns.push(`fake product chrome: ${badges.slice(0, 4).map((t) => `"${t}"`).join(", ")} in a pill or box; NEW, BETA, LIVE, PRO and HOT badges are app ornament (mark data-allow="chrome" if deliberate)`);
      // 2. pills and radii: capsules with text, and more than two corner radii
      const pills = [], radii = new Set(), INLINE = /^(SPAN|B|I|EM|STRONG|A|SMALL|CODE|SVG|IMG|BR|U|MARK)$/;
      for (const e of els) {
        if (e instanceof SVGElement || allowed(e, "pill")) continue;
        const cs = css.get(e), r = rects.get(e);
        if (!r.width || !r.height || !(hasFill(cs) || boxSides(cs) >= 3 || /^(IMG|VIDEO|CANVAS)$/.test(e.tagName))) continue; // a radius only shows on something painted
        const cr = corners(cs, r), half = Math.min(r.width, r.height) / 2 - 0.5;
        if (cr.every((c) => c > 0 && c >= half)) {
          const text = [...e.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim()) || (e.textContent.trim() && [...e.children].every((c) => INLINE.test(c.tagName)));
          if (text && r.width > r.height + 2 && r.height <= 140) pills.push(e);
        } else for (const c of cr) if (c > 0.5) radii.add(Math.round(c));
      }
      if (pills.length >= 3) warns.push(`${pills.length} pill-shaped tags (corner radius at least half the height, e.g. "${pills[0].textContent.trim().slice(0, 20)}"): a template tell; set them as plain text or square fields (mark data-allow="pill" if deliberate)`);
      if (radii.size > 2) warns.push(`${radii.size} different corner radii (${[...radii].sort((a, b) => b - a).join("px, ")}px); one radius for the piece, two at most by role`);
      // 3. nested panels: a box with its own fill or border inside another such box inside a third
      const depth = new Map(), deep = [];
      const groundOf = (e) => { for (let x = e.parentElement; x; x = x.parentElement) { const c = rgb(getComputedStyle(x).backgroundColor); if (c && c.a >= 0.5) return c; if (x === sec) break; } return null; };
      for (const e of els) {
        let d = depth.get(e.parentElement) || 0;
        const cs = css.get(e), r = rects.get(e);
        if (!(e instanceof SVGElement) && cs.display !== "inline" && r.width >= 24 && r.height >= 24 && e.textContent.trim() && !allowed(e, "nested")) {
          const fill = rgb(cs.backgroundColor), under = fill && fill.a >= 0.08 ? groundOf(e) : null;
          if (boxSides(cs) >= 3 || (cs.backgroundImage && cs.backgroundImage !== "none") || (fill && fill.a >= 0.08 && (!under || Math.max(Math.abs(fill.r - under.r), Math.abs(fill.g - under.g), Math.abs(fill.b - under.b)) > 8))) { d++; if (d >= 3) deep.push(e); }
        }
        depth.set(e, d);
      }
      if (deep.length) warns.push(`nested panels: ${deep.length} box(es) sit three deep in boxes that each paint a fill or a border (first: ${label(deep[0])} "${deep[0].textContent.trim().slice(0, 24)}"); group by space first, one container level (mark data-allow="nested" if deliberate)`);
      // 4. raw colours in the page's own styles instead of var(--token)
      const raw = new Set(), ok = (x) => !x.closest("[data-allow~=colour]");
      for (const { sel, ks } of ruleColours) { let hit = false; try { hit = (sec.matches(sel) && ok(sec)) || [...sec.querySelectorAll(sel)].some(ok); } catch {} if (hit) ks.forEach((k) => raw.add(k)); }
      for (const e of [sec, ...sec.querySelectorAll("*")]) {
        if (!ok(e)) continue;
        const st = e.getAttribute("style"); if (st) literals(st).forEach((k) => raw.add(k));
        if (e instanceof SVGElement) for (const a of ["fill", "stroke", "stop-color", "flood-color", "lighting-color", "color"]) { const v = e.getAttribute(a); if (v && /^\s*(#|rgb|hsl|hwb|lab|lch|oklab|oklch)/i.test(v)) literals(v).forEach((k) => raw.add(k)); }
      }
      if (raw.size > rawMax) warns.push(`${raw.size} raw colours in this page's own styles (${[...raw].slice(0, 6).map((k) => (/^[0-9a-f]{6}$/.test(k) ? "#" + k : k)).join(", ")}${raw.size > 6 ? ", ..." : ""}); more than ${rawMax} hard-wires the palette, so use var(--token) and a palette or ground change reaches it (mark data-allow="colour" for a fixed material)`);
      return { warns, rawColours: raw.size };
    };
    const pages = [];
    for (const [i, sec] of [...document.querySelectorAll("section.page")].entries()) {
      sec.scrollIntoView({ block: "start" });
      const sr = sec.getBoundingClientRect();
      const out = { page: i + 1, texts: 0, words: 0, minFont: 999, minAll: 999, sizes: new Set(), families: new Set(), fails: [], warns: [], boxes: [], centredChars: 0, chars: 0 };
      let eyebrows = 0, glows = 0, gradients = 0, chains = 0, arrows = 0;
      const textRects = [], unknown = [], small = [], owns = [];
      const judge = (own, size, cr, fine, how = "") => {
        const where = `"${own.slice(0, 32)}" ${Math.round(size)}px ${cr.toFixed(1)}:1${how}`;
        if (cr < 3) out.fails.push(`contrast under 3:1: ${where}`);
        else if (cr < 4.5 && size < 48) out.fails.push(`contrast under 4.5:1 for text under 48px: ${where}`);
        else if (cr < 7 && size < 40 && !fine) out.warns.push(`body contrast under 7:1: ${where}`);
      };
      for (const el of sec.querySelectorAll("*")) {
        const cs = getComputedStyle(el);
        if (cs.display === "none" || cs.visibility === "hidden" || Number(cs.opacity) === 0) continue;
        if (/gradient/.test(cs.backgroundImage) && !el.closest("[data-allow~=gradient]")) gradients++;
        if ((cs.textShadow !== "none" && /\d+px\)?$|\d+px [^,]*\d+px/.test(cs.textShadow)) || (cs.boxShadow !== "none" && !el.closest("[data-allow~=shadow]"))) glows++;
        if (el.dataset.role) {
          const r = el.getBoundingClientRect();
          out.boxes.push({ role: el.dataset.role, x: Math.round(r.left - sr.left), y: Math.round(r.top - sr.top), w: Math.round(r.width), h: Math.round(r.height) });
        }
        const own = [...el.childNodes].filter((n) => n.nodeType === 3).map((n) => n.textContent).join("").trim();
        if (!own) continue;
        const k = scaleOf(el), size = sizeOf(el, cs, k);
        const fine = !!el.closest("[data-role=fine]");
        // a word holds a letter or a digit, so a lone "." or "/" after an inline span is not counted
        out.texts++; out.words += own.split(/\s+/).filter((w) => /[\p{L}\p{N}]/u.test(w)).length; out.chars += own.length;
        // text set sideways, steeply slanted, upside down or mirrored is hard to read on a phone: judged on the page as loaded
        const turn = cover && !el.closest("[data-allow~=rotate]") ? tiltOf(el) : null;
        if (turn) {
          const quote = own.slice(0, 28), keep = ' (set it level; mark data-allow="rotate" if deliberate)';
          if (/^(vertical|sideways)/.test(cs.writingMode)) out.fails.push(`text set sideways (writing-mode: ${cs.writingMode}): "${quote}"${keep}`);
          else if (turn.mirrored) out.fails.push(`text mirrored: "${quote}"${keep}`);
          else if (turn.tilt > 30) out.fails.push(`text turned ${turn.tilt} degrees: "${quote}"${keep}`);
          else if (turn.tilt > 10) out.warns.push(`text turned ${turn.tilt} degrees: "${quote}" (check it still reads on a phone)`);
        }
        if (/\S\s[·•|]\s\S.*\s[·•|]\s\S/.test(own)) chains++;
        if (/(→|->)\s*$/.test(own)) arrows++;
        // this element's own text only (the boxes its children draw are theirs), as drawn
        const drawn = [];
        for (const n of el.childNodes) if (n.nodeType === 3 && n.textContent.trim()) { const range = document.createRange(); range.selectNodeContents(n); drawn.push(...range.getClientRects()); }
        // glyph boxes trimmed to the line height, so tight display leading is not mistaken for overlap
        const lh = (cs.lineHeight === "normal" ? parseFloat(cs.fontSize) * 1.2 : parseFloat(cs.lineHeight)) * k;
        const mine = [];
        for (const r of drawn) {
          if (r.width < 2 || r.height < 2) continue;
          const h = Math.min(r.height, lh * 0.92);
          const rr = { el, x: r.left - sr.left, y: r.top - sr.top + (r.height - h) / 2, w: r.width, h, t: own.slice(0, 28) };
          textRects.push(rr); mine.push(rr);
          const off = rr.x < -1 || rr.y < -1 || rr.x + rr.w > sr.width + 1 || rr.y + rr.h > sr.height + 1;
          if (off && el.closest("[data-allow~=bleed]")) out.warns.push(`deliberate bleed: "${rr.t}" (check it still reads)`);
          else if (off) out.fails.push(`text runs off the page: "${rr.t}" (mark data-allow="bleed" if deliberate)`);
        }
        if (cs.textAlign === "center") out.centredChars += own.length;
        out.sizes.add(Math.round(size)); out.families.add(cs.fontFamily.split(",")[0].replace(/["']/g, "").trim());
        out.minAll = Math.min(out.minAll, size);
        owns.push({ el, own, size, weight: parseFloat(cs.fontWeight) || 400 });
        if (!fine) {
          out.minFont = Math.min(out.minFont, size);
          const floor = condensed(cs) ? 36 : 32;
          if (size < floor) small.push({ size, floor, t: own.slice(0, 32), drawn: k !== 1 ? ` (set at ${cs.fontSize}, drawn at ${k.toFixed(2)}x)` : "" });
        }
        // caps are caps whether typed or transformed
        const letters = own.replace(/[^\p{L}]/gu, "");
        const caps = cs.textTransform === "uppercase" || (letters.length >= 3 && letters === letters.toUpperCase());
        if (caps && size < 32 && parseFloat(cs.letterSpacing || 0) > size * 0.05) eyebrows++;
        const fg = rgb(cs.color), bg = bgOf(el, drawn.find((r) => r.width >= 2 && r.height >= 2) || el.getBoundingClientRect());
        if (fg && fg.a < 0.1) continue;
        if (fg && bg.unknown) unknown.push({ rects: mine, fg, size, fine, own });
        else if (fg) judge(own, size, ratio(fg, bg), fine);
        if (fine && size < 22) out.fails.push(`fine print under 22px: "${own.slice(0, 32)}" ${size}px`);
      }
      let shot = null;   // the page as rendered with its text hidden, decoded once into a canvas
      const shotCtx = async () => {
        if (shot) return shot;
        const im = new Image(); im.src = "data:image/png;base64," + shots[i]; await im.decode();
        const cv = document.createElement("canvas"); cv.width = im.naturalWidth; cv.height = im.naturalHeight;
        shot = cv.getContext("2d", { willReadFrequently: true }); shot.drawImage(im, 0, 0);
        return shot;
      };
      if (unknown.length) {
        // text over a gradient, hatch or picture: judge it on the pixels that are really there
        const ctx = await shotCtx();
        for (const u of unknown) { const cr = sampled(ctx, u.rects, u.fg); if (cr) judge(u.own, u.size, cr, u.fine, " (over the rendered background)"); }
      }
      // accent paint: the share of the page drawn in the page's --accent (palette.css sets it), text left out, because an accent hook or
      // number counts as that element (as in attention.py). The rule (SKILL.md): one accent, under 5% of the area, on one thing.
      const probe = document.createElement("i"); sec.appendChild(probe);
      const colourOf = (v) => { probe.style.color = ""; probe.style.color = v; return v && probe.style.color ? rgb(getComputedStyle(probe).color) : null; };
      const cssOf = (name) => getComputedStyle(sec).getPropertyValue(name).trim();
      const accent = colourOf(cssOf("--accent")), ground = colourOf(cssOf("--ground")), text = colourOf(cssOf("--text"));
      probe.remove();
      const near = (p, q, tol) => (p.r - q.r) ** 2 + (p.g - q.g) ** 2 + (p.b - q.b) ** 2 <= tol * tol;
      if (accent && ![ground, text].some((c) => c && near(accent, c, 40))) {   // a colour-field page, whose plan makes the accent its text colour, has no accent to measure
        const ctx = await shotCtx(), d = ctx.getImageData(0, 0, ctx.canvas.width, ctx.canvas.height).data;
        let n = 0;
        for (let k = 0; k < d.length; k += 4) if (near({ r: d[k], g: d[k + 1], b: d[k + 2] }, accent, 30)) n++;
        out.accent = Math.round((1000 * n) / (d.length / 4)) / 10;
        if (out.accent >= 5) out.warns.push(`accent paint covers ${out.accent}% of the page (text left out): the rule is under 5%, on the one thing to remember (an accent fill on a row or a band is the usual cause)`);
      }
      // display type (60px or more as drawn): no word alone on the last line, no line ending on a small word (references/type.md)
      const SMALL = new Set("a an the of to in on at for and or by with from as".split(" "));
      const blockOf = (e) => { while (e && e !== sec && /^inline/.test(getComputedStyle(e).display)) e = e.parentElement; return e; };
      const blocks = new Map();
      const tw = document.createTreeWalker(sec, NodeFilter.SHOW_TEXT);
      for (let n = tw.nextNode(); n; n = tw.nextNode()) {
        const p = n.parentElement;
        if (!p || p instanceof SVGElement || !visible(p) || sizeOf(p, getComputedStyle(p)) < 60) continue;
        const re = /\S+/g; let m;
        while ((m = re.exec(n.textContent))) {
          const range = document.createRange(); range.setStart(n, m.index); range.setEnd(n, m.index + m[0].length);
          const b = [...range.getClientRects()].find((x) => x.width > 0);
          if (b) { const k = blockOf(p); if (!blocks.has(k)) blocks.set(k, []); blocks.get(k).push({ w: m[0], top: b.top, h: b.height }); }
        }
      }
      for (const words of blocks.values()) {
        const lines = [];
        for (const w of words) { const l = lines[lines.length - 1]; if (l && Math.abs(w.top - l.top) < w.h * 0.5) l.words.push(w.w); else lines.push({ top: w.top, words: [w.w] }); }
        const text = words.map((w) => w.w).join(" ").slice(0, 40);
        if (words.length >= 3 && lines.length >= 2 && lines[lines.length - 1].words.length === 1) out.warns.push(`display type leaves one word alone on its last line: "${lines[lines.length - 1].words[0]}" in "${text}" (text-wrap: balance, or break by sense; references/type.md)`);
        for (const l of lines.slice(0, -1)) { const end = l.words[l.words.length - 1]; if (SMALL.has(end.toLowerCase())) out.warns.push(`a display line ends on "${end}": "${l.words.join(" ")}" (break lines by sense; references/type.md)`); }
      }
      if (i === 0 && cover) {
        let maxAll = 0, maxHook = 0;
        for (const el of sec.querySelectorAll("*")) {
          const own = [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
          if (!own) continue;
          const fs = sizeOf(el, getComputedStyle(el));
          maxAll = Math.max(maxAll, fs);
          if (el.closest("[data-role=hook],[data-role=number]")) maxHook = Math.max(maxHook, fs);
        }
        if (!maxHook) out.fails.push('cover: no data-role="hook" or "number"; mark the hook');
        else if (maxHook < maxAll) out.fails.push(`cover: the hook is ${maxHook}px but other text is ${maxAll}px; the hook must be the biggest type`);
      }
      // overlapping text (not parent and child): the commonest craft failure
      const seen = new Set();
      for (let a = 0; a < textRects.length; a++) for (let b = a + 1; b < textRects.length; b++) {
        const A = textRects[a], B = textRects[b];
        if (A.el === B.el || A.el.contains(B.el) || B.el.contains(A.el)) continue;
        const ix = Math.min(A.x + A.w, B.x + B.w) - Math.max(A.x, B.x), iy = Math.min(A.y + A.h, B.y + B.h) - Math.max(A.y, B.y);
        if (ix > 3 && iy > 3 && ix * iy > 0.15 * Math.min(A.w * A.h, B.w * B.h)) {
          const key = A.t + "|" + B.t;
          if (!seen.has(key)) { seen.add(key); out.fails.push(`text overlaps text: "${A.t}" and "${B.t}"`); }
        }
      }
      // a shape or picture painted above text (a ring through a label, a triangle over a word): its box covers over 15% of the text and its paint really lies on it
      const shapes = [...sec.querySelectorAll(SHAPES)].filter((s) => !s.closest("[data-allow~=over]") && Number(getComputedStyle(s).opacity) > 0)
        .map((s) => { const b = s.getBoundingClientRect(), sw = s.matches("img") ? 0 : parseFloat(getComputedStyle(s).strokeWidth) / 2 || 0; return { s, l: b.left - sw, t: b.top - sw, r: b.right + sw, b: b.bottom + sw }; });
      for (const T of textRects) for (const S of shapes) {
        if (S.s.contains(T.el) || T.el.contains(S.s)) continue;
        const l = Math.max(sr.left + T.x, S.l), t = Math.max(sr.top + T.y, S.t), ix = Math.min(sr.left + T.x + T.w, S.r) - l, iy = Math.min(sr.top + T.y + T.h, S.b) - t;
        const key = S.s.tagName + "|" + T.t;
        if (!(ix > 0 && iy > 0 && ix * iy > 0.15 * T.w * T.h) || seen.has(key)) continue;
        let touches = false;
        for (let gx = 0; gx < 60 && !touches; gx++) for (let gy = 0; gy < 5 && !touches; gy++) {
          const stack = document.elementsFromPoint(l + (ix * (gx + 0.5)) / 60, t + (iy * (gy + 0.5)) / 5);
          const si = stack.indexOf(S.s), ti = stack.findIndex((e) => T.el.contains(e));
          touches = si >= 0 && ti >= 0 && si < ti;
        }
        if (touches) { seen.add(key); out.warns.push(`${S.s.tagName.toLowerCase()} painted over "${T.t}", its box covers ${Math.round((100 * ix * iy) / (T.w * T.h))}% of the text (move it, or mark data-allow="over" if deliberate)`); }
      }
      // a rule through text: a border (a table's, a cell's, a box's) or a thin painted bar (an hr, a div drawn as a line) that crosses the
      // middle of a line of text, where the eye reads it as a strike. Measured, then confirmed on the render with the text hidden, so a rule
      // covered by an opaque label does not count. Hard fail, like text over text; data-allow="over" on the rule or a parent marks a deliberate strike.
      const rules = [];
      for (const e of sec.querySelectorAll("*")) {
        if (e instanceof SVGElement || !visible(e) || e.closest("[data-allow~=over]")) continue;
        const cs = getComputedStyle(e), r = e.getBoundingClientRect();
        if (!r.width || !r.height) continue;
        const x = r.left - sr.left, y = r.top - sr.top;
        for (const side of ["Top", "Right", "Bottom", "Left"]) {
          const bw = px(cs[`border${side}Width`]), c = rgb(cs[`border${side}Color`]);
          if (bw < 1 || /none|hidden/.test(cs[`border${side}Style`]) || !c || c.a < 0.3) continue;
          rules.push({ e, c, what: `the ${side.toLowerCase()} border of ${label(e)}`, ...(side === "Top" ? { x, y, w: r.width, h: bw } : side === "Bottom" ? { x, y: y + r.height - bw, w: r.width, h: bw } : side === "Left" ? { x, y, w: bw, h: r.height } : { x: x + r.width - bw, y, w: bw, h: r.height }) });
        }
        const fill = rgb(cs.backgroundColor);
        if (fill && fill.a >= 0.3 && !e.textContent.trim() && (r.height <= 12 || r.width <= 12)) rules.push({ e, c: fill, what: `the ${r.height <= 12 ? "horizontal" : "vertical"} bar ${label(e)}`, x, y, w: r.width, h: r.height });
      }
      for (const T of textRects) for (const R of rules) {
        const flat = R.w >= R.h;   // a horizontal rule must cross the middle 60% of the line; a vertical one, the line's inner width and half its height
        const cx0 = flat ? T.x : T.x + 4, cx1 = flat ? T.x + T.w : T.x + T.w - 4, cy0 = flat ? T.y + 0.2 * T.h : T.y, cy1 = flat ? T.y + 0.8 * T.h : T.y + T.h;
        const l = Math.max(R.x, cx0), t = Math.max(R.y, cy0), ix = Math.min(R.x + R.w, cx1) - l, iy = Math.min(R.y + R.h, cy1) - t;
        if (!(flat ? ix > 8 && iy > 0 : iy > 0.5 * T.h && ix > 0)) continue;
        const key = "rule|" + R.what + "|" + T.t;
        if (seen.has(key)) continue;
        const ctx = await shotCtx(), d = ctx.getImageData(Math.floor(l), Math.floor(t), Math.max(1, Math.ceil(ix)), Math.max(1, Math.ceil(iy))).data;
        let on = 0;
        for (let k = 0; k < d.length; k += 4) if ((d[k] - R.c.r) ** 2 + (d[k + 1] - R.c.g) ** 2 + (d[k + 2] - R.c.b) ** 2 <= 40 * 40) on++;
        if (on >= 0.4 * (d.length / 4)) { seen.add(key); out.fails.push(`a rule runs through text: ${R.what} crosses "${T.t}" (move the rule or the text; mark data-allow="over" if it is a deliberate strike)`); }
      }
      // platform UI zones on 9:16 (Reels, TikTok, Shorts, Stories): bottom buttons and captions, right-hand actions
      if (safe === "reels" || safe === "story") {
        const bottom = safe === "reels" ? 320 : 250, right = safe === "reels" ? 140 : 0, top = 220;
        for (const r of textRects) {
          if (r.y + r.h > sr.height - bottom || r.x + r.w > sr.width - right || r.y < top) out.fails.push(`text in the ${safe} UI zone: "${r.t}"`);
        }
      }
      if (chains) out.warns.push(`${chains} "A · B · C" chain(s): a template tell`);
      if (arrows) out.warns.push(`${arrows} line(s) ending in an arrow: a template tell`);
      small.sort((a, b) => a.size / a.floor - b.size / b.floor);
      for (const s of small.slice(0, 5)) out.fails.push(`text at ${Math.round(s.size * 10) / 10}px${s.drawn}; the floor is ${s.floor}px${s.floor > 32 ? " for condensed type" : ""} (about ${Math.round(s.floor / 3)}px on a phone): "${s.t}"`);
      if (small.length > 5) out.fails.push(`${small.length - 5} more text elements under the floor`);
      if (eyebrows >= 3) out.warns.push(`${eyebrows} tiny uppercase tracked labels (an AI-template tell)`);
      if (glows) out.warns.push(`${glows} glow or shadow effect(s); use flat fields (mark data-allow="shadow" if deliberate)`);
      if (gradients) out.warns.push(`${gradients} gradient(s); use flat fields (mark data-allow="gradient" if deliberate)`);
      if (out.sizes.size > 6) out.warns.push(`${out.sizes.size} font sizes; two or three should do the work`);
      if (out.families.size > 3) out.warns.push(`${out.families.size} typefaces: ${[...out.families].join(", ")}`);
      if (out.words > WORDS) out.warns.push(`${out.words} words on one page, ${out.words - WORDS} over the budget of ${WORDS} (references/copy.md "Word budget": the hook, the object's labels, one line of proof and the source; the post text carries the rest). Cut ${out.words - WORDS} word${out.words - WORDS === 1 ? "" : "s"} before a critic sees the page`);
      if (out.chars && out.centredChars / out.chars > 0.72) out.warns.push("over 72% of the text is centred");
      // ---- before the critic: five faults the 30 Oct 2026 art-directors charged that no check above names (warnings, never fails)
      // 1. phone read: text a phone shows at 12 px or less, or under about 13 px in a thin stroke, fine print included (references/type.md)
      const thin = owns.filter((o) => !o.el.closest("[data-role=logo]") && (o.size < 36 || (o.size < 40 && o.weight < 500)));
      if (thin.length) out.warns.push(`phone read: ${thin.length} line(s) under 36 px, or under 40 px in a weight under 500, fine print included (${thin.slice(0, 3).map((o) => `"${o.own.slice(0, 24)}" ${Math.round(o.size)}px ${o.weight}`).join(", ")}${thin.length > 3 ? ", ..." : ""}); at 360 px wide that is about ${Math.round(Math.min(...thin.map((o) => o.size)) / 3)} px, and the art-director charges it: set a line the reader needs at 36 to 40 px in weight 500 or more, or move it to the post text (references/type.md "Floors and legibility")`);
      // 2. claim twice: another line on the page repeats the hook's words ("9 fit one pause" under "Nine fit one pause.")
      const NUM = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty".split(" ");
      const STOP = new Set("a an the of to in on at for and or by with from as is are was be it its this that so".split(" "));
      const words = (s) => s.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, " ").split(" ").filter((w) => w && !STOP.has(w)).map((w) => (NUM.includes(w) ? String(NUM.indexOf(w)) : w.length > 3 && w.endsWith("s") ? w.slice(0, -1) : w));
      const hookWords = new Set(words([...sec.querySelectorAll("[data-role=hook]")].map((h) => h.textContent).join(" ")));
      for (const o of owns) {
        if (!hookWords.size || o.el.closest("[data-role=hook],[data-role=fine],[data-role=logo]")) continue;
        const w = words(o.own), shared = w.filter((x) => hookWords.has(x));
        if (w.length >= 3 && shared.length / w.length >= 0.75) { out.warns.push(`claim twice: "${o.own.slice(0, 32)}" repeats the hook's words (${[...new Set(shared)].join(", ")}); the page says its claim once, in the hook: label the device with its number alone, or cut the line (references/copy.md "Rules")`); break; }
      }
      // 3. wrapped run: identical marks (boxes, dots, ticks) that wrap and leave a shorter last row, so the count no longer reads as one run
      const groups = new Map();
      for (const e of sec.querySelectorAll("*")) {
        if (!visible(e) || e.textContent.trim() || !e.parentElement) continue;
        const r = e.getBoundingClientRect(), cs = getComputedStyle(e);
        if (r.width < 8 || r.height < 8 || r.width > 200 || r.height > 200 || !(hasFill(cs) || boxSides(cs) >= 3 || /^(circle|rect|ellipse|img)$/i.test(e.tagName))) continue;
        const k = groups.get(e.parentElement) || new Map(); groups.set(e.parentElement, k);
        const id = `${e.tagName}|${Math.round(r.width)}|${Math.round(r.height)}`; if (!k.has(id)) k.set(id, []); k.get(id).push(r);
      }
      const wrapped = [];
      for (const [parent, byKind] of groups) for (const rs of byKind.values()) {
        if (rs.length < 4) continue;
        const rows = [];
        for (const r of [...rs].sort((a, b) => a.top - b.top || a.left - b.left)) { const l = rows[rows.length - 1]; if (l && Math.abs(r.top - l.top) < r.height / 2) l.n++; else rows.push({ top: r.top, left: r.left, h: r.height, n: 1 }); }
        let chain = [rows[0]];
        const flush = () => { if (chain.length >= 2 && chain[chain.length - 1].n < chain[0].n) wrapped.push(`${chain.reduce((s, x) => s + x.n, 0)} as ${chain.map((x) => x.n).join(" + ")} (${label(parent)})`); };
        for (const r of rows.slice(1)) { const p = chain[chain.length - 1]; if (Math.abs(r.left - p.left) <= 4 && r.top - p.top <= 2 * p.h) chain.push(r); else { flush(); chain = [r]; } }
        flush();
      }
      if (wrapped.length) out.warns.push(`wrapped run: a run of identical marks wraps and leaves a short last row: ${wrapped.slice(0, 3).join("; ")}; a count reads as one run: set it on one line (a smaller mark or gap), or break it where the count itself breaks`);
      // 4. hairline accent: the accent mark (data-role="accent", no text) is drawn thinner than 8 px, about 2.7 px on a phone
      for (const a of sec.querySelectorAll("[data-role=accent]")) {
        if (a.textContent.trim() || !visible(a)) continue;
        let t = 0;
        for (const p of [a, ...a.querySelectorAll("*")]) {
          const cs = getComputedStyle(p), r = p.getBoundingClientRect();
          if (p instanceof SVGElement) {
            if (!/^(path|line|polyline|polygon|rect|circle|ellipse)$/i.test(p.tagName)) continue;
            const m = p.getScreenCTM && p.getScreenCTM(), k = m ? Math.sqrt(Math.abs(m.a * m.d - m.b * m.c)) : 1;
            if (cs.stroke !== "none" && px(cs.strokeWidth) > 0) t = Math.max(t, px(cs.strokeWidth) * k);
            if (cs.fill !== "none" && (rgb(cs.fill)?.a ?? 1) > 0.1 && !/^(line|polyline)$/i.test(p.tagName)) t = Math.max(t, Math.min(r.width, r.height));
          } else {
            const k = scaleOf(p);
            for (const s of ["Top", "Right", "Bottom", "Left"]) if (px(cs[`border${s}Width`]) && !/none|hidden/.test(cs[`border${s}Style`])) t = Math.max(t, px(cs[`border${s}Width`]) * k);
            if (hasFill(cs)) t = Math.max(t, Math.min(r.width, r.height));
          }
        }
        if (t > 0 && t < 8) { out.warns.push(`hairline accent: the accent mark ${label(a)} is drawn ${Math.round(t * 10) / 10} px thick, about ${Math.round(t / 3 * 10) / 10} px on a phone, the lightest mark on the page; the accent carries the one thing to remember: draw it 8 px or more, or carry it in a filled shape or the type`); break; }
      }
      // 5. empty cell: in one row of cells (side by side, the same height), one cell's content spans under 40% of its height beside one over 75%
      const extent = (c) => {
        const cr = c.getBoundingClientRect(); let top = Infinity, bottom = -Infinity;
        const add = (r) => { if (r.width >= 2 && r.height >= 2) { top = Math.min(top, r.top); bottom = Math.max(bottom, r.bottom); } };
        const tw2 = document.createTreeWalker(c, NodeFilter.SHOW_TEXT);
        for (let n = tw2.nextNode(); n; n = tw2.nextNode()) if (n.textContent.trim() && visible(n.parentElement)) { const g = document.createRange(); g.selectNodeContents(n); [...g.getClientRects()].forEach(add); }
        for (const d of c.querySelectorAll("*")) { if (!visible(d)) continue; const cs = getComputedStyle(d); if (hasFill(cs) || boxSides(cs) >= 1 || /^(path|line|rect|circle|ellipse|polygon|polyline|img)$/i.test(d.tagName)) add(d.getBoundingClientRect()); }
        return top === Infinity ? null : { text: (c.textContent.trim().split("\n")[0] || "").slice(0, 28), fill: (bottom - top) / cr.height, w: cr.width, h: cr.height, el: c };
      };
      let emptyCell = null;
      for (const p of [sec, ...sec.querySelectorAll("*")]) {
        const kids = [...p.children].filter((k) => visible(k) && !(k instanceof SVGElement)).map((k) => ({ k, r: k.getBoundingClientRect() })).filter(({ r }) => r.width >= 160 && r.height >= 160);
        for (let x = 0; x < kids.length && !emptyCell; x++) for (let y = x + 1; y < kids.length && !emptyCell; y++) {
          const A = kids[x].r, B = kids[y].r, vo = Math.min(A.bottom, B.bottom) - Math.max(A.top, B.top), ho = Math.min(A.right, B.right) - Math.max(A.left, B.left);
          if (ho > 4 || vo < 0.8 * Math.max(A.height, B.height)) continue;
          const ea = extent(kids[x].k), eb = extent(kids[y].k);
          if (!ea || !eb) continue;
          const [lo, hi] = ea.fill < eb.fill ? [ea, eb] : [eb, ea];
          if (lo.fill < 0.4 && hi.fill >= 0.75) emptyCell = `empty cell: "${lo.text}" spans ${Math.round(lo.fill * 100)}% of its cell (${label(lo.el)}, ${Math.round(lo.w)} x ${Math.round(lo.h)} px) beside a cell filled to ${Math.round(hi.fill * 100)}%: one half of the row carries all the weight; give the empty cell its own material, or shorten the row (references/composition.md "Space")`;
        }
        if (emptyCell) break;
      }
      if (emptyCell) out.warns.push(emptyCell);
      // ---- two more the 30 Oct 2026 art-directors charged (round 12): a mark the reader needs drawn too faint, and display type drawn too thin
      // 6. faint mark (WCAG 1.4.11, non-text contrast 3:1): a shape with no text (a slot, a dot, a bar, an outline, an SVG shape), its fill
      //    or its border composited over the ground right behind it. Fields and panels that carry words are grounds, not marks.
      const SHAPE = /^(path|circle|ellipse|rect|polygon|polyline|line)$/i;
      const alphaOf = (e) => { let a = 1; for (let x = e; x && x !== sec.parentElement; x = x.parentElement) a *= Number(getComputedStyle(x).opacity); return a; };
      const over = (c, a, g) => ({ r: c.r * a + g.r * (1 - a), g: c.g * a + g.g * (1 - a), b: c.b * a + g.b * (1 - a) });
      // the ground behind a mark. A small shape in the mark's own colour (a dot on its line, a tick on its bar) is part of the same drawn
      // shape, not its ground, and a shape smaller than the mark (a dot under a marker) cannot be its ground: skip both and measure against
      // what lies behind. A large field in the mark's colour still counts (an invisible mark on its panel is faint). An SVG line has no fill.
      const behind = (e, r, own) => {
        const same = (c) => own.some((o) => Math.max(Math.abs(o.r - c.r), Math.abs(o.g - c.g), Math.abs(o.b - c.b)) <= 6);
        const area = (x) => { const b = x.getBoundingClientRect(); return b.width * b.height; };
        const notGround = (x, c) => area(x) < r.width * r.height || (same(c) && area(x) <= 0.1 * pageArea);
        const stack = document.elementsFromPoint(r.left + r.width / 2, r.top + r.height / 2), k = stack.indexOf(e);
        const chain = k >= 0 ? stack.slice(k + 1) : (() => { const a = []; for (let x = e.parentElement; x; x = x.parentElement) a.push(x); return a; })();
        for (const x of chain) {
          if (x === e || e.contains(x)) continue;
          if (/^(CANVAS|IMG|VIDEO)$/.test(x.tagName)) return null;
          const cs = getComputedStyle(x);
          if (x instanceof SVGElement) {
            if (SHAPE.test(x.tagName) && x.tagName.toLowerCase() !== "line" && cs.fill !== "none") { const c = rgb(cs.fill); if (c && c.a * Number(cs.fillOpacity) > 0.5 && !notGround(x, c)) return c; }
            continue;
          }
          if (cs.backgroundImage && cs.backgroundImage !== "none") return null;
          const c = rgb(cs.backgroundColor);
          if (c && c.a > 0.5 && !notGround(x, c)) return c;
        }
        return { r: 255, g: 255, b: 255, a: 1 };
      };
      const faint = new Map(), pageArea = sr.width * sr.height;
      for (const e of sec.querySelectorAll("*")) {
        const svg = e instanceof SVGElement;
        if ((svg ? !SHAPE.test(e.tagName) || e.closest("defs,clipPath,mask,pattern,marker,symbol") : e.textContent.trim() || e.children.length || /^(IMG|VIDEO|CANVAS|BR)$/.test(e.tagName))
          || !visible(e) || e.closest("[data-role=logo],[data-allow~=faint]")) continue;
        const r = e.getBoundingClientRect();
        if (Math.max(r.width, r.height) < 8 || Math.min(r.width, r.height) < 2 || r.width * r.height > 0.1 * pageArea) continue;
        if (textRects.some((T) => sr.left + T.x + T.w / 2 > r.left && sr.left + T.x + T.w / 2 < r.right && sr.top + T.y + T.h / 2 > r.top && sr.top + T.y + T.h / 2 < r.bottom)) continue;   // it carries words: a ground
        const cs = getComputedStyle(e), paints = [];
        if (svg) {
          if (cs.fill !== "none" && e.tagName.toLowerCase() !== "line") paints.push([rgb(cs.fill), Number(cs.fillOpacity)]);
          if (cs.stroke !== "none" && px(cs.strokeWidth) > 0) paints.push([rgb(cs.stroke), Number(cs.strokeOpacity)]);
        } else {
          if (!(cs.backgroundImage && cs.backgroundImage !== "none")) paints.push([rgb(cs.backgroundColor), 1]);
          const side = ["Top", "Right", "Bottom", "Left"].find((s) => px(cs[`border${s}Width`]) >= 1 && !/none|hidden/.test(cs[`border${s}Style`]));
          if (side) paints.push([rgb(cs[`border${side}Color`]), 1]);
        }
        const a0 = alphaOf(e), shown = paints.filter(([c, o]) => c && c.a * o * a0 >= 0.05);
        if (!shown.length) continue;
        const g = behind(e, r, shown.map(([c]) => c));
        if (!g) continue;   // over a picture, a gradient or a drawn film: not measured here
        const best = Math.max(...shown.map(([c, o]) => ratio(over(c, c.a * o * a0, g), g)));
        if (best < 3) { const key = `${label(e)} ${best.toFixed(1)}:1`; faint.set(key, (faint.get(key) || 0) + 1); }
      }
      if (faint.size) {
        const n = [...faint.values()].reduce((s, x) => s + x, 0), list = [...faint].sort((p, q) => parseFloat(p[0].split(" ").pop()) - parseFloat(q[0].split(" ").pop()));
        out.warns.push(`faint mark: ${n} mark(s) with no text under 3:1 against the ground behind them (${list.slice(0, 3).map(([k, x]) => (x > 1 ? `${x} x ${k}` : k)).join(", ")}${list.length > 3 ? ", ..." : ""}); WCAG 1.4.11 asks 3:1 for a mark the reader needs (an empty slot, a dot, a bar, an outline): darken it to 3:1 or more, or mark data-allow="faint" if it is decoration only`);
      }
      // 7. thin stroke: display type (48 px or more as drawn) in a script, hairline or light face, whose stroke is under 6 px (2 px on a phone at
      //    360 px wide) and under 6.5% of its size. Regular text faces draw 7 to 9% of their size, so a large regular line passes.
      //    The stroke is measured on the glyphs: twice the ink area over the ink outline, drawn in the element's own font.
      const strokeOf = (o) => {
        const cs = getComputedStyle(o.el), font = `${cs.fontStyle} ${cs.fontWeight} ${o.size}px ${cs.fontFamily}`, text = o.own.slice(0, 40);
        const cv2 = document.createElement("canvas"), g = cv2.getContext("2d");
        g.font = font;
        const w = Math.ceil(g.measureText(text).width) + 20, h = Math.ceil(o.size * 1.6);
        if (w < 21 || w * h > 4e6) return 0;
        cv2.width = w; cv2.height = h;
        g.font = font; g.textBaseline = "middle"; g.fillStyle = "#000"; g.fillText(text, 10, h / 2);
        const d = g.getImageData(0, 0, w, h).data, ink = (x, y) => x >= 0 && y >= 0 && x < w && y < h && d[(y * w + x) * 4 + 3] > 127;
        let area = 0, edge = 0;
        for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) if (ink(x, y)) { area++; if (!ink(x + 1, y) || !ink(x - 1, y) || !ink(x, y + 1) || !ink(x, y - 1)) edge++; }
        return edge ? (2 * area) / edge : 0;
      };
      for (const o of owns) {
        if (o.size < 48 || o.el instanceof SVGElement || o.el.closest("[data-role=logo],[data-role=fine]") || !/[\p{L}\p{N}]/u.test(o.own)) continue;
        const s = strokeOf(o);
        if (s > 0 && s < 6 && s / o.size < 0.065) {
          out.warns.push(`thin stroke: "${(o.el.innerText || o.own).replace(/\s+/g, " ").trim().slice(0, 28)}" ${Math.round(o.size)}px in ${getComputedStyle(o.el).fontFamily.split(",")[0].replace(/["']/g, "")} draws its strokes about ${s.toFixed(1)} px thick, about ${(s / 3).toFixed(1)} px on a phone (${(100 * s / o.size).toFixed(1)}% of its size; a regular text face draws 7 to 9%); at 360 px wide the biggest words read as hairlines: set the line in a heavier weight or face, or larger, so its stroke is 6 px or more (references/type.md "Floors and legibility")`);
          break;
        }
      }
      let dr; try { dr = doctrine(sec); } catch (err) { dr = { warns: [`the design-doctrine checks could not run: ${err.message}`], rawColours: 0 }; }
      out.warns.push(...dr.warns); out.rawColours = dr.rawColours;
      out.sizes = [...out.sizes].sort((a, b) => a - b); out.families = [...out.families];
      out.centred = out.chars ? Math.round((100 * out.centredChars) / out.chars) : 0;
      delete out.centredChars; delete out.chars;
      pages.push(out);
    }
    return pages;
  };
  // auditAt(t, cover): every page at film time t, seeked as motion.mjs seeks (null: the page as loaded). Each pass first shoots the page
  // with its text made invisible: what the text sits on, for contrast over a gradient, a hatch or a drawn film.
  const auditAt = async (t, cover) => {
    if (t !== null) await page.evaluate((ms) => { for (const a of document.getAnimations()) { a.pause(); a.currentTime = ms; } if (typeof window.seek === "function") window.seek(ms / 1000); }, t * 1000);
    const hide = await page.addStyleTag({ content: "*{-webkit-text-fill-color:transparent!important;-webkit-text-stroke:0!important;text-shadow:none!important;text-decoration:none!important}text,tspan,textPath{fill:transparent!important;stroke:none!important}" });
    const shots = [];
    for (const s of sections) shots.push((await s.screenshot()).toString("base64"));
    await hide.evaluate((e) => e.remove());
    return page.evaluate(auditPages, { safe, shots, rawMax, WORDS, cover });
  };
  await page.addStyleTag({ content: "*{pointer-events:auto!important}" });   // so elementsFromPoint also sees overlays that ignore the pointer
  const report = await auditAt(null, true);
  // a motion page: the hard rules again every half second and at the poster time
  const film = await page.evaluate(() => ({ moving: typeof window.seek === "function" || document.getAnimations().length > 0, art: (window.ART && window.ART.duration) || 0,
    css: Math.max(0, ...document.getAnimations().map((a) => (a.effect ? a.effect.getComputedTiming().endTime : 0)).filter(Number.isFinite)) / 1000 }));
  const lenIdx = args.indexOf("--seconds"), posterIdx = args.indexOf("--poster");
  const length = lenIdx >= 0 ? Number(args[lenIdx + 1]) : Number(timeline?.seconds) || film.art || film.css;
  const times = [], poster = posterIdx >= 0 ? Number(args[posterIdx + 1]) : Math.min(3, length / 2);
  if (film.moving && length > 0) {
    for (let k = 1; k / 2 < length; k++) times.push(k / 2);   // every half second: a fault on screen for a second or less still shows
    if (poster > 0 && poster < length && !times.includes(poster)) times.push(poster);
    times.sort((a, b) => a - b);
  } else if (film.moving) console.log("audit: a motion page of unknown length, checked at its first frame only; pass --seconds N (as for motion.mjs) to check every half second and the poster time");
  const known = report.map((p) => new Set(p.fails));
  let posterBoxes = null;   // the labelled boxes where they are at the poster time: attention.py and cvd.py read poster.png with them
  for (const t of times) {
    let later;
    try { later = await auditAt(t, false); } catch (err) {   // the page threw while seeking or being measured at t: one FAIL line, not a stack trace
      report[0].fails.push(`at ${t} s: the page threw an error here: ${String((err && err.message) || err).split(/\r?\n/)[0].replace(/^page\.evaluate: /, "")} (later times not checked: fix it and audit again)`);
      break;
    }
    if (t === poster) posterBoxes = later[0].boxes;
    for (const [i, p] of later.entries()) for (const f of p.fails) if (!known[i].has(f)) { known[i].add(f); report[i].fails.push(`at ${t} s: ${f}`); }
  }
  if (film.moving) for (const p of report) p.times = times;
  fs.writeFileSync(path.join(outDir, "audit.json"), JSON.stringify(report, null, 1));
  fs.writeFileSync(path.join(outDir, "boxes.json"), JSON.stringify([...report.map((p) => ({ page: p.page, boxes: p.boxes })), ...(posterBoxes ? [{ page: "poster", boxes: posterBoxes }] : [])], null, 1));
  for (const p of report) {
    console.log(`audit page ${p.page}: ${p.words} words, min ${p.minFont}px${p.minAll < p.minFont ? ` (${p.minAll}px with fine print)` : ""}, sizes ${p.sizes.join("/")}, ${p.families.join(" + ")}${p.rawColours ? `, ${p.rawColours} raw colour(s)` : ""}${p.accent !== undefined ? `, accent paint ${p.accent}%` : ""}${p.times && p.times.length ? `; hard rules checked again at ${p.times.join(", ")} s` : ""}`);
    for (const f of p.fails) console.log(`  FAIL ${f}`);
    for (const w of p.warns) console.log(`  warn ${w}`);
    if (p.fails.length) auditFail = true;
  }
  console.log(auditFail ? "audit: FAIL" : "audit: PASS (no hard fails)");
}
await browser.close();

if (scenesFile) {
  const scenes = JSON.parse(fs.readFileSync(scenesFile, "utf8"));
  const list = path.join(outDir, "scenes.txt");
  const lines = [];
  for (const s of scenes) {
    lines.push(`file '${pngs[s.page - 1].replace(/\\/g, "/")}'`, `duration ${s.seconds}`);
  }
  lines.push(`file '${pngs[scenes[scenes.length - 1].page - 1]}'`);
  fs.writeFileSync(list, lines.join("\n") + "\n");
  const out = path.join(outDir, "video.mp4");
  execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", list,
    "-vf", `fps=30,format=yuv420p,scale=${W}:${H}`, "-c:v", "libx264", "-preset", "medium", "-crf", "20",
    "-movflags", "+faststart", out]);
  fs.unlinkSync(list);
  const total = scenes.reduce((a, s) => a + s.seconds, 0);
  console.log(`video: ${out} (${total}s, no audio, captions burned in)`);
}
if (auditFail) process.exitCode = 1;
