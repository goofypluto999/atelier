#!/usr/bin/env node
// Render a CSS-animated page to a sharp MP4, frame by frame. Free and local: Playwright plus ffmpeg.
//
//   node motion.mjs <motion.html> --seconds 20 [--fps 30] [--sub 4] [--poster 3.5] [--size 1080x1350] [--out <dir>]
//
// motion.html holds ONE <section class="page">. Three ways to animate it:
//   1. CSS @keyframes (animation-delay places each beat). Every animation is paused and stepped to the
//      exact frame time.
//   2. A pure function of time: window.seek(t) paints the frame for t seconds. Use the skill's assets/lib/motion.js
//      (closed-form springs, track() for values with several targets). No timers, no Math.random.
//   3. A drawn film: ART.film (assets/lib/art-motion.js) paints a canvas world with a camera, springs and a film
//      finish under the page's words, and sets window.seek(t) (references/art-motion.md).
// If window.seek exists it is used; CSS animations are stepped as well, so the two can be mixed.
// --sub N renders N steps per frame and blends them: real motion blur on fast moves (default 1, try 4).
// The page may load local files only: any other request (http, https, ws) is blocked and the render fails.
// Writes video.mp4 (H.264, yuv420p, no audio), frame0.png, poster.png (the frame at --poster seconds)
// and, if captions.json exists next to the HTML ([{start, end, text}] in seconds), captions.srt; next to the HTML,
// or in --out <dir>.
// Words on screen: mark each block of words to read with data-read="<id>", and words drawn on a canvas with
// window.texts(t) = [{id, text, x0, y0, x1, y1}] (page pixels). motion.mjs then writes texts.json: for each piece, its longest
// stretch whole on screen (every word at opacity 0.9 or more, every line inside the page, each overflow box and each clip-path
// inset) and when it starts. The same id with new text is a new piece. video_check.py judges the reading time (references/motion.md).
import { createRequire } from "node:module";
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

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
const opt = (name, def) => {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : def;
};
if (!file) {
  console.error("usage: node motion.mjs <motion.html> --seconds 20 [--fps 30] [--sub 4] [--poster 3.5] [--size 1080x1350] [--out <dir>]");
  process.exit(2);
}
const seconds = Number(opt("--seconds", "20"));
const fps = Number(opt("--fps", "30"));
const sub = Math.max(1, Number(opt("--sub", "1")));
const posterAt = Number(opt("--poster", String(Math.min(3, seconds / 2))));
const [w, h] = opt("--size", "1080x1350").split("x").map(Number);
const src = path.dirname(path.resolve(file));
const dir = path.resolve(opt("--out", src));
fs.mkdirSync(dir, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
// local files only: a film never fetches from the network, so its frames cannot change with a remote server
const blocked = [];
await page.route("**/*", (r) => (/^(file|data|blob):/.test(r.request().url()) ? r.continue() : (blocked.push(r.request().url()), r.abort())));
await page.goto(pathToFileURL(path.resolve(file)).href, { waitUntil: "networkidle" });
if (blocked.length) {
  console.error(`motion: blocked ${blocked.length} request(s) that are not local files; a film loads local files only:\n  ${blocked.join("\n  ")}`);
  await browser.close();
  process.exit(1);
}
await page.evaluate(() => document.fonts.ready);
const el = await page.$("section.page");
if (!el) throw new Error('no <section class="page"> found');
// Each frame is the page box, measured again at every step, so a page box that moves is followed. An element screenshot
// rounds a box that starts between two pixels outward, one pixel more than the box (a collapsed margin of 26.8 px gives 451
// rows for 450), and H.264 in yuv420p refuses an odd size ("ffmpeg 187"). So the clip takes the box's size rounded to an even
// number of pixels and ends where the browser paints the box's far edge (that edge rounded), never past the document's end.
// A box on whole pixels with an even size gives the same clip as before.
await page.evaluate(() => {
  window.__atelierClip = () => {
    const r = document.querySelector("section.page").getBoundingClientRect();
    const width = 2 * Math.round(r.width / 2), height = 2 * Math.round(r.height / 2);
    return { x: Math.max(0, Math.round(r.right + scrollX) - width), y: Math.max(0, Math.round(r.bottom + scrollY) - height), width, height };
  };
});
// The reading-time check (the idea of lemo-opuscar's core/render/readcheck.mjs, MIT, commit bebbbe1, rewritten for DOM pages):
// a marked block is judged by the line boxes of its own text, so a hidden word, a line still inside its mask or a clip-path
// reveal keeps the block from being whole. Not seen: an element painted over the words (render.mjs --audit checks text over text).
const reads = await page.evaluate(() => {
  const pg = document.querySelector("section.page");
  const fits = (r, c, dy) => r.left >= c.left - 0.5 && r.right <= c.right + 0.5 && r.top >= c.top - dy && r.bottom <= c.bottom + dy;
  const inset = (a, cs) => {   // clip-path: inset(...) as a box; other clip shapes are not modelled
    const m = /^inset\(([^)]*)\)/.exec(cs.clipPath || "");
    if (!m) return null;
    const r = a.getBoundingClientRect(), [t, rt = t, b = t, l = rt] = m[1].split(" round ")[0].trim().split(/\s+/);
    const len = (v, full) => (v.endsWith("%") ? (parseFloat(v) / 100) * full : parseFloat(v) || 0);
    return { left: r.left + len(l, r.width), right: r.right - len(rt, r.width), top: r.top + len(t, r.height), bottom: r.bottom - len(b, r.height) };
  };
  const state = (node, P) => {   // null: not drawn; otherwise whether it is nearly opaque and every line box is inside every clip
    const host = node.parentElement, range = document.createRange();
    range.selectNodeContents(node);
    const lines = [...range.getClientRects()].filter((r) => r.width > 0 && r.height > 0);
    if (!lines.length || getComputedStyle(host).visibility !== "visible") return null;
    const dy = Math.max(0.5, 0.2 * (parseFloat(getComputedStyle(host).fontSize) || 16));   // a glyph box is taller than a tight line box
    const clips = [P];
    let alpha = 1;
    for (let a = host; a && a !== pg.parentElement; a = a.parentElement) {
      const cs = getComputedStyle(a);
      alpha *= Number(cs.opacity);
      if (cs.overflow !== "visible") clips.push(a.getBoundingClientRect());
      const c = inset(a, cs);
      if (c) clips.push(c);
    }
    return { opaque: alpha >= 0.9, whole: lines.every((r) => clips.every((c) => fits(r, c, dy))) };
  };
  window.__atelierWords = (t) => {
    const P = pg.getBoundingClientRect(), out = [];
    pg.querySelectorAll("[data-read]").forEach((e, n) => {
      const text = (e.textContent || "").replace(/\s+/g, " ").trim();
      if (!text) return;
      const parts = [], walk = document.createTreeWalker(e, NodeFilter.SHOW_TEXT);
      for (let node = walk.nextNode(); node; node = walk.nextNode()) if (node.data.trim()) parts.push(state(node, P));
      const lit = parts.filter((s) => s && s.opaque);
      if (lit.length) out.push({ id: e.dataset.read || `read-${n + 1}`, text, whole: lit.length === parts.length && lit.every((s) => s.whole) });
    });
    if (typeof window.texts === "function") {
      for (const b of window.texts(t) || []) {
        const text = String(b.text ?? "").replace(/\s+/g, " ").trim();
        const box = { left: b.x0, top: b.y0, right: b.x1, bottom: b.y1 }, frame = { left: 0, top: 0, right: P.width, bottom: P.height };
        if (text) out.push({ id: String(b.id), text, whole: fits(box, frame, 0.5) });
      }
    }
    return out;
  };
  return pg.querySelector("[data-read]") !== null || typeof window.texts === "function";
});
const seen = [];

const out = path.join(dir, "video.mp4");
const vf = sub > 1 ? `tmix=frames=${sub},select='eq(mod(n\\,${sub})\\,${sub - 1})',setpts=N/${fps}/TB,format=yuv420p` : "format=yuv420p";
const ff = spawn("ffmpeg", ["-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", String(fps * sub), "-i", "-",
  "-vf", vf, "-r", String(fps), "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-movflags", "+faststart", out]);
const done = new Promise((res, rej) => ff.on("close", (c) => (c === 0 ? res() : rej(new Error("ffmpeg " + c)))));

const total = Math.round(seconds * fps * sub);
const posterFrame = Math.max(0, Math.min(total - 1, Math.round(posterAt * fps * sub)));   // the nearest step: a time halfway between two once gave no poster.png
for (let i = 0; i < total; i++) {
  const t = (i / (fps * sub)) * 1000;
  const { words, clip } = await page.evaluate(({ ms, look }) => {
    for (const a of document.getAnimations()) { a.pause(); a.currentTime = ms; }
    if (typeof window.seek === "function") window.seek(ms / 1000);
    return { words: look ? window.__atelierWords(ms / 1000) : null, clip: window.__atelierClip() };
  }, { ms: t, look: reads && i % sub === 0 });
  if (words) seen.push(words);
  const buf = await page.screenshot({ type: "png", clip, fullPage: true });
  if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once("drain", r));
  if (i === 0) fs.writeFileSync(path.join(dir, "frame0.png"), buf);
  if (i === posterFrame) fs.writeFileSync(path.join(dir, "poster.png"), buf);
}
ff.stdin.end();
await done;
await browser.close();

const textsFile = path.join(dir, "texts.json");
if (reads) {
  // One entry per piece (an id with its text): its longest whole stretch. A gap of 0.2 s or less (a shake, a punch) does not end a stretch.
  const bridge = Math.round(0.2 * fps), pieces = new Map();
  seen.forEach((words, f) => {
    for (const w of words) {
      const key = JSON.stringify([w.id, w.text]);
      if (!pieces.has(key)) pieces.set(key, { id: w.id, text: w.text, first: f, frames: [] });
      if (w.whole) pieces.get(key).frames.push(f);
    }
  });
  const texts = [...pieces.values()].map(({ id, text, first, frames }) => {
    if (!frames.length) return { id, text, start: +(first / fps).toFixed(3), shown: 0, whole: false };
    let best = [frames[0], frames[0]], run = best;
    for (const f of frames.slice(1)) {
      run = f - run[1] - 1 <= bridge ? [run[0], f] : [f, f];
      if (run[1] - run[0] > best[1] - best[0]) best = run;
    }
    return { id, text, start: +(best[0] / fps).toFixed(3), shown: +((best[1] - best[0] + 1) / fps).toFixed(3), whole: true };
  });
  fs.writeFileSync(textsFile, JSON.stringify({ fps, seconds, texts }, null, 1) + "\n");
} else {
  fs.rmSync(textsFile, { force: true });   // an older film's texts.json in the same folder would be judged as this one's
}

const capFile = path.join(src, "captions.json");
if (fs.existsSync(capFile)) {
  const caps = JSON.parse(fs.readFileSync(capFile, "utf8"));
  const ts = (s) => {
    const ms = Math.round(s * 1000);
    const hh = String(Math.floor(ms / 3600000)).padStart(2, "0");
    const mm = String(Math.floor((ms % 3600000) / 60000)).padStart(2, "0");
    const ss = String(Math.floor((ms % 60000) / 1000)).padStart(2, "0");
    return `${hh}:${mm}:${ss},${String(ms % 1000).padStart(3, "0")}`;
  };
  fs.writeFileSync(path.join(dir, "captions.srt"),
    caps.map((c, i) => `${i + 1}\n${ts(c.start)} --> ${ts(c.end)}\n${c.text}\n`).join("\n"));
}
console.log(`motion: ${out} (${seconds}s at ${fps} fps${sub > 1 ? `, ${sub} blended steps per frame` : ""}, no audio) + poster.png + frame0.png${reads ? " + texts.json" : ""}`);
