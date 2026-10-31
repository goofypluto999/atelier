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

const out = path.join(dir, "video.mp4");
const vf = sub > 1 ? `tmix=frames=${sub},select='eq(mod(n\\,${sub})\\,${sub - 1})',setpts=N/${fps}/TB,format=yuv420p` : "format=yuv420p";
const ff = spawn("ffmpeg", ["-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", String(fps * sub), "-i", "-",
  "-vf", vf, "-r", String(fps), "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-movflags", "+faststart", out]);
const done = new Promise((res, rej) => ff.on("close", (c) => (c === 0 ? res() : rej(new Error("ffmpeg " + c)))));

const total = Math.round(seconds * fps * sub);
const posterFrame = Math.max(0, Math.min(total - 1, Math.round(posterAt * fps * sub)));   // the nearest step: a time halfway between two once gave no poster.png
for (let i = 0; i < total; i++) {
  const t = (i / (fps * sub)) * 1000;
  await page.evaluate((ms) => {
    for (const a of document.getAnimations()) { a.pause(); a.currentTime = ms; }
    if (typeof window.seek === "function") window.seek(ms / 1000);
  }, t);
  const buf = await el.screenshot({ type: "png" });
  if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once("drain", r));
  if (i === 0) fs.writeFileSync(path.join(dir, "frame0.png"), buf);
  if (i === posterFrame) fs.writeFileSync(path.join(dir, "poster.png"), buf);
}
ff.stdin.end();
await done;
await browser.close();

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
console.log(`motion: ${out} (${seconds}s at ${fps} fps${sub > 1 ? `, ${sub} blended steps per frame` : ""}, no audio) + poster.png + frame0.png`);
